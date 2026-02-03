# Standalone Benchmark

Diese Ordnerstruktur enthält drei eigenständige Skripte, um den akademischen Deep-Research-Flow in einzelne Schritte aufzuteilen.

## Skripte

1. `01_query_to_sources_and_questions.py`
   - Nimmt eine User-Query, erstellt 10 Suchbegriffe, sammelt 10 URLs, scraped die Inhalte und erzeugt Rückfragen.
2. `02_answers_to_plan.py`
   - Nimmt Antworten auf die Rückfragen und erstellt einen finalen Forschungsplan.
3. `03_plan_to_deep_research.py`
   - Führt den Plan aus, erstellt Dossiers pro Abschnitt und gibt am Ende eine Synthese + Conclusion aus.

## Logging & Crash-Safety

- Jede Stage schreibt eine `run.log` Datei.
- LLM-Requests/Responses werden sofort als JSON gespeichert.
- `status.json` und `checkpoint.json` werden nach jedem Schritt aktualisiert.
- Alle JSONs werden zusätzlich als `.bak` gespeichert.

## Beispiel-Aufrufe

```bash
python "Standalone Benchmark/01_query_to_sources_and_questions.py" --id run_001 --query "Wie beeinflusst KI die medizinische Diagnostik?"
python "Standalone Benchmark/02_answers_to_plan.py" --id run_001 --answers-file /path/to/answers.json
python "Standalone Benchmark/03_plan_to_deep_research.py" --id run_001
```

## Hinweise

- OpenRouter API Key ist in `_common.py` hardcoded (`OPENROUTER_API_KEY`).
- Scraping wird mit Camoufox durchgeführt, maximale Parallelität: 10 gleichzeitige Scrapes.
