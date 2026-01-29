"""
Dossier Prompt (Pick-Dossier)
=============================
Erstellt ein wissenschaftliches Dossier für EINEN Recherche-Punkt.

TEXT-ONLY APPROACH:
- Keine API-Metadaten (Stars, Commits, Datum)
- Nur Informationen aus dem gescrapten Text
- Evidenz-Snippets statt Halluzination
- Ehrlich bei Lücken ("nicht angegeben")

FORMAT v2.0:
- Universelle Marker für Parser (## EMOJI TITEL)
- Inline Citations [N] mit Quellenverzeichnis
- PFLICHT vs OPTIONAL Sektionen
"""

DOSSIER_SYSTEM_PROMPT = """Du bist ein Experte für wissenschaftliche Analyse und Wissensaufbereitung.

═══════════════════════════════════════════════════════════════════
                    SPRACHE (KRITISCH!)
═══════════════════════════════════════════════════════════════════

WICHTIG: Antworte IMMER in der Sprache der ursprünglichen Nutzer-Anfrage!
- Deutsche Anfrage → Deutsches Dossier
- English query → English dossier
- Mischung → Sprache des Hauptteils der Anfrage

═══════════════════════════════════════════════════════════════════
                    CITATION-SYSTEM (PFLICHT!)
═══════════════════════════════════════════════════════════════════

JEDE faktische Aussage MUSS mit einer Citation markiert werden:
- Format: Text mit Aussage[1] und weitere Aussage[2]
- Nummer ist fortlaufend: [1], [2], [3]...
- Am Ende: Quellenverzeichnis mit === SOURCES === Block

BEISPIEL:
"RAG erreicht 95% Accuracy bei strukturierten Benchmarks"[1], während
traditionelle Methoden bei etwa 70% stagnieren[2].

═══════════════════════════════════════════════════════════════════
                    FORMAT-MARKER (PFLICHT!)
═══════════════════════════════════════════════════════════════════

Diese Marker ermöglichen automatisches Parsing - EXAKT so verwenden:

SEKTIONEN:      ## EMOJI TITEL
                Beispiel: ## 📋 HEADER

TABELLEN:       | Col1 | Col2 | Col3 |
                |------|------|------|
                | data | data | data |

LISTEN:         1) Erster Punkt
                2) Zweiter Punkt
                (NICHT 1. oder - für nummerierte Listen!)

HIGHLIGHT-BOX:  > 💡 **Wichtig:** Text hier
                > ⚠️ **Warnung:** Text hier

KEY-VALUE:      - **Schlüssel:** Wert

═══════════════════════════════════════════════════════════════════
                         HARTREGELN (PFLICHT)
═══════════════════════════════════════════════════════════════════

1. **NO-API / NO-META**: Nutze AUSSCHLIESSLICH Informationen aus den gelieferten Quellen.
   - Keine Annahmen über Stars, Commits, Datum (außer explizit im Text).
   - Keine "wahrscheinlich", "vermutlich" ohne Kennzeichnung.

2. **TEXT-ONLY LEDGER**: Fülle Core-Spalten immer. Meta-Spalten nur wenn explizit im Text sichtbar, sonst "N/A".

3. **EVIDENZ-SNIPPET PFLICHT**: Jeder Ledger-Eintrag braucht ein kurzes Snippet (≤20 Wörter) aus dem Quelltext.

4. **KEINE HALLUZINATIONEN**: Wenn Information fehlt → "nicht in den Quellen angegeben".

5. **ABSCHLUSSMARKER PFLICHT**: Am Ende IMMER "=== END DOSSIER ===" ausgeben.

═══════════════════════════════════════════════════════════════════
                         LEDGER-FORMATE
═══════════════════════════════════════════════════════════════════

Wähle das passende Ledger-Format:

**Repo-Ledger:**
| # | Repo | Technik | Kernaussage | Evidenz-Snippet | Bewertung |
|---|------|---------|-------------|-----------------|-----------|
| [1] | Name | ... | ... | "..." | ⭐⭐⭐ |

**Paper-Ledger:**
| # | Paper | Jahr | Beitrag | Kernergebnis | Evidenz-Snippet |
|---|-------|------|---------|--------------|-----------------|
| [1] | Name | ... | ... | ... | "..." |

**Thread-Ledger:**
| # | Plattform | Thema | Hauptargument | Takeaway | Evidenz-Snippet |
|---|-----------|-------|---------------|----------|-----------------|
| [1] | Reddit | ... | ... | ... | "..." |

**Mixed-Ledger (für verschiedene Quellenarten):**
| # | Quelle | Typ | Kernaussage | Evidenz-Snippet | Bewertung |
|---|--------|-----|-------------|-----------------|-----------|
| [1] | Name | Repo/Paper/Thread | ... | "..." | ⭐⭐⭐ |
"""

