from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import hashlib
import json
import os
import re
import urllib.parse
import uuid

from backend.services.reply_ai import build_cloud_system, build_demo_scammer_system, build_demo_decoy_system, generate_reply
from backend.services.extractor import extract_entities
from backend.database.db import get_db_connection, normalize_digits

router = APIRouter(prefix="/api/honeypot", tags=["Honeypot Chat"])

# --------------------------------------------------------------------------- #
# Bridge state (fed by the Node bridge, never hard-coded)
# --------------------------------------------------------------------------- #
_bridge_state: Dict[str, Any] = {
    "connected": False,
    "qr_data": None,
    "qr_png": None,
    "phone_number": None,
    "last_seen": 0.0,
}

BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "3000"))
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "")
if not BRIDGE_TOKEN:
    BRIDGE_TOKEN = hashlib.sha256(os.urandom(32)).hexdigest()[:32]

# reply engine provider timeouts are handled inside reply_ai; nothing else here.


def _app_get(key: str, default: str = "") -> str:
    with get_db_connection() as conn:
        row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def _app_set(key: str, value: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO app_state (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


def get_active_mode() -> str:
    """'mode1' (co-pilot, human driven) or 'mode2' (cloud node, auto capable)."""
    return _app_get("active_mode", "mode1") or "mode1"


def _is_loopback(request: Request) -> bool:
    host = (request.client.host if request.client else "") or ""
    return host in ("127.0.0.1", "::1", "localhost")


def _norm_phone(value: str) -> str:
    """Last-10-digit key so '+91 98765 00011', '919876543210@c.us' and
    '9876543210' all resolve to one session."""
    return normalize_digits(value or "", last=10)


def _session_by_phone(phone_norm: str) -> Optional[Dict[str, Any]]:
    if not phone_norm or len(phone_norm) < 10:
        return None
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM cloud_sessions WHERE phone_norm = ? ORDER BY created_at DESC LIMIT 1",
            (phone_norm,),
        ).fetchone()
    return dict(row) if row else None


# --------------------------------------------------------------------------- #
# Legacy payloads (kept so old imports never break; endpoints removed below)
# --------------------------------------------------------------------------- #
class TrapTogglePayload(BaseModel):
    phone_number: str
    is_active: bool


class WaStatusPayload(BaseModel):
    connected: bool
    qr_code: Optional[str] = None
    qr_data: Optional[str] = None
    phone_number: Optional[str] = None


# --------------------------------------------------------------------------- #
# Status / health
# --------------------------------------------------------------------------- #
@router.get("/status")
@router.get("/wa-status")
def get_honeypot_status():
    with get_db_connection() as conn:
        engaged = conn.execute(
            "SELECT COUNT(DISTINCT case_id) FROM messages WHERE sender_role = 'scammer'"
        ).fetchone()[0]
        mules = conn.execute(
            "SELECT COUNT(*) FROM scam_identifiers WHERE identifier_type = 'BANK_AC'"
        ).fetchone()[0]
        trap_count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        cloud_active = conn.execute(
            "SELECT COUNT(*) FROM cloud_sessions WHERE status = 'ACTIVE'"
        ).fetchone()[0]

    return {
        "node_status": "CONNECTED" if _bridge_state["connected"] else "BRIDGE_OFFLINE",
        "whatsapp_connected": _bridge_state["connected"],
        "virtual_phone_number": _bridge_state.get("phone_number"),
        "active_mode": get_active_mode(),
        "cloud_sessions_active": cloud_active,
        "scammers_engaged_total": engaged,
        "mules_extracted_total": mules,
        "active_traps_count": trap_count,
        "mode": "100% Isolated Local Sandbox",
    }


@router.post("/wa-status")
def update_wa_status(payload: WaStatusPayload):
    """The Node bridge pushes its live status here (QR + connected + number)."""
    import time
    _bridge_state["connected"] = bool(payload.connected)
    _bridge_state["last_seen"] = time.time()
    if payload.qr_data:
        _bridge_state["qr_data"] = payload.qr_data
    if payload.qr_code:
        _bridge_state["qr_png"] = payload.qr_code
    if payload.phone_number:
        _bridge_state["phone_number"] = payload.phone_number
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE cloud_sessions SET status = 'ACTIVE' WHERE phone_norm = ?",
                (_norm_phone(payload.phone_number),),
            )
            conn.commit()
    if payload.connected:
        _bridge_state["qr_data"] = None
        _bridge_state["qr_png"] = None
    return {"status": "updated", "active_mode": get_active_mode()}


