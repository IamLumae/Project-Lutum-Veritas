"""
Academic Plan Prompt v2.0
=========================
Creates a hierarchical research plan with AUTONOMOUS AREAS
for parallel deep research.

DIFFERENCE TO NORMAL MODE:
- Normal: Flat list (1), (2), (3)... → processed sequentially
- Academic: Areas with sub-points → processed in parallel

Each area is INDEPENDENTLY researchable (no dependencies between areas).
Key learnings flow only WITHIN an area.

v2.0 UPDATES:
- Evidence diversity per area (different source types)
- Explicit perspective assignment
- Parser-compatible format
"""

import re
from typing import Optional
from lutum.core.log_config import get_logger
from lutum.core.api_config import get_work_model
from lutum.core.llm_client import call_chat_completion
from lutum.researcher.context_state import ContextState

logger = get_logger(__name__)


ACADEMIC_PLAN_SYSTEM_PROMPT = """You are a research architect creating multi-disciplinary research plans.

═══════════════════════════════════════════════════════════════════
                    FORMAT MARKERS (MANDATORY!)
═══════════════════════════════════════════════════════════════════

These markers enable automatic parsing - use EXACTLY like this:

AREA HEADER:    === AREA N: [Title] ===
POINTS:         1) Text of the point
                2) Text of the point
END MARKER:     === END PLAN ===

═══════════════════════════════════════════════════════════════════
                    ACADEMIC MODE - WHAT IT IS
═══════════════════════════════════════════════════════════════════

You create a plan with **AUTONOMOUS AREAS** instead of a flat list.

WHY AREAS?
- Each area is researched in PARALLEL (not sequentially)
- This enables multi-disciplinary perspectives on the same problem
- At the end, areas are combined in a META-SYNTHESIS
- Cross-connections are only found AFTER independent research

═══════════════════════════════════════════════════════════════════
                    PERSPECTIVE DIVERSITY (NEW!)
═══════════════════════════════════════════════════════════════════

Each area should represent a DIFFERENT PERSPECTIVE:

POSSIBLE PERSPECTIVES (choose 3-5 fitting ones):
- **Theoretical/Fundamental**: Basics, principles, axioms
- **Empirical/Experimental**: Studies, data, measurements
- **Practical/Applied**: Implementations, use cases, tools
- **Critical/Skeptical**: Counter-arguments, limitations, controversies
- **Historical/Evolutionary**: Development, milestones, trends
- **Interdisciplinary**: Connections to other fields
- **Future/Speculative**: Predictions, open questions, research gaps

EXAMPLE for "Climate Change":
- Area 1: Physical Fundamentals (Theoretical)
- Area 2: Measurement Data and Models (Empirical)
- Area 3: Counter-arguments and Controversies (Critical)
- Area 4: Technological Solutions (Practical)

═══════════════════════════════════════════════════════════════════
                    EVIDENCE DIVERSITY PER AREA (NEW!)
═══════════════════════════════════════════════════════════════════

Each area should target different SOURCE TYPES:

- **Primary sources**: Original studies, papers, patents
- **Secondary sources**: Reviews, meta-analyses, textbooks
- **Gray literature**: Preprints, conference papers, whitepapers
- **Community**: Forums, discussions, expert opinions
- **Practice**: Documentation, tutorials, case studies

Formulate points so that different source types are found!

═══════════════════════════════════════════════════════════════════
                    HARD RULES (MANDATORY!)
═══════════════════════════════════════════════════════════════════

1. **AUTONOMY RULE**: Each area MUST be independently researchable!
   - NO dependencies between areas
   - NO references like "based on Area 1..."
   - Each area stands on its own

2. **BALANCE RULE**:
   - 3-5 areas (optimal: 4)
   - 2-4 points per area
   - Similar depth per area

3. **DIVERSITY RULE**:
   - Different PERSPECTIVES (not just different topics)
   - At least 1 critical/skeptical area if controversial

4. **CONCRETENESS RULE**:
   - Each point begins with verb (Research, Analyze, Compare...)
   - Each point has a measurable goal
   - Each point is googleable

═══════════════════════════════════════════════════════════════════
                    EXAMPLE COMPLETE OUTPUT
═══════════════════════════════════════════════════════════════════

Question: "Is nuclear fusion a realistic energy source?"

=== AREA 1: Physical Fundamentals (Theoretical) ===
1) Research the fundamental fusion reactions (D-T, D-D, p-B11) and their energy yield
2) Analyze the Lawson criterion and requirements for plasma confinement
3) Compare theoretical efficiency limits with fission and renewables

=== AREA 2: Experimental Status (Empirical) ===
1) Document results from ITER, NIF, JET and other large experiments
2) Research the current Q-factor record and development since 2020
3) Analyze peer-reviewed papers on plasma instabilities and their solutions

=== AREA 3: Criticism and Obstacles (Skeptical) ===
1) Collect arguments from fusion critics (costs, timeline, material problems)
2) Research the "50 years away" problem and historical failed predictions
3) Analyze tritium availability and breeding ratio issues

=== AREA 4: Commercial Development (Practical) ===
1) Identify private fusion companies (Commonwealth, TAE, Helion) and their approaches
2) Research investment amounts and timelines for commercial reactors
3) Compare alternative confinement methods (Tokamak vs. Stellarator vs. Laser)

=== AREA 5: Energy Policy Context (Interdisciplinary) ===
1) Analyze fusion compared to other decarbonization pathways
2) Research political funding programs and their justifications
3) Investigate the role of fusion in energy scenarios (IEA, IPCC)

=== END PLAN ===

CRITICAL - LANGUAGE: Always respond in the same language as the user's original query shown below."""


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 3000) -> tuple[Optional[str], Optional[str]]:
    """
    Calls LLM via OpenRouter.

    Returns:
        Tuple (response_text, error_message)
        - Success: (text, None)
        - Failure: (None, error_string)
    """
    result = call_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=get_work_model(),
        max_tokens=max_tokens,
        timeout=90
    )

    if result.error:
        logger.error(f"LLM error: {result.error}")
        return None, result.error

    if not result.content:
        return None, "LLM response empty"

    answer = str(result.content)
    logger.info(f"[ACADEMIC PLAN] RAW LLM RESPONSE:\n{answer[:2000]}...")
    return answer, None


