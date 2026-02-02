# Known Bugs - Lutum Veritas

## Research Pipeline (lutum-backend)

### Key Learnings Extraction Inconsistent
**Status:** Fixed (v1.2.6)
**Description:** Dossiers extrahierten manchmal NICHT die "For Next Steps" Key Learnings, obwohl das Dossier sie enthielt. Frontend zeigte "Keine Key Learnings".
**Root Cause:** Parser suchte nach `## 💡 KEY LEARNINGS` (mit ##), aber LLM schrieb oft `💡 KEY LEARNINGS` (ohne ##) → Parser fand die Section nicht.
**Fix:** Parser jetzt flexibler - sucht erst mit ##, dann ohne ##, dann alte Format (=== KEY LEARNINGS ===). Alle 3 Varianten werden erkannt.
**Impact Before Fix:** Context-Accumulation zwischen Dossiers funktionierte bei ~45% der Fälle nicht (6/11 Erfolgsrate).
**Files:** `lutum/researcher/prompts/dossier.py` (parse_dossier_response)
**Reference:** Screenshots zeigten Parser-Miss trotz vorhandener Section

---

## Desktop App (lutum-desktop)

### Windows Desktop Shortcut Icon
**Status:** Won't Fix (for now)
**Description:** The desktop shortcut icon shows the default Tauri icon instead of the LV logo. This is a known Tauri/NSIS issue.
**Workaround:** The taskbar icon displays correctly. Only the desktop shortcut is affected.
**Reference:** https://github.com/tauri-apps/tauri/issues/8453

---

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

## Recently Fixed

### Academic Mode Output & Persistence
**Status:** Fixed (v1.2.5)
**Description:** Academic Mode produced only 48k chars instead of 200k+, and created no backups/sessions.
**Fix:** Token limits increased (48k/96k), Toulmin/GRADE/Falsification re-added, backup logic implemented.
**Reference:** See PATCH_NOTES.md v1.2.5

---

*Last updated: 2026-02-02*
