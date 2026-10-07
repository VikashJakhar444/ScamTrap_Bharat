"""
ScamTrap Bharat — Cognitive AI Detective  (spec §4)
====================================================
A 4-principle scoring model with FIXED, auditable weights:

    Principle 1  Authority & Trust Manipulation .......... 35
    Principle 2  Urgency & Fear Engineering .............. 30
    Principle 3  Money-Flow Redirection ................. 20
    Principle 4  Linguistic & Behavioural Cues .......... 15
                                                  -------------
                                                   total 100

Principle 1 (Authority) ALWAYS outranks the others: a message that claims to
be an institution, a court or a bank is already the dominant signal no matter
how polite the language is.

Provider order (spec §4, revised so no billing quota can ever own this app):

    1. `local_nli`  — free on-device NLI model (`backend/services/local_ai.py`).
                      No key, no quota, offline after the first download, ~0.1 s.
    2. `gemini`     — backup only, used when the local model is unavailable
                      (not downloaded, failed to load, or too little text to
                      score) and an API key is configured.
    3. `local_engine` — the deterministic rules engine, always used as the
                      evidence floor and as the last resort.

The free model is *merged* with the rules rather than replacing them: the rules
own Authority and Urgency (they have the domain vocabulary and score far better
there), while the model owns Money-Flow and Linguistic cues in Hindi and in
paraphrases the regex never sees. Each principle takes the higher of the two.

Ruled out of every input: the 25-point prompt-injection penalty from
`security_guard`, applied ONLY after principle scoring and never narrated as
a detection.
"""

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from backend.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MODEL_FALLBACKS
from backend.services import local_ai, security_guard

MODEL = GEMINI_MODEL
MODEL_CANDIDATES = GEMINI_MODEL_FALLBACKS

# ── Principle weights (fixed; Principle 1 is dominant) ────────────────────────
PRINCIPLES = [
    ("p1_authority", "Authority & Trust Manipulation", 35),
    ("p2_urgency", "Urgency & Fear Engineering", 30),
    ("p3_money", "Money-Flow Redirection", 20),
    ("p4_language", "Linguistic & Behavioural Cues", 15),
]
TOTAL_WEIGHT = sum(w for _, _, w in PRINCIPLES)   # 100

# Authority institutions are claimed with these exact words.
_AUTHORITY_CLAIMS = [
    "electricity department", "power office", "bijli", "discom", "substation",
    "sbi", "hdfc", "icici", "axis bank", "pnb", "bank", "rbi",
    "police", "cbi", "ed ", "cyber cell", "customs", "narcotics",
    "court", "mha", "passport office", "income tax", "gst",
    "uidai", "aadhaar", "government", "govt", "municipal",
    "college", "university", "principal", "hospital", "icu",
    "fedex", "dhl", "bluedart", "india post", "courier",
    "telecom", "trai", "airtel", "jio", "vi ",
    "loan", "lender", "nbfc", "credit line",
]
_AUTHORITY_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(a.strip()) for a in _AUTHORITY_CLAIMS) + r")\b",
    re.IGNORECASE,
)
_FAKE_ARREST = re.compile(
    r"digital arrest|arrest warrant|your (?:call|phone) (?:is|has been) (?:tapped|recorded)|"
    r"you (?:are|have been) involved in|parcel (?:has been )?seized|money laundering|"
    r"case (?:has been )?registered|non-bailable warrant|custody", re.IGNORECASE)

_URGENCY_RE = re.compile(
    r"\b(?:immediately|urgent(?:ly)?|instantly|now|jaldi|turant|asap|"
    r"within \d+ (?:minutes|hours)|tonight|today only|last date|final warning|"
    r"expired?|suspend(?:ed)?|deactivat\w+|disconnect(?:ed)?|blocked|"
    r"before .*close of business|last (?:warning|notice))\b", re.IGNORECASE)
_FEAR_RE = re.compile(
    r"\b(?:disconnected?|cut (?:off|your)|terminate|block(?:ed)?|freeze|"
    r"closed? for good|legal action|fine|penalt\w+|lose your|will be reported|"
    r"negative mark|bad cibil|fir filed|jail|prison|cancelled?)\b", re.IGNORECASE)

