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
    if matched_categories:
        risk_score += 40
        reasons.append(f"Matches high-risk fraud pattern: {', '.join(matched_categories)}")
        
    risk_score = min(100, max(0, risk_score))
    
    return {
        "upis": found_upis,
        "phones": cleaned_phones,
        "ifsc_codes": found_ifsc,
        "detected_category": primary_category,
        "matched_categories": matched_categories,
        "heuristic_risk_score": risk_score,
        "reasons": reasons
    }
