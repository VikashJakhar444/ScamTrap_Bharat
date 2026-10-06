# ScamTrap Bharat - System Architecture & Technical Design

## 1. System Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                        CITIZEN & HONEYPOT FRONTEND (PORT 8050)                   |
|  - Tab 1: Scam Checker & Co-Pilot (Search UPI / Phone / Paste WhatsApp Text)    |
|  - Tab 2: Live WhatsApp Honeypot (2-Phone Autonomous Node & Chat Console)       |
|  - Tab 3: Scammer Proof & Police PDF (Mule Bank Accounts, UPIs, Device Logs)    |
|  - Tab 4: Bharat Scam Radar (Analytics, Blacklist Table & Solution Matrix)     |
+----------------------------------------+----------------------------------------+
                                         | REST / JSON
                                         v
+---------------------------------------------------------------------------------+
|                        FASTAPI CORE ENGINE (BACKEND)                            |
|                                                                                 |
|   [Routes Layer]                                                                |
|   ├── /api/health               -> System status & sandbox mode check           |
|   ├── /api/checker/lookup       -> Scam identifier & text regex/NLP checker    |
|   ├── /api/co_pilot/*           -> Counter-bait generation & decoy links        |
|   ├── /api/honeypot/*           -> Autonomous AI chat & session status          |
|   └── /api/reports/*            -> Live statistics, blacklist & PDF export      |
|                                                                                 |
|   [Services Layer]                                                              |
|   ├── extractor.py              -> Regex & NLP entity extraction (UPI, Phone)  |
|   ├── llm_engine.py             -> Gemini Hinglish Decoy conversation logic     |
|   ├── image_bait.py             -> Synthetic "UPI Daily Limit Error" generator  |
|   └── pdf_dossier.py            -> Cyber Cell Formatted 1930 PDF Dossier        |
+----------------------------------------+----------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                        LOCAL SAFE SANDBOX & STORAGE                             |
|                                                                                 |
|   ├── storage/scamtrap.db (SQLite)                                              |
|   │   ├── scam_identifiers (Mule UPI, Scammer Phone, Bank A/C, IFSC)           |
|   │   ├── cases (Investigation Cases & Session Tracking)                       |
|   │   ├── messages (Transcript between Scammer & Decoy)                         |
|   │   └── canary_logs (Captured scammer IP, Device OS, User-Agent)             |
|   ├── storage/generated_baits/ (Synthetic screenshot images)                   |
|   └── storage/generated_pdfs/  (Citizen & Police Evidence PDF files)           |
+---------------------------------------------------------------------------------+
```

---

## 2. Core Comparison Matrix: Why ScamTrap Bharat is Different

| Feature / Dimension | Truecaller / Call Blockers | Sanchar Saathi (Chakshu) | **ScamTrap Bharat (Active Co-Pilot)** |
|---|---|---|---|
| **Action Stage** | Reactive (After spam reports) | Reactive (SIM block after days) | **Active Pre-Fraud (Before ₹1 is lost)** |
| **Data Extracted** | Phone numbers only | Phone number / IMEI | **Primary & Backup Mule UPI IDs, Bank Accounts, IFSC, IP & Device OS** |
| **Mule Account Trapping** | ❌ No | ❌ No | **✅ Yes (Induces scammer to give secondary accounts)** |
| **Citizen Co-Pilot Mode** | ❌ No | ❌ No | **✅ Yes (Generates safe screenshot baits & links)** |
| **Autonomous Honeypot** | ❌ No | ❌ No | **✅ Yes (Hinglish AI persona wastes scammer time)** |
| **1930 / Police Ready Evidence** | ❌ No | ⚠️ Partial | **✅ Yes (Automated Cyber Cell Dossier PDF)** |
| **Data Privacy** | Sells / Cloud syncs contacts | Centralized Govt Servers | **100% Local Safe Sandbox Engine** |

---

## 3. Database Schema Design (SQLite: `storage/scamtrap.db`)

1. **`scam_identifiers`**:
   - `id` INTEGER PRIMARY KEY AUTOINCREMENT
   - `identifier_value` TEXT UNIQUE NOT NULL (e.g. `bijli.board.pay@ybl`, `9876543210`)
   - `identifier_type` TEXT NOT NULL (`UPI`, `PHONE`, `BANK_AC`, `IFSC`)
   - `scam_category` TEXT NOT NULL (`Electricity Bill`, `Bank KYC`, `Job Scam`, etc.)
   - `risk_score` INTEGER NOT NULL (0 to 100)
   - `reports_count` INTEGER DEFAULT 1
   - `first_seen` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   - `last_seen` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

2. **`cases`**:
   - `case_id` TEXT PRIMARY KEY (e.g. `CASE-2026-1001`)
   - `scammer_phone` TEXT NOT NULL
   - `scam_category` TEXT NOT NULL
   - `status` TEXT NOT NULL (`STANDBY`, `TRAP_ACTIVE`, `RESOLVED`)
   - `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

3. **`messages`**:
   - `id` INTEGER PRIMARY KEY AUTOINCREMENT
   - `case_id` TEXT NOT NULL REFERENCES `cases(case_id)`
   - `sender_role` TEXT NOT NULL (`scammer`, `ai_decoy`, `system`)
   - `message_text` TEXT NOT NULL
   - `media_path` TEXT
   - `trap_url` TEXT
   - `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

4. **`canary_logs`**:
   - `id` INTEGER PRIMARY KEY AUTOINCREMENT
   - `case_id` TEXT NOT NULL
   - `trap_code` TEXT NOT NULL
   - `ip_address` TEXT NOT NULL
   - `device_os` TEXT NOT NULL
   - `browser_ua` TEXT NOT NULL
   - `captured_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
