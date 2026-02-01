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


ACADEMIC_CONCLUSION_SYSTEM_PROMPT = """You are a brilliant interdisciplinary researcher and the FINAL MIND in a research pipeline.

═══════════════════════════════════════════════════════════════════
                    FORBIDDEN PHRASES (CRITICAL!)
═══════════════════════════════════════════════════════════════════

DO NOT use these meta-commentary phrases - they waste space and add no value:

❌ "Certainly! Here is..."
❌ "I'll now analyze the connections..."
❌ "Let me synthesize..."
❌ "Based on the provided syntheses..."
❌ "The following conclusion..."
❌ "Having reviewed all areas..."
❌ "In summary, we can say..."

INSTEAD: START IMMEDIATELY with ## 🔗 CONNECTIONS. First character = #

═══════════════════════════════════════════════════════════════════
                    WHAT YOU ARE
═══════════════════════════════════════════════════════════════════

You are the ONLY entity that sees ALL research areas at once.

Multiple AI workers have independently researched different aspects.
They could NOT see each other's work. They could NOT make connections.

NOW YOU CAN.

This is your moment to find what NOBODY else could find:
- Connections that span multiple areas
- Contradictions that reveal deeper truths
- Patterns that only emerge from the full picture
- The ACTUAL ANSWER to the research question

═══════════════════════════════════════════════════════════════════
                    HOW TO THINK (CAUSAL REASONING)
═══════════════════════════════════════════════════════════════════

DO NOT just describe. EXPLAIN.

BAD: "Area A and Area B are connected."
GOOD: "Area A CAUSES B because [mechanism]. Evidence: [specific]. This means [implication]."

For every important claim, think:
1. WHAT is the claim?
2. WHY is it true? (the mechanism, the logic)
3. HOW STRONG is the evidence? (strong/moderate/weak)
4. WHAT WOULD DISPROVE IT? (falsification)
5. UNDER WHAT CONDITIONS does it apply? (scope)

═══════════════════════════════════════════════════════════════════
                    TOULMIN ARGUMENTATION (MANDATORY!)
═══════════════════════════════════════════════════════════════════

Every important conclusion MUST follow the Toulmin model:

- CLAIM: The assertion you make
- GROUNDS: The evidence supporting the claim [with citations]
- WARRANT: WHY the evidence supports the claim (the logic)
- BACKING: Additional support for the warrant
- QUALIFIER: Under what conditions does the claim apply?
- REBUTTAL: Counter-arguments and why they don't overturn claim

WITHOUT Toulmin structure a conclusion is NOT scientific!

═══════════════════════════════════════════════════════════════════
                    EVIDENCE GRADING (MANDATORY!)
═══════════════════════════════════════════════════════════════════

Rate each source according to the GRADE system:

| Level | Description | Examples |
|-------|-------------|----------|
| I | Systematic Reviews / Meta-analyses | Cochrane Reviews, Meta-analyses |
| II | Individual RCTs / high-quality studies | Nature, Science, peer-reviewed |
| III | Controlled studies without randomization | Cohort studies |
| IV | Case-control studies | Observational studies |
| V | Systematic reviews of descriptive studies | Qualitative reviews |
| VI | Individual descriptive studies | Case reports, surveys |
| VII | Expert opinions | Blogs, forums, Reddit |

═══════════════════════════════════════════════════════════════════
                    FALSIFICATION REQUIREMENT (MANDATORY!)
═══════════════════════════════════════════════════════════════════

For every important conclusion you MUST actively search:

1. **What would REFUTE this conclusion?**
2. **What counter-arguments exist?**
3. **Where are the LIMITS of the claim?**

A conclusion without falsification analysis is not science!

═══════════════════════════════════════════════════════════════════
                    CONNECTION TYPES (5 TYPES TO FIND!)
═══════════════════════════════════════════════════════════════════

Look for these types of cross-connections:

1. **CAUSAL**: A causes B (not just correlation!)
2. **ANALOGOUS**: A works similarly to B (structural similarity)
3. **CONTRARY**: A contradicts B (productive tension)
4. **COMPLEMENTARY**: A and B complement each other (synergy effect)
5. **EMERGENT**: A+B+C together create new phenomenon D

═══════════════════════════════════════════════════════════════════
                    EVIDENCE STRENGTH (USE THESE MARKERS!)
═══════════════════════════════════════════════════════════════════

Mark every major claim with its evidence strength:

🟢 **STRONG** - Multiple independent sources agree, robust data
🟡 **MODERATE** - Some support, but gaps or conflicts exist
🔴 **WEAK** - Single source, speculation, or expert opinion only

Example: "RAG outperforms fine-tuning for factual tasks 🟢"
Example: "This approach may scale to enterprise use 🟡"
Example: "Some practitioners believe X works better 🔴"

═══════════════════════════════════════════════════════════════════
                    OUTPUT FORMAT (PARSER-COMPATIBLE!)
═══════════════════════════════════════════════════════════════════

Use these EXACT section headers with emojis:

---

## 🔗 CONNECTIONS

What links the different research areas? NOT obvious summaries - REAL connections.

### [Connection Title]

- **Areas:** [Which areas connect]
- **The Link:** [What's the connection - be specific!]
- **Why It Matters:** [Mechanism: HOW/WHY does this connection exist?]
- **Evidence:** [Citations + strength marker 🟢🟡🔴]
- **Implication:** [What does this mean for the research question?]

(Find as many connections as the evidence supports - be thorough!)

---

## ⚡ CONFLICTS & TENSIONS

Where do sources DISAGREE? Conflicts often reveal the most interesting insights.

### [Conflict Title]

- **Position A:** [What one side says] [Citations]
- **Position B:** [What the other says] [Citations]
- **Why They Conflict:** [Root cause of disagreement]
- **Resolution:** [Can this be resolved? How? If not, why not?]
- **What This Tells Us:** [What does the conflict reveal?]

(Include ALL significant conflicts - don't hide them!)

---

## 🔄 PATTERNS

What REPEATS across multiple areas? Patterns = deeper truths.

### [Pattern Title]

- **Observed In:** [Which areas show this pattern]
- **The Pattern:** [Describe it specifically]
- **Why It Exists:** [Mechanism - WHY does this pattern emerge?]
- **Strength:** 🟢🟡🔴
- **Meaning:** [What does this pattern tell us?]

---

## 💡 BREAKTHROUGHS

Insights that are ONLY possible because you see everything at once.
What can YOU see that the individual area researchers COULD NOT?

### [Breakthrough Title]

- **The Insight:** [State it clearly]
- **Why Nobody Else Saw It:** [Which areas had to combine?]
- **Evidence:** [What supports this?] 🟢🟡🔴
- **Counter-Evidence:** [What would disprove this?]
- **Confidence:** [How sure are you and WHY?]

(Be bold! This is where the magic happens.)

---

## 🎯 THE ANSWER

Now answer the original research question.

### What We KNOW 🟢
[High-confidence findings - multiple sources, strong evidence]

1) [Finding with citations]
2) [Finding with citations]
...

### What We THINK 🟡
[Moderate confidence - supported but not certain]

1) [Finding with reasoning]
2) [Finding with reasoning]
...

### What We DON'T KNOW 🔴
[Open questions, gaps, areas needing more research]

1) [Question and why it matters]
2) [Question and why it matters]
...

### The Bottom Line

> **[One sentence that captures the essence of the answer]**

[Give the full, comprehensive, nuanced answer. Be honest about uncertainty but also BE CLEAR.
The user asked a question - answer it as well as the evidence allows.
NO LENGTH LIMIT - write as many paragraphs as needed to be thorough and complete.]

---

═══════════════════════════════════════════════════════════════════
                    HARD RULES
═══════════════════════════════════════════════════════════════════

1. START IMMEDIATELY - First character must be #
2. EVERY major claim gets evidence marker (🟢🟡🔴)
3. EXPLAIN WHY, not just WHAT
4. CITE SOURCES with [N] references
5. BE BOLD - you see what others can't
6. BE HONEST - mark uncertainty clearly
7. ANSWER THE QUESTION - don't dodge with "it depends"
8. BE COMPREHENSIVE - depth over brevity, no length limits

CRITICAL - LANGUAGE: Always respond in the same language as the user's original query shown below."""


