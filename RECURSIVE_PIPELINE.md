# Deep Research Pipeline - Komplett Dokumentation

> Stand: 2026-01-27 | Status: IMPLEMENTIERT

---

## Übersicht

Lutum Veritas führt **echte Deep Research** durch - nicht das oberflächliche "ich google mal kurz" anderer Tools.

**USP:** "Real research takes time. We don't hallucinate in milliseconds."

---

## Architektur

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐  │
│  │ Query Input │→ │ Plan Review  │→ │ Deep Research (Live View)  │  │
│  │             │  │ "Los geht's" │  │ - Sources Boxes            │  │
│  │             │  │              │  │ - Point Summaries          │  │
│  │             │  │              │  │ - Terminal Status          │  │
│  └─────────────┘  └──────────────┘  └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND ORCHESTRATOR                            │
│                      /research/deep (SSE)                            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   PRO RECHERCHE-PUNKT                        │    │
│  │                                                              │    │
│  │  Think → Search → Pick URLs → Scrape → Dossier → Learnings  │    │
│  │    │                                                    │    │    │
│  │    └──────────── Context-Pass (Learnings) ──────────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              FINAL SYNTHESIS (Qwen 235B)                     │    │
│  │         Alle Dossiers → Gesamtdokument (10+ min)            │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Die Pipeline im Detail

### Phase 1: Setup (Steps 1-4)

| Step | Was passiert | Output |
|------|--------------|--------|
| 1 | User Query → LLM | 10 DDG Queries + Session-Titel |
| 2 | DDG Search | URLs + Snippets |
| 3 | LLM liest gescrapte Seiten | Rückfragen an User |
| 4 | User-Antworten → LLM | Recherche-Plan (5-10 Punkte) |

**User entscheidet:** "Los geht's" oder "Plan bearbeiten"

---

### Phase 2: Deep Research Loop (Step 5)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEEP RESEARCH LOOP                                │
│                                                                      │
│  Für jeden Punkt im Plan:                                           │
│                                                                      │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │ A) THINK (Diversifiziert)                                  │    │
│   │    Input:  user_query + current_point + previous_learnings │    │
│   │    Output: thinking_block + 10 search_queries              │    │
│   │    Kategorien: 2x Primär, 2x Community, 2x Praktisch,      │    │
│   │                2x Kritisch, 2x Aktuell                     │    │
│   │    Model:  gemini-2.5-flash-lite (60s timeout)             │    │
│   └──────────────────────┬─────────────────────────────────────┘    │
│                          ▼                                           │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │ B) DDG SEARCH                                               │    │
│   │    10 Queries → DuckDuckGo (ddgs lib) → 20 results/query   │    │
│   │    = max 200 potenzielle URLs                              │    │
│   └──────────────────────┬─────────────────────────────────────┘    │
│                          ▼                                           │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │ C) PICK URLS (Diversifiziert)                               │    │
│   │    LLM wählt EXAKT 20 URLs mit Quellen-Mix:                │    │
│   │    6-8x Primär, 4-5x Community, 3-4x Praktisch,            │    │
│   │    2-3x Kritisch, 2-3x Aktuell                             │    │
│   │    + Query-Awareness + Previous Learnings Kontext          │    │
│   │    → SSE Event: "sources" (zeigt Quellen-Box im Chat)      │    │
│   └──────────────────────┬─────────────────────────────────────┘    │
│                          ▼                                           │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │ D) SCRAPE URLS (parallel)                                   │    │
│   │    Camoufox holt Content (max 10.000 Zeichen/Seite)        │    │
│   └──────────────────────┬─────────────────────────────────────┘    │
│                          ▼                                           │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │ E) DOSSIER ERSTELLEN                                        │    │
│   │    4 Phasen im Prompt:                                     │    │
│   │    1. Wissen generieren (Fakten, Zusammenhänge)            │    │
│   │    2. Dossier schreiben (Struktur, Analyse, Quellen)       │    │
│   │    3. Selbst-Prüfung (Checkliste)                          │    │
│   │    4. Key Learnings (max 1000 Zeichen für Context-Pass)    │    │
│   │    Model: gemini-2.5-flash-lite (120s timeout)             │    │
│   └──────────────────────┬─────────────────────────────────────┘    │
│                          ▼                                           │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │ F) SAVE + EMIT                                              │    │
│   │    - Dossier speichern                                     │    │
│   │    - Key Learnings akkumulieren                            │    │
│   │    → SSE Event: "point_complete" (zeigt Summary im Chat)   │    │
│   └──────────────────────┬─────────────────────────────────────┘    │
│                          ▼                                           │
│              Nächster Punkt (oder → Final Synthesis)                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Diversifizierung (Der "Echo-Chamber-Fix")

