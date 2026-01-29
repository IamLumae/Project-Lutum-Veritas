# Academic Deep Research - Flow Design

## Konzept

Academic Mode unterscheidet sich fundamental vom Normal Mode durch **parallele, autonome Bereiche** statt sequenzieller Punkt-für-Punkt Abarbeitung.

---

## Normal Mode vs Academic Mode

### Normal Mode (aktuell)
```
Punkt 1 → Punkt 2 → Punkt 3 → Punkt 4 → Punkt 5 → SYNTHESIS
    └─key learnings─┘    └─key learnings─┘
         (sequenziell, aufeinander aufbauend)
```

### Academic Mode (neu)
```
┌─ Bereich 1 ─┐   ┌─ Bereich 2 ─┐   ┌─ Bereich 3 ─┐
│  Punkt 1.1  │   │  Punkt 2.1  │   │  Punkt 3.1  │
│      ↓      │   │      ↓      │   │      ↓      │
│  Punkt 1.2  │   │  Punkt 2.2  │   │  Punkt 3.2  │
│      ↓      │   │      ↓      │   │      ↓      │
│ SYNTHESE 1  │   │ SYNTHESE 2  │   │ SYNTHESE 3  │
└─────────────┘   └─────────────┘   └─────────────┘
       │                 │                 │
       └────────────────┼─────────────────┘
                        ↓
              META-SYNTHESE
              (Querverbindungen)
                        ↓
              FINAL DOCUMENT
```

---

## Vollständiger Flow

### 1. USER EINGABE
```
"Löse P vs NP..."
```

### 2. OVERVIEW (overview.py)
- LLM generiert initiale Suchqueries
- Return: `["query1", "query2", ...]`

### 3. CLARIFY (clarify.py) [optional]
- LLM stellt Rückfragen zur Präzisierung
- User antwortet

### 4. ACADEMIC PLAN (plan.py) - MODIFIZIERT
- LLM erstellt Recherche-Plan mit **autonomen Bereichen**
- Jeder Bereich muss **unabhängig** erforschbar sein
- Keine Abhängigkeiten zwischen Bereichen
- Return:
```json
{
  "bereiche": [
    {
      "titel": "Thermodynamik & Statistische Mechanik",
      "punkte": [
        "Spin-Gläser und NP-Härte",
        "Phasenübergänge und Komplexität",
        "Energieminimierung als SAT"
      ]
    },
    {
      "titel": "Biologische Analogrechner",
      "punkte": [
        "Proteinfaltung als NP-Problem",
        "Morphogenese und kombinatorische Räume"
      ]
    },
    {
      "titel": "Quantenmechanik & Alternative Modelle",
      "punkte": [
        "Topologische Quantencomputer",
        "Nicht-Turing Berechnungsmodelle"
      ]
    }
  ]
}
```

### 5. PARALLELE BEREICHS-PIPELINES

**Für jeden Bereich SIMULTAN:**

```
BEREICH N PIPELINE:
│
├─► Für jeden Punkt im Bereich:
│   │
│   ├─ THINK (think.py)
│   │  → "Was suchen wir? Welche Queries?"
│   │  → Return: search_queries[]
│   │
│   ├─ SEARCH (search.py)
│   │  → DuckDuckGo / Google Scholar
│   │  → Return: URLs[]
│   │
│   ├─ PICK URLs (pick.py)
│   │  → LLM wählt relevanteste URLs
│   │  → Return: selected_urls[]
│   │
│   ├─ SCRAPE (camoufox_scraper.py)
│   │  → Camoufox holt Content
│   │  → Return: {url: content}
│   │
│   ├─ DOSSIER (dossier.py)
│   │  → LLM erstellt Dossier
│   │  → Return: dossier_text, key_learnings
│   │
│   └─ Key Learnings → nächster Punkt IM SELBEN BEREICH
│
└─► BEREICHS-SYNTHESE
    → Alle Dossiers des Bereichs → 1 Bereichs-Report
```

