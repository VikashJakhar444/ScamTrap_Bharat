"""
ScamTrap Bharat — Case Logger  (spec §6)
=========================================
Writes the forensic record of every Tab 1 investigation:

    storage/investigation_logs/INV-YYYYMMDD-HHMMSS-XXXX.log
    storage/investigation_logs/INV-YYYYMMDD-HHMMSS-XXXX.json

Format  : INV-YYYYMMDD-HHMMSS-<4 hex>   (e.g. INV-20261006-142530-A7F3)
Sections: exactly five, in order
    1. INPUT           raw input, de-obfuscated text, input type, SHA-256
    2. OSINT LAYERS    all five layer evidences (internal, un-sanitised)
    3. COGNITIVE AI    the four principle weights + scores + findings
    4. VERDICT         threat level, category, citizen summary and action
    5. AUDIT           client IP, probe/injection/rate-limit flags, model,
                       integrity hash

Timestamps are IST (UTC+05:30). The integrity hash is a FULL 64-character
SHA-256 over sections 1-4. Nothing here is ever returned to the API caller.
"""

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import BASE_DIR
from backend.database.db import record_investigation_audit

INVESTIGATION_LOG_DIR = BASE_DIR / "storage" / "investigation_logs"
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

INPUT_TYPES = ("TEXT", "IMAGE_OCR", "VOICE_AUDIO", "QR_CODE", "IDENTIFIER_LOOKUP")


# ── Identity ──────────────────────────────────────────────────────────────────
def new_investigation_id(when: Optional[datetime] = None) -> str:
    """INV-YYYYMMDD-HHMMSS-<4 hex>, clock taken in IST."""
    now = (when or datetime.now(IST))
    return f"INV-{now:%Y%m%d}-{now:%H%M%S}-{secrets.token_hex(2).upper()}"


def _ensure_dir() -> Path:
    INVESTIGATION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return INVESTIGATION_LOG_DIR


def _sha256_of(payload: str) -> str:
    """FULL 64-character SHA-256 — never truncated."""
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()


# ── Section builders ──────────────────────────────────────────────────────────
def section_input(record: Dict[str, Any]) -> Dict[str, Any]:
    raw = record.get("raw_input") or ""
    return {
        "investigation_id": record.get("investigation_id"),
        "case_id": record.get("case_id"),
        "input_type": record.get("input_type", "TEXT"),
        "input_sha256": _sha256_of(raw),
        "input_bytes": len(raw.encode("utf-8", errors="replace")),
        "raw_input": raw,
        "deobfuscated_text": record.get("deobfuscated_text", ""),
        "deobfuscation_changes": record.get("deobfuscation_changes", []),
        "transcription": record.get("transcription"),
        "ocr_text": record.get("ocr_text"),
        "qr_payloads": record.get("qr_payloads", []),
        "client_ip": record.get("client_ip"),
        "captured_at_ist": record.get("timestamp_ist"),
    }


def section_osint_layers(layers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "layer_count": len(layers or []),
        "layers": [
            {
                "layer": l.get("layer"),
                "name": l.get("name"),
                "score": l.get("score"),
                "flags": l.get("flags", []),
                "evidence": l.get("evidence", {}),      # forensic-only detail
            }
            for l in (layers or [])
        ],
    }


def section_cognitive_ai(det: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "model": det.get("model"),
        "ai_source": det.get("ai_source"),
        "principles": [
            {
                "key": p.get("key"),
                "name": p.get("name"),
                "weight": p.get("weight"),
                "score": p.get("score"),
                "evidence": p.get("evidence"),
                "findings": p.get("findings", []),
            }
            for p in (det.get("principles") or [])
        ],
        "weighted_score": det.get("weighted_score"),
        "prompt_injection_detected": det.get("prompt_injection_detected", False),
        "injection_matches": det.get("injection_matches", []),
    }


def section_verdict(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "threat_level": report.get("threat_level"),
        "final_score": report.get("final_score"),
        "scam_category": report.get("scam_category", report.get("primary_category")),
        "primary_category": report.get("primary_category"),
        "is_known_scam": report.get("is_known_scam"),
        "blacklist_hits": report.get("blacklist_hits", []),
        "verified_bank": report.get("verified_bank"),
        "citizen_summary": report.get("citizen_summary"),
        "citizen_action": report.get("citizen_action"),
        "counter_bait_available": report.get("counter_bait_available"),
    }


def section_audit(record: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "investigation_id": record.get("investigation_id"),
        "case_id": report.get("case_id"),
        "client_ip": record.get("client_ip"),
        "input_type": record.get("input_type", "TEXT"),
        "input_sha256": _sha256_of(record.get("raw_input") or ""),
        "is_scammer_probing": bool(record.get("is_scammer_probing")),
        "probe_recent_count": record.get("probe_recent_count", 0),
        "rate_limited": bool(record.get("rate_limited")),
        "prompt_injection_detected": bool(report.get("prompt_injection_detected")),
        "ai_source": report.get("ai_source"),
        "model": report.get("model"),
        "upload_validation": record.get("upload_validation", {}),
        "exec_disguise_detected": record.get("exec_disguise_detected", False),
        "upserted_identifiers": record.get("upserted_identifiers", []),
        "log_written_at_ist": record.get("timestamp_ist"),
    }


