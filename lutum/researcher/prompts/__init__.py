"""
Research Prompts
================
Prompts für die Deep Research Pipeline.

FLOW:
1. THINK (rekursiv) - Suchstrategie pro Punkt
2. PICK_URLS (rekursiv) - URL-Auswahl pro Punkt
3. DOSSIER (rekursiv) - Dossier pro Punkt
4. FINAL_SYNTHESIS (einmalig) - Alle Dossiers → Finales Dokument
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
]