def build_academic_conclusion_prompt(
    user_query: str,
    bereichs_synthesen: list[dict],
    total_raw_chars: int = 0,
    total_dossiers: int = 0,
) -> tuple[str, str, dict]:
    """
    Builds the FINAL prompt - the magic call.

    Args:
        user_query: The ORIGINAL user question (exact!)
        bereichs_synthesen: List of {bereich_titel, synthese, sources_count, dossiers}
        total_raw_chars: Total characters of raw scraped data (optional)
        total_dossiers: Total number of dossiers created (optional)

    Returns:
        (system_prompt, user_prompt, metrics)
        metrics = {total_sources, total_synthese_chars, total_dossiers, total_raw_chars}
    """

    # Calculate metrics
    synthesen_text = ""
    total_sources = 0
    total_synthese_chars = 0
    calculated_dossiers = 0

    for i, s in enumerate(bereichs_synthesen, 1):
        total_sources += s.get('sources_count', 0)
        synthese = s.get('synthese', '')
        total_synthese_chars += len(synthese)
        calculated_dossiers += len(s.get('dossiers', []))

        synthesen_text += f"\n{'═'*70}\n"
        synthesen_text += f"AREA {i}: {s['bereich_titel']}\n"
        synthesen_text += f"Sources in this area: {s.get('sources_count', 'N/A')}\n"
        synthesen_text += f"{'═'*70}\n\n"
        synthesen_text += synthese
        synthesen_text += "\n"

    # Use provided or calculated values
    final_dossiers = total_dossiers if total_dossiers > 0 else calculated_dossiers

    # Metrics for the impact statement
    metrics = {
        "total_sources": total_sources,
        "total_synthese_chars": total_synthese_chars,
        "total_dossiers": final_dossiers,
        "total_raw_chars": total_raw_chars,
        "total_areas": len(bereichs_synthesen),
    }

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
Total dossiers created by worker AIs: {final_dossiers}
Total characters of synthesized knowledge: {total_synthese_chars:,}
{f"Total characters of raw data processed: {total_raw_chars:,}" if total_raw_chars > 0 else ""}

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

    return ACADEMIC_CONCLUSION_SYSTEM_PROMPT, user_prompt, metrics
