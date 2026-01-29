"""
Meta-Synthese Prompt v2.0
=========================
Findet QUERVERBINDUNGEN zwischen unabhängig recherchierten Bereichs-Synthesen
und erstellt wissenschaftlich fundierte Schlussfolgerungen.

v2.0 UPDATES:
- Toulmin-Argumentation (Claim + Evidence + Warrant + Qualifier + Rebuttal)
- Evidenz-Grading (Level I-VII für jede Quelle)
- PRISMA-artige Methodik-Transparenz
- Aktive Falsifikations-Suche
- Parser-kompatibles Format
"""

import re
from typing import Optional
import requests
from lutum.core.log_config import get_logger
from lutum.core.api_config import get_api_key

logger = get_logger(__name__)

# Gleiches Modell wie Final Synthesis - braucht Premium für Qualität
META_SYNTHESIS_MODEL = "anthropic/claude-sonnet-4.5"
META_SYNTHESIS_TIMEOUT = 600  # 10 Minuten

META_SYNTHESIS_SYSTEM_PROMPT = """Du bist ein Meister der wissenschaftlichen Synthese und Argumentation.

═══════════════════════════════════════════════════════════════════
                    SPRACHE (KRITISCH!)
═══════════════════════════════════════════════════════════════════

WICHTIG: Antworte IMMER in der Sprache der ursprünglichen Nutzer-Anfrage!
- Deutsche Anfrage → Deutsche Meta-Synthese
- English query → English meta-synthesis
- Alle Sektionen, Überschriften und Inhalte in der gleichen Sprache!

═══════════════════════════════════════════════════════════════════
                    FORMAT-MARKER (PFLICHT!)
═══════════════════════════════════════════════════════════════════

Diese Marker ermöglichen automatisches Parsing - EXAKT so verwenden:

SEKTIONEN:      ## EMOJI TITEL
                Beispiel: ## 🔗 QUERVERBINDUNGEN

SUB-SEKTIONEN:  ### Untertitel
                Beispiel: ### Verbindung 1: Thermodynamik ↔ Biologie

TABELLEN:       | Col1 | Col2 | Col3 |
                |------|------|------|
                | data | data | data |

LISTEN:         1) Erster Punkt
                2) Zweiter Punkt
                (NICHT 1. oder - für nummerierte Listen!)

HIGHLIGHT-BOX:  > 💡 **Wichtig:** Text hier
                > ⚠️ **Warnung:** Text hier
                > ❓ **Offen:** Text hier

KEY-VALUE:      - **Schlüssel:** Wert

CITATION:       Text mit Quellenbeleg[1] und weiterer Beleg[2][3]

ABSCHLUSS:      === END META-SYNTHESIS ===

═══════════════════════════════════════════════════════════════════
                    DEINE AUFGABE
═══════════════════════════════════════════════════════════════════

Du erhältst N UNABHÄNGIG recherchierte Bereichs-Synthesen.

Diese Bereiche wurden PARALLEL erforscht - ohne Wissen voneinander.
Jetzt findest du VERBINDUNGEN die erst sichtbar werden wenn man
alle Bereiche zusammen betrachtet.

DAS IST NICHT:
- Zusammenfassen was in den Bereichen steht
- Wiederholen der Kernerkenntnisse
- Aneinanderreihen der Synthesen

DAS IST:
- NEUE Erkenntnisse aus der KOMBINATION
- QUERVERBINDUNGEN die niemand sehen konnte
- WIDERSPRÜCHE und deren Auflösung
- MUSTER über alle Bereiche
- BEWEISE für Schlussfolgerungen

═══════════════════════════════════════════════════════════════════
                    TOULMIN-ARGUMENTATION (PFLICHT!)
═══════════════════════════════════════════════════════════════════

Jede wichtige Schlussfolgerung MUSS dem Toulmin-Modell folgen:

┌─────────────────────────────────────────────────────────────────┐
│ CLAIM:     Die Behauptung die du aufstellst                     │
│ GROUNDS:   Die Evidenz die den Claim stützt [mit Citations]     │
│ WARRANT:   WARUM die Evidenz den Claim stützt (die Logik)       │
│ BACKING:   Zusätzliche Stützung des Warrants                    │
│ QUALIFIER: Unter welchen Bedingungen gilt der Claim?            │
│ REBUTTAL:  Gegenargumente und warum sie den Claim nicht kippen  │
└─────────────────────────────────────────────────────────────────┘

BEISPIEL:
- **Claim:** P≠NP ist eine physikalische Notwendigkeit
- **Grounds:** Thermodynamische Analysen zeigen exponentielle Entropiekosten[1][2]
- **Warrant:** Exponentielle Entropie würde den 2. Hauptsatz verletzen
- **Backing:** Der 2. Hauptsatz ist das am besten bestätigte Naturgesetz
- **Qualifier:** In klassischen Berechnungsmodellen (nicht Quanten)
- **Rebuttal:** Quantenalgorithmen könnten Kosten reduzieren, aber Messungen bleiben irreversibel[3]

OHNE Toulmin-Struktur ist eine Schlussfolgerung NICHT wissenschaftlich!

═══════════════════════════════════════════════════════════════════
                    EVIDENZ-GRADING (PFLICHT!)
═══════════════════════════════════════════════════════════════════

Bewerte jede Quelle nach dem GRADE-System:

| Level | Beschreibung | Beispiele |
|-------|--------------|-----------|
| I | Systematic Reviews / Meta-Analysen | Cochrane Reviews, Meta-Analysen |
| II | Einzelne RCTs / hochwertige Studien | Nature, Science, Peer-reviewed |
| III | Kontrollierte Studien ohne Randomisierung | Kohortenstudien |
| IV | Fall-Kontroll-Studien | Observationsstudien |
| V | Systematische Reviews deskriptiver Studien | Qualitative Reviews |
| VI | Einzelne deskriptive Studien | Case Reports, Surveys |
| VII | Expertenmeinungen | Blogs, Foren, Reddit |

In der Synthese MUSS klar sein:
- Welches Evidenz-Level stützt welchen Claim?
- Wo stützt Level I-II? (starke Evidenz)
- Wo nur Level VI-VII? (schwache Evidenz, mehr Forschung nötig)

FORMAT: "Claim X wird durch Level II Evidenz gestützt[1][2], während
Claim Y nur auf Level VII Expertenmeinungen basiert[3]."

═══════════════════════════════════════════════════════════════════
                    FALSIFIKATIONS-PFLICHT (NEU!)
═══════════════════════════════════════════════════════════════════

Für jede wichtige Schlussfolgerung MUSST du aktiv suchen:

1. **Was würde diese Schlussfolgerung WIDERLEGEN?**
   - Welche Evidenz würde den Claim falsifizieren?
   - Gibt es diese Evidenz in den Quellen?

2. **Welche Gegenargumente existieren?**
   - Was sagen Kritiker?
   - Warum sind deren Argumente (nicht) überzeugend?

3. **Wo sind die GRENZEN des Claims?**
   - Unter welchen Bedingungen gilt er NICHT?
   - Welche Annahmen sind erforderlich?

Eine Schlussfolgerung ohne Falsifikations-Analyse ist keine Wissenschaft!

═══════════════════════════════════════════════════════════════════
                    VERBINDUNGS-TYPEN
═══════════════════════════════════════════════════════════════════

Suche nach diesen Typen von Querverbindungen:

1. **KAUSAL**: A verursacht B (nicht nur Korrelation!)
2. **ANALOG**: A funktioniert ähnlich wie B (strukturelle Ähnlichkeit)
3. **KONTRÄR**: A widerspricht B (produktive Spannung)
4. **KOMPLEMENTÄR**: A und B ergänzen sich (Synergieeffekt)
5. **EMERGENT**: A+B+C zusammen erzeugen neues Phänomen D

Für jede Verbindung: Welcher Typ ist es und warum?
"""

