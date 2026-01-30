"""
Meta-Synthesis Prompt v2.0
==========================
Finds CROSS-CONNECTIONS between independently researched area syntheses
and creates scientifically founded conclusions.

v2.0 UPDATES:
- Toulmin argumentation (Claim + Evidence + Warrant + Qualifier + Rebuttal)
- Evidence grading (Level I-VII for each source)
- PRISMA-like methodology transparency
- Active falsification search
- Parser-compatible format
"""

import re
from typing import Optional
import requests
from lutum.core.log_config import get_logger
from lutum.core.api_config import get_api_key

logger = get_logger(__name__)

# Same model as Final Synthesis - needs premium for quality
META_SYNTHESIS_MODEL = "anthropic/claude-sonnet-4.5"
META_SYNTHESIS_TIMEOUT = 600  # 10 minutes

META_SYNTHESIS_SYSTEM_PROMPT = """You are a master of scientific synthesis and argumentation.

═══════════════════════════════════════════════════════════════════
                    FORMAT MARKERS (MANDATORY!)
═══════════════════════════════════════════════════════════════════

These markers enable automatic parsing - use EXACTLY like this:

SECTIONS:       ## EMOJI TITLE
                Example: ## 🔗 CROSS-CONNECTIONS

SUB-SECTIONS:   ### Subtitle
                Example: ### Connection 1: Thermodynamics ↔ Biology

TABLES:         | Col1 | Col2 | Col3 |
                |------|------|------|
                | data | data | data |

LISTS:          1) First point
                2) Second point
                (NOT 1. or - for numbered lists!)

HIGHLIGHT BOX:  > 💡 **Important:** Text here
                > ⚠️ **Warning:** Text here
                > ❓ **Open:** Text here

KEY-VALUE:      - **Key:** Value

CITATION:       Text with source reference[1] and another reference[2][3]

END MARKER:     === END META-SYNTHESIS ===

═══════════════════════════════════════════════════════════════════
                    YOUR TASK
═══════════════════════════════════════════════════════════════════

You receive N INDEPENDENTLY researched area syntheses.

These areas were researched in PARALLEL - without knowledge of each other.
Now you find CONNECTIONS that only become visible when viewing
all areas together.

THIS IS NOT:
- Summarizing what's in the areas
- Repeating the core findings
- Stringing syntheses together

THIS IS:
- NEW insights from the COMBINATION
- CROSS-CONNECTIONS nobody could see
- CONTRADICTIONS and their resolution
- PATTERNS across all areas
- EVIDENCE for conclusions

═══════════════════════════════════════════════════════════════════
                    TOULMIN ARGUMENTATION (MANDATORY!)
═══════════════════════════════════════════════════════════════════

Every important conclusion MUST follow the Toulmin model:

┌─────────────────────────────────────────────────────────────────┐
│ CLAIM:     The assertion you make                               │
│ GROUNDS:   The evidence supporting the claim [with citations]   │
│ WARRANT:   WHY the evidence supports the claim (the logic)      │
│ BACKING:   Additional support for the warrant                   │
│ QUALIFIER: Under what conditions does the claim apply?          │
│ REBUTTAL:  Counter-arguments and why they don't overturn claim  │
└─────────────────────────────────────────────────────────────────┘

EXAMPLE:
- **Claim:** P≠NP is a physical necessity
- **Grounds:** Thermodynamic analyses show exponential entropy costs[1][2]
- **Warrant:** Exponential entropy would violate the 2nd law of thermodynamics
- **Backing:** The 2nd law is the best-confirmed law of nature
- **Qualifier:** In classical computation models (not quantum)
- **Rebuttal:** Quantum algorithms could reduce costs, but measurements remain irreversible[3]

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

In the synthesis it MUST be clear:
- Which evidence level supports which claim?
- Where does Level I-II support? (strong evidence)
- Where only Level VI-VII? (weak evidence, more research needed)

FORMAT: "Claim X is supported by Level II evidence[1][2], while
Claim Y is based only on Level VII expert opinions[3]."

═══════════════════════════════════════════════════════════════════
                    FALSIFICATION REQUIREMENT (NEW!)
═══════════════════════════════════════════════════════════════════

For every important conclusion you MUST actively search:

1. **What would REFUTE this conclusion?**
   - What evidence would falsify the claim?
   - Does this evidence exist in the sources?

2. **What counter-arguments exist?**
   - What do critics say?
   - Why are their arguments (not) convincing?

3. **Where are the LIMITS of the claim?**
   - Under what conditions does it NOT apply?
   - What assumptions are required?

A conclusion without falsification analysis is not science!

═══════════════════════════════════════════════════════════════════
                    CONNECTION TYPES
═══════════════════════════════════════════════════════════════════

Look for these types of cross-connections:

1. **CAUSAL**: A causes B (not just correlation!)
2. **ANALOGOUS**: A works similarly to B (structural similarity)
3. **CONTRARY**: A contradicts B (productive tension)
4. **COMPLEMENTARY**: A and B complement each other (synergy effect)
5. **EMERGENT**: A+B+C together create new phenomenon D

For each connection: What type is it and why?

CRITICAL - LANGUAGE: Always respond in the same language as the user's original query shown below."""

