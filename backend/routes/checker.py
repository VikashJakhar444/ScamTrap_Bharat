from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.database.db import lookup_identifier, get_db_connection
from backend.services.extractor import extract_entities, localize_category

router = APIRouter(prefix="/api/checker", tags=["Scam Checker"])

class CheckRequest(BaseModel):
    query: str
    lang: str = "en"

class CheckResponse(BaseModel):
    is_known_scam: bool
    risk_score: int
    threat_level: str # 'HIGH_DANGER' | 'MODERATE' | 'LOW'
    category: str
    reports_count: int
    matched_record: Optional[Dict[str, Any]] = None
    extracted_entities: Dict[str, Any]
    action_guidance: str
    counter_bait_available: bool

@router.post("/lookup", response_model=CheckResponse)
def check_scam_item(req: CheckRequest):
    query_text = req.query.strip()
    lang = "hi" if req.lang == "hi" else "en"

    if not query_text:
        empty_msg = (
            "कृपया जांच के लिए फोन नंबर, UPI ID दर्ज करें या कोई संदेश पेस्ट करें।"
            if lang == "hi" else
            "Please enter a valid phone number, UPI ID, or paste a message to analyze."
        )
        return CheckResponse(
            is_known_scam=False,
            risk_score=0,
            threat_level="LOW",
            category="None",
            reports_count=0,
            matched_record=None,
            extracted_entities={"upis": [], "phones": [], "ifsc_codes": [], "bank_accounts": [], "detected_category": "None", "reasons": []},
            action_guidance=empty_msg,
            counter_bait_available=False
        )

    # 1. First check if exact query is already blacklisted in SQLite database
    matched_db = lookup_identifier(query_text)
    
    # 2. Extract entities and fraud indicators
    entities = extract_entities(query_text)
    
    # 3. Check if any extracted UPI or Phone in text exists in DB
    db_matches = []
    with get_db_connection() as conn:
        for u in entities.get("upis", []):
            row = conn.execute("SELECT * FROM scam_identifiers WHERE LOWER(identifier_value) = ?", (u.lower(),)).fetchone()
            if row:
                db_matches.append(dict(row))
        for p in entities.get("phones", []):
            row = conn.execute("SELECT * FROM scam_identifiers WHERE identifier_value LIKE ?", (f"%{p}%",)).fetchone()
            if row:
                db_matches.append(dict(row))
        for b in entities.get("bank_accounts", []):
            row = conn.execute("SELECT * FROM scam_identifiers WHERE identifier_value = ?", (b,)).fetchone()
            if row:
                db_matches.append(dict(row))
                
    if matched_db:
        db_matches.append(matched_db)
        
    is_known = len(db_matches) > 0
    
    if is_known:
        top_match = db_matches[0]
        risk = max(top_match.get("risk_score", 90), entities.get("heuristic_risk_score", 0))
        category = top_match.get("scam_category", entities.get("detected_category", "Identified Scam"))
        reports = top_match.get("reports_count", 1)
        threat = "HIGH_DANGER"
        counter_bait = True
        guidance = (
            "पैसे या लिंक बिल्कुल न भेजें! यह खाता/नंबर साइबर स्कैम ब्लैकलिस्ट में दर्ज है। "
            "नीचे दिए को-पायलट काउंटर-बेट से इसका दूसरा म्यूल खाता सुरक्षित रूप से निकालें।"
            if lang == "hi" else
            "DO NOT SEND ANY MONEY OR CLICK LINKS! This account/number is confirmed in the Cyber Scam Blacklist. Use the Co-Pilot counter-bait below to safely lure their secondary mule account."
        )
    elif entities.get("heuristic_risk_score", 0) >= 40:
        risk = entities.get("heuristic_risk_score", 0)
        category = entities.get("detected_category", "Suspicious Alert")
        reports = 1
        threat = "HIGH_DANGER" if risk >= 70 else "MODERATE"
        counter_bait = True
        guidance = (
            f"उच्च धोखाधड़ी के लक्षण मिले ({localize_category(category, 'hi')}). "
            "स्कैमर अक्सर तुरंत UPI भुगतान के लिए दबाव बनाते हैं। पैसे ट्रांसफर न करें।"
            if lang == "hi" else
            f"High fraud characteristics detected ({category}). Scammers typically create urgency to extract instant UPI payments. Do not transfer funds."
        )
    else:
        risk = max(5, entities.get("heuristic_risk_score", 0))
        category = "No Direct Threat Found"
        reports = 0
        threat = "LOW"
        counter_bait = False
        guidance = (
            "इस क्वेरी पर कोई सक्रिय ब्लैकलिस्ट रिपोर्ट नहीं मिली। सतर्क रहें और अनजान कॉलर पर कभी भी OTP या PIN साझा न करें।"
            if lang == "hi" else
            "No active blacklisted reports found for this specific query. Always remain vigilant and never share OTPs or PINs with unknown callers."
        )

    return CheckResponse(
        is_known_scam=is_known,
        risk_score=risk,
        threat_level=threat,
        category=localize_category(category, lang),
        reports_count=reports,
        matched_record=matched_db or (db_matches[0] if db_matches else None),
        extracted_entities=entities,
        action_guidance=guidance,
        counter_bait_available=counter_bait
    )
