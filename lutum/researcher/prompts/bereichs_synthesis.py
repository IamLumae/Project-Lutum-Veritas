# Lutum Veritas - Deep Research Engine
# Copyright (C) 2026 Martin Gehrken
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Area Synthesis Prompt
=====================
Each area gets its OWN LLM call.
Focused, compressed, no distraction from other areas.
"""

import logging

logger = logging.getLogger(__name__)

# Model for Area Synthesis (FINAL = qwen 235b like Conclusion)
BEREICHS_SYNTHESIS_MODEL = "qwen/qwen3-vl-235b-a22b-instruct"
BEREICHS_SYNTHESIS_TIMEOUT = 180  # 3 minutes per area (large model)


BEREICHS_SYNTHESIS_SYSTEM_PROMPT = """You are an academic research assistant.

Your task: Synthesize the dossiers of ONE research area into a coherent,
focused report. This area was researched INDEPENDENTLY from other areas.

IMPORTANT:
- Focus ONLY on this area
- Extract the CORE FINDINGS
- Identify patterns WITHIN this area
- Evaluate evidence quality
- Name open questions of THIS area

FORMAT:
## [Area Title]

### Core Findings
1) First central finding[1]
2) Second central finding[2]
...

### Detailed Analysis
[In-depth analysis of the most important aspects]

### Evidence Evaluation
- **Strongly supported:** ...
- **Moderately supported:** ...
- **Weak/Speculative:** ...

### Open Questions
- Question 1
- Question 2

### Area Conclusion
[2-3 sentences summarizing this area]

CITATIONS: Keep all [N] references!

CRITICAL - LANGUAGE: Always respond in the same language as the user's original query shown below."""


def build_bereichs_synthesis_prompt(
    user_query: str,
    bereich_titel: str,
    bereich_dossiers: list[dict],
) -> tuple[str, str]:
    """
    Builds the prompt for synthesizing ONE area.

    Args:
        user_query: Original user question
        bereich_titel: Title of the area
        bereich_dossiers: List of {point, dossier, sources}

    Returns:
        (system_prompt, user_prompt)
    """

    # Format dossiers
    dossiers_text = ""
    for i, d in enumerate(bereich_dossiers, 1):
        dossiers_text += f"\n{'='*60}\n"
        dossiers_text += f"DOSSIER {i}: {d['point']}\n"
        dossiers_text += f"{'='*60}\n"
        dossiers_text += d['dossier']
        dossiers_text += f"\n\nSources: {len(d.get('sources', []))} URLs\n"

    user_prompt = f"""CONTEXT:
Original research question: "{user_query}"

AREA: {bereich_titel}
Number of dossiers: {len(bereich_dossiers)}

{'-'*60}
DOSSIERS OF THIS AREA:
{dossiers_text}
{'-'*60}

TASK:
Synthesize these {len(bereich_dossiers)} dossiers into ONE coherent report
for the area "{bereich_titel}".

Focus exclusively on this area. Other areas are handled separately."""

    logger.debug(f"Bereichs-Synthesis prompt for '{bereich_titel}': {len(user_prompt)} chars")

    return BEREICHS_SYNTHESIS_SYSTEM_PROMPT, user_prompt