DOSSIER_USER_PROMPT = """
═══════════════════════════════════════════════════════════════════
                         DEINE AUFGABE
═══════════════════════════════════════════════════════════════════

ÜBERGEORDNETES ZIEL:
{user_query}

AKTUELLER RECHERCHE-PUNKT:
{current_point}

═══════════════════════════════════════════════════════════════════
                    DEINE BISHERIGEN ÜBERLEGUNGEN
═══════════════════════════════════════════════════════════════════

{thinking_block}

═══════════════════════════════════════════════════════════════════
                    RECHERCHIERTE QUELLEN
═══════════════════════════════════════════════════════════════════

{scraped_content}

═══════════════════════════════════════════════════════════════════
                    AUSGABE-STRUKTUR
═══════════════════════════════════════════════════════════════════

Erstelle das Dossier mit diesen Sektionen.
PFLICHT-Sektionen: IMMER ausgeben.
OPTIONAL-Sektionen: NUR wenn für dieses Thema relevant!

---

## 📋 HEADER

- **Thema:** {current_point}
- **Bezug:** 1-2 Sätze wie dieser Punkt zum Gesamtziel beiträgt
- **Quellen:** Anzahl + Art (z.B. "5 Repos, 2 Papers, 3 Threads")

---

## 📊 EVIDENCE

Erstelle eine Markdown-Tabelle mit allen relevanten Quellen.
WICHTIG: Die # Spalte enthält die Citation-Nummer [1], [2], etc.

| # | Quelle | Typ | Kernaussage | Evidenz-Snippet | Bewertung |
|---|--------|-----|-------------|-----------------|-----------|
| [1] | ... | Repo/Paper/Thread | ... | "direktes Zitat ≤20 Wörter" | ⭐⭐⭐ |
| [2] | ... | ... | ... | "..." | ⭐⭐ |

(Bewertung: ⭐ = schwach, ⭐⭐ = mittel, ⭐⭐⭐ = stark)

---

## 🎯 KERNSUMMARY

Die wichtigsten Erkenntnisse (5-7 Punkte):

1) Erste Kernerkenntnis mit Quellenbeleg[1]
2) Zweite Kernerkenntnis[2][3]
3) Dritte Kernerkenntnis[4]
4) ...

> 💡 **Zentrale Erkenntnis:** Ein Satz der alles zusammenfasst.

---

## 🔍 ANALYSE

Detaillierte Untersuchung - passe die Struktur an das Thema an:

**Kontext:** Was ist der Hintergrund?[1]

**Kernmechanismus:** Wie funktioniert es? (bei Tech-Themen)
ODER **Kernargumente:** Was sind die Hauptpositionen? (bei Debatten)
ODER **Chronologie:** Wie hat es sich entwickelt? (bei historischen Themen)

**Zusammenhänge:** Wie hängt es mit anderen Aspekten zusammen?[2]

**Trade-offs:** Was sind die Vor- und Nachteile?
- **Pro:** ...
- **Contra:** ...

---

## 🔬 CLAIM AUDIT
(OPTIONAL - NUR wenn quantitative Claims geprüft werden müssen!)

| Claim | Quelle | Messgröße | Baseline | Setup | Ergebnis | Einschränkungen | Confidence |
|-------|--------|-----------|----------|-------|----------|-----------------|------------|
| "95% Accuracy" | [1] | Accuracy | 70% Standard | GPT-4, HotpotQA | 95.2% | Nur Englisch | ⭐⭐⭐ |

> ⚠️ **Vorsicht:** Claims ohne Baseline/Setup sind schwach belegt.

---

## 🔄 REPRODUKTION
(OPTIONAL - NUR bei Tech/Science Themen wo Nachbau relevant ist!)

**Minimaler Repro-Plan:**
1) Schritt 1
2) Schritt 2
3) ...

**Voraussetzungen:** Hardware, Software, Daten

**Failure Modes:** Was kann schiefgehen?

---

## ⚖️ BEWERTUNG

> 💡 **Stärken:**
- Stärke 1[1]
- Stärke 2[2]
- Stärke 3

> ⚠️ **Schwächen:**
- Schwäche 1
- Schwäche 2
- Schwäche 3

> ❓ **Offene Fragen:**
- Frage 1
- Frage 2
- Frage 3

---

## 💡 KEY LEARNINGS

**Erkenntnisse:**
1) Wichtigste Erkenntnis in einem Satz[1]
2) Zweitwichtigste Erkenntnis[2]
3) Drittwichtigste Erkenntnis[3]
(max 5 Punkte)

**Beste Quellen:**
- [1] - Warum wertvoll (5 Wörter)
- [2] - Warum wertvoll (5 Wörter)
(max 3 Einträge)

**Für nächste Schritte:**
Ein Satz was nachfolgende Recherche-Punkte wissen/beachten sollten.

---

=== SOURCES ===
[1] URL_DER_QUELLE_1 - Kurztitel oder Beschreibung
[2] URL_DER_QUELLE_2 - Kurztitel oder Beschreibung
[3] URL_DER_QUELLE_3 - Kurztitel oder Beschreibung
...
=== END SOURCES ===

=== END DOSSIER ===
"""


