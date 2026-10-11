from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from backend.database.db import get_scam_summary, get_db_connection, get_case_evidence
from backend.services.pdf_dossier import generate_complaint_dossier
from backend.services.kill_chain import classify_transcript
from backend.config import GENERATED_PDFS_DIR
from pathlib import Path

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])

class GeneratePdfRequest(BaseModel):
    case_id: Optional[str] = "CASE-2026-1001"

PENDING_CAPTURE = "Awaiting canary capture"

def _build_case_payload(case_id: str) -> dict:
    """Builds the dossier payload straight from the recorded evidence bundle.
    `pdf_dossier` renders whatever is present; anything missing prints as
    "Not recorded" instead of being invented."""
    ev = get_case_evidence(case_id)
    if ev.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=f"No case found with id {case_id}")
    # `messages` stay as dicts so the dossier can show verbatim role+text.
    return {
        "case_id": case_id,
        "scammer_phone": ev.get("scammer_phone"),
        "scam_category": ev.get("scam_category"),
        "created_at": ev.get("created_at"),
        "source_table": ev.get("source_table"),
        "messages": ev.get("messages") or [],
        "identifiers": ev.get("identifiers") or [],
        "canary_captures": ev.get("canary_captures") or [],
        "latest_capture": ev.get("latest_capture"),
        "evidence_hash": ev.get("evidence_hash"),
    }

@router.get("/case-evidence")
def get_case_evidence_report(case_id: str = Query(default="CASE-2026-1001")):
    """Returns the real, recorded evidence bundle for a case: transcript,
    kill-chain classification, extracted identifiers cross-checked against
    the blacklist, and any canary captures logged when the trap link was
    opened. Works for both `cases` and `cloud_sessions` case ids."""
    ev = get_case_evidence(case_id)
    if ev.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=f"No case found with id {case_id}")
    # Deterministic kill-chain classification of the real transcript.
    ev["kill_chain"] = classify_transcript(ev.get("messages") or [])
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
    # Containment check: resolve and make sure we stayed inside the PDF dir.
    filepath = (GENERATED_PDFS_DIR / filename).resolve()
    try:
        filepath.relative_to(GENERATED_PDFS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if filepath.suffix.lower() != ".pdf" or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)
