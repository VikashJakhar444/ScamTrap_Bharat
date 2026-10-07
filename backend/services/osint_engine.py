"""
ScamTrap Bharat — OSINT Engine  (spec §3)
==========================================
Five INDEPENDENT investigation layers. Each returns:

    { "layer": n, "name": str, "score": 0-100, "flags": [...], "evidence": {...} }

`score` and `flags` are citizen-facing after `security_guard.sanitize_layers()`.
`evidence` is forensic-only and travels exclusively to the .log / .json file.

Layer 1 — Live Bank & Authority Verification   (IFSC, VPA, authority registry)
Layer 2 — Digital Footprint Correlation        (UPI impersonation, cross-links)
Layer 3 — Network Signal Analysis              (sender type, geography, VoIP)
Layer 4 — URL / Domain & Payload Reputation    (shorteners, typosquat, malware)
Layer 5 — Local Crowd-Sourced Intelligence     (the community blacklist + upsert)
"""

import re
import time
import threading
from typing import Any, Dict, List, Optional

import requests

from backend.database.db import get_db_connection, lookup_identifier, upsert_identifier

# ── Tunables ──────────────────────────────────────────────────────────────────
IFSC_ENDPOINT = "https://ifsc.razorpay.com/{ifsc}"
IFSC_TIMEOUT = 3.5                      # seconds, never let a live call hang a judge demo
IFSC_CACHE_TTL = 6 * 3600               # 6 hours — a branch record rarely changes
UPSCORE_THRESHOLD = 70                  # "report it back to the community" line

_IFSC_CACHE: Dict[str, Dict[str, Any]] = {}
_IFSC_LOCK = threading.Lock()

# ── Static authority / bank registries ────────────────────────────────────────
BANK_FROM_IFSC = {
    "SBIN": "State Bank of India", "HDFC": "HDFC Bank", "ICIC": "ICICI Bank",
    "UTIB": "Axis Bank", "KKBK": "Kotak Mahindra Bank", "PNBK": "Punjab National Bank",
    "BARB": "Bank of Baroda", "CNRB": "Canara Bank", "IDFB": "IDFC First Bank",
    "FDRL": "Federal Bank", "INDB": "IndusInd Bank", "YESB": "Yes Bank",
    "KARB": "Karnataka Bank", "TMBL": "Tamilnad Mercantile Bank",
    "CIUB": "City Union Bank", "DCBL": "DCB Bank", "BDBL": "Bandhan Bank",
    "AUBL": "AU Small Finance Bank", "PPBL": "Paytm Payments Bank",
    "AIRP": "Airtel Payments Bank", "JIOS": "Jio Payments Bank",
}

AUTHORITY_UPI_PREFIXES = [
    "sbihcp", "hdfcbank", "icicibank", "axisbank", "payzapp", "kotak",
    "pnb", "bobworld", "canarabank", "unionbank", "indianbank",
    "bijli", "electricity", "discom", "bses", "bescom", "msedcl",
    "tpost", "indiapost", "passport", "uidai", "mygov", "epfindia",
]

CONSUMER_UPI_SUFFIXES = {"ybl", "ibl", "axl", "apl", "yapl", "pnp", "fbl", "blax"}

SHORTENER_DOMAINS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "is.gd", "ow.ly", "cutt.ly",
    "shorturl.at", "rb.gy", "s.id", "tiny.cc", "t.ly", "bl.ink", "lnkd.in",
    "rebrand.ly", "v.gd", "clck.ru", "trib.al",
}

# Common authority names scammers typosquat.
AUTHORITY_BRANDS = ["sbi", "hdfc", "icici", "axis", "rbi", "uidai", "aadhaar", "irctc"]

