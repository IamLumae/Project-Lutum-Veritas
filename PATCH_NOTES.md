# Lutum Veritas - Patch Notes

## v1.2.3 (2026-01-30)

### 🌐 Language Detection Fix

**Root Cause Found & Fixed**
- `context_state.py` hatte deutsche Header (`=== DEINE AUFGABE ===`, `=== RÜCKFRAGEN ===`)
- Diese wurden vor jeden LLM-Call geprefixed → LLM dachte "deutscher Kontext = deutsche Antwort"
- Fix: Alle Header auf Englisch (`=== YOUR TASK ===`, `=== FOLLOW-UP QUESTIONS ===`, etc.)

**Zusätzliche Prompt-Fixes:**
- `clarify.py`, `plan.py`, `overview.py`, `search.py` komplett auf Englisch
- Jeder Prompt endet mit: `CRITICAL: Respond in SAME LANGUAGE as user query`

### 🎨 UI Redesign - Techno/Cyber Theme

**Loading Indicator (komplett neu):**
- Weg mit Mac-Terminal-Dots, rein mit Cyber-Style
- Blauer Glow-Border mit Scan-Line Animation
- Animiertes Hex-Icon mit Ping-Effekt
- Gradient Progress-Bar
- Orange `›` Prompt-Character

**Log Messages (Warnings/Errors):**
- Gradient Backgrounds statt flat colors
- Pulsing Glow-Effekte
- Animierter Status-Dot
- Labels: "System Error" / "System Notice"

**Message Boxes:**
- User: Enhanced blue gradient mit Glow-Shadow
- Assistant: Subtile Corner-Accents (blau oben-links, orange unten-rechts)

**CSS Animations hinzugefügt:**
- `scan` - Scan-Line Effekt (top-to-bottom)
- `progress` - Shimmer Progress-Bar
- `glow-pulse` - Border Glow
- `cursor-blink` - Typing Cursor
- `hex-rotate` - Icon Rotation

### 🔍 URL Picker Fix

**Problem:** LLM pickte nur 3 URLs statt 10
- Alter Prompt: "Select the best URLs (max 10)" → LLM interpretierte "ich kann auch weniger wählen"
- Neuer Prompt: "ALWAYS select EXACTLY 10 URLs. Not 3, not 5 - exactly 10!"
- Mandatory Mix definiert: 2-3 Official + 2-3 Community + 2-3 Reviews + 2-3 Technical

### 📝 Technical Details

**Geänderte Dateien:**
```
# Language Fix
lutum/researcher/context_state.py
lutum/researcher/clarify.py
lutum/researcher/plan.py
lutum/researcher/overview.py
lutum/researcher/search.py

# UI Redesign
lutum-desktop/src/components/MessageList.tsx
lutum-desktop/src/App.css
```

---

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

### 🔌 Multi-Provider Support

**5 API Provider zur Auswahl**
- OpenRouter (Default) - Model-Dropdown mit 200+ Modellen
- OpenAI - GPT-4, GPT-4o, etc.
- Anthropic - Claude 3.5, Claude 3 Opus, etc.
- Google Gemini - Gemini Pro, Gemini Flash, etc.
- HuggingFace - Open-Source Modelle

**UI-Änderungen:**
- Provider-Dropdown in Settings
- Bei OpenRouter: Modell-Dropdowns mit Suchfunktion
- Bei anderen Providern: Manuelle Modell-Eingabe (Textfelder)
- API Key Placeholder passt sich dem Provider an

**Backend:**
- `base_url` Parameter für alle Research-Endpoints
- Dynamische API-URL statt hardcoded OpenRouter

### 🐛 Bug Fixes

**PDF Export: Markdown-Tabellen gefixt**
- Problem: Tabellen wurden vertikal statt horizontal gerendert (jedes Zeichen einzeln)
- Ursache: Fehlerhafte `parseRow()` Filter-Logik und zu strikte Tabellenerkennung
- Fix:
  - Tabellenerkennung prüft jetzt Header + Separator-Zeile (mit `-`)
  - `parseRow()` entfernt korrekt leere Zellen von führenden/trailing Pipes
  - Fallback wenn Table-Parsing fehlschlägt (rewind und als Text verarbeiten)

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
# i18n
lutum/researcher/prompts/think.py
lutum/researcher/prompts/dossier.py
lutum/researcher/prompts/final_synthesis.py
lutum/researcher/prompts/pick_urls.py
lutum/researcher/prompts/meta_synthesis.py
lutum/researcher/prompts/academic_conclusion.py
lutum/researcher/prompts/bereichs_synthesis.py
lutum/researcher/prompts/academic_plan.py

# Multi-Provider
lutum-desktop/src/stores/settings.ts
lutum-desktop/src/components/Settings.tsx
lutum-desktop/src/components/Chat.tsx
lutum-desktop/src/hooks/useBackend.ts
lutum-backend/routes/research.py
```

---

## v1.2.1 (2026-01-29)

- Initial public release
- Deep Research Pipeline
- Academic Mode with parallel area research
- Camoufox Scraper (0% bot detection)
- PDF Export
- OpenRouter Integration
