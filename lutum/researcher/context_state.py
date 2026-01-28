"""
Context State Manager
=====================
Verwaltet den Recherche-Kontext für die LLM.

Prinzip: JSON ist Silber, kein JSON ist Gold.
- Intern: Python dict
- Für LLM: Klar formatierter Text mit Markern
- Parsing: Regex auf Text-Patterns
"""

from dataclasses import dataclass, field
from typing import Optional
from lutum.core.log_config import get_logger

logger = get_logger(__name__)


@dataclass
class ContextState:
    """
    Recherche-Kontext der durch die Pipeline wandert.

    Enthält NUR was die LLM braucht um zu wissen wo sie steht:
    - User Query
    - Rückfragen + Antworten
    - Aktueller Recherche-Plan

    KEINE Suchergebnisse, KEINE gescrapten Inhalte.
    """
    user_query: str = ""

    # Step 3: Rückfragen
    clarification_questions: list[str] = field(default_factory=list)
    clarification_answers: list[str] = field(default_factory=list)

    # Step 4: Recherche-Plan
    research_plan: list[str] = field(default_factory=list)
    plan_version: int = 0

    # Meta
    session_title: str = ""
    current_step: int = 0

    def add_clarification(self, questions: list[str]):
        """Rückfragen aus Step 3 hinzufügen."""
        self.clarification_questions = questions
        logger.debug(f"Added {len(questions)} clarification questions")

    def add_answers(self, answers: list[str]):
        """User-Antworten auf Rückfragen hinzufügen."""
        self.clarification_answers = answers
        logger.debug(f"Added {len(answers)} user answers")

    def set_plan(self, plan_points: list[str]):
        """Recherche-Plan setzen (ersetzt alten)."""
        self.research_plan = plan_points
        self.plan_version += 1
        logger.debug(f"Set research plan v{self.plan_version} with {len(plan_points)} points")

    def format_for_llm(self) -> str:
        """
        Formatiert den State als lesbaren Text für die LLM.

        Returns:
            Klar strukturierter Text den die LLM versteht
        """
        lines = []

        # User Query - immer da
        lines.append("=== DEINE AUFGABE ===")
        lines.append(self.user_query)
        lines.append("")

        # Rückfragen falls vorhanden
        if self.clarification_questions:
            lines.append("=== RÜCKFRAGEN ===")
            for i, q in enumerate(self.clarification_questions, 1):
                lines.append(f"{i}. {q}")
            lines.append("")

        # User Antworten falls vorhanden
        if self.clarification_answers:
            lines.append("=== USER ANTWORTEN ===")
            for i, a in enumerate(self.clarification_answers, 1):
                lines.append(f"{i}. {a}")
            lines.append("")

        # Recherche-Plan falls vorhanden
        if self.research_plan:
            lines.append(f"=== RECHERCHE-PLAN (v{self.plan_version}) ===")
            for i, point in enumerate(self.research_plan, 1):
                lines.append(f"({i}) {point}")
            lines.append("")

        return "\n".join(lines)

    def format_plan_for_user(self) -> str:
        """
        Formatiert nur den Plan für die User-Anzeige.

        Returns:
            Plan als formatierter Text
        """
        if not self.research_plan:
            return "Kein Recherche-Plan vorhanden."

        lines = ["**Recherche-Plan:**", ""]
        for i, point in enumerate(self.research_plan, 1):
            lines.append(f"({i}) {point}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Für Serialisierung/Speicherung."""
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
        """Aus gespeichertem dict laden."""
        state = cls()
        state.user_query = data.get("user_query", "")
        state.clarification_questions = data.get("clarification_questions", [])
        state.clarification_answers = data.get("clarification_answers", [])
        state.research_plan = data.get("research_plan", [])
        state.plan_version = data.get("plan_version", 0)
        state.session_title = data.get("session_title", "")
        state.current_step = data.get("current_step", 0)
        return state
