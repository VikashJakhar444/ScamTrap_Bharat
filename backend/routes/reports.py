from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from backend.database.db import get_scam_summary, get_db_connection, get_case_evidence
from backend.services.pdf_dossier import generate_complaint_dossier
from backend.config import GENERATED_PDFS_DIR
from pathlib import Path

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])

class GeneratePdfRequest(BaseModel):
    case_id: Optional[str] = "CASE-2026-1001"

PENDING_CAPTURE = "Awaiting canary capture"

def _build_case_payload(case_id: str) -> dict:
    """Builds the dossier payload from recorded evidence only. Values that have
    not actually been captured are reported as pending instead of invented."""
    ev = get_case_evidence(case_id)
    latest = ev.get("latest_capture") or {}

    def _pick(kind: str) -> Optional[str]:
        for ident in ev["identifiers"]:
            if ident["type"] == kind and ident["blacklisted"] is False:
                return ident["value"]
        for ident in ev["identifiers"]:
            if ident["type"] == kind:
                return ident["value"]
        return None

    return {
        "case_id": case_id,
        "scammer_phone": ev.get("scammer_phone") or "Not recorded",
        "scam_category": ev.get("scam_category") or "Unclassified",
        "primary_upi": _pick("UPI") or "Not captured",
        "bank_ac": _pick("BANK_AC") or "Not captured",
        "ifsc": _pick("IFSC") or "Not captured",
        "ip_address": latest.get("ip_address") or PENDING_CAPTURE,
        "device_os": latest.get("device_os") or PENDING_CAPTURE,
        "browser_ua": latest.get("browser_ua") or PENDING_CAPTURE,
        "messages": [f"[{m['sender_role'].upper()}]: {m['message_text']}" for m in ev["messages"]],
    }

@router.get("/case-evidence")
def get_case_evidence_report(case_id: str = Query(default="CASE-2026-1001")):
    """Returns the real, recorded evidence bundle for a case: transcript,
    extracted identifiers cross-checked against the blacklist, and any
    canary captures logged when the trap link was opened."""
    ev = get_case_evidence(case_id)
    if ev.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=f"No case found with id {case_id}")
    return {"status": "success", "data": ev}


@router.get("/summary")
def get_summary_report():
    """Returns real counts, category breakdowns, and blacklist records from SQLite."""
    return {"status": "success", "data": get_scam_summary()}


@router.get("/download-pdf")
def download_official_pdf(case_id: str = Query(default="CASE-2026-1001")):
    """Generates and serves the 1930 Cyber Cell & BSA Sec 63 complaint PDF directly."""
    case_info = _build_case_payload(case_id)
    result = generate_complaint_dossier(case_info)
    return FileResponse(result["filepath"], media_type="application/pdf", filename=result["filename"])

@router.post("/generate-dossier")
def create_pdf_dossier(req: GeneratePdfRequest):
    """Generates an official-grade 1930 Cyber Cell PDF complaint evidence dossier."""
    case_id = req.case_id or "CASE-2026-1001"
    case_info = _build_case_payload(case_id)
    result = generate_complaint_dossier(case_info)
    return {
        "status": "success",
        "file": result
    }

@router.get("/download/{filename}")
def download_pdf_by_name(filename: str):
    """Serves the generated PDF file safely."""
    filepath = GENERATED_PDFS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)
