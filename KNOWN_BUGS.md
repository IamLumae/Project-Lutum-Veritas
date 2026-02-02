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

*Last updated: 2026-02-02*