**Wichtig:**
- Key Learnings fließen nur INNERHALB eines Bereichs
- Bereiche sind voneinander UNABHÄNGIG
- Alle Bereiche laufen PARALLEL

### 6. META-SYNTHESE (neu!)

Nach Abschluss ALLER Bereichs-Pipelines:

```
Input: Alle Bereichs-Synthesen

Prompt:
"Hier sind N unabhängig recherchierte Bereichs-Synthesen.
Deine Aufgabe:
1. Finde QUERVERBINDUNGEN zwischen den Bereichen
2. Identifiziere WIDERSPRÜCHE
3. Erkenne übergreifende MUSTER
4. Ziehe NEUE ERKENNTNISSE die nur durch Kombination sichtbar werden"

Output: Meta-Analyse mit Querverbindungen
```

### 7. FINAL DOCUMENT

Struktur des finalen Dokuments:

```markdown
# [TITEL]

## Executive Summary

## Methodik

## Bereich 1: [Titel]
[Bereichs-Synthese 1]

## Bereich 2: [Titel]
[Bereichs-Synthese 2]

## Bereich 3: [Titel]
[Bereichs-Synthese 3]

## Querverbindungen & Synthese
[Meta-Analyse]
- Verbindungen zwischen Bereichen
- Widersprüche
- Übergreifende Muster
- Neue Erkenntnisse

## Kritische Würdigung

## Quellenverzeichnis
```

---

## Technische Herausforderungen

### 1. Paralleles Scraping
- Ein Camoufox-Browser kann nicht mehrere Seiten gleichzeitig scrapen
- **Lösung A:** Pool von N Browser-Instanzen
- **Lösung B:** Shared Scrape-Queue, Bereiche teilen sich Browser
- **Lösung C:** Scraping sequenziell, aber THINK/DOSSIER parallel

### 2. Plan-Format ändern
- Aktuell: Flache Liste `["Punkt 1", "Punkt 2", ...]`
- Neu: Hierarchisch `{bereiche: [{titel, punkte}, ...]}`

### 3. Frontend-Anzeige
- Mehrere parallele Progress-Bars?
- Oder: "Bereich 1: 2/3, Bereich 2: 1/2, Bereich 3: 3/3"

### 4. Checkpoints
- Pro Bereich eigener Checkpoint
- Oder: Globaler Checkpoint mit Bereichs-Status

---

## Implementierungs-Schritte

**Erkenntnis: Fast alles existiert schon! Minimale Änderungen nötig:**

### 1. Frontend: Warnung beim Umschalten (Settings.tsx)
```typescript
// Popup wenn academicMode aktiviert wird:
"⚠️ Achtung: Academic Mode verursacht ca. 10x höhere Kosten!
Jeder Bereich durchläuft eine vollständige Research-Pipeline."
```

### 2. Backend: Academic Plan Prompt (plan.py oder academic_plan.py)
```python
ACADEMIC_PLAN_PROMPT = """
Erstelle einen hierarchischen Recherche-Plan mit AUTONOMEN BEREICHEN.

WICHTIG:
- Jeder Bereich muss UNABHÄNGIG erforschbar sein
- Keine Abhängigkeiten zwischen Bereichen
- Bereiche werden PARALLEL bearbeitet

FORMAT:
=== BEREICH 1: [Titel] ===
1) Punkt 1.1
2) Punkt 1.2
...
=== BEREICH 2: [Titel] ===
1) Punkt 2.1
...
=== END PLAN ===
"""
```

### 3. Backend: Plan Parser + Parallel-Aufruf (research.py)
```python
def parse_academic_plan(plan_text: str) -> dict[str, list[str]]:
    """Parst hierarchischen Plan in {bereich: [punkte]}"""
    ...

async def run_academic_deep_research(request):
    bereiche = parse_academic_plan(plan_text)

    # Für jeden Bereich eine Pipeline starten
    tasks = [
        run_bereich_pipeline(bereich_name, punkte, ...)
        for bereich_name, punkte in bereiche.items()
    ]

    # PARALLEL ausführen
    bereichs_synthesen = await asyncio.gather(*tasks)

    # Meta-Synthese
    meta = await generate_meta_synthesis(bereichs_synthesen)

    # Final zusammenbauen
    return combine_all(bereichs_synthesen, meta)
```