_MONEY_RE = re.compile(
    r"\b(?:upi|pay|transfer|gpay|phonepe|paytm|bhim|imps|neft|rtgs|"
    r"deposit|account\s*(?:no\.?|number)|a/c|ifsc|scan|qr code|"
    r"wallet|crypto|refund|recharge)\b", re.IGNORECASE)
_MONEY_NEW_TARGET = re.compile(
    r"\b(?:instead of|backup account|secondary (?:account|upi)|another (?:account|upi)|"
    r"transfer to|pay to|send to|alternate|use this|this one|new number)\b", re.IGNORECASE)
_PREREQ_PAYMENT = re.compile(
    r"\b(?:registration fee|processing fee|activation fee|advance|token amount|"
    r"gst will be|refundable|small amount first|verification (?:charge|fee)|"
    r"charge.*before|pay first|prepaid)\b", re.IGNORECASE)

_LANGUAGE_RE = re.compile(
    r"\b(?:kindly|dear (?:customer|user|applicant|sir)|valued customer|"
    r"verify your|update your|confirm your|click (?:on )?(?:the )?link|"
    r"do not (?:tell|share with) (?:anyone|anybody|your (?:family|bank))|"
    r"keep this confidential|share otp|otp\b|password|screen ?share|"
    r"install|download|remote|anydesk|teamviewer|whatsapp only|"
    r"assalam|regards, ?(?:team|bank|dept))\b", re.IGNORECASE)
_TYPO_RE = re.compile(r"\b(?:kindly|imediately|recieve|occured|detials|benificiary|"
                      r"trasaction|plese|kindely)\b", re.IGNORECASE)
_PROFESSIONAL_CLAIM = re.compile(r"\b(?:official|department|head office|branch manager|"
                                 r"senior officer|customs dept|investigation team)\b", re.IGNORECASE)


