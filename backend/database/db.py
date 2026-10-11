import sqlite3
import os
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import DB_PATH

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class _ClosingConnection(sqlite3.Connection):
    """sqlite3.Connection whose `with` block actually CLOSES on exit.

    The stock Connection.__exit__ only commits/rollbacks — every `with
    get_db_connection() as conn:` in this codebase would otherwise leak a
    file handle per request. Overriding __exit__ fixes the leak without
    touching a single call site."""

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with Row factory enabled.

    WAL + busy_timeout make the concurrent bridge sweep / webhook / Tab 1
    audit writes safe; the custom factory closes the handle on `with` exit."""
    conn = sqlite3.connect(DB_PATH, timeout=10, factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _migrate_columns(conn: sqlite3.Connection, table: str, wanted: Dict[str, str]) -> None:
    """Adds any missing columns to an existing table (SQLite has no
    `ADD COLUMN IF NOT EXISTS`, so we introspect)."""
    have = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    for col, decl in wanted.items():
        if col not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def init_db():
    """Initializes the database schema and seeds initial data if empty."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with get_db_connection() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        # Upgrade pre-existing databases in place.
        _migrate_columns(conn, "cloud_sessions", {
            "phone_norm": "TEXT",
            "persona_mode": "TEXT NOT NULL DEFAULT 'self'",
            "transport": "TEXT NOT NULL DEFAULT 'own'",
        })
        _migrate_columns(conn, "cloud_messages", {
            "send_state": "INTEGER NOT NULL DEFAULT 0",
        })
        conn.commit()
        
        # Check if scam_identifiers table has records
        cursor = conn.execute("SELECT COUNT(*) FROM scam_identifiers")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Seed identifiers based on real Indian cyber-fraud patterns reported
            # by I4C / RBI / PIB (Feb–Jul 2026). All values are FICTIONAL —
            # chosen to match typical mule-account / UPI-handle formats seen in
            # public cybercrime advisories, without referencing any real victim
            # or real mule account.
            initial_seeds = [
                # Electricity-bill disconnection UPI mule (I4C advisory, Mar 2026)
                ("apcol.bijli.bill@ybl", "UPI", "Electricity Bill", 98, 47),
                # Bank-KYC update UPI mule (RBI cyber-fraud circular, Apr 2026)
                ("sbi.kyc.refund@okaxis", "UPI", "Bank KYC", 97, 112),
                # Job-scam phone (I4C "Digital Arrest" advisory, May 2026)
                ("+918826451097", "PHONE", "Job Scam", 93, 61),
                # Part-time-task mule account (typical HDFC savings format,
                # matches pattern in I4C mule-account advisory)
                ("50100218476309", "BANK_AC", "Part-Time Task", 96, 78),
                # IFSC for the above account (HDFC branch code, fictional)
                ("HDFC0001937", "IFSC", "Part-Time Task", 94, 33),
                # Fake-loan phone (I4C instant-loan app advisory, Jun 2026)
                ("+917042318856", "PHONE", "Fake Loan", 91, 44),
                # Digital-arrest UPI mule (I4C "CBI/Cyber Cell" impersonation)
                ("cyber.cell.refund@paytm", "UPI", "Digital Arrest", 99, 156),
                # OTP-fraud phone (RBI "never share OTP" campaign, Jul 2026)
                ("+919643207158", "PHONE", "OTP Fraud", 95, 89),
            ]
            conn.executemany(
                """
                INSERT INTO scam_identifiers 
                (identifier_value, identifier_type, scam_category, risk_score, reports_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                initial_seeds
            )
            
            # Seed a sample resolved case for the evidence tab.
            # Phone matches the electricity-bill mule above (+918826451097).
            conn.execute(
                """
                INSERT OR IGNORE INTO cases (case_id, scammer_phone, scam_category, status)
                VALUES ('CASE-2026-1001', '+918826451097', 'Electricity Bill Disconnection', 'RESOLVED')
                """
            )
            
            sample_messages = [
                ('CASE-2026-1001', 'scammer',
                 'Dear Consumer, Your Electricity power will be disconnected tonight 9:30 PM from power office '
                 'because your previous month bill was not updated. Please immediately contact our officer '
                 'at +918826451097.'),
                ('CASE-2026-1001', 'ai_decoy',
                 'Sir please mat kaato light! Bachhe padh rahe hain. Kahan pay karna hai batayein?'),
                ('CASE-2026-1001', 'scammer',
                 'Pay Rs 45 immediately on our official power UPI: apcol.bijli.bill@ybl or bill will not update.'),
                ('CASE-2026-1001', 'ai_decoy',
                 'Sir maine try kiya par UPI Daily Limit Reached error aa raha hai. Dekhiye screenshot. '
                 'Koi alternate account number ya secondary UPI do jaldi?'),
                ('CASE-2026-1001', 'scammer',
                 'Theek hai is backup account pe transfer karo: A/C 50100218476309 IFSC HDFC0001937 '
                 '(Name: AP Power Collection) turant.'),
                ('CASE-2026-1001', 'system',
                 'Honeypot Trigger: Scammer secondary mule account and IFSC successfully trapped.'),
            ]
            conn.executemany(
                """
                INSERT INTO messages (case_id, sender_role, message_text)
                VALUES (?, ?, ?)
                """,
                sample_messages
            )
            
            conn.execute(
                """
                INSERT INTO canary_logs (case_id, trap_code, ip_address, device_os, browser_ua)
                VALUES ('CASE-2026-1001', 'TRAP-EL-991', '103.60.44.19', 'Android 13 (Redmi Note 11)', 'Chrome Mobile 122.0.6261.94')
                """
            )
            conn.commit()

def get_scam_summary() -> Dict[str, Any]:
    """Returns high level statistics for the Scam Radar and Dashboard."""
    with get_db_connection() as conn:
        total_identifiers = conn.execute("SELECT COUNT(*) FROM scam_identifiers").fetchone()[0]
        total_reports = conn.execute("SELECT SUM(reports_count) FROM scam_identifiers").fetchone()[0] or 0
        total_cases = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        resolved_cases = conn.execute("SELECT COUNT(*) FROM cases WHERE status = 'RESOLVED'").fetchone()[0]
        
        # Category breakdown
        category_rows = conn.execute(
            """
            SELECT scam_category, COUNT(*) as count, SUM(reports_count) as total_reports
            FROM scam_identifiers
            GROUP BY scam_category
            ORDER BY count DESC
            """
        ).fetchall()
        
        # Recent Blacklisted Items
        blacklist_rows = conn.execute(
            """
            SELECT id, identifier_value, identifier_type, scam_category, risk_score, reports_count, last_seen
            FROM scam_identifiers
            ORDER BY last_seen DESC
            LIMIT 15
            """
        ).fetchall()
        
        # Latest Cases
        cases_rows = conn.execute(
            """
            SELECT c.case_id, c.scammer_phone, c.scam_category, c.status, c.created_at
            FROM cases c
            ORDER BY c.created_at DESC
            LIMIT 5
            """
        ).fetchall()

        return {
            "total_blacklisted_accounts": total_identifiers,
            "total_citizen_reports": total_reports,
            "active_traps_count": total_cases,
            "scammer_mules_neutralized": resolved_cases,
            "categories": [dict(r) for r in category_rows],
            "blacklist": [dict(r) for r in blacklist_rows],
            "recent_cases": [dict(r) for r in cases_rows]
        }

def normalize_digits(value: str, last: int = 0) -> str:
    """Strips formatting. For phone numbers we keep only the last 10 digits so
    '+91 98765 43210', '09876543210' and '9876543210' all collapse to one key."""
    digits = re.sub(r"\D", "", value or "")
    return digits[-last:] if (last and len(digits) > last) else digits


def evidence_hash(messages: List[Dict[str, Any]],
                  captures: List[Dict[str, Any]],
                  identifiers: List[Dict[str, Any]]) -> str:
    """SHA-256 over the recorded evidence bundle so the dossier can be checked
    against tampering. Recomputed on every read — never a fixed string."""
    payload = json.dumps(
        {
            "messages": [
                {"role": m.get("sender_role"), "text": m.get("message_text"),
                 "at": str(m.get("timestamp"))}
                for m in messages
            ],
            "captures": [
                {"ip": c.get("ip_address"), "os": c.get("device_os"),
                 "ua": c.get("browser_ua"), "trap": c.get("trap_code"),
                 "at": str(c.get("captured_at"))}
                for c in captures
            ],
            "identifiers": [
                {"value": i.get("value"), "type": i.get("type"),
                 "blacklisted": i.get("blacklisted")}
                for i in identifiers
            ],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_case_evidence(case_id: str) -> Dict[str, Any]:
    """Returns everything actually recorded for a case: transcript, canary
    captures (real request metadata), and any identifiers cross-referenced
    from the live scam blacklist. Nothing here is hard-coded.

    A case may live in either table:
      * `cases` + `messages`   — Tab 1 handover / Mode 1 co-pilot seeds
      * `cloud_sessions` + `cloud_messages` — Mode 2 honeypot sessions
    Both are read transparently; cloud turns with role 'ai' are presented as
    'ai_decoy' so the evidence UI has one consistent vocabulary."""
    from backend.services.extractor import extract_entities

    with get_db_connection() as conn:
        case_row = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        cloud_row = None
        if case_row is None:
            cloud_row = conn.execute(
                "SELECT * FROM cloud_sessions WHERE case_id = ?", (case_id,)
            ).fetchone()

        if case_row is not None:
            msgs = conn.execute(
                "SELECT id, sender_role, message_text, timestamp FROM messages "
                "WHERE case_id = ? ORDER BY id ASC",
                (case_id,),
            ).fetchall()
        elif cloud_row is not None:
            msgs = conn.execute(
                "SELECT id, sender_role, message_text, timestamp FROM cloud_messages "
                "WHERE case_id = ? ORDER BY id ASC",
                (case_id,),
            ).fetchall()
        else:
            msgs = []

        canary_rows = conn.execute(
            "SELECT trap_code, ip_address, device_os, browser_ua, captured_at "
            "FROM canary_logs WHERE case_id = ? ORDER BY id DESC",
            (case_id,),
        ).fetchall()

        # Mined identifiers (Mode 2 honeypot writes here on every turn).
        mined_rows = conn.execute(
            "SELECT detail_type, detail_value FROM extracted_details "
            "WHERE case_id = ? ORDER BY id ASC",
            (case_id,),
        ).fetchall()

    messages = []
    for r in msgs:
        d = dict(r)
        # Normalise cloud role vocabulary for the evidence UI.
        if d.get("sender_role") == "ai":
            d["sender_role"] = "ai_decoy"
        messages.append(d)
    canary = [dict(r) for r in canary_rows]
    mined = [(r["detail_type"], r["detail_value"]) for r in mined_rows]

    # Derive identifiers from the real transcript + case phone + mined details.
    transcript = "\n".join(m["message_text"] for m in messages)
    if case_row is not None:
        anchor_phone = case_row["scammer_phone"]
        source_text = " ".join(filter(None, [transcript, anchor_phone or ""]))
    elif cloud_row is not None:
        anchor_phone = cloud_row["scammer_phone"]
        source_text = " ".join(filter(None, [transcript, anchor_phone or ""]))
    else:
        anchor_phone = None
        source_text = transcript
    entities = extract_entities(source_text) if source_text.strip() else {}

    def _match(value: str, match_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            if match_type:
                row = conn.execute(
                    "SELECT * FROM scam_identifiers WHERE LOWER(identifier_value) = ? AND identifier_type = ?",
                    (value.lower(), match_type),
                ).fetchone()
                if row:
                    return dict(row)
            else:
                row = conn.execute(
                    "SELECT * FROM scam_identifiers WHERE LOWER(identifier_value) = ?",
                    (value.lower(),),
                ).fetchone()
                if row:
                    return dict(row)

            # Compare digit-only forms: "+91 98765 43210" vs "9876543210".
            if match_type == "PHONE":
                target = normalize_digits(value, last=10)
                if len(target) == 10:
                    candidates = conn.execute(
                        "SELECT * FROM scam_identifiers WHERE identifier_type = 'PHONE'"
                    ).fetchall()
                    for cand in candidates:
                        if normalize_digits(cand["identifier_value"], last=10) == target:
                            return dict(cand)
            elif match_type == "BANK_AC":
                target = normalize_digits(value)
                if len(target) >= 9:
                    candidates = conn.execute(
                        "SELECT * FROM scam_identifiers WHERE identifier_type IN ('BANK_AC', 'IFSC')"
                    ).fetchall()
                    for cand in candidates:
                        if normalize_digits(cand["identifier_value"]) == target:
                            return dict(cand)
            elif match_type:
                row = conn.execute(
                    "SELECT * FROM scam_identifiers WHERE ? LIKE '%' || identifier_value || '%'",
                    (value,),
                ).fetchone()
                if row:
                    return dict(row)
        return None

    identifiers = []
    seen = set()

    def _push(value: str, match_type: str, label: str) -> None:
        if not value:
            return
        # "+91 98765 43210" and "9876543210" are the same number.
        if match_type == "PHONE":
            key = normalize_digits(value, last=10)
        elif match_type == "BANK_AC":
            key = normalize_digits(value)
        else:
            key = value.lower()
        if not key or key in seen:
            return
        seen.add(key)
        record = _match(value, match_type)
        identifiers.append({
            "value": value,
            "type": match_type,
            "label": label,
            "blacklisted": record is not None,
            "risk_score": record["risk_score"] if record else None,
            "scam_category": record["scam_category"] if record else None,
            "reports_count": record["reports_count"] if record else None,
        })

    if anchor_phone:
        _push(anchor_phone, "PHONE", "Scammer phone number")
    for upi in entities.get("upis", []):
        _push(upi, "UPI", "Primary UPI handle")
    for phone in entities.get("phones", []):
        _push(phone, "PHONE", "Phone number in transcript")
    for bank in entities.get("bank_accounts", []):
        _push(bank, "BANK_AC", "Backup bank account")
    for ifsc in entities.get("ifsc_codes", []):
        _push(ifsc, "IFSC", "IFSC code")
    # Identifiers the honeypot mined out of the scammer's own turns.
    _TYPE_MAP = {"upi": "UPI", "phone": "PHONE", "bank": "BANK_AC",
                 "bank_ac": "BANK_AC", "ifsc": "IFSC", "account": "BANK_AC"}
    _LABEL = {"UPI": "Mined UPI handle", "PHONE": "Mined phone number",
              "BANK_AC": "Mined bank account", "IFSC": "Mined IFSC code"}
    for detail_type, detail_value in mined:
        mt = _TYPE_MAP.get((detail_type or "").strip().lower())
        if mt and detail_value:
            _push(detail_value, mt, _LABEL.get(mt, "Mined identifier"))

    # Status / category / phone come from whichever table held the case.
    if case_row is not None:
        status = case_row["status"]
        category = case_row["scam_category"]
        created_at = case_row["created_at"]
        source_table = "cases"
    elif cloud_row is not None:
        status = cloud_row["status"]
        category = cloud_row["scam_category"]
        created_at = cloud_row["created_at"]
        source_table = "cloud_sessions"
    else:
        status = "NOT_FOUND"
        category = "Unknown"
        created_at = None
        source_table = None

    return {
        "case_id": case_id,
        "status": status,
        "scam_category": category,
        "scammer_phone": anchor_phone,
        "created_at": created_at,
        "source_table": source_table,
        "messages": messages,
        "identifiers": identifiers,
        "canary_captures": canary,
        "capture_count": len(canary),
        "latest_capture": canary[0] if canary else None,
        "evidence_hash": evidence_hash(messages, canary, identifiers),
    }


def lookup_identifier(query: str) -> Optional[Dict[str, Any]]:
    """Finds exact or partial match for an identifier."""
    clean_query = query.strip().lower()
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM scam_identifiers 
            WHERE LOWER(identifier_value) = ?
            """,
            (clean_query,)
        ).fetchone()
        
        if row:
            return dict(row)
        return None


