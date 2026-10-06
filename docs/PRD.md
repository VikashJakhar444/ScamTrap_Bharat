# ScamTrap Bharat - Product Requirements Document (PRD)

## 1. Executive Summary & Vision
**ScamTrap Bharat** is India's first active, pre-fraud cyber safety platform and citizen co-pilot. Built for the **Hack for Social Cause (Mentored by IIT Bombay)** track on the MY Bharat Portal, it fundamentally reimagines digital fraud defense for Indian citizens.

### 1.1 The Core Problem & Gap
India loses thousands of crores annually to WhatsApp/SMS cyber frauds (Electricity Bill disconnection notices, Fake Bank KYC, Fake Police Digital Arrests, Work-From-Home Task scams). Existing interventions are strictly **passive and post-fraud**:
- **Truecaller / Spam Blockers:** Only label numbers after thousands have already been targeted.
- **Sanchar Saathi (Chakshu):** Only revokes SIM cards weeks after reports are filed.
- **National Cyber Crime Helpline (1930):** Only initiated AFTER a victim has lost money and accounts are drained.

### 1.2 The ScamTrap Bharat Solution (Core USP)
**Active Pre-Fraud Intelligence & Counter-Baiting Engine**:
Instead of waiting for citizens to lose money, ScamTrap Bharat extracts scammers' financial supply chain (**Primary and Backup Mule UPI IDs, Bank Accounts, IFSC codes, Device OS, and IP footprints**) *before* any money is transferred.

---

## 2. Two Safe Operational Modes

### Mode A: Citizen Co-Pilot & Scam Checker (Web Portal)
- **Instant Risk Assessment:** Citizens search UPI IDs, phone numbers, or paste whole Hindi/English WhatsApp messages.
- **Intelligent Keyword & Threat Heuristics:** Matches known scam registries and detects fraud patterns (urgent electricity disconnection, KYC deactivation threats, part-time job lures).
- **Active Counter-Bait Generator:** Generates a realistic "UPI Daily Limit Reached" error receipt along with an authentic-looking verification link. When given to the scammer, it induces the scammer to reveal their **secondary bank account or alternate mule UPI ID** while logging their device metadata in a safe sandbox.

### Mode B: Live 2-Phone Autonomous Honeypot Node
- **Autonomous WhatsApp Engagement:** Runs on a dedicated honeypot node connected via WhatsApp Web bridge.
- **Natural Hinglish AI Persona ("Vikas Ji" / Confused Citizen):** Engages scammers realistically, acting naive and eager to pay, stringing them along to waste their operational time while systematically extracting payment handles.
- **Zero Real Transfers:** All transactions and validations are simulated in a 100% isolated local sandbox (`storage/scamtrap.db`).

---

## 3. Key Target User Personas
1. **The Everyday Indian Citizen:** Wants a simple, 0-jargon tool in English or Hindi to verify if a message is genuine or dangerous.
2. **Cyber Defense & Law Enforcement Volunteers (1930 / I4C / Citizen Police):** Needs structured, downloadable PDF evidence dossiers containing verifiable scammer bank accounts and digital audit trails to freeze mule accounts rapidly.

---

## 4. Key Functional Modules

| Module | Purpose | Status in Step 1 |
|---|---|---|
| **Scam Checker & Search** | Checks identifiers & parses suspicious message texts | Core Implementation |
| **Bharat Scam Radar** | Public blacklist & real-time analytics with comparative matrix | Core Implementation |
| **Citizen Co-Pilot Bait Engine** | Generates synthetic UPI error proof & Canary trap | Scaffolded / Service Ready |
| **Honeypot Chat Bridge** | Web WhatsApp session management & automated replies | Scaffolded / Service Ready |
| **Scammer Dossier Generator** | Formats 1930-ready evidence PDF dossiers | Scaffolded / Service Ready |

---

## 5. Security & Privacy Guarantees
- **100% Local Safe Sandbox:** Data is saved locally in SQLite (`storage/scamtrap.db`).
- **No External Bank/Gov API Calls:** Strictly safe simulations to guarantee compliance and user privacy.
- **No Technical Jargon:** Clean, accessible terminology with a 1-click English/हिंदी toggle.
