"""
ScamTrap Bharat — Free Local AI Engine  (primary provider)
==========================================================
A zero-key, zero-quota, offline-after-first-download NLI model that scores the
same four principles the Cognitive Detective uses:

    Principle 1  Authority & Trust Manipulation .......... 35
    Principle 2  Urgency & Fear Engineering .............. 30
    Principle 3  Money-Flow Redirection ................. 20
    Principle 4  Linguistic & Behavioural Cues .......... 15

Why this exists
---------------
Gemini is rate-limited by a billing quota that this deployment does not own, so
the detective used to degrade to plain regex whenever the quota ran out. This
module inverts the order: the free on-device model runs FIRST and is always
available; Gemini is demoted to a backup; the deterministic rules engine stays
last as a guard rail.

How it scores
-------------
One batched forward pass of a multilingual MNLI model over four tailored
hypotheses. The entailment probability for each hypothesis becomes that
principle's `evidence` (0-100). Multilingual XNLI training means English
hypotheses work on Hindi, Hinglish and English inputs alike.

Configuration (env)
-------------------
    SCAMTRAP_LOCAL_AI              1/0  — master switch         (default 1)
    SCAMTRAP_LOCAL_MODEL           HF repo id of an NLI model
    SCAMTRAP_LOCAL_AI_MAXLEN       truncate to N tokens         (default 256)
    SCAMTRAP_LOCAL_AI_WAIT_S       how long a request may wait for warm-up (10)
    SCAMTRAP_LOCAL_AI_CACHE        HF cache dir (default: HF default)

Failure is never fatal: every entry point returns ``None`` so the caller moves
on to the next provider.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger("scamtrap.local_ai")

ENABLED = os.getenv("SCAMTRAP_LOCAL_AI", "1").strip().lower() not in {"0", "false", "no", "off"}
MODEL_ID = os.getenv(
    "SCAMTRAP_LOCAL_MODEL",
    "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli",
)
MAX_LENGTH = int(os.getenv("SCAMTRAP_LOCAL_AI_MAXLEN", "192"))
WAIT_S = float(os.getenv("SCAMTRAP_LOCAL_AI_WAIT_S", "10"))
MIN_TEXT = int(os.getenv("SCAMTRAP_LOCAL_AI_MIN_CHARS", "20"))
CACHE_LIMIT = 512

# Hypotheses — one per principle, phrased as "this message is about X" topics.
# Kept short and topical: XNLI entailment scores collapse on long compound
# hypotheses (measured: ~0 across the board) but separates cleanly on topics.
# English is deliberate — XNLI gives the model a shared cross-lingual space, so
# the same topic matches a Hindi, Hinglish or English premise. Measured on a
# 9-message labelled set (3 benign / 6 scam): benign 0-17, scams 33-86.
HYPOTHESES: Dict[str, str] = {
    "p1_authority": "impersonating a bank or government official",
    "p2_urgency": "an urgent threat or deadline",
    "p3_money": "sending money or paying a fee",
    "p4_language": "sharing an OTP or password",
}
HYPOTHESIS_TEMPLATE = "This message is about {}."

# Anything under this entailment probability is treated as "no signal" so a
# benign message cannot be nudged upward by model noise.
MIN_EVIDENCE = int(os.getenv("SCAMTRAP_LOCAL_AI_MIN_EVIDENCE", "12"))

_lock = threading.Lock()
_ready = threading.Event()
_load_thread: Optional[threading.Thread] = None
_load_error: Optional[str] = None
_pipe: Any = None
_entail_label: Optional[str] = None
_model_tag: Optional[str] = None
_last_attempt = 0.0
_RETRY_AFTER_S = 300.0
_cache: Dict[str, Dict[str, int]] = {}


# ==============================================================================
# Loading
# ==============================================================================
def _resolve_entail_label(model: Any) -> Optional[str]:
    id2label = getattr(getattr(model, "config", None), "id2label", None) or {}
    labels = {int(k): str(v) for k, v in dict(id2label).items()}
    for key in sorted(labels):
        if "entail" in labels[key].lower():
            return labels[key]
    # MNLI convention when label names are unusable: [contradiction, neutral, entailment]
    if len(labels) >= 3:
        return labels.get(max(labels))
    return None


def _do_load() -> None:
    global _pipe, _entail_label, _model_tag, _load_error, _last_attempt
    _last_attempt = time.time()
    try:
        import torch
        from transformers import (  # noqa: F401 — imported for the side effect
            AutoModelForSequenceClassification,
            AutoTokenizer,
            pipeline,
        )

        cache_dir = os.getenv("SCAMTRAP_LOCAL_AI_CACHE") or None
        kwargs: Dict[str, Any] = {}
        if cache_dir:
            kwargs["cache_dir"] = cache_dir

        torch.set_num_threads(max(1, int(os.getenv("SCAMTRAP_LOCAL_AI_THREADS", "8"))))

        tok = AutoTokenizer.from_pretrained(MODEL_ID, **kwargs)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, **kwargs)
        model.eval()
        torch.set_grad_enabled(False)

        entail = _resolve_entail_label(model)
        if not entail:
            raise RuntimeError("model exposes no entailment label: %r"
                               % dict(getattr(model.config, "id2label", {}) or {}))

        clf = pipeline("text-classification", model=model, tokenizer=tok, device=-1)

        with _lock:
            _pipe = clf
            _entail_label = entail
            _model_tag = MODEL_ID.split("/")[-1]
            _load_error = None
        _ready.set()
        log.info("local AI ready: %s (entailment label %r)", MODEL_ID, entail)
        print(">>> [ScamTrap Bharat] Free local AI ready: %s" % _model_tag, flush=True)
    except Exception as exc:                              # noqa: BLE001
        _load_error = "%s: %s" % (type(exc).__name__, exc)
        _last_attempt = time.time()
        _ready.clear()
        log.warning("local AI unavailable (%s); falling through to the next provider", _load_error)
        print(">>> [ScamTrap Bharat] Free local AI unavailable: %s" % _load_error, flush=True)


def warmup_async() -> bool:
    """Kick the model download/load onto a daemon thread. Never blocks."""
    global _load_thread
    if not ENABLED:
        return False
    if _ready.is_set():
        return True
    with _lock:
        if _load_thread and _load_thread.is_alive():
            return False
        if time.time() - _last_attempt < _RETRY_AFTER_S and _load_thread:
            return False
        _load_thread = threading.Thread(target=_do_load, name="local-ai-load", daemon=True)
        _load_thread.start()
    return True


def _ensure_loaded(wait_s: float) -> bool:
    if not ENABLED:
        return False
    if _ready.is_set():
        return True
    warmup_async()
    if wait_s > 0:
        _ready.wait(wait_s)
    return _ready.is_set()


def status() -> Dict[str, Any]:
    """Used by /api/health so the demo can show which engine is live."""
    return {
        "enabled": ENABLED,
        "ready": _ready.is_set(),
        "loading": bool(_load_thread and _load_thread.is_alive()),
        "model": MODEL_ID,
        "label": _model_tag,
        "error": _load_error,
    }


# ==============================================================================
# Scoring
# ==============================================================================
def _entailment_of(result: Any, entail_label: str) -> float:
    if isinstance(result, dict):
        result = [result]
    if not isinstance(result, (list, tuple)) or not result:
        return 0.0
    for item in result:
        if isinstance(item, dict) and str(item.get("label", "")).lower() == entail_label.lower():
            try:
                return max(0.0, min(1.0, float(item.get("score", 0.0))))
            except (TypeError, ValueError):
                return 0.0
    # Label strings can differ in casing/formatting across model revisions.
    for item in result:
        if isinstance(item, dict) and "entail" in str(item.get("label", "")).lower():
            try:
                return max(0.0, min(1.0, float(item.get("score", 0.0))))
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _cache_key(text: str) -> str:
    return hashlib.sha1(text.strip().lower().encode("utf-8", "ignore")).hexdigest()


def score(text: str) -> Optional[Dict[str, int]]:
    """Returns ``{principle_key: evidence_0_100}`` or ``None`` if unavailable.

    ``None`` means "try the next provider" — it is never an error state.
    """
    if not ENABLED:
        return None
    body = (text or "").strip()
    if len(body) < MIN_TEXT:
        return None

    if not _ensure_loaded(WAIT_S):
        return None

    key = _cache_key(body)
    hit = _cache.get(key)
    if hit is not None:
        return hit

    with _lock:
        pipe, entail = _pipe, _entail_label
    if pipe is None or not entail:
        return None

    keys = list(HYPOTHESES)
    inputs = [
        {"text": body, "text_pair": HYPOTHESIS_TEMPLATE.format(HYPOTHESES[k])}
        for k in keys
    ]
    try:
        results = pipe(inputs, top_k=None, truncation=True, max_length=MAX_LENGTH)
    except Exception as exc:                              # noqa: BLE001
        log.warning("local AI inference failed: %s", exc)
        return None

    if not isinstance(results, list) or len(results) != len(keys):
        log.warning("local AI returned %s results for %s inputs",
                    len(results) if isinstance(results, list) else type(results), len(keys))
        return None

    out: Dict[str, int] = {}
    for k, res in zip(keys, results):
        prob = _entailment_of(res, entail)
        ev = int(round(prob * 100.0))
        out[k] = ev if ev >= MIN_EVIDENCE else 0

    if len(_cache) >= CACHE_LIMIT:
        _cache.clear()
    _cache[key] = out
    return out


def available() -> bool:
    """True when the model is loaded and ready to answer synchronously."""
    return bool(ENABLED and _ready.is_set())
