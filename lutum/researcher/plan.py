"""
Step 4: Research Plan Generation
================================
LLM creates a deep research plan based on:
- User Query
- Follow-up questions + answers

Output: At least 5 research points.
"""

import re
from typing import Optional, Tuple
from lutum.core.log_config import get_logger
from lutum.core.api_config import get_work_model
from lutum.core.llm_client import call_chat_completion
from lutum.researcher.context_state import ContextState

logger = get_logger(__name__)


PLAN_SYSTEM_PROMPT = """You are a research expert who creates deep, reproducible research plans.

YOUR GOAL:
Create a research plan that is so concrete that another researcher can execute it 1:1
(including search strings, filters, expected deliverables).

═══════════════════════════════════════════════════════════════════
                         HARD RULES (MANDATORY)
═══════════════════════════════════════════════════════════════════

- Output consists ONLY of numbered points: (1), (2), (3) ...
- Between EVERY point: an EMPTY LINE.
- Each point begins with a verb (Search, Research, Identify, Check, Investigate, Compare, Extract, Validate ...).
- No introduction, no meta-explanation, no conclusion outside the points.
- At least 5 points; more if thematically necessary.
- NO scope drift: Keep time windows and platforms exactly as specified.

═══════════════════════════════════════════════════════════════════
                         QUALITY (MANDATORY)
═══════════════════════════════════════════════════════════════════

Each point MUST contain this mini-structure:

a) **Goal** (1 sentence): What exactly should be found/verified?
b) **Search Queries**: At least 2 concrete search queries (with operators if useful)
c) **Filters/Constraints**: e.g. time period, platform, language, etc.
d) **Output**: What artifact is produced? (List, table, comparison)
e) **Validation** (1 sentence): How do you check relevance/quality?

═══════════════════════════════════════════════════════════════════
                         LEDGER TYPES (Reference)
═══════════════════════════════════════════════════════════════════

Write in each point which ledger is filled:

**Repo Ledger** (for GitHub/GitLab):
Repo | Link | Tech/Keyword | Claim (1 sentence) | Evidence Snippet | Maturity | Notes

**Paper Ledger** (for Arxiv/Papers):
Paper | Link | Year | Contribution | Key Result | Evidence Snippet | Limitations

**Thread Ledger** (for Reddit/HN/Forums):
Platform | Link | Topic | Main Argument | Takeaway | Evidence Snippet | Credibility

**Issue Ledger** (for GitHub Issues/PRs):
Project | Issue/PR | Status | Feature | Link | Notes

═══════════════════════════════════════════════════════════════════
                         EXAMPLE FORMAT
═══════════════════════════════════════════════════════════════════

(1) Search for GitHub repositories implementing adaptive RAG chunking.
**Goal:** Identify active open-source projects that implement dynamic chunk sizing.
**Search Queries:** "adaptive chunking RAG" site:github.com, "dynamic chunk size langchain"
**Filters:** Only repos with >10 stars, last commit <12 months
**Output:** Repo Ledger with 5-10 entries
**Validation:** Repo must have working code, not just README.

(2) Research r/LocalLLaMA for experience reports on chunking strategies.
**Goal:** Collect practical insights from the community on chunking problems.
**Search Queries:** "chunking" site:reddit.com/r/LocalLLaMA, "chunk size RAG reddit"
**Filters:** Posts from last 6 months, >10 upvotes
**Output:** Thread Ledger with bottlenecks and workarounds
**Validation:** Only threads with concrete experiences, no unanswered questions.

(3) ...etc.

═══════════════════════════════════════════════════════════════════
CRITICAL: Your research plan must ALWAYS be in the SAME LANGUAGE as the user's query/question. Match the user's language exactly.
═══════════════════════════════════════════════════════════════════"""


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> Tuple[Optional[str], Optional[str]]:
    """
    Calls LLM via OpenRouter.
    """
    result = call_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=get_work_model(),
        max_tokens=max_tokens,
        timeout=60
    )

    if result.error:
        logger.error(f"LLM error: {result.error}")
        return None, result.error

    if not result.content:
        return None, "LLM response empty"

    answer = str(result.content)
    logger.info(f"[PLAN] RAW LLM RESPONSE:\n{answer[:2000]}...")
    return answer, None


