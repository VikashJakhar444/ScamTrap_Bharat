import re
from typing import Dict, List, Any

# Regex patterns for Indian cyber fraud vectors
UPI_PATTERN = re.compile(r'[\w\.\-]+@(?:okhdfcbank|okaxis|okicici|oksbi|ybl|ibl|axl|paytm|apl|barodampay|upi|postbank|unionbank|idfcbank)', re.IGNORECASE)
PHONE_PATTERN = re.compile(r'(?:(?:\+91|91|0)?[ -]?)?([6-9]\d{9})\b')
IFSC_PATTERN = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', re.IGNORECASE)
BANK_AC_PATTERN = re.compile(r'\b\d{9,18}\b')

# Threat and scam category keywords
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
    """Extracts UPIs, Phone numbers, Bank accounts, and detects scam indicators."""
    found_upis = list(set(UPI_PATTERN.findall(text)))
    
    # Phone numbers
    phone_matches = PHONE_PATTERN.findall(text)
    cleaned_phones = list(set([p for p in phone_matches if len(p) == 10]))
    
    # IFSC
    found_ifsc = list(set(IFSC_PATTERN.findall(text)))

    # Bank account numbers (9-18 digits) excluding phone numbers, years and IFSC leftovers
    phone_set = set(cleaned_phones)
    found_accounts = []
    for raw in BANK_AC_PATTERN.findall(text):
        digits = raw.strip()
        if len(digits) < 9 or len(digits) > 18:
            continue
        if digits in phone_set:
            continue
        if digits.upper() in {f.upper() for f in found_ifsc}:
            continue
        if digits not in found_accounts:
            found_accounts.append(digits)
    
    # Category detection
    text_lower = text.lower()
    matched_categories = []
    
    for category, keywords in SCAM_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                matched_categories.append(category)
                break
                
    primary_category = matched_categories[0] if matched_categories else "General Suspicious"
    
    # Compute heuristic risk score
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
        
    risk_score = min(100, max(0, risk_score))
    
    return {
        "upis": found_upis,
        "phones": cleaned_phones,
        "ifsc_codes": found_ifsc,
        "bank_accounts": found_accounts,
        "detected_category": primary_category,
        "matched_categories": matched_categories,
        "heuristic_risk_score": risk_score,
        "reasons": reasons
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
