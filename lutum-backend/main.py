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
import subprocess
import socket
from pathlib import Path
from contextlib import asynccontextmanager


# === ZOMBIE KILLER ===
def kill_zombie_on_port(port: int = 8420):
    """Killt jeden Prozess der auf dem Port hängt - vor dem Start."""
    try:
        # Check ob Port frei ist
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('127.0.0.1', port))
            if result != 0:
                return  # Port frei, alles gut

        print(f"[WARN] Port {port} belegt - suche Zombie...")

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
                        print(f"[INFO] Killing zombie PID {pid} on port {port}...")
                        subprocess.run(
                            ['powershell', '-Command', f'Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue'],
                            capture_output=True
                        )
                        print(f"[OK] Zombie killed!")
                        return
        else:
            # Linux/Mac: lsof + kill
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                pid = result.stdout.strip()
                print(f"[INFO] Killing zombie PID {pid} on port {port}...")
                subprocess.run(['kill', '-9', pid])
                print(f"[OK] Zombie killed!")

    except Exception as e:
        print(f"[WARN] Zombie killer failed: {e}")


# Beim Import ausführen
kill_zombie_on_port(8420)


# === AUTO-INSTALL DEPENDENCIES ===
# Package-Name → Import-Name Mapping (wenn unterschiedlich)
IMPORT_NAMES = {
    "beautifulsoup4": "bs4",
    "sse-starlette": "sse_starlette",
    "camoufox": "camoufox",
    "search-engines-scraper-tasos": "search_engines",
    "ddgs": "ddgs",
}


def ensure_dependencies():
    """Installiert fehlende Dependencies automatisch beim Start."""
    requirements_file = Path(__file__).parent / "requirements.txt"

    if not requirements_file.exists():
        print("[WARN] requirements.txt nicht gefunden!")
        return

    # Lese required packages
    required = []
    for line in requirements_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            # Package name extrahieren (ohne version specifier)
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
        print(f"[INFO] Installiere {len(missing)} fehlende Dependencies...")
        for pkg in missing:
            print(f"  → {pkg}")

        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-q", "--user", *missing
            ])
            print("[OK] Dependencies installiert!")

            # Camoufox braucht Browser-Download nach Install
            if any("camoufox" in m for m in missing):
                print("[INFO] Lade Camoufox Browser herunter...")
                subprocess.check_call([sys.executable, "-m", "camoufox", "fetch"])
                print("[OK] Camoufox Browser ready!")

            # Nach Installation: User muss manuell neustarten
            print("[INFO] Dependencies installiert - bitte Backend neu starten!")
            print("[INFO] Drücke Enter und starte dann erneut.")
            input()
            sys.exit(0)

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] pip install failed: {e}")
            print("[WARN] Bitte manuell ausführen: pip install -r requirements.txt")

# Beim Import ausführen
ensure_dependencies()


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Füge lutum zum Path hinzu - .resolve() für absolute Pfade
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lutum.core.log_config import get_logger
from routes.chat import router as chat_router
from routes.health import router as health_router
from routes.research import router as research_router

logger = get_logger(__name__)


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

# CORS für Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tauri App
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router registrieren
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(research_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8420)
