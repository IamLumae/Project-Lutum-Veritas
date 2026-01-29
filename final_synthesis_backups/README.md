# Veritas Research - Synthesis Backups

**Automatisch gespeicherte Deep Research Dokumente**

Jede Deep Research wird hier als Markdown-File gesichert:
- Format: `synthesis_YYYYMMDD_HHMMSS.md`
- Enthält: Original-Markdown mit vollständiger Formatierung
- Erstellt von: `lutum-backend/routes/research.py` Zeile 950-958

**Falls Backup fehlt:**
- Backend muss online sein (Port 8420)
- `/research/deep` Endpoint muss aufgerufen werden
- `final_document` darf nicht None sein

**Recovery:**
- GET `/latest-synthesis` holt neuestes Backup
- Desktop-App nutzt das bei unterbrochener SSE-Verbindung