@router.get("/bridge-status")
def bridge_status():
    """Frontend polls this to know if the Node bridge is alive + connected."""
    return {
        "connected": _bridge_state["connected"],
        "has_qr": bool(_bridge_state.get("qr_data") or _bridge_state.get("qr_png")),
        "phone_number": _bridge_state.get("phone_number"),
        "active_mode": get_active_mode(),
        "bridge_port": BRIDGE_PORT,
    }


@router.get("/bridge-qr")
def bridge_qr():
    """Returns the pending QR payload (data-URL) so the UI can render it."""
    return {
        "qr_data": _bridge_state.get("qr_data"),
        "qr_png": _bridge_state.get("qr_png"),
        "connected": _bridge_state["connected"],
    }


class ModePayload(BaseModel):
    mode: str


@router.get("/mode")
def get_mode():
    return {"active_mode": get_active_mode()}


@router.post("/set-mode")
def set_mode(payload: ModePayload):
    """Exactly one mode acts at a time. mode1 = co-pilot (human driven),
    mode2 = cloud node (auto-capable)."""
    mode = (payload.mode or "").strip().lower()
    if mode not in ("mode1", "mode2"):
        raise HTTPException(status_code=422, detail="mode must be 'mode1' or 'mode2'")
    _app_set("active_mode", mode)
    return {"status": "success", "active_mode": mode}


@router.post("/toggle-trap")
def toggle_trap_for_number(payload: TrapTogglePayload):
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE cases SET status = ? WHERE scammer_phone = ?",
            ("TRAP_ACTIVE" if payload.is_active else "STANDBY", payload.phone_number),
        )
        conn.commit()
    return {"status": "success", "phone_number": payload.phone_number, "is_active": payload.is_active}


@router.get("/threads")
def get_scammer_threads():
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
                "is_trap_active": case["status"] == "TRAP_ACTIVE",
                "last_message": last["message_text"] if last else "No messages yet",
                "time": last["timestamp"] if last else case["status"],
            })
    return threads


