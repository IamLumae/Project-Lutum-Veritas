# LUTUM VERITAS - Brainstorm

> "Wahrheit aus dem Schlamm" - Proprietäre Deep Research Engine

---

## Vision

Eine Deep Research Engine die unabhängig von Perplexity, OpenAI Deep Research, etc. ist.
User bringt eigenen API Key → zahlt nur API-Kosten → kein Abo, kein Middleman.

**USP:** "Real research takes time. We don't hallucinate in milliseconds."

---

## Status: VOLL FUNKTIONSFÄHIG

| Komponente | Status | Beschreibung |
|------------|--------|--------------|
| **Scraper** | ✅ DONE | Camoufox (John Wick - 0% Detection) |
| **Analyzer** | ✅ DONE | LLM-Pipeline mit 4 Modi |
| **Search** | ✅ DONE | DuckDuckGo (ddgs library, kein Browser) |
| **Pipeline Step 1** | ✅ DONE | User Query → LLM → 10 Search Queries + Session-Titel |
| **Pipeline Step 2** | ✅ DONE | Queries → DDG Search → LLM pickt 20 URLs (diversifiziert) |
| **Pipeline Step 3** | ✅ DONE | URLs scrapen (parallel) → LLM stellt Rückfragen |
| **Pipeline Step 4** | ✅ DONE | User antwortet → LLM erstellt Recherche-Plan |
| **Pipeline Step 5** | ✅ DONE | Deep Research Loop (pro Punkt: Think→Search→Scrape→Dossier) |
| **Final Synthesis** | ✅ DONE | Qwen 235B kombiniert alle Dossiers (10min timeout) |
| **Context-Pass** | ✅ DONE | Key Learnings werden an nachfolgende Punkte weitergegeben |
| **Retry-Loop** | ✅ DONE | Bei <2 URLs → Queries reformulieren |
| **UI (Tauri)** | ✅ DONE | Desktop App mit Live-View |
| **MCP Tool** | ✅ DONE | `web_search(url, query)` in `mcp_iris_memory.py` |

---

## Core Flow

```
User Frage
    ↓
Step 1-3: Übersicht + Rückfragen
    ↓
Step 4: Recherche-Plan erstellen
    ↓
User: "Los geht's"
    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DEEP RESEARCH LOOP (Step 5)                   │
│                                                                  │
│  Für jeden Punkt im Plan:                                       │
│                                                                  │
│    Think (10 Queries, 5 Kategorien)                             │
│      → DDG Search (20 results/query)                            │
│      → Pick URLs (EXAKT 20, diversifiziert)                     │
│      → Scrape → Dossier → Learnings                             │
│      ↑                                                     │    │
│      └─────────── Context-Pass (Learnings) ────────────────┘    │
│                                                                  │
│  [Live im Chat: Sources-Boxen + Point-Summaries]                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
    ↓
Final Synthesis (Qwen 235B, bis 10 min)
    ↓
Finales Dokument (3000+ Wörter, echte Synthese)
```

---

## UI Features (Tauri Desktop App)

| Feature | Status | Beschreibung |
|---------|--------|--------------|
| Session Management | ✅ | Erstellen, Löschen, Umbenennen (Rechtsklick) |
| Persistenter State | ✅ | Phase + ContextState bleiben nach App-Neustart |
| Markdown Rendering | ✅ | react-markdown + remark-gfm |
| Quellen-Box | ✅ | Aufklappbar, klickbare Links → Browser |
| Timer | ✅ | MM:SS während Recherche |
| Terminal-Status | ✅ | macOS-Style Terminal mit Live-Status |
| Point-Summaries | ✅ | Grüne Box mit Progress + Key Learnings |
| Plan-Buttons | ✅ | "Los geht's" / "Plan bearbeiten" |
| Dark Mode | ✅ | System-Theme Support |

### "Don't hide the sweat" UI

Während der Recherche sieht der User alles was passiert:
- Terminal-Status mit blinkender Cursor
- Sources-Boxen nach jedem URL-Scrape
- Point-Summary-Boxen nach jedem abgeschlossenen Punkt
- Progress-Bar (X/Y Punkte, %)

---

## Technische Details

### Scraper (5 Stufen)
```
Stufe 1: SimpleScraper      - httpx + trafilatura (schnell)
Stufe 2: StealthScraper     - curl_cffi TLS Bypass
Stufe 3: PatchrightScraper  - Undetected Playwright
Stufe 4: ZendriverScraper   - CDP Bypass
Stufe 5: CamoufoxScraper    - Firefox C++ Fork, 0% Detection ← JOHN WICK
```

**Getestet gegen:**
- moxfield.com (Cloudflare) → ✅ 8,455 chars
- bloomberg.com (Heavy Protection) → ✅ 3,881 chars
- tcgplayer.com (JS Required) → ✅ 4,496 chars
- dev.thelastrag.de (Cloudflare) → ✅ 5,076 chars

### Search Engine (DDG)
```
DuckDuckGo Search via ddgs Library:
- Kein Browser/Scraper nötig
- Stabil, schnell, keine Rate-Limits
- 20 Results pro Query
- 10 Queries pro Dossier-Punkt
- = 200 potenzielle URLs pro Punkt
```

### Query Diversifizierung (5 Kategorien)
```
Pro Punkt 10 Queries in 5 Kategorien:
- 2x Primär: Offizielle Docs, GitHub, Papers
- 2x Community: Reddit, HN, Foren
- 2x Praktisch: Tutorials, Guides, Examples
- 2x Kritisch: Limitations, Problems, Alternatives
- 2x Aktuell: News 2024/2025, Latest, Trends
```

