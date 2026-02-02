# Lutum Veritas - Patch Notes

## v1.3.0 (2026-02-02)

### 🎯 NEW FEATURE: Ask Mode - Deep Question Pipeline

**Fast, Verified Answers with Dual-Scraping Verification System**

Ask Mode is a new research mode optimized for **quick, fact-checked answers** to specific questions. Unlike Deep Research (which explores topics comprehensively), Ask Mode focuses on **speed + accuracy + verification**.

#### How It Works
- **6-Stage Pipeline** (~70-90 seconds per question)
  - C1: Intent Analysis - Understands what you're asking
  - C2: Knowledge Requirements - Identifies needed information
  - C3: Search Strategy - Generates 10 targeted search queries
  - **SCRAPE Phase 1** - Parallel scraping of 10 URLs
  - C4: Answer Synthesis - Creates comprehensive answer with citations [1], [2], [3]
  - C5: Claim Audit - Identifies claims needing verification
  - **SCRAPE Phase 2** - Scrapes 10 additional verification sources
  - C6: Verification Report - Fact-checks each claim with [V1], [V2] citations

#### UI Features
- **Mode Toggle** - Switch between Deep Research ↔ Ask Mode in header
- **Separate Sidebars** - Ask sessions stored separately from Research sessions
- **Live Progress** - Real-time stage updates with scraping progress (0/10 → 10/10)
- **Citation System** - Inline citations [1], [2] for sources + [V1], [V2] for verification
- **Persistent State** - Sessions survive app restart, can switch between sessions mid-research

#### Technical Details
- **Model:** `google/gemini-2.5-flash-lite-preview-09-2025` (fast + cheap)
- **Backend:** New `/ask` routes with SSE streaming
- **Frontend:** Dual-state management (Research + Ask sessions isolated)
- **Storage:** IndexedDB persistence for both modes

#### Language Support
- Automatic language detection from user query
- Supports English, German (and other languages)
- UI translations for status messages

#### Bug Fixes
- **Critical:** Fixed Ask Mode routing bug - messages were landing in Research Mode instead of Ask Mode due to stale `useCallback` dependencies
- Added `appMode`, `askSessionsState`, `activeAskSession`, `addAskMessage`, `startAskPipeline`, `setAskSessionsState`, `language` to `handleSend` dependencies

#### Files Changed
- `lutum-backend/routes/ask.py` (new, 716 lines) - Ask Mode endpoints
- `lutum-desktop/src/components/Chat.tsx` - Dual-mode routing + state management
- `lutum-desktop/src/components/AskSidebar.tsx` (new) - Ask sessions sidebar
- `lutum-desktop/src/hooks/useAskEvents.ts` (new) - SSE hook for live updates
- `lutum-desktop/src/stores/askSessions.ts` (new) - Ask session persistence
- `deep_question_pipeline.py` (new) - Core pipeline logic

#### Known Issues
- Deep Research recovery ("Resume Session") does not work - see KNOWN_BUGS.md

---

## v1.2.6 (2026-02-01)

### Dossier Key Learnings Parser Fix

