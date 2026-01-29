"""
Research Prompts
================
Prompts für die Deep Research Pipeline.

NORMAL MODE FLOW:
1. THINK (rekursiv) - Suchstrategie pro Punkt
2. PICK_URLS (rekursiv) - URL-Auswahl pro Punkt
3. DOSSIER (rekursiv) - Dossier pro Punkt
4. FINAL_SYNTHESIS (einmalig) - Alle Dossiers → Finales Dokument

ACADEMIC MODE FLOW:
1. ACADEMIC_PLAN - Erstellt hierarchische Bereiche
2. Für jeden Bereich PARALLEL:
   - THINK → PICK_URLS → DOSSIER (wie Normal Mode)
   - BEREICHS_SYNTHESE (pro Bereich)
3. META_SYNTHESIS - Querverbindungen zwischen Bereichen
4. FINAL_SYNTHESIS - Alles zusammen
"""

from .think import (
    build_think_prompt,
    parse_think_response,
    THINK_SYSTEM_PROMPT,
    THINK_USER_PROMPT,
)

from .pick_urls import (
    build_pick_urls_prompt,
    parse_pick_urls_response,
    PICK_URLS_SYSTEM_PROMPT,
    PICK_URLS_USER_PROMPT,
)

from .dossier import (
    build_dossier_prompt,
    parse_dossier_response,
    DOSSIER_SYSTEM_PROMPT,
    DOSSIER_USER_PROMPT,
)

from .final_synthesis import (
    build_final_synthesis_prompt,
    FINAL_SYNTHESIS_SYSTEM_PROMPT,
    FINAL_SYNTHESIS_USER_PROMPT,
    FINAL_SYNTHESIS_MODEL,
    FINAL_SYNTHESIS_TIMEOUT,
)

# Academic Mode Prompts
from .academic_plan import (
    create_academic_plan,
    parse_academic_plan,
    format_academic_plan,
    ACADEMIC_PLAN_SYSTEM_PROMPT,
)

from .meta_synthesis import (
    build_meta_synthesis_prompt,
    parse_meta_synthesis_response,
    META_SYNTHESIS_SYSTEM_PROMPT,
    META_SYNTHESIS_USER_PROMPT,
    META_SYNTHESIS_MODEL,
    META_SYNTHESIS_TIMEOUT,
)

# NEU: Bereichs-Synthese (jeder Bereich = eigener LLM Call)
from .bereichs_synthesis import (
    build_bereichs_synthesis_prompt,
    BEREICHS_SYNTHESIS_SYSTEM_PROMPT,
    BEREICHS_SYNTHESIS_MODEL,
    BEREICHS_SYNTHESIS_TIMEOUT,
)

# NEU: Academic Conclusion (DER magische finale Call)
from .academic_conclusion import (
    build_academic_conclusion_prompt,
    ACADEMIC_CONCLUSION_SYSTEM_PROMPT,
    ACADEMIC_CONCLUSION_MODEL,
    ACADEMIC_CONCLUSION_TIMEOUT,
)

__all__ = [
    # Think
    "build_think_prompt",
    "parse_think_response",
    "THINK_SYSTEM_PROMPT",
    "THINK_USER_PROMPT",
    # Pick URLs
    "build_pick_urls_prompt",
    "parse_pick_urls_response",
    "PICK_URLS_SYSTEM_PROMPT",
    "PICK_URLS_USER_PROMPT",
    # Dossier
    "build_dossier_prompt",
    "parse_dossier_response",
    "DOSSIER_SYSTEM_PROMPT",
    "DOSSIER_USER_PROMPT",
    # Final Synthesis
    "build_final_synthesis_prompt",
    "FINAL_SYNTHESIS_SYSTEM_PROMPT",
    "FINAL_SYNTHESIS_USER_PROMPT",
    "FINAL_SYNTHESIS_MODEL",
    "FINAL_SYNTHESIS_TIMEOUT",
    # Academic Plan
    "create_academic_plan",
    "parse_academic_plan",
    "format_academic_plan",
    "ACADEMIC_PLAN_SYSTEM_PROMPT",
    # Meta Synthesis
    "build_meta_synthesis_prompt",
    "parse_meta_synthesis_response",
    "META_SYNTHESIS_SYSTEM_PROMPT",
    "META_SYNTHESIS_USER_PROMPT",
    "META_SYNTHESIS_MODEL",
    "META_SYNTHESIS_TIMEOUT",
    # Bereichs-Synthese
    "build_bereichs_synthesis_prompt",
    "BEREICHS_SYNTHESIS_SYSTEM_PROMPT",
    "BEREICHS_SYNTHESIS_MODEL",
    "BEREICHS_SYNTHESIS_TIMEOUT",
    # Academic Conclusion
    "build_academic_conclusion_prompt",
    "ACADEMIC_CONCLUSION_SYSTEM_PROMPT",
    "ACADEMIC_CONCLUSION_MODEL",
    "ACADEMIC_CONCLUSION_TIMEOUT",
]
