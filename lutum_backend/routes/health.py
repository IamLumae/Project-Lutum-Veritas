"""
Health Check Endpoint
=====================
Simple health check für Frontend und Monitoring.
Camoufox auto-download with real progress tracking.
"""

import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from lutum.core.log_config import get_logger


def _get_proxy_config() -> Optional[str]:
    """Get proxy configuration from environment variables. Fixes SOCKS proxy URL format."""
    proxy = os.environ.get("ALL_PROXY") or os.environ.get("all_proxy")
    if not proxy:
        proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if not proxy:
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    if proxy and proxy.startswith("socks://"):
        proxy = proxy.replace("socks://", "socks5://", 1)
        logger.debug(f"Fixed SOCKS proxy URL: {proxy}")

    return proxy


logger = get_logger(__name__)
router = APIRouter(tags=["Health"])

# Camoufox download state
_camoufox_download_in_progress = False
_camoufox_download_error: str | None = None
_camoufox_download_progress: int = 0  # 0-100 percent
_camoufox_download_status: str = ""  # Human-readable status message
_CAMOUFOX_EXPECTED_SIZE_MB = 530  # Expected download+extract size ~530 MB


@router.get("/health")
async def health_check():
    """Health Check Endpoint."""
    return {"status": "ok", "service": "lutum-veritas"}


def _check_camoufox_installed() -> bool:
    """Check if Camoufox browser binary is actually installed."""
    try:
        from camoufox.pkgman import camoufox_path

        path = camoufox_path(download_if_missing=False)
        # Check for Windows executable
        browser_exe_windows = Path(path) / "camoufox.exe"
        if browser_exe_windows.exists():
            return True
        # Check for Linux/macOS executable
        browser_exe_unix = Path(path) / "camoufox"
        if browser_exe_unix.exists():
            return True
        # Also check if camoufox is in PATH
        import shutil

        if shutil.which("camoufox"):
            return True
        return False
    except (FileNotFoundError, ImportError, Exception):
        # Fallback: check if camoufox is in PATH
        try:
            import shutil

            return shutil.which("camoufox") is not None
        except Exception:
            return False


def _get_camoufox_dir_size_mb() -> float:
    """Get current size of camoufox download directory in MB."""
    # Try Windows path first
    camo_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "camoufox"
    # Fallback to Linux/macOS path
    if not camo_dir.exists():
        home = Path.home()
        camo_dir = home / ".cache" / "camoufox"
    if not camo_dir.exists():
        return 0.0
    total = 0
    try:
        for f in camo_dir.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except (OSError, PermissionError):
        pass
    return total / (1024 * 1024)


def _progress_monitor():
    """Monitor download directory size and update progress percentage."""
    global _camoufox_download_progress, _camoufox_download_status
    while _camoufox_download_in_progress:
        size_mb = _get_camoufox_dir_size_mb()
        # Calculate progress: 0-95% based on directory size, 100% when done
        pct = min(int((size_mb / _CAMOUFOX_EXPECTED_SIZE_MB) * 95), 95)
        if pct > _camoufox_download_progress and _camoufox_download_progress < 95:
            _camoufox_download_progress = pct
        if size_mb < 1:
            _camoufox_download_status = "Download wird gestartet..."
        elif size_mb < _CAMOUFOX_EXPECTED_SIZE_MB * 0.9:
            _camoufox_download_status = (
                f"Herunterladen... ({size_mb:.0f} / ~{_CAMOUFOX_EXPECTED_SIZE_MB} MB)"
            )
        else:
            _camoufox_download_status = "Wird entpackt und eingerichtet..."
        time.sleep(1)


