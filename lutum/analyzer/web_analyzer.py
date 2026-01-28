"""
Lutum Veritas - Web Analyzer
============================
Scraped eine URL mit Camoufox und analysiert den Content mit LLM.

Usage:
    python -m lutum.analyzer.web_analyzer "https://example.com"
    python -m lutum.analyzer.web_analyzer "https://example.com" --query "Was kostet das Produkt?"
    python -m lutum.analyzer.web_analyzer "https://example.com" -o result.txt
"""

import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

from lutum.scrapers.camoufox_scraper import camoufox_scrape_raw
from lutum.core.log_config import get_logger
from lutum.core.api_config import get_api_key


# === CONFIG ===
MODEL = "google/gemini-3-flash-preview"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "outputs"

# Logger für dieses Modul
logger = get_logger(__name__)


# === SYSTEM PROMPT ===
SYSTEM_PROMPT = """Du bist ein Web-Content-Extraktor. Du bekommst:
1. Den RAW sichtbaren Text einer Webseite
2. Eine Nutzer-Nachricht

=== SCHRITT 1: MODUS ERKENNEN ===

Lies die Nutzer-Nachricht und waehle den passenden Modus:

**MODUS A - ZUSAMMENFASSUNG** (User sagt: zusammenfassen, keypoints, kurz, ueberblick, worum gehts, tldr)
→ Fasse den Inhalt KOMPAKT zusammen
→ Fokus auf Kernaussagen
→ Bullet Points erlaubt
→ Kuerzen erlaubt

**MODUS B - VOLLEXTRAKTION** (User sagt: alles, komplett, detail, was steht da, zeig mir)
→ 1:1 Wiedergabe des GESAMTEN Contents
→ NICHTS kuerzen oder weglassen
→ Jede Headline, jeder Artikel, jede Zahl
→ So lesbar wie die echte Seite

**MODUS C - ANALYSE** (User sagt: aufbau, aussehen, struktur, design, wie ist die seite)
→ Beschreibe WIE die Seite aufgebaut ist
→ Welche Sektionen gibt es
→ Wo sind Buttons, Tabellen, Listen
→ Visueller Eindruck

**MODUS D - SPEZIFISCHE FRAGE** (User fragt etwas Konkretes)
→ Beantworte NUR die Frage
→ Praezise und direkt
→ Mit Belegen aus dem Text

=== SCHRITT 2: AUSFUEHREN ===

Fuehre den erkannten Modus aus.

BEI ALLEN MODI IGNORIERE:
- Navigation (Home, Login, Menu)
- Footer (Impressum, Privacy, Copyright)
- Cookie-Banner
- Subscribe/Sign-up Spam

FORMATIERUNG:
- Markdown fuer Struktur
- # ## ### fuer Hierarchie
- **fett** fuer Wichtiges
- Listen mit - oder 1. 2. 3.
- --- zwischen Sektionen

=== SCHRITT 3: ABSCHLUSS ===

Am Ende IMMER:
---
*Moechtest du einen anderen Modus? (Zusammenfassung / Vollextraktion / Analyse / Frage)*"""


def _scrape_url(url: str, timeout: int) -> Optional[str]:
    """
    Step 1: Scraped URL mit Camoufox.

    Args:
        url: Zu scrapende URL
        timeout: Timeout in Sekunden

    Returns:
        Raw text oder None bei Fehler
    """
    logger.debug(f"Starting scrape: {url}")

    try:
        raw_text = camoufox_scrape_raw(url, timeout=timeout)

        if not raw_text:
            logger.warning(f"Scrape returned empty: {url}")
            return None

        logger.info(f"Scrape successful: {len(raw_text):,} chars from {url}")
        return raw_text

    except Exception as e:
        logger.error(f"Scrape failed: {url} - {e}")
        return None