def create_research_plan(context: ContextState) -> dict:
    """
    Creates a research plan based on the Context State.

    Args:
        context: ContextState with Query, follow-up questions and answers

    Returns:
        dict with:
        - plan_points: List of plan points
        - plan_text: Formatted plan text
        - raw_response: Raw LLM response
        - error: Error message if occurred
    """
    logger.info("Creating research plan...")

    try:
        # Format context for LLM
        context_text = context.format_for_llm()

        # Build prompt
        user_prompt = f"""{context_text}

Now create a deep research plan (at least 5 points).
Use the specified format with Goal/Search Queries/Filters/Output/Validation per point."""

        logger.debug(f"Plan prompt length: {len(user_prompt)} chars")

        # Call LLM via OpenRouter
        raw_response, error_message = _call_llm(PLAN_SYSTEM_PROMPT, user_prompt)

        if not raw_response:
            return {"error": error_message or "LLM call failed", "plan_points": []}

        logger.debug(f"Plan response: {raw_response[:200]}...")

        # Parse plan points
        plan_points = _parse_plan_points(raw_response)

        if len(plan_points) < 5:
            logger.warning(f"Only {len(plan_points)} plan points found, expected at least 5")

        return {
            "plan_points": plan_points,
            "plan_text": _format_plan(plan_points),
            "raw_response": raw_response,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        return {"error": str(e), "plan_points": []}


def revise_research_plan(context: ContextState, user_feedback: str) -> dict:
    """
    Revises the research plan based on user feedback.

    Args:
        context: ContextState with existing plan
        user_feedback: What the user wants to change

    Returns:
        dict with new plan
    """
    logger.info(f"Revising research plan based on feedback: {user_feedback[:100]}...")

    try:
        # Format context for LLM
        context_text = context.format_for_llm()

        # Prompt with feedback
        user_prompt = f"""{context_text}

=== USER FEEDBACK ON PLAN ===
{user_feedback}

Revise the research plan based on the feedback.
Keep what was good, change what the user criticized.
At least 5 points, numbered with (1), (2), etc.
Use the specified format with Goal/Search Queries/Filters/Output/Validation per point."""

        # Call LLM via OpenRouter
        raw_response, error_message = _call_llm(PLAN_SYSTEM_PROMPT, user_prompt)

        if not raw_response:
            return {"error": error_message or "LLM call failed", "plan_points": []}

        # Parse plan points
        plan_points = _parse_plan_points(raw_response)

        return {
            "plan_points": plan_points,
            "plan_text": _format_plan(plan_points),
            "raw_response": raw_response,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Plan revision failed: {e}", exc_info=True)
        return {"error": str(e), "plan_points": []}


def _parse_plan_points(text: str) -> list[str]:
    """
    Parses numbered plan points from LLM output.

    Expected format:
    (1) First point...
    (2) Second point...

    Args:
        text: Raw LLM output

    Returns:
        List of plan points (without numbering)
    """
    # Pattern: (1), (2), etc. at line start
    pattern = r'\((\d+)\)\s*(.+?)(?=\n\(\d+\)|\n\n|\Z)'
    matches = re.findall(pattern, text, re.DOTALL)

    points = []
    for num, content in matches:
        # Cleanup: line breaks to spaces, trim
        clean_content = " ".join(content.split())
        if clean_content:
            points.append(clean_content)

    logger.debug(f"Parsed {len(points)} plan points")
    logger.info(f"[PLAN] PARSED POINTS: {len(points)} points")
    for i, p in enumerate(points, 1):
        logger.info(f"[PLAN] POINT {i}: {p[:100]}...")
    return points


def _format_plan(points: list[str]) -> str:
    """Formats plan points for display."""
    if not points:
        return "No plan created."

    lines = []
    for i, point in enumerate(points, 1):
        lines.append(f"({i}) {point}")

    return "\n\n".join(lines)


# === CLI TEST ===
if __name__ == "__main__":
    # Test with dummy context
    ctx = ContextState()
    ctx.user_query = "What are the latest RAG techniques for LLMs?"
    ctx.clarification_questions = [
        "Which specific aspects interest you?",
        "Do you have experience with RAG systems?",
    ]
    ctx.clarification_answers = [
        "Compression and token reduction",
        "Yes, basic knowledge with LangChain",
    ]

    print("Context for LLM:")
    print("=" * 60)
    print(ctx.format_for_llm())
    print("=" * 60)

    result = create_research_plan(ctx)

    if result.get("error"):
        logger.error("Error: %s", result["error"])
    else:
        print(f"\nGenerated Plan ({len(result['plan_points'])} points):")
        print(result["plan_text"])
