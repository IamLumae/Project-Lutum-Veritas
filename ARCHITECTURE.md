# Lutum Veritas - Architecture Documentation

**Version:** 1.3.0
**Last Updated:** February 2, 2026

This document explains the core research pipelines of Lutum Veritas. It's written for contributors who want to understand how the system works internally.

---

## Table of Contents

1. [Overview](#overview)
2. [Ask Mode (Deep Question)](#ask-mode-deep-question)
3. [Deep Research (Normal Mode)](#deep-research-normal-mode)
4. [Academic Mode](#academic-mode)
5. [Core Components](#core-components)
6. [Code Structure](#code-structure)

---

## Overview

Lutum Veritas uses **three distinct research pipelines**, each optimized for different use cases:

| Mode | Use Case | Duration | Output Length |
|------|----------|----------|---------------|
| **Ask Mode** | Quick verified answers | ~70-90s | 500-2,000 words |
| **Deep Research** | Comprehensive analysis | ~5-15 min | 5,000-10,000 words |
| **Academic Mode** | Scholarly research | ~20-45 min | 50,000-200,000+ chars |

All three modes share the same **core principle**:
- Real-time web search (no stale training data)
- Source verification (no hallucinations)
- Camoufox scraping (0% bot detection)

---

## Ask Mode (Deep Question)

**Goal:** Fast, verified answers with dual-scraping verification.

### Pipeline Architecture

```
User Question
    ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: ANSWER GENERATION                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  C1: Intent Evaluation                                  │
│      → Understand WHAT the user wants to know           │
│      → Detect question type (factual, comparison, etc)  │
│      → Identify language (auto-detect)                  │
│                                                          │
│  C2: Knowledge Requirements                             │
│      → Identify WHICH knowledge is needed               │
│      → List required information pieces                 │
│      → Determine depth level                            │
│                                                          │
│  C3: Search Query Formulation                           │
│      → Formulate targeted search queries                │
│      → Multiple search angles (Google, DuckDuckGo)      │
│      → Diversify information sources                    │
│                                                          │
│  Camoufox Scraping (Round 1)                            │
│      → Execute searches                                 │
│      → Scrape top results (5-10 URLs)                   │
│      → Extract text content                             │
│                                                          │
│  C4: Answer Synthesis                                   │
│      Input:                                             │
│        - User Question                                  │
│        - C1 Intent Analysis                             │
│        - C2 Knowledge Requirements                      │
│        - Scraped Results (Round 1)                      │
│      Output:                                            │
│        - Initial Answer with inline citations [1][2]    │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ PHASE 2: CLAIM VERIFICATION                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  C5: Claim Audit                                        │
│      → Analyze: Are the statements correct?             │
│      → Identify verifiable claims                       │
│      → Extract factual assertions                       │
│                                                          │
│  C6: Verification Query Formulation                     │
│      → Formulate fact-check searches                    │
│      → Target independent sources                       │
│      → Cross-reference angle                            │
│                                                          │
│  Camoufox Scraping (Round 2)                            │
│      → Execute verification searches                    │
│      → Scrape verification sources (3-7 URLs)           │
│      → Extract verification evidence                    │
│                                                          │
│  C6: Confirmation Report                                │
│      → Compare claims with verification results         │
│      → Rate confidence per claim (High/Medium/Low)      │
│      → Flag contradictions                              │
│                                                          │
└─────────────────────────────────────────────────────────┘
    ↓
Final Response
    → Answer text (with [1][2] citations for sources)
    → Verification Report (with [V1][V2] citations)
    → Source Registry (clickable URLs)
```

### Key Features

- **Dual-Scraping**: Two independent scraping rounds (answer + verification)
- **Citation System**:
  - `[1], [2]` = Sources used for answer
  - `[V1], [V2]` = Sources used for verification
- **Claim Auditing**: Every factual statement is fact-checked
- **Auto-Language**: Responds in same language as question
- **Cost**: ~$0.0024 per query (416 answers for $1)

### Code Location

- **Backend:** `lutum_backend/routes/ask.py`
- **Prompts:** `lutum_backend/deep_question_pipeline.py`
- **Frontend:** `lutum-desktop/src/components/AskSidebar.tsx`
- **State:** `lutum-desktop/src/stores/askSessions.ts`

---

## Deep Research (Normal Mode)

**Goal:** Comprehensive multi-source analysis with contextual synthesis.

### Pipeline Architecture

```
User Question
    ↓
Clarification Questions
    → Refine scope and requirements
    ↓
Research Plan
    → Generate 5-10 research points
    ↓
┌─────────────────────────────────────────────────────────┐
│ FOR EACH RESEARCH POINT:                                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Think (Search Strategy)                                │
│      → What do I need to know for this point?           │
│      → Formulate search queries (Google + DDG)          │
│      → Plan information gathering approach              │
│      Model: Gemini 2.0 Flash Lite                       │
│      Prompt: lutum/researcher/prompts/think.py          │
│                                                          │
│  Search                                                 │
│      → Execute searches on Google, DuckDuckGo           │
│      → Collect 15-30 candidate URLs                     │
│      Scraper: Camoufox (0% detection)                   │
│                                                          │
│  Pick URLs                                              │
│      → Evaluate URL quality and relevance               │
│      → Select top 5-8 sources to scrape                 │
│      → Diversify source types (academic, news, etc)     │
│      Model: Gemini 2.0 Flash Lite                       │
│      Prompt: lutum/researcher/prompts/pick_urls.py      │
│                                                          │
│  Scrape                                                 │
│      → Camoufox scrapes selected URLs                   │
│      → Extract clean text content                       │
│      → Handle paywalls, JS-heavy sites, anti-bot        │
│      Scraper: Camoufox (hardened Firefox fork)          │
│                                                          │
│  Dossier Creation                                       │
│      Input:                                             │
│        - Research Point Question                        │
│        - Think Output (search strategy)                 │
│        - Scraped Content from 5-8 sources               │
│        - CONTEXT: Previous dossiers (recursive!)        │
│      Output:                                            │
│        - Comprehensive analysis (1,500-3,000 words)     │
│        - Key learnings                                  │
│        - Source citations                               │
│      Model: Gemini 2.0 Flash Lite                       │
│      Prompt: lutum/researcher/prompts/dossier.py        │
│                                                          │
│  ** CRITICAL: Context Accumulation **                   │
│      Each dossier receives ALL previous dossiers        │
│      → Dossier 3 knows what Dossier 1 + 2 found         │
│      → Enables causal connections across topics         │
│      → No information silos                             │
│                                                          │
└─────────────────────────────────────────────────────────┘
    ↓ (Repeat for all points)
    ↓
Final Synthesis
    Input:
      - User's original question
      - Research plan
      - ALL dossiers (full context)
      - Source registry
    Output:
      - Comprehensive report (5,000-10,000 words)
      - Cross-referenced findings
      - Conclusion with key insights
    Model: Qwen 2.5 235B Instruct
    Prompt: lutum/researcher/prompts/final_synthesis.py
    ↓
Export (Markdown / PDF)
```

### Key Features

- **Context Accumulation**: Each research point builds on previous findings
- **Causal Connections**: System discovers relationships between topics
- **Source Diversity**: 20-50+ sources per research session
- **Recursive Depth**: Later dossiers are richer because they have more context
- **Cost**: ~$0.08-0.20 per research (depending on depth)

### Code Location

- **Backend:** `lutum_backend/routes/research.py`
- **Prompts:** `lutum/researcher/prompts/`
- **Orchestrator:** `lutum_backend/routes/research.py` (POST `/research/deep`)

---

## Academic Mode

**Goal:** Scholarly-grade research with hierarchical structure and meta-synthesis.

### Pipeline Architecture

```
User Question
    ↓
Clarification Questions
    → Academic focus, methodology, scope
    ↓
Academic Plan
    → Generate hierarchical structure:
      - Area 1
        └─ Point 1.1
        └─ Point 1.2
      - Area 2
        └─ Point 2.1
        └─ Point 2.2
        └─ Point 2.3
    Prompt: lutum/researcher/prompts/academic_plan.py
    ↓
┌─────────────────────────────────────────────────────────┐
│ FOR EACH RESEARCH POINT (within each area):            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Think → Search → Pick → Scrape → Dossier              │
│  (Same as Deep Research mode)                           │
│                                                          │
│  ** Context Accumulation within Area **                 │
│      Point 1.2 receives context from Point 1.1          │
│                                                          │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ FOR EACH AREA:                                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Bereichs-Synthesis (Area Synthesis)                    │
│      Input:                                             │
│        - All dossiers within this area                  │
│        - Area title and scope                           │
│      Output:                                            │
│        - Comprehensive area summary                     │
│        - Toulmin argumentation structure                │
│        - Evidence grading (Level I-VII)                 │
│        - Claim audit table with confidence ratings      │
│      Model: Qwen 2.5 235B Instruct                      │
│      Prompt: lutum/researcher/prompts/bereichs_synthesis.py │
│                                                          │
└─────────────────────────────────────────────────────────┘
    ↓
Meta-Synthesis
    Input:
      - ALL Area Syntheses
      - Original research question
    Goal:
      - Find cross-connections between areas
      - Identify emergent patterns
      - Synthesize holistic understanding
    Model: Qwen 2.5 235B Instruct
    Prompt: lutum/researcher/prompts/meta_synthesis.py
    ↓
Academic Conclusion
    Input:
      - Meta-Synthesis
      - All Area Syntheses
      - Research question
    Output:
      - Executive summary
      - Key findings
      - Methodological reflections
      - Future research directions
      - Impact statement
    Model: Qwen 2.5 235B Instruct
    Prompt: lutum/researcher/prompts/academic_conclusion.py
    ↓
Final Academic Document
    → 50,000-200,000+ characters
    → Hierarchical structure
    → Evidence-graded claims
    → Cross-referenced areas
    → Publication-ready depth
```

### Key Features

- **Hierarchical Structure**: Areas → Points → Dossiers
- **Toulmin Argumentation**: Data → Claim → Warrant → Backing
- **Evidence Grading**: Level I (Meta-Analysis) → Level VII (Expert Opinion)
- **Claim Auditing**: Confidence ratings for every assertion
- **Meta-Synthesis**: Discovers connections between research areas
- **Publication-Grade**: Suitable for academic submissions
- **Cost**: ~$0.30-0.80 per research (depending on scope)

### Code Location

- **Backend:** `lutum_backend/routes/research.py`
- **Prompts:** `lutum/researcher/prompts/academic_*.py`
- **Orchestrator:** POST `/research/academic`

---

## Core Components

### Camoufox Scraper

**What:** Hardened Firefox fork with anti-detection features.

**Why:** Bypasses:
- Cloudflare
- DataDome
- PerimeterX
- Bloomberg, TCGPlayer, most anti-bot systems

**Detection Rate:** 0%

**Code:** `lutum/scrapers/camoufox_scraper.py`

**Functions:**
```python
# Raw text (what a human sees)
camoufox_scrape_raw(url, timeout=30)

# Cleaned content (extracted)
camoufox_scrape(url, timeout=30)

# Full scraper (content + HTML)
CamoufoxScraper().scrape(url)
```

---

### LLM Provider Architecture

**Multi-Provider Support:**
- OpenRouter (200+ models)
- OpenAI
- Anthropic
- Google Gemini
- HuggingFace

**Default Model Assignment:**

| Task | Model | Why |
|------|-------|-----|
| Think | Gemini 2.0 Flash Lite | Fast, cheap, good at search strategy |
| Pick URLs | Gemini 2.0 Flash Lite | Fast evaluation of source quality |
| Dossier | Gemini 2.0 Flash Lite | Balanced analysis speed/quality |
| Synthesis | Qwen 2.5 235B Instruct | Deep reasoning, context integration |
| Ask Mode (C1-C6) | Gemini 2.5 Flash Lite | Ultra-fast, cheap for verification |

**Code:** `lutum_backend/app/core/config.py`

---

### Session Management

**Storage:** File-based JSON (no database required)

**Browser Mode:**
- localStorage in browser profile
- Sessions persist across browser restarts

**Desktop App Mode:**
- localStorage in Tauri WebView
- Sessions stored in app data directory
- Identical behavior to browser mode

**Code:**
- Frontend: `lutum-desktop/src/stores/sessions.ts`
- Backend: In-memory only (sessions not persisted server-side)

---

## Code Structure

```
lutum-veritas/
├── lutum/                          # Core Python library
│   ├── researcher/
│   │   └── prompts/                # LLM prompts for all modes
│   │       ├── think.py            # Search strategy
│   │       ├── pick_urls.py        # URL selection
│   │       ├── dossier.py          # Dossier creation
│   │       ├── final_synthesis.py  # Normal mode synthesis
│   │       ├── academic_plan.py    # Academic structure
│   │       ├── bereichs_synthesis.py # Area synthesis
│   │       ├── meta_synthesis.py   # Cross-area connections
│   │       └── academic_conclusion.py # Final academic report
│   └── scrapers/
│       └── camoufox_scraper.py     # Zero-detection web scraper
│
├── lutum_backend/                  # FastAPI server
│   ├── routes/
│   │   ├── research.py             # Deep Research + Academic endpoints
│   │   └── ask.py                  # Ask Mode endpoint
│   ├── deep_question_pipeline.py   # Ask Mode prompts (C1-C6)
│   └── app/
│       └── core/
│           └── config.py           # LLM provider configuration
│
└── lutum-desktop/                  # Tauri desktop app
    ├── src/
    │   ├── components/
    │   │   ├── ChatInterface.tsx   # Deep Research UI
    │   │   └── AskSidebar.tsx      # Ask Mode UI
    │   ├── hooks/
    │   │   └── useBackend.ts       # Backend API wrapper
    │   └── stores/
    │       ├── sessions.ts         # Deep Research sessions
    │       └── askSessions.ts      # Ask Mode sessions
    └── src-tauri/
        └── src/lib.rs              # Auto-start backend logic
```

---

## Performance Characteristics

### Ask Mode

- **Duration:** 70-90 seconds
- **API Calls:** 6 LLM calls (C1-C6) + 2 scraping rounds
- **Token Usage:** ~100k input, ~3k output
- **Cost:** $0.0024 per query
- **Sources:** 8-15 total (5-10 answer, 3-7 verification)

### Deep Research

- **Duration:** 5-15 minutes (depends on plan size)
- **API Calls:** 4 calls per point + 1 synthesis
  - 5 points = 21 calls
  - 10 points = 41 calls
- **Token Usage:** 500k-1M input, 50k-100k output
- **Cost:** $0.08-0.20
- **Sources:** 20-50+

### Academic Mode

- **Duration:** 20-45 minutes
- **API Calls:** 4 calls per point + 1 area synthesis per area + 1 meta-synthesis + 1 conclusion
  - 3 areas × 3 points each = 36 + 3 + 1 + 1 = 41 calls
- **Token Usage:** 1M-3M+ input, 100k-200k+ output
- **Cost:** $0.30-0.80
- **Sources:** 50-100+

---

## Contributor Guidelines

### What NOT to Touch (Core Logic)

**If you're contributing QOL improvements, avoid modifying:**
- `lutum/researcher/prompts/*.py` - LLM prompts (core research method)
- `lutum_backend/routes/research.py` - Research orchestration logic
- `lutum_backend/deep_question_pipeline.py` - Ask Mode pipeline
- `lutum/scrapers/camoufox_scraper.py` - Scraper core

**These are the "engine" - they work, don't break them.**

### What's Safe to Improve

**QOL contributions welcome:**
- Frontend UI/UX (`lutum-desktop/src/components/`)
- Design/colors/themes
- GitHub Actions (build automation)
- Tests
- Distribution (installers, packaging)
- Documentation
- Error handling and user feedback
- Session export formats
- Settings UI improvements

### How to Test Your Changes

**Backend:**
```bash
cd lutum_backend
uvicorn main:app --reload --port 8420
```

**Frontend:**
```bash
cd lutum-desktop
npm run tauri dev
```

**Full Build:**
```bash
cd lutum-desktop
npm run build
npm run tauri build
```

---

## Questions?

If something in this architecture is unclear:

1. Check the code at the referenced file paths
2. Open a GitHub Discussion
3. Ask in PR comments

This document will be updated as the architecture evolves.

---

**Last Updated:** February 2, 2026
**Contributors:** Martin Gehrken (@IamLumae), Ada (Claude Sonnet 4.5)
