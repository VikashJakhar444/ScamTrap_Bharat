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

# Ensure directories exist
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_BAITS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_PDFS_DIR.mkdir(parents=True, exist_ok=True)
