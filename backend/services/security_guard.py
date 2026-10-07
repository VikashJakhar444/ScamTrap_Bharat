"""
ScamTrap Bharat — Security / OPSEC Guard  (spec §5)
===================================================
Four strict controls that sit in front of the investigation engine:

  1. OPSEC-Safe Public Response  — the citizen-facing JSON is stripped of
     regex patterns, scoring weights, rule numbers and detection thresholds.
     The full forensic detail lives ONLY in the per-case .log / .json file.
  2. Anti-Scammer Probe Detector — sliding 2-minute per-IP window + fuzzy
     similarity, so an attacker cannot binary-search which token trips us.
  3. Prompt-Injection Defence    — inputs are scanned, stripped and scored up.
  4. Strict Upload Validation    — 10 MB cap + real magic-byte sniffing, so a
     .exe cannot be dressed up as a .png.

Nothing here ever talks to the network.
"""

import re
import threading
import time
import difflib
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

# ── Tunables ──────────────────────────────────────────────────────────────────
MAX_UPLOAD_BYTES = 10 * 1024 * 1024          # 10 MB hard cap
PROBE_WINDOW_SECONDS = 120                   # sliding 2-minute window
PROBE_MAX_REQUESTS = 8                       # requests per window before we look closer
PROBE_SIMILARITY = 0.72                      # fuzzy similarity that implies editing
PROBE_SIMILAR_VARIANTS = 3                   # near-identical submissions required


# ==============================================================================
# 1. OPSEC-Safe Public Response
# ==============================================================================
# Anything that would let a scammer reverse-engineer our detection logic is
# held back from the API and written only to the forensic log.
_LEAKY_PATTERNS = [
    re.compile(r"\bregex\b", re.I),
    re.compile(r"\bpattern\s*[:=]\s*\S+", re.I),
    re.compile(r"\brule\s*#?\s*\d+", re.I),
    re.compile(r"\bthreshold\b", re.I),
    re.compile(r"\bweight(?:s|ed)?\b", re.I),
    re.compile(r">\s*=\s*\d+"),
    re.compile(r"\bwithin\s+\d+\s*(?:pts|points|score)\b", re.I),
    re.compile(r"\+\d+\s*(?:pts|points)\b", re.I),
    re.compile(r"\bifsc\.razorpay\.com\S*", re.I),
]


