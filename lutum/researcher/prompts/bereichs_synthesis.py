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

═══════════════════════════════════════════════════════════════════
                    FORBIDDEN PHRASES (CRITICAL!)
═══════════════════════════════════════════════════════════════════

DO NOT use these meta-commentary phrases - they waste space and add no value:

❌ "Certainly! Here is..."
❌ "I'll now create/analyze/synthesize..."
❌ "Let me examine/review..."
❌ "The following report/analysis..."
❌ "Based on my analysis..."
❌ "In this synthesis, I will..."
❌ "This section aims to..."

INSTEAD: START IMMEDIATELY with ## [Area Title]. First character = #

═══════════════════════════════════════════════════════════════════
                         YOUR TASK
═══════════════════════════════════════════════════════════════════

Synthesize the dossiers of ONE research area into a coherent, focused report.
This area was researched INDEPENDENTLY from other areas.

REQUIREMENTS:
- Focus ONLY on this area
- Extract the CORE FINDINGS
- Identify patterns WITHIN this area
- Evaluate evidence quality (what is well-supported vs speculative?)
- Name open questions specific to THIS area

DEPTH OVER BREVITY:
- Be COMPREHENSIVE, not compressed
- We want detailed analysis, not executive summaries
- More explanation is better than less

═══════════════════════════════════════════════════════════════════
                         OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════

## [Area Title]

### Key Findings
1) First central finding[1]
2) Second central finding[2]
3) Third central finding[3]
...
(10-15 findings MINIMUM for comprehensive coverage!)

### Deep Analysis
[In-depth analysis of the most important aspects. NOT a summary - actual analysis!]
- What mechanisms/dynamics/relationships are at play?
- How do the findings connect to each other?
- What does this mean for the broader research question?

### Evidence Quality
- **Strong evidence (multiple sources agree):** ...
- **Moderate evidence (some support):** ...
- **Weak/Speculative (limited data):** ...

### Gaps & Open Questions
- Question 1 - why it matters
- Question 2 - why it matters
- Question 3 - what would answer it

### Area Summary
[Comprehensive summary of this area's contribution to the research question.
Be thorough - include key mechanisms, evidence, and implications.
NO LENGTH LIMIT - as long as needed to be complete.]

═══════════════════════════════════════════════════════════════════
                         HARD RULES
═══════════════════════════════════════════════════════════════════

1. CITATIONS: Keep ALL [N] references from the dossiers!
2. BE COMPREHENSIVE: Explain fully - don't compress or summarize excessively
3. DEPTH: Analysis section must be substantial (not just restating findings)
4. START IMMEDIATELY: First output character must be #
5. NO LENGTH LIMITS: Write as much as needed to be thorough

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