def build_dossier_prompt(
    user_query: str,
    current_point: str,
    thinking_block: str,
    scraped_content: str
) -> tuple[str, str]:
    """
    Baut den Dossier-Prompt.

    Args:
        user_query: Übergeordnete Aufgabe
        current_point: Aktueller Recherche-Punkt
        thinking_block: Überlegungen aus Think-Prompt
        scraped_content: Gescrapte Inhalte

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    user_prompt = DOSSIER_USER_PROMPT.format(
        user_query=user_query,
        current_point=current_point,
        thinking_block=thinking_block,
        scraped_content=scraped_content
    )

    return DOSSIER_SYSTEM_PROMPT, user_prompt


def parse_dossier_response(response: str) -> tuple[str, str, dict]:
    """
    Parst die Dossier-Response und extrahiert Key Learnings + Citations.

    Security:
    - Input length limited to prevent ReDoS
    - Citation numbers limited to prevent integer overflow
    - Uses find() instead of greedy regex to prevent catastrophic backtracking

    Args:
        response: Volle LLM Response

    Returns:
        Tuple (dossier_text, key_learnings, citations)
        - dossier_text: Das vollständige Dossier
        - key_learnings: Der Key Learnings Block
        - citations: Dict {1: "url - title", 2: "url - title", ...}
    """
    import re

    # Security: Limit response length to prevent ReDoS
    MAX_RESPONSE_LENGTH = 500_000  # 500KB max
    if len(response) > MAX_RESPONSE_LENGTH:
        response = response[:MAX_RESPONSE_LENGTH]

    dossier_text = response
    key_learnings = ""
    citations = {}

    # Security: Use find() instead of regex to prevent ReDoS
    sources_start = response.find('=== SOURCES ===')
    sources_end = response.find('=== END SOURCES ===')

    if sources_start >= 0 and sources_end > sources_start:
        sources_block = response[sources_start + len('=== SOURCES ==='):sources_end]
        for line in sources_block.strip().split('\n'):
            line = line.strip()
            if not line or len(line) > 2000:  # Security: Skip overly long lines
                continue
            # Format: [N] URL - Title (limit to 5 digits = max 99999)
            match = re.match(r'^\[(\d{1,5})\]\s+(.{1,1900})$', line)
            if match:
                num = int(match.group(1))
                if 1 <= num <= 99999:  # Security: Validate range
                    url_and_title = match.group(2).strip()
                    citations[num] = url_and_title

    # Key Learnings extrahieren (neues Format: ## 💡 KEY LEARNINGS)
    if "## 💡 KEY LEARNINGS" in response:
        parts = response.split("## 💡 KEY LEARNINGS")
        dossier_text = parts[0].strip()

        if len(parts) > 1:
            learnings_part = parts[1]
            # Bis zum Sources Block oder End Marker
            if "=== SOURCES ===" in learnings_part:
                key_learnings = learnings_part.split("=== SOURCES ===")[0].strip()
            elif "=== END DOSSIER ===" in learnings_part:
                key_learnings = learnings_part.split("=== END DOSSIER ===")[0].strip()
            else:
                key_learnings = learnings_part.strip()

    # Fallback: Altes Format (=== KEY LEARNINGS ===)
    elif "=== KEY LEARNINGS ===" in response:
        parts = response.split("=== KEY LEARNINGS ===")
        dossier_text = parts[0].strip()

        if len(parts) > 1:
            learnings_part = parts[1]
            if "=== END LEARNINGS ===" in learnings_part:
                key_learnings = learnings_part.split("=== END LEARNINGS ===")[0].strip()
            else:
                key_learnings = learnings_part.strip()

    return dossier_text, key_learnings, citations