### URL-Auswahl (Diversifiziert)
```
LLM wählt EXAKT 20 URLs mit Quellen-Mix:
- 6-8x Primär: GitHub, ArXiv, Docs
- 4-5x Community: Reddit, HN, SO
- 3-4x Praktisch: Tutorials, Blogs
- 2-3x Kritisch: Benchmarks, Vergleiche
- 2-3x Aktuell: News, Releases
```

### Modell-Konfiguration
| Prompt | Modell | Timeout |
|--------|--------|---------|
| Think | gemini-2.5-flash-lite | 60s |
| Pick URLs | gemini-2.5-flash-lite | 60s |
| Dossier | gemini-2.5-flash-lite | 120s |
| Final Synthesis | qwen/qwen3-vl-235b-a22b-instruct | 600s |

---

## USP vs. Konkurrenz

| Feature | Perplexity | OpenAI Deep | Lutum Veritas |
|---------|------------|-------------|---------------|
| Kosten | $20/mo Abo | $200/mo Abo | API-Kosten only |
| Daten | Deren Server | Deren Server | Lokal |
| Kontrolle | Keine | Keine | Volle |
| Iterationen | Begrenzt | Begrenzt | Unbegrenzt |
| Anti-Bot Bypass | Schwach | Schwach | Camoufox (0%) |
| Live-View | Nein | Minimal | Volle Transparenz |
| Anpassbar | Nein | Nein | Ja |

---

## Kosten-Vergleich (Echter Benchmark)

**Test-Session:** 513,746 Input Tokens / 55,510 Output Tokens (2 Dossiers + Final Synthesis)

| Anbieter | Kosten | Faktor vs. Lutum |
|----------|--------|------------------|
| OpenAI o3-deep-research | $7.36 | **92x teurer** |
| Perplexity Sonar Deep | ~$2-3 | **25-37x teurer** |
| Google Deep Research | ~$2-3 | **25-37x teurer** |
| OpenAI o4-mini-deep | $1.47 | **18x teurer** |
| **Lutum Veritas** | **$0.08** | **Baseline** |

### Rechnung (transparent)

**Lutum Veritas:**
- Gemini 2.5 Flash Lite (32 Calls): $0.068
- Qwen3 235B (Final Synthesis): $0.012
- **Total: $0.08** (8 Cent!)

**OpenAI o3-deep-research:** ($10/M input, $40/M output)
- Input: 513,746 × $10/M = $5.14
- Output: 55,510 × $40/M = $2.22
- Total: $7.36

**OpenAI o4-mini-deep:** ($2/M input, $8/M output)
- Input: 513,746 × $2/M = $1.03
- Output: 55,510 × $8/M = $0.44
- Total: $1.47

**Perplexity Sonar Deep:** ($2/M input, $8/M output + Citations + Reasoning + Search)
- Basis: $1.47
- Plus Extras: ~$1-2
- Total: ~$2-3

### Warum so günstig?

1. **Kein Middleman** - Direkt zu OpenRouter, kein Aufschlag
2. **Smartes Model-Routing** - Flash Lite für Tasks, 235B nur für Final
3. **Eigene Infrastruktur** - Camoufox lokal, keine Cloud-Scraper-Kosten
4. **Keine Token-Verschwendung** - Context-Pass statt Full-Context

---

## Files

```
Project Lutum Veritas/
├── lutum/
│   ├── core/
│   │   └── logging.py
│   ├── researcher/
│   │   ├── overview.py          # Step 1
│   │   ├── search.py            # Step 2 (DDG Search)
│   │   ├── clarify.py           # Step 3
│   │   ├── plan.py              # Step 4
│   │   ├── context_state.py
│   │   ├── pipeline.py          # Step 1-3 Orchestrator
│   │   └── prompts/             # Step 5 Prompts
│   │       ├── think.py         # 10 Queries, 5 Kategorien Diversifizierung
│   │       ├── pick_urls.py     # 20 URLs, Quellen-Mix + Query-Awareness
│   │       ├── dossier.py       # Dossier + Key Learnings
│   │       └── final_synthesis.py  # Qwen 235B
│   ├── scrapers/
│   │   └── camoufox_scraper.py  # John Wick
│   └── analyzer/
│       └── web_analyzer.py
├── lutum-backend/
│   ├── main.py                  # FastAPI Server
│   └── routes/
│       └── research.py          # /research/deep (Step 5 Orchestrator)
├── lutum-desktop/               # Tauri Desktop App
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.tsx         # handleStartResearch()
│   │   │   ├── MessageList.tsx  # PointSummaryBox, Terminal-Status
│   │   │   └── ...
│   │   ├── hooks/
│   │   │   └── useBackend.ts    # runDeepResearch()
│   │   └── stores/
│   │       └── sessions.ts      # point_summary Message Type
│   └── src-tauri/
├── dist/
│   ├── lutum-backend.exe        # Backend (PyInstaller)
│   └── LutumVeritas-Frontend-Setup.exe  # Installer v1.1.0
├── BRAINSTORM.md                # Diese Datei
├── RECURSIVE_PIPELINE.md        # Detaillierte Pipeline-Doku
└── CODE_LAWS.md
```

---

## TODO

- [ ] Modus-Auswahl UI (Standard vs. Akademisch)
- [ ] Export-Funktionen (PDF, Markdown Download)
- [ ] Akademischer Modus (rekursive Tiefe pro Punkt)
- [ ] Progress-Persistence (Recherche nach Browser-Restart fortsetzen)
- [ ] Raw HTML Scrape Option
- [ ] Screenshot Scrape für visuelle Analyse

---

*Erstellt: 2026-01-26*
*Letztes Update: 2026-01-27 - DDG Search, 10 Queries/Punkt, 20 URLs/Pick, 5-Kategorien Diversifizierung*
