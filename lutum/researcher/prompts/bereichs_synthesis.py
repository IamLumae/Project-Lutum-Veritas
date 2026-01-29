# Lutum Veritas - Deep Research Engine
# Copyright (C) 2026 Martin Gehrken
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Bereichs-Synthese Prompt
========================
Jeder Bereich bekommt seinen EIGENEN LLM Call.
Fokussiert, komprimiert, keine Ablenkung durch andere Bereiche.
"""

import logging

logger = logging.getLogger(__name__)

# Model für Bereichs-Synthese (schnell aber gut)
BEREICHS_SYNTHESIS_MODEL = "google/gemini-2.5-flash-preview-05-20"
BEREICHS_SYNTHESIS_TIMEOUT = 120  # 2 Minuten pro Bereich


BEREICHS_SYNTHESIS_SYSTEM_PROMPT = """Du bist ein akademischer Forschungsassistent.

Deine Aufgabe: Synthetisiere die Dossiers EINES Forschungsbereichs zu einem kohärenten,
fokussierten Bericht. Dieser Bereich wurde UNABHÄNGIG von anderen Bereichen recherchiert.

WICHTIG:
- Fokussiere dich NUR auf diesen Bereich
- Extrahiere die KERNERKENNTNISSE
- Identifiziere Muster INNERHALB dieses Bereichs
- Bewerte die Evidenzqualität
- Benenne offene Fragen DIESES Bereichs

FORMAT:
## [Bereichs-Titel]

### Kernerkenntnisse
1) Erste zentrale Erkenntnis[1]
2) Zweite zentrale Erkenntnis[2]
...

### Detailanalyse
[Tiefgehende Analyse der wichtigsten Aspekte]

### Evidenzbewertung
- **Stark belegt:** ...
- **Moderat belegt:** ...
- **Schwach/Spekulativ:** ...

### Offene Fragen
- Frage 1
- Frage 2

### Bereichs-Fazit
[2-3 Sätze die diesen Bereich zusammenfassen]

SPRACHE: Antworte in der Sprache der User-Anfrage!
CITATIONS: Behalte alle [N] Referenzen bei!"""


def build_bereichs_synthesis_prompt(
    user_query: str,
    bereich_titel: str,
    bereich_dossiers: list[dict],
) -> tuple[str, str]:
    """
    Baut den Prompt für die Synthese EINES Bereichs.

    Args:
        user_query: Originale User-Frage
        bereich_titel: Titel des Bereichs
        bereich_dossiers: Liste von {point, dossier, sources}

    Returns:
        (system_prompt, user_prompt)
    """

    # Dossiers formatieren
    dossiers_text = ""
    for i, d in enumerate(bereich_dossiers, 1):
        dossiers_text += f"\n{'='*60}\n"
        dossiers_text += f"DOSSIER {i}: {d['point']}\n"
        dossiers_text += f"{'='*60}\n"
        dossiers_text += d['dossier']
        dossiers_text += f"\n\nQuellen: {len(d.get('sources', []))} URLs\n"

    user_prompt = f"""KONTEXT:
Ursprüngliche Forschungsfrage: "{user_query}"

BEREICH: {bereich_titel}
Anzahl Dossiers: {len(bereich_dossiers)}

{'-'*60}
DOSSIERS DIESES BEREICHS:
{dossiers_text}
{'-'*60}

AUFGABE:
Synthetisiere diese {len(bereich_dossiers)} Dossiers zu EINEM kohärenten Bericht
für den Bereich "{bereich_titel}".

Fokussiere dich ausschließlich auf diesen Bereich. Andere Bereiche werden separat behandelt."""

    logger.debug(f"Bereichs-Synthesis prompt for '{bereich_titel}': {len(user_prompt)} chars")

    return BEREICHS_SYNTHESIS_SYSTEM_PROMPT, user_prompt
