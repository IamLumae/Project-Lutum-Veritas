"""
Think Prompt (Prompt 2)
=======================
LLM überlegt welche Informationen benötigt werden und generiert Suchanfragen.

Rekursiv: Wird für jeden Punkt im Research Plan ausgeführt.
"""

THINK_SYSTEM_PROMPT = """Du bist ein erfahrener Research-Stratege.

WICHTIG - SPRACHLICHE ANPASSUNG: Wenn die ursprüngliche Nutzer-Anfrage auf Englisch formuliert wurde, antworte auf Englisch. Wenn sie auf Deutsch war, antworte auf Deutsch.

Deine Aufgabe: Analysiere den aktuellen Recherche-Punkt und entwickle eine
präzise Suchstrategie. Du musst herausfinden welche Informationen du brauchst
und wie du sie am besten findest.

## KRITISCH: FORMAT DER SUCHANFRAGEN

GENERIERE NUR EINFACHE SUCHBEGRIFFE - KEINE URLS!

FALSCH: https://github.com/search?q=adaptive+chunking
FALSCH: site:github.com adaptive chunking
RICHTIG: adaptive chunking python implementation
RICHTIG: RAG chunking strategies 2024

Jede Suchanfrage ist ein einfacher Text-String mit Keywords, KEINE URL!

## SUCHSTRATEGIE-PRINZIPIEN

1. **Spezifisch**: Keine generischen Suchen. Je präziser, desto besser die Ergebnisse.
2. **Aktuell**: Jahreszahlen einbauen wenn Aktualität wichtig ist (2024, 2025).
3. **Quellenorientiert**: Keywords wie "github", "paper", "docs", "reddit" gezielt einbauen.

## KRITISCH: DIVERSIFIZIERUNG (PFLICHT!)

NIEMALS 10 Suchen in die gleiche Richtung feuern!

Verteile deine Suchen auf MINDESTENS 4 verschiedene Perspektiven:
- **Primär**: Offizielle Quellen, Dokumentation, Original-Repos, Papers
- **Community**: Diskussionen, Reddit, HN, Foren, Erfahrungsberichte
- **Praktisch**: Tutorials, How-tos, Implementierungen, Beispiele
- **Kritisch**: Probleme, Limitationen, Alternativen, Vergleiche
- **Aktuell**: News, "2024", "neu", "latest", Trends

BEISPIEL - FALSCH (Monokultur):
search 1: RAG chunking techniques
search 2: RAG chunking methods
search 3: RAG chunking strategies
search 4: RAG chunking best practices
→ 4x dasselbe in grün!

BEISPIEL - RICHTIG (Diversifiziert):
search 1: RAG chunking implementation github
search 2: "chunking problems" RAG reddit
search 3: RAG chunking vs semantic splitting comparison
search 4: RAG chunking 2024 new approaches
"""

THINK_USER_PROMPT = """
# KONTEXT

## Übergeordnete Aufgabe
{user_query}

## Aktueller Recherche-Punkt
{current_point}

{previous_learnings_block}

---

# AUFGABE

Denke darüber nach welche Informationen du brauchst um den Recherche-Punkt
"{current_point}" gründlich zu bearbeiten.

Entwickle eine Suchstrategie mit konkreten Google-Suchanfragen.

---

# FORMAT (EXAKT SO - Kategorie ist PFLICHT!)

=== THINKING ===
[Deine Überlegungen: Was brauchst du? Warum? Welche Aspekte sind wichtig?]

=== SEARCHES ===
search 1 (Primär): [offizielle Quelle, Docs, Repo, Paper]
search 2 (Primär): [offizielle Quelle, Docs, Repo, Paper]
search 3 (Community): [Reddit, HN, Forum, Diskussion]
search 4 (Community): [Reddit, HN, Forum, Diskussion]
search 5 (Praktisch): [Tutorial, How-to, Beispiel, Implementation]
search 6 (Praktisch): [Tutorial, How-to, Beispiel, Implementation]
search 7 (Kritisch): [Probleme, Limitationen, Alternativen, Vergleich]
search 8 (Kritisch): [Probleme, Limitationen, Alternativen, Vergleich]
search 9 (Aktuell): [News, 2024, 2025, neu, latest, Trends]
search 10 (Aktuell): [News, 2024, 2025, neu, latest, Trends]
"""


def build_think_prompt(
    user_query: str,
    current_point: str,
    previous_learnings: list[str] | None = None
) -> tuple[str, str]:
    """
    Baut den Think-Prompt.

    Args:
        user_query: Übergeordnete Aufgabe
        current_point: Aktueller Recherche-Punkt
        previous_learnings: Liste der Key Learnings aus vorherigen Punkten (optional)

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    # Previous Learnings Block formatieren
    if previous_learnings and len(previous_learnings) > 0:
        learnings_text = "\n\n---\n".join(
            f"**Punkt {i+1}:**\n{learning}"
            for i, learning in enumerate(previous_learnings)
        )
        previous_learnings_block = f"""
## Bisherige Erkenntnisse (aus vorherigen Punkten)

WICHTIG: Diese Informationen hast du bereits. Suche NICHT erneut danach!
Fokussiere dich auf NEUE Aspekte die für "{current_point}" relevant sind.

{learnings_text}
"""
    else:
        previous_learnings_block = ""

    user_prompt = THINK_USER_PROMPT.format(
        user_query=user_query,
        current_point=current_point,
        previous_learnings_block=previous_learnings_block
    )

    return THINK_SYSTEM_PROMPT, user_prompt


def parse_think_response(response: str) -> tuple[str, list[str]]:
    """
    Parst die Think-Response.

    Args:
        response: LLM Response

    Returns:
        Tuple (thinking_block, search_list)
    """
    thinking_block = ""
    searches = []

    # Thinking Block extrahieren
    if "=== THINKING ===" in response:
        parts = response.split("=== THINKING ===")
        if len(parts) > 1:
            thinking_part = parts[1]
            if "=== SEARCHES ===" in thinking_part:
                thinking_block = thinking_part.split("=== SEARCHES ===")[0].strip()
            else:
                thinking_block = thinking_part.strip()

    # Searches extrahieren
    if "=== SEARCHES ===" in response:
        search_part = response.split("=== SEARCHES ===")[1]
        for line in search_part.strip().split("\n"):
            line = line.strip()
            if line.lower().startswith("search"):
                if ":" in line:
                    query = line.split(":", 1)[1].strip()
                    # URL-Filter: Wenn LLM URLs generiert, extrahiere Keywords
                    if query:
                        if query.startswith("http://") or query.startswith("https://"):
                            # URL → versuche Keywords zu extrahieren
                            import re
                            # Extrahiere q= Parameter oder path segments
                            if "q=" in query:
                                match = re.search(r'[?&]q=([^&]+)', query)
                                if match:
                                    query = match.group(1).replace("+", " ").replace("%20", " ")
                                    query = re.sub(r'%[0-9A-Fa-f]{2}', ' ', query)  # URL decode cleanup
                            else:
                                continue  # Skip non-search URLs
                        # Entferne URL-artige Patterns die durchrutschen
                        if "://" in query or query.startswith("site:"):
                            continue
                        if query and len(query) > 3:
                            searches.append(query)

    return thinking_block, searches[:10]  # Max 10