def create_academic_plan(context: ContextState) -> dict:
    """
    Creates a hierarchical Academic research plan with autonomous areas.

    Args:
        context: ContextState with query, follow-up questions and answers

    Returns:
        dict with:
        - bereiche: Dict {area_title: [point1, point2, ...]}
        - plan_text: Formatted plan text
        - raw_response: Raw LLM response
        - error: Error message if occurred
    """
    logger.info("Creating ACADEMIC research plan with autonomous areas...")

    try:
        # Format context for LLM
        context_text = context.format_for_llm()

        user_prompt = f"""{context_text}

Now create an ACADEMIC MODE research plan with autonomous areas.

IMPORTANT:
- 3-5 areas with different PERSPECTIVES
- 2-4 points per area
- Each area MUST be independently researchable
- At least 1 critical area if the topic is controversial
- Use the exact format with === AREA N: [Title] ===
- End with === END PLAN ===

Respond in the same language as the original query!"""

        logger.debug(f"Academic plan prompt length: {len(user_prompt)} chars")

        raw_response, llm_error = _call_llm(ACADEMIC_PLAN_SYSTEM_PROMPT, user_prompt)

        if llm_error:
            return {"error": llm_error, "bereiche": {}}

        if not raw_response:
            return {"error": "Empty response from LLM", "bereiche": {}}

        # Parse areas
        bereiche = parse_academic_plan(raw_response)

        if len(bereiche) < 2:
            logger.warning(f"Only {len(bereiche)} areas found, expected at least 3")

        total_points = sum(len(points) for points in bereiche.values())
        logger.info(f"[ACADEMIC PLAN] Parsed {len(bereiche)} areas with {total_points} total points")

        return {
            "bereiche": bereiche,
            "plan_text": format_academic_plan(bereiche),
            "raw_response": raw_response,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Academic plan generation failed: {e}", exc_info=True)
        return {"error": str(e), "bereiche": {}}


def parse_academic_plan(text: str) -> dict[str, list[str]]:
    """
    Parses the hierarchical Academic Plan.

    Input Format:
    === AREA 1: Thermodynamics ===
    1) Point one
    2) Point two
    === AREA 2: Biology ===
    1) Point one
    ...
    === END PLAN ===

    Returns:
        Dict {area_title: [point1, point2, ...]}
    """
    bereiche = {}

    # Pattern for area header (supports both AREA and BEREICH for compatibility)
    bereich_pattern = r'===\s*(?:AREA|BEREICH)\s*\d+:\s*(.+?)\s*==='

    # Find all area headers and their positions
    headers = list(re.finditer(bereich_pattern, text, re.IGNORECASE))

    for i, header_match in enumerate(headers):
        bereich_titel = header_match.group(1).strip()

        # Content between this header and the next (or END PLAN)
        start_pos = header_match.end()
        if i + 1 < len(headers):
            end_pos = headers[i + 1].start()
        else:
            # Until END PLAN or end
            end_match = re.search(r'===\s*END\s*PLAN\s*===', text[start_pos:], re.IGNORECASE)
            if end_match:
                end_pos = start_pos + end_match.start()
            else:
                end_pos = len(text)

        bereich_content = text[start_pos:end_pos]

        # Extract points from the area
        # Format: 1) Text or - Text
        punkt_pattern = r'(?:^\s*\d+\)|\s*-)\s*(.+?)(?=\n\s*\d+\)|\n\s*-|\n\s*===|\Z)'
        punkt_matches = re.findall(punkt_pattern, bereich_content, re.MULTILINE | re.DOTALL)

        punkte = []
        for punkt in punkt_matches:
            clean_punkt = " ".join(punkt.split()).strip()
            if clean_punkt and len(clean_punkt) > 10:  # Minimum length for meaningful point
                punkte.append(clean_punkt)

        if punkte:
            bereiche[bereich_titel] = punkte
            logger.info(f"[ACADEMIC PLAN] Area '{bereich_titel}': {len(punkte)} points")

    return bereiche


def format_academic_plan(bereiche: dict[str, list[str]]) -> str:
    """Formats Academic Plan for display."""
    if not bereiche:
        return "No plan created."

    lines = []
    for i, (bereich_titel, punkte) in enumerate(bereiche.items(), 1):
        lines.append(f"\n**Area {i}: {bereich_titel}**")
        for j, punkt in enumerate(punkte, 1):
            lines.append(f"  {j}) {punkt}")

    return "\n".join(lines)


# === CLI TEST ===
if __name__ == "__main__":
    ctx = ContextState()
    ctx.user_query = "Is nuclear fusion a realistic energy source?"
    ctx.clarification_questions = ["What aspects interest you most?"]
    ctx.clarification_answers = ["Technical feasibility and timeline"]

    print("Context for LLM:")
    print("=" * 60)
    print(ctx.format_for_llm())
    print("=" * 60)

    result = create_academic_plan(ctx)

    if result.get("error"):
        logger.error("Error: %s", result["error"])
    else:
        print(f"\nGenerated Academic Plan ({len(result['bereiche'])} areas):")
        print(result["plan_text"])