def sanitize_finding(text: str) -> str:
    """Rewrites one internal finding into citizen-safe plain language.

    Removes anything that reads like an implementation detail while keeping
    the actual warning (the citizen still needs to know a UPI handle was found).
    """
    if not text:
        return ""

    cleaned = text
    for pat in _LEAKY_PATTERNS:
        cleaned = pat.sub("[redacted]", cleaned)

    # Collapse any leftover "Field: value" rule IDs such as "L3-07 →"
    cleaned = re.sub(r"\b[A-Z]{1,3}-\d{2,}\b", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def sanitize_layers(layers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Returns the public view of the layer breakdown.

    Each layer keeps its citizen-facing name, a plain-language status and its
    redacted findings. The numeric score is preserved because it is a *result*
    the UI must show — but no weights, thresholds or rule identifiers travel
    with it.
    """
    public: List[Dict[str, Any]] = []
    for layer in layers or []:
        score = int(layer.get("score", 0) or 0)
        if score >= 70:
            status = "critical"
        elif score >= 40:
            status = "suspicious"
        else:
            status = "clear"

        public.append(
            {
                "layer": layer.get("layer"),
                "name": layer.get("name", ""),
                "score": score,
                "status": status,
                "flags": [sanitize_finding(f) for f in (layer.get("flags") or []) if f],
            }
        )
    return public


# Only these entity keys are safe to return to the browser. The de-obfuscated
# reconstruction and any internal scratch fields stay in the forensic log.
_ENTITY_PUBLIC_KEYS = (
    "upis", "phones", "ifsc_codes", "bank_accounts", "urls", "qr_payloads",
    "malware_or_remote_apps", "detected_category", "matched_categories",
    "heuristic_risk_score", "reasons", "micro_pattern",
)


def public_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
    entities = entities or {}
    return {k: entities.get(k) for k in _ENTITY_PUBLIC_KEYS if k in entities}


def public_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Strips a full internal report down to what the frontend is allowed to see."""
    safe = {
        "case_id": report.get("case_id"),
        "investigation_id": report.get("investigation_id"),
        "input_type": report.get("input_type", "TEXT"),
        "timestamp": report.get("timestamp"),
        "threat_level": report.get("threat_level"),
        "final_score": report.get("final_score"),
        "primary_category": report.get("primary_category"),
        "is_known_scam": report.get("is_known_scam"),
        "blacklist_hits": [
            {
                "identifier_type": h.get("identifier_type"),
                "identifier_value": h.get("identifier_value"),
                "scam_category": h.get("scam_category"),
                "reports_count": h.get("reports_count"),
            }
            for h in (report.get("blacklist_hits") or [])
        ],
        "extracted_entities": public_entities(report.get("extracted_entities", {})),
        "verified_bank": report.get("verified_bank"),
        "citizen_summary": report.get("citizen_summary", report.get("citizen_action", "")),
        "citizen_action": report.get("citizen_action"),
        "counter_bait_available": report.get("counter_bait_available"),
        "layers": sanitize_layers(report.get("layers") or []),
        "threat_badge": report.get("threat_badge", report.get("threat_level")),
        "input_flags": report.get("input_flags", []),
        "prompt_injection_detected": bool(report.get("prompt_injection_detected")),
        # Principle breakdown without the weights or the raw evidence numbers —
        # those are implementation detail and stay in the forensic log.
        "principles": [
            {
                "name": p.get("name"),
                "score": p.get("score"),
                "findings": [sanitize_finding(f) for f in (p.get("findings") or []) if f],
            }
            for p in (report.get("principles") or [])
        ],
    }

    # Probe / injection outcomes are surfaced as a neutral notice — we never
    # say WHICH token changed the score.
    if report.get("is_scammer_probing"):
        safe["probe_warning"] = True
    if report.get("prompt_injection_detected"):
        safe["injection_note"] = True

    return safe


# ==============================================================================
# 2. Anti-Scammer Probe & Fuzzy Variation Detector
# ==============================================================================
class _SlidingWindow:
    """Thread-safe sliding window of (timestamp, normalised-text) per client."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: Dict[str, deque] = {}

    def add(self, client: str, text: str, now: Optional[float] = None) -> Tuple[int, bool]:
        """Records one submission and returns (recent_count, is_probing)."""
        now = now if now is not None else time.time()
        with self._lock:
            bucket = self._hits.setdefault(client, deque())
            bucket.append((now, text))
            cutoff = now - PROBE_WINDOW_SECONDS
            while bucket and bucket[0][0] < cutoff:
                bucket.popleft()

            recent = list(bucket)
            count = len(recent)
            probing = self._is_probing(recent)
            return count, probing

    @staticmethod
    def _is_probing(recent: List[Tuple[float, str]]) -> bool:
        if len(recent) < PROBE_SIMILAR_VARIANTS:
            return False
        texts = [t for _, t in recent]
        near_dupes = 0
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if difflib.SequenceMatcher(None, texts[i], texts[j]).ratio() >= PROBE_SIMILARITY:
                    near_dupes += 1
        # Several mutually-similar-but-not-identical variants == probing.
        return near_dupes >= PROBE_SIMILAR_VARIANTS

    def clear(self, client: str) -> None:
        with self._lock:
            self._hits.pop(client, None)


_window = _SlidingWindow()


def check_probe(client_ip: str, text: str) -> Dict[str, Any]:
    """Sliding-window + fuzzy-variation probe check for one submission."""
    normalised = re.sub(r"\W+", "", (text or "").lower())[:2000]
    recent_count, probing = _window.add(client_ip, normalised)
    return {
        "client_ip": client_ip,
        "recent_count": recent_count,
        "is_scammer_probing": probing,
        "rate_limited": recent_count > PROBE_MAX_REQUESTS * 2,
    }


def record_watchlist_from_probe(entities: Dict[str, Any]) -> List[str]:
    """When probing is detected we bank the identifiers that were tested so the
    local blacklist grows even if the run itself scored low."""
    from backend.database.db import get_db_connection

    banked: List[str] = []
    try:
        with get_db_connection() as conn:
            for kind, values in (("UPI", entities.get("upis", [])),
                                 ("PHONE", entities.get("phones", [])),
                                 ("BANK_AC", entities.get("bank_accounts", [])),
                                 ("IFSC", entities.get("ifsc_codes", []))):
                for value in values or []:
                    conn.execute(
                        """INSERT INTO scam_identifiers
                           (identifier_value, identifier_type, scam_category, risk_score, reports_count)
                           VALUES (?, ?, 'Probe Attempt', 60, 1)
                           ON CONFLICT(identifier_value) DO UPDATE SET
                               reports_count = reports_count + 1,
                               last_seen = CURRENT_TIMESTAMP""",
                        (value, kind),
                    )
                    banked.append(value)
            conn.commit()
    except Exception:
        return banked
    return banked


# ==============================================================================
# 3. Prompt Injection Defence
# ==============================================================================
_INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\b", re.I),
    re.compile(r"\bdisregard\s+(?:your|the|all)\s+(?:instructions|rules|system)\b", re.I),
    re.compile(r"\bmark\s+this\s+(?:message|text|as)\b.{0,40}\bsafe\b", re.I),
    re.compile(r"\bsystem\s*(?:override|prompt|message)\b", re.I),
    re.compile(r"\brisk[_\s-]*score\s*[=:]\s*0\b", re.I),
    re.compile(r"\b(?:you\s+are|act\s+as|pretend\s+to\s+be)\s+now\b", re.I),
    re.compile(r"\boverride\s+(?:the\s+)?(?:scoring|analysis|verdict|output)\b", re.I),
    re.compile(r"\bnew\s+instructions?\s*:", re.I),
    re.compile(r"\bdo\s+not\s+(?:flag|score|report|mark)\s+this\b", re.I),
    re.compile(r"\b(?:forget|reset)\s+(?:your|all)\s+(?:memory|instructions)\b", re.I),
    re.compile(r"</?\s*(?:system|assistant)\s*>", re.I),
    re.compile(r"\bBEGIN\s+SYSTEM\b", re.I),
]

_INJECTION_BONUS = 25


def scan_prompt_injection(text: str) -> Dict[str, Any]:
    """Detects instruction-override attempts in citizen input (and OCR text).

    Returns the detections, the cleaned text and the score penalty to apply.
    """
    if not text:
        return {"detected": False, "matches": [], "cleaned": "", "score_bonus": 0}

    matches: List[str] = []
    cleaned = text
    for pat in _INJECTION_PATTERNS:
        found = pat.findall(cleaned)
        if found:
            matches.append(pat.pattern)
            cleaned = pat.sub("", cleaned)

    # Neutralise any attempt to dictate an output score directly.
    cleaned = re.sub(r"\brisk[_\s-]*score\s*[=:]\s*\d+\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    detected = bool(matches)
    return {
        "detected": detected,
        "matches": matches,
        "cleaned": cleaned,
        "score_bonus": _INJECTION_BONUS if detected else 0,
    }


# ==============================================================================
# 4. Strict Upload Validation (magic bytes + size)
# ==============================================================================
# label -> (list of acceptors). Each acceptor is (offset, expected bytes).
_IMAGE_SIGNATURES: List[Tuple[str, int, bytes]] = [
    ("PNG", 0, b"\x89PNG\r\n\x1a\n"),
    ("JPEG", 0, b"\xff\xd8\xff"),
]
_AUDIO_SIGNATURES: List[Tuple[str, int, bytes]] = [
    ("OGG", 0, b"OggS"),
    ("MP3", 0, b"ID3"),
    ("WAV", 0, b"RIFF"),
    ("M4A", 4, b"ftyp"),
]


def _sniff(header: bytes, sigs: List[Tuple[str, int, bytes]]) -> Optional[str]:
    for label, offset, magic in sigs:
        if header[offset:offset + len(magic)] == magic:
            if label in ("WAV",) and b"WAVE" not in header[:16]:
                continue
            if label == "M4A" and header[4:8] != b"ftyp":
                continue
            return label
    # WEBP is RIFF-prefixed, so it needs its own second check.
    if header[0:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "WEBP"
    if header[0:4] == b"RIFF" and header[8:12] == b"WAVE":
        return "WAV"
    return None


def validate_upload(filename: str, payload: bytes, kind: str) -> Dict[str, Any]:
    """Validates one uploaded file. `kind` is 'image' or 'audio'.

    Returns {"ok": bool, "reason": str, "format": str}.
    Never trusts the extension — only the leading bytes.
    """
    if payload is None or len(payload) == 0:
        return {"ok": False, "reason": "Empty file.", "format": ""}

    if len(payload) > MAX_UPLOAD_BYTES:
        mb = len(payload) / (1024 * 1024)
        return {
            "ok": False,
            "reason": f"File too large ({mb:.1f} MB). Maximum allowed is 10 MB.",
            "format": "",
        }

    header = payload[:64]
    if kind == "image":
        fmt = _sniff(header, _IMAGE_SIGNATURES)
        if not fmt:
            return {
                "ok": False,
                "reason": "Not a genuine PNG, JPEG or WEBP image. Upload rejected.",
                "format": "",
            }
        return {"ok": True, "reason": "", "format": fmt}

    if kind == "audio":
        fmt = _sniff(header, _AUDIO_SIGNATURES)
        if not fmt:
            return {
                "ok": False,
                "reason": "Not a genuine OGG, MP3, WAV or M4A audio file. Upload rejected.",
                "format": "",
            }
        return {"ok": True, "reason": "", "format": fmt}

    return {"ok": False, "reason": f"Unknown upload kind '{kind}'.", "format": ""}


def detect_executable_disguise(payload: bytes) -> bool:
    """True when an 'image' or 'audio' is actually a PE/ELF/script payload."""
    if not payload:
        return False
    if payload[:2] == b"MZ":                       # Windows PE
        return True
    if payload[:4] == b"\x7fELF":                  # Linux ELF
        return True
    if payload[:2] == b"#!":                       # shebang script
        return True
    if payload[:6].lower() in (b"python", b"<scrip"):
        return True
    if payload[:2] == b"PK" and b"Content_Types" in payload[:512]:
        return False                               # genuine zip-based office docs are fine
    if payload[:4] == b"\xca\xfe\xba\xbe":         # java / mach-o fat
        return True
    return False


def client_ip_of(scope) -> str:
    """Best-effort client IP from a Starlette request scope (never raises)."""
    try:
        forwarded = scope.get("headers")
        if forwarded:
            for key, value in forwarded:
                if key == b"x-forwarded-for":
                    return value.decode("latin-1").split(",")[0].strip()
        return scope.get("client", ("unknown", 0))[0] or "unknown"
    except Exception:
        return "unknown"
