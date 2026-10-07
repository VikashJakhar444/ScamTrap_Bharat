import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

# ──────────────────────────────────────────────────────────────────────────────
# Regex patterns for Indian cyber fraud vectors
# ──────────────────────────────────────────────────────────────────────────────
UPI_PATTERN = re.compile(
    r'[\w\.\-]+@(?:okhdfcbank|okaxis|okicici|oksbi|ybl|ibl|axl|paytm|apl|barodampay|'
    r'upi|postbank|unionbank|idfcbank|sbi|icici|hdfcbank|ptaxis|ptyes|pthdfc|ptsbi|'
    r'yapl|pnp|ibbl|fbl|payzapp|okbank|blax|apl)',
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r'(?:(?:\+91|91|0)?[ -]?)?([6-9]\d{9})\b')
IFSC_PATTERN = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', re.IGNORECASE)
BANK_AC_PATTERN = re.compile(r'\b\d{9,18}\b')
QR_PAYLOAD_PATTERN = re.compile(r'upi://pay\?[^\s"\'<>]+', re.IGNORECASE)
URL_PATTERN = re.compile(r'https?://[^\s"\'<>()]+', re.IGNORECASE)

# Known NPCI / PSP UPI suffixes — used to spot obfuscated handles.
UPI_SUFFIXES = {
    "ybl", "ibl", "axl", "okaxis", "okhdfcbank", "okicici", "oksbi", "paytm",
    "apl", "barodampay", "upi", "postbank", "unionbank", "idfcbank", "sbi",
    "icici", "hdfcbank", "ptaxis", "ptyes", "pthdfc", "ptsbi", "yapl", "pnp",
    "ibbl", "fbl", "payzapp", "okbank", "blax", "jio", "freecharge",
}

# Remote-access / sideloading tooling we treat as malware indicators.
MALWARE_APPS = [
    "anydesk", "teamviewer", "rustdesk", "quicksupport", "quick support",
    "ultraview", "ammyy", "logmein", "vnc", "radmin", "screen share",
    "screenshare", "screen-share", "remote desktop", "remote support",
]
APK_PATTERN = re.compile(r'[\w\.\-]+\.apk\b', re.IGNORECASE)

# Institutional senders that NEVER collect money on a personal UPI handle.
AUTHORITY_CLAIMS = [
    ("electricity", ["electricity", "bijli", "vidyut", "discom", "bescom", "msedcl",
                     "power board", "substation", "meter reader"]),
    ("bank", ["kyc", "bank", "sbi", "hdfc", "icici", "axis", "pnb", "bob",
              "netbanking", "debit card", "credit card", "ifsc"]),
    ("police", ["police", "cbi", "ed ", "cyber cell", "narcotics", "customs",
                "court", "digital arrest", "arrest warrant"]),
    ("government", ["government", "govt", "rbi", "uidai", "aadhaar", "pan card",
                    "pm kisan", "income tax", "passport", "municipal"]),
    ("college", ["college", "university", "principal", "dean", "registrar",
                 "hostel", "semester", "lab"]),
    ("hospital", ["hospital", "clinic", "doctor", "icu", "operation", "patient"]),
    ("courier", ["courier", "fedex", "dhl", "bluedart", "india post", "parcel",
                 "custom clearance"]),
    ("lender", ["loan", "lender", "nbfc", "bajaj", "moneyview", "credit line",
                "instant credit", "loan approved"]),
]

# ──────────────────────────────────────────────────────────────────────────────
# De-obfuscation — scammers deliberately break identifiers to dodge regexes
# ──────────────────────────────────────────────────────────────────────────────
# "bijli.pay [at] ybl" / "pay (at) okaxis" / "x {at} paytm" / "x \" at \" ybl"
_AT_BRACKET = re.compile(r'([\w\.\-]+)\s*[\[\({]\s*at\s*[\]\)}]\s*([\w\.\-]+)', re.IGNORECASE)
_AT_QUOTED = re.compile(r'([\w\.\-]+)\s*["\'`]\s*at\s*["\'`]\s*([\w\.\-]+)', re.IGNORECASE)
_AT_BARE = re.compile(r'([\w\.\-]+)\s+at\s+([\w\.\-]+)', re.IGNORECASE)

# A phone may be split as 98.765.43210 | 98765 - 43210 | +91 (987) 654-3210
_PHONE_CANDIDATE = re.compile(r'(?<!\d)(?:\+?\d{1,3}[\s.\-]?)?[\d][\d\s.\-()]{6,26}\d(?!\d)')

