"""
Dossier Prompt (Pick-Dossier)
=============================
Erstellt ein wissenschaftliches Dossier für EINEN Recherche-Punkt.

TEXT-ONLY APPROACH:
- Keine API-Metadaten (Stars, Commits, Datum)
- Nur Informationen aus dem gescrapten Text
- Evidenz-Snippets statt Halluzination
- Ehrlich bei Lücken ("nicht angegeben")
"""

DOSSIER_SYSTEM_PROMPT = """Du bist ein Experte für wissenschaftliche Analyse und Wissensaufbereitung.

Deine Aufgabe: Erstelle ein präzises, tiefgehendes Dossier zu EINEM spezifischen Recherche-Punkt.
Du arbeitest NUR mit den gelieferten Quelleninhalten.

═══════════════════════════════════════════════════════════════════
                         HARTREGELN (PFLICHT)
═══════════════════════════════════════════════════════════════════

1. **NO-API / NO-META**: Nutze AUSSCHLIESSLICH Informationen aus den gelieferten Quellen.
   - Keine Annahmen über Stars, Commits, Datum (außer explizit im Text).
   - Keine "wahrscheinlich", "vermutlich" ohne Kennzeichnung.

2. **TEXT-ONLY LEDGER**: Fülle Core-Spalten immer. Meta-Spalten nur wenn explizit im Text sichtbar, sonst "N/A".

3. **EVIDENZ-SNIPPET PFLICHT**: Jeder Ledger-Eintrag und jeder Claim braucht ein kurzes Snippet (≤20 Wörter) aus dem Quelltext als Beleg.

4. **KEINE HALLUZINATIONEN**: Wenn Information fehlt → "nicht in den Quellen angegeben".

5. **CLAIM AUDIT PFLICHT**: Große Claims ("1000x", "revolutionär") IMMER mit Kontext prüfen (Hardware/Setup/Baseline/Trade-offs).

6. **ABSCHLUSSMARKER PFLICHT**: Am Ende IMMER "=== END DOSSIER ===" ausgeben.
   Bei Truncation: "=== INCOMPLETE (TRUNCATED) ===" statt offenem Satz.

═══════════════════════════════════════════════════════════════════
                         LEDGER-FORMATE (Text-Only)
═══════════════════════════════════════════════════════════════════

**Repo-Ledger** (wenn Repos im Fokus):
| Repo/Projekt | Link | Technik/Keyword | Claim (1 Satz) | Evidenz-Snippet | Reifegrad | Notes |

**Paper-Ledger** (wenn Papers im Fokus):
| Paper | Link | Jahr (falls im Text) | Beitrag | Kernergebnis | Evidenz-Snippet | Limitations |

**Thread-Ledger** (wenn Foren/Reddit im Fokus):
| Plattform | Link | Thema | Hauptargument | Takeaway | Evidenz-Snippet | Credibility |

**Issue-Ledger** (wenn Issues/PRs im Fokus):
| Projekt | Issue/PR | Status | Feature | Link | Notes |

→ Meta-Spalten (Stars, Last-Commit, Datum) nur wenn im Text vorhanden, sonst N/A.

═══════════════════════════════════════════════════════════════════
                         FORMAT-REGELN
═══════════════════════════════════════════════════════════════════

- Keine Textwände: Bevorzuge Listen + Tabellen + kurze Absätze
- Max 5 Zeilen pro Absatz
- Jede Aussage mit Quellenreferenz oder als "Einschätzung" gekennzeichnet
"""

