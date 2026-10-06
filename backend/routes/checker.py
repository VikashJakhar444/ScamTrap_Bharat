from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.database.db import lookup_identifier, get_db_connection
from backend.services.extractor import extract_entities

router = APIRouter(prefix="/api/checker", tags=["Scam Checker"])

class CheckRequest(BaseModel):
    query: str

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
    if not query_text:
        return CheckResponse(
            is_known_scam=False,
            risk_score=0,
            threat_level="LOW",
            category="None",
            reports_count=0,
            matched_record=None,
            extracted_entities={"upis": [], "phones": [], "ifsc_codes": [], "detected_category": "None", "reasons": []},
            action_guidance="Please enter a valid phone number, UPI ID, or paste a message to analyze.",
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
                
    if matched_db:
        db_matches.append(matched_db)
        
    is_known = len(db_matches) > 0
    
    if is_known:
        top_match = db_matches[0]
        risk = max(top_match.get("risk_score", 90), entities.get("heuristic_risk_score", 0))
        category = top_match.get("scam_category", entities.get("detected_category", "Identified Scam"))
        reports = top_match.get("reports_count", 1)
        threat = "HIGH_DANGER"
        guidance = "⚠️ DO NOT SEND ANY MONEY OR CLICK LINKS! This account/number is confirmed in the Cyber Scam Blacklist. Use the Co-Pilot counter-bait below to safely lure their secondary mule account."
        counter_bait = True
    elif entities.get("heuristic_risk_score", 0) >= 40:
        risk = entities.get("heuristic_risk_score", 0)
        category = entities.get("detected_category", "Suspicious Alert")
        reports = 1
        threat = "HIGH_DANGER" if risk >= 70 else "MODERATE"
        guidance = f"🚨 High fraud characteristics detected ({category}). Scammers typically create urgency to extract instant UPI payments. Do not transfer funds."
        counter_bait = True
    else:
        risk = max(5, entities.get("heuristic_risk_score", 0))
        category = "No Direct Threat Found"
        reports = 0
        threat = "LOW"
        guidance = "✅ No active blacklisted reports found for this specific query. Always remain vigilant and never share OTPs or PINs with unknown callers."
        counter_bait = False

    return CheckResponse(
        is_known_scam=is_known,
        risk_score=risk,
        threat_level=threat,
        category=category,
        reports_count=reports,
        matched_record=matched_db or (db_matches[0] if db_matches else None),
        extracted_entities=entities,
        action_guidance=guidance,
        counter_bait_available=counter_bait
    )