# A bank credit alert that never actually came from a bank header.
_FAKE_CREDIT = re.compile(
    r'(?:a/c|account|acct)\s*(?:no\.?|number)?\s*[\w*]{2,}\s*'
    r'(?:is\s+)?credited\s+with|credited\s+with\s+(?:inr|rs\.?|₹)\s*[\d,]+|'
    r'galti\s+se\s+paise\s+chale\s+gaye|money\s+sent\s+by\s+mistake|'
    r'received\s+(?:inr|rs\.?|₹)\s*[\d,]+\s+in\s+your\s+account',
    re.IGNORECASE,
)
_TRAI_HEADER = re.compile(r'\b[A-Z]{2}-[A-Z0-9]{6,}\b')       # AD-SBIINB, VM-HDFCBK
_CONTACT_URGENCY = re.compile(
    r'\b(?:contact|call|whatsapp|telephon)\w*\b.{0,60}\b(?:before|urgently|immediately|now|jaldi|turant)\b',
    re.IGNORECASE | re.DOTALL,
)


def _fix_upi_at(text: str) -> str:
    """Rebuilds `@` that scammers replaced with [at] / (at) / {at} / 'at'.

    The bare-`at` form is only rewritten when the right-hand token is a real
    PSP suffix, so ordinary prose like "available at the office" is untouched.
    """
    text = _AT_BRACKET.sub(lambda m: f"{m.group(1)}@{m.group(2)}", text)
    text = _AT_QUOTED.sub(lambda m: f"{m.group(1)}@{m.group(2)}", text)

    def _bare(m: re.Match) -> str:
        if m.group(2).lower().strip(".") in UPI_SUFFIXES:
            return f"{m.group(1)}@{m.group(2)}"
        return m.group(0)

    return _AT_BARE.sub(_bare, text)


def deobfuscate(text: str) -> str:
    """Returns the cleaned text with hidden identifiers reconstructed."""
    if not text:
        return ""
    cleaned = text.replace("\u200b", "").replace("\ufeff", "")
    cleaned = _fix_upi_at(cleaned)
    return cleaned


