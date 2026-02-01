# Known Bugs - Lutum Veritas

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

## Recently Fixed

### Academic Mode Output & Persistence
**Status:** Fixed (v1.2.5)
**Description:** Academic Mode produced only 48k chars instead of 200k+, and created no backups/sessions.
**Fix:** Token limits increased (48k/96k), Toulmin/GRADE/Falsification re-added, backup logic implemented.
**Reference:** See PATCH_NOTES.md v1.2.5

---

*Last updated: 2026-02-01*
