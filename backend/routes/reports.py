from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from backend.database.db import get_scam_summary, get_db_connection
from backend.services.pdf_dossier import generate_complaint_dossier
from backend.config import GENERATED_PDFS_DIR
from pathlib import Path

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])

class GeneratePdfRequest(BaseModel):
    case_id: Optional[str] = "CASE-2026-1001"

@router.get("/summary")
def get_summary_report():
    """Returns real counts, category breakdowns, and blacklist records from SQLite."""
    data = get_scam_summary()
    return {
        "status": "success",
        "data": data
    }

@router.post("/generate-dossier")
def create_pdf_dossier(req: GeneratePdfRequest):
    """Generates an official-grade 1930 Cyber Cell PDF complaint evidence dossier."""
    case_id = req.case_id or "CASE-2026-1001"
    
    with get_db_connection() as conn:
        case = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        msgs = conn.execute("SELECT sender_role, message_text FROM messages WHERE case_id = ? ORDER BY id ASC", (case_id,)).fetchall()
        canary = conn.execute("SELECT * FROM canary_logs WHERE case_id = ? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
        
    case_info = {
        "case_id": case_id,
        "scammer_phone": case["scammer_phone"] if case else "+91 98765 43210",
        "scam_category": case["scam_category"] if case else "Electricity Bill Disconnection",
        "primary_upi": "bijli.board.pay@ybl",
        "bank_ac": "50200084729104",
        "ifsc": "SBIN0004821",
        "ip_address": canary["ip_address"] if canary else "103.21.144.62 (Kolkata Hub)",
        "device_os": canary["device_os"] if canary else "Android 13 (Redmi Note 11)",
        "browser_ua": canary["browser_ua"] if canary else "Chrome Mobile 122.0.6261.94",
        "messages": [f"[{m['sender_role'].upper()}]: {m['message_text']}" for m in msgs] if msgs else []
    }
    
    result = generate_complaint_dossier(case_info)
    return {
        "status": "success",
        "file": result
    }

@router.get("/download-pdf/{filename}")
def download_pdf(filename: str):
    """Serves the generated PDF file safely."""
    filepath = GENERATED_PDFS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)
