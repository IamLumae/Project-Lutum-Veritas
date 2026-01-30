"""
Final Synthesis Prompt
======================
Creates the final overall document from all individual dossiers.

ONCE at the end: Receives all point dossiers and synthesizes them
into an ultra-detailed final document.

MODEL: anthropic/claude-sonnet-4.5
(Premium model for highest quality in Final Synthesis)

FORMAT v2.0:
- Universal markers for parser (## EMOJI TITLE)
- Consolidated citation system [N]
- MANDATORY vs OPTIONAL sections (generic for ANY research)
"""

# Model for Final Synthesis (larger model for all dossiers)
FINAL_SYNTHESIS_MODEL = "anthropic/claude-sonnet-4.5"

# IMPORTANT: High timeout! Final Synthesis can take 15-20 minutes for large documents
FINAL_SYNTHESIS_TIMEOUT = 1200  # 20 minutes in seconds

FINAL_SYNTHESIS_SYSTEM_PROMPT = """You are a master of scientific synthesis and documentation.

═══════════════════════════════════════════════════════════════════
                    FORBIDDEN PHRASES (CRITICAL!)
═══════════════════════════════════════════════════════════════════

DO NOT use these meta-commentary phrases - they waste space and add no value:

❌ "Certainly! Here is..."
❌ "I'll now create/synthesize..."
❌ "Let me compile the findings..."
❌ "The following report presents..."
❌ "Based on the dossiers provided..."
❌ "This synthesis aims to..."
❌ "In conclusion, we have examined..."

INSTEAD: START IMMEDIATELY with # [TITLE]. First character = #

═══════════════════════════════════════════════════════════════════
                    CITATION SYSTEM (MANDATORY!)
═══════════════════════════════════════════════════════════════════

EVERY factual statement MUST be marked with a citation:
- Format: Text with statement[1] and another statement[2]
- Take over citations from the dossiers
- Consolidate into a global source list at the end
- Renumber sequentially: [1], [2], [3]... (continuous throughout the document)

EXAMPLE:
"RAG achieves 95% accuracy on structured benchmarks"[1], while
traditional methods stagnate at around 70%[2]. Newer approaches
combine both techniques for optimal results[3][4].

═══════════════════════════════════════════════════════════════════
                    FORMAT MARKERS (MANDATORY!)
═══════════════════════════════════════════════════════════════════

These markers enable automatic parsing - use EXACTLY like this:

SECTIONS:       ## EMOJI TITLE
                Example: ## 📊 EXECUTIVE SUMMARY

SUB-SECTIONS:   ### Subtitle
                Example: ### Key Takeaways

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
                         WHAT SYNTHESIS MEANS
═══════════════════════════════════════════════════════════════════

Synthesis is NOT:
- Simply copying dossiers together
- Stringing sections together
- Repeating the same information

Synthesis IS:
- Drawing NEW insights from the COMBINATION of information
- Establishing CROSS-CONNECTIONS between topics
- Recognizing PATTERNS not visible in individual dossiers
- Creating a NARRATIVE that connects everything
- Resolving CONTRADICTIONS or making them transparent

═══════════════════════════════════════════════════════════════════
                         HARD RULES (MANDATORY)
═══════════════════════════════════════════════════════════════════

1. **NO REDUNDANCY**: Identical content from dossiers only once, then reference.

2. **NO UNFOUNDED SUPERLATIVES**: Claims only when supported by dossier evidence.

3. **TEXT-ONLY**: Do not invent API metadata. Only what's in the dossiers.

4. **END MARKER MANDATORY**: At the end ALWAYS output "=== END REPORT ===".

5. **CITATIONS MANDATORY**: Every factual statement needs [N] reference.

═══════════════════════════════════════════════════════════════════
                         CATEGORY LOGIC
═══════════════════════════════════════════════════════════════════

MANDATORY sections: Must appear in EVERY report!
OPTIONAL sections: ONLY if truly relevant for this topic!

When uncertain: OMIT is better than padding with filler.

Example - "History of the Roman Empire":
- Action recommendations → OMIT (not actionable)
- Maturity Matrix → OMIT (no tech comparisons)
- Claim Ledger → OMIT (no quantitative claims)

Example - "RAG Optimization for Enterprise":
- Action recommendations → INCLUDE (very actionable)
- Maturity Matrix → INCLUDE (tech comparison makes sense)
- Claim Ledger → INCLUDE (performance claims to verify)

CRITICAL - LANGUAGE: Always respond in the same language as the user's original query shown below."""

FINAL_SYNTHESIS_USER_PROMPT = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                           SYNTHESIS TASK                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

ORIGINAL TASK:
{user_query}

COMPLETED RESEARCH PLAN:
{research_plan}

════════════════════════════════════════════════════════════════════════════════
                              INDIVIDUAL DOSSIERS
════════════════════════════════════════════════════════════════════════════════

{all_dossiers}

════════════════════════════════════════════════════════════════════════════════
                         OUTPUT STRUCTURE
════════════════════════════════════════════════════════════════════════════════

Create the final document with these sections.
MANDATORY = Always output | OPTIONAL = Only if relevant!

---

# [TITLE]

A concise title describing the entire research.

---

## 📊 EXECUTIVE SUMMARY
(MANDATORY)

### Key Takeaways

The absolute core findings (5-7 points):

1) First key finding with source reference[1]
2) Second key finding[2]
3) Third key finding[3][4]
4) ...

