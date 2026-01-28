"""
Lutum Veritas - Camoufox Scraper (John Wick Edition)
====================================================
Stufe 5: The scraper that can scrape ANYTHING from ANY site.

Camoufox = Firefox with C++-level fingerprint spoofing.
0% detection rate on fingerprint tests.
83.3% bypass rate on anti-bot systems (Cloudflare, Datadome, Akamai).

ACHTUNG: Braucht camoufox: pip install camoufox[geoip] && python -m camoufox fetch
"""

import asyncio
from typing import Optional, Tuple

from lutum.scrapers.base import BaseScraper
from lutum.core.config import ScraperConfig


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

        Returns:
            Tuple (html, error_message)
        """
        if not self._ensure_camoufox():
            return (None, "camoufox not installed")

        try:
            async with self._camoufox(headless=True) as browser:
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

        Returns:
            Visible text or None
        """
        if not self._ensure_camoufox():
            return None

        async def get_text():
            try:
                async with self._camoufox(headless=True) as browser:
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

    Args:
        urls: List of URLs to scrape
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

    try:
        from camoufox.async_api import AsyncCamoufox
    except ImportError:
        logger.error("camoufox not installed")
        return {}

    results = {}
    total = len(urls)

    try:
        async with AsyncCamoufox(headless=True) as browser:
            logger.info(f"Scraping {total} URLs (sequential, {timeout}s timeout each)...")

            page = await browser.new_page()

            for i, url in enumerate(urls, 1):
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
                        results[url] = text
                        logger.info(f"  [{i}/{total}] OK: {len(text)} chars in {time.time() - start:.1f}s")
                    else:
                        logger.warning(f"  [{i}/{total}] EMPTY in {time.time() - start:.1f}s")

                except Exception as e:
                    logger.warning(f"  [{i}/{total}] FAILED in {time.time() - start:.1f}s: {str(e)[:50]}")

            await page.close()

        logger.info(f"Scraping complete: {len(results)}/{total} successful")

    except Exception as e:
        logger.error(f"Scrape failed: {e}")

    return results
