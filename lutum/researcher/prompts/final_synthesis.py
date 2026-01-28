"""
Final Synthesis Prompt
======================
Erstellt das finale Gesamtdokument aus allen einzelnen Dossiers.

EINMALIG am Ende: Bekommt alle Punkt-Dossiers und synthetisiert sie
zu einem ultra-detaillierten finalen Dokument.

MODELL: anthropic/claude-sonnet-4.5
(Premium-Modell für höchste Qualität bei Final Synthesis)

TEXT-ONLY APPROACH:
- Keine API-Metadaten erforderlich
- Konsolidiert was in den Dossiers steht
- Evidenz-basiert, nicht spekulativ
"""

# Model für Final Synthesis (größeres Modell für alle Dossiers)
FINAL_SYNTHESIS_MODEL = "anthropic/claude-sonnet-4.5"

# WICHTIG: Hoher Timeout! Final Synthesis kann 15-20 Minuten dauern bei großen Dokumenten
FINAL_SYNTHESIS_TIMEOUT = 1200  # 20 Minuten in Sekunden

FINAL_SYNTHESIS_SYSTEM_PROMPT = """Du bist ein Meister der wissenschaftlichen Synthese und Dokumentation.

Deine Aufgabe: Aus mehreren einzelnen Dossiers ein kohärentes, tiefgehendes Gesamtwerk erschaffen.

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

2. **KEINE UNBEGRÜNDETEN SUPERLATIVE**: Claims nur wenn im Dossier-Evidence/Claim-Audit belegt.

3. **TEXT-ONLY**: Keine API-Metadaten erfinden. Nur was in den Dossiers steht.

4. **ABSCHLUSSMARKER PFLICHT**: Am Ende IMMER "=== END REPORT ===" ausgeben.
   Bei Truncation: "=== INCOMPLETE (TRUNCATED) ===" statt offenem Satz.

═══════════════════════════════════════════════════════════════════
                         FORMAT-PRIORITÄT
═══════════════════════════════════════════════════════════════════

- MEHR Tabellen/Listen, WENIGER Fließtext
- Kurze Absätze (max 5 Zeilen)
- Ziel: Maximal informationsdicht
- Substanz > Länge (kein Mindestwortcount, aber vollständig)

═══════════════════════════════════════════════════════════════════
                         PFLICHT-DELIVERABLES
═══════════════════════════════════════════════════════════════════

Diese MÜSSEN im finalen Dokument vorkommen:

A) **Evidence Appendix**: Deduplizierte Ledger-Tabellen (Repos/Papers/Threads) - Top-Einträge je Kategorie

B) **Claim Ledger**: Konsolidierte Claim-Audit-Tabelle (Top 10-20 wichtigste Claims) inkl. Setup/Baseline

C) **Maturity Matrix**: Technik vs. Reifegrad vs. Aufwand vs. Nutzen (Tabelle)

D) **Action Plan**: 5-10 konkrete nächste Schritte (Quick Wins + Experimente + Benchmarks)
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
                         AUSGABE-STRUKTUR (PFLICHT)
════════════════════════════════════════════════════════════════════════════════

Erstelle das finale Dokument EXAKT in dieser Reihenfolge:

---

# [TITEL]
[Ein prägnanter Titel der die gesamte Recherche beschreibt]

---

## EXECUTIVE SUMMARY

### Das Wichtigste in Kürze
(max 7 Bullets - die absoluten Kernerkenntnisse)
- ...

### Die zentrale Erkenntnis
[EIN Satz der alles zusammenfasst]

### Für wen ist das relevant?
(max 5 Bullets - Zielgruppe und Anwendungskontext)
- ...

---

## METHODIK

### Quellenarten
- Welche Quellenarten wurden genutzt? (Repos/Papers/Threads/Docs)
- Anzahl je Kategorie

### Filter & Constraints
- Welche Zeiträume/Plattformen/Kriterien?

### Systematische Lücken
- Was wurde NICHT abgedeckt?
- Wo könnten blinde Flecken sein?

---

## THEMENKAPITEL

[Strukturiere nach THEMEN, nicht nach Dossiers!]

### Kapitel 1: [Themenbereich]

**Kernerkenntnisse:** (Bullets)
- ...

**Mechanismus:** (kurz - wie funktioniert es?)

**Trade-offs:** (Kosten/Latenz/Komplexität/Qualität)

**Reifegrad:** Proto / Active / Prod - mit Begründung

**When to use:** ...
**When NOT to use:** ...

### Kapitel 2: [Themenbereich]
...

[So viele Kapitel wie thematisch sinnvoll]

---

## SYNTHESE

### Querverbindungen
(Bullets - wie hängen die Themen zusammen?)
- ...

### Widersprüche & Spannungen
(Bullets - wo widersprechen sich Quellen? Auflösung?)
- ...

### Übergreifende Muster
(Bullets - was wird erst im Zusammenspiel sichtbar?)
- ...

### Neue Erkenntnisse
(Bullets - was ergibt sich erst aus der Kombination?)
- ...

---

## KRITISCHE WÜRDIGUNG

### Was wissen wir sicher?
(Gut belegte Erkenntnisse mit starker Evidenz)
- ...

### Was bleibt unsicher?
(Offene Fragen, dünne Evidenz, widersprüchliche Quellen)
- ...

### Limitationen dieser Recherche
(Explizit: Was wurde nicht abgedeckt?)
- ...

---

## HANDLUNGSEMPFEHLUNGEN

### Sofort umsetzbar (Quick Wins)
- ...

### 2-6 Wochen (Experimente & Benchmarks)
- ...

### Strategisch (Architektur-Entscheidungen)
- ...

---

## ANHANG (PFLICHT-DELIVERABLES)

### A) Evidence Appendix

#### Repo-Ledger (dedupliziert, Top-Einträge)
| Repo | Link | Technik | Claim | Evidenz-Snippet | Reifegrad | Notes |
|------|------|---------|-------|-----------------|-----------|-------|
| ... | ... | ... | ... | ... | ... | ... |

#### Paper-Ledger (dedupliziert, Top-Einträge)
| Paper | Link | Jahr | Beitrag | Kernergebnis | Evidenz-Snippet | Limitations |
|-------|------|------|---------|--------------|-----------------|-------------|
| ... | ... | ... | ... | ... | ... | ... |

#### Thread-Ledger (dedupliziert, Top-Einträge)
| Plattform | Link | Thema | Hauptargument | Takeaway | Evidenz-Snippet | Credibility |
|-----------|------|-------|---------------|----------|-----------------|-------------|
| ... | ... | ... | ... | ... | ... | ... |

---

### B) Claim Ledger (konsolidiert)
| Claim | Quelle | Messgröße | Baseline | Setup | Ergebnis | Einschränkungen | Confidence |
|-------|--------|-----------|----------|-------|----------|-----------------|------------|
| ... | ... | ... | ... | ... | ... | ... | ... |

(Top 10-20 wichtigste Claims aus allen Dossiers)

---

### C) Maturity Matrix
| Technik/Ansatz | Reifegrad | Aufwand | Nutzen | Empfehlung |
|----------------|-----------|---------|--------|------------|
| ... | Proto/Active/Prod | Low/Med/High | Low/Med/High | ... |

---

### D) Action Plan
| # | Aktion | Typ | Priorität | Abhängigkeiten | Erwartetes Ergebnis |
|---|--------|-----|-----------|----------------|---------------------|
| 1 | ... | Quick Win | High | - | ... |
| 2 | ... | Experiment | Med | ... | ... |
| ... | ... | ... | ... | ... | ... |

(5-10 konkrete nächste Schritte)

---

### Glossar (optional, wenn Fachbegriffe erklärt werden müssen)

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
        all_dossiers: Liste von {point: str, dossier: str, sources: list}

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
        dossier_parts.append(f"""
┌──────────────────────────────────────────────────────────────────────────────┐
│ DOSSIER {i}: {d['point'][:60]}{'...' if len(d['point']) > 60 else ''}
└──────────────────────────────────────────────────────────────────────────────┘

{d['dossier']}
""")

    dossiers_text = "\n".join(dossier_parts)

    user_prompt = FINAL_SYNTHESIS_USER_PROMPT.format(
        user_query=user_query,
        research_plan=plan_text,
        all_dossiers=dossiers_text
    )

    return FINAL_SYNTHESIS_SYSTEM_PROMPT, user_prompt