META_SYNTHESIS_USER_PROMPT = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        META-SYNTHESE-AUFTRAG                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

URSPRÜNGLICHE FORSCHUNGSFRAGE:
{user_query}

════════════════════════════════════════════════════════════════════════════════
                         BEREICHS-SYNTHESEN
════════════════════════════════════════════════════════════════════════════════

{all_syntheses}

════════════════════════════════════════════════════════════════════════════════
                         AUSGABE-STRUKTUR
════════════════════════════════════════════════════════════════════════════════

Erstelle die Meta-Synthese mit diesen Sektionen:

---

## 🔬 METHODIK-TRANSPARENZ

### Quellenübersicht

| Bereich | Quellen | Level I-II | Level III-V | Level VI-VII |
|---------|---------|------------|-------------|--------------|
| Bereich 1 | N | X | Y | Z |
| Bereich 2 | N | X | Y | Z |
| ... | ... | ... | ... | ... |

### Evidenz-Verteilung

> 💡 **Stärken:** Wo haben wir starke Evidenz (Level I-II)?

> ⚠️ **Schwächen:** Wo basieren wir nur auf schwacher Evidenz (Level VI-VII)?

### Systematische Lücken

Was wurde NICHT gefunden oder abgedeckt?
1) Lücke 1 - warum problematisch
2) Lücke 2 - warum problematisch

---

## 🔗 QUERVERBINDUNGEN

