"""
Final Synthesis Prompt
======================
Erstellt das finale Gesamtdokument aus allen einzelnen Dossiers.

EINMALIG am Ende: Bekommt alle Punkt-Dossiers und synthetisiert sie
zu einem ultra-detaillierten finalen Dokument.

MODELL: anthropic/claude-sonnet-4.5
(Premium-Modell für höchste Qualität bei Final Synthesis)

FORMAT v2.0:
- Universelle Marker für Parser (## EMOJI TITEL)
- Konsolidiertes Citation-System [N]
- PFLICHT vs OPTIONAL Sektionen (generisch für JEDE Recherche)
"""

# Model für Final Synthesis (größeres Modell für alle Dossiers)
FINAL_SYNTHESIS_MODEL = "anthropic/claude-sonnet-4.5"

# WICHTIG: Hoher Timeout! Final Synthesis kann 15-20 Minuten dauern bei großen Dokumenten
FINAL_SYNTHESIS_TIMEOUT = 1200  # 20 Minuten in Sekunden

FINAL_SYNTHESIS_SYSTEM_PROMPT = """Du bist ein Meister der wissenschaftlichen Synthese und Dokumentation.

═══════════════════════════════════════════════════════════════════
                    SPRACHE (KRITISCH!)
═══════════════════════════════════════════════════════════════════

WICHTIG: Antworte IMMER in der Sprache der ursprünglichen Nutzer-Anfrage!
- Deutsche Anfrage → Deutscher Report
- English query → English report
- Mischung → Sprache des Hauptteils der Anfrage

═══════════════════════════════════════════════════════════════════
                    CITATION-SYSTEM (PFLICHT!)
═══════════════════════════════════════════════════════════════════

JEDE faktische Aussage MUSS mit einer Citation markiert werden:
- Format: Text mit Aussage[1] und weitere Aussage[2]
- Übernimm Citations aus den Dossiers
- Konsolidiere zu einem globalen Quellenverzeichnis am Ende
- Nummeriere neu durch: [1], [2], [3]... (fortlaufend im gesamten Dokument)

BEISPIEL:
"RAG erreicht 95% Accuracy bei strukturierten Benchmarks"[1], während
traditionelle Methoden bei etwa 70% stagnieren[2]. Neuere Ansätze
kombinieren beide Techniken für optimale Ergebnisse[3][4].

═══════════════════════════════════════════════════════════════════
                    FORMAT-MARKER (PFLICHT!)
═══════════════════════════════════════════════════════════════════

Diese Marker ermöglichen automatisches Parsing - EXAKT so verwenden:

SEKTIONEN:      ## EMOJI TITEL
                Beispiel: ## 📊 EXECUTIVE SUMMARY

SUB-SEKTIONEN:  ### Untertitel
                Beispiel: ### Das Wichtigste in Kürze

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
                         WAS SYNTHESE BEDEUTET
═══════════════════════════════════════════════════════════════════

Synthese ist NICHT:
- Einfaches Zusammenkopieren der Dossiers
- Aneinanderreihen von Abschnitten
- Wiederholung derselben Informationen

Synthese IST:
- Neue Erkenntnisse aus der KOMBINATION der Informationen ziehen
- QUERVERBINDUNGEN zwischen den Themen herstellen
- MUSTER erkennen die in Einzeldossiers nicht sichtbar sind
- Ein NARRATIV schaffen das alles verbindet
- WIDERSPRÜCHE auflösen oder transparent machen

═══════════════════════════════════════════════════════════════════
                         HARTREGELN (PFLICHT)
═══════════════════════════════════════════════════════════════════

1. **KEINE REDUNDANZ**: Identische Inhalte aus Dossiers nur einmal, dann referenzieren.

2. **KEINE UNBEGRÜNDETEN SUPERLATIVE**: Claims nur wenn im Dossier-Evidence belegt.

3. **TEXT-ONLY**: Keine API-Metadaten erfinden. Nur was in den Dossiers steht.

4. **ABSCHLUSSMARKER PFLICHT**: Am Ende IMMER "=== END REPORT ===" ausgeben.

5. **CITATIONS PFLICHT**: Jede faktische Aussage braucht [N] Referenz.

═══════════════════════════════════════════════════════════════════
                         KATEGORIEN-LOGIK
═══════════════════════════════════════════════════════════════════

PFLICHT-Sektionen: Diese MÜSSEN in JEDEM Report vorkommen!
OPTIONAL-Sektionen: NUR wenn für dieses Thema wirklich relevant!

Bei Unsicherheit: WEGLASSEN ist besser als mit Fülltext aufblähen.

Beispiel - "Geschichte des Römischen Reichs":
- Handlungsempfehlungen → WEGLASSEN (nicht actionable)
- Maturity Matrix → WEGLASSEN (keine Tech-Vergleiche)
- Claim Ledger → WEGLASSEN (keine quantitativen Claims)

Beispiel - "RAG-Optimierung für Enterprise":
- Handlungsempfehlungen → EINSCHLIESSEN (sehr actionable)
- Maturity Matrix → EINSCHLIESSEN (Tech-Vergleich sinnvoll)
- Claim Ledger → EINSCHLIESSEN (Performance-Claims prüfen)
"""

