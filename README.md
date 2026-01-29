<p align="center">
  <img src="assets/logo.png" alt="LV Research Logo" width="400"/>
</p>

<h1 align="center">Lutum Veritas</h1>

<p align="center">
  <strong>Open Source Deep Research Engine</strong><br>
  <em>"Shaping Truth from Raw Data"</em>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#tech-stack">Tech Stack</a> •
  <a href="#license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-AGPL--3.0-blue.svg" alt="License: AGPL-3.0"/>
  <img src="https://img.shields.io/badge/Version-1.2.1-green.svg" alt="Version"/>
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey.svg" alt="Platform"/>
  <img src="https://img.shields.io/badge/Python-3.11+-yellow.svg" alt="Python"/>
</p>

---

## What is Lutum Veritas?

**Lutum Veritas** is a self-hosted Deep Research Engine that transforms any question into a comprehensive research document. Unlike Perplexity, ChatGPT, or Google's AI Overview, you bring your own API key and everything runs locally.

### Why Use This?

| Problem | Lutum Veritas Solution |
|---------|----------------------|
| **Expensive subscriptions** | Pay only for API tokens (~$0.08 per research) |
| **Surface-level answers** | Deep multi-source analysis with 20+ sources per topic |
| **Black-box results** | See every source, every step, full transparency |
| **Bot detection blocks** | Camoufox scraper with 0% detection rate |
| **No local control** | Runs 100% on your machine |

---

## Features

### 🔬 Deep Research Pipeline

```
Your Question
     ↓
┌─────────────────────────────────────────────────────┐
│  1. CLARIFICATION                                   │
│     AI asks smart follow-up questions               │
├─────────────────────────────────────────────────────┤
│  2. RESEARCH PLAN                                   │
│     Creates structured investigation points         │
├─────────────────────────────────────────────────────┤
│  3. DEEP RESEARCH (per point)                       │
│     Think → Search → Pick URLs → Scrape → Dossier   │
├─────────────────────────────────────────────────────┤
│  4. FINAL SYNTHESIS                                 │
│     Cross-reference all findings into one document  │
└─────────────────────────────────────────────────────┘
     ↓
📄 Comprehensive Report (3000+ words)
```

### 🎓 Academic Mode (NEW!)

Hierarchical research with autonomous areas:
- **Parallel Processing**: Research areas independently
- **Meta-Synthesis**: Find cross-connections between areas
- **Toulmin Argumentation**: Structured academic reasoning
- **Evidence Grading**: Rate source quality (Level I-VII)

### 💻 Desktop App Features

| Feature | Description |
|---------|-------------|
| **Live Progress** | Watch research happen in real-time |
| **Session Management** | Save, rename, delete research sessions |
| **Source Boxes** | Expandable boxes showing all scraped URLs |
| **Citation Links** | Clickable `[1]` references to sources |
| **Export** | Download as Markdown or PDF |
| **Dark Mode** | System theme support |
| **i18n** | German & English interface |

### 🛡️ Zero Detection Scraping

Powered by **Camoufox** - a hardened Firefox fork that bypasses:
- Cloudflare
- DataDome
- PerimeterX
- Most anti-bot systems

---

## Installation

### Option A: Download Installer (Recommended)

1. Download from [Releases](../../releases):
   - `Lutum Veritas_1.2.1_x64-setup.exe` (Installer)
   - `lutum-backend.exe` (Backend Server)

