"""
Scraper Module
==============
Step 3: Scraped URLs mit Camoufox.

URLs → Camoufox (stealth browser) → Page Content
"""

import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from lutum.core.log_config import get_logger
from lutum.scrapers.camoufox_scraper import camoufox_scrape

logger = get_logger(__name__)


def _scrape_single_url(url: str, timeout: int = 30) -> dict:
    """
    Scraped eine einzelne URL mit Camoufox.

    Args:
        url: Die zu scrapende URL
        timeout: Timeout in Sekunden

    Returns:
        Dict mit: url, content, error
    """
    logger.debug(f"Scraping: {url[:80]}...")

    try:
        # camoufox_scrape() ist die Convenience-Funktion
        # Gibt extracted content oder None zurück
        content = camoufox_scrape(url, timeout=timeout)

        if content:
            logger.info(f"Scraped {url[:50]}: {len(content)} chars")
            return {
                "url": url,
                "content": content,
                "error": None
            }
        else:
            logger.warning(f"Empty content from: {url[:50]}")
            return {
                "url": url,
                "content": None,
                "error": "Empty content or scrape failed"
            }

    except TimeoutError:
        logger.warning(f"Scrape timeout: {url[:50]}")
        return {
            "url": url,
            "content": None,
            "error": "Timeout"
        }

    except Exception as e:
        logger.error(f"Scrape failed for {url[:50]}: {e}")
        return {
            "url": url,
            "content": None,
            "error": str(e)
        }


def scrape_urls(urls: list[str], max_workers: int = 3, timeout: int = 30) -> dict:
    """
    Step 3: Scraped alle URLs parallel.

    Args:
        urls: Liste der URLs zum Scrapen
        max_workers: Max parallele Scraper
        timeout: Timeout pro URL in Sekunden

    Returns:
        Dict mit:
            - scraped: Liste von {url, content, error}
            - success_count: Anzahl erfolgreicher Scrapes
            - error: Allgemeiner Fehler falls aufgetreten
    """
    logger.info(f"scrape_urls called: {len(urls)} URLs, {max_workers} workers")

    if not urls:
        logger.warning("No URLs to scrape")
        return {
            "scraped": [],
            "success_count": 0,
            "error": "No URLs provided"
        }

    results = []

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(_scrape_single_url, url, timeout): url
                for url in urls
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Scraper thread failed for '{url[:50]}': {e}")
                    results.append({
                        "url": url,
                        "content": None,
                        "error": str(e)
                    })

        success_count = sum(1 for r in results if r["content"])
        logger.info(f"Scraping complete: {success_count}/{len(urls)} successful")

        return {
            "scraped": results,
            "success_count": success_count,
            "error": None
        }

    except Exception as e:
        logger.error(f"scrape_urls failed: {e}")
        return {
            "scraped": results,
            "success_count": sum(1 for r in results if r.get("content")),
            "error": str(e)
        }


def format_scraped_for_llm(scraped_results: list[dict], max_chars_per_page: int = 5000) -> str:
    """
    Formatiert Scrape-Ergebnisse für LLM-Analyse.

    Args:
        scraped_results: Liste von {url, content, error}
        max_chars_per_page: Max Zeichen pro Seite (truncation)

    Returns:
        Formatierter String für LLM
    """
    logger.debug(f"Formatting {len(scraped_results)} scrape results for LLM")

    try:
        lines = []

        for i, result in enumerate(scraped_results, 1):
            url = result.get("url", "unknown")
            content = result.get("content")
            error = result.get("error")

            lines.append(f"=== PAGE {i}: {url} ===")

            if error:
                lines.append(f"[FEHLER: {error}]")
            elif content:
                # Truncate if too long
                if len(content) > max_chars_per_page:
                    content = content[:max_chars_per_page] + "\n[... truncated ...]"
                lines.append(content)
            else:
                lines.append("[Kein Content]")

            lines.append("")

        formatted = "\n".join(lines)
        logger.info(f"Formatted scrape results: {len(formatted)} chars total")
        return formatted

    except Exception as e:
        logger.error(f"Format scrape results failed: {e}")
        return "Fehler beim Formatieren der Scrape-Ergebnisse."


# === CLI TEST ===
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m lutum.researcher.scraper <url1> <url2> ...")
        sys.exit(1)

    test_urls = sys.argv[1:]
    print(f"Scraping {len(test_urls)} URLs...\n")

    result = scrape_urls(test_urls)

    print("=" * 60)
    print("SCRAPE RESULTS:")
    print("=" * 60)

    for r in result["scraped"]:
        status = "OK" if r["content"] else f"FAIL: {r['error']}"
        chars = len(r["content"]) if r["content"] else 0
        print(f"  {r['url'][:60]}: {status} ({chars} chars)")

    print(f"\nSuccess: {result['success_count']}/{len(test_urls)}")

    if result["error"]:
        print(f"Error: {result['error']}")
