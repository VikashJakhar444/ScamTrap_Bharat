"""
ScamTrap Bharat — Kill-Chain Stage Classifier
=============================================
Rule-based, deterministic classification of a scam transcript into the four
stages of a social-engineering kill chain:

    approach  → rapport → pressure → payment_demand

Nothing here is invented: every message is scored against an explicit
keyword/regex vocabulary (English + Hinglish, because Indian scammers use
both), the winning stage is reported together with the exact terms that
matched. The UI can therefore show *why* a message landed where it did.

No LLM call, no network, ~1 ms for a full transcript — safe to run on
every evidence read.
"""

import re
from typing import Any, Dict, List, Optional

STAGES = [
    {
        "key": "approach",
        "label": "Approach",
        "icon": "i-target",
        "summary": "First contact — the opener, the pretext, the introduction.",
    },
    {
        "key": "rapport",
        "label": "Rapport",
        "icon": "i-users",
        "summary": "Trust-building — fake authority, reassurance, legitimacy claims.",
    },
    {
        "key": "pressure",
        "label": "Pressure",
        "icon": "i-alert",
        "summary": "Urgency and threats — deadlines, suspension, legal action.",
    },
    {
        "key": "payment_demand",
        "label": "Payment Demand",
        "icon": "i-zap",
        "summary": "Money extraction — UPI handles, account numbers, fees.",
    },
]

# --------------------------------------------------------------------------- #
# Vocabulary. Each entry is (compiled_regex, human-readable term shown in UI).
# Kept intentionally conservative: a stage only fires on real scam vocabulary.
# --------------------------------------------------------------------------- #
_VOCAB: Dict[str, List[tuple]] = {
    "approach": [
        (r"\b(hello|hi|hey|namaste|namaskar|salaam)\b", "greeting"),
        (r"\b(good (morning|afternoon|evening)|as(s)?alam)", "time greeting"),
        (r"\b(i am|i'm|this is|calling from|message from|speaking from)\b", "self-intro"),
        (r"\b(customer|account|kyc|loan|dept|department|officer|team)\b.*(here|contacting|reaching)",
         "pretext intro"),
        (r"\b(reached out|contacting you|getting in touch)\b", "outreach"),
    ],
    "rapport": [
        (r"\b(verified|genuine|official|authorised|authorized|legit)\b", "legitimacy claim"),
        (r"\b(government|rbi|sebi|itr|tax|bank of|sbi|hdfc|icici|paytm|phonepe|gpay)\b.*"
         r"\b(official|team|department|representative)\b", "fake authority"),
        (r"\b(don'?t worry|no problem|rest assured|i assure|trust me|be assured)\b", "reassurance"),
        (r"\b(sir|madam|ji|ma'?am)\b", "deference"),
        (r"\b(verified profile|confirmed|secure|safe|guaranteed)\b", "safety claim"),
        (r"\b(help you|assist you|guide you|support you)\b", "helpfulness"),
    ],
    "pressure": [
        (r"\b(urgent|urgently|immediately|asap|quickly|hurry|fast)\b", "urgency"),
        (r"\b(tonight|today only|last (chance|warning|call)|final (notice|warning))\b", "deadline"),
        (r"\b(suspend|suspended|block|blocked|freeze|frozen|deactivate|disable)\b", "account threat"),
        (r"\b(arrest|police|court|legal (action|notice)|fir|cyber crime|cybercrime)\b", "legal threat"),
        (r"\b(expir(e|es|ed|y)|closing|terminated| blacklist)\b", "expiry threat"),
        (r"\b(within \d+|\d+ (minutes|hours|hrs)|before \d)\b", "time box"),
        (r"\b(kyc (expire|pending|update)|account (block|suspend)|money (stuck|blocked))\b",
         "kyc scare"),
    ],
    "payment_demand": [
        (r"(upi|upi id|vpa|@[\w.\-]{2,}\.(com|in|ybl|okaxis|paytm|ibl))", "UPI handle"),
        (r"(₹|rs\.?|inr|rupees?)\s?\d", "rupee amount"),
        (r"\b(bank|a/c|acct|account)\s?(number|no\.?|#|:)?\s?\d{4,}\b", "bank account"),
        (r"\b(ifsc)\b", "IFSC"),
        (r"\b(pay|payment|transfer|send|deposit|remit|credit)\b.*\b(money|amount|fee|rs|₹)",
         "money verb"),
        (r"\b(process(ing)? fee|service charge|verification fee|tax|gst|charge)\b", "fee pretext"),
        (r"\b(qr code|scan|scan karo|scan this)\b", "QR request"),
    ],
}

_COMPILED: Dict[str, List[tuple]] = {
    stage: [(re.compile(pat, re.I), term) for pat, term in entries]
    for stage, entries in _VOCAB.items()
}

# Payment demand is the most severe stage: on a tie it wins.
_STAGE_RANK = {"approach": 0, "rapport": 1, "pressure": 2, "payment_demand": 3}


def _score_message(text: str) -> Dict[str, List[str]]:
    """Returns {stage: [matched terms]} for one message."""
    hits: Dict[str, List[str]] = {}
    for stage, patterns in _COMPILED.items():
        matched = []
        for rx, term in patterns:
            if rx.search(text):
                matched.append(term)
        if matched:
            hits[stage] = matched
    return hits


def classify_transcript(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Classify an ordered transcript into kill-chain stages.

    `messages` is [{id, sender_role, message_text, timestamp}] oldest-first.
    Returns a structure the UI can render directly:
        {
          stages: [{key,label,icon,summary,count,first_ts,last_ts,
                    messages:[{id,role,text,ts,matched}], complete}],
          reached_stage: <deepest stage key with >=1 message or None>,
          total_classified: int,
        }
    """
    per_message: List[Dict[str, Any]] = []
    n = len(messages)
    stage_counts = {s["key"]: 0 for s in STAGES}

    for idx, row in enumerate(messages):
        text = (row.get("message_text") or row.get("text") or "").strip()
        role = (row.get("sender_role") or row.get("role") or "scammer").strip().lower()
        ts = row.get("timestamp") or row.get("ts") or ""
        if not text:
            continue

        hits = _score_message(text)
        if hits:
            # Highest-rank stage wins; ties broken by rank.
            best = max(hits.keys(), key=lambda s: _STAGE_RANK.get(s, 0))
        else:
            # Honest fallback: position-based context, marked as such so the
            # UI can label it "context" rather than claiming a keyword match.
            pos = idx / max(n - 1, 1)
            best = "approach" if pos < 0.25 else ("rapport" if pos < 0.6 else "pressure")
            hits = {best: ["context (position)"]}

        stage_counts[best] += 1
        per_message.append({
            "id": row.get("id"),
            "role": role,
            "text": text,
            "ts": str(ts),
            "stage": best,
            "matched": hits.get(best, []),
            "all_hits": hits,
        })

    stages_out = []
    reached = None
    for st in STAGES:
        key = st["key"]
        msgs = [m for m in per_message if m["stage"] == key]
        if msgs:
            reached = key
        stages_out.append({
            "key": key,
            "label": st["label"],
            "icon": st["icon"],
            "summary": st["summary"],
            "count": len(msgs),
            "first_ts": msgs[0]["ts"] if msgs else None,
            "last_ts": msgs[-1]["ts"] if msgs else None,
            "messages": msgs,
            "complete": len(msgs) > 0,
        })

    return {
        "stages": stages_out,
        "reached_stage": reached,
        "total_classified": sum(stage_counts.values()),
        "counts": stage_counts,
    }
