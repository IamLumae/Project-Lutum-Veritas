# Lutum Veritas - Deep Research Engine
# Copyright (C) 2026 Martin Gehrken
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Academic Conclusion Prompt - THE MAGIC FINAL CALL
=================================================
This is where the magic happens. This is where hundreds of sources and
tens of thousands of characters of knowledge meet: "NOW find the solution."

This call receives:
1. The original user question (EXACT)
2. All area syntheses (already compressed, focused)

Its task:
- Find cross-connections between areas
- Identify contradictions
- Recognize overarching patterns
- NEW insights only visible through combination
- The ANSWER to the original question
"""

import logging

logger = logging.getLogger(__name__)

# The BEST model for the final call
ACADEMIC_CONCLUSION_MODEL = "qwen/qwen3-vl-235b-a22b-instruct"
ACADEMIC_CONCLUSION_TIMEOUT = 300  # 5 minutes - this is the most important call


ACADEMIC_CONCLUSION_SYSTEM_PROMPT = """You are a brilliant interdisciplinary researcher.

You receive:
1. A complex research question
2. Multiple INDEPENDENTLY researched area syntheses

These areas were INTENTIONALLY researched in isolation from each other.
Now is YOUR moment: You see the complete picture FIRST.

═══════════════════════════════════════════════════════════════════
                        YOUR MISSION
═══════════════════════════════════════════════════════════════════

1. FIND CROSS-CONNECTIONS
   - Which concepts from Area A explain phenomena in Area B?
   - Where are there unexpected parallels?
   - What bridges exist between disciplines?

2. IDENTIFY CONTRADICTIONS
   - Where do the areas contradict each other?
   - Are these contradictions resolvable or fundamental?
   - What do they mean for the overall question?

3. RECOGNIZE OVERARCHING PATTERNS
   - Which patterns appear in multiple areas?
   - What does this tell us about the underlying problem?

4. SYNTHESIZE NEW INSIGHTS
   - What only becomes visible NOW that all areas come together?
   - What conclusions can NOBODY draw who only knows one area?

5. FORMULATE THE ANSWER
   - Answer the original question as well as the evidence allows
   - Be honest about uncertainties
   - Name what we KNOW vs. what we ASSUME

═══════════════════════════════════════════════════════════════════
                        OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════

## 🔗 CROSS-CONNECTIONS

### Connection 1: [Title]
[Description of how Area X and Y relate]

### Connection 2: [Title]
...

## ⚡ CONTRADICTIONS & TENSIONS

### Contradiction 1: [Title]
- **Area A says:** ...
- **Area B says:** ...
- **Resolution/Meaning:** ...

## 🔄 OVERARCHING PATTERNS

1) Pattern appearing in multiple areas
2) ...

## 💡 NEW INSIGHTS

> These insights are ONLY possible through combining the areas:

1) First meta-insight
2) Second meta-insight
...

## 🎯 ANSWER TO THE RESEARCH QUESTION

### What we know (high confidence):
- ...

### What we assume (moderate confidence):
- ...

### What remains open:
- ...

### Conclusion
[The best answer the evidence allows - honest, nuanced, but clear]

═══════════════════════════════════════════════════════════════════

THINK DEEP: This is the most important part of the entire research.
BE BOLD: Draw conclusions others wouldn't see.

CRITICAL - LANGUAGE: Always respond in the same language as the user's original query shown below."""


def build_academic_conclusion_prompt(
    user_query: str,
    bereichs_synthesen: list[dict],
) -> tuple[str, str]:
    """
    Builds the FINAL prompt - the magic call.

    Args:
        user_query: The ORIGINAL user question (exact!)
        bereichs_synthesen: List of {bereich_titel, synthese, sources_count}

    Returns:
        (system_prompt, user_prompt)
    """

    # Format all syntheses
    synthesen_text = ""
    total_sources = 0

    for i, s in enumerate(bereichs_synthesen, 1):
        total_sources += s.get('sources_count', 0)
        synthesen_text += f"\n{'═'*70}\n"
        synthesen_text += f"AREA {i}: {s['bereich_titel']}\n"
        synthesen_text += f"Sources in this area: {s.get('sources_count', 'N/A')}\n"
        synthesen_text += f"{'═'*70}\n\n"
        synthesen_text += s['synthese']
        synthesen_text += "\n"

    user_prompt = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    ORIGINAL RESEARCH QUESTION                         ║
╚══════════════════════════════════════════════════════════════════════╝

"{user_query}"

╔══════════════════════════════════════════════════════════════════════╗
║                        RESEARCH OVERVIEW                              ║
╚══════════════════════════════════════════════════════════════════════╝

Number of independent areas: {len(bereichs_synthesen)}
Total number of analyzed sources: {total_sources}

The following areas were researched INDEPENDENTLY of each other.
Each area had its own search strategies, own sources, own analysis.
You see them together for the FIRST TIME now.

╔══════════════════════════════════════════════════════════════════════╗
║                      AREA SYNTHESES                                   ║
╚══════════════════════════════════════════════════════════════════════╝
{synthesen_text}

╔══════════════════════════════════════════════════════════════════════╗
║                         YOUR TASK                                     ║
╚══════════════════════════════════════════════════════════════════════╝

You now have access to {len(bereichs_synthesen)} independent research perspectives
based on {total_sources} analyzed sources.

FIND:
1. Cross-connections between areas
2. Contradictions and tensions
3. Overarching patterns
4. New insights that are ONLY visible through combination
5. The best possible ANSWER to the research question

This is your moment. Think deep. Be brilliant."""

    logger.info(f"Academic Conclusion prompt: {len(user_prompt)} chars, {len(bereichs_synthesen)} areas, {total_sources} sources")

    return ACADEMIC_CONCLUSION_SYSTEM_PROMPT, user_prompt
