"""
ScamTrap Bharat — Investigation Orchestrator  (spec §1 + §3 + §4 + §6)
=======================================================================
Wires the whole Tab 1 engine together, in the spec's fixed order:

    de-obfuscate → extract entities → 5 OSINT layers → 4-principle
    Cognitive AI Detective → +25 injection penalty → verdict → log

Back-compat surface (do NOT rename without grepping `checker.py`):
    run_full_investigation(...)
    FORENSIC_LOG_DIR  ->  now storage/investigation_logs (spec §6)
"""

import datetime
from statistics import mean
from typing import Any, Dict, List, Optional

from backend.config import GEMINI_API_KEY, BASE_DIR
from backend.services.extractor import extract_entities, localize_category, SCAM_KEYWORDS
from backend.services import security_guard as guard
from backend.services.osint_engine import run_osint
from backend.services.llm_engine import cognitive_detective, MODEL
from backend.services.case_logger import (
    INVESTIGATION_LOG_DIR,
    new_investigation_id,
    write_investigation,
    read_investigation,
    list_investigations,
)

# Legacy alias — kept so `from backend.services.analyzer import FORENSIC_LOG_DIR`
# keeps resolving to the spec-compliant directory.
FORENSIC_LOG_DIR = INVESTIGATION_LOG_DIR
INVESTIGATION_DIR = INVESTIGATION_LOG_DIR

# Blend of the two engines. The Cognitive AI Detective carries more weight
# because it is the only one that reads meaning, not tokens.
_DETECTIVE_WEIGHT = 0.6
_OSINT_WEIGHT = 0.4

_INPUT_FLAGS_TEXT = {
    "prompt_injection_detected": "Some instruction-override text in the input was ignored.",
    "is_scammer_probing": "This looks like an automated probe — the result is not a real customer warning.",
    "rate_limited": "Too many checks in a short time; results may be rate limited.",
    "exec_disguise_detected": "The uploaded file was not a genuine image/audio and was rejected.",
}


def _threat_for(score: int, known: bool) -> str:
    if known or score >= 70:
        return "HIGH_DANGER"
    if score >= 40:
        return "MODERATE"
    return "LOW"


