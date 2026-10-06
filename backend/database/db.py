import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import DB_PATH

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds initial data if empty."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with get_db_connection() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        
        # Check if scam_identifiers table has records
        cursor = conn.execute("SELECT COUNT(*) FROM scam_identifiers")
        count = cursor.fetchone()[0]
        
        if count == 0:
            initial_seeds = [
                ("bijli.board.pay@ybl", "UPI", "Electricity Bill", 98, 42),
                ("9876543210", "PHONE", "Bank KYC", 94, 87),
                ("sbi.kyc.update@okaxis", "UPI", "Bank KYC", 99, 115),
                ("SBIN0004821", "IFSC", "Fake Loan", 88, 19),
                ("9123456780", "PHONE", "Job Scam", 91, 53),
                ("50200084729104", "BANK_AC", "Part-Time Task", 96, 64)
            ]
            conn.executemany(
                """
                INSERT INTO scam_identifiers 
                (identifier_value, identifier_type, scam_category, risk_score, reports_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                initial_seeds
            )
            
            # Also seed a sample resolved case for the police dossier tab
            conn.execute(
                """
                INSERT OR IGNORE INTO cases (case_id, scammer_phone, scam_category, status)
                VALUES ('CASE-2026-1001', '+91 98765 43210', 'Electricity Bill Disconnection', 'RESOLVED')
                """
            )
            
            sample_messages = [
                ('CASE-2026-1001', 'scammer', 'Dear Consumer, Your Electricity power will be disconnected tonight 9:30 PM from power office because your previous month bill was not updated. Please immediately contact our officer at 9876543210.'),
                ('CASE-2026-1001', 'ai_decoy', 'Sir please mat kaato light! Bachhe padh rahe hain. Kahan pay karna hai batayein?'),
                ('CASE-2026-1001', 'scammer', 'Pay Rs 45 immediately on our official power UPI: bijli.board.pay@ybl or bill will not update.'),
                ('CASE-2026-1001', 'ai_decoy', 'Sir maine try kiya par UPI Daily Limit Reached error aa raha hai. Dekhiye screenshot. Koi alternate account number ya secondary UPI do jaldi?'),
                ('CASE-2026-1001', 'scammer', 'Theek hai is backup account pe transfer karo: A/C 50200084729104 IFSC SBIN0004821 (Name: Bijli Collection Unit) turant.'),
                ('CASE-2026-1001', 'system', 'Honeypot Trigger: Scammer secondary mule account and IFSC successfully trapped.')
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
                VALUES ('CASE-2026-1001', 'TRAP-EL-991', '103.21.144.62 (Kolkata/Jamtara Region)', 'Android 13 (Redmi Note 11)', 'Chrome Mobile 122.0.6261.94')
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