FINAL_SYNTHESIS_USER_PROMPT = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                           SYNTHESE-AUFTRAG                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

URSPRÜNGLICHE AUFGABE:
{user_query}

ABGEARBEITETER RECHERCHE-PLAN:
{research_plan}

════════════════════════════════════════════════════════════════════════════════
                              EINZELNE DOSSIERS
════════════════════════════════════════════════════════════════════════════════

{all_dossiers}

════════════════════════════════════════════════════════════════════════════════
                         AUSGABE-STRUKTUR
════════════════════════════════════════════════════════════════════════════════

Erstelle das finale Dokument mit diesen Sektionen.
PFLICHT = Immer ausgeben | OPTIONAL = Nur wenn relevant!

---

# [TITEL]

Ein prägnanter Titel der die gesamte Recherche beschreibt.

---

## 📊 EXECUTIVE SUMMARY
(PFLICHT)

### Das Wichtigste in Kürze

Die absoluten Kernerkenntnisse (5-7 Punkte):

1) Erste Kernerkenntnis mit Quellenbeleg[1]
2) Zweite Kernerkenntnis[2]
3) Dritte Kernerkenntnis[3][4]
4) ...

> 💡 **Die zentrale Erkenntnis:** Ein Satz der alles zusammenfasst.

### Für wen ist das relevant?

- **Zielgruppe 1:** Warum relevant
- **Zielgruppe 2:** Warum relevant
- **Zielgruppe 3:** Warum relevant

---

## 🔬 METHODIK
(PFLICHT)

### Quellenarten

| Typ | Anzahl | Beispiele |
|-----|--------|-----------|
| GitHub Repos | X | repo1, repo2 |
| Papers/ArXiv | X | paper1, paper2 |
| Community (Reddit/HN) | X | thread1, thread2 |
| Dokumentation | X | docs1, docs2 |

### Filter & Constraints

- **Zeitraum:** z.B. 2023-2025
- **Plattformen:** z.B. GitHub, ArXiv, Reddit
- **Sprachen:** z.B. Englisch, Deutsch
- **Kriterien:** z.B. >100 Stars, Peer-reviewed

### Systematische Lücken

> ⚠️ **Diese Bereiche wurden NICHT abgedeckt:**
- Lücke 1 (warum)
- Lücke 2 (warum)
- Lücke 3 (warum)

---

## 📚 THEMENKAPITEL
(PFLICHT)

Strukturiere nach THEMEN, nicht nach Dossiers!
So viele Kapitel wie thematisch sinnvoll.

### Kapitel 1: [Themenbereich]

**Kernerkenntnisse:**
1) Erkenntnis mit Citation[5]
2) Erkenntnis mit Citation[6]
3) ...

**Details:**
- **Aspekt 1:** Beschreibung[7]
- **Aspekt 2:** Beschreibung[8]

**Trade-offs:**
- **Pro:** ...
- **Contra:** ...

> 💡 **Takeaway:** Zusammenfassung dieses Kapitels in einem Satz.

### Kapitel 2: [Themenbereich]

[Gleiche Struktur wie Kapitel 1]

### Kapitel N: [Themenbereich]

[So viele Kapitel wie nötig]

---

## 🔗 SYNTHESE
(PFLICHT)

### Querverbindungen

Wie hängen die Themen zusammen?

- **Verbindung 1:** Thema A und Thema B hängen zusammen weil...[9]
- **Verbindung 2:** ...[10]

### Widersprüche & Spannungen

Wo widersprechen sich Quellen?

1) **Widerspruch:** Quelle A sagt X[11], Quelle B sagt Y[12]
   - **Auflösung:** ...

2) **Spannung:** ...

### Übergreifende Muster

> 💡 **Was wird erst in der Zusammenschau sichtbar:**
- Muster 1
- Muster 2
- Muster 3

### Neue Erkenntnisse

Was ergibt sich erst aus der Kombination der Dossiers?

1) Neue Erkenntnis 1
2) Neue Erkenntnis 2

---

## ⚖️ KRITISCHE WÜRDIGUNG
(PFLICHT)

### Was wissen wir sicher?

Gut belegte Erkenntnisse mit starker Evidenz:

1) Sichere Erkenntnis 1[13][14]
2) Sichere Erkenntnis 2[15]
3) ...

### Was bleibt unsicher?

Offene Fragen, dünne Evidenz, widersprüchliche Quellen:

