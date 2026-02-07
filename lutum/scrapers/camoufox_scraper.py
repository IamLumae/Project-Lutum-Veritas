"""
Lutum Veritas - Camoufox Scraper (John Wick Edition)
====================================================
Stufe 5: The scraper that can scrape ANYTHING from ANY site.

Camoufox = Firefox with C++-level fingerprint spoofing.
0% detection rate on fingerprint tests.
83.3% bypass rate on anti-bot systems (Cloudflare, Datadome, Akamai).

ACHTUNG: Braucht camoufox: pip install camoufox[geoip] && python -m camoufox fetch

Security:
- All URLs are validated before scraping (SSRF protection)
- Private IPs and internal hostnames are blocked
- Response size limits prevent memory exhaustion
"""

import asyncio
from typing import Optional, Tuple

from lutum.scrapers.base import BaseScraper
from lutum.core.config import ScraperConfig
from lutum.core.security import validate_url, validate_urls, sanitize_error

# Security limits
MAX_URLS_PER_BATCH = 100
MAX_RESPONSE_SIZE = 10_000_000  # 10MB
MIN_RATE_LIMIT_DELAY = 0.5  # 500ms between requests


class CamoufoxScraper(BaseScraper):
    """
    Stufe 5: John Wick of scrapers - gets through everything.

    Uses Camoufox (Firefox with C++ fingerprint spoofing) for
    maximum stealth against Cloudflare, Datadome, Akamai etc.

    Wenn Stufe 1-4 versagen, Stufe 5 schafft es.
    """

    level = 5
    name = "CAMOUFOX"
    description = "Firefox C++ Fork - 0% Detection, Maximum Stealth"

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self._camoufox = None
        self.wait_after_load = 2.0  # Reduziert von 5s - RAM sparen
        self.max_body_wait = 5.0    # Reduziert von 10s

    def _ensure_camoufox(self) -> bool:
        """Lazy load camoufox."""
        if self._camoufox is not None:
            return True

        try:
            from camoufox.async_api import AsyncCamoufox
            self._camoufox = AsyncCamoufox
            return True
        except ImportError:
            self.logger.error("camoufox not installed: pip install camoufox[geoip]")
            return False

    def is_available(self) -> bool:
        """Check if camoufox is installed."""
        try:
            from camoufox.async_api import AsyncCamoufox
            return True
        except ImportError:
            return False

    async def _scrape_async(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Async implementation - opens URL with Camoufox, returns HTML.

        Security: URL is validated before scraping (SSRF protection).

        Returns:
            Tuple (html, error_message)
        """
        # Security: Validate URL before scraping
        if not validate_url(url):
            self.logger.warning(f"Blocked unsafe URL: {url[:100]}")
            return (None, f"URL blocked for security reasons: {url[:50]}...")

        if not self._ensure_camoufox():
            return (None, "camoufox not installed")

        try:
            from camoufox import DefaultAddons
            async with self._camoufox(headless=True, exclude_addons=[DefaultAddons.UBO]) as browser:
                page = await browser.new_page()

                self.logger.debug(f"Loading: {url}")

                # Navigate - domcontentloaded statt networkidle (RAM sparen)
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.config.timeout * 1000
                )

                # Wait for JS rendering
                await asyncio.sleep(self.wait_after_load)

                # Scroll to trigger lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await asyncio.sleep(0.5)

                # Get full HTML (for ContentExtractor)
                html = await page.content()

                self.logger.debug(f"Got HTML: {len(html)} chars")

                return (html, None)

        except asyncio.TimeoutError:
            return (None, f"Timeout after {self.config.timeout}s")

        except Exception as e:
            return (None, str(e))

    def _scrape_impl(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Synchronous wrapper for async scraping.

        Returns:
            Tuple (html, error_message)
        """
        try:
            return asyncio.run(self._scrape_async(url))
        except RuntimeError as e:
            if "running event loop" in str(e):
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    return asyncio.run(self._scrape_async(url))
                except ImportError:
                    return (None, "nest_asyncio not installed")
            raise

    def scrape_raw(self, url: str) -> Optional[str]:
        """
        Alternative: Get raw visible text (innerText) without extraction.

        Use this when you want exactly what a human sees, no processing.

        Security: URL is validated before scraping (SSRF protection).

        Returns:
            Visible text or None
        """
        # Security: Validate URL before scraping
        if not validate_url(url):
            self.logger.warning(f"Blocked unsafe URL: {url[:100]}")
            return None

        if not self._ensure_camoufox():
            return None

        async def get_text():
            try:
                from camoufox import DefaultAddons
                async with self._camoufox(headless=True, exclude_addons=[DefaultAddons.UBO]) as browser:
                    page = await browser.new_page()
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=self.config.timeout * 1000
                    )

                    # Warten bis document.body existiert (SPA fix)
                    waited = 0
                    while waited < self.max_body_wait:
                        has_body = await page.evaluate("document.body !== null")
                        if has_body:
                            break
                        await asyncio.sleep(0.5)
                        waited += 0.5

                    await asyncio.sleep(self.wait_after_load)

                    # Scroll fuer lazy loading
                    try:
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                    except:
                        pass  # Ignorieren wenn body noch Probleme macht

                    await asyncio.sleep(1.0)

                    return await page.evaluate("document.body?.innerText || ''")
            except Exception as e:
                self.logger.error(f"Raw scrape failed: {e}")
                return None

        try:
            return asyncio.run(get_text())
        except RuntimeError as e:
            if "running event loop" in str(e):
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    return asyncio.run(get_text())
                except ImportError:
                    return None
            raise


