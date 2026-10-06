import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import BASE_DIR, STORAGE_DIR, SANDBOX_MODE
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

# Enable CORS for local cross-origin development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()
    print(">>> [ScamTrap Bharat] SQLite Database & Seed Data Initialized Successfully.")

# Register API Routers
app.include_router(checker_router)
app.include_router(reports_router)
app.include_router(co_pilot_router)
app.include_router(honeypot_router)

# Health Check Route
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app_name": "ScamTrap Bharat",
        "sandbox_mode": SANDBOX_MODE,
        "database": "storage/scamtrap.db (Connected)"
    }

# Mount Storage Directory for Generated Baits & PDFs
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

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
def serve_receipt():
    return FileResponse(FRONTEND_DIR / "verify_receipt.html")

if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
