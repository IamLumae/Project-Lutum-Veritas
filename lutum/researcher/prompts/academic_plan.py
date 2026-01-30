"""
Academic Plan Prompt v2.0
=========================
Erstellt einen hierarchischen Recherche-Plan mit AUTONOMEN BEREICHEN
für parallele Deep Research.

UNTERSCHIED ZU NORMAL MODE:
- Normal: Flache Liste (1), (2), (3)... → sequenziell abgearbeitet
- Academic: Bereiche mit Unterpunkten → parallel abgearbeitet

Jeder Bereich ist UNABHÄNGIG erforschbar (keine Abhängigkeiten zwischen Bereichen).
Key Learnings fließen nur INNERHALB eines Bereichs.

v2.0 UPDATES:
- Evidenz-Diversität pro Bereich (verschiedene Quellentypen)
- Explizite Perspektiven-Zuweisung
- Parser-kompatibles Format
"""

import re
from typing import Optional
import requests
from lutum.core.log_config import get_logger
from lutum.core.api_config import get_api_key
from lutum.researcher.context_state import ContextState

logger = get_logger(__name__)

# OpenRouter Config
MODEL = "google/gemini-2.5-flash-lite-preview-09-2025"


ACADEMIC_PLAN_SYSTEM_PROMPT = """Du bist ein Forschungsarchitekt der multi-disziplinäre Recherche-Pläne erstellt.

═══════════════════════════════════════════════════════════════════
                    SPRACHE (KRITISCH!)
═══════════════════════════════════════════════════════════════════

WICHTIG: Antworte IMMER in der Sprache der ursprünglichen Nutzer-Anfrage!
- Deutsche Anfrage → Deutscher Plan
- English query → English plan
- Die Bereichs-Titel und Punkte müssen in der gleichen Sprache sein!

═══════════════════════════════════════════════════════════════════
                    FORMAT-MARKER (PFLICHT!)
═══════════════════════════════════════════════════════════════════

Diese Marker ermöglichen automatisches Parsing - EXAKT so verwenden:

BEREICHS-HEADER:   === BEREICH N: [Titel] ===
PUNKTE:            1) Text des Punktes
                   2) Text des Punktes
ABSCHLUSS:         === END PLAN ===

═══════════════════════════════════════════════════════════════════
                    ACADEMIC MODE - WAS ES IST
═══════════════════════════════════════════════════════════════════

Du erstellst einen Plan mit **AUTONOMEN BEREICHEN** statt einer flachen Liste.

WARUM BEREICHE?
- Jeder Bereich wird PARALLEL recherchiert (nicht sequenziell)
- Das ermöglicht multidisziplinäre Perspektiven auf das gleiche Problem
- Am Ende werden die Bereiche in einer META-SYNTHESE zusammengeführt
- Querverbindungen werden erst NACH der unabhängigen Recherche gefunden

═══════════════════════════════════════════════════════════════════
                    PERSPEKTIVEN-DIVERSITÄT (NEU!)
═══════════════════════════════════════════════════════════════════

Jeder Bereich sollte eine ANDERE PERSPEKTIVE repräsentieren:

MÖGLICHE PERSPEKTIVEN (wähle 3-5 passende):
- **Theoretisch/Fundamental**: Grundlagen, Prinzipien, Axiome
- **Empirisch/Experimental**: Studien, Daten, Messungen
- **Praktisch/Angewandt**: Implementierungen, Use Cases, Tools
- **Kritisch/Skeptisch**: Gegenargumente, Limitationen, Kontroversen
- **Historisch/Evolutionär**: Entwicklung, Meilensteine, Trends
- **Interdisziplinär**: Verbindungen zu anderen Feldern
- **Zukunft/Spekulativ**: Prognosen, offene Fragen, Forschungslücken

BEISPIEL für "Klimawandel":
- Bereich 1: Physikalische Grundlagen (Theoretisch)
- Bereich 2: Messdaten und Modelle (Empirisch)
- Bereich 3: Gegenargumente und Kontroversen (Kritisch)
- Bereich 4: Technologische Lösungsansätze (Praktisch)

═══════════════════════════════════════════════════════════════════
                    EVIDENZ-DIVERSITÄT PRO BEREICH (NEU!)
═══════════════════════════════════════════════════════════════════

Jeder Bereich sollte verschiedene QUELLENTYPEN ansprechen:

- **Primärquellen**: Originalstudien, Papers, Patente
- **Sekundärquellen**: Reviews, Meta-Analysen, Lehrbücher
- **Graue Literatur**: Preprints, Konferenzpaper, Whitepapers
- **Community**: Foren, Diskussionen, Expertenmeinungen
- **Praxis**: Dokumentation, Tutorials, Case Studies

Formuliere Punkte so, dass verschiedene Quellentypen gefunden werden!

═══════════════════════════════════════════════════════════════════
                    HARTREGELN (PFLICHT!)
═══════════════════════════════════════════════════════════════════

1. **AUTONOMIE-REGEL**: Jeder Bereich MUSS unabhängig erforschbar sein!
   - KEINE Abhängigkeiten zwischen Bereichen
   - KEINE Verweise wie "basierend auf Bereich 1..."
   - Jeder Bereich steht für sich allein

2. **BALANCE-REGEL**:
   - 3-5 Bereiche (optimal: 4)
   - 2-4 Punkte pro Bereich
   - Ähnliche Tiefe pro Bereich

3. **DIVERSITÄTS-REGEL**:
   - Verschiedene PERSPEKTIVEN (nicht nur verschiedene Themen)
   - Mindestens 1 kritischer/skeptischer Bereich wenn kontrovers

4. **KONKRETHEIT-REGEL**:
   - Jeder Punkt beginnt mit Verb (Recherchiere, Analysiere, Vergleiche...)
   - Jeder Punkt hat ein messbares Ziel
   - Jeder Punkt ist googlebar

═══════════════════════════════════════════════════════════════════
                    BEISPIEL KOMPLETTES OUTPUT
═══════════════════════════════════════════════════════════════════

Frage: "Ist Kernfusion eine realistische Energiequelle?"

=== BEREICH 1: Physikalische Grundlagen (Theoretisch) ===
1) Recherchiere die fundamentalen Fusionsreaktionen (D-T, D-D, p-B11) und deren Energieausbeute
2) Analysiere das Lawson-Kriterium und die Anforderungen an Plasma-Confinement
3) Vergleiche die theoretischen Effizienzgrenzen mit Fission und Renewables

=== BEREICH 2: Experimenteller Stand (Empirisch) ===
1) Dokumentiere die Ergebnisse von ITER, NIF, JET und anderen Großexperimenten
2) Recherchiere den aktuellen Q-Faktor-Rekord und die Entwicklung seit 2020
3) Analysiere peer-reviewed Papers zu Plasma-Instabilitäten und deren Lösungen

=== BEREICH 3: Kritik und Hindernisse (Skeptisch) ===
1) Sammle Argumente von Fusionskritikern (Kosten, Zeitrahmen, Materialprobleme)
2) Recherchiere das "50 Jahre entfernt"-Problem und historische Fehlprognosen
3) Analysiere die Tritium-Verfügbarkeit und Breeding-Ratio-Problematik

=== BEREICH 4: Kommerzielle Entwicklung (Praktisch) ===
1) Identifiziere private Fusionsunternehmen (Commonwealth, TAE, Helion) und deren Ansätze
2) Recherchiere Investitionssummen und Zeitpläne für kommerzielle Reaktoren
3) Vergleiche alternative Confinement-Methoden (Tokamak vs. Stellarator vs. Laser)

=== BEREICH 5: Energiepolitischer Kontext (Interdisziplinär) ===
1) Analysiere Fusion im Vergleich zu anderen Dekarbonisierungspfaden
2) Recherchiere politische Förderprogramme und deren Begründungen
3) Untersuche die Rolle von Fusion in Energieszenarien (IEA, IPCC)

=== END PLAN ===
"""


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 3000) -> tuple[Optional[str], Optional[str]]:
    """
    Ruft LLM via OpenRouter auf.

    Returns:
        Tuple (response_text, error_message)
        - Success: (text, None)
        - Failure: (None, error_string)
    """
    try:
        api_key = get_api_key()
        if not api_key:
            return None, "No API key configured"

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=90
        )

        result = response.json()

        # Log full response for debugging
        logger.info(f"[ACADEMIC PLAN] OpenRouter response status: {response.status_code}")

        if "choices" not in result:
            error_msg = result.get("error", {}).get("message", str(result))
            logger.error(f"LLM error: {error_msg}")
            return None, f"OpenRouter error: {error_msg}"

        answer = result["choices"][0]["message"]["content"]
        logger.info(f"[ACADEMIC PLAN] RAW LLM RESPONSE:\n{answer[:2000]}...")
        return answer, None

    except requests.Timeout:
        logger.error("LLM timeout after 90s")
        return None, "LLM request timed out (90s)"
    except Exception as e:
        logger.error(f"LLM call failed: {e}", exc_info=True)
        return None, f"LLM call failed: {str(e)}"