### Verbindung 1: [Prägnanter Titel]

- **Bereiche:** Bereich X ↔ Bereich Y
- **Typ:** [Kausal/Analog/Konträr/Komplementär/Emergent]
- **Erkenntnis:** Was verbindet sie auf nicht-offensichtliche Weise?

**Toulmin-Analyse:**
- **Claim:** [Die Verbindungs-Behauptung]
- **Grounds:** [Evidenz aus beiden Bereichen][Citations]
- **Warrant:** [WARUM diese Evidenz die Verbindung beweist]
- **Qualifier:** [Unter welchen Bedingungen gilt das?]
- **Rebuttal:** [Gegenargumente und deren Widerlegung]

### Verbindung 2: [Prägnanter Titel]
[Gleiche Struktur]

### Verbindung N: [Prägnanter Titel]
[Mindestens 3 nicht-triviale Verbindungen!]

---

## ⚠️ WIDERSPRÜCHE & SPANNUNGEN

### Widerspruch 1: [Prägnanter Titel]

- **Bereich X sagt:** [Position A][Citation]
- **Bereich Y sagt:** [Position B][Citation]
- **Evidenz-Level:** X basiert auf Level [N], Y auf Level [M]

**Auflösungsversuch:**
- **Möglichkeit A:** [Wie könnte der Widerspruch aufgelöst werden?]
- **Möglichkeit B:** [Alternative Erklärung]
- **Bewertung:** [Welche Auflösung ist wahrscheinlicher und warum?]

> ❓ **Falls nicht auflösbar:** Was müsste erforscht werden um diesen Widerspruch zu klären?

---

## 🧩 ÜBERGREIFENDE MUSTER

Was zeigt sich erst wenn man ALLE Bereiche zusammen betrachtet?

### Muster 1: [Prägnanter Titel]

- **Beschreibung:** [Das Muster das sich über mehrere Bereiche zieht]
- **Beobachtet in:** Bereich X, Y, Z
- **Evidenz-Stärke:** [Wie gut belegt ist dieses Muster?]

> 💡 **Implikation:** Was bedeutet dieses Muster für die Forschungsfrage?

### Muster 2: [Prägnanter Titel]
[Gleiche Struktur]

---

## 💎 ZENTRALE SCHLUSSFOLGERUNGEN

### Schlussfolgerung 1: [Prägnanter Titel]

**Toulmin-Vollanalyse:**

| Element | Inhalt |
|---------|--------|
| **CLAIM** | [Die Hauptaussage] |
| **GROUNDS** | [Evidenz mit Citations und Level-Angabe] |
| **WARRANT** | [Die logische Brücke: WARUM beweist die Evidenz den Claim?] |
| **BACKING** | [Zusätzliche Stützung des Warrants] |
| **QUALIFIER** | [Einschränkungen: Wann/wo gilt das?] |
| **REBUTTAL** | [Gegenargumente und deren Adressierung] |

**Falsifikations-Check:**
- **Was würde diesen Claim widerlegen?** [Konkrete Bedingungen]
- **Existiert diese Gegen-Evidenz?** [Ja/Nein, mit Begründung]
- **Konfidenz:** [Hoch/Mittel/Niedrig] weil [Begründung]

### Schlussfolgerung 2: [Prägnanter Titel]
[Gleiche Struktur]

---

## 🎯 SYNTHESE-FAZIT

### Die Meta-Erkenntnis

> 💡 **Ein Satz der die gesamte interdisziplinäre Synthese zusammenfasst:**
[Der zentrale Takeaway]

### Antwort auf die Forschungsfrage

Basierend auf der Synthese aller Bereiche:

1) [Hauptantwort mit Evidenz-Level-Angabe]
2) [Sekundäre Erkenntnis]
3) [Tertiäre Erkenntnis]

### Was wir NICHT beantworten können

> ⚠️ **Offene Fragen die weitere Forschung erfordern:**
1) [Offene Frage 1 - warum relevant]
2) [Offene Frage 2 - warum relevant]

### Empfehlungen für weitere Recherche

Falls die Forschungsfrage tiefer untersucht werden soll:
1) [Empfehlung 1 - was und warum]
2) [Empfehlung 2 - was und warum]

---

## 📎 QUELLENVERZEICHNIS

Konsolidiertes Verzeichnis mit Evidenz-Level:

=== SOURCES ===
[1] URL - Titel | Level: [I-VII]
[2] URL - Titel | Level: [I-VII]
[3] URL - Titel | Level: [I-VII]
...
=== END SOURCES ===

---

