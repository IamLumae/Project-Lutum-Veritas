"""
Context State Manager
=====================
Manages the research context for the LLM.

Principle: JSON is silver, no JSON is gold.
- Internal: Python dict
- For LLM: Clearly formatted text with markers
- Parsing: Regex on text patterns
"""

from dataclasses import dataclass, field
from typing import Optional
from lutum.core.log_config import get_logger

logger = get_logger(__name__)


@dataclass
class ContextState:
    """
    Research context that travels through the pipeline.

    Contains ONLY what the LLM needs to know where it stands:
    - User Query
    - Follow-up questions + answers
    - Current research plan

    NO search results, NO scraped content.
    """
    user_query: str = ""

    # Step 3: Follow-up questions
    clarification_questions: list[str] = field(default_factory=list)
    clarification_answers: list[str] = field(default_factory=list)

    # Step 4: Research plan
    research_plan: list[str] = field(default_factory=list)
    plan_version: int = 0

    # Meta
    session_title: str = ""
    current_step: int = 0

    def add_clarification(self, questions: list[str]):
        """Add follow-up questions from Step 3."""
        self.clarification_questions = questions
        logger.debug(f"Added {len(questions)} clarification questions")

    def add_answers(self, answers: list[str]):
        """Add user answers to follow-up questions."""
        self.clarification_answers = answers
        logger.debug(f"Added {len(answers)} user answers")

    def set_plan(self, plan_points: list[str]):
        """Set research plan (replaces old one)."""
        self.research_plan = plan_points
        self.plan_version += 1
        logger.debug(f"Set research plan v{self.plan_version} with {len(plan_points)} points")

    def format_for_llm(self) -> str:
        """
        Formats the state as readable text for the LLM.

        Returns:
            Clearly structured text that the LLM understands
        """
        lines = []

        # User Query - always present
        lines.append("=== YOUR TASK ===")
        lines.append(self.user_query)
        lines.append("")

        # Follow-up questions if present
        if self.clarification_questions:
            lines.append("=== FOLLOW-UP QUESTIONS ===")
            for i, q in enumerate(self.clarification_questions, 1):
                lines.append(f"{i}. {q}")
            lines.append("")

        # User answers if present
        if self.clarification_answers:
            lines.append("=== USER ANSWERS ===")
            for i, a in enumerate(self.clarification_answers, 1):
                lines.append(f"{i}. {a}")
            lines.append("")

        # Research plan if present
        if self.research_plan:
            lines.append(f"=== RESEARCH PLAN (v{self.plan_version}) ===")
            for i, point in enumerate(self.research_plan, 1):
                lines.append(f"({i}) {point}")
            lines.append("")

        return "\n".join(lines)

    def format_plan_for_user(self) -> str:
        """
        Formats only the plan for user display.

        Returns:
            Plan as formatted text
        """
        if not self.research_plan:
            return "No research plan available."

        lines = ["**Research Plan:**", ""]
        for i, point in enumerate(self.research_plan, 1):
            lines.append(f"({i}) {point}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """For serialization/storage."""
        return {
            "user_query": self.user_query,
            "clarification_questions": self.clarification_questions,
            "clarification_answers": self.clarification_answers,
            "research_plan": self.research_plan,
            "plan_version": self.plan_version,
            "session_title": self.session_title,
            "current_step": self.current_step,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContextState":
        """Load from saved dict."""
        state = cls()
        state.user_query = data.get("user_query", "")
        state.clarification_questions = data.get("clarification_questions", [])
        state.clarification_answers = data.get("clarification_answers", [])
        state.research_plan = data.get("research_plan", [])
        state.plan_version = data.get("plan_version", 0)
        state.session_title = data.get("session_title", "")
        state.current_step = data.get("current_step", 0)
        return state
