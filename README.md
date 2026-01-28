# Lutum Veritas

> "Wahrheit aus dem Schlamm" - Proprietäre Deep Research Engine

## Was ist das?

Eine vollständige **Deep Research Engine** die unabhängig von Perplexity, OpenAI Deep Research, etc. ist.

- **Keine Abos** - Du bringst deinen eigenen API Key
- **Volle Kontrolle** - Alles läuft lokal
- **Maximale Tiefe** - Unbegrenzte Iterationen
- **0% Bot-Detection** - Camoufox umgeht Cloudflare & Co

---

## Quick Start

### 1. Backend starten
```powershell
cd lutum-backend
python main.py
# Läuft auf http://localhost:8420
```

### 2. Frontend starten
```powershell
cd lutum-desktop
npm run tauri dev
```

### Oder: Fertige Installer nutzen
```
dist/
├── lutum-backend.exe           # Backend (doppelklick startet Server)
└── LutumVeritas-Frontend-Setup.exe  # Frontend Installer
```

---

## Features

### Deep Research Pipeline

```
User Frage → Rückfragen → Plan erstellen → "Los geht's"
                                               ↓
┌─────────────────────────────────────────────────────────────┐
│                    DEEP RESEARCH LOOP                        │
│                                                              │
│  Pro Punkt: Think → Search → Scrape → Dossier → Learnings  │
│                                                              │
│  [Live im Chat: Sources-Boxen + Point-Summaries]            │
└─────────────────────────────────────────────────────────────┘
                               ↓
               Final Synthesis (Qwen 235B)
                               ↓
              Finales Dokument (3000+ Wörter)
```

### UI Features

| Feature | Beschreibung |
|---------|--------------|
| Session Management | Erstellen, Löschen, Umbenennen |
| Live Terminal | macOS-Style mit Status-Updates |
| Sources-Box | Aufklappbar, klickbare Links |
| Point-Summaries | Progress-Bar + Key Learnings |
| Markdown Rendering | Code-Blöcke, Tabellen, Listen |
| Dark Mode | System-Theme Support |

### Technologie

| Komponente | Tech |
|------------|------|
| Frontend | Tauri (Rust) + React + TypeScript |
| Backend | FastAPI (Python) |
| Scraper | Camoufox (Firefox C++ Fork) |
| LLMs | Gemini Flash Lite + Qwen 235B |

---

## Architektur

```
┌─────────────────────────────────────────────────────┐
│              LutumVeritas Desktop App               │
│  ┌───────────────────────────────────────────────┐  │
│  │           Tauri Shell (Rust)                  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │        React Frontend (Chat)            │  │  │
│  │  │  - MessageList (Markdown, Sources)      │  │  │
│  │  │  - Terminal Status, Progress Bars       │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
│                      ↓ HTTP :8420                   │
│  ┌───────────────────────────────────────────────┐  │
│  │         FastAPI Backend (Python)              │  │
│  │  - /research/deep (Orchestrator)              │  │
│  │  - SSE Events (status, sources, point_done)   │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │     Camoufox Scraper (John Wick)        │  │  │
│  │  │     0% Detection Rate                    │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## API Endpoints

### POST /research/deep
Deep Research Pipeline starten (SSE Stream)

### POST /research/plan
Recherche-Plan erstellen

### POST /research/run
Steps 1-3 ausführen (Übersicht + Rückfragen)

### GET /health
Backend Health Check

---

## Struktur

```
Project Lutum Veritas/
├── lutum/
│   ├── researcher/
│   │   └── prompts/         # Think, Pick, Dossier, Final
│   ├── scrapers/
│   │   └── camoufox_scraper.py  # John Wick
│   └── core/
├── lutum-backend/
│   └── routes/
│       └── research.py      # Deep Research Orchestrator
├── lutum-desktop/
│   └── src/
│       ├── components/
│       │   └── MessageList.tsx  # Point-Summaries, Terminal
│       └── hooks/
│           └── useBackend.ts    # runDeepResearch()
├── dist/                    # Fertige Installer
├── BRAINSTORM.md            # Vision & Status
├── RECURSIVE_PIPELINE.md    # Technische Doku
└── CODE_LAWS.md             # Coding Standards
```

---

## Lizenz

- Camoufox: MIT License
- Lutum Veritas: Proprietär

---

*Stand: 2026-01-27*
