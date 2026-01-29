"""
Pick URLs Prompt (Prompt 3)
===========================
LLM wählt die relevantesten URLs aus den Suchergebnissen.

Rekursiv: Wird für jeden Punkt im Research Plan ausgeführt.

Security:
- All parsed URLs are validated (SSRF protection)
- Input lengths are limited
- Response parsing has bounds
"""

from lutum.core.security import validate_url, sanitize_user_input, MAX_URL_LENGTH

PICK_URLS_SYSTEM_PROMPT = """Du wählst URLs aus Suchergebnissen.

═══════════════════════════════════════════════════════════════════
                    OUTPUT-FORMAT (PFLICHT!)
═══════════════════════════════════════════════════════════════════

REGEL 1: KEINE ANALYSE. KEINE ERKLÄRUNG. NUR URLS.
REGEL 2: Beginne SOFORT mit "=== SELECTED ===" - KEIN Text davor!
REGEL 3: Jede Zeile: "url N: https://..." - nichts anderes.
REGEL 4: EXAKT 20 URLs. Nicht 19, nicht 21.

═══════════════════════════════════════════════════════════════════
                    QUERY-AWARENESS (PFLICHT!)
═══════════════════════════════════════════════════════════════════

Passe deine Auswahlstrategie an den AUFTRAG an:
- "unbekannte/kleine/nische/experimental" → WENIGER offensichtliche Quellen
- "etablierte/Enterprise/bewährt/production-ready" → bekannte, viel-referenzierte Quellen
- "akademisch/wissenschaftlich" → Papers und Forschung priorisieren
- "praktisch/hands-on/tutorial" → Code-Beispiele und Guides priorisieren

═══════════════════════════════════════════════════════════════════
                    DIVERSIFIZIERUNG (PFLICHT!)
═══════════════════════════════════════════════════════════════════

Wähle URLs aus VERSCHIEDENEN Perspektiven:
- Nicht 15x GitHub, sondern: GitHub + Reddit + Paper + Blog + Docs
- Nicht 15x dasselbe Thema, sondern: verschiedene Aspekte abdecken

QUELLEN-MIX (ungefähre Verteilung für 20 URLs):
- 6-8x Primär: GitHub Repos, Offizielle Docs, Papers (arxiv)
- 4-5x Community: Reddit, HN, Foren, Stack Overflow
- 3-4x Praktisch: Tutorials, Medium, Dev.to, Guides
- 2-3x Kritisch: Vergleiche, Benchmarks, Limitations
- 2-3x Aktuell: News, 2024/2025 Releases, Updates

═══════════════════════════════════════════════════════════════════
                    QUELLEN-RANKING
═══════════════════════════════════════════════════════════════════

**Hochwertig:** GitHub Repos, Papers (arxiv), Offizielle Docs, Experten-Blogs
**Mittelwertig:** Medium/Dev.to, Reddit (wenn substantiell), Stack Overflow
**Vermeiden:** Generische Newsseiten, SEO-Spam, Veraltetes (vor 2023)
"""

PICK_URLS_USER_PROMPT = """
# KONTEXT

## Übergeordnete Aufgabe
{user_query}

## Aktueller Recherche-Punkt
{current_point}

## Deine Überlegungen (aus vorherigem Schritt)
{thinking_block}

{previous_learnings_block}

---

# SUCHERGEBNISSE

{search_results}

---

# AUFGABE

Wähle EXAKT 20 URLs. KEINE ANALYSE. KEINE ERKLÄRUNG. NUR URLS.

KRITISCH: Beginne SOFORT mit "=== SELECTED ===" - KEIN Text davor!

=== SELECTED ===
url 1: https://example.com/1
url 2: https://example.com/2
...
url 20: https://example.com/20

=== REJECTED ===
rejected: X URLs wegen Grund
"""


def build_pick_urls_prompt(
    user_query: str,
    current_point: str,
    thinking_block: str,
    search_results: str,
    previous_learnings: list[str] | None = None
) -> tuple[str, str]:
    """
    Baut den Pick-URLs-Prompt.

    Args:
        user_query: Übergeordnete Aufgabe
        current_point: Aktueller Recherche-Punkt
        thinking_block: Überlegungen aus Think-Prompt
        search_results: Formatierte Suchergebnisse
        previous_learnings: Key Learnings aus vorherigen Dossiers (optional)

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    # Previous Learnings Block formatieren
    if previous_learnings and len(previous_learnings) > 0:
        learnings_text = "\n\n---\n".join(
            f"**Dossier {i+1}:**\n{learning}"
            for i, learning in enumerate(previous_learnings)
        )
        previous_learnings_block = f"""
## BISHERIGE ERKENNTNISSE (aus vorherigen Dossiers)

WICHTIG:
- Wenn hier URLs empfohlen werden → PRIORISIERE diese!
- Wenn hier Themen als "wichtig" markiert sind → suche gezielt danach!
- Wähle URLs die NEUE Informationen liefern, nicht dieselben nochmal!
- Vermeide Duplikate zu bereits gescrapeten URLs!

{learnings_text}
"""
    else:
        previous_learnings_block = ""

    user_prompt = PICK_URLS_USER_PROMPT.format(
        user_query=user_query,
        current_point=current_point,
        thinking_block=thinking_block,
        previous_learnings_block=previous_learnings_block,
        search_results=search_results
    )

    return PICK_URLS_SYSTEM_PROMPT, user_prompt


def parse_pick_urls_response(response: str) -> list[str]:
    """
    Parst die Pick-URLs-Response (nur URLs).

    Security:
    - Response length is limited
    - URLs are validated (SSRF protection)
    - URL length is limited

    Args:
        response: LLM Response

    Returns:
        Liste der URLs (only safe URLs)
    """
    # Security: Limit response length
    if len(response) > 100_000:
        response = response[:100_000]

    urls = []

    for line in response.strip().split("\n"):
        line = line.strip()
        if line.lower().startswith("url"):
            if ":" in line:
                url = line.split(":", 1)[1].strip()

                # Security: Skip URLs that are too long
                if len(url) > MAX_URL_LENGTH:
                    continue

                # Security: Validate URL (SSRF protection)
                if url.startswith("http") and validate_url(url):
                    urls.append(url)

    return urls[:20]  # Max 20


def parse_pick_urls_full(response: str) -> dict:
    """
    Parst die Pick-URLs-Response KOMPLETT (URLs + Rejections).

    Security:
    - Response length is limited
    - URLs are validated (SSRF protection)
    - URL length is limited

    Args:
        response: LLM Response

    Returns:
        dict mit:
        - urls: Liste der ausgewählten URLs (only safe URLs)
        - rejections: Liste der Rejection-Gründe (z.B. "5 URLs wegen Paywall")
    """
    # Security: Limit response length
    if len(response) > 100_000:
        response = response[:100_000]

    urls = []
    rejections = []

    for line in response.strip().split("\n"):
        line = line.strip()
        if line.lower().startswith("url"):
            if ":" in line:
                url = line.split(":", 1)[1].strip()

                # Security: Skip URLs that are too long
                if len(url) > MAX_URL_LENGTH:
                    continue

                # Security: Validate URL (SSRF protection)
                if url.startswith("http") and validate_url(url):
                    urls.append(url)

        elif line.lower().startswith("rejected:"):
            reason = line.split(":", 1)[1].strip()
            if reason and len(reason) < 500:  # Limit reason length
                rejections.append(reason)

    return {
        "urls": urls[:20],
        "rejections": rejections[:10]  # Limit rejections too
    }
