# 🛡️ ScamTrap Bharat - Citizen Cyber Safety & Active Scam Account Hunter

> **Submission for "Hack for Social Cause (Mentored by IIT Bombay)" — MY Bharat Portal**  
> *Active Pre-Fraud Honeypot & Citizen Co-Pilot Platform*

---

## 🌟 1. The Core Problem & Our USP

India loses thousands of crores annually to digital cyber frauds (Electricity bill disconnection notices, Bank KYC freeze threats, Fake CBI digital arrests, and Work-From-Home task scams).

### 🚨 Why Existing Tools Fail:
- **Truecaller:** Reactive spam tagging only after thousands have already been defrauded.
- **Sanchar Saathi (Chakshu):** Takes days/weeks to revoke SIMs after manual review.
- **1930 Cyber Crime Helpline:** Initiated only **AFTER** money is drained from victim bank accounts.

### 🛡️ The ScamTrap Bharat Solution:
**ScamTrap Bharat** is India's first active **Pre-Fraud Interception Engine**. Instead of waiting for money to be lost:
1. **Citizen Co-Pilot:** Generates realistic **"NPCI U16 UPI Daily Limit Exceeded"** counter-bait error receipts to induce scammers into revealing their **secondary backup bank accounts, IFSC codes, and beneficiary names**.
2. **Autonomous 2-Phone WhatsApp Honeypot:** Connects a dedicated WhatsApp node running a natural Hinglish AI persona ("Vikas Ji") that wastes scammers' operational time and safely traps their financial supply chain.
3. **1-Click 1930 / BSA Sec 63 Evidence Dossier:** Generates official, standardized Cyber Cell PDF evidence reports with SHA-256 integrity hashes for rapid freezing of mule accounts.
4. **100% Local Safe Sandbox:** Zero data is sent to external bank or government servers.

---

## 🏗️ 2. Project Architecture

```
ScamTrap-Bharat/
├── backend/               # FastAPI core engine & routes
│   ├── database/          # SQLite schema & seed manager
│   ├── routes/            # Checker, Co-Pilot, Honeypot & Reports
│   └── services/          # Entity extraction, LLM Decoy, Pillow Bait & ReportLab PDF
├── frontend/              # 4-Tab Citizen Web Portal
│   ├── assets/css/        # Public utility design system (Plus Jakarta Sans)
│   ├── js/                # App logic & 1-click English/Hindi i18n toggle
│   ├── index.html         # Main 4-Tab application
│   └── verify_receipt.html # Safe Canary decoy landing page
├── docs/                  # PRD & Technical Architecture specifications
├── storage/               # Local SQLite DB & generated evidence artifacts
└── wa_bridge/             # Node.js WhatsApp Web 2-Phone honeypot bridge
```

---

## 🚀 3. Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ (Optional, for real WhatsApp 2-Phone link)

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start the Local FastAPI Backend Server
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8050 --reload
```

### Step 3: Open the Web Portal
Open your browser and navigate to:
👉 **`http://localhost:8050`**

---

## 📱 4. Four Core Operational Tabs

| Tab | Feature | Description |
|---|---|---|
| **Tab 1** | **🔍 Check a Scam & Co-Pilot** | Search any UPI/phone or paste WhatsApp text. Generates realistic fake UPI limit screenshots. |
| **Tab 2** | **🤖 Live WhatsApp Honeypot** | Autonomous 2-Phone WhatsApp Node with live Hinglish conversation console. |
| **Tab 3** | **📄 Scammer Proof & Police PDF** | Visualized trapped accounts, device OS & IP logs, and 1-Click 1930 PDF export. |
| **Tab 4** | **📊 Bharat Scam Radar** | Real-time database analytics and comparison matrix vs Truecaller / Sanchar Saathi. |

---

## ⚖️ 5. Ethics & Safety Compliance
- All simulations run locally in `storage/scamtrap.db`.
- No live funds are ever transferred.
- 1-click **English / हिंदी** toggle for universal accessibility across India.

---

## 🧪 6. Running Tests

Smoke tests cover the core API endpoints (health, scam analysis, identifier lookup, reports, honeypot).

```bash
# Start the backend first (see Quick Start), then:
pytest tests/ -v
```

---

## 🤖 7. AI Disclosure (HSC Requirement)

Per HSC 2027 guidelines, we disclose all AI tool usage:

| Component | AI Used? | Details |
|---|---|---|
| **Scam Detection (Tab 1)** | No | Deterministic rules-engine — keyword/pattern matching, risk scoring. No LLM involved. |
| **Decoy Conversation (Tab 2)** | Yes | Offline LLM via **Ollama** (deepseek-r1 / llama3 / phi3) generates Hinglish scammer replies. Cloud fallback (Groq/Gemini) is optional and disabled by default. |
| **Image OCR / QR decode** | Yes | Gemini vision (optional). Offline QR decode via OpenCV fallback. |
| **Audio transcription** | Yes | Gemini speech-to-text (optional). Graceful degradation when unavailable. |
| **Evidence PDF (Tab 3)** | No | Template-based ReportLab generation. No AI. |
| **Trends dashboard (Tab 4)** | No | Static official government data (MHA/NCRP/IC3). No AI. |

**Proportion of AI-assisted work:** ~15% (decoy conversation engine only). All detection logic, evidence generation, and data analytics are deterministic and offline-capable.

**No user data is ever sent to third-party AI services** when running in offline mode (default).

---

## 📄 8. License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.