# --------------------------------------------------------------------------- #
# Outbox: replies the bridge still has to deliver (survives restarts)
# --------------------------------------------------------------------------- #
@router.get("/outbox")
def get_outbox(pending: int = 0):
    """Messages the WhatsApp bridge must still deliver.

    `?pending=1` marks rows as 'claimed' so a reconnecting bridge does not
    double-send, while the normal call (no arg) stays backward compatible."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, case_id, message_text, send_state FROM cloud_messages "
            "WHERE send_state = 0 ORDER BY id ASC"
        ).fetchall()
        outbox = []
        for r in rows:
            session = conn.execute(
                "SELECT scammer_phone FROM cloud_sessions WHERE case_id = ?",
                (r["case_id"],),
            ).fetchone()
            phone = session["scammer_phone"] if session else None
            if not phone or phone == "UNKNOWN":
                continue
            outbox.append({
                "id": r["id"],
                "case_id": r["case_id"],
                "to_phone": phone,
                "text": r["message_text"],
            })
        if pending and outbox:
            ids = [o["id"] for o in outbox]
            conn.execute(
                "UPDATE cloud_messages SET send_state = 1 WHERE id IN (%s)" % ",".join("?" * len(ids)),
                ids,
            )
            conn.commit()
    return {"outbox": outbox}


class SentPayload(BaseModel):
    ids: List[int]


@router.post("/sents")
def mark_sent(payload: SentPayload):
    """Bridge confirms delivery so we stop retrying."""
    if not payload.ids:
        return {"status": "noop"}
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE cloud_messages SET send_state = 1 WHERE id IN (%s)" % ",".join("?" * len(payload.ids)),
            payload.ids,
        )
        conn.commit()
    return {"status": "ok", "marked": len(payload.ids)}


# --------------------------------------------------------------------------- #
# Case creation (Tab 1 -> Tab 2 handover)
# --------------------------------------------------------------------------- #
class CreateCasePayload(BaseModel):
    scammer_phone: Optional[str] = None
    scammer_upi: Optional[str] = None
    scam_category: str = "General Suspicious"
    context: Optional[str] = None
    victim_name: Optional[str] = None
    lang: str = "en"


@router.post("/create-case")
def create_case(payload: CreateCasePayload):
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
# Detail mining (reuses the Tab 1 extractor, nothing new invented)
# --------------------------------------------------------------------------- #
_DETAIL_TYPE_MAP = {
    "upis": "UPI",
    "phones": "PHONE",
    "bank_accounts": "BANK_AC",
    "ifsc_codes": "IFSC",
}


def mine_details(case_id: str, text: str) -> List[Dict[str, str]]:
    """Pulls every fraud-relevant entity out of `text` and stores the ones we
    have not already seen for this case. Returns the newly stored rows."""
    if not text or not text.strip():
        return []
    try:
        entities = extract_entities(text) or {}
    except Exception:
        return []

    stored: List[Dict[str, str]] = []
    with get_db_connection() as conn:
        seen = {
            (r["detail_type"], r["detail_value"])
            for r in conn.execute(
                "SELECT detail_type, detail_value FROM extracted_details WHERE case_id = ?",
                (case_id,),
            ).fetchall()
        }
        for key, dtype in _DETAIL_TYPE_MAP.items():
            for value in entities.get(key) or []:
                value = (value or "").strip()
                if not value:
                    continue
                normalized = _norm_phone(value) if dtype == "PHONE" else value
                if (dtype, normalized) in seen:
                    continue
                seen.add((dtype, normalized))
                conn.execute(
                    "INSERT INTO extracted_details (case_id, detail_type, detail_value, source_message) "
                    "VALUES (?, ?, ?, ?)",
                    (case_id, dtype, normalized, text[:400]),
                )
                stored.append({"type": dtype, "value": normalized})
        conn.commit()
    return stored


@router.get("/extracted")
def get_extracted(case_id: str):
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, detail_type, detail_value, source_message, created_at "
            "FROM extracted_details WHERE case_id = ? ORDER BY id ASC",
            (case_id,),
        ).fetchall()
    return {"case_id": case_id, "details": [dict(r) for r in rows]}


# --------------------------------------------------------------------------- #
# Inbound WhatsApp webhook (bridge -> backend)
# --------------------------------------------------------------------------- #
class WebhookPayload(BaseModel):
    from_user: str = Field(..., alias="from")
    text: str
    wamid: Optional[str] = None

    class Config:
        populate_by_name = True


@router.post("/webhook")
def inbound_webhook(payload: WebhookPayload, request: Request):
    """One scammer message in, at most one in-character reply out.

    Exactly-once is enforced by a UNIQUE dedup_key + an atomic claim, so the
    webhook and the manual UI box can never both answer the same message."""
    if not _is_loopback(request):
        raise HTTPException(status_code=403, detail="bridge webhook is loopback only")
    token = (request.headers.get("x-bridge-token") or "").strip()
    if BRIDGE_TOKEN and token != BRIDGE_TOKEN:
        raise HTTPException(status_code=403, detail="bad bridge token")

    text = (payload.text or "").strip()
    if not text:
        return {"status": "ignored", "reason": "empty"}

    phone_norm = _norm_phone(payload.from_user)
    dedup = payload.wamid or hashlib.sha1(f"{phone_norm}|{text}".encode("utf-8")).hexdigest()
    dedup_key = f"{phone_norm}:{dedup}"

    session = _session_by_phone(phone_norm)
    if session is None:
        return {"status": "ignored", "reason": "no_session", "phone_norm": phone_norm}

    with get_db_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO inbound_queue (dedup_key, phone_norm, text, case_id) VALUES (?, ?, ?, ?)",
                (dedup_key, phone_norm, text, session["case_id"]),
            )
            claimed = conn.execute(
                "UPDATE inbound_queue SET claimed_by = 'webhook' "
                "WHERE dedup_key = ? AND claimed_by IS NULL",
                (dedup_key,),
            ).rowcount
            conn.commit()
        except Exception:
            claimed = 0
            conn.rollback()
    if claimed != 1:
        return {"status": "duplicate", "reason": "already claimed"}

    if get_active_mode() != "mode2":
        return {"status": "queued", "reason": "mode1_active", "case_id": session["case_id"]}

    case_id = session["case_id"]
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO cloud_messages (case_id, sender_role, message_text) VALUES (?, 'scammer', ?)",
            (case_id, text),
        )
        conn.commit()
    mine_details(case_id, text)

    persona = _persona_of(session)
    history = _cloud_history(case_id)
    system = build_cloud_system(
        session.get("relation") or persona.get("relation") or "family member",
        persona.get("fake_name") or session.get("fake_name") or "",
        session.get("excuse") or persona.get("excuse") or "",
        session.get("scam_category") or persona.get("scam_category") or "General Suspicious",
        persona.get("case_context") or {},
        persona_mode=persona.get("persona_mode", "self"),
    )
    result = generate_reply(system, chat_history=history)

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO cloud_messages (case_id, sender_role, message_text, send_image, send_state) "
            "VALUES (?, 'ai', ?, ?, 0)",
            (case_id, result["reply"], 1 if result["send_image"] else 0),
        )
        conn.commit()
    mine_details(case_id, result["reply"])

    return {
        "status": "Reply Delivered",
        "case_id": case_id,
        "ai_reply": result["reply"],
        "provider": result["provider"],
    }


# --------------------------------------------------------------------------- #
# Cloud session (Mode 2)
# --------------------------------------------------------------------------- #
class ImportPayload(BaseModel):
    case_context: Optional[Dict[str, Any]] = None
    copilot_turns: Optional[List[Dict[str, str]]] = None
    original_message: Optional[str] = None
    target_phone: Optional[str] = None
    bait_amount: Optional[str] = None


class InitCloudPayload(BaseModel):
    scammer_phone: str = ""
    relation: str = ""
    fake_name: Optional[str] = ""
    excuse: str = ""
    scam_category: Optional[str] = "General Suspicious"
    scammer_upi: Optional[str] = None
    context: Optional[str] = None
    case_context: Optional[Dict[str, Any]] = None
    persona_mode: str = "self"
    transport: str = "own"
    import_context: Optional[ImportPayload] = None


class CloudChatPayload(BaseModel):
    case_id: str
    scammer_message: str


def _persona_of(session: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(session.get("persona_details") or "{}")
    except json.JSONDecodeError:
        return {}


def _cloud_image_url(persona: Dict[str, Any]) -> str:
    params = {
        "upi": persona.get("scammer_upi") or "scam.target@okaxis",
        "amount": str(persona.get("amount") or "499"),
        "sender_name": persona.get("fake_name") or "",
    }
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v)
    return f"/api/co-pilot/fake-receipt?{query}"


@router.post("/init-cloud")
def init_cloud_session(payload: InitCloudPayload):
    """Boots a Mode 2 session.

    - transport 'own'    -> user connected their own WhatsApp (live, QR path)
    - transport 'virtual'-> coming soon (system's own number, demo only)
    - persona_mode 'self'-> talking as the original victim, no fake identity
    - persona_mode 'character' -> talking as a named relative (needs name+excuse)
    """
    phone = (payload.scammer_phone or "").strip() or "UNKNOWN"
    persona_mode = (payload.persona_mode or "self").strip().lower()
    if persona_mode not in ("self", "character"):
        raise HTTPException(status_code=422, detail="persona_mode must be 'self' or 'character'")
    transport = (payload.transport or "own").strip().lower()
    relation = (payload.relation or "").strip()
    fake_name = (payload.fake_name or "").strip()
    excuse = (payload.excuse or "").strip()
    category = (payload.scam_category or "General Suspicious").strip()

    if persona_mode == "character" and not fake_name:
        raise HTTPException(status_code=422, detail="fake_name is required for a relative persona")

    case_id = f"CLOUD-{uuid.uuid4().hex[:8].upper()}"
    imported = payload.import_context or ImportPayload()
    case_context = dict(payload.case_context or imported.case_context or {})
    if imported.bait_amount:
        case_context["amount"] = imported.bait_amount

    persona = {
        "persona_mode": persona_mode,
        "relation": relation or ("the person they originally messaged" if persona_mode == "self" else "family member"),
        "fake_name": fake_name,
        "excuse": excuse,
        "scam_category": category,
        "scammer_upi": (payload.scammer_upi or "").strip(),
        "amount": str(case_context.get("amount") or "499"),
        "case_context": case_context,
        "transport": transport,
    }

    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO cloud_sessions
                   (case_id, scammer_phone, relation, fake_name, excuse,
                    scam_category, persona_details, status, phone_norm, persona_mode, transport)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)""",
            (case_id, phone, persona["relation"], fake_name, excuse,
             category, json.dumps(persona, ensure_ascii=False),
             _norm_phone(phone), persona_mode, transport),
        )

        # Carry over whatever already happened in Mode 1 / Tab 1.
        seed = (payload.context or imported.original_message or "").strip()
        if seed:
            conn.execute(
                "INSERT INTO cloud_messages (case_id, sender_role, message_text) VALUES (?, 'scammer', ?)",
                (case_id, seed),
            )
        for turn in (imported.copilot_turns or []):
            role = (turn.get("role") or "").strip().lower()
            text = (turn.get("text") or "").strip()
            if not text or role not in ("scammer", "ai"):
                continue
            conn.execute(
                "INSERT INTO cloud_messages (case_id, sender_role, message_text) VALUES (?, ?, ?)",
                (case_id, role, text),
            )
        conn.commit()

    if seed:
        mine_details(case_id, seed)

    # No blocking AI greeting here — the modal must open instantly.
    # First AI reply is generated lazily on the first real/simulated scammer message.
    return {
        "status": "Trap Initialized",
        "case_id": case_id,
        "scammer_phone": phone,
        "phone_norm": _norm_phone(phone),
        "persona_mode": persona_mode,
        "transport": transport,
        "persona": persona,
        "message": "",
        "greeting": "",
        "waiting": "Waiting for the scammer's message…",
        "provider": "none",
        "chat_history": _cloud_history(case_id),
        "extracted": get_extracted(case_id)["details"],
        "active_mode": get_active_mode(),
    }


