"""
ScamTrap Bharat — Enhanced Checker Routes
Exposes:
  POST /api/checker/lookup        — identifier / quick lookup (INPUT_MODE 2)
  POST /api/checker/analyze       — full investigation on pasted text (MODE 1)
  POST /api/checker/analyze-image — screenshot upload  (MODE 3, OCR + QR)
  POST /api/checker/analyze-audio — voice-note upload  (MODE 4, transcription)
  POST /api/checker/analyze-qr    — UPI QR payload      (MODE 5)
  GET  /api/checker/investigation/{id} — stored forensic .json (MODE 6)
  GET  /api/checker/investigations     — index of stored investigations
  GET  /api/checker/log/{case_id}      — download the forensic .log file
"""

import base64
import io
import re
import time

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from backend.database.db import lookup_identifier, get_db_connection
from backend.services.extractor import extract_entities, localize_category
from backend.services.analyzer import (
    run_full_investigation,
    FORENSIC_LOG_DIR,
    read_investigation,
    list_investigations,
)
from backend.services import security_guard as guard
from backend.services.case_logger import INVESTIGATION_LOG_DIR, new_investigation_id
from backend.database.db import record_investigation_audit
from backend.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MODEL_FALLBACKS

router = APIRouter(prefix="/api/checker", tags=["Scam Checker"])

MAX_TEXT_CHARS = 5000

# Vision / speech model — walks the same candidate list as the detective.
_MODEL = GEMINI_MODEL


# ── Pydantic models ────────────────────────────────────────────────────────────

class CheckRequest(BaseModel):
    query: str
    lang: str = "en"


class CheckResponse(BaseModel):
    is_known_scam: bool
    risk_score: int
    threat_level: str        # 'HIGH_DANGER' | 'MODERATE' | 'LOW'
    category: str
    reports_count: int
    matched_record: Optional[Dict[str, Any]] = None
    extracted_entities: Dict[str, Any]
    action_guidance: str
    counter_bait_available: bool


class AnalyzeRequest(BaseModel):
    query: str
    lang: str = "en"
    case_id: Optional[str] = None
    input_type: str = "TEXT"


def _client_ip(request: Request) -> str:
    return guard.client_ip_of(request.scope)


