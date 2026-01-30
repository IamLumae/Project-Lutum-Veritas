# Lutum Veritas - Patch Notes

## v1.2.2 (2026-01-30)

### 🌍 Internationalization (i18n) Complete

**Multi-Language Support für Research Output**
- Alle 8 LLM-Prompts von Deutsch auf Englisch übersetzt
- Prompts enthalten jetzt klare Anweisung: "Respond in the same language as the user's query"
- User-Query wird in allen Prompts korrekt übergeben → LLM erkennt Sprache automatisch
- Betroffene Dateien:
  - `think.py` - Search Strategy Prompt
  - `dossier.py` - Dossier Creation Prompt
  - `final_synthesis.py` - Final Report Prompt
  - `pick_urls.py` - URL Selection Prompt
  - `meta_synthesis.py` - Meta-Synthesis Prompt
  - `academic_conclusion.py` - Academic Conclusion Prompt
  - `bereichs_synthesis.py` - Area Synthesis Prompt
  - `academic_plan.py` - Academic Plan Prompt

**Status Messages i18n**
- `language` Parameter zu `runDeepResearch` und `runAcademicResearch` hinzugefügt
- Status-Nachrichten werden jetzt in der App-Sprache angezeigt (DE/EN)

### 🐛 Bug Fixes

**"Think failed" ohne Error-Log behoben**
- Problem: Wenn LLM leere Response zurückgab, wurde "Think failed" angezeigt aber kein Error geloggt
- Ursache: `call_llm` returned leeren String/null ohne Warning
- Fix: Detailliertes Logging hinzugefügt:
  - `LLM returned null content (finish_reason=X, refusal=Y, model=Z)`
  - `LLM returned empty string (finish_reason=X, model=Z)`
- Betrifft beide Pipelines: Deep Research & Academic Research

### 📝 Technical Details

**Geänderte Dateien:**
```
lutum/researcher/prompts/think.py
lutum/researcher/prompts/dossier.py
lutum/researcher/prompts/final_synthesis.py
lutum/researcher/prompts/pick_urls.py
lutum/researcher/prompts/meta_synthesis.py
lutum/researcher/prompts/academic_conclusion.py
lutum/researcher/prompts/bereichs_synthesis.py
lutum/researcher/prompts/academic_plan.py
lutum-backend/routes/research.py
lutum-desktop/src/components/Chat.tsx
```

---

## v1.2.1 (2026-01-29)

- Initial public release
- Deep Research Pipeline
- Academic Mode with parallel area research
- Camoufox Scraper (0% bot detection)
- PDF Export
- OpenRouter Integration
