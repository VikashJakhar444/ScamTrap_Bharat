import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import (
    BASE_DIR, STORAGE_DIR, SANDBOX_MODE,
    GENERATED_BAITS_DIR, GENERATED_PDFS_DIR,
)
from backend.database.db import init_db
from backend.routes.checker import router as checker_router
from backend.routes.reports import router as reports_router
from backend.routes.co_pilot import router as co_pilot_router
from backend.routes.honeypot import router as honeypot_router

app = FastAPI(
    title="ScamTrap Bharat - Active Pre-Fraud Citizen Defense & Honeypot Engine",
    description="Active Pre-Fraud Cyber Safety Platform for MY Bharat / IIT Bombay Track",
    version="1.0.0"
)

# CORS: same-origin app (frontend is served by this process). No wildcard.
_app_port = int(os.getenv("PORT", "8050"))
_allowed_origins = [
    f"http://127.0.0.1:{_app_port}",
    f"http://localhost:{_app_port}",
    f"http://127.0.0.1:{_app_port + 2000}",
    f"http://localhost:{_app_port + 2000}",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()
    print(">>> [ScamTrap Bharat] SQLite Database & Seed Data Initialized Successfully.")

    # Warm the free on-device AI on a background thread so the first analyse
    # request does not pay the model load. Failures are logged, never fatal.
    try:
        from backend.services import local_ai
        if local_ai.warmup_async():
            print(">>> [ScamTrap Bharat] Free local AI warming up in the background...")
    except Exception as exc:                              # noqa: BLE001
        print(">>> [ScamTrap Bharat] Free local AI warm-up skipped: %s" % exc)

# Register API Routers
app.include_router(checker_router)
app.include_router(reports_router)
app.include_router(co_pilot_router)
app.include_router(honeypot_router)

# Health Check Route
@app.get("/api/health")
def health_check():
    try:
        from backend.services import local_ai
        ai = local_ai.status()
    except Exception as exc:                              # noqa: BLE001
        ai = {"enabled": False, "ready": False, "error": str(exc)}
    return {
        "status": "healthy",
        "app_name": "ScamTrap Bharat",
        "sandbox_mode": SANDBOX_MODE,
        "database": "storage/scamtrap.db (Connected)",
        "local_ai": ai
    }

# Mount ONLY the generated bait / PDF directories. The whole `storage/`
# tree also contains scamtrap.db and forensic investigation logs — those
# must never be statically served.
app.mount("/storage/generated_baits", StaticFiles(directory=str(GENERATED_BAITS_DIR)), name="baits")
app.mount("/storage/generated_pdfs", StaticFiles(directory=str(GENERATED_PDFS_DIR)), name="pdfs")

# Mount Frontend Static Assets
FRONTEND_DIR = BASE_DIR / "frontend"
if (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

# Serve Index and Verification Pages
@app.get("/")
def serve_home():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/verify_receipt.html")
@app.get("/receipt/{trap_code}")
def serve_receipt(trap_code: str = ""):
    return FileResponse(FRONTEND_DIR / "verify_receipt.html")

if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
