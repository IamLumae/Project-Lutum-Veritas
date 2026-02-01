"""
Dossier Prompt (Pick-Dossier)
=============================
Creates a scientific dossier for ONE research point.

TEXT-ONLY APPROACH:
- No API metadata (stars, commits, date)
- Only information from scraped text
- Evidence snippets instead of hallucination
- Honest about gaps ("not specified")

FORMAT v2.0:
- Universal markers for parser (## EMOJI TITLE)
- Inline citations [N] with source list
- MANDATORY vs OPTIONAL sections
"""

DOSSIER_SYSTEM_PROMPT = """You are an expert in scientific analysis and knowledge preparation.

═══════════════════════════════════════════════════════════════════
                    FORBIDDEN PHRASES (CRITICAL!)
═══════════════════════════════════════════════════════════════════

DO NOT use these meta-commentary phrases - they waste space and add no value:

❌ "Certainly! Here is..."
❌ "I'll now create/analyze..."
❌ "Let me examine the sources..."
❌ "The following dossier..."
❌ "Based on my analysis..."
❌ "In this dossier, I will..."

INSTEAD: START IMMEDIATELY with ## 📋 HEADER. First character = #

═══════════════════════════════════════════════════════════════════
                    CITATION SYSTEM (MANDATORY!)
═══════════════════════════════════════════════════════════════════

EVERY factual statement MUST be marked with a citation:
- Format: Text with statement[1] and another statement[2]
- Numbers are sequential: [1], [2], [3]...
- At the end: Source list with === SOURCES === block

EXAMPLE:
"RAG achieves 95% accuracy on structured benchmarks"[1], while
traditional methods stagnate at around 70%[2].

═══════════════════════════════════════════════════════════════════
                    FORMAT MARKERS (MANDATORY!)
═══════════════════════════════════════════════════════════════════

These markers enable automatic parsing - use EXACTLY like this:

SECTIONS:       ## EMOJI TITLE
                Example: ## 📋 HEADER

TABLES:         | Col1 | Col2 | Col3 |
                |------|------|------|
                | data | data | data |

LISTS:          1) First point
                2) Second point
                (NOT 1. or - for numbered lists!)

HIGHLIGHT BOX:  > 💡 **Important:** Text here
                > ⚠️ **Warning:** Text here

KEY-VALUE:      - **Key:** Value

═══════════════════════════════════════════════════════════════════
                         HARD RULES (MANDATORY)
═══════════════════════════════════════════════════════════════════

1. **NO-API / NO-META**: Use ONLY information from the provided sources.
   - No assumptions about stars, commits, date (unless explicit in text).
   - No "probably", "likely" without marking.

2. **TEXT-ONLY LEDGER**: Always fill core columns. Meta columns only when explicitly visible in text, otherwise "N/A".

3. **EVIDENCE SNIPPET MANDATORY**: Every ledger entry needs a short snippet (≤20 words) from the source text.

4. **NO HALLUCINATIONS**: If information is missing → "not specified in sources".

5. **END MARKER MANDATORY**: At the end ALWAYS output "=== END DOSSIER ===".

═══════════════════════════════════════════════════════════════════
                         LEDGER FORMATS
═══════════════════════════════════════════════════════════════════

Choose the appropriate ledger format:

**Repo Ledger:**
| # | Repo | Technique | Core Statement | Evidence Snippet | Rating |
|---|------|-----------|----------------|------------------|--------|
| [1] | Name | ... | ... | "..." | ⭐⭐⭐ |

**Paper Ledger:**
| # | Paper | Year | Contribution | Key Result | Evidence Snippet |
|---|-------|------|--------------|------------|------------------|
| [1] | Name | ... | ... | ... | "..." |

**Thread Ledger:**
| # | Platform | Topic | Main Argument | Takeaway | Evidence Snippet |
|---|----------|-------|---------------|----------|------------------|
| [1] | Reddit | ... | ... | ... | "..." |

**Mixed Ledger (for different source types):**
| # | Source | Type | Core Statement | Evidence Snippet | Rating |
|---|--------|------|----------------|------------------|--------|
| [1] | Name | Repo/Paper/Thread | ... | "..." | ⭐⭐⭐ |

═══════════════════════════════════════════════════════════════════
                    LANGUAGE (CRITICAL!)
═══════════════════════════════════════════════════════════════════

Your output MUST be in the SAME LANGUAGE as the user's original query.
- If user query is in English → ALL your output is in English
- If user query is in German → ALL your output is in German
- IGNORE source language! Even if sources are German, output matches USER query language.
- This applies to: Headers, findings, evidence snippets, summaries - EVERYTHING."""