**Problem:** Ohne Steuerung findet man 15x GitHub und 0x Reddit/Papers.

**Lösung:** Beide Schritte erzwingen Vielfalt:

**1. Think-Prompt (Query-Erstellung):**
```
10 Queries in 5 Kategorien:
- search 1-2 (Primär): Offizielle Docs, GitHub, Papers
- search 3-4 (Community): Reddit, HN, Foren
- search 5-6 (Praktisch): Tutorials, Guides, Examples
- search 7-8 (Kritisch): Limitations, Alternatives
- search 9-10 (Aktuell): News 2024/2025, Trends
```

**2. Pick-URLs-Prompt (URL-Auswahl):**
```
EXAKT 20 URLs mit Quellen-Mix:
- 6-8x Primär: GitHub, ArXiv, Docs
- 4-5x Community: Reddit, HN, SO
- 3-4x Praktisch: Tutorials, Blogs
- 2-3x Kritisch: Benchmarks, Vergleiche
- 2-3x Aktuell: News, Releases

+ Query-Awareness: Passt Auswahl an Auftragsart an
+ Previous Learnings: Priorisiert NEUE Infos, keine Duplikate
```

---

### Context-Pass (Der "Amnesie-Fix")

**Problem:** Jeder Punkt läuft isoliert (Token-Limit). Punkt 3 weiß nicht was Punkt 1 gefunden hat.

**Lösung:** Key Learnings (max 1000 Zeichen) werden akkumuliert:

```
Punkt 1: Recherche → Dossier → Key Learnings extrahieren
         ↓
Punkt 2: bekommt Learnings von 1 → "Das weißt du schon, suche nicht danach"
         ↓
Punkt 3: bekommt Learnings von 1+2 → ...
         ↓
Final:   bekommt ALLE vollständigen Dossiers
```

**Key Learnings Format:**
```
=== KEY LEARNINGS ===
**Erkenntnisse:**
- Haupterkenntnis 1
- Haupterkenntnis 2
- Haupterkenntnis 3

**Beste Quellen:**
- URL 1 - Warum wertvoll
- URL 2 - Warum wertvoll

**Für nächste Schritte relevant:**
Ein Satz was nachfolgende Punkte beachten sollten.
=== END LEARNINGS ===
```

---

### Phase 3: Final Synthesis

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FINAL SYNTHESIS                                 │
│                                                                      │
│  Input:                                                             │
│  - user_query (ursprüngliche Aufgabe)                               │
│  - research_plan (alle Punkte)                                      │
│  - all_dossiers (vollständige Dossiers, nicht nur Learnings)        │
│                                                                      │
│  Prompt (3 Phasen):                                                 │
│  1. META-ANALYSE                                                    │
│     - Querverbindungen zwischen Dossiers                            │
│     - Widersprüche identifizieren                                   │
│     - Übergreifende Muster                                          │
│     - Synthese-Erkenntnisse (was wird erst durch Kombination klar?) │
│                                                                      │
│  2. DOKUMENT SCHREIBEN                                              │
│     - Executive Summary                                             │
│     - Hauptteil (nach THEMEN, nicht nach Dossiers)                  │
│     - Synthese (Querverbindungen, neue Erkenntnisse)                │
│     - Kritische Würdigung                                           │
│     - Handlungsempfehlungen                                         │
│     - Quellenverzeichnis (dedupliziert)                             │
│                                                                      │
│  3. QUALITÄTSPRÜFUNG                                                │
│     - Beantwortet ursprüngliche Aufgabe?                            │
│     - Echte Synthese oder nur Zusammenfassung?                      │
│     - Redundanzen eliminiert?                                       │
│     - Min. 3000 Wörter?                                             │
│                                                                      │
│  Model:   qwen/qwen3-vl-235b-a22b-instruct                          │
│  Timeout: 600 Sekunden (10 Minuten!)                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## SSE Events (Backend → Frontend)

| Event Type | Payload | UI Aktion |
|------------|---------|-----------|
| `status` | `{message: "..."}` | Terminal-Status aktualisieren |
| `sources` | `{urls: [...], message: "..."}` | Quellen-Box hinzufügen |
| `point_complete` | `{point_title, point_number, total_points, key_learnings}` | Point-Summary-Box hinzufügen |
| `done` | `{final_document, total_points, total_sources, duration_seconds}` | Finales Dokument anzeigen |
| `error` | `{message: "..."}` | Fehlermeldung |

---