TRAI_SPAM_SERIES = re.compile(r"\b(?:14\d{2}|1800\d{6,})\b")
ENTERPRISE_HEADER = re.compile(r"\b[A-Z]{2}-[A-Z0-9]{6,}\b")     # VM-HDFCBK
VOLP_FOREIGN_CC = re.compile(r"\+\s?(?:1|44|234|65|61|971|966|880|92|94|977)\b")


# ==============================================================================
# Layer 1 — Live Bank & Authority Verification
# ==============================================================================
def _live_ifsc(ifsc: str) -> Dict[str, Any]:
    """Cached live IFSC resolution against Razorpay's public IFSC API."""
    key = (ifsc or "").upper()
    if not key:
        return {"ok": False, "reason": "missing"}

    with _IFSC_LOCK:
        hit = _IFSC_CACHE.get(key)
        if hit and time.time() - hit["at"] < IFSC_CACHE_TTL:
            return hit["data"]

    try:
        resp = requests.get(IFSC_ENDPOINT.format(ifsc=key), timeout=IFSC_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            payload = {
                "ok": True,
                "bank": data.get("BANK", ""),
                "branch": data.get("BRANCH", ""),
                "address": data.get("ADDRESS", ""),
                "city": data.get("CITY", ""),
                "state": data.get("STATE", ""),
                "ifsc": data.get("IFSC", key),
            }
        elif resp.status_code == 404:
            payload = {"ok": False, "reason": "not_found"}
        else:
            payload = {"ok": False, "reason": f"http_{resp.status_code}"}
    except requests.exceptions.Timeout:
        payload = {"ok": False, "reason": "timeout"}
    except Exception as exc:                                  # noqa: BLE001
        payload = {"ok": False, "reason": f"error:{type(exc).__name__}"}

    if payload.get("ok") or payload.get("reason") == "not_found":
        with _IFSC_LOCK:
            _IFSC_CACHE[key] = {"at": time.time(), "data": payload}
    return payload


def layer1_bank_authority(entities: Dict[str, Any], text: str) -> Dict[str, Any]:
    score = 0
    flags: List[str] = []
    evidence: Dict[str, Any] = {"ifsc": [], "upi_authority": []}

    for ifsc in entities.get("ifsc_codes", []):
        bank_name = BANK_FROM_IFSC.get(ifsc[:4])
        live = _live_ifsc(ifsc)
        evidence["ifsc"].append({"ifsc": ifsc, "bank": bank_name or "", "live": live})

        if not bank_name and not live.get("ok"):
            score += 50
            flags.append(f"IFSC {ifsc} does not map to any known bank — likely fabricated.")
        elif not live.get("ok"):
            score += 35
            flags.append(f"IFSC {ifsc} looks structurally valid but could not be verified with {bank_name}.")
        else:
            score += 20
            declared = _match_declared_bank(text)
            if declared and declared.lower() not in (bank_name or "").lower():
                score += 30
                flags.append(
                    f"Message claims {declared} but IFSC {ifsc} actually belongs to "
                    f"{bank_name} ({live.get('branch', 'branch unlisted')})."
                )
            elif not declared:
                flags.append(
                    f"IFSC {ifsc} resolves to {bank_name}, {live.get('branch', '')} "
                    f"({live.get('city', '')}) — confirm with the bank before paying."
                )

    # Does the sender claim an institution but collect on a consumer handle?
    from backend.services.extractor import detect_authority_on_personal_handle
    auth = detect_authority_on_personal_handle(entities.get("upis", []), text)
    evidence["upi_authority"] = auth
    if auth.get("contradiction"):
        score += 45
        flags.append(
            "Authority impersonation: sender claims "
            + ", ".join(auth["claimed"])
            + " but money is being collected on a personal UPI handle ("
            + ", ".join(auth["collecting_on"]) + ")."
        )
    elif entities.get("upis"):
        flags.append("UPI handle captured — verify ownership in the UPI app before paying.")

    if entities.get("ifsc_codes") and not flags:
        flags.append("IFSC code present; bank identity not independently confirmed.")

    return {"layer": 1, "name": "Live Bank & Authority Verification",
            "score": min(100, score), "flags": flags, "evidence": evidence}


def _match_declared_bank(text: str) -> Optional[str]:
    low = (text or "").lower()
    aliases = {
        "State Bank of India": ["sbi", "state bank"],
        "HDFC Bank": ["hdfc"], "ICICI Bank": ["icici"], "Axis Bank": ["axis"],
        "Punjab National Bank": ["pnb", "punjab national"],
        "Bank of Baroda": ["bank of baroda", "bob"],
    }
    for name, kws in aliases.items():
        for kw in kws:
            if re.search(rf"\b{re.escape(kw)}\b", low):
                return name
    return None


# ==============================================================================
# Layer 2 — Digital Footprint Correlation
# ==============================================================================
def layer2_digital_footprint(entities: Dict[str, Any], text: str) -> Dict[str, Any]:
    score = 0
    flags: List[str] = []
    evidence: Dict[str, Any] = {"upis": [], "cross_links": []}

    upis = entities.get("upis", [])
    phones = entities.get("phones", [])
    accounts = entities.get("bank_accounts", [])

    for vpa in upis:
        prefix, _, suffix = vpa.lower().partition("@")
        is_consumer = suffix in CONSUMER_UPI_SUFFIXES
        looks_personal = bool(re.search(r"(?:\.|_|pay|upi|kol|desk|board)", prefix))

        if is_consumer and looks_personal:
            score += 30
            flags.append(
                f"Consumer UPI handle {vpa} is styled to look institutional — "
                "personal handles cannot be official organisation collection accounts."
            )
        evidence["upis"].append({"vpa": vpa, "consumer_psp": is_consumer})

        # Cross-link: does this same handle already live in our registry?
        rec = lookup_identifier(vpa)
        if rec:
            score += 40
            flags.append(
                f"{vpa} is already reported to ScamTrap Bharat "
                f"({rec.get('reports_count', 0)} reports, category: {rec.get('scam_category', '—')})."
            )
            evidence["cross_links"].append({"value": vpa, "type": "UPI", "record": dict(rec)})

    # New identifiers that crossed the confidence bar get contributed back.
    for phone in phones:
        rec = lookup_identifier(phone)
        if rec:
            score += 35
            flags.append(f"Phone {phone} matches a reported scam number ({rec.get('scam_category', '—')}).")
            evidence["cross_links"].append({"value": phone, "type": "PHONE", "record": dict(rec)})

    for acct in accounts:
        rec = lookup_identifier(acct)
        if rec:
            score += 35
            flags.append(f"Bank account {acct} matches a reported mule account ({rec.get('scam_category', '—')}).")
            evidence["cross_links"].append({"value": acct, "type": "BANK_AC", "record": dict(rec)})

    # Money-flow spread: many accounts offered in one thread is a classic mule fan-out.
    if len(accounts) >= 2:
        score += 25
        flags.append(f"{len(accounts)} different bank accounts were offered — money-mule fan-out pattern.")

    if entities.get("qr_payloads"):
        score += 30
        flags.append(
            "A UPI QR was attached. A UPI QR can ONLY take money out of the "
            "scanning app — it can never receive a payment."
        )

    if not flags:
        flags.append("No established links found in the local footprint registry.")

    return {"layer": 2, "name": "Digital Footprint Correlation",
            "score": min(100, score), "flags": flags, "evidence": evidence}


# ==============================================================================
# Layer 3 — Network Signal Analysis
# ==============================================================================
def layer3_network_signals(entities: Dict[str, Any], text: str,
                           upstream: str = "") -> Dict[str, Any]:
    score = 0
    flags: List[str] = []
    phones = entities.get("phones", [])
    has_header = bool(ENTERPRISE_HEADER.search(text or ""))

    micro = entities.get("micro_pattern", {})

    if micro.get("fake_bank_credit_from_personal_sim"):
        score += 45
        flags.append(
            "A bank credit confirmation arrived from an ordinary personal mobile "
            "number — real banks never send account alerts from a personal SIM."
        )
    elif micro.get("first_contact_bait"):
        score += 30
        flags.append(
            "No link and no UPI were shared — only an urgent number to call. "
            "That is the first-contact bait technique."
        )

    if phones and not has_header:
        score += 25
        flags.append(
            "The number reached you from a normal personal mobile connection "
            "instead of a verified business sender header."
        )

    if has_header:
        flags.append(f"Sender header {ENTERPRISE_HEADER.search(text).group(0)} present — verify it on the bank's official site.")

    # 140 / 1800-series are the Indian spam/reporting ranges.
    if TRAI_SPAM_SERIES.search(text or ""):
        score += 15
        flags.append("Contains a 140-series / toll-free number commonly abused for spam calls.")

    # Foreign dial-in + VoIP is a standard refund-scam signature.
    if VOLP_FOREIGN_CC.search(text or ""):
        score += 35
        flags.append("A foreign country-code number was shared — typical of overseas refund scams.")

    # Display-name spoofing: the caller name looks like an institution.
    spoofed_name = _spoofed_display_name(text or "")
    if spoofed_name:
        score += 35
        flags.append(f"The caller ID display name is set to '{spoofed_name}' — caller names are freely spoofable.")
    evidence = {"phones": phones, "trai_header": has_header, "spoofed_name": spoofed_name,
                "upstream": upstream}

    if not flags:
        flags.append("Sender appears to be an ordinary mobile connection with no known spam markers.")

    return {"layer": 3, "name": "Network Signal Analysis",
            "score": min(100, score), "flags": flags, "evidence": evidence}


def _spoofed_display_name(text: str) -> Optional[str]:
    m = re.search(r"(?:caller(?:\s*id)?|display(?:\s*name)?|name)\s*[:\-]\s*([A-Za-z ]{3,30})", text, re.I)
    if not m:
        return None
    name = m.group(1).strip()
    low = name.lower()
    return name if any(b in low for b in ("bank", "sbi", "hdfc", "icici", "axis", "police",
                                          "customs", "govt", "electricity", "rbi", "cbi")) else None


# ==============================================================================
# Layer 4 — URL / Domain & Payload Reputation
# ==============================================================================
def layer4_domain_payload(entities: Dict[str, Any], text: str) -> Dict[str, Any]:
    score = 0
    flags: List[str] = []
    evidence: Dict[str, Any] = {"urls": [], "malware": entities.get("malware_or_remote_apps", {})}

    for raw_url in entities.get("urls", []):
        host = _host_of(raw_url)
        evidence["urls"].append(raw_url)
        if not host:
            continue
        if host in SHORTENER_DOMAINS or host.split(".")[-2] in SHORTENER_DOMAINS:
            score += 35
            flags.append(f"{host} is a link shortener — the real destination is hidden.")
            continue
        if any(b in host for b in AUTHORITY_BRANDS) and not host.startswith(("https://www.", "https://")):
            pass
        if _typosquat(host):
            score += 45
            flags.append(f"{host} is a misspelling of an official domain — classic typosquat.")
        elif re.match(r"^https?://[\d]{1,3}(\.[\d]{1,3}){3}", raw_url):
            score += 45
            flags.append(f"{host} is a raw IP address rather than a real bank or government domain.")
        elif not host.endswith((".gov.in", ".nic.in", ".co.in", ".com", ".org", ".in")):
            score += 25
            flags.append(f"{host} is an unusual top-level domain — verify before opening.")
        else:
            flags.append(f"Link to {host} — open it only in a browser after checking the spelling.")

    malware = entities.get("malware_or_remote_apps", {}) or {}
    apps = malware.get("remote_access_apps", [])
    apks = malware.get("apk_files", [])
    if apps:
        score += 50
        flags.append(
            "Remote-control software mentioned (" + ", ".join(apps) + ") — these tools "
            "hand over full control of your phone or laptop to the caller."
        )
    if apks:
        score += 45
        flags.append(
            "An installable APK was offered (" + ", ".join(apks) + ") — never install "
            "apps from chat links; they carry banking trojans."
        )

    if not flags:
        flags.append("No links, shorteners or remote-control payloads detected.")

    return {"layer": 4, "name": "URL, Domain & Payload Reputation",
            "score": min(100, score), "flags": flags, "evidence": evidence}


def _host_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return (urlparse(url).netloc or "").lower().lstrip("www.")
    except Exception:
        return ""


def _typosquat(host: str) -> bool:
    """Fuzzy match against official authority domains (edit-distance ≤ 2)."""
    import difflib
    core = host.split(":")[0]
    if "." not in core:
        return False
    registered = ".".join(core.split(".")[-2:])
    for brand in AUTHORITY_BRANDS:
        official = f"{brand}.co.in"
        if registered != official and difflib.SequenceMatcher(None, registered, official).ratio() >= 0.85:
            return True
        if registered.startswith(brand) and registered != official and len(registered) > len(brand) + 3:
            return True
    return False


# ==============================================================================
# Layer 5 — Local Crowd-Sourced Intelligence (+ auto-upsert ≥ 70)
# ==============================================================================
def layer5_local_intel(entities: Dict[str, Any], base_score: int,
                       category: str) -> Dict[str, Any]:
    score = 0
    flags: List[str] = []
    evidence: Dict[str, Any] = {"hits": [], "upserted": []}

    pairs = (
        [("UPI", u) for u in entities.get("upis", [])]
        + [("PHONE", p) for p in entities.get("phones", [])]
        + [("BANK_AC", b) for b in entities.get("bank_accounts", [])]
        + [("IFSC", f) for f in entities.get("ifsc_codes", [])]
    )

    for kind, value in pairs:
        rec = lookup_identifier(value)
        if rec:
            score += 40
            evidence["hits"].append({"type": kind, "value": value, **dict(rec)})
            flags.append(
                f"{kind} {value} already reported {rec.get('reports_count', 0)} time(s), "
                f"category {rec.get('scam_category', '—')}, risk {rec.get('risk_score', 0)}."
            )

    # ── Contribution: anything that cleared the confidence bar is written back ──
    contributed = max(base_score, score)
    if contributed >= UPSCORE_THRESHOLD:
        for kind, value in pairs:
            if lookup_identifier(value):
                continue
            if upsert_identifier(value, kind, "Reported via investigation",
                                 category or "General Suspicious", contributed):
                evidence["upserted"].append(value)
        if evidence["upserted"]:
            flags.append(
                "Contribution: " + str(len(evidence["upserted"])) +
                " new identifier(s) reported to the ScamTrap Bharat community blacklist."
            )

    if not flags:
        flags.append("No matches in the community blacklist yet — this input was still analysed.")

    try:
        with get_db_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM scam_identifiers").fetchone()[0]
        evidence["registry_size"] = total
        flags.append(f"Community blacklist currently holds {total} verified identifiers.")
    except Exception:
        pass

    return {"layer": 5, "name": "Local Crowd-Sourced Intelligence",
            "score": min(100, score), "flags": flags, "evidence": evidence}


# ==============================================================================
# Public entry point
# ==============================================================================
def run_osint(entities: Dict[str, Any], text: str, base_score: int,
              category: str, upstream: str = "") -> List[Dict[str, Any]]:
    """Runs all five layers in order and returns their results."""
    return [
        layer1_bank_authority(entities, text),
        layer2_digital_footprint(entities, text),
        layer3_network_signals(entities, text, upstream),
        layer4_domain_payload(entities, text),
        layer5_local_intel(entities, base_score, category),
    ]