### 4. Backend: Meta-Synthese Prompt (meta_synthesis.py)
```python
META_SYNTHESIS_PROMPT = """
Du erhältst N unabhängig recherchierte Bereichs-Synthesen.

Deine Aufgabe:
1. QUERVERBINDUNGEN zwischen Bereichen finden
2. WIDERSPRÜCHE identifizieren
3. Übergreifende MUSTER erkennen
4. NEUE ERKENNTNISSE die nur durch Kombination sichtbar werden

Bereichs-Synthesen:
{all_syntheses}
"""
```

### 5. Backend: Final Document Assembly
```python
def assemble_academic_document(bereichs_synthesen, meta_synthesis):
    doc = "# [TITEL]\n\n"
    doc += "## Executive Summary\n...\n\n"

    for name, synthese in bereichs_synthesen:
        doc += f"## {name}\n{synthese}\n\n"

    doc += "## Querverbindungen & Erkenntnisse\n"
    doc += meta_synthesis

    return doc
```

---

**Zusammenfassung: Was ist NEU?**

| Komponente | Status | Aufwand |
|------------|--------|---------|
| Research Pipeline | ✅ Existiert | - |
| Dossier Generation | ✅ Existiert | - |
| Final Synthesis | ✅ Existiert | - |
| Camoufox Scraper | ✅ Existiert | - |
| Academic Plan Prompt | 🆕 Neu | Klein |
| Plan Parser (Bereiche) | 🆕 Neu | Klein |
| Parallel Pipeline Aufruf | 🆕 Neu | Mittel |
| Meta-Synthese Prompt | 🆕 Neu | Klein |
| Document Assembly | 🆕 Neu | Klein |
| Frontend Warnung | 🆕 Neu | Minimal |

**Geschätzter Aufwand: 1-2 Sessions**

---

## Beispiel: P vs NP Recherche

### Academic Plan:
```
Bereich 1: Thermodynamik & Statistische Mechanik
├── Spin-Gläser und Grundzustand als NP-Härte
├── Phasenübergänge und Komplexitätsklassen
└── Energieminimierung ↔ SAT Isomorphie

Bereich 2: Biologische Computation
├── Proteinfaltung als NP-vollständiges Problem
└── Morphogenese: Wie löst Natur kombinatorische Probleme?

Bereich 3: Alternative Berechnungsmodelle
├── Topologische Quantencomputer
├── Nicht-Turing Modelle
└── Oracle-Barrieren umgehen

Bereich 4: Meta-Komplexität
├── P vs NP als Gödel-Problem
└── Unabhängigkeit von ZFC
```

### Parallele Ausführung:
```
t=0   Bereich 1 startet    Bereich 2 startet    Bereich 3 startet    Bereich 4 startet
t=2   B1: Dossier 1.1      B2: Dossier 2.1      B3: Dossier 3.1      B4: Dossier 4.1
t=4   B1: Dossier 1.2      B2: Dossier 2.2      B3: Dossier 3.2      B4: Dossier 4.2
t=6   B1: Dossier 1.3      B2: SYNTHESE 2       B3: Dossier 3.3      B4: SYNTHESE 4
t=8   B1: SYNTHESE 1       -                     B3: SYNTHESE 3       -
t=10  ─────────────────── META-SYNTHESE ───────────────────
t=12  ─────────────────── FINAL DOCUMENT ──────────────────
```

---

## Vorteile von Academic Mode

1. **Schneller** - Parallele Ausführung statt sequenziell
2. **Tiefgründiger** - Jeder Bereich wird vollständig erforscht
3. **Strukturierter** - Paper-ähnliche Gliederung
4. **Objektivier** - Bereiche beeinflussen sich nicht gegenseitig
5. **Besser für komplexe Fragen** - Multidisziplinäre Recherche
