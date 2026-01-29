# Lutum Veritas - Deep Research Engine
# Copyright (C) 2026 Martin Gehrken
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Academic Conclusion Prompt - DER MAGISCHE FINALE CALL
=====================================================
Hier passiert die Magie. Hier treffen hunderte Quellen und
zehntausende Zeichen Wissen auf: "JETZT finde die Lösung."

Dieser Call bekommt:
1. Die originale User-Frage (EXAKT)
2. Alle Bereichs-Synthesen (bereits komprimiert, fokussiert)

Seine Aufgabe:
- Querverbindungen zwischen Bereichen finden
- Widersprüche identifizieren
- Übergreifende Muster erkennen
- NEUE Erkenntnisse die nur durch Kombination sichtbar werden
- Die ANTWORT auf die ursprüngliche Frage
"""

import logging

logger = logging.getLogger(__name__)

# Das BESTE Model für den finalen Call
ACADEMIC_CONCLUSION_MODEL = "qwen/qwen3-vl-235b-a22b-instruct"
ACADEMIC_CONCLUSION_TIMEOUT = 300  # 5 Minuten - das ist der wichtigste Call


ACADEMIC_CONCLUSION_SYSTEM_PROMPT = """Du bist ein brillanter interdisziplinärer Forscher.

Du erhältst:
1. Eine komplexe Forschungsfrage
2. Mehrere UNABHÄNGIG recherchierte Bereichs-Synthesen

Diese Bereiche wurden ABSICHTLICH isoliert voneinander erforscht.
Jetzt ist DEIN Moment: Du siehst als ERSTER das Gesamtbild.

═══════════════════════════════════════════════════════════════════
                        DEINE MISSION
═══════════════════════════════════════════════════════════════════

1. QUERVERBINDUNGEN FINDEN
   - Welche Konzepte aus Bereich A erklären Phänomene in Bereich B?
   - Wo gibt es unerwartete Parallelen?
   - Welche Brücken existieren zwischen den Disziplinen?

2. WIDERSPRÜCHE IDENTIFIZIEREN
   - Wo widersprechen sich die Bereiche?
   - Sind diese Widersprüche auflösbar oder fundamental?
   - Was bedeuten sie für die Gesamtfrage?

3. ÜBERGREIFENDE MUSTER ERKENNEN
   - Welche Muster tauchen in mehreren Bereichen auf?
   - Was sagt uns das über das zugrundeliegende Problem?

4. NEUE ERKENNTNISSE SYNTHETISIEREN
   - Was wird ERST JETZT sichtbar, da alle Bereiche zusammenkommen?
   - Welche Schlussfolgerungen kann NIEMAND ziehen der nur einen Bereich kennt?

5. DIE ANTWORT FORMULIEREN
   - Beantworte die ursprüngliche Frage so gut es die Evidenz erlaubt
   - Sei ehrlich über Unsicherheiten
   - Benenne was wir WISSEN vs. was wir VERMUTEN

═══════════════════════════════════════════════════════════════════
                        OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════

## 🔗 QUERVERBINDUNGEN

### Verbindung 1: [Titel]
[Beschreibung wie Bereich X und Y zusammenhängen]

### Verbindung 2: [Titel]
...

## ⚡ WIDERSPRÜCHE & SPANNUNGEN

### Widerspruch 1: [Titel]
- **Bereich A sagt:** ...
- **Bereich B sagt:** ...
- **Auflösung/Bedeutung:** ...

## 🔄 ÜBERGREIFENDE MUSTER

1) Muster das in mehreren Bereichen auftaucht
2) ...

## 💡 NEUE ERKENNTNISSE

> Diese Erkenntnisse sind NUR durch die Kombination der Bereiche möglich:

1) Erste Meta-Erkenntnis
2) Zweite Meta-Erkenntnis
...

## 🎯 ANTWORT AUF DIE FORSCHUNGSFRAGE

### Was wir wissen (hohe Konfidenz):
- ...

### Was wir vermuten (moderate Konfidenz):
- ...

### Was offen bleibt:
- ...

### Fazit
[Die beste Antwort die die Evidenz hergibt - ehrlich, nuanciert, aber klar]

═══════════════════════════════════════════════════════════════════

SPRACHE: Antworte in der Sprache der ursprünglichen Frage!
DENKE TIEF: Das ist der wichtigste Teil der gesamten Recherche.
SEI MUTIG: Ziehe Schlüsse die andere nicht sehen würden."""


def build_academic_conclusion_prompt(
    user_query: str,
    bereichs_synthesen: list[dict],
) -> tuple[str, str]:
    """
    Baut den FINALEN Prompt - der magische Call.

    Args:
        user_query: Die ORIGINALE User-Frage (exakt!)
        bereichs_synthesen: Liste von {bereich_titel, synthese, sources_count}

    Returns:
        (system_prompt, user_prompt)
    """

    # Alle Synthesen formatieren
    synthesen_text = ""
    total_sources = 0

    for i, s in enumerate(bereichs_synthesen, 1):
        total_sources += s.get('sources_count', 0)
        synthesen_text += f"\n{'═'*70}\n"
        synthesen_text += f"BEREICH {i}: {s['bereich_titel']}\n"
        synthesen_text += f"Quellen in diesem Bereich: {s.get('sources_count', 'N/A')}\n"
        synthesen_text += f"{'═'*70}\n\n"
        synthesen_text += s['synthese']
        synthesen_text += "\n"

    user_prompt = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    URSPRÜNGLICHE FORSCHUNGSFRAGE                     ║
╚══════════════════════════════════════════════════════════════════════╝

"{user_query}"

╔══════════════════════════════════════════════════════════════════════╗
║                        RECHERCHE-ÜBERSICHT                           ║
╚══════════════════════════════════════════════════════════════════════╝

Anzahl unabhängiger Bereiche: {len(bereichs_synthesen)}
Gesamtzahl analysierter Quellen: {total_sources}

Die folgenden Bereiche wurden UNABHÄNGIG voneinander recherchiert.
Jeder Bereich hatte eigene Suchstrategien, eigene Quellen, eigene Analyse.
Du siehst sie jetzt zum ERSTEN MAL zusammen.

╔══════════════════════════════════════════════════════════════════════╗
║                      BEREICHS-SYNTHESEN                              ║
╚══════════════════════════════════════════════════════════════════════╝
{synthesen_text}

╔══════════════════════════════════════════════════════════════════════╗
║                         DEINE AUFGABE                                ║
╚══════════════════════════════════════════════════════════════════════╝

Du hast jetzt Zugang zu {len(bereichs_synthesen)} unabhängigen Forschungsperspektiven
basierend auf {total_sources} analysierten Quellen.

FINDE:
1. Querverbindungen zwischen den Bereichen
2. Widersprüche und Spannungen
3. Übergreifende Muster
4. Neue Erkenntnisse die NUR durch Kombination sichtbar werden
5. Die beste mögliche ANTWORT auf die Forschungsfrage

Das ist dein Moment. Denke tief. Sei brillant."""

    logger.info(f"Academic Conclusion prompt: {len(user_prompt)} chars, {len(bereichs_synthesen)} areas, {total_sources} sources")

    return ACADEMIC_CONCLUSION_SYSTEM_PROMPT, user_prompt
