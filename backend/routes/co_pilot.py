from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.services.image_bait import generate_upi_limit_receipt
from backend.database.db import get_db_connection
from backend.config import GENERATED_BAITS_DIR
import uuid

router = APIRouter(prefix="/api/co-pilot", tags=["Citizen Co-Pilot"])

class GenerateBaitRequest(BaseModel):
    scammer_upi: Optional[str] = "bijli.board.pay@ybl"
    amount: Optional[str] = "450.00"
    case_id: Optional[str] = "CASE-2026-1001"

@router.post("/generate-receipt-bait")
def create_receipt_bait(req: GenerateBaitRequest):
    """Generates a realistic UPI Daily Limit Reached screenshot to prompt the scammer for backup accounts."""
    result = generate_upi_limit_receipt(scammer_upi=req.scammer_upi or "bijli.board.pay@ybl", amount=req.amount or "450.00")
    
    # Generate a verification trap code
    trap_code = f"TRAP-{uuid.uuid4().hex[:6].upper()}"
    trap_url = f"/verify_receipt.html?code={trap_code}&case={req.case_id}"
    
    return {
        "status": "success",
        "bait_image": result,
        "trap_code": trap_code,
        "trap_url": trap_url,
        "recommended_text_english": f"Sir, I tried sending Rs {req.amount or '450'} via UPI but my bank returned a 'Daily Limit Exceeded' error. Here is the transaction receipt screenshot. Please send your secondary Bank Account Number, IFSC, or alternative UPI ID immediately so I can transfer without delay.",
        "recommended_text_hindi": f"सर, मैंने UPI से Rs {req.amount or '450'} भेजने की कोशिश की लेकिन 'Daily Limit Exceeded' आ गया। ये रहा रसीद का स्क्रीनशॉट। कृपया अपना दूसरा बैंक खाता नंबर और IFSC या दूसरा UPI ID भेजें ताकि मैं तुरंत ट्रांसफर कर सकूं।"
    }

@router.post("/log-trap-visit")
async def log_trap_visit(request: Request):
    """Logs the scammer's browser User-Agent, IP, and OS when they inspect the receipt link."""
    data = await request.json()
    case_id = data.get("case_id", "CASE-2026-1001")
    trap_code = data.get("trap_code", "TRAP-AUTO")
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown Device")
    
    # Simple OS detection
    device_os = "Unknown Mobile/Desktop"
    if "Android" in user_agent:
        device_os = "Android Smartphone"
    elif "iPhone" in user_agent or "iOS" in user_agent:
        device_os = "Apple iPhone (iOS)"
    elif "Windows" in user_agent:
        device_os = "Windows PC"
    elif "Mac" in user_agent:
        device_os = "Mac OS"
    elif "Linux" in user_agent:
        device_os = "Linux System"
        
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO canary_logs (case_id, trap_code, ip_address, device_os, browser_ua)
            VALUES (?, ?, ?, ?, ?)
            """,
            (case_id, trap_code, client_ip, device_os, user_agent)
        )
        conn.commit()
        
    return {
        "status": "logged",
        "captured": {
            "ip": client_ip,
            "os": device_os,
            "user_agent": user_agent
        }
    }
