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

*Last updated: 2026-01-30*