META_SYNTHESIS_USER_PROMPT = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        META-SYNTHESIS TASK                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

ORIGINAL RESEARCH QUESTION:
{user_query}

════════════════════════════════════════════════════════════════════════════════
                         AREA SYNTHESES
════════════════════════════════════════════════════════════════════════════════

{all_syntheses}

════════════════════════════════════════════════════════════════════════════════
                         OUTPUT STRUCTURE
════════════════════════════════════════════════════════════════════════════════

Create the meta-synthesis with these sections:

---

## 🔬 METHODOLOGY TRANSPARENCY

### Source Overview

| Area | Sources | Level I-II | Level III-V | Level VI-VII |
|------|---------|------------|-------------|--------------|
| Area 1 | N | X | Y | Z |
| Area 2 | N | X | Y | Z |
| ... | ... | ... | ... | ... |

### Evidence Distribution

> 💡 **Strengths:** Where do we have strong evidence (Level I-II)?

> ⚠️ **Weaknesses:** Where do we rely only on weak evidence (Level VI-VII)?

### Systematic Gaps

What was NOT found or covered?
1) Gap 1 - why problematic
2) Gap 2 - why problematic

---

## 🔗 CROSS-CONNECTIONS

### Connection 1: [Concise Title]

- **Areas:** Area X ↔ Area Y
- **Type:** [Causal/Analogous/Contrary/Complementary/Emergent]
- **Insight:** What connects them in a non-obvious way?

**Toulmin Analysis:**
- **Claim:** [The connection claim]
- **Grounds:** [Evidence from both areas][Citations]
- **Warrant:** [WHY this evidence proves the connection]
- **Qualifier:** [Under what conditions does this apply?]
- **Rebuttal:** [Counter-arguments and their refutation]

### Connection 2: [Concise Title]
[Same structure]

### Connection N: [Concise Title]
[At least 3 non-trivial connections!]

---

## ⚠️ CONTRADICTIONS & TENSIONS

### Contradiction 1: [Concise Title]

- **Area X says:** [Position A][Citation]
- **Area Y says:** [Position B][Citation]
- **Evidence Level:** X is based on Level [N], Y on Level [M]

**Resolution Attempt:**
- **Possibility A:** [How could the contradiction be resolved?]
- **Possibility B:** [Alternative explanation]
- **Assessment:** [Which resolution is more likely and why?]

> ❓ **If not resolvable:** What would need to be researched to clarify this contradiction?

---

## 🧩 OVERARCHING PATTERNS

What only becomes visible when viewing ALL areas together?

### Pattern 1: [Concise Title]

- **Description:** [The pattern that spans multiple areas]
- **Observed in:** Area X, Y, Z
- **Evidence Strength:** [How well supported is this pattern?]

> 💡 **Implication:** What does this pattern mean for the research question?

### Pattern 2: [Concise Title]
[Same structure]

---

## 💎 CENTRAL CONCLUSIONS

### Conclusion 1: [Concise Title]

**Full Toulmin Analysis:**

| Element | Content |
|---------|---------|
| **CLAIM** | [The main statement] |
| **GROUNDS** | [Evidence with citations and level indication] |
| **WARRANT** | [The logical bridge: WHY does the evidence prove the claim?] |
| **BACKING** | [Additional support for the warrant] |
| **QUALIFIER** | [Limitations: When/where does this apply?] |
| **REBUTTAL** | [Counter-arguments and their addressing] |