2. Install the desktop app
3. Run `lutum-backend.exe` (keep it running)
4. Launch Lutum Veritas
5. Enter your [OpenRouter API Key](https://openrouter.ai/keys) in Settings

### Option B: Build from Source

**Requirements:**
- Python 3.11+
- Node.js 18+
- Rust (for Tauri)

```bash
# Clone
git clone https://github.com/IamLumae/lutum-veritas.git
cd lutum-veritas

# Backend
cd lutum-backend
pip install -r requirements.txt
python main.py

# Frontend (new terminal)
cd lutum-desktop
npm install
npm run tauri dev
```

---

## Quick Start

1. **Start Backend** - Run `lutum-backend.exe` or `python main.py`
2. **Launch App** - Open Lutum Veritas
3. **Enter API Key** - Settings → OpenRouter API Key
4. **Ask Anything** - Type your research question
5. **Answer Clarifications** - Help the AI understand your needs
6. **Review Plan** - Approve or modify the research plan
7. **Click "Let's Go"** - Watch the magic happen
8. **Export** - Download your research as MD or PDF

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LUTUM VERITAS DESKTOP                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Tauri Shell (Rust + WebView)              │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │           React Frontend (TypeScript)           │  │  │
│  │  │  • Chat Interface     • Session Management      │  │  │
│  │  │  • Live Status        • Markdown Rendering      │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↕ HTTP                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend (Python)                  │  │
│  │  • Research Orchestrator    • LLM Integration         │  │
│  │  • Session Persistence      • SSE Streaming           │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │         Camoufox Scraper (Firefox Fork)         │  │  │
│  │  │              0% Bot Detection Rate               │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### LLM Pipeline

| Step | Model | Purpose |
|------|-------|---------|
| Think | Gemini Flash Lite | Generate search strategies |
| Pick URLs | Gemini Flash Lite | Select best sources |
| Dossier | Gemini Flash Lite | Analyze and summarize |
| Final Synthesis | Qwen 235B | Create comprehensive report |

All models accessed via [OpenRouter](https://openrouter.ai) - you only need one API key.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Desktop Shell** | Tauri 2.0 (Rust) |
| **Frontend** | React 18 + TypeScript + Tailwind CSS |
| **Backend** | FastAPI (Python 3.11) |
| **Scraper** | Camoufox (Hardened Firefox) |
| **LLMs** | OpenRouter (Gemini, Qwen, Claude, etc.) |
| **Database** | File-based JSON (sessions) |

---

## Project Structure

```
lutum-veritas/
├── lutum/                      # Core Python library
│   ├── researcher/
│   │   └── prompts/            # LLM prompts (Think, Pick, Dossier, Synthesis)
│   └── scrapers/
│       └── camoufox_scraper.py # Zero-detection web scraper
├── lutum-backend/              # FastAPI server
│   └── routes/
│       └── research.py         # Research pipeline orchestrator
├── lutum-desktop/              # Tauri desktop app
│   └── src/
│       ├── components/         # React components
│       ├── hooks/              # useBackend API hook
│       └── stores/             # Session state management
├── dist/                       # Pre-built binaries
├── LICENSE                     # AGPL-3.0
├── NOTICE                      # Copyright & commercial licensing
└── README.md                   # You are here
```

---

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Backend health check |
| `/research/overview` | POST | Initial analysis & clarification questions |
| `/research/plan` | POST | Generate research plan |
| `/research/plan/revise` | POST | Modify plan based on feedback |
| `/research/deep` | POST | Execute deep research (SSE stream) |
| `/research/academic` | POST | Execute academic research (SSE stream) |

### SSE Events (Deep Research)

```javascript
// Status updates
{"type": "status", "message": "Searching Google..."}

// Sources found
{"type": "sources", "urls": ["https://...", "https://..."]}

// Point completed
{"type": "point_complete", "point_title": "...", "key_learnings": "..."}

// Synthesis starting
{"type": "synthesis_start", "dossier_count": 5, "total_sources": 45}

// Research complete
{"type": "done", "data": {"final_document": "...", "source_registry": {...}}}
```

---

## Cost Comparison

Real benchmark: 513k input tokens, 55k output tokens

| Service | Cost | vs Lutum |
|---------|------|----------|
| **Lutum Veritas** | **$0.08** | - |
| ChatGPT Plus | $20/mo | Subscription |
| Perplexity Pro | $20/mo | Subscription |
| OpenAI o3 | $7.36 | 92x more |
| OpenAI o4-mini | $1.44 | 18x more |
| Google Gemini Pro | $2.95 | 37x more |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

### Development Setup

```bash
# Backend (with hot reload)
cd lutum-backend
uvicorn main:app --reload --port 8420

# Frontend (with hot reload)
cd lutum-desktop
npm run tauri dev
```

---

## License

**Lutum Veritas** is licensed under the [GNU Affero General Public License v3.0](LICENSE).

This means:
- ✅ Free to use, modify, and distribute
- ✅ Commercial use allowed
- ⚠️ Must disclose source code (including SaaS)
- ⚠️ Modifications must use same license

### Commercial Licensing

Need to use Lutum Veritas without AGPL obligations? Commercial licenses are available.

**Contact:** iamlumae@gmail.com

---

## Security

SHA256 Checksums for v1.2.1:

```
lutum-desktop.exe:              4b4e3730faaba4702791bd55b295b77286503914f7bddd68f5d6f8dbbc3bb7b5
lutum-backend.exe:              45497969ecd54b15a43aa911c43a89dfa14d3bdf084da747cf2fda96552a22a5
Lutum Veritas_1.2.1_x64-setup:  71e5b6ef08744293d73c5c8328cea7fca1afe62794c293424bb86a2874008cb8
```

---

## Acknowledgments

- [Camoufox](https://github.com/nicholaslazooffers/camoufox) - The magic behind zero-detection scraping
- [Tauri](https://tauri.app) - Lightweight desktop app framework
- [OpenRouter](https://openrouter.ai) - Unified LLM API access

---

<p align="center">
  <strong>Built with obsessive attention to detail</strong><br>
  <em>Because truth shouldn't be locked behind paywalls</em>
</p>

<p align="center">
  <a href="https://github.com/IamLumae">@IamLumae</a>
</p>