def reconstruct_phones(text: str) -> List[str]:
    """Pulls 10-digit Indian mobiles out of dotted / dashed / bracketed runs."""
    found: List[str] = []
    for match in _PHONE_CANDIDATE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) in (11, 12) and digits[:2] in ("91", "81", "71"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in "6789" and digits not in found:
            found.append(digits)
    return found


def parse_qr_payloads(text: str) -> List[Dict[str, Any]]:
    """Decodes `upi://pay?pa=..&pn=..&am=..` payloads found in text/OCR.

    A UPI QR can ONLY debit the scanner's account — it can never receive money.
    """
    payloads: List[Dict[str, Any]] = []
    for raw in QR_PAYLOAD_PATTERN.findall(text or ""):
        try:
            parsed = urlparse(raw)
            qs = parse_qs(parsed.query)
        except Exception:
            continue
        pa = (qs.get("pa") or [""])[0]
        pn = (qs.get("pn") or [""])[0]
        am = (qs.get("am") or [""])[0]
        payloads.append({
            "raw": raw,
            "payee_vpa": pa,
            "payee_name": pn,
            "amount": am,
            "is_upi_pay": parsed.scheme.lower() == "upi",
            "deduction_only": True,
        })
    return payloads


def detect_malware_indicators(text: str) -> Dict[str, List[str]]:
    """Remote-access tooling + sideloaded APK names mentioned in the message."""
    low = (text or "").lower()
    apps = sorted({a for a in MALWARE_APPS if a in low})
    apks = sorted(set(APK_PATTERN.findall(text or "")))
    return {"remote_access_apps": apps, "apk_files": apks}


def detect_authority_on_personal_handle(upis: List[str], text: str) -> Dict[str, Any]:
    """Layer-2 core check: does the sender claim an institution while collecting
    on a personal consumer UPI handle?

    Keywords are matched on WORD BOUNDARIES — a short token like "ed" must not
    fire on the "ed" inside "disconnected".
    """
    if not upis:
        return {"claimed": [], "collecting_on": [], "contradiction": False}

    low = (text or "").lower()
    claimed = [
        label for label, kws in AUTHORITY_CLAIMS
        if any(re.search(rf"\b{re.escape(k.strip())}", low) for k in kws)
    ]
    if not claimed:
        return {"claimed": [], "collecting_on": upis, "contradiction": False}

    # Personal / consumer PSP handles are the tell-tale.
    personal = []
    for u in upis:
        suffix = u.rsplit("@", 1)[-1].lower() if "@" in u else ""
        prefix = u.split("@", 1)[0].lower() if "@" in u else ""
        if suffix in {"ybl", "ibl", "axl", "apl", "yapl", "paytm", "okaxis",
                      "okhdfcbank", "okicici", "oksbi", "pnp", "fbl", "blax"}:
            personal.append(u)
        elif "." in prefix or "_" in prefix:
            personal.append(u)

    return {
        "claimed": claimed,
        "collecting_on": personal or upis,
        "contradiction": bool(claimed and personal),
    }


def _micro_patterns(text: str, upis: List[str], phones: List[str],
                    urls: List[str]) -> Dict[str, Any]:
    """Two scam shapes that regex-only models routinely miss."""
    low = (text or "").lower()

    # (a) Fake bank credit SMS arriving from a normal personal mobile number.
    looks_credit = bool(_FAKE_CREDIT.search(text or ""))
    has_personal_sender = bool(phones)
    has_header = bool(_TRAI_HEADER.search(text or ""))
    fake_credit = looks_credit and has_personal_sender and not has_header

    # (b) First-contact bait: no link and no UPI on purpose, only a number to call.
    first_contact = (
        not upis
        and not urls
        and bool(phones)
        and bool(_CONTACT_URGENCY.search(text or ""))
    )

    return {
        "fake_bank_credit_from_personal_sim": fake_credit,
        "first_contact_bait": first_contact,
        "has_trai_header": has_header,
    }


# Threat and scam category keywords (kept for the offline fallback engine)
SCAM_KEYWORDS = {
    "Electricity Bill Disconnection": [
        "bijli", "electricity", "power will be disconnected", "power disconnect", "light disconnect",
        "power office", "bill update", "urgent bill", "officer number", "substation", "disconnect tonight",
        "bill not updated", "electric department"
    ],
    "Bank KYC & Account Block": [
        "kyc", "sbi", "hdfc", "icici", "pnb", "account blocked", "pan card", "aadhaar link",
        "sim blocked", "deactivation", "debit card block", "netbanking suspended", "update your kyc"
    ],
    "Fake Police & Digital Arrest": [
        "cbi", "police", "customs", "parcel seized", "digital arrest", "narcotics", "court order",
        "mha", "cyber cell", "arrest warrant", "trafficking", "dhl parcel", "money laundering"
    ],
    "Part-Time Job / Telegram Task": [
        "youtube like", "telegram task", "daily 3000", "daily 5000", "work from home", "earn money",
        "part time job", "hotel review", "google map review", "prepaid task", "crypto investment"
    ],
    "Fake Lottery / Loan Approval": [
        "lottery", "kbc", "winner", "loan approved", "instant loan", "zero interest loan",
        "claim prize", "congratulations won", "gift voucher"
    ]
}


def extract_entities(text: str) -> Dict[str, Any]:
    """De-obfuscates then extracts every fraud-relevant entity from `text`.

    Returns the legacy keys (upis / phones / ifsc_codes / bank_accounts /
    detected_category / matched_categories / heuristic_risk_score / reasons)
    plus qr_payloads, urls, malware_or_remote_apps and micro_pattern flags.
    """
    if not text:
        return {
            "upis": [], "phones": [], "ifsc_codes": [], "bank_accounts": [],
            "urls": [], "qr_payloads": [], "malware_or_remote_apps": {},
            "detected_category": "None", "matched_categories": [],
            "heuristic_risk_score": 0, "reasons": [],
            "micro_pattern": {}, "deobfuscated_text": "",
        }

    # ── Stage: de-obfuscate first, then run the patterns on the clean text ──
    deob = deobfuscate(text)

    found_upis = list(dict.fromkeys(UPI_PATTERN.findall(deob)))

    # Phones — reconstruct from split/dotted/bracketed runs, then fall back.
    cleaned_phones = reconstruct_phones(deob)
    if not cleaned_phones:
        cleaned_phones = list(dict.fromkeys(
            p for p in PHONE_PATTERN.findall(deob) if len(p) == 10
        ))

    found_ifsc = list(dict.fromkeys(m.upper() for m in IFSC_PATTERN.findall(deob)))

    urls = list(dict.fromkeys(URL_PATTERN.findall(deob)))

    # Bank accounts (9-18 digits) excluding phones, years and IFSC leftovers.
    phone_set = set(cleaned_phones)
    ifsc_set = {f.upper() for f in found_ifsc}
    found_accounts: List[str] = []
    for raw in BANK_AC_PATTERN.findall(deob):
        digits = raw.strip()
        if len(digits) < 9 or len(digits) > 18:
            continue
        if digits in phone_set:
            continue
        if digits.upper() in ifsc_set:
            continue
        if digits in found_accounts:
            continue
        found_accounts.append(digits)

    qr_payloads = parse_qr_payloads(deob)
    malware = detect_malware_indicators(deob)
    micro = _micro_patterns(deob, found_upis, cleaned_phones, urls)

    # Category detection
    text_lower = deob.lower()
    matched_categories = []
    for category, keywords in SCAM_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                matched_categories.append(category)
                break
    primary_category = matched_categories[0] if matched_categories else "General Suspicious"

    # ── Heuristic risk score ────────────────────────────────────────────────
    risk_score = 0
    reasons = []

    if found_upis:
        risk_score += 35
        reasons.append(f"Contains {len(found_upis)} UPI ID(s)")
    if cleaned_phones:
        risk_score += 25
        reasons.append(f"Contains {len(cleaned_phones)} Contact Phone Number(s)")
    if found_ifsc:
        risk_score += 30
        reasons.append("Contains Bank IFSC Code")
    if found_accounts:
        risk_score += 35
        reasons.append(f"Contains {len(found_accounts)} Bank Account Number(s)")
    if matched_categories:
        risk_score += 40
        reasons.append(f"Matches high-risk fraud pattern: {', '.join(matched_categories)}")
    if qr_payloads:
        risk_score += 30
        reasons.append("Contains a UPI QR / upi://pay payload (deduction-only)")
    if urls:
        risk_score += 15
        reasons.append(f"Contains {len(urls)} link(s)")
    if malware["remote_access_apps"] or malware["apk_files"]:
        risk_score += 30
        reasons.append("Mentions remote-access tooling or an APK install")
    if micro.get("fake_bank_credit_from_personal_sim"):
        risk_score += 30
        reasons.append("Bank credit alert arriving from a personal mobile number")
    if micro.get("first_contact_bait"):
        risk_score += 20
        reasons.append("No link/UPI — only an urgent callback number (first-contact bait)")

    risk_score = min(100, max(0, risk_score))

    return {
        "upis": found_upis,
        "phones": cleaned_phones,
        "ifsc_codes": found_ifsc,
        "bank_accounts": found_accounts,
        "urls": urls,
        "qr_payloads": qr_payloads,
        "malware_or_remote_apps": malware,
        "detected_category": primary_category,
        "matched_categories": matched_categories,
        "heuristic_risk_score": risk_score,
        "reasons": reasons,
        "micro_pattern": micro,
        "deobfuscated_text": deob,
    }


# Hindi labels for every category the engine or the seeded registry can emit.
CATEGORY_LABELS_HI = {
    "Electricity Bill": "बिजली बिल धोखाधड़ी",
    "Bank KYC": "बैंक KYC धोखाधड़ी",
    "Fake Loan": "नकली लोन धोखाधड़ी",
    "Job Scam": "नौकरी धोखाधड़ी",
    "Part-Time Task": "पार्ट-टाइम टास्क धोखाधड़ी",
    "Electricity Bill Disconnection": "बिजली बिल कनेक्शन कटौती धोखाधड़ी",
    "Bank KYC & Account Block": "बैंक KYC व खाता ब्लॉक धोखाधड़ी",
    "Fake Police & Digital Arrest": "नकली पुलिस व डिजिटल अरेस्ट धोखाधड़ी",
    "Part-Time Job / Telegram Task": "पार्ट-टाइम जॉब / टेलीग्राम टास्क धोखाधड़ी",
    "Fake Lottery / Loan Approval": "नकली लॉटरी / लोन स्वीकृति धोखाधड़ी",
    "General Suspicious": "सामान्य संदिग्ध गतिविधि",
    "Suspicious Alert": "संदिग्ध चेतावनी",
    "Identified Scam": "पहचाना गया स्कैम",
    "No Direct Threat Found": "कोई सीधा खतरा नहीं मिला",
    "None": "कुछ नहीं",
}


def localize_category(category: str, lang: str) -> str:
    """Maps an English category label to Hindi when requested."""
    if lang != "hi":
        return category
    return CATEGORY_LABELS_HI.get(category, category)