**Falsification Check:**
- **What would refute this claim?** [Specific conditions]
- **Does this counter-evidence exist?** [Yes/No, with justification]
- **Confidence:** [High/Medium/Low] because [justification]

### Conclusion 2: [Concise Title]
[Same structure]

---

## 🎯 SYNTHESIS CONCLUSION

### The Meta-Insight

> 💡 **One sentence summarizing the entire interdisciplinary synthesis:**
[The central takeaway]

### Answer to the Research Question

Based on the synthesis of all areas:

1) [Main answer with evidence level indication]
2) [Secondary insight]
3) [Tertiary insight]

### What We CANNOT Answer

> ⚠️ **Open questions requiring further research:**
1) [Open question 1 - why relevant]
2) [Open question 2 - why relevant]

### Recommendations for Further Research

If the research question should be investigated deeper:
1) [Recommendation 1 - what and why]
2) [Recommendation 2 - what and why]

---

## 📎 SOURCE LIST

Consolidated list with evidence levels:

=== SOURCES ===
[1] URL - Title | Level: [I-VII]
[2] URL - Title | Level: [I-VII]
[3] URL - Title | Level: [I-VII]
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
    Builds the Meta-Synthesis prompt.

    Args:
        user_query: Original research question
        bereichs_synthesen: List of {bereich_titel: str, synthese: str, sources: list}

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    # Format area syntheses
    synthesen_parts = []
    for i, s in enumerate(bereichs_synthesen, 1):
        bereich_titel = s.get('bereich_titel', f'Area {i}')
        synthese_content = s.get('synthese', '')
        sources = s.get('sources', [])

        synthesen_parts.append(f"""
┌──────────────────────────────────────────────────────────────────────────────┐
│ AREA {i}: {bereich_titel}
│ ({len(sources)} sources)
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
    Parses the Meta-Synthesis response.

    Args:
        response: Full LLM Response

    Returns:
        Tuple (meta_synthesis_text, metadata)
        - meta_synthesis_text: The complete text
        - metadata: Dict with extracted elements
    """
    metadata = {
        "querverbindungen": 0,
        "widersprueche": 0,
        "muster": 0,
        "schlussfolgerungen": 0,
        "evidenz_levels": {},
    }

    # Count cross-connections
    verbindungen = re.findall(r'###\s*Connection\s*\d+', response, re.IGNORECASE)
    if not verbindungen:
        verbindungen = re.findall(r'###\s*Verbindung\s*\d+', response)
    metadata["querverbindungen"] = len(verbindungen)

    # Count contradictions/tensions
    widersprueche = re.findall(r'###\s*(?:Contradiction|Widerspruch|Tension|Spannung)\s*\d+', response, re.IGNORECASE)
    metadata["widersprueche"] = len(widersprueche)

    # Count patterns
    muster = re.findall(r'###\s*(?:Pattern|Muster)\s*\d+', response, re.IGNORECASE)
    metadata["muster"] = len(muster)

    # Count conclusions
    schlussfolgerungen = re.findall(r'###\s*(?:Conclusion|Schlussfolgerung)\s*\d+', response, re.IGNORECASE)
    metadata["schlussfolgerungen"] = len(schlussfolgerungen)

    # Extract evidence levels from Sources block
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
    # Test with dummy data
    test_synthesen = [
        {
            "bereich_titel": "Thermodynamics & Statistical Mechanics",
            "synthese": """
## Key Findings

1) NP-complete problems can be mapped to the Ising spin glass model[1][2]
2) The energy landscape shows "topological turbulence"[3]
3) P=NP would violate the Second Law[4]
""",
            "sources": ["arxiv.org/1", "arxiv.org/2", "arxiv.org/3", "arxiv.org/4"]
        },
        {
            "bereich_titel": "Biological Computation",
            "synthese": """
## Key Findings

1) Amoebas solve TSP in linear time through physical parallelism[5]
2) Protein folding is NP-complete but proteins fold quickly[6]
""",
            "sources": ["nature.com/1", "pnas.org/1"]
        },
    ]

    system, user = build_meta_synthesis_prompt(
        "Explain P vs NP from a physical perspective",
        test_synthesen
    )

    print("System Prompt (first 1000 chars):")
    print(system[:1000])
    print("\n" + "=" * 60 + "\n")
    print("User Prompt (first 2000 chars):")
    print(user[:2000])
