from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.services.decoy_persona import generate_decoy_reply
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
    """Returns 2-phone honeypot connection and node health. Totals are counted
    from the live database rather than hard-coded."""
    with get_db_connection() as conn:
        engaged = conn.execute(
            "SELECT COUNT(DISTINCT case_id) FROM messages WHERE sender_role = 'scammer'"
        ).fetchone()[0]
        mules = conn.execute(
            "SELECT COUNT(*) FROM scam_identifiers WHERE identifier_type = 'BANK_AC'"
        ).fetchone()[0]
        trap_count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]

    return {
        "node_status": "CONNECTED" if wa_bridge_state["connected"] else "ONLINE_STANDBY",
        "qr_ready": True,
        "whatsapp_connected": wa_bridge_state["connected"],
        "virtual_phone_number": wa_bridge_state["phone_number"],
        "active_persona": wa_bridge_state["persona"],
        "mode": "100% Isolated Local Sandbox",
        "trap_active_numbers": wa_bridge_state["trap_active_numbers"],
        "scammers_engaged_total": engaged,
        "mules_extracted_total": mules,
        "active_traps_count": trap_count,
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
    """Returns active threads for Tab 2 UI, built from stored cases and their
    most recent message."""
    with get_db_connection() as conn:
        cases = conn.execute(
            "SELECT case_id, scammer_phone, scam_category, status FROM cases ORDER BY created_at DESC"
        ).fetchall()
        threads = []
        for case in cases:
            last = conn.execute(
                "SELECT message_text, timestamp FROM messages WHERE case_id = ? AND sender_role != 'system' ORDER BY id DESC LIMIT 1",
                (case["case_id"],),
            ).fetchone()
            threads.append({
                "case_id": case["case_id"],
                "phone": case["scammer_phone"],
                "category": case["scam_category"],
                "is_trap_active": wa_bridge_state["trap_active_numbers"].get(
                    case["scammer_phone"], case["status"] != "STANDBY"
                ),
                "last_message": last["message_text"] if last else "No messages yet",
                "time": last["timestamp"] if last else case["status"],
            })
    return threads

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


class CreateCasePayload(BaseModel):
    scammer_phone: Optional[str] = None
    scammer_upi: Optional[str] = None
    scam_category: str = "General Suspicious"
    context: Optional[str] = None
    victim_name: Optional[str] = None
    lang: str = "en"


@router.post("/create-case")
def create_case(payload: CreateCasePayload):
    """spec §7 — hands a Tab 1 investigation over to Tab 2 (the Honeypot).

    Creates a `cases` row plus a seed `scammer` message carrying the original
    context, so the co-pilot chat has the real thread to work with.
    """
    import uuid

    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    phone = (payload.scammer_phone or "").strip() or "UNSPECIFIED"
    category = (payload.scam_category or "General Suspicious").strip()

    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO cases (case_id, scammer_phone, scam_category, status)
               VALUES (?, ?, ?, 'STANDBY')""",
            (case_id, phone, category),
        )
        seed_text = (payload.context or "").strip()
        if seed_text:
            conn.execute(
                """INSERT INTO messages (case_id, sender_role, message_text)
                   VALUES (?, 'scammer', ?)""",
                (case_id, seed_text),
            )
        if payload.scammer_upi:
            conn.execute(
                """INSERT INTO scam_identifiers
                       (identifier_value, identifier_type, scam_category, risk_score, reports_count)
                   VALUES (?, 'UPI', ?, 80, 1)
                   ON CONFLICT(identifier_value) DO UPDATE SET
                       reports_count = reports_count + 1,
                       last_seen = CURRENT_TIMESTAMP""",
                (payload.scammer_upi.strip(), category),
            )
        conn.commit()

    return {
        "status": "success",
        "case_id": case_id,
        "scammer_phone": phone,
        "scammer_upi": payload.scammer_upi,
        "scam_category": category,
        "message": "Case opened in the Honeypot tab.",
    }
