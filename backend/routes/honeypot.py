from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import urllib.parse
import uuid

from backend.services.decoy_persona import generate_decoy_reply
from backend.services.reply_ai import build_cloud_system, generate_reply
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


# --------------------------------------------------------------------------- #
# Tab 2 · Cloud AI Node (autonomous takeover)
# --------------------------------------------------------------------------- #
class InitCloudPayload(BaseModel):
    scammer_phone: str = ""
    relation: str = "family member"
    fake_name: Optional[str] = ""
    excuse: str = ""
    scam_category: Optional[str] = "General Suspicious"
    scammer_upi: Optional[str] = None
    context: Optional[str] = None
    case_context: Optional[Dict[str, Any]] = None


class CloudChatPayload(BaseModel):
    case_id: str
    scammer_message: str


def _cloud_image_url(persona: Dict[str, Any]) -> str:
    """Receipt URL the terminal can show as an attached screenshot."""
    params = {
        "upi": persona.get("scammer_upi") or "scam.target@okaxis",
        "amount": str(persona.get("amount") or "499"),
        "sender_name": persona.get("fake_name") or "Rahul Sharma",
    }
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    return f"/api/co-pilot/fake-receipt?{query}"


@router.post("/init-cloud")
def init_cloud_session(payload: InitCloudPayload):
    """Boots an autonomous decoy session and returns its first in-character greeting."""
    phone = (payload.scammer_phone or "").strip() or "UNKNOWN"
    relation = (payload.relation or "family member").strip()
    fake_name = (payload.fake_name or "").strip()
    excuse = (payload.excuse or "").strip()
    category = (payload.scam_category or "General Suspicious").strip()

    if not excuse:
        raise HTTPException(status_code=422, detail="excuse is required")

    case_id = f"CLOUD-{uuid.uuid4().hex[:8].upper()}"
    persona = {
        "relation": relation,
        "fake_name": fake_name or "Rahul Sharma",
        "excuse": excuse,
        "scam_category": category,
        "scammer_upi": (payload.scammer_upi or "").strip(),
        "amount": "499",
        "case_context": payload.case_context or {},
    }

    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO cloud_sessions
                   (case_id, scammer_phone, relation, fake_name, excuse,
                    scam_category, persona_details, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE')""",
            (case_id, phone, relation, fake_name, excuse,
             category, json.dumps(persona, ensure_ascii=False)),
        )

        seed = (payload.context or "").strip()
        if seed:
            conn.execute(
                "INSERT INTO cloud_messages (case_id, sender_role, message_text) VALUES (?, 'scammer', ?)",
                (case_id, seed),
            )
        conn.commit()

    system = build_cloud_system(relation, persona["fake_name"], excuse, category, payload.case_context)
    opener_seed = seed or (
        f"The scammer has been messaged about a {category} payment request and is waiting "
        "for a reply from this new number."
    )
    greeting = generate_reply(
        system + "\n\nThis is the FIRST message of the chat, so write it in character as your "
        "own opening message rather than an answer.",
        chat_history=[{"role": "scammer", "text": opener_seed}],
    )

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO cloud_messages (case_id, sender_role, message_text, send_image) VALUES (?, 'ai', ?, ?)",
            (case_id, greeting["reply"], 1 if greeting["send_image"] else 0),
        )
        conn.commit()

    return {
        "status": "success",
        "case_id": case_id,
        "scammer_phone": phone,
        "persona": persona,
        "greeting": greeting["reply"],
        "provider": greeting["provider"],
        "chat_history": _cloud_history(case_id),
    }


def _cloud_history(case_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, sender_role, message_text, send_image, timestamp FROM cloud_messages "
            "WHERE case_id = ? ORDER BY id ASC",
            (case_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/cloud-history")
def get_cloud_history(case_id: str):
    with get_db_connection() as conn:
        session = conn.execute(
            "SELECT case_id, scammer_phone, persona_details, status FROM cloud_sessions WHERE case_id = ?",
            (case_id,),
        ).fetchone()
    if session is None:
        raise HTTPException(status_code=404, detail="cloud session not found")
    return {"session": dict(session), "chat_history": _cloud_history(case_id)}


@router.post("/chat-message")
def cloud_chat_message(payload: CloudChatPayload):
    """One scammer turn in, one in-character decoy turn out (stateless-ish:
    the transcript is re-read from SQLite so refreshes keep context)."""
    text = (payload.scammer_message or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="scammer_message is required")

    with get_db_connection() as conn:
        session = conn.execute(
            "SELECT * FROM cloud_sessions WHERE case_id = ?", (payload.case_id,)
        ).fetchone()
    if session is None:
        raise HTTPException(status_code=404, detail="cloud session not found")

    try:
        persona = json.loads(session["persona_details"] or "{}")
    except json.JSONDecodeError:
        persona = {}

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO cloud_messages (case_id, sender_role, message_text) VALUES (?, 'scammer', ?)",
            (payload.case_id, text),
        )
        conn.commit()

    history = _cloud_history(payload.case_id)
    system = build_cloud_system(
        session["relation"] or persona.get("relation") or "family member",
        persona.get("fake_name") or session["fake_name"] or "Rahul Sharma",
        session["excuse"] or persona.get("excuse") or "the original number was not reachable",
        session["scam_category"] or persona.get("scam_category") or "General Suspicious",
        persona.get("case_context") or {},
    )
    result = generate_reply(system, chat_history=history)

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO cloud_messages (case_id, sender_role, message_text, send_image) VALUES (?, 'ai', ?, ?)",
            (payload.case_id, result["reply"], 1 if result["send_image"] else 0),
        )
        conn.commit()

    return {
        "status": "success",
        "case_id": payload.case_id,
        "ai_reply": result["reply"],
        "send_image": result["send_image"],
        "image_url": _cloud_image_url(persona) if result["send_image"] else None,
        "provider": result["provider"],
        "chat_history": _cloud_history(payload.case_id),
    }