def _call_llm(raw_text: str, url: str, user_message: str, max_tokens: int) -> Optional[str]:
    """
    Step 2: Sendet Text an LLM zur Analyse.

    Args:
        raw_text: Gescrapeter Text
        url: Original URL (für Kontext)
        user_message: User Query
        max_tokens: Max Response Tokens

    Returns:
        LLM Response oder None bei Fehler
    """
    logger.debug(f"Calling LLM: {MODEL}, max_tokens={max_tokens}")

    full_prompt = f"""=== WEBSEITE ===
URL: {url}

=== RAW SICHTBARER TEXT ===
{raw_text}

=== NUTZER-NACHRICHT ===
{user_message}"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {get_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ],
                "max_tokens": max_tokens
            },
            timeout=120
        )

        result = response.json()

        if "choices" not in result:
            logger.error(f"LLM error response: {result}")
            return None

        answer = result["choices"][0]["message"]["content"]
        logger.info(f"LLM response: {len(answer):,} chars")
        return answer

    except requests.Timeout:
        logger.error("LLM request timeout (120s)")
        return None
    except requests.RequestException as e:
        logger.error(f"LLM request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM unexpected error: {e}")
        return None


def _save_output(answer: str, url: str, user_message: str, raw_chars: int, output_file: Optional[Path]) -> Path:
    """
    Step 3: Speichert Ergebnis in Datei.

    Args:
        answer: LLM Response
        url: Original URL
        user_message: User Query
        raw_chars: Anzahl gescrapeter Zeichen
        output_file: Ziel-Pfad (oder None für Auto)

    Returns:
        Pfad zur gespeicherten Datei
    """
    # Auto-generate filename if needed
    if output_file is None:
        try:
            DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create output dir: {e}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain = url.split("//")[-1].split("/")[0].replace(".", "_")
        output_file = DEFAULT_OUTPUT_DIR / f"{timestamp}_{domain}.txt"

    output_file = Path(output_file)

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Lutum Veritas - Web Analysis\n")
            f.write(f"# URL: {url}\n")
            f.write(f"# Query: {user_message}\n")
            f.write(f"# Date: {datetime.now().isoformat()}\n")
            f.write(f"# Model: {MODEL}\n")
            f.write(f"# Raw chars: {raw_chars:,}\n")
            f.write(f"#\n")
            f.write(f"# {'='*60}\n\n")
            f.write(answer)

        logger.info(f"Saved to: {output_file}")
        return output_file

    except Exception as e:
        logger.error(f"Failed to save output: {e}")
        raise


def analyze_url(
    url: str,
    user_query: Optional[str] = None,
    output_file: Optional[Path] = None,
    timeout: int = 45,
    max_tokens: int = 8000,
    verbose: bool = True
) -> str:
    """
    Scraped URL und analysiert mit LLM.

    Args:
        url: Die zu analysierende URL
        user_query: Optionale Nutzer-Frage (None = Content-Extraktion)
        output_file: Optionaler Pfad fuer Output-Datei
        timeout: Scraping Timeout in Sekunden
        max_tokens: Max Tokens fuer LLM Response
        verbose: Print Status-Updates zu stdout

    Returns:
        LLM Response als String

    Raises:
        RuntimeError: Bei Scrape- oder LLM-Fehler
    """
    logger.debug(f"analyze_url called: url={url}, query={user_query}")

    # === STEP 1: SCRAPE ===
    if verbose:
        print(f"[1/3] Scraping: {url}")

    raw_text = _scrape_url(url, timeout)

    if not raw_text:
        raise RuntimeError(f"Scraping failed for {url}")

    if verbose:
        print(f"      Got {len(raw_text):,} chars")

    # === STEP 2: LLM CALL ===
    user_message = user_query or "Was ist auf dieser Seite? (Extrahiere den kompletten Content)"

    if verbose:
        print(f"[2/3] Sending to LLM ({MODEL})...")

    answer = _call_llm(raw_text, url, user_message, max_tokens)

    if not answer:
        raise RuntimeError(f"LLM call failed for {url}")

    if verbose:
        print(f"      Got {len(answer):,} chars response")

    # === STEP 3: SAVE ===
    saved_path = _save_output(answer, url, user_message, len(raw_text), output_file)

    if verbose:
        print(f"[3/3] Saved to: {saved_path}")

    return answer


def main():
    """CLI Entry Point."""
    parser = argparse.ArgumentParser(
        description="Analyze a webpage with Camoufox + LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m lutum.analyzer.web_analyzer "https://bloomberg.com/technology"
  python -m lutum.analyzer.web_analyzer "https://example.com" --query "Was kostet es?"
  python -m lutum.analyzer.web_analyzer "https://example.com" -o result.txt -q
        """
    )

    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--query", "-Q", help="User query (default: extract content)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--timeout", "-t", type=int, default=45, help="Scrape timeout (default: 45)")
    parser.add_argument("--max-tokens", "-m", type=int, default=8000, help="Max LLM tokens (default: 8000)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress status output")
    parser.add_argument("--print", "-p", action="store_true", help="Print result to stdout")

    args = parser.parse_args()

    logger.debug(f"CLI args: {args}")

    output_path = Path(args.output) if args.output else None

    try:
        result = analyze_url(
            url=args.url,
            user_query=args.query,
            output_file=output_path,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
            verbose=not args.quiet
        )

        if args.print:
            print("\n" + "="*60)
            print(result)

    except RuntimeError as e:
        logger.error(f"Analysis failed: {e}")
        print(f"ERROR: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"ERROR: {e}")
        exit(1)


if __name__ == "__main__":
    main()
