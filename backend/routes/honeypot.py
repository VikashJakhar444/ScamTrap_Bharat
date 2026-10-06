from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.services.llm_engine import generate_decoy_reply
from backend.database.db import get_db_connection

router = APIRouter(prefix="/api/honeypot", tags=["Honeypot Chat"])

# In-memory session tracking for WhatsApp Bridge and simulated threads
wa_bridge_state = {
    "connected": False,
    "qr_code": None,
    "phone_number": "+91 91234 56780",
    "persona": "Vikas Ji (52y Retired Citizen)",
    "trap_active_numbers": {"+91 98765 43210": True}
}

outbox_queue: List[Dict[str, Any]] = []

class MessagePayload(BaseModel):
    case_id: str = "CASE-2026-1001"
    message_text: str
    sender_role: str = "scammer"
    sender_phone: Optional[str] = "+91 98765 43210"

class TrapTogglePayload(BaseModel):
    phone_number: str
    is_active: bool

class WaStatusPayload(BaseModel):
    connected: bool
    qr_code: Optional[str] = None
    phone_number: Optional[str] = None

@router.get("/status")
@router.get("/wa-status")
def get_honeypot_status():
    """Returns 2-phone honeypot connection and node health."""
    return {
        "node_status": "CONNECTED" if wa_bridge_state["connected"] else "ONLINE_STANDBY",
        "qr_ready": True,
        "whatsapp_connected": wa_bridge_state["connected"],
        "virtual_phone_number": wa_bridge_state["phone_number"],
        "active_persona": wa_bridge_state["persona"],
        "mode": "100% Isolated Local Sandbox",
        "trap_active_numbers": wa_bridge_state["trap_active_numbers"],
        "scammers_engaged_total": 12,
        "mules_extracted_total": 9
    }

@router.post("/wa-status")
def update_wa_status(payload: WaStatusPayload):
    """Updates WhatsApp Bridge status from Node.js."""
    wa_bridge_state["connected"] = payload.connected
    if payload.qr_code:
        wa_bridge_state["qr_code"] = payload.qr_code
    if payload.phone_number:
        wa_bridge_state["phone_number"] = payload.phone_number
    return {"status": "updated"}

@router.post("/toggle-trap")
def toggle_trap_for_number(payload: TrapTogglePayload):
    """Toggles active AI decoy trap for a specific scammer phone number."""
    wa_bridge_state["trap_active_numbers"][payload.phone_number] = payload.is_active
    return {
        "status": "success",
        "phone_number": payload.phone_number,
        "is_active": payload.is_active
    }

@router.get("/threads")
def get_scammer_threads():
    """Returns active threads for Tab 2 UI."""
    return [
        {
            "phone": "+91 98765 43210",
            "category": "Electricity Bill Scam",
            "is_trap_active": wa_bridge_state["trap_active_numbers"].get("+91 98765 43210", True),
            "last_message": "Theek hai is backup account pe transfer karo: A/C 50200084729104",
            "time": "Just now"
        },
        {
            "phone": "+91 91234 56789",
            "category": "Bank KYC Fraud",
            "is_trap_active": wa_bridge_state["trap_active_numbers"].get("+91 91234 56789", False),
            "last_message": "Send Rs 100 on sbi.kyc.update@okaxis to unlock YONO",
            "time": "12m ago"
        }
    ]

@router.post("/send-message")
@router.post("/incoming")
def process_scammer_message(payload: MessagePayload):
    """Processes an incoming message from the scammer and computes the AI decoy response."""
    with get_db_connection() as conn:
        # Save scammer message
        conn.execute(
            "INSERT INTO messages (case_id, sender_role, message_text) VALUES (?, ?, ?)",
            (payload.case_id, payload.sender_role, payload.message_text)
        )
        conn.commit()
        
        # Retrieve recent conversation
        rows = conn.execute(
            "SELECT sender_role, message_text FROM messages WHERE case_id = ? ORDER BY id ASC",
            (payload.case_id,)
        ).fetchall()
        
        chat_history = [{"role": r["sender_role"], "text": r["message_text"]} for r in rows]
        
        # Generate decoy response
        decoy_reply = generate_decoy_reply(chat_history)
        
        # Save decoy response
        conn.execute(
            "INSERT INTO messages (case_id, sender_role, message_text) VALUES (?, 'ai_decoy', ?)",
            (payload.case_id, decoy_reply)
        )
        conn.commit()
        
        # Fetch updated messages
        updated_rows = conn.execute(
            "SELECT id, sender_role, message_text, timestamp FROM messages WHERE case_id = ? ORDER BY id ASC",
            (payload.case_id,)
        ).fetchall()

    # Add to outbox for WA Bridge if needed
    outbox_queue.append({
        "to_phone": payload.sender_phone or "+91 98765 43210",
        "text": decoy_reply
    })

    return {
        "status": "success",
        "decoy_response": decoy_reply,
        "chat_history": [dict(r) for r in updated_rows]
    }

@router.get("/outbox")
def get_outbox():
    """Returns messages pending to be sent by the WhatsApp bridge."""
    messages_to_send = list(outbox_queue)
    outbox_queue.clear()
    return {"outbox": messages_to_send}