# Convenience functions
def camoufox_scrape(url: str, timeout: int = 30) -> Optional[str]:
    """
    One-liner: URL in, extracted content out (with maximum stealth).

    Uses ContentExtractor for clean output.

    Usage:
        content = camoufox_scrape("https://moxfield.com")
    """
    from lutum.core.config import ScraperConfig
    config = ScraperConfig(timeout=timeout)
    scraper = CamoufoxScraper(config)
    content, _ = scraper.scrape(url)
    return content


def camoufox_scrape_raw(url: str, timeout: int = 30) -> Optional[str]:
    """
    One-liner: URL in, raw visible text out (no extraction).

    Returns exactly what a human would see (document.body.innerText).

    Usage:
        text = camoufox_scrape_raw("https://moxfield.com")
    """
    from lutum.core.config import ScraperConfig
    config = ScraperConfig(timeout=timeout)
    scraper = CamoufoxScraper(config)
    return scraper.scrape_raw(url)


async def scrape_urls_batch(urls: list[str], timeout: int = 15, max_concurrent: int = 5) -> dict[str, str]:
    """
    Scrape multiple URLs SEQUENZIELL aber SCHNELL (kurze Timeouts).

    Parallelität mit einem Browser funktioniert nicht zuverlässig,
    daher sequenziell mit 15s Timeout pro URL.

    Security:
    - All URLs are validated before scraping (SSRF protection)
    - Maximum 100 URLs per batch
    - Rate limiting between requests

    Args:
        urls: List of URLs to scrape (max 100)
        timeout: Timeout per URL in seconds (default 15 - short!)
        max_concurrent: Ignored (kept for API compatibility)

    Returns:
        Dict {url: content} for successful scrapes
    """
    import time
    from lutum.core.log_config import get_logger
    logger = get_logger(__name__)

    if not urls:
        return {}

    # Security: Limit number of URLs
    if len(urls) > MAX_URLS_PER_BATCH:
        logger.warning(f"URL list truncated: {len(urls)} -> {MAX_URLS_PER_BATCH}")
        urls = urls[:MAX_URLS_PER_BATCH]

    # Security: Validate all URLs and filter out unsafe ones
    safe_urls = validate_urls(urls)
    blocked_count = len(urls) - len(safe_urls)
    if blocked_count > 0:
        logger.warning(f"Blocked {blocked_count} unsafe URLs (SSRF protection)")

    if not safe_urls:
        logger.warning("No safe URLs to scrape after validation")
        return {}

    try:
        from camoufox.async_api import AsyncCamoufox
    except ImportError:
        logger.error("camoufox not installed")
        return {}

    results = {}
    total = len(safe_urls)

    browser = None
    try:
        from camoufox import DefaultAddons
        browser = await AsyncCamoufox(headless=True, exclude_addons=[DefaultAddons.UBO]).start()
        logger.info(f"Scraping {total} URLs (sequential, {timeout}s timeout each)...")

        page = await browser.new_page()
        last_request_time = 0.0

        for i, url in enumerate(safe_urls, 1):
            # Security: Rate limiting
            elapsed = time.time() - last_request_time
            if elapsed < MIN_RATE_LIMIT_DELAY:
                await asyncio.sleep(MIN_RATE_LIMIT_DELAY - elapsed)

            last_request_time = time.time()
            start = time.time()
            logger.info(f"  [{i}/{total}] Scraping: {url[:60]}...")

            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=timeout * 1000
                )

                # Minimal wait for JS
                await asyncio.sleep(1.0)

                # Text extrahieren
                text = await page.evaluate("document.body?.innerText || ''")

                if text and len(text.strip()) > 50:
                    # Security: Limit response size
                    if len(text) > MAX_RESPONSE_SIZE:
                        text = text[:MAX_RESPONSE_SIZE] + "\n[...TRUNCATED - exceeded size limit...]"
                        logger.warning(f"  [{i}/{total}] Response truncated to {MAX_RESPONSE_SIZE} bytes")

                    results[url] = text
                    logger.info(f"  [{i}/{total}] OK: {len(text)} chars in {time.time() - start:.1f}s")
                else:
                    logger.warning(f"  [{i}/{total}] EMPTY in {time.time() - start:.1f}s")

            except Exception as e:
                # Security: Sanitize error message
                safe_error = sanitize_error(e)
                logger.warning(f"  [{i}/{total}] FAILED in {time.time() - start:.1f}s: {safe_error[:50]}")

        logger.info(f"Scraping done, closing browser...")

    except Exception as e:
        logger.error(f"Scrape failed: {e}")

    finally:
        # Browser mit Timeout schließen - NICHT blockieren!
        if browser:
            try:
                await asyncio.wait_for(browser.close(), timeout=10.0)
                logger.info(f"Browser closed, {len(results)}/{total} successful")
            except asyncio.TimeoutError:
                logger.warning(f"Browser close timed out, returning {len(results)} results anyway")
            except Exception as e:
                logger.warning(f"Browser close failed: {e}, returning {len(results)} results anyway")

    return results