def run_full_investigation(raw_text: str,
                           case_id: Optional[str] = None,
                           lang: str = "en",
                           input_type: str = "TEXT",
                           client_ip: str = "unknown",
                           image_bytes: Optional[bytes] = None,
                           audio_bytes: Optional[bytes] = None,
                           transcription: Optional[str] = None,
                           ocr_text: Optional[str] = None,
                           upload_validation: Optional[Dict[str, Any]] = None,
                           exec_disguise_detected: bool = False) -> Dict[str, Any]:
    """Runs the full engine and returns the citizen-facing (sanitised) report."""
    lang = "hi" if lang == "hi" else "en"
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp_ist = now.astimezone(
        datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    ).isoformat()

    # ── Stage 0: security controls ──────────────────────────────────────────
    probe = guard.check_probe(client_ip, raw_text or "")
    injected = guard.scan_prompt_injection(raw_text or "")

    # ── Stage 1: de-obfuscation + entity extraction ─────────────────────────
    entities = extract_entities(raw_text or "")
    deob_text = entities.get("deobfuscated_text", raw_text or "")
    changes = []
    if deob_text != (raw_text or ""):
        changes.append("Reconstructed '@' / split phone digits from obfuscated text.")
    if ocr_text and not entities.get("upis"):
        entities = extract_entities(f"{deob_text}\n{ocr_text}")
    if transcription and not entities.get("upis"):
        entities = extract_entities(f"{deob_text}\n{transcription}")

    # ── Stage 2: OSINT — five independent layers ────────────────────────────
    layers: List[Dict[str, Any]] = run_osint(
        entities, deob_text,
        base_score=entities.get("heuristic_risk_score", 0),
        category=entities.get("detected_category", "General Suspicious"),
        upstream=client_ip,
    )
    layer_scores = [int(l.get("score", 0) or 0) for l in layers]
    osint_mean = int(round(mean(layer_scores))) if layer_scores else 0
    # A single layer that tripped hard must not be averaged away by the four
    # that stayed quiet — blend the mean with the peak.
    osint_signal = int(round(0.5 * osint_mean + 0.5 * max(layer_scores))) if layer_scores else 0

    # ── Stage 3: Cognitive AI Detective — four principles ───────────────────
    upis = entities.get("upis") or []
    det = cognitive_detective(
        deob_text, entities=entities,
        image_bytes=image_bytes, audio_bytes=audio_bytes,
        facts={
            "authority_on_personal_handle": next(
                (l["evidence"].get("upi_authority", {}) for l in layers
                 if l["layer"] == 1), {}),
            "confirmed_scam": bool(upis) and _known(upis),
        },
    )
    detective_score = int(det.get("weighted_score", 0))

    # ── Stage 4: verdict ────────────────────────────────────────────────────
    base = _DETECTIVE_WEIGHT * detective_score + _OSINT_WEIGHT * osint_signal
    final_score = int(round(max(0, min(100, base))))
    # Dominance rule: any layer that already tripped hard stays hard.
    if layer_scores and max(layer_scores) >= 70:
        final_score = max(final_score, 70)
    # A confirmed blacklist match is never downgraded by heuristic blending.
    blacklist_hits = _blacklist_hits(entities)
    is_known = bool(blacklist_hits)
    if is_known:
        final_score = max(final_score, 85)

    threat_level = _threat_for(final_score, is_known)

    category_en = det.get("category") or entities.get("detected_category") or "General Suspicious"
    if is_known and blacklist_hits:
        category_en = blacklist_hits[0].get("scam_category") or category_en
    if category_en == "General Suspicious" and not entities.get("matched_categories"):
        category_en = "No Direct Threat Found" if final_score < 40 else category_en

    investigation_id = case_id or new_investigation_id()
    verified_bank = next(
        (i.get("bank") or i.get("live", {}).get("bank")
         for l in layers if l["layer"] == 1
         for i in (l.get("evidence", {}).get("ifsc") or [])
         if i.get("bank") or i.get("live", {}).get("ok")),
        None,
    )

    report: Dict[str, Any] = {
        "case_id": investigation_id,
        "investigation_id": investigation_id,
        "input_type": input_type,
        "timestamp": now.isoformat(),
        "threat_level": threat_level,
        "threat_badge": threat_level,
        "final_score": final_score,
        "primary_category": localize_category(category_en, lang),
        "scam_category": category_en,
        "is_known_scam": is_known,
        "blacklist_hits": blacklist_hits,
        "extracted_entities": entities,
        "verified_bank": verified_bank,
        "citizen_summary": det.get("citizen_summary", ""),
        "citizen_action": det.get("citizen_action", ""),
        "counter_bait_available": is_known or final_score >= 45,
        "ai_source": det.get("ai_source"),
        "model": det.get("model"),
        "prompt_injection_detected": det.get("prompt_injection_detected", False),
        "principles": det.get("principles", []),
        "layers": layers,
        "input_flags": _input_flags(probe, det, exec_disguise_detected),
    }

    # ── Stage 5: forensic record (spec §6) ──────────────────────────────────
    written = write_investigation(
        record={
            "investigation_id": investigation_id,
            "case_id": investigation_id,
            "raw_input": raw_text or "",
            "deobfuscated_text": deob_text,
            "deobfuscation_changes": changes,
            "input_type": input_type,
            "client_ip": client_ip,
            "timestamp_ist": timestamp_ist,
            "is_scammer_probing": probe.get("is_scammer_probing", False),
            "probe_recent_count": probe.get("recent_count", 0),
            "rate_limited": probe.get("rate_limited", False),
            "transcription": transcription,
            "ocr_text": ocr_text,
            "qr_payloads": entities.get("qr_payloads", []),
            "upload_validation": upload_validation or {},
            "exec_disguise_detected": exec_disguise_detected,
            "upserted_identifiers": layers[-1].get("evidence", {}).get("upserted", [])
            if layers else [],
        },
        report=report,
        det=det,
        layers=layers,
    )

    report["forensic_log_available"] = True
    report["forensic_log_url"] = f"/api/checker/log/{investigation_id}"
    report["forensic_json_url"] = f"/api/checker/investigation/{investigation_id}"
    report["integrity_sha256"] = written.get("integrity_sha256")

    # ── Final OPSEC gate: the API never sees internal evidence/weights ─────
    safe = guard.public_report(report)
    safe["layers"] = guard.sanitize_layers(layers)
    safe["forensic_log_available"] = report["forensic_log_available"]
    safe["forensic_log_url"] = report["forensic_log_url"]
    safe["forensic_json_url"] = report["forensic_json_url"]
    safe["integrity_sha256"] = report["integrity_sha256"]
    safe["ai_source"] = report["ai_source"]
    safe["model"] = report.get("model")
    safe["citizen_summary"] = report["citizen_summary"]
    safe["action_guidance"] = report["citizen_action"]
    safe["threat_badge"] = report["threat_badge"]
    safe["scam_category"] = report["scam_category"]
    return safe


# ── Helpers ───────────────────────────────────────────────────────────────────
def _known(values: List[str]) -> bool:
    from backend.database.db import lookup_identifier
    return any(lookup_identifier(v) for v in values)


def _blacklist_hits(entities: Dict[str, Any]) -> List[Dict[str, Any]]:
    from backend.database.db import lookup_identifier
    hits: List[Dict[str, Any]] = []
    seen = set()
    for kind, values in (("UPI", entities.get("upis", [])),
                         ("PHONE", entities.get("phones", [])),
                         ("BANK_AC", entities.get("bank_accounts", [])),
                         ("IFSC", entities.get("ifsc_codes", []))):
        for value in values or []:
            if value in seen:
                continue
            seen.add(value)
            rec = lookup_identifier(value)
            if rec:
                hits.append({
                    "identifier_type": kind,
                    "identifier_value": value,
                    "scam_category": rec.get("scam_category"),
                    "risk_score": rec.get("risk_score"),
                    "reports_count": rec.get("reports_count"),
                })
    return hits


def _input_flags(probe: Dict[str, Any], det: Dict[str, Any],
                 exec_disguise: bool) -> List[str]:
    flags: List[str] = []
    if probe.get("is_scammer_probing"):
        flags.append(_INPUT_FLAGS_TEXT["is_scammer_probing"])
    if probe.get("rate_limited"):
        flags.append(_INPUT_FLAGS_TEXT["rate_limited"])
    if det.get("prompt_injection_detected"):
        flags.append(_INPUT_FLAGS_TEXT["prompt_injection_detected"])
    if exec_disguise:
        flags.append(_INPUT_FLAGS_TEXT["exec_disguise_detected"])
    return flags