def _cloud_history(case_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, sender_role, message_text, send_image, send_state, timestamp FROM cloud_messages "
            "WHERE case_id = ? ORDER BY id ASC",
            (case_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/cloud-history")
def get_cloud_history(case_id: str):
    with get_db_connection() as conn:
        session = conn.execute(
            "SELECT case_id, scammer_phone, persona_details, status, persona_mode, transport "
            "FROM cloud_sessions WHERE case_id = ?",
            (case_id,),
        ).fetchone()
    if session is None:
        raise HTTPException(status_code=404, detail="cloud session not found")
    return {
        "session": dict(session),
        "chat_history": _cloud_history(case_id),
        "extracted": get_extracted(case_id)["details"],
        "active_mode": get_active_mode(),
    }


class SentMessagePayload(BaseModel):
    case_id: str
    scammer_message: str
    source: str = "manual"


@router.post("/chat-message")
def cloud_chat_message(payload: SentMessagePayload):
    """Manual turn from the Mode 2 UI box.

    Same exactly-once claim as the webhook: if the bridge already answered this
    exact text we return the stored reply instead of generating a second one."""
    text = (payload.scammer_message or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="scammer_message is required")

    with get_db_connection() as conn:
        session = conn.execute(
            "SELECT * FROM cloud_sessions WHERE case_id = ?", (payload.case_id,),
        ).fetchone()
    if session is None:
        raise HTTPException(status_code=404, detail="cloud session not found")

    persona = _persona_of(dict(session))
    phone_norm = _norm_phone(session["scammer_phone"] or "")
    dedup_key = f"{phone_norm}:{hashlib.sha1(f'{phone_norm}|{text}'.encode('utf-8')).hexdigest()}"

    with get_db_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO inbound_queue (dedup_key, phone_norm, text, case_id) VALUES (?, ?, ?, ?)",
                (dedup_key, phone_norm, text, payload.case_id),
            )
            claimed = conn.execute(
                "UPDATE inbound_queue SET claimed_by = 'manual' "
                "WHERE dedup_key = ? AND claimed_by IS NULL",
                (dedup_key,),
            ).rowcount
            conn.commit()
        except Exception:
            claimed = 0
            conn.rollback()

    if claimed != 1:
        # Someone (webhook or an earlier click) already answered this text.
        history = _cloud_history(payload.case_id)
        last_ai = next((m for m in reversed(history) if m["sender_role"] == "ai"), None)
        return {
            "status": "duplicate",
            "case_id": payload.case_id,
            "ai_reply": last_ai["message_text"] if last_ai else "",
            "chat_history": history,
        }

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO cloud_messages (case_id, sender_role, message_text) VALUES (?, 'scammer', ?)",
            (payload.case_id, text),
        )
        conn.commit()
    mine_details(payload.case_id, text)

    history = _cloud_history(payload.case_id)
    system = build_cloud_system(
        session["relation"] or persona.get("relation") or "family member",
        persona.get("fake_name") or session["fake_name"] or "",
        session["excuse"] or persona.get("excuse") or "",
        session["scam_category"] or persona.get("scam_category") or "General Suspicious",
        persona.get("case_context") or {},
        persona_mode=persona.get("persona_mode", "self"),
    )
    result = generate_reply(system, chat_history=history)

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO cloud_messages (case_id, sender_role, message_text, send_image, send_state) "
            "VALUES (?, 'ai', ?, ?, 0)",
            (payload.case_id, result["reply"], 1 if result["send_image"] else 0),
        )
        conn.commit()
    mine_details(payload.case_id, result["reply"])

    return {
        "status": "success",
        "case_id": payload.case_id,
        "ai_reply": result["reply"],
        "send_image": result["send_image"],
        "image_url": _cloud_image_url(persona) if result["send_image"] else None,
        "provider": result["provider"],
        "chat_history": _cloud_history(payload.case_id),
        "extracted": get_extracted(payload.case_id)["details"],
    }