# ── Renderers ─────────────────────────────────────────────────────────────────
def _render_log(sections: Dict[str, Any]) -> str:
    def _block(obj: Any, indent: int = 0) -> str:
        pad = "  " * indent
        if isinstance(obj, dict):
            return "\n".join(
                f"{pad}{k}:\n{_block(v, indent + 1)}" if isinstance(v, (dict, list))
                else f"{pad}{k}: {v}"
                for k, v in obj.items()
            )
        if isinstance(obj, list):
            if not obj:
                return f"{pad}(none)"
            return "\n".join(
                f"{pad}- " + (_block(v, indent + 1).lstrip() if isinstance(v, (dict, list)) else str(v))
                for v in obj
            )
        return f"{pad}{obj}"

    titles = {
        "input": "SECTION 1 — INPUT (raw vs de-obfuscated)",
        "layers": "SECTION 2 — OSINT LAYERS (five independent probes)",
        "ai": "SECTION 3 — COGNITIVE AI DETECTIVE (four principles)",
        "verdict": "SECTION 4 — VERDICT & CITIZEN GUIDANCE",
        "audit": "SECTION 5 — AUDIT & INTEGRITY",
    }
    out = ["=" * 78, "SCAMTRAP BHARAT — INVESTIGATION RECORD", "=" * 78]
    for key in ("input", "layers", "ai", "verdict", "audit"):
        out += ["", "-" * 78, titles[key], "-" * 78, _block(sections.get(key) or {}), ""]
    return "\n".join(out)


def write_investigation(record: Dict[str, Any],
                        report: Dict[str, Any],
                        det: Dict[str, Any],
                        layers: List[Dict[str, Any]]) -> Dict[str, str]:
    """Writes both `.log` and `.json`, records the audit row, returns their paths."""
    directory = _ensure_dir()
    inv_id = record.get("investigation_id") or new_investigation_id()

    sections = {
        "input": section_input({**record, "investigation_id": inv_id}),
        "layers": section_osint_layers(layers),
        "ai": section_cognitive_ai(det),
        "verdict": section_verdict(report),
        "audit": section_audit({**record, "investigation_id": inv_id}, report),
    }

    # Integrity over sections 1-4 only (section 5 carries the hash itself).
    integrity = _sha256_of(json.dumps(
        {k: sections[k] for k in ("input", "layers", "ai", "verdict")},
        ensure_ascii=False, sort_keys=True, default=str,
    ))
    sections["audit"]["integrity_sha256"] = integrity
    sections["audit"]["log_path"] = str((directory / f"{inv_id}.log"))
    sections["audit"]["json_path"] = str((directory / f"{inv_id}.json"))

    log_path = directory / f"{inv_id}.log"
    json_path = directory / f"{inv_id}.json"

    log_path.write_text(_render_log(sections), encoding="utf-8")
    json_path.write_text(
        json.dumps(sections, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    record_investigation_audit({
        "investigation_id": inv_id,
        "case_id": report.get("case_id"),
        "input_type": record.get("input_type", "TEXT"),
        "input_sha256": sections["input"]["input_sha256"],
        "client_ip": record.get("client_ip"),
        "prompt_injection_detected": sections["audit"]["prompt_injection_detected"],
        "is_scammer_probing": sections["audit"]["is_scammer_probing"],
        "rate_limited": sections["audit"]["rate_limited"],
        "risk_score": report.get("final_score"),
        "threat_level": report.get("threat_level"),
        "scam_category": report.get("primary_category"),
        "upserted_count": len(record.get("upserted_identifiers") or []),
        "model_source": det.get("ai_source"),
        "log_path": str(log_path),
        "json_path": str(json_path),
    })

    return {"investigation_id": inv_id, "log_path": str(log_path),
            "json_path": str(json_path), "integrity_sha256": integrity}


def read_investigation(investigation_id: str) -> Optional[Dict[str, Any]]:
    """Loads a stored .json record (used by GET /api/checker/investigation/{id})."""
    safe = os.path.basename(investigation_id or "").replace(".json", "").replace(".log", "")
    if not safe:
        return None
    path = _ensure_dir() / f"{safe}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return None


def list_investigations(limit: int = 50) -> List[Dict[str, Any]]:
    """Newest-first index of stored investigations."""
    try:
        files = sorted(_ensure_dir().glob("INV-*.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    except Exception:                                        # noqa: BLE001
        return []
    index: List[Dict[str, Any]] = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            audit = data.get("audit", {})
            index.append({
                "investigation_id": audit.get("investigation_id") or path.stem,
                "case_id": audit.get("case_id"),
                "input_type": audit.get("input_type"),
                "threat_level": data.get("verdict", {}).get("threat_level"),
                "final_score": data.get("verdict", {}).get("final_score"),
                "is_scammer_probing": audit.get("is_scammer_probing"),
                "prompt_injection_detected": audit.get("prompt_injection_detected"),
                "ai_source": audit.get("ai_source"),
                "written_at": audit.get("log_written_at_ist"),
            })
        except Exception:                                    # noqa: BLE001
            continue
    return index