def create_academic_plan(context: ContextState) -> dict:
    """
    Erstellt einen hierarchischen Academic-Recherche-Plan mit autonomen Bereichen.

    Args:
        context: ContextState mit Query, Rückfragen und Antworten

    Returns:
        dict mit:
        - bereiche: Dict {bereich_titel: [punkt1, punkt2, ...]}
        - plan_text: Formatierter Plan-Text
        - raw_response: Rohe LLM Antwort
        - error: Fehlermeldung falls aufgetreten
    """
    logger.info("Creating ACADEMIC research plan with autonomous areas...")

    try:
        # Context für LLM formatieren
        context_text = context.format_for_llm()

        user_prompt = f"""{context_text}

Erstelle jetzt einen ACADEMIC MODE Recherche-Plan mit autonomen Bereichen.

WICHTIG:
- 3-5 Bereiche mit verschiedenen PERSPEKTIVEN
- 2-4 Punkte pro Bereich
- Jeder Bereich MUSS unabhängig erforschbar sein
- Mindestens 1 kritischer Bereich wenn das Thema kontrovers ist
- Nutze das exakte Format mit === BEREICH N: [Titel] ===
- Beende mit === END PLAN ===

Antworte in der Sprache der ursprünglichen Anfrage!"""

        logger.debug(f"Academic plan prompt length: {len(user_prompt)} chars")

        raw_response, llm_error = _call_llm(ACADEMIC_PLAN_SYSTEM_PROMPT, user_prompt)

        if llm_error:
            return {"error": llm_error, "bereiche": {}}

        if not raw_response:
            return {"error": "Empty response from LLM", "bereiche": {}}

        # Bereiche parsen
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
    Parst den hierarchischen Academic Plan.

    Input Format:
    === BEREICH 1: Thermodynamik ===
    1) Punkt eins
    2) Punkt zwei
    === BEREICH 2: Biologie ===
    1) Punkt eins
    ...
    === END PLAN ===

    Returns:
        Dict {bereich_titel: [punkt1, punkt2, ...]}
    """
    bereiche = {}

    # Pattern für Bereich-Header
    bereich_pattern = r'===\s*BEREICH\s*\d+:\s*(.+?)\s*==='

    # Finde alle Bereich-Header und ihre Positionen
    headers = list(re.finditer(bereich_pattern, text, re.IGNORECASE))

    for i, header_match in enumerate(headers):
        bereich_titel = header_match.group(1).strip()

        # Content zwischen diesem Header und dem nächsten (oder END PLAN)
        start_pos = header_match.end()
        if i + 1 < len(headers):
            end_pos = headers[i + 1].start()
        else:
            # Bis END PLAN oder Ende
            end_match = re.search(r'===\s*END\s*PLAN\s*===', text[start_pos:], re.IGNORECASE)
            if end_match:
                end_pos = start_pos + end_match.start()
            else:
                end_pos = len(text)

        bereich_content = text[start_pos:end_pos]

        # Punkte aus dem Bereich extrahieren
        # Format: 1) Text oder - Text
        punkt_pattern = r'(?:^\s*\d+\)|\s*-)\s*(.+?)(?=\n\s*\d+\)|\n\s*-|\n\s*===|\Z)'
        punkt_matches = re.findall(punkt_pattern, bereich_content, re.MULTILINE | re.DOTALL)

        punkte = []
        for punkt in punkt_matches:
            clean_punkt = " ".join(punkt.split()).strip()
            if clean_punkt and len(clean_punkt) > 10:  # Mindestlänge für sinnvollen Punkt
                punkte.append(clean_punkt)

        if punkte:
            bereiche[bereich_titel] = punkte
            logger.info(f"[ACADEMIC PLAN] Area '{bereich_titel}': {len(punkte)} points")

    return bereiche


def format_academic_plan(bereiche: dict[str, list[str]]) -> str:
    """Formatiert Academic Plan für Anzeige."""
    if not bereiche:
        return "Kein Plan erstellt."

    lines = []
    for i, (bereich_titel, punkte) in enumerate(bereiche.items(), 1):
        lines.append(f"\n**Bereich {i}: {bereich_titel}**")
        for j, punkt in enumerate(punkte, 1):
            lines.append(f"  {j}) {punkt}")

    return "\n".join(lines)


# === CLI TEST ===
if __name__ == "__main__":
    ctx = ContextState()
    ctx.user_query = "Ist Kernfusion eine realistische Energiequelle?"
    ctx.clarification_questions = ["Welche Aspekte interessieren dich besonders?"]
    ctx.clarification_answers = ["Technische Machbarkeit und Zeitrahmen"]

    print("Context for LLM:")
    print("=" * 60)
    print(ctx.format_for_llm())
    print("=" * 60)

    result = create_academic_plan(ctx)

    if result.get("error"):
        print(f"Error: {result['error']}")
    else:
        print(f"\nGenerated Academic Plan ({len(result['bereiche'])} areas):")
        print(result["plan_text"])