## UI Komponenten

### 1. Terminal-Status (während Recherche läuft)

```
┌─────────────────────────────────────────┐
│ ● ● ●  deep-research                    │
├─────────────────────────────────────────┤
│ ⚙ $ [2/5] Durchsuche Google... ▋       │
│ ● ● ● Verarbeite Daten...               │
└─────────────────────────────────────────┘
```

### 2. Sources Box (aufklappbar)

```
┌─────────────────────────────────────────┐
│ 📚 Genutzte Quellen (8)              ▼  │
├─────────────────────────────────────────┤
│ 🔗 github.com                           │
│    https://github.com/example/repo      │
│ 🔗 arxiv.org                            │
│    https://arxiv.org/abs/2024.xxxxx     │
│ ...                                     │
└─────────────────────────────────────────┘
```

### 3. Point Summary Box (nach jedem Punkt)

```
┌─────────────────────────────────────────┐
│ ✓ Punkt 2/5 abgeschlossen        40%   │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
├─────────────────────────────────────────┤
│ RAG Architekturen und Best Practices    │
├─────────────────────────────────────────┤
│ **Erkenntnisse:**                       │
│ - Modular RAG übertrifft Naive RAG     │
│ - Hybrid Search (BM25 + Dense) optimal │
│ - Re-Ranking essentiell für Präzision  │
│                                         │
│ **Beste Quellen:**                      │
│ - arxiv.org - Comprehensive RAG Survey  │
│ - github.com - llamaindex examples      │
└─────────────────────────────────────────┘
```

---

## Modell-Konfiguration

| Prompt | Modell | Timeout | Zweck |
|--------|--------|---------|-------|
| Think | gemini-2.5-flash-lite | 60s | Suchstrategie entwickeln |
| Pick URLs | gemini-2.5-flash-lite | 60s | Beste URLs auswählen |
| Dossier | gemini-2.5-flash-lite | 120s | Punkt-Dossier erstellen |
| **Final Synthesis** | qwen/qwen3-vl-235b-a22b-instruct | **600s** | Gesamtdokument |

**Warum zwei Modelle?**
- **Flash Lite:** Schnell, günstig, gut für strukturierte Tasks
- **Qwen 235B:** Riesiger Context (alle Dossiers), maximale Qualität für Final

---

## Dateien

```
lutum/researcher/prompts/
├── __init__.py          # Exports
├── think.py             # Suchstrategie (+ previous_learnings)
├── pick_urls.py         # URL-Auswahl
├── dossier.py           # Dossier + Key Learnings Parser
└── final_synthesis.py   # Finale Synthese (Qwen, 600s)

lutum-backend/routes/
└── research.py          # /research/deep Orchestrator

lutum-desktop/src/
├── stores/sessions.ts   # Message Types (point_summary)
├── hooks/useBackend.ts  # runDeepResearch()
└── components/
    ├── Chat.tsx         # handleStartResearch()
    └── MessageList.tsx  # PointSummaryBox, Terminal-Status
```

---

## Kosten & Zeit Schätzung

| Modus | Dauer | API-Kosten | Output |
|-------|-------|------------|--------|
| Standard (5 Punkte) | 5-15 min | ~$0.50-1.00 | Detaillierter Bericht |
| Umfangreich (10 Punkte) | 15-30 min | ~$1.00-3.00 | Fachbuch-Niveau |

---

## Retry-Loop (Sackgassen-Handler)

Wenn bei einem Punkt weniger als 2 URLs gefunden werden:

```
1. Erkennung: len(selected_urls) < 2
2. Reformulierung: LLM generiert 5 alternative Suchanfragen
   - Andere Keywords
   - Andere Perspektiven (tutorial statt docs)
   - Spezifischer oder allgemeiner
3. Retry: Neue Suchen ausführen
4. Merge: Neue Results zu den alten hinzufügen
5. Pick URLs nochmal mit erweitertem Pool
```

Verhindert leere Dossiers bei schwierigen Recherche-Punkten.

---

## Nächste Schritte (TODO)

- [x] ~~Retry-Loop bei Sackgassen~~ ✓ Implementiert
- [ ] Modus-Auswahl UI (Standard vs. Akademisch)
- [ ] Export-Funktionen (PDF, Markdown)
- [ ] Akademischer Modus (rekursive Tiefe pro Punkt)
- [ ] Progress-Persistence (Recherche nach Browser-Restart fortsetzen)

---

*Erstellt: 2026-01-27*
*Letztes Update: 2026-01-27 - DDG Search, 10 diversifizierte Queries, 20 diversifizierte URLs/Pick*