1) Unsichere Frage 1
2) Unsichere Frage 2
3) ...

### Limitationen dieser Recherche

> ⚠️ **Explizite Grenzen:**
- Limitation 1 (z.B. nur englische Quellen)
- Limitation 2 (z.B. kein Zugang zu Paywalled Papers)
- Limitation 3 (z.B. Zeitraum begrenzt)

---

## 🎯 HANDLUNGSEMPFEHLUNGEN
(OPTIONAL - NUR wenn actionable Empfehlungen sinnvoll sind!)

### Sofort umsetzbar (Quick Wins)

| Aktion | Aufwand | Erwartung |
|--------|---------|-----------|
| Aktion 1 | Gering | Ergebnis 1 |
| Aktion 2 | Gering | Ergebnis 2 |

### Mittelfristig (2-6 Wochen)

1) Empfehlung 1
2) Empfehlung 2

### Strategisch (Langfristig)

1) Strategische Empfehlung 1
2) Strategische Empfehlung 2

---

## 📊 MATURITY MATRIX
(OPTIONAL - NUR bei Tech-Vergleichen oder Produkt-Evaluierungen!)

| Technik/Ansatz | Reifegrad | Setup | Operations | Nutzen | Empfehlung |
|----------------|-----------|-------|------------|--------|------------|
| Technik 1 | Production | Low | Low | High | Quick Win |
| Technik 2 | Beta | Medium | Medium | Medium-High | Test |
| Technik 3 | Research | High | High | Varies | Beobachten |

---

## 📋 TOP QUELLEN
(OPTIONAL - NUR wenn besonders wertvolle Quellen hervorgehoben werden sollen!)

Die wichtigsten Quellen aus der Recherche:

| # | Quelle | Typ | Warum wertvoll |
|---|--------|-----|----------------|
| [1] | Name | Repo/Paper/Thread | Kurzbeschreibung |
| [2] | Name | ... | ... |

---

## 📎 QUELLENVERZEICHNIS
(PFLICHT)

Konsolidiertes Verzeichnis aller zitierten Quellen:

=== SOURCES ===
[1] URL_1 - Titel/Beschreibung
[2] URL_2 - Titel/Beschreibung
[3] URL_3 - Titel/Beschreibung
[4] URL_4 - Titel/Beschreibung
[5] URL_5 - Titel/Beschreibung
...
=== END SOURCES ===

---

=== END REPORT ===
"""


def build_final_synthesis_prompt(
    user_query: str,
    research_plan: list[str],
    all_dossiers: list[dict]
) -> tuple[str, str]:
    """
    Baut den Final-Synthesis-Prompt.

    Args:
        user_query: Ursprüngliche Aufgabe
        research_plan: Liste der Recherche-Punkte
        all_dossiers: Liste von {point: str, dossier: str, sources: list, citations: dict}

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    # Research Plan formatieren
    plan_lines = []
    for i, point in enumerate(research_plan, 1):
        plan_lines.append(f"{i}. {point}")
    plan_text = "\n".join(plan_lines)

    # Dossiers formatieren
    dossier_parts = []
    for i, d in enumerate(all_dossiers, 1):
        point_title = d.get('point', f'Punkt {i}')
        dossier_content = d.get('dossier', '')

        dossier_parts.append(f"""
┌──────────────────────────────────────────────────────────────────────────────┐
│ DOSSIER {i}: {point_title[:60]}{'...' if len(point_title) > 60 else ''}
└──────────────────────────────────────────────────────────────────────────────┘

{dossier_content}
""")

    dossiers_text = "\n".join(dossier_parts)

    user_prompt = FINAL_SYNTHESIS_USER_PROMPT.format(
        user_query=user_query,
        research_plan=plan_text,
        all_dossiers=dossiers_text
    )

    return FINAL_SYNTHESIS_SYSTEM_PROMPT, user_prompt


def parse_final_synthesis_response(response: str) -> tuple[str, dict]:
    """
    Parst die Final-Synthesis-Response und extrahiert Citations.

    Args:
        response: Volle LLM Response

    Returns:
        Tuple (report_text, citations)
        - report_text: Der vollständige Report
        - citations: Dict {1: "url - title", 2: "url - title", ...}
    """
    import re

    report_text = response
    citations = {}

    # Sources Block extrahieren
    sources_match = re.search(
        r'=== SOURCES ===\n(.+?)\n=== END SOURCES ===',
        response, re.DOTALL
    )

    if sources_match:
        sources_block = sources_match.group(1)
        for line in sources_block.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            # Format: [N] URL - Title
            match = re.match(r'\[(\d+)\]\s+(.+)', line)
            if match:
                num = int(match.group(1))
                url_and_title = match.group(2).strip()
                citations[num] = url_and_title

    return report_text, citations