# ==============================================================================
# Deterministic fallback — the `local_engine`
# ==============================================================================
def _score_principles(text: str, entities: Dict[str, Any],
                      facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Applies each principle's regex/rule evidence and caps it at its weight."""
    low = (text or "").lower()
    out: List[Dict[str, Any]] = []

    # ── Principle 1: Authority & Trust Manipulation (weight 35) ─────────────
    p1 = 0
    findings: List[str] = []
    claims = sorted({m.group(0).strip() for m in _AUTHORITY_RE.finditer(text or "")}, key=str.lower)
    if claims:
        p1 += 60
        findings.append(f"Claims institutional authority: {', '.join(claims)}.")
    if _FAKE_ARREST.search(text or ""):
        p1 += 75
        findings.append("Uses a criminal-threat / 'digital arrest' script.")
    auth = facts.get("authority_on_personal_handle") or {}
    if auth.get("contradiction"):
        p1 += 100
        findings.append(
            "Contradiction: claims to be " + ", ".join(auth.get("claimed", [])) +
            " yet collects on a personal UPI handle " + ", ".join(auth.get("collecting_on", [])) + "."
        )
    if _PROFESSIONAL_CLAIM.search(text or "") and claims:
        p1 += 20
        findings.append("Signs off with a professional designation to borrow credibility.")
    out.append(_principle_row("p1_authority", findings, p1, 35))

    # ── Principle 2: Urgency & Fear Engineering (weight 30) ─────────────────
    p2 = 0
    findings = []
    if _URGENCY_RE.search(text or ""):
        p2 += 45
        findings.append("Manufactures a deadline so you act before thinking.")
    if _FEAR_RE.search(text or ""):
        p2 += 45
        findings.append("Threatens a loss — disconnection, block, fine or arrest.")
    if _URGENCY_RE.search(text or "") and _FEAR_RE.search(text or ""):
        p2 += 30
        findings.append("Deadline plus threat stacked together — classic pressure combination.")
    if re.search(r"\b(?:do not|don't|avoid|mat)\b.{0,40}\b(?:tell|share|inform|batayein)\b",
                 text or "", re.IGNORECASE | re.DOTALL):
        p2 += 40
        findings.append("Explicitly tells you to keep it from family or the bank.")
    out.append(_principle_row("p2_urgency", findings, p2, 30))

    # ── Principle 3: Money-Flow Redirection (weight 20) ─────────────────────
    p3 = 0
    findings = []
    if _MONEY_RE.search(text or ""):
        p3 += 40
        findings.append("Directs a payment through UPI, QR, bank transfer or an account number.")
    if _MONEY_NEW_TARGET.search(text or ""):
        p3 += 60
        findings.append("Redirects the payment to a different/new account than expected.")
    if _PREREQ_PAYMENT.search(text or ""):
        p3 += 75
        findings.append("Demands an upfront fee before any benefit — the money never comes back.")
    if entities.get("qr_payloads"):
        p3 += 60
        findings.append("A UPI QR was attached; a UPI QR can only debit the scanner, never pay you.")
    if len(entities.get("bank_accounts") or []) >= 2:
        p3 += 45
        findings.append(f"{len(entities.get('bank_accounts'))} bank accounts offered — money-mule fan-out.")
    if (entities.get("upis") or []) and (entities.get("bank_accounts") or []):
        p3 += 35
        findings.append("Both a UPI handle and a bank account were given — layered collection routes.")
    out.append(_principle_row("p3_money", findings, p3, 20))

    # ── Principle 4: Linguistic & Behavioural Cues (weight 15) ──────────────
    p4 = 0
    findings = []
    if _LANGUAGE_RE.search(text or ""):
        p4 += 40
        findings.append("Uses social-engineering triggers — OTP, screen share, install, keep quiet.")
    if _TYPO_RE.search(text or ""):
        p4 += 30
        findings.append("Spelling mistakes inconsistent with an official department.")
    if re.search(r"\b(?:sir|bhaiya|madam|ji)\b", low) and claims:
        p4 += 15
        findings.append("Mixes formal authority with informal flattery.")
    if len(text or "") < 60 and (entities.get("upis") or entities.get("phones")):
        p4 += 25
        findings.append("Very short message straight to a payment — no context offered.")
    out.append(_principle_row("p4_language", findings, p4, 15))

    return out


def _principle_row(key: str, findings: List[str], raw: int, weight: int) -> Dict[str, Any]:
    """Caps the raw evidence at 100 then converts to the principle's weight."""
    capped = max(0, min(100, raw))
    return {
        "key": key,
        "name": dict((k, n) for k, n, _ in PRINCIPLES)[key],
        "weight": weight,
        "score": round(capped * weight / 100.0, 1),
        "evidence": capped,
        "findings": findings,
    }


def _weighted_total(rows: List[Dict[str, Any]]) -> int:
    return int(round(sum(r["score"] for r in rows)))


# Plain-language note appended when the on-device model saw something the rules
# did not — never mentions weights, thresholds or model internals.
_AI_FINDING = {
    "p1_authority": "reads it as a bank or government impersonation",
    "p2_urgency": "reads an urgent threat or deadline in it",
    "p3_money": "reads it as a request to move money",
    "p4_language": "reads a request for an OTP or a password in it",
}


def _merge_local_rows(rule_rows: List[Dict[str, Any]],
                      ai_evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Merges the free model's evidence with the deterministic evidence.

    Per principle the higher of the two wins, so the model can only ever add
    signal — it can never talk the app out of a rule it already proved. When
    the model is the one that fired, its reason is appended to `findings`.
    """
    rows: List[Dict[str, Any]] = []
    for row in rule_rows:
        rule_ev = max(0, min(100, int(row["evidence"])))
        try:
            ai_ev = max(0, min(100, int(ai_evidence.get(row["key"], 0))))
        except (TypeError, ValueError):
            ai_ev = 0

        findings = list(row["findings"])
        if ai_ev > rule_ev:
            note = _AI_FINDING.get(row["key"])
            if note:
                findings.append(f"On-device AI {note}.")
        evidence = max(rule_ev, ai_ev)

        rows.append({
            "key": row["key"],
            "name": row["name"],
            "weight": row["weight"],
            "score": round(evidence * row["weight"] / 100.0, 1),
            "evidence": evidence,
            "findings": findings[:6],
        })
    return rows


# ==============================================================================
# Gemini path — text + image + audio
# ==============================================================================
_DETECTIVE_PROMPT = """You are ScamTrap Bharat's Cognitive AI Detective.

Analyse the input against EXACTLY these four principles and nothing else:
1. Authority & Trust Manipulation (weight 35) — does it claim to be a bank, the electricity department, police, a court, a college, a government office?
2. Urgency & Fear Engineering (weight 30) — deadlines, threats of arrest, service cuts, account blocks, "do not tell anyone".
3. Money-Flow Redirection (weight 20) — asks for UPI, QR, a new/backup account, an upfront fee.
4. Linguistic & Behavioural Cues (weight 15) — OTP/screen-share/install requests, spelling mistakes, professional claims.

Return ONLY a JSON object with these keys:
{"category": str, "summary": str, "action": str,
 "principles": [{"key": "p1_authority","evidence": 0-100, "findings": [str]}, ... for p1..p4]}

`evidence` is 0-100 for that principle alone. Keep findings to plain Hindi/English
warning language a citizen understands. Never mention regex, thresholds, weights or rule ids."""


def _gemini_available() -> bool:
    return bool(GEMINI_API_KEY)


_WORKING_MODEL: Optional[str] = None
_RETIRED_MODELS: set = set()                    # 404/400 — never retry
_MODEL_COOLDOWN: Dict[str, float] = {}          # 429/503/504 — retry after t

# Hard ceiling on how long the detective may spend talking to Gemini. Past this
# the caller falls back to `local_engine` instead of holding the request open.
CALL_BUDGET_S = float(os.getenv("GEMINI_CALL_BUDGET_S", "14"))
_HTTP_TIMEOUT_MS = int(os.getenv("GEMINI_HTTP_TIMEOUT_MS", "10000"))
# Vision/multimodal replies are far slower than a one-line text reply.
_HTTP_TIMEOUT_IMAGE_MS = int(os.getenv("GEMINI_HTTP_TIMEOUT_IMAGE_MS", "30000"))
_TRANSIENT_CODES = {408, 429, 500, 502, 503, 504}
_DEAD_CODES = {400, 401, 403, 404, 405, 410}
# 429 on this key is a billing quota, not a burst — backing off for 3s would
# just burn the whole request budget on a call that cannot succeed.
_QUOTA_COOLDOWN_S = 120.0


def _status_of(exc: Exception) -> Optional[int]:
    """Best-effort HTTP status from a google-genai / httpx exception."""
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    match = re.search(r"\b(4\d\d|5\d\d)\b", str(exc))
    return int(match.group(1)) if match else None


def _genai_config(_types) -> Any:
    """JSON-only, function-calling off.

    AFC makes `resp.text` come back as None when the model emits a
    functionCall instead of prose, which silently drops a good answer.
    """
    cfg: Dict[str, Any] = {"response_mime_type": "application/json",
                           "temperature": 0.2}
    try:
        cfg["automatic_function_calling"] = _types.AutomaticFunctionCallingConfig(disable=True)
    except Exception:                                    # noqa: BLE001
        pass
    try:
        return _types.GenerateContentConfig(**cfg)
    except Exception:                                    # noqa: BLE001
        cfg.pop("automatic_function_calling", None)
        try:
            return _types.GenerateContentConfig(**cfg)
        except Exception:                                # noqa: BLE001
            return None


def _call_gemini(prompt: str, image_bytes: Optional[bytes] = None,
                 audio_bytes: Optional[bytes] = None,
                 budget_s: Optional[float] = None,
                 timeout_ms: Optional[int] = None):
    """Calls the detective on Gemini and parses the JSON reply.

    Returns `(payload, model_used)`. Walks `MODEL_CANDIDATES`, pinning the
    first model that answers. Error handling is split on purpose:

      * 404 / 400 (model retired or not on this key) -> remembered forever,
        so a dead name is never paid for twice.
      * 429 / 503 / 504 (rate limit or high demand)  -> short cooldown, then
        retried. A single transient blip must NOT disable a model for the
        lifetime of the process.

    The whole walk is capped by `budget_s`; when it expires the caller falls
    back to the deterministic `local_engine`.
    """
    global _WORKING_MODEL

    if not _gemini_available():
        return None, None

    try:
        from google import genai as _genai
        from google.genai import types as _types
    except ImportError:
        return None, None

    ms = timeout_ms
    if ms is None:
        ms = _HTTP_TIMEOUT_IMAGE_MS if (image_bytes or audio_bytes) else _HTTP_TIMEOUT_MS
    try:
        client = _genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=_types.HttpOptions(timeout=ms),
        )
        new_sdk = True
    except Exception:                                   # noqa: BLE001
        client = _genai.Client(api_key=GEMINI_API_KEY)
        new_sdk = True

    config = _genai_config(_types) if new_sdk else None
    deadline = time.monotonic() + (budget_s if budget_s is not None else CALL_BUDGET_S)
    now = time.monotonic

    # Preferred model first, then the rest of the candidate list.
    order: List[str] = []
    if _WORKING_MODEL:
        order.append(_WORKING_MODEL)
    order.extend(m for m in MODEL_CANDIDATES if m and m != _WORKING_MODEL)

    for attempt in range(2):                            # two passes max
        for model_name in order:
            if now() >= deadline:
                return None, None
            if model_name in _RETIRED_MODELS:
                continue
            if _MODEL_COOLDOWN.get(model_name, 0.0) > now():
                continue
            try:
                parts: List[Any] = [prompt]
                if image_bytes:
                    parts.append(_types.Part.from_bytes(data=image_bytes,
                                                        mime_type="image/png"))
                if audio_bytes:
                    parts.append(_types.Part.from_bytes(data=audio_bytes,
                                                        mime_type="audio/mpeg"))
                kwargs = {"model": model_name, "contents": parts}
                if config is not None:
                    kwargs["config"] = config
                resp = client.models.generate_content(**kwargs)
                text = getattr(resp, "text", None)
                if text:
                    payload = _extract_json(text)
                    if payload:
                        _WORKING_MODEL = model_name
                        _MODEL_COOLDOWN.pop(model_name, None)
                        return payload, model_name
                # Answered but unusable — give the model a short rest.
                _MODEL_COOLDOWN[model_name] = now() + 20.0
            except Exception as exc:                    # noqa: BLE001
                code = _status_of(exc)
                if code in _DEAD_CODES:
                    _RETIRED_MODELS.add(model_name)
                elif code == 429:
                    _MODEL_COOLDOWN[model_name] = now() + _QUOTA_COOLDOWN_S
                elif code in _TRANSIENT_CODES:
                    _MODEL_COOLDOWN[model_name] = now() + (2.0 * (attempt + 1))
                else:
                    # Unknown failure: assume transient, but don't hot-loop.
                    _MODEL_COOLDOWN[model_name] = now() + (5.0 * (attempt + 1))
        if now() >= deadline:
            return None, None
        # Second pass waits out the shortest cooldown, if there is still time.
        wait = min([t - now() for t in _MODEL_COOLDOWN.values() if t > now()] or [0.0])
        if wait <= 0:
            continue
        if now() + wait >= deadline:
            return None, None
        time.sleep(min(wait, 1.0))
    return None, None


def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
    raw = (raw or "").strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:                                       # noqa: BLE001
        return None


def _rows_from_gemini(payload: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    given = payload.get("principles") or []
    by_key = {str(p.get("key")): p for p in given if isinstance(p, dict)}
    rows: List[Dict[str, Any]] = []
    for key, name, weight in PRINCIPLES:
        p = by_key.get(key)
        if not p:
            return None                                      # incomplete → force fallback
        try:
            evidence = max(0, min(100, int(p.get("evidence", 0))))
        except Exception:                                    # noqa: BLE001
            return None
        rows.append({
            "key": key, "name": name, "weight": weight,
            "score": round(evidence * weight / 100.0, 1),
            "evidence": evidence,
            "findings": [str(f) for f in (p.get("findings") or [])][:6],
        })
    return rows


# ==============================================================================
# Public entry point
# ==============================================================================
def cognitive_detective(text: str,
                        entities: Optional[Dict[str, Any]] = None,
                        image_bytes: Optional[bytes] = None,
                        audio_bytes: Optional[bytes] = None,
                        facts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Scores the input across the four principles and returns the verdict.

    Order of operations (spec §4):
      scan_prompt_injection → stage the four principles → apply the +25
      injection penalty → round → categorise.
    """
    entities = entities or {}
    facts = facts or {}
    scanned = security_guard.scan_prompt_injection(text or "")
    clean_text = scanned.get("cleaned") or text or ""

    source = "local_engine"
    model_used = "local_engine"
    rows: Optional[List[Dict[str, Any]]] = None
    llm_payload: Optional[Dict[str, Any]] = None

    # Computed first: it is the evidence floor for the free model AND the last
    # resort if every provider is unavailable.
    rule_rows = _score_principles(clean_text, entities, facts)

    # 1 ── Free on-device model — primary, no key and no quota to run out of.
    ai_evidence = local_ai.score(clean_text)
    if ai_evidence:
        rows = _merge_local_rows(rule_rows, ai_evidence)
        source = "local_nli"
        model_used = local_ai.status().get("label") or local_ai.MODEL_ID

    # 2 ── Gemini — backup only, and only when there is something the local
    #      model cannot read (a screenshot or a voice note with no usable text).
    if rows is None and (image_bytes or audio_bytes or _gemini_available()):
        llm_payload, served_model = _call_gemini(
            _DETECTIVE_PROMPT + "\n\nINPUT:\n" + clean_text[:6000],
            image_bytes=image_bytes, audio_bytes=audio_bytes,
        )
        if llm_payload:
            parsed = _rows_from_gemini(llm_payload)
            if parsed:
                rows = parsed
                source = served_model or MODEL
                model_used = served_model or MODEL

    # 3 ── Deterministic rules.
    if rows is None:
        rows = rule_rows

    base = _weighted_total(rows)

    # Prompt-injection rule: +25, added last, never narrated as a detection.
    score = max(0, min(100, base + scanned.get("score_bonus", 0)))

    category = _categorise(score, llm_payload, clean_text, entities, facts)
    summary = (llm_payload or {}).get("summary") or _fallback_summary(rows, category, score)
    action = (llm_payload or {}).get("action") or _fallback_action(score, category)

    return {
        "principles": rows,
        "weighted_score": score,
        "ai_source": source,
        "model": model_used,
        "category": category,
        "citizen_summary": summary,
        "citizen_action": action,
        "prompt_injection_detected": scanned["detected"],
        "injection_matches": scanned["matches"],
        "raw": llm_payload,
    }


def _categorise(score: int, payload: Optional[Dict[str, Any]], text: str,
                entities: Dict[str, Any], facts: Dict[str, Any]) -> str:
    if payload and payload.get("category"):
        return str(payload["category"])
    if facts.get("confirmed_scam"):
        return "Identified Scam"
    if score >= 75:
        return "Identified Scam"
    if score >= 45:
        return "Suspicious Alert"
    if entities.get("matched_categories") and score >= 25:
        return "Suspicious Alert"
    if score >= 20:
        return "General Suspicious"
    return "No Direct Threat Found"


def _fallback_summary(rows: List[Dict[str, Any]], category: str, score: int) -> str:
    top = max(rows, key=lambda r: r["score"]) if rows else None
    lead = top["findings"][0] if top and top["findings"] else "No strong signal was found."
    return f"{category} (score {score}/100). {lead}"


def _fallback_action(score: int, category: str) -> str:
    if score >= 75:
        return ("Do not pay and do not share an OTP. Block the number, and report it at "
                "cybercrime.gov.in or call 1930 within the golden hour.")
    if score >= 45:
        return ("Verify independently — call the bank or department on a number you find "
                "yourself, never the one in the message. Do not install anything.")
    if score >= 20:
        return "Pause before acting. Confirm the sender through the official website or app."
    return "No immediate threat detected — still never share an OTP or install an app from a chat."
