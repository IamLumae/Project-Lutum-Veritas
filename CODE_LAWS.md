# CODE LAWS - Lutum Veritas

> Diese Regeln sind GESETZ. Keine Ausnahmen.

---

## 1. KEINE MONOLITHEN

```
❌ VERBOTEN:
lutum.py (571 Zeilen alles drin)

✅ RICHTIG:
lutum/
├── core/
├── scrapers/
├── analyzer/
└── extractor/
```

**Jeder Service eine Datei.** Connectoren zwischen den Dateien via Imports.

---

## 2. CLASSES VON ANFANG AN

Sobald sich eine Struktur ergibt → Class.

```python
# ❌ VERBOTEN
def scrape(url):
    config = {...}
    result = {...}

# ✅ RICHTIG
class CamoufoxScraper:
    def __init__(self, config):
        self.config = config
```

---

## 3. SINNVOLLE STRUKTUR

Für Wartbarkeit:
- `core/` - Config, Logging, Exceptions
- `scrapers/` - Scraper-Implementierungen
- `analyzer/` - LLM Pipeline
- `extractor/` - Content Extraction

---

## 4. KOMMENTARE

```python
# ✅ WAS ist das
class CamoufoxScraper:
    """John Wick Scraper - 0% Detection, Firefox C++ Fork."""

# ✅ ACHTUNG Hinweise
self.wait_after_load = 5.0  # ACHTUNG: SPAs brauchen länger, hängt an config.timeout

# ✅ WARUM nicht nur WAS
# Warten auf document.body weil SPAs erst nach JS-Execution rendern
for _ in range(20):
    has_body = await page.evaluate("document.body !== null")
```

---

## 5. ERROR HANDLING - AUSNAHMSLOS

**JEDE noch so kleine Funktion** hat Error Handling + Logging.

```python
# ❌ VERBOTEN
def scrape(url):
    return requests.get(url).text

# ✅ RICHTIG
def scrape(url: str) -> Optional[str]:
    """Scraped URL. Returns None on error."""
    try:
        response = requests.get(url, timeout=30)
        self.logger.debug(f"Got {len(response.text)} chars from {url}")
        return response.text
    except requests.Timeout:
        self.logger.warning(f"Timeout: {url}")
        return None
    except Exception as e:
        self.logger.error(f"Scrape failed: {url} - {e}")
        return None
```

---

## 6. LOGGING

Jede Funktion loggt:
- **DEBUG**: Was sie tut, Zwischenergebnisse
- **INFO**: Erfolgreiche Operationen
- **WARNING**: Recoverable Fehler
- **ERROR**: Kritische Fehler

```python
self.logger = get_logger(__name__)

def do_thing(self):
    self.logger.debug(f"Starting thing with {params}")
    try:
        result = actual_work()
        self.logger.info(f"Thing done: {result}")
        return result
    except RecoverableError as e:
        self.logger.warning(f"Thing partially failed: {e}")
        return fallback
    except Exception as e:
        self.logger.error(f"Thing failed: {e}")
        raise
```

---

## 7. LOG LEVELS

| Level | Wann | Beispiel |
|-------|------|----------|
| **DEBUG** | Dev, alles | "Loading page...", "Got 5000 chars" |
| **INFO** | Produktion normal | "Scrape successful", "Saved to file" |
| **WARNING** | Recoverable | "Timeout, retrying", "Fallback used" |
| **ERROR** | Kritisch | "Scrape failed", "LLM error" |

```python
# In config
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # DEBUG in dev, INFO in prod
```

---

*Erstellt: 2026-01-26*
*Diese Regeln gelten für JEDEN Code in diesem Projekt.*
