from fastapi import APIRouter, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.services.reply_ai import build_copilot_system, generate_reply
from backend.services.image_bait import generate_upi_limit_receipt
from backend.database.db import get_db_connection
from backend.config import GENERATED_BAITS_DIR
import uuid

router = APIRouter(prefix="/api/co-pilot", tags=["Citizen Co-Pilot"])

class GenerateBaitRequest(BaseModel):
    scammer_upi: Optional[str] = "bijli.board.pay@ybl"
    amount: Optional[str] = "25,000"
    sender_name: Optional[str] = "Rahul Sharma"
    case_id: Optional[str] = "CASE-2026-1001"

@router.get("/fake-receipt")
def get_fake_receipt(
    upi: str = Query(default="bijli.board.pay@ybl"),
    amount: str = Query(default="25,000"),
    sender_name: str = Query(default="Rahul Sharma"),
    case_id: str = Query(default="CASE-2026-1001")
):
    """Generates and directly returns the PNG image for the fake Payment Failed receipt."""
    result = generate_upi_limit_receipt(scammer_upi=upi, amount=amount, sender_name=sender_name)
    return FileResponse(result["filepath"], media_type="image/png", filename=result["filename"])

@router.post("/generate-receipt-bait")
@router.post("/generate-bait")          # spec §7 alias — same handler
def create_receipt_bait(req: GenerateBaitRequest):
    """Generates a realistic UPI Daily Limit Reached screenshot and ready-to-copy Hinglish text."""
    result = generate_upi_limit_receipt(
        scammer_upi=req.scammer_upi or "bijli.board.pay@ybl",
        amount=req.amount or "25,000",
        sender_name=(req.sender_name or "").strip() or "Rahul Sharma",
    )
    
    trap_code = f"TRAP-{uuid.uuid4().hex[:6].upper()}"
    trap_url = f"/receipt/{trap_code}?case={req.case_id}"
    
    return {
        "status": "success",
        "bait_image": result,
        "trap_code": trap_code,
        "trap_url": trap_url,
        "recommended_text_english": f"Sir, I tried sending ₹{req.amount or '25,000'} via UPI but my bank says 'NPCI Error: U16 Daily Inward Limit Reached' for your UPI ID ({req.scammer_upi or 'bijli.board.pay@ybl'}). Screenshot attached. Please immediately send your backup Bank Account Number + IFSC code or secondary UPI so I can complete payment without delay.",
        "recommended_text_hindi": f"सर, मैंने ₹{req.amount or '25,000'} UPI से भेजने की कोशिश की लेकिन आपके UPI ID ({req.scammer_upi or 'bijli.board.pay@ybl'}) पर 'Daily Limit Exceeded (U16)' का एरर आ गया। स्क्रीनशॉट संलग्न है। कृपया तुरंत अपना दूसरा बैकअप बैंक खाता नंबर और IFSC कोड भेजें ताकि मैं बिना रुकावट ट्रांसफर कर सकूं।"
    }

@router.post("/log-trap-visit")
async def log_trap_visit(request: Request):
    """Logs the scammer's browser User-Agent, IP, and OS when they inspect the receipt link."""
    data = await request.json()
    case_id = data.get("case_id", "CASE-2026-1001")
    trap_code = data.get("trap_code", "TRAP-AUTO")
    
    # Extract client IP
    client_ip = request.headers.get("x-forwarded-for")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"
        
    user_agent = request.headers.get("user-agent", "Mozilla/5.0 Android Device")
    
    # OS detection
    device_os = "Unknown Device"
    if "Android" in user_agent:
        device_os = "Android Smartphone (Redmi / Vivo)"
    elif "iPhone" in user_agent or "iOS" in user_agent:
        device_os = "Apple iPhone (iOS)"
    elif "Windows" in user_agent:
        device_os = "Windows PC"
    elif "Mac" in user_agent:
        device_os = "Macintosh OS"
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


class NextReplyRequest(BaseModel):
    """Tab 2 · Co-Pilot Mode - draft the citizen's next safe WhatsApp reply."""
    scam_category: Optional[str] = "General Suspicious"
    chat_history: Optional[List[Dict[str, str]]] = None
    scammer_new_message: str
    scammer_upi: Optional[str] = None
    case_context: Optional[Dict[str, Any]] = None


@router.post("/next-reply")
def next_reply(req: NextReplyRequest):
    text = (req.scammer_new_message or "").strip()
    if not text:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="scammer_new_message is required")

    system = build_copilot_system(req.scam_category or "General Suspicious", req.case_context)
    result = generate_reply(system, chat_history=req.chat_history, user_message=text)
    return {
        "status": "success",
        "suggested_reply": result["reply"],
        "send_image": result["send_image"],
        "provider": result["provider"],
        "elapsed_ms": result["elapsed_ms"],
    }