=== END META-SYNTHESIS ===
"""


def build_meta_synthesis_prompt(
    user_query: str,
    bereichs_synthesen: list[dict]
) -> tuple[str, str]:
    """
    Baut den Meta-Synthese-Prompt.

    Args:
        user_query: Ursprüngliche Forschungsfrage
        bereichs_synthesen: Liste von {bereich_titel: str, synthese: str, sources: list}

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    # Bereichs-Synthesen formatieren
    synthesen_parts = []
    for i, s in enumerate(bereichs_synthesen, 1):
        bereich_titel = s.get('bereich_titel', f'Bereich {i}')
        synthese_content = s.get('synthese', '')
        sources = s.get('sources', [])

        synthesen_parts.append(f"""
┌──────────────────────────────────────────────────────────────────────────────┐
│ BEREICH {i}: {bereich_titel}
│ ({len(sources)} Quellen)
└──────────────────────────────────────────────────────────────────────────────┘

{synthese_content}
""")

    synthesen_text = "\n".join(synthesen_parts)

    user_prompt = META_SYNTHESIS_USER_PROMPT.format(
        user_query=user_query,
        all_syntheses=synthesen_text
    )

    return META_SYNTHESIS_SYSTEM_PROMPT, user_prompt


def parse_meta_synthesis_response(response: str) -> tuple[str, dict]:
    """
    Parst die Meta-Synthese-Response.

    Args:
        response: Volle LLM Response

    Returns:
        Tuple (meta_synthesis_text, metadata)
        - meta_synthesis_text: Der vollständige Text
        - metadata: Dict mit extrahierten Elementen
    """
    metadata = {
        "querverbindungen": 0,
        "widersprueche": 0,
        "muster": 0,
        "schlussfolgerungen": 0,
        "evidenz_levels": {},
    }

    # Querverbindungen zählen
    verbindungen = re.findall(r'###\s*Verbindung\s*\d+', response)
    metadata["querverbindungen"] = len(verbindungen)

    # Widersprüche/Spannungen zählen
    widersprueche = re.findall(r'###\s*(?:Widerspruch|Spannung)\s*\d+', response)
    metadata["widersprueche"] = len(widersprueche)

    # Muster zählen
    muster = re.findall(r'###\s*Muster\s*\d+', response)
    metadata["muster"] = len(muster)

    # Schlussfolgerungen zählen
    schlussfolgerungen = re.findall(r'###\s*Schlussfolgerung\s*\d+', response)
    metadata["schlussfolgerungen"] = len(schlussfolgerungen)

    # Evidenz-Level aus Sources Block extrahieren
    sources_match = re.search(
        r'=== SOURCES ===\n(.+?)\n=== END SOURCES ===',
        response, re.DOTALL
    )
    if sources_match:
        sources_block = sources_match.group(1)
        level_counts = {"I-II": 0, "III-V": 0, "VI-VII": 0}
        for line in sources_block.split('\n'):
            if 'Level:' in line:
                if any(x in line for x in ['Level: I', 'Level: II']):
                    level_counts["I-II"] += 1
                elif any(x in line for x in ['Level: III', 'Level: IV', 'Level: V']):
                    level_counts["III-V"] += 1
                elif any(x in line for x in ['Level: VI', 'Level: VII']):
                    level_counts["VI-VII"] += 1
        metadata["evidenz_levels"] = level_counts

    logger.info(f"[META-SYNTHESIS] Parsed: {metadata}")

    return response, metadata


# === CLI TEST ===
if __name__ == "__main__":
    # Test mit Dummy-Daten
    test_synthesen = [
        {
            "bereich_titel": "Thermodynamik & Statistische Mechanik",
            "synthese": """
## Kernerkenntnisse

1) NP-vollständige Probleme können auf das Ising-Spin-Glas-Modell abgebildet werden[1][2]
2) Die Energielandschaft zeigt "topologische Turbulenz"[3]
3) P=NP würde den Zweiten Hauptsatz verletzen[4]
""",
            "sources": ["arxiv.org/1", "arxiv.org/2", "arxiv.org/3", "arxiv.org/4"]
        },
        {
            "bereich_titel": "Biologische Computation",
            "synthese": """
## Kernerkenntnisse

1) Amöben lösen TSP in linearer Zeit durch physikalische Parallelität[5]
2) Proteinfaltung ist NP-vollständig aber Proteine falten sich schnell[6]
""",
            "sources": ["nature.com/1", "pnas.org/1"]
        },
    ]

    system, user = build_meta_synthesis_prompt(
        "Erkläre P vs NP aus physikalischer Perspektive",
        test_synthesen
    )

    print("System Prompt (first 1000 chars):")
    print(system[:1000])
    print("\n" + "=" * 60 + "\n")
    print("User Prompt (first 2000 chars):")
    print(user[:2000])