def _guard_text(query: str) -> str:
    text = (query or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(status_code=413,
                            detail=f"Input too long. Maximum {MAX_TEXT_CHARS:,} characters.")
    return text


# ── Quick lookup (legacy endpoint — kept unchanged) ────────────────────────────

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

    # 1. Exact blacklist lookup
    matched_db = lookup_identifier(query_text)

    # 2. Entity extraction
    entities = extract_entities(query_text)

    # 3. Cross-reference extracted entities against DB
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

    # INPUT_MODE 2 — every identifier lookup leaves an audit row (spec §6).
    lookup_id = new_investigation_id()
    probe = guard.check_probe("lookup", query_text)
    record_investigation_audit({
        "investigation_id": lookup_id,
        "case_id": lookup_id,
        "input_type": "IDENTIFIER_LOOKUP",
        "input_sha256": __import__("hashlib").sha256(query_text.encode()).hexdigest(),
        "client_ip": "lookup",
        "prompt_injection_detected": False,
        "is_scammer_probing": probe.get("is_scammer_probing", False),
        "risk_score": risk,
        "threat_level": threat,
        "scam_category": category,
        "model_source": "local_engine",
    })

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


# ── Full 5-layer investigation (new endpoint) ──────────────────────────────────

@router.post("/analyze")
def analyze_scam_deep(req: AnalyzeRequest, request: Request):
    """
    Runs the complete investigation engine on the submitted text.
    Returns layer-by-layer breakdown + final verdict + forensic log path.
    """
    query_text = _guard_text(req.query)
    lang = "hi" if req.lang == "hi" else "en"

    report = run_full_investigation(
        query_text,
        case_id=req.case_id,
        lang=lang,
        input_type=(req.input_type or "TEXT").upper() if
        (req.input_type or "TEXT").upper() in
        ("TEXT", "IMAGE_OCR", "VOICE_AUDIO", "QR_CODE", "IDENTIFIER_LOOKUP")
        else "TEXT",
        client_ip=_client_ip(request),
    )
    return report


# ── Forensic log download ──────────────────────────────────────────────────────

@router.get("/log/{case_id}")
def download_forensic_log(case_id: str):
    """Returns the raw forensic .log file for a given case ID."""
    # Sanitize: only alphanumerics + hyphens
    import re
    if not re.match(r'^[A-Za-z0-9\-]{1,40}$', case_id):
        raise HTTPException(status_code=400, detail="Invalid case ID format.")

    log_path = FORENSIC_LOG_DIR / f"{case_id}.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"No forensic log found for case {case_id}.")

    return FileResponse(
        path=str(log_path),
        media_type="text/plain; charset=utf-8",
        filename=f"ScamTrap_{case_id}_forensic.log",
    )


# ── Stored forensic JSON + index (spec §6) ────────────────────────────────────

_ID_RE = re.compile(r"^[A-Za-z0-9\-]{1,60}$")


@router.get("/investigation/{investigation_id}")
def get_investigation(investigation_id: str):
    """Returns the full five-section forensic record for one investigation."""
    if not _ID_RE.match(investigation_id):
        raise HTTPException(status_code=400, detail="Invalid investigation ID format.")
    data = read_investigation(investigation_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"No investigation record for {investigation_id}.")
    return JSONResponse(content=data)


@router.get("/investigations")
def investigations_index(limit: int = 50):
    """Newest-first index of every investigation written so far."""
    return {"count": len(list_investigations(limit)),
            "items": list_investigations(limit)}


# ── Input modes 3, 4, 5 — uploads ─────────────────────────────────────────────

def _qr_variants(img):
    """Grayscale renderings that make a QR code easy to spot.

    OpenCV's detector needs a few pixels per module, so a 37x37 symbol drawn at
    1 px/module is invisible to it. Real uploads also arrive dark-mode inverted
    or inside a giant screenshot, so we normalise size and try both polarities.
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = gray.shape[:2]
    if not h or not w:
        return []

    # Keep detection on a sane canvas: too big is slow, too small is unreadable.
    shortest, longest = min(h, w), max(h, w)
    factors = [1.0]
    if shortest < 420:
        factors.append(min(8.0, 420.0 / shortest))
    if longest > 1600:
        factors.append(1600.0 / longest)

    variants = []
    for polar in (gray, 255 - gray):
        for f in dict.fromkeys(round(x, 3) for x in factors):
            out = polar if f == 1.0 else cv2.resize(
                polar, None, fx=f, fy=f, interpolation=cv2.INTER_NEAREST)
            variants.append(np.ascontiguousarray(out))
    return variants


def _decode_qr(payload: bytes) -> Optional[str]:
    """Offline QR decode via OpenCV — no network, no extra DLL.

    Tries the raw frame, an upscaled frame and the inverted (dark-mode)
    polarity, single and multi symbol, before giving up.
    """
    try:
        import cv2
        import numpy as np
        arr = np.frombuffer(payload, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
    except Exception:                                        # noqa: BLE001
        return None

    detector = cv2.QRCodeDetector()
    for variant in _qr_variants(img):
        try:
            data, _, _ = detector.detectAndDecode(variant)
        except Exception:                                    # noqa: BLE001
            data = ""
        if data:
            return data
        try:
            ok, multi, _, _ = detector.detectAndDecodeMulti(variant)
        except Exception:                                    # noqa: BLE001
            ok, multi = False, ()
        if ok:
            for item in multi or ():
                if item:
                    return item
    return None


def _gemini_text(prompt: str, content_part, timeout_ms: int = 10000) -> Optional[str]:
    """One Gemini text call that walks the same model candidates as the
    detective. Returns None when there is no key or every candidate fails."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None

    from backend.services.llm_engine import (
        CALL_BUDGET_S, _status_of, _MODEL_COOLDOWN, _RETIRED_MODELS, _WORKING_MODEL,
    )

    config = None
    try:
        config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            temperature=0.1,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
    except Exception:                                    # noqa: BLE001
        config = None

    order = ([_WORKING_MODEL] if _WORKING_MODEL else []) + [
        m for m in GEMINI_MODEL_FALLBACKS if m and m != _WORKING_MODEL
    ]
    deadline = time.monotonic() + CALL_BUDGET_S

    for model_name in order:
        if time.monotonic() >= deadline:
            break
        if not model_name or model_name in _RETIRED_MODELS:
            continue
        if _MODEL_COOLDOWN.get(model_name, 0.0) > time.monotonic():
            continue
        try:
            client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
            kwargs = {"model": model_name, "contents": [prompt, content_part]}
            if config is not None:
                kwargs["config"] = config
            resp = client.models.generate_content(**kwargs)
            text = (resp.text or "").strip()
            if text:
                return text
            _MODEL_COOLDOWN[model_name] = time.monotonic() + 20.0
        except Exception as exc:                         # noqa: BLE001
            code = _status_of(exc)
            if code in (400, 401, 403, 404, 405, 410):
                _RETIRED_MODELS.add(model_name)
            elif code == 429:
                # Billing quota on this key — do not spend the budget on it.
                _MODEL_COOLDOWN[model_name] = time.monotonic() + 120.0
            else:
                _MODEL_COOLDOWN[model_name] = time.monotonic() + 3.0
    return None


_MIME_BY_FORMAT = {
    "PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp",
    "OGG": "audio/ogg", "MP3": "audio/mpeg", "WAV": "audio/wav", "M4A": "audio/mp4",
}


def _gemini_image_text(payload: bytes, fmt: str = "PNG") -> Optional[str]:
    """Gemini vision: decode a QR code when there is one, otherwise OCR.

    One call covers both so a screenshot is not charged for two round trips.
    Returns None when there is no API key or the call fails.
    """
    try:
        from google.genai import types
        return _gemini_text(
            "Look at this image. FIRST: if it contains a QR code, decode it and "
            "return ONLY its payload (for example upi://pay?pa=...&am=...). "
            "SECOND: if there is no QR code, transcribe EVERY visible string "
            "exactly as written, including phone numbers, UPI IDs, bank "
            "accounts, IFSC codes and headers. Return only the result.",
            types.Part.from_bytes(data=payload,
                                  mime_type=_MIME_BY_FORMAT.get(fmt, "image/png")),
            timeout_ms=30000,
        )
    except Exception:                                        # noqa: BLE001
        return None


_QR_SCHEMES = ("upi://", "http://", "https://", "mailto:", "tel:", "sms:",
               "smsto:", "matmsg:", "wifi:", "begin:vcard", "geo:")


def _looks_like_qr_payload(text: str) -> bool:
    """True when a vision reply is a QR payload rather than transcribed prose."""
    value = (text or "").strip()
    if not value:
        return False
    low = value.lower()
    if any(low.startswith(s) for s in _QR_SCHEMES):
        return True
    # Bare VPA on a single token, e.g. bijli.board.pay@ybl — no sentence.
    if "\n" not in value and " " not in value and "@" in value:
        local, _, domain = value.partition("@")
        return bool(local) and "." in domain
    return False


def _gemini_audio_text(payload: bytes, fmt: str = "MP3") -> Optional[str]:
    """Gemini speech-to-text when an API key is configured; otherwise None."""
    try:
        from google.genai import types
        return _gemini_text(
            "Transcribe this voice note verbatim into English/Hinglish text. "
            "Return only the transcription.",
            types.Part.from_bytes(data=payload,
                                  mime_type=_MIME_BY_FORMAT.get(fmt, "audio/mpeg")),
            timeout_ms=30000,
        )
    except Exception:                                        # noqa: BLE001
        return None


def _upload_or_reject(file: UploadFile, kind: str) -> tuple:
    """Returns (payload, validation, exec_disguise) or raises 413/415."""
    payload = file.file.read()
    validation = guard.validate_upload(file.filename or "", payload, kind)
    if not validation["ok"]:
        status = 413 if "large" in validation["reason"].lower() else 415
        raise HTTPException(status_code=status, detail=validation["reason"])
    if guard.detect_executable_disguise(payload):
        raise HTTPException(
            status_code=415,
            detail="This file is actually an executable, not a genuine "
                   f"{kind}. Upload rejected for safety.",
        )
    return payload, validation, False


@router.post("/analyze-image")
def analyze_image(request: Request,
                  file: UploadFile = File(...),
                  lang: str = Form("en")):
    """INPUT_MODE 3 — screenshot / photo upload (magic-byte check, QR, OCR)."""
    payload, validation, exec_flag = _upload_or_reject(file, "image")

    # Offline pass first (free, ~50 ms). Only pay for vision when it misses.
    qr_text = _decode_qr(payload)
    ocr_text = None
    if not qr_text:
        reply = _gemini_image_text(payload, validation.get("format", "PNG"))
        if reply:
            if _looks_like_qr_payload(reply):
                qr_text = reply.strip()
            else:
                ocr_text = reply

    if qr_text:
        raw_text = qr_text
        input_type = "QR_CODE"
    elif ocr_text:
        raw_text = ocr_text
        input_type = "IMAGE_OCR"
    else:
        raw_text = (file.filename or "uploaded screenshot")
        input_type = "IMAGE_OCR"

    report = run_full_investigation(
        raw_text, lang=lang, input_type=input_type,
        client_ip=_client_ip(request), image_bytes=payload,
        ocr_text=ocr_text, upload_validation=validation,
        exec_disguise_detected=exec_flag,
    )
    report["ocr_text"] = ocr_text
    report["qr_payload"] = qr_text
    if not qr_text and not ocr_text:
        if not GEMINI_API_KEY:
            reason = ("no Gemini API key is configured")
        else:
            reason = ("the vision service is rate-limited right now "
                      "(quota exhausted), so no speech or text could be read")
        report["ocr_note"] = (
            f"Offline analysis: {reason}. The upload was still validated, "
            "logged, scanned for an embedded QR code and scored on whatever "
            "was recovered from it.")
        report["ocr_unavailable"] = True
    return report


@router.post("/analyze-audio")
def analyze_audio(request: Request,
                  file: UploadFile = File(...),
                  lang: str = Form("en")):
    """INPUT_MODE 4 — voice note / call recording upload."""
    payload, validation, exec_flag = _upload_or_reject(file, "audio")

    transcript = _gemini_audio_text(payload, validation.get("format", "MP3"))
    raw_text = transcript or (file.filename or "uploaded voice note")

    report = run_full_investigation(
        raw_text, lang=lang, input_type="VOICE_AUDIO",
        client_ip=_client_ip(request), audio_bytes=payload,
        transcription=transcript, upload_validation=validation,
        exec_disguise_detected=exec_flag,
    )
    report["transcription"] = transcript
    if not transcript:
        report["transcription_note"] = ("The voice note was validated, logged and "
                                        "scored, but no speech could be transcribed "
                                        "from it (silence, or the speech service did "
                                        "not return text).")
    return report


class QRRequest(BaseModel):
    payload: str
    lang: str = "en"


@router.post("/analyze-qr")
def analyze_qr(req: QRRequest, request: Request):
    """INPUT_MODE 5 — a raw UPI QR payload pasted or decoded as text."""
    text = (req.payload or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="QR payload cannot be empty.")
    if len(text) > 4000:
        raise HTTPException(status_code=413, detail="QR payload too long.")
    if "upi://" not in text.lower() and "@" not in text:
        raise HTTPException(status_code=422,
                            detail="Not a recognised UPI QR payload (expected upi://pay?...).")
    return run_full_investigation(
        text, lang=req.lang, input_type="QR_CODE",
        client_ip=_client_ip(request),
    )
