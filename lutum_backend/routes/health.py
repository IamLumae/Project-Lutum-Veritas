"""
Health Check Endpoint
=====================
Simple health check für Frontend und Monitoring.
"""

import sys
import subprocess
import threading
from pathlib import Path

from fastapi import APIRouter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from lutum.core.log_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])

# Camoufox download state
_camoufox_download_in_progress = False
_camoufox_download_error: str | None = None
_camoufox_download_progress: int = 0  # 0-100 percent


@router.get("/health")
async def health_check():
    """
    Health Check Endpoint.

    Gibt Status zurück wenn Server läuft.
    Wird vom Frontend genutzt um Backend-Verfügbarkeit zu prüfen.

    Returns:
        Dict mit status und service name
    """
    logger.debug("Health check requested")

    try:
        response = {
            "status": "ok",
            "service": "lutum-veritas"
        }
        logger.debug("Health check OK")
        return response

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "service": "lutum-veritas",
            "error": str(e)
        }


def _check_camoufox_installed() -> bool:
    """Check if Camoufox browser binary is actually installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "camoufox", "path"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return False

        # Check if the path actually exists AND contains the browser binary
        cache_path = result.stdout.strip()
        if not cache_path:
            return False

        browser_exe = Path(cache_path) / "camoufox.exe"
        return browser_exe.exists()
    except Exception:
        return False


def _download_camoufox_background():
    """Download Camoufox in background thread with progress tracking."""
    global _camoufox_download_in_progress, _camoufox_download_error, _camoufox_download_progress
    _camoufox_download_in_progress = True
    _camoufox_download_error = None
    _camoufox_download_progress = 0

    try:
        logger.info("Starting Camoufox browser download...")

        # Run with stderr capture to parse progress
        import re
        process = subprocess.Popen(
            [sys.executable, "-m", "camoufox", "fetch"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Read stderr line by line for progress updates
        # Format: " 39%|###9      | 208M/530M [01:46<03:05, 1.73MiB/s]"
        progress_pattern = re.compile(r'(\d+)%\|')

        for line in process.stderr:
            match = progress_pattern.search(line)
            if match:
                _camoufox_download_progress = int(match.group(1))

        process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, "camoufox fetch")

        _camoufox_download_progress = 100
        logger.info("Camoufox browser download complete!")
    except subprocess.CalledProcessError as e:
        _camoufox_download_error = str(e)
        logger.error(f"Camoufox download failed: {e}")
    except Exception as e:
        _camoufox_download_error = str(e)
        logger.error(f"Camoufox download error: {e}")
    finally:
        _camoufox_download_in_progress = False


@router.get("/health/camoufox")
async def camoufox_status():
    """
    Check Camoufox browser status.

    Returns:
        - ready: true if browser is installed and ready
        - downloading: true if download is in progress
        - progress: download progress 0-100
        - error: error message if download failed
    """
    global _camoufox_download_in_progress, _camoufox_download_error, _camoufox_download_progress

    is_installed = _check_camoufox_installed()

    return {
        "ready": is_installed,
        "downloading": _camoufox_download_in_progress,
        "progress": _camoufox_download_progress,
        "error": _camoufox_download_error
    }


@router.post("/health/camoufox/install")
async def install_camoufox():
    """
    Start Camoufox browser download if not already installed.

    Returns status of the installation.
    """
    global _camoufox_download_in_progress

    if _check_camoufox_installed():
        return {"status": "already_installed"}

    if _camoufox_download_in_progress:
        return {"status": "downloading"}

    # Start download in background
    thread = threading.Thread(target=_download_camoufox_background, daemon=True)
    thread.start()

    return {"status": "started"}