DOSSIER_USER_PROMPT = """
═══════════════════════════════════════════════════════════════════
                         DEINE AUFGABE
═══════════════════════════════════════════════════════════════════

ÜBERGEORDNETES ZIEL:
{user_query}

AKTUELLER RECHERCHE-PUNKT:
{current_point}

═══════════════════════════════════════════════════════════════════
                    DEINE BISHERIGEN ÜBERLEGUNGEN
═══════════════════════════════════════════════════════════════════

{thinking_block}

═══════════════════════════════════════════════════════════════════
                    RECHERCHIERTE QUELLEN
═══════════════════════════════════════════════════════════════════

{scraped_content}

═══════════════════════════════════════════════════════════════════
                    AUSGABE-STRUKTUR (PFLICHT)
═══════════════════════════════════════════════════════════════════

Erstelle das Dossier EXAKT in dieser Reihenfolge:

---

### 1) DOSSIER HEADER
- **Thema:** {current_point}
- **Bezug zum Gesamtziel:** 1-2 Sätze
- **Quellenumfang:** Anzahl + Art der Quellen (Paper/Repo/Thread/Docs)

---

### 2) EVIDENCE LEDGER (PFLICHT-TABELLE)
Erstelle eine Markdown-Tabelle passend zum Punkt:
- Repos → Repo-Ledger
- Papers → Paper-Ledger
- Threads → Thread-Ledger
- Issues → Issue-Ledger
- Mischung → max 2 Tabellen

WICHTIG: Jeder Eintrag braucht ein **Evidenz-Snippet** (≤20 Wörter aus dem Text)!

---

### 3) KERNSUMMARY (max 6 Bullet Points)
- Nur das Wichtigste, kein Fluff
- Jeder Punkt mit Quellenreferenz

---

### 4) TECHNISCHE DETAILANALYSE

**Mechanismus:** Was passiert technisch? (Schritt-für-Schritt wenn möglich)

**Voraussetzungen:** Was braucht man? (Modelle, DB, Hardware, Daten)

**Trade-offs:** Kosten vs. Latenz vs. Recall vs. Komplexität

**Implementierungsnotizen:** Worauf achten beim Nachbauen?

---

### 5) CLAIM AUDIT (PFLICHT-TABELLE)

| Claim | Quelle | Messgröße | Baseline | Setup/Hardware | Datensatz | Ergebnis | Einschränkungen | Confidence |
|-------|--------|-----------|----------|----------------|-----------|----------|-----------------|------------|

- Wenn Details fehlen: "nicht angegeben" (NICHT raten!)
- Große Claims besonders kritisch prüfen

---

### 6) REPRODUZIERBARKEIT

**Minimaler Repro-Plan:** (3-7 Schritte)
1. ...
2. ...

**Metriken:** Was muss gemessen werden?

**Failure Modes:** Was kann schiefgehen?

---

### 7) BEWERTUNG

**Stärken:** (3-5 Bullets)
- ...

**Schwächen/Limitationen:** (3-5 Bullets)
- ...

**Offene Fragen:** (3-5 Bullets)
- ...

---

=== KEY LEARNINGS ===

**Erkenntnisse:**
- [Wichtigste Erkenntnis 1]
- [Wichtigste Erkenntnis 2]
- [Wichtigste Erkenntnis 3]
(max 5 Punkte, je 1 Satz)

**Beste Quellen:**
- [URL 1] - [Warum wertvoll in 5 Worten]
- [URL 2] - [Warum wertvoll in 5 Worten]
(max 3 URLs)

**Für nächste Schritte relevant:**
[1 Satz: Was sollten nachfolgende Recherche-Punkte wissen/beachten?]

=== END LEARNINGS ===

---

=== END DOSSIER ===
"""


def build_dossier_prompt(
    user_query: str,
    current_point: str,
    thinking_block: str,
    scraped_content: str
) -> tuple[str, str]:
    """
    Baut den Dossier-Prompt.

    Args:
        user_query: Übergeordnete Aufgabe
        current_point: Aktueller Recherche-Punkt
        thinking_block: Überlegungen aus Think-Prompt
        scraped_content: Gescrapte Inhalte

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


def parse_dossier_response(response: str) -> tuple[str, str]:
    """
    Parst die Dossier-Response und extrahiert Key Learnings.

    Args:
        response: Volle LLM Response

    Returns:
        Tuple (dossier_text, key_learnings)
        - dossier_text: Das vollständige Dossier
        - key_learnings: Der vollständige Learning-Block
    """
    dossier_text = response
    key_learnings = ""

    # Key Learnings extrahieren (MARKER BEIBEHALTEN für Parser!)
    if "=== KEY LEARNINGS ===" in response:
        parts = response.split("=== KEY LEARNINGS ===")
        dossier_text = parts[0].strip()

        if len(parts) > 1:
            learnings_part = parts[1]
            # End-Marker finden
            if "=== END LEARNINGS ===" in learnings_part:
                key_learnings = learnings_part.split("=== END LEARNINGS ===")[0].strip()
            else:
                # Fallback: Alles nach dem Start-Marker
                key_learnings = learnings_part.strip()

    return dossier_text, key_learnings
