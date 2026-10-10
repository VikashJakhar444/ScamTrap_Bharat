"""
ScamTrap Bharat · one-shot runner.

What it does
  1. Verifies Python deps (installs only the missing ones)
  2. Verifies WhatsApp-bridge npm deps (installs only if node_modules is absent)
  3. Starts the FastAPI backend (uvicorn :8050)
  4. Starts the WhatsApp bridge (node :3000)
  5. Ctrl+C shuts both down cleanly

Usage
  python run.py            # install-if-needed + start both
  python run.py --check    # report status only, start nothing
  python run.py --no-bridge
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_PORT = 8050
BRIDGE_DIR = ROOT / "whatsapp-bridge"
LOG_DIR = ROOT / "storage" / "logs"

# (import-name, pip-name)
PY_DEPS = [
    ("fastapi", "fastapi>=0.110.0"),
    ("uvicorn", "uvicorn[standard]>=0.28.0"),
    ("pydantic", "pydantic>=2.6.0"),
    ("PIL", "pillow>=10.2.0"),
    ("reportlab", "reportlab>=4.1.0"),
    ("google.genai", "google-genai>=1.0.0"),
    ("dotenv", "python-dotenv>=1.0.1"),
    ("requests", "requests>=2.31.0"),
    ("jinja2", "jinja2>=3.1.3"),
    ("aiofiles", "aiofiles>=23.2.1"),
    ("multipart", "python-multipart>=0.0.9"),
    ("cv2", "opencv-python>=4.9.0"),
]

# Heavy ML extras — reported but never auto-installed (they pull GBs).
OPTIONAL_PY = [
    ("transformers", "transformers>=4.40.0"),
    ("torch", "torch>=2.2.0"),
    ("huggingface_hub", "huggingface_hub>=0.23.0"),
]

IS_WIN = os.name == "nt"


def _c(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def ok(msg: str) -> None:
    print(f"  {_c('OK  ', '32')} {msg}")


def warn(msg: str) -> None:
    print(f"  {_c('SKIP', '33')} {msg}")


def bad(msg: str) -> None:
    print(f"  {_c('FAIL', '31')} {msg}")


def step(msg: str) -> None:
    print(f"\n{_c(msg, '1;36')}")


def have(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def check_python_deps(auto_install: bool) -> bool:
    step("1/4 · Python dependencies")
    missing = [(mod, pkg) for mod, pkg in PY_DEPS if not have(mod)]
    for mod, pkg in PY_DEPS:
        (ok if have(mod) else warn)(pkg)
    optional_missing = [pkg for mod, pkg in OPTIONAL_PY if not have(mod)]
    if optional_missing:
        warn(f"optional (not required for Mode 1/2): {', '.join(optional_missing)}")

    if not missing:
        ok("all required packages present")
        return True
    if not auto_install:
        bad(f"missing: {', '.join(p for _, p in missing)} — run: pip install {' '.join(p for _, p in missing)}")
        return False

    print(f"\n  installing {len(missing)} package(s)…")
    cmd = [sys.executable, "-m", "pip", "install", "--quiet"] + [p for _, p in missing]
    try:
        subprocess.run(cmd, check=True, cwd=ROOT)
    except subprocess.CalledProcessError as exc:
        bad(f"pip install failed ({exc.returncode})")
        return False
    still = [p for mod, p in missing if not have(mod)]
    if still:
        bad(f"still missing after install: {', '.join(still)}")
        return False
    ok("installed and verified")
    return True


def check_bridge_deps(auto_install: bool) -> bool:
    step("2/4 · WhatsApp bridge (npm)")
    if not BRIDGE_DIR.exists():
        bad(f"{BRIDGE_DIR} not found")
        return False
    modules_ok = (BRIDGE_DIR / "node_modules" / "whatsapp-web.js").exists()
    express_ok = (BRIDGE_DIR / "node_modules" / "express").exists()
    if modules_ok and express_ok:
        ok("node_modules present (whatsapp-web.js, express)")
        return True
    if not auto_install:
        bad("node_modules incomplete — run: cd whatsapp-bridge && npm install")
        return False

    print("  npm install (first run downloads Chromium, can take a few minutes)…")
    try:
        subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund"],
            check=True, cwd=BRIDGE_DIR,
            shell=IS_WIN,  # npm is npm.cmd on Windows
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        bad(f"npm install failed: {exc}")
        return False
    ok("npm dependencies installed")
    return True


def port_free(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) != 0


def start_backend(log_path: Path) -> subprocess.Popen | None:
    step("3/4 · Backend (uvicorn :8050)")
    if not port_free(BACKEND_PORT):
        warn(f"port {BACKEND_PORT} already in use — assuming backend is running")
        return None
    log = open(log_path, "a", encoding="utf-8", errors="replace")
    cmd = [sys.executable, "-m", "uvicorn", "backend.main:app",
           "--host", "127.0.0.1", "--port", str(BACKEND_PORT)]
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    ok(f"started (pid {proc.pid}) → {log_path}")
    return proc


def start_bridge(log_path: Path) -> subprocess.Popen | None:
    step("4/4 · WhatsApp bridge (node :3000)")
    if not port_free(3000):
        warn("port 3000 already in use — assuming bridge is running")
        return None
    entry = BRIDGE_DIR / "index.js"
    if not entry.exists():
        bad(f"{entry} not found")
        return None
    log = open(log_path, "a", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(["node", str(entry)], cwd=BRIDGE_DIR,
                            stdout=log, stderr=subprocess.STDOUT)
    ok(f"started (pid {proc.pid}) → {log_path}")
    return proc


def wait_health(timeout: float = 12.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{BACKEND_PORT}/api/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="ScamTrap Bharat runner")
    ap.add_argument("--check", action="store_true", help="report status, start nothing")
    ap.add_argument("--no-install", action="store_true", help="never auto-install, fail instead")
    ap.add_argument("--no-bridge", action="store_true", help="start only the backend")
    args = ap.parse_args()

    print(_c("ScamTrap Bharat · runner", "1;35"))
    print(f"  root: {ROOT}")

    if args.check:
        check_python_deps(False)
        check_bridge_deps(False)
        print(f"\n  backend port {BACKEND_PORT}: {'FREE' if port_free(BACKEND_PORT) else 'IN USE'}")
        print(f"  bridge  port 3000:    {'FREE' if port_free(3000) else 'IN USE'}")
        return 0

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not check_python_deps(not args.no_install):
        return 1
    if not args.no_bridge and not check_bridge_deps(not args.no_install):
        return 1

    procs: list[subprocess.Popen] = []
    backend = start_backend(LOG_DIR / "backend.log")
    if backend:
        procs.append(backend)
    bridge = None
    if not args.no_bridge:
        bridge = start_bridge(LOG_DIR / "bridge.log")
        if bridge:
            procs.append(bridge)

    print("\n" + _c("waiting for backend…", "1;36"))
    if wait_health():
        print(f"  {_c('OK  ', '32')} http://127.0.0.1:{BACKEND_PORT} is healthy")
        print(f"  open http://127.0.0.1:{BACKEND_PORT}/ in your browser")
    else:
        bad(f"backend did not answer in time — see {LOG_DIR / 'backend.log'}")

    if bridge:
        print(f"  bridge log: {LOG_DIR / 'bridge.log'} (QR appears there / in console)")
    print(_c("\nPress Ctrl+C to stop everything.", "1;33"))

    def shutdown(*_a):
        print("\nshutting down…")
        for p in procs:
            if p.poll() is None:
                try:
                    p.terminate()
                except OSError:
                    pass
        time.sleep(1.0)
        for p in procs:
            if p.poll() is None:
                try:
                    p.kill()
                except OSError:
                    pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1.0)
            for p in procs:
                if p.poll() is not None:
                    print(bad(f"process exited (code {p.returncode}) — check logs"))
                    shutdown()
    except KeyboardInterrupt:
        shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
