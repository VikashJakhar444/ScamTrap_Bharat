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
