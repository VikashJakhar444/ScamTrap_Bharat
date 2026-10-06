from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.services.llm_engine import generate_decoy_reply
from backend.database.db import get_db_connection

router = APIRouter(prefix="/api/honeypot", tags=["Honeypot Chat"])

class MessagePayload(BaseModel):
    case_id: str = "CASE-2026-1001"
    message_text: str
    sender_role: str = "scammer"

@router.get("/status")
def get_honeypot_status():
    """Returns 2-phone honeypot connection and node health."""
    return {
        "node_status": "ONLINE_STANDBY",
        "qr_ready": True,
        "whatsapp_connected": True,
        "virtual_phone_number": "+91 91234 56780",
        "active_persona": "Vikas Ji (Elderly Citizen Decoy)",
        "mode": "100% Isolated Local Sandbox",
        "scammers_engaged_total": 12,
        "mules_extracted_total": 9
    }

@router.post("/send-message")
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

    return {
        "status": "success",
        "decoy_response": decoy_reply,
        "chat_history": [dict(r) for r in updated_rows]
    }

@router.get("/chat-history/{case_id}")
def get_chat_history(case_id: str):
    """Retrieves the full message history for a specific case."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, sender_role, message_text, timestamp FROM messages WHERE case_id = ? ORDER BY id ASC",
            (case_id,)
        ).fetchall()
    return {
        "case_id": case_id,
        "messages": [dict(r) for r in rows]
    }
