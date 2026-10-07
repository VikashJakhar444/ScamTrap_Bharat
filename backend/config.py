import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

PORT = int(os.getenv("PORT", 8050))
HOST = os.getenv("HOST", "0.0.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SANDBOX_MODE = os.getenv("SANDBOX_MODE", "true").lower() == "true"
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "storage/scamtrap.db")
STORAGE_DIR = BASE_DIR / "storage"
GENERATED_BAITS_DIR = STORAGE_DIR / "generated_baits"
GENERATED_PDFS_DIR = STORAGE_DIR / "generated_pdfs"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ---- Free reply chain (Tab 2 honeypot) -------------------------------------
# Order matters: Groq (primary, key in .env) -> Ollama (local, free) ->
# Gemini (rare, last resort - quota burns fast) -> local composer.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")

# Verified live against this Groq key (2026-10-07):
#   openai/gpt-oss-120b -> 0.6-1.6s, best target discipline
#   qwen/qwen3.8-27b    -> 0.2-3.3s, strong Hinglish
#   openai/gpt-oss-20b  -> 0.5-3.6s, adequate fallback
#   llama-3.3-70b / llama-3.1-8b / qwen3-32b -> 404 on this key
_GROQ_CANDIDATES = [
    os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "allam-2-7b",
]
GROQ_MODELS = list(dict.fromkeys(m for m in _GROQ_CANDIDATES if m))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
# Fastest-warm local models first. Big 4B+ models time out on this box.
_OLLAMA_CANDIDATES = [
    os.getenv("OLLAMA_MODEL", "phi3:mini"),
    "phi3:mini",
    "llama3:latest",
    "gemma3:4b",
]
OLLAMA_MODELS = list(dict.fromkeys(m for m in _OLLAMA_CANDIDATES if m))

# Gemini is the *third* option on purpose: this key has almost no free quota.
_GEMINI_REPLY_CANDIDATES = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
]
GEMINI_REPLY_MODELS = list(dict.fromkeys(m for m in _GEMINI_REPLY_CANDIDATES if m))

# Model candidates, most-preferred first. Verified live against this key:
#   gemini-3.8-flash -> works but is flaky (504 under load)
#   gemini-3.7-flash / gemini-3.6-flash -> stable
#   gemini-flash-latest -> 503 under spikes
#   gemini-3.5-flash -> 429 quota on this key
#   gemini-2.5-flash / gemini-2.0-flash / *-lite -> 404, retired
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
_GEMINI_CANDIDATES = [
    GEMINI_MODEL,
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash",
]
GEMINI_MODEL_FALLBACKS = list(dict.fromkeys(m for m in _GEMINI_CANDIDATES if m))

# Ensure directories exist
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_BAITS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_PDFS_DIR.mkdir(parents=True, exist_ok=True)