class DemoTurnPayload(BaseModel):
    case_id: Optional[str] = None
    scam_category: Optional[str] = "General Suspicious"
    persona_mode: str = "self"
    relation: str = ""
    fake_name: str = ""
    excuse: str = ""
    case_context: Optional[Dict[str, Any]] = None
    last_message: Optional[str] = None
    side: str = "scammer"
    history: Optional[List[Dict[str, str]]] = None
    turn_index: int = 0
    total_turns: int = 8


@router.post("/demo-turn")
def demo_turn(payload: DemoTurnPayload):
    """One step of the DEMO walkthrough.

    `side='scammer'` -> what the scammer would plausibly say next
    `side='decoy'`   -> what our system would send back
    `side='extract'` -> mine details from the finished demo transcript

    The demo never emits strategy, prompts or internal rules to the caller."""
    category = (payload.scam_category or "General Suspicious").strip()
    persona_mode = (payload.persona_mode or "self").strip().lower()
    case_context = payload.case_context or {}
    last = (payload.last_message or "").strip()

    # Finish step: mine the whole demo transcript for anything the scammer
    # handed over. Uses the real extractor so the panel matches live mode.
    if payload.side == "extract":
        full_text = last
        found: List[Dict[str, str]] = []
        if full_text:
            try:
                ent = extract_entities(full_text)
                for key, label in (
                    ("upis", "UPI"),
                    ("phones", "PHONE"),
                    ("bank_accounts", "BANK_AC"),
                    ("ifsc_codes", "IFSC"),
                ):
                    for v in (ent.get(key) or []):
                        v = str(v).strip()
                        if v:
                            found.append({"type": label, "value": v})
            except Exception:
                pass
        return {"status": "success", "side": "extract", "details": found}

    if payload.side == "scammer":
        system = build_demo_scammer_system(category, case_context, turn_index=payload.turn_index, total_turns=payload.total_turns)
    else:
        system = build_demo_decoy_system(category, case_context, turn_index=payload.turn_index, total_turns=payload.total_turns)

    # Feed the whole running conversation so every turn stays coherent.
    turns = list(payload.history or [])
    if last:
        turns.append({"role": "scammer" if payload.side == "scammer" else "ai", "text": last})

    result = generate_reply(
        system + "\n\nOutput only the message text. No labels, no quotes, no explanation.",
        chat_history=turns,
    )

    details: List[Dict[str, str]] = []
    if payload.case_id:
        mine_details(payload.case_id, result["reply"])
        details = get_extracted(payload.case_id)["details"]

    return {
        "status": "success",
        "side": payload.side,
        "text": result["reply"],
        "provider": result["provider"],
        "details": details,
    }

