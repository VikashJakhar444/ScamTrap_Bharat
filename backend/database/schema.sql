-- ScamTrap Bharat Database Schema (SQLite)

CREATE TABLE IF NOT EXISTS scam_identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier_value TEXT UNIQUE NOT NULL,
    identifier_type TEXT NOT NULL CHECK (identifier_type IN ('UPI', 'PHONE', 'BANK_AC', 'IFSC')),
    scam_category TEXT NOT NULL,
    risk_score INTEGER NOT NULL DEFAULT 85,
    reports_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    scammer_phone TEXT NOT NULL,
    scam_category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'STANDBY' CHECK (status IN ('STANDBY', 'TRAP_ACTIVE', 'RESOLVED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    sender_role TEXT NOT NULL CHECK (sender_role IN ('scammer', 'ai_decoy', 'system')),
    message_text TEXT NOT NULL,
    media_path TEXT,
    trap_url TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS canary_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    trap_code TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    device_os TEXT NOT NULL,
    browser_ua TEXT NOT NULL,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Per-investigation audit trail (one row per Tab 1 check/search).
CREATE TABLE IF NOT EXISTS investigation_audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id TEXT UNIQUE NOT NULL,
    case_id TEXT,
    input_type TEXT NOT NULL CHECK (input_type IN (
        'TEXT', 'IMAGE_OCR', 'VOICE_AUDIO', 'QR_CODE', 'IDENTIFIER_LOOKUP'
    )),
    input_sha256 TEXT NOT NULL,
    client_ip TEXT,
    prompt_injection_detected INTEGER NOT NULL DEFAULT 0,
    is_scammer_probing INTEGER NOT NULL DEFAULT 0,
    rate_limited INTEGER NOT NULL DEFAULT 0,
    risk_score INTEGER NOT NULL DEFAULT 0,
    threat_level TEXT,
    scam_category TEXT,
    upserted_count INTEGER NOT NULL DEFAULT 0,
    model_source TEXT,
    log_path TEXT,
    json_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_identifier_val ON scam_identifiers (identifier_value);
CREATE INDEX IF NOT EXISTS idx_messages_case ON messages (case_id);
CREATE INDEX IF NOT EXISTS idx_canary_case ON canary_logs (case_id);