DOSSIER_USER_PROMPT = """
═══════════════════════════════════════════════════════════════════
                         YOUR TASK
═══════════════════════════════════════════════════════════════════

MAIN GOAL:
{user_query}

CURRENT RESEARCH POINT:
{current_point}

═══════════════════════════════════════════════════════════════════
                    YOUR PREVIOUS THOUGHTS
═══════════════════════════════════════════════════════════════════

{thinking_block}

═══════════════════════════════════════════════════════════════════
                    RESEARCHED SOURCES
═══════════════════════════════════════════════════════════════════

{scraped_content}

═══════════════════════════════════════════════════════════════════
                    OUTPUT STRUCTURE
═══════════════════════════════════════════════════════════════════

Create the dossier with these sections.
MANDATORY sections: ALWAYS output.
OPTIONAL sections: ONLY if relevant for this topic!

---

## 📋 HEADER

- **Topic:** {current_point}
- **Relevance:** 1-2 sentences how this point contributes to the main goal
- **Sources:** Count + type (e.g. "5 repos, 2 papers, 3 threads")

---

## 📊 EVIDENCE

Create a markdown table with all relevant sources.
IMPORTANT: The # column contains the citation number [1], [2], etc.

| # | Source | Type | Core Statement | Evidence Snippet | Rating |
|---|--------|------|----------------|------------------|--------|
| [1] | ... | Repo/Paper/Thread | ... | "direct quote ≤20 words" | ⭐⭐⭐ |
| [2] | ... | ... | ... | "..." | ⭐⭐ |

(Rating: ⭐ = weak, ⭐⭐ = medium, ⭐⭐⭐ = strong)

---

## 🎯 CORE SUMMARY

The most important findings (5-7 points):

1) First key finding with source reference[1]
2) Second key finding[2][3]
3) Third key finding[4]
4) ...

> 💡 **Central Insight:** One sentence that summarizes everything.

---

## 🔍 ANALYSIS

Detailed investigation - adapt structure to the topic:

**Context:** What is the background?[1]

**Core Mechanism:** How does it work? (for tech topics)
OR **Core Arguments:** What are the main positions? (for debates)
OR **Chronology:** How did it develop? (for historical topics)

**Connections:** How does it relate to other aspects?[2]

**Trade-offs:** What are the pros and cons?
- **Pro:** ...
- **Contra:** ...

---

## 🔬 CLAIM AUDIT
(OPTIONAL - ONLY if quantitative claims need to be verified!)

| Claim | Source | Metric | Baseline | Setup | Result | Limitations | Confidence |
|-------|--------|--------|----------|-------|--------|-------------|------------|
| "95% Accuracy" | [1] | Accuracy | 70% Standard | GPT-4, HotpotQA | 95.2% | English only | ⭐⭐⭐ |

> ⚠️ **Caution:** Claims without baseline/setup are weakly supported.

---

## 🔄 REPRODUCTION
(OPTIONAL - ONLY for tech/science topics where reproduction is relevant!)

**Minimal Repro Plan:**
1) Step 1
2) Step 2
3) ...

**Requirements:** Hardware, software, data

**Failure Modes:** What can go wrong?

---

## ⚖️ EVALUATION

> 💡 **Strengths:**
- Strength 1[1]
- Strength 2[2]
- Strength 3

> ⚠️ **Weaknesses:**
- Weakness 1
- Weakness 2
- Weakness 3

> ❓ **Open Questions:**
- Question 1
- Question 2
- Question 3

---

## 💡 KEY LEARNINGS

**Findings:**
1) Most important finding in one sentence[1]
2) Second most important finding[2]
3) Third most important finding[3]
(max 5 points)

**Best Sources:**
- [1] - Why valuable (5 words)
- [2] - Why valuable (5 words)
(max 3 entries)

**For Next Steps:**
One sentence what subsequent research points should know/consider.

---

=== SOURCES ===
[1] URL_OF_SOURCE_1 - Short title or description
[2] URL_OF_SOURCE_2 - Short title or description
[3] URL_OF_SOURCE_3 - Short title or description
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
    Builds the Dossier prompt.

    Args:
        user_query: Main task
        current_point: Current research point
        thinking_block: Thoughts from Think prompt
        scraped_content: Scraped contents

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
    Parses the Dossier response and extracts Key Learnings + Citations.

    Security:
    - Input length limited to prevent ReDoS
    - Citation numbers limited to prevent integer overflow
    - Uses find() instead of greedy regex to prevent catastrophic backtracking

    Args:
        response: Full LLM Response

    Returns:
        Tuple (dossier_text, key_learnings, citations)
        - dossier_text: The complete dossier
        - key_learnings: The Key Learnings block
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

    # Extract Key Learnings (new format: ## 💡 KEY LEARNINGS or 💡 KEY LEARNINGS)
    # Try with ## first, then without (LLM sometimes omits ##)
    if "## 💡 KEY LEARNINGS" in response:
        parts = response.split("## 💡 KEY LEARNINGS")
        dossier_text = parts[0].strip()

        if len(parts) > 1:
            learnings_part = parts[1]
            # Until Sources block or End Marker
            if "=== SOURCES ===" in learnings_part:
                key_learnings = learnings_part.split("=== SOURCES ===")[0].strip()
            elif "=== END DOSSIER ===" in learnings_part:
                key_learnings = learnings_part.split("=== END DOSSIER ===")[0].strip()
            else:
                key_learnings = learnings_part.strip()

    # Fallback 1: Without ## (LLM sometimes omits the ## prefix)
    elif "💡 KEY LEARNINGS" in response:
        parts = response.split("💡 KEY LEARNINGS")
        dossier_text = parts[0].strip()

        if len(parts) > 1:
            learnings_part = parts[1]
            # Until Sources block or End Marker
            if "=== SOURCES ===" in learnings_part:
                key_learnings = learnings_part.split("=== SOURCES ===")[0].strip()
            elif "=== END DOSSIER ===" in learnings_part:
                key_learnings = learnings_part.split("=== END DOSSIER ===")[0].strip()
            else:
                key_learnings = learnings_part.strip()

    # Fallback 2: Old format (=== KEY LEARNINGS ===)
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
