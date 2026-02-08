# Known Bugs - Lutum Veritas

## Desktop App (lutum-desktop)

### PDF Export Formatting
**Status:** Open
**Description:** PDF export has formatting issues - layout/styling doesn't match the in-app rendering.
**Workaround:** Use Markdown export instead, then convert to PDF with external tool if needed.

---

### Deep Research Session Recovery
**Status:** Open
**Description:** When closing the app mid-research and reopening, the "Resume Session" button appears with message "🔄 Session found: X/Y dossiers complete. Resuming..." but the pipeline does not actually resume - nothing happens.
**Impact:** User must restart research from scratch.
**Workaround:** Don't close the app during Deep Research. Use Ask Mode for quick questions that can be interrupted.
**Files:** `useBackend.ts` (resumeSession), `research.py` (resume endpoint)

---

### Academic Mode Falls Back to Normal Mode After Plan Revision
**Status:** Open
**Description:** When Academic Mode is toggled ON and the user revises the research plan (e.g. "change point 3"), the `/research/plan/revise` endpoint does not preserve the `academic_bereiche` structure. It returns a flat `plan_points` list instead, overwriting the context state. When "Los geht's" is clicked, the frontend check `ctx.academic_bereiche` finds nothing and falls through to Normal Deep Research instead of Academic Research.
**Root Cause:** `PlanReviseRequest` has no `academic_mode` field. `research_plan_revise()` always calls `revise_research_plan()` which returns flat points. The hierarchical `academic_bereiche` from the original plan creation is destroyed.
**Impact:** Academic Mode is effectively broken whenever the user edits the plan. Only works if the plan is accepted without any revision.
**Workaround:** Accept the initial Academic plan without requesting changes. Do not revise/edit the plan when Academic Mode is active.
**Files:** `research.py:604-661` (revise endpoint), `Chat.tsx:1176` (academic check)
**Fix needed:**
1. Add `academic_mode` field to `PlanReviseRequest`
2. When `academic_mode=true`, call `create_academic_plan` with updated context instead of `revise_research_plan`
3. Return `academic_bereiche` in the revise response

---

### Negative or Zero Source Citation Numbers in Dossiers
**Status:** Open (cosmetic)
**Description:** In Deep Research dossiers, the "Best Sources" section sometimes shows negative or zero citation numbers like `[-1]`, `[0]`, `[-10]` instead of proper positive references like `[1]`, `[2]`, `[3]`. The actual source content (URLs, descriptions) is still present — only the numbering is wrong.
**Impact:** Cosmetic only. The research results and final synthesis are not affected. The sources are correctly used in the analysis, just incorrectly numbered in the per-point dossier display.
**Workaround:** None needed. Ignore the citation numbers in individual dossiers — the final synthesis generates its own correct source registry.

---

## Expected Behavior (Not Bugs)

### Occasional Search Timeouts
Individual DuckDuckGo searches may timeout (`ConnectTimeout`). This is normal — the pipeline runs multiple search queries per research point and continues with whatever results it gets. A single timed-out query does not affect the overall research quality. No action needed.

### Dead URLs During Scraping
Errors like `NS_ERROR_UNKNOWN_HOST` or `Page.goto failed` during scraping mean a URL returned by the search engine no longer exists or the server is unreachable. This is expected — the internet changes constantly. The scraper skips dead URLs and continues with the remaining sources.

### Minor LLM Formatting Deviations
The AI models occasionally deviate from the exact requested output format (e.g. slightly different section headers, missing separators, inconsistent bullet styles). This does not affect research results — the parsing is robust enough to handle variations. The content and analysis quality remain unaffected.

---

*Last updated: 2026-02-08*