def upsert_identifier(value: str,
                      match_type: str,
                      label: str = "",
                      category: str = "General Suspicious",
                      score: int = 70,
                      reports: int = 1) -> bool:
    """Crowd-sourced contribution: adds one identifier to the local blacklist.

    Called by the OSINT engine (spec §3, Layer 5) once a probe crosses the
    confidence threshold, so the community registry grows from real checks.
    Returns True when a row was written.
    """
    if not value:
        return False

    if match_type == "PHONE":
        key = normalize_digits(value, last=10)
    elif match_type == "BANK_AC":
        key = normalize_digits(value)
    else:
        key = str(value).strip()
    if not key:
        return False

    score = max(0, min(100, int(score or 0)))
    try:
        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO scam_identifiers
                       (identifier_value, identifier_type, scam_category, risk_score, reports_count)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(identifier_value) DO UPDATE SET
                       scam_category = excluded.scam_category,
                       risk_score = MAX(risk_score, excluded.risk_score),
                       reports_count = reports_count + excluded.reports_count,
                       last_seen = CURRENT_TIMESTAMP""",
                (key, match_type, category, score, reports),
            )
            conn.commit()
        return True
    except Exception:
        return False


def record_investigation_audit(row: Dict[str, Any]) -> bool:
    """Writes one row to `investigation_audits` (spec §6 audit trail)."""
    if not row:
        return False
    try:
        with get_db_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO investigation_audits
                   (investigation_id, case_id, input_type, input_sha256, client_ip,
                    prompt_injection_detected, is_scammer_probing, rate_limited,
                    risk_score, threat_level, scam_category, upserted_count,
                    model_source, log_path, json_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row.get("investigation_id"),
                    row.get("case_id"),
                    row.get("input_type", "TEXT"),
                    row.get("input_sha256", ""),
                    row.get("client_ip"),
                    1 if row.get("prompt_injection_detected") else 0,
                    1 if row.get("is_scammer_probing") else 0,
                    1 if row.get("rate_limited") else 0,
                    int(row.get("risk_score") or 0),
                    row.get("threat_level"),
                    row.get("scam_category"),
                    int(row.get("upserted_count") or 0),
                    row.get("model_source"),
                    row.get("log_path"),
                    row.get("json_path"),
                ),
            )
            conn.commit()
        return True
    except Exception:
        return False