> 💡 **The central insight:** One sentence that summarizes everything.

### Who is this relevant for?

- **Target audience 1:** Why relevant
- **Target audience 2:** Why relevant
- **Target audience 3:** Why relevant

---

## 🔬 METHODOLOGY
(MANDATORY)

### Source Types

| Type | Count | Examples |
|------|-------|----------|
| GitHub Repos | X | repo1, repo2 |
| Papers/ArXiv | X | paper1, paper2 |
| Community (Reddit/HN) | X | thread1, thread2 |
| Documentation | X | docs1, docs2 |

### Filters & Constraints

- **Time period:** e.g. 2023-2025
- **Platforms:** e.g. GitHub, ArXiv, Reddit
- **Languages:** e.g. English, German
- **Criteria:** e.g. >100 stars, peer-reviewed

### Systematic Gaps

> ⚠️ **These areas were NOT covered:**
- Gap 1 (why)
- Gap 2 (why)
- Gap 3 (why)

---

## 📚 TOPIC CHAPTERS
(MANDATORY)

Structure by TOPICS, not by dossiers!
As many chapters as thematically sensible.

### Chapter 1: [Topic Area]

**Key Findings:**
1) Finding with citation[5]
2) Finding with citation[6]
3) ...

**Details:**
- **Aspect 1:** Description[7]
- **Aspect 2:** Description[8]

**Trade-offs:**
- **Pro:** ...
- **Contra:** ...

> 💡 **Takeaway:** Summary of this chapter in one sentence.

### Chapter 2: [Topic Area]

[Same structure as Chapter 1]

### Chapter N: [Topic Area]

[As many chapters as needed]

---

## 🔗 SYNTHESIS
(MANDATORY)

### Cross-Connections

How are the topics connected?

- **Connection 1:** Topic A and Topic B are connected because...[9]
- **Connection 2:** ...[10]

### Contradictions & Tensions

Where do sources contradict each other?

1) **Contradiction:** Source A says X[11], Source B says Y[12]
   - **Resolution:** ...

2) **Tension:** ...

### Overarching Patterns

> 💡 **What only becomes visible in the overall view:**
- Pattern 1
- Pattern 2
- Pattern 3

### New Insights

What emerges only from combining the dossiers?

1) New insight 1
2) New insight 2

---

## ⚖️ CRITICAL ASSESSMENT
(MANDATORY)

### What do we know for certain?

Well-supported findings with strong evidence:

1) Certain finding 1[13][14]
2) Certain finding 2[15]
3) ...

### What remains uncertain?

Open questions, thin evidence, contradictory sources:

1) Uncertain question 1
2) Uncertain question 2
3) ...

### Limitations of this Research

> ⚠️ **Explicit limitations:**
- Limitation 1 (e.g. English sources only)
- Limitation 2 (e.g. no access to paywalled papers)
- Limitation 3 (e.g. time period limited)

---

## 🎯 ACTION RECOMMENDATIONS
(OPTIONAL - ONLY if actionable recommendations make sense!)

### Immediately actionable (Quick Wins)

| Action | Effort | Expected Outcome |
|--------|--------|------------------|
| Action 1 | Low | Result 1 |
| Action 2 | Low | Result 2 |

### Medium-term (2-6 weeks)

1) Recommendation 1
2) Recommendation 2

### Strategic (Long-term)

1) Strategic recommendation 1
2) Strategic recommendation 2

---

## 📊 MATURITY MATRIX
(OPTIONAL - ONLY for tech comparisons or product evaluations!)

| Tech/Approach | Maturity | Setup | Operations | Benefit | Recommendation |
|---------------|----------|-------|------------|---------|----------------|
| Tech 1 | Production | Low | Low | High | Quick Win |
| Tech 2 | Beta | Medium | Medium | Medium-High | Test |
| Tech 3 | Research | High | High | Varies | Monitor |

---

## 📋 TOP SOURCES
(OPTIONAL - ONLY if particularly valuable sources should be highlighted!)

The most important sources from the research:

| # | Source | Type | Why valuable |
|---|--------|------|--------------|
| [1] | Name | Repo/Paper/Thread | Short description |
| [2] | Name | ... | ... |

---

## 📎 SOURCE LIST
(MANDATORY)

Consolidated list of all cited sources:

=== SOURCES ===
[1] URL_1 - Title/Description
[2] URL_2 - Title/Description
[3] URL_3 - Title/Description
[4] URL_4 - Title/Description
[5] URL_5 - Title/Description
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
    Builds the Final Synthesis prompt.

    Args:
        user_query: Original task
        research_plan: List of research points
        all_dossiers: List of {point: str, dossier: str, sources: list, citations: dict}

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    # Format research plan
    plan_lines = []
    for i, point in enumerate(research_plan, 1):
        plan_lines.append(f"{i}. {point}")
    plan_text = "\n".join(plan_lines)

    # Format dossiers
    dossier_parts = []
    for i, d in enumerate(all_dossiers, 1):
        point_title = d.get('point', f'Point {i}')
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
    Parses the Final Synthesis response and extracts citations.

    Args:
        response: Full LLM Response

    Returns:
        Tuple (report_text, citations)
        - report_text: The complete report
        - citations: Dict {1: "url - title", 2: "url - title", ...}
    """
    import re

    report_text = response
    citations = {}

    # Extract Sources block
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