#### Key Learnings Extraction Fixed
- **Issue:** Dossiers zeigten "Keine Key Learnings" obwohl die Section im Output vorhanden war
- **Root Cause:** Parser suchte nach `## 💡 KEY LEARNINGS` (mit ##), aber LLM schrieb oft ohne ##
- **Fix:** Parser jetzt flexibler - erkennt 3 Varianten:
  1. `## 💡 KEY LEARNINGS` (mit ##)
  2. `💡 KEY LEARNINGS` (ohne ##) ← NEU
  3. `=== KEY LEARNINGS ===` (legacy)
- **Impact:** Context-Accumulation zwischen Dossiers funktioniert jetzt zuverlässiger (~55% → ~95%+ Erfolgsrate erwartet)
- **Files:** `lutum/researcher/prompts/dossier.py` (parse_dossier_response, Line 356-382)

---

## v1.2.5 (2026-02-01)

### Academic Mode Output & Persistence Fixes

#### Academic Mode Output Length Restored
- **Issue:** Academic Mode output dropped from 200k+ chars to ~48k chars
- **Root Cause:**
  - Token limits too low (16k for Area Synthesis, 32k for Conclusion)
  - Prompt rework removed Toulmin/GRADE/Falsification requirements
  - Added restrictive length limits ("2-3 paragraphs", "5-7 findings")
- **Fix:**
  - Token limits increased: Area Synthesis 16k→48k, Academic Conclusion 32k→96k
  - Re-added Toulmin Argumentation, GRADE Evidence System, Falsification Requirement, 5 Connection Types
  - Removed all length limits ("2-3 paragraphs" → "NO LENGTH LIMIT")
  - Changed "NO FILLER" to "BE COMPREHENSIVE"
  - Increased minimum findings: 5-7 → 10-15
- **Files:** `bereichs_synthesis.py`, `academic_conclusion.py`, `research.py` (lines 1856, 1919)

#### Academic Mode Backup/Persistence Added
- **Issue:** Academic Sessions created no backups, no fallbacks, no database entries
- **Root Cause:** Normal Mode had backup logic (lines 1276-1284), Academic Mode did not
- **Fix:** Added backup saving for Academic Mode final documents
  - Backups saved to: `academic_synthesis_backups/academic_YYYYMMDD_HHMMSS.md`
  - Fallbacks already existed for Area Synthesis (line 1862-1866) and Conclusion (line 1925-1926)
- **Files:** `research.py` (line ~1978)

---

## v1.2.4 (2026-01-31)

### Bug Fixes

#### Duplicate Source Display Removed
- **Issue:** Sources were displayed twice (inline "Quellenverzeichnis" + separate "Source Registry")
- **Fix:** Removed redundant `sources_registry` message - inline version in report is sufficient
- **Files:** `Chat.tsx` (lines 870-881, 1009-1020)

#### Language Race Condition Fixed
- **Issue:** UI briefly showed German despite English settings
- **Root Cause:** `useState<Language>('de')` initialized before settings loaded
- **Fix:** Initialize state directly from settings: `useState(() => loadSettings().language)`
- **Files:** `Chat.tsx` (line 47)

#### Session Title Internationalized
- **Issue:** "Neue Recherche" was hardcoded German
- **Fix:** Use `t('newResearch', lang)` from translations
- **Files:** `sessions.ts` (createSession function)

#### Backend Offline Flicker Fixed
- **Issue:** "Offline" status appeared briefly after each dossier
- **Root Cause:** Health check ran during heavy rendering/processing
- **Fix:** Skip health checks when `loading === true`
- **Files:** `Chat.tsx` (health check useEffect)

#### Dossier Language Enforcement Strengthened
- **Issue:** One dossier output was German despite English query (source language bleed)
- **Fix:** Enhanced prompt: "Output MUST be in USER QUERY language, IGNORE source language"
- **Files:** `lutum/researcher/prompts/dossier.py`

### Multi-Provider API Support Fixed
- **Issue:** Google Gemini returned truncated responses (3 URLs instead of 10)
- **Root Cause:** All providers used OpenAI format; Gemini needed `temperature: 0.3`
- **Fix:** Provider-aware request building with proper parameters
- **Files:** `lutum/core/llm_client.py`

---

## v1.2.3 (2026-01-30)

### Language Detection Fix

**Root Cause Found & Fixed**
- `context_state.py` had German headers (`=== DEINE AUFGABE ===`, `=== RÜCKFRAGEN ===`)
- These were prepended to every LLM call, causing German responses
- Fix: All headers changed to English (`=== YOUR TASK ===`, `=== FOLLOW-UP QUESTIONS ===`)

**Additional Prompt Fixes:**
- `clarify.py`, `plan.py`, `overview.py`, `search.py` fully converted to English
- Every prompt ends with: `CRITICAL: Respond in SAME LANGUAGE as user query`

### UI Redesign - Techno/Cyber Theme

**Loading Indicator (Complete Redesign):**
- Replaced Mac-Terminal dots with Cyber-Style
- Blue glow border with scan-line animation
- Animated hex icon with ping effect
- Gradient progress bar
- Orange `>` prompt character

**Log Messages (Warnings/Errors):**
- Gradient backgrounds instead of flat colors
- Pulsing glow effects
- Animated status dot
- Labels: "System Error" / "System Notice"

**Message Boxes:**
- User: Enhanced blue gradient with glow shadow
- Assistant: Subtle corner accents (blue top-left, orange bottom-right)

**CSS Animations Added:**
- `scan` - Scan-line effect (top-to-bottom)
- `progress` - Shimmer progress bar
- `glow-pulse` - Border glow
- `cursor-blink` - Typing cursor
- `hex-rotate` - Icon rotation

### URL Picker Fix

- **Issue:** LLM picked only 3 URLs instead of 10
- **Root Cause:** Prompt said "max 10" which LLM interpreted as optional
- **Fix:** Changed to "EXACTLY 10 URLs. Not 3, not 5 - exactly 10!"
- Added mandatory mix: 2-3 Official + 2-3 Community + 2-3 Reviews + 2-3 Technical

---

## v1.2.2 (2026-01-30)

### Internationalization (i18n) Complete

**Multi-Language Support for Research Output**
- All 8 LLM prompts translated from German to English
- Prompts now include: "Respond in the same language as the user's query"
- User query correctly passed to all prompts for automatic language detection
- Affected files:
  - `think.py` - Search Strategy Prompt
  - `dossier.py` - Dossier Creation Prompt
  - `final_synthesis.py` - Final Report Prompt
  - `pick_urls.py` - URL Selection Prompt
  - `meta_synthesis.py` - Meta-Synthesis Prompt
  - `academic_conclusion.py` - Academic Conclusion Prompt
  - `bereichs_synthesis.py` - Area Synthesis Prompt
  - `academic_plan.py` - Academic Plan Prompt

**Status Messages i18n**
- Added `language` parameter to `runDeepResearch` and `runAcademicResearch`
- Status messages now display in app language (DE/EN)

### Multi-Provider Support

**5 API Providers Available**
- OpenRouter (Default) - Model dropdown with 200+ models
- OpenAI - GPT-4, GPT-4o, etc.
- Anthropic - Claude 3.5, Claude 3 Opus, etc.
- Google Gemini - Gemini Pro, Gemini Flash, etc.
- HuggingFace - Open-source models

**UI Changes:**
- Provider dropdown in Settings
- For OpenRouter: Model dropdowns with search
- For other providers: Manual model input (text fields)
- API Key placeholder adapts to provider

**Backend:**
- `base_url` parameter for all research endpoints
- Dynamic API URL instead of hardcoded OpenRouter

### Bug Fixes

**PDF Export: Markdown Tables Fixed**
- Issue: Tables rendered vertically instead of horizontally
- Cause: Faulty `parseRow()` filter logic and strict table detection
- Fix: Table detection now checks header + separator line with `-`

**"Think failed" Without Error Log Fixed**
- Issue: Empty LLM responses showed "Think failed" without logging
- Fix: Added detailed logging with finish_reason, refusal, and model info

---

## v1.2.1 (2026-01-29)

- Initial public release
- Deep Research Pipeline
- Academic Mode with parallel area research
- Camoufox Scraper (0% bot detection)
- PDF Export
- OpenRouter Integration
