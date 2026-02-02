"""
Lutum Veritas - Backend API Server
==================================
FastAPI Server für die Desktop App.
v2 - Camoufox sync API

Endpoints:
    POST /chat - Chat mit Lutum Veritas
    GET /health - Health Check

Usage:
    uvicorn main:app --port 8420
"""

import sys
import os
import subprocess
import socket
from pathlib import Path
from contextlib import asynccontextmanager

# PyInstaller frozen check
FROZEN = getattr(sys, 'frozen', False)

# Fix für windowed apps: stdout/stderr müssen existieren für uvicorn logging
if FROZEN and sys.stdout is None:
    # Redirect to devnull wenn kein Console
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

# Pfad-Setup: unterschiedlich für frozen vs development
if FROZEN:
    # PyInstaller: _MEIPASS enthält entpackte Daten
    BASE_PATH = Path(sys._MEIPASS)
    sys.path.insert(0, str(BASE_PATH))
else:
    # Development: Parent-Ordner für lutum
    # Wenn wir als Package installiert sind, ist dies vielleicht nicht nötig, aber schadet nicht
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lutum.core.log_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


# === ZOMBIE KILLER ===
def kill_zombie_on_port(port: int = 8420):
    """Killt jeden Prozess der auf dem Port hängt - vor dem Start."""
    try:
        # Check ob Port frei ist
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('127.0.0.1', port))
            if result != 0:
                return  # Port frei, alles gut

        logger.warning("Port %s belegt - suche Zombie...", port)

        # Windows: netstat + taskkill
        if sys.platform == 'win32':
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                # LISTENING (EN) oder ABHÖREN (DE)
                if f':{port}' in line and ('LISTENING' in line.upper() or 'ABH' in line.upper()):
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit():
                        logger.info("Killing zombie PID %s on port %s...", pid, port)
                        subprocess.run(
                            ['powershell', '-Command', f'Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue'],
                            capture_output=True
                        )
                        logger.info("Zombie killed!")
                        return
        else:
            # Linux/Mac: lsof + kill
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                pid = result.stdout.strip()
                logger.info("Killing zombie PID %s on port %s...", pid, port)
                subprocess.run(['kill', '-9', pid])
                logger.info("Zombie killed!")

    except Exception as e:
        logger.warning("Zombie killer failed: %s", e)


# Beim Import ausführen
kill_zombie_on_port(8420)


# === AUTO-INSTALL DEPENDENCIES (nur wenn NICHT frozen) ===
if not FROZEN:
    IMPORT_NAMES = {
        "beautifulsoup4": "bs4",
        "sse-starlette": "sse_starlette",
        "camoufox": "camoufox",
        "search-engines-scraper-tasos": "search_engines",
        "ddgs": "ddgs",
    }

    def ensure_dependencies():
        """Installiert fehlende Dependencies automatisch beim Start."""
        # Suche requirements.txt im gleichen Ordner
        requirements_file = Path(__file__).parent / "requirements.txt"

        if not requirements_file.exists():
            # Wenn nicht gefunden, vielleicht sind wir installiert und requirements fehlen?
            # Wenn wir als Package laufen, verlassen wir uns auf pip install
            # Aber wir loggen nur warning
            logger.warning("requirements.txt nicht gefunden (okay if installed as package)!")
            return

        # Lese required packages
        required = []
        for line in requirements_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pkg = line.split(">=")[0].split("==")[0].split("[")[0].strip()
                required.append((pkg, line))

        # Prüfe welche fehlen
        missing = []
        for pkg, full_spec in required:
            import_name = IMPORT_NAMES.get(pkg, pkg.replace("-", "_"))
            try:
                __import__(import_name)
            except ImportError:
                missing.append(full_spec)

        if missing:
            logger.info("Installiere %s fehlende Dependencies...", len(missing))
            for pkg in missing:
                logger.info("  → %s", pkg)

            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    "-q", "--user", *missing
                ])
                logger.info("Dependencies installiert!")

                if any("camoufox" in m for m in missing):
                    logger.info("Lade Camoufox Browser herunter...")
                    subprocess.check_call([sys.executable, "-m", "camoufox", "fetch"])
                    logger.info("Camoufox Browser ready!")

                logger.info("Dependencies installiert - bitte Backend neu starten!")
                logger.info("Drücke Enter und starte dann erneut.")
                input()
                sys.exit(0)

            except subprocess.CalledProcessError as e:
                logger.error("pip install failed: %s", e)
                logger.warning("Bitte manuell ausführen: pip install -r requirements.txt")

    ensure_dependencies()
else:
    logger.info("Running as frozen executable - skipping dependency check")


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Imports angepasst für Package vs Script Execution
if __package__ is None or __package__ == '':
    # Script Mode (z.B. python backend/main.py)
    sys.path.append(str(Path(__file__).parent))
    from routes.chat import router as chat_router
    from routes.health import router as health_router
    from routes.research import router as research_router
else:
    # Package Mode (z.B. uvx run)
    from .routes.chat import router as chat_router
    from .routes.health import router as health_router
    from .routes.research import router as research_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup und Shutdown Events."""
    logger.info("Lutum Veritas Backend starting...")
    logger.info("Server ready on http://localhost:8420")
    yield
    logger.info("Lutum Veritas Backend shutting down...")


app = FastAPI(
    title="Lutum Veritas API",
    description="Web Scraping + LLM Analysis Backend",
    version="1.0.0",
    lifespan=lifespan
)

# === SECURITY HEADERS MIDDLEWARE ===
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Enable XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Prevent caching of sensitive data if it's API, but allow caching for static
        # Simple heuristic: if path starts with /api or /chat or /research or /health, no cache
        path = request.url.path
        if any(path.startswith(p) for p in ["/chat", "/research", "/health"]):
             response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
             response.headers["Pragma"] = "no-cache"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS für Frontend - Lokale App, daher permissiv
# Tauri apps use tauri://localhost origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lokale App - kein externer Zugriff möglich
    allow_credentials=False,
    allow_methods=["*"],  # GET, POST, OPTIONS etc.
    allow_headers=["*"],
)

# Router registrieren
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(research_router)

# Mount Static Files (Frontend)
# Wir suchen den 'www' Ordner relativ zu dieser Datei
www_path = Path(__file__).parent / "www"

if www_path.exists():
    logger.info(f"Serving static files from {www_path}")
    # Mount assets, etc.
    app.mount("/assets", StaticFiles(directory=str(www_path / "assets")), name="assets")

    # Catch-all für SPA Routing (muss am Ende kommen)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API requests wurden schon von Routern behandelt.
        # Check ob Datei existiert (z.B. favicon.ico)
        try:
            file_path = (www_path / full_path).resolve()
            if file_path.is_relative_to(www_path.resolve()) and file_path.exists() and file_path.is_file():
                 return FileResponse(file_path)
        except Exception:
            pass

        # Fallback auf index.html für React Router
        return FileResponse(www_path / "index.html")
else:
    logger.warning(f"Static files not found at {www_path}. Web UI will not be available.")


def start():
    """Entry point for the application script."""
    import uvicorn
    import webbrowser
    import threading
    import time

    def open_browser():
        time.sleep(1.5)
        print("\n" + "="*50)
        print("Lutum Veritas is running!")
        print("Open your browser at: http://localhost:8420")
        print("="*50 + "\n")
        try:
             webbrowser.open("http://localhost:8420")
        except:
             pass

    # Wenn wir im Script Mode sind oder uvx, Browser öffnen
    if os.environ.get("LUTUM_NO_BROWSER") != "1":
        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=8420)

if __name__ == "__main__":
    start()