def _download_camoufox_background():
    """Download Camoufox in background thread with progress tracking."""
    global _camoufox_download_in_progress, _camoufox_download_error
    global _camoufox_download_progress, _camoufox_download_status
    _camoufox_download_in_progress = True
    _camoufox_download_error = None
    _camoufox_download_progress = 0
    _camoufox_download_status = "Download wird vorbereitet..."

    # Start progress monitor thread
    monitor = threading.Thread(target=_progress_monitor, daemon=True)
    monitor.start()

    try:
        logger.info("Starting Camoufox browser download...")
        from camoufox.pkgman import CamoufoxFetcher

        fetcher = CamoufoxFetcher()
        fetcher.install()
        _camoufox_download_progress = 100
        _camoufox_download_status = "Browser-Engine bereit!"
        logger.info("Camoufox browser download complete!")
    except ImportError as e:
        _camoufox_download_error = f"camoufox package not available: {e}"
        _camoufox_download_status = f"Fehler: {e}"
        logger.error(f"Camoufox download failed: {e}")
    except Exception as e:
        _camoufox_download_error = str(e)
        _camoufox_download_status = f"Fehler: {e}"
        logger.error(f"Camoufox download error: {e}")
    finally:
        _camoufox_download_in_progress = False


def auto_start_camoufox_download():
    """Called from main.py on startup - auto-starts download if needed."""
    if _check_camoufox_installed():
        logger.info("Camoufox browser already installed")
        return
    if _camoufox_download_in_progress:
        return
    logger.info("Camoufox browser not found - starting auto-download")
    thread = threading.Thread(target=_download_camoufox_background, daemon=True)
    thread.start()


@router.get("/health/camoufox")
async def camoufox_status():
    """
    Check Camoufox browser status with real progress.

    Returns:
        - ready: browser installed and ready
        - downloading: download in progress
        - progress: 0-100 based on actual download size
        - status: human-readable status message
        - error: error message if failed
    """
    is_installed = _check_camoufox_installed()

    return {
        "ready": is_installed,
        "downloading": _camoufox_download_in_progress,
        "progress": _camoufox_download_progress,
        "status": _camoufox_download_status,
        "error": _camoufox_download_error,
    }


@router.get("/health/debug/ddg")
async def debug_ddg_search():
    """Debug endpoint: test DDG search directly."""
    try:
        from ddgs import DDGS

        proxy = _get_proxy_config()
        with DDGS(proxy=proxy) as ddgs:
            results = list(
                ddgs.text(
                    "test query python",
                    region="wt-wt",
                    safesearch="moderate",
                    max_results=3,
                )
            )
        return {
            "status": "ok",
            "results": len(results),
            "first": results[0] if results else None,
        }
    except Exception as e:
        import traceback

        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@router.get("/health/debug/scrape")
async def debug_scrape_test():
    """Debug endpoint: test full DDG search + camoufox scrape pipeline."""
    import traceback

    result = {"ddg": None, "scrape": None}

    # Step 1: DDG search
    try:
        from ddgs import DDGS

        proxy = _get_proxy_config()
        with DDGS(proxy=proxy) as ddgs:
            search_results = list(
                ddgs.text(
                    "python tutorial",
                    region="wt-wt",
                    safesearch="moderate",
                    max_results=3,
                )
            )
        result["ddg"] = {
            "status": "ok",
            "count": len(search_results),
            "urls": [r.get("href", "") for r in search_results],
        }
    except Exception as e:
        result["ddg"] = {
            "status": "error",
            "error": str(e),
            "tb": traceback.format_exc(),
        }
        return result

    # Step 2: Camoufox scrape first URL
    if search_results:
        test_url = search_results[0].get("href", "")
        try:
            from camoufox.async_api import AsyncCamoufox
            from camoufox import DefaultAddons

            async with AsyncCamoufox(
                headless=True, exclude_addons=[DefaultAddons.UBO]
            ) as browser:
                page = await browser.new_page()
                await page.goto(test_url, timeout=15000)
                text = await page.evaluate("() => document.body.innerText")
                result["scrape"] = {
                    "status": "ok",
                    "url": test_url,
                    "text_length": len(text),
                    "preview": text[:200],
                }
        except Exception as e:
            result["scrape"] = {
                "status": "error",
                "url": test_url,
                "error": str(e),
                "tb": traceback.format_exc(),
            }

    return result


@router.post("/health/camoufox/install")
async def install_camoufox():
    """Start Camoufox browser download if not already installed."""
    if _check_camoufox_installed():
        return {"status": "already_installed"}
    if _camoufox_download_in_progress:
        return {"status": "downloading"}

    thread = threading.Thread(target=_download_camoufox_background, daemon=True)
    thread.start()
    return {"status": "started"}
