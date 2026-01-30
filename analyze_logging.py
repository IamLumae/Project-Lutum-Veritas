"""
Logging & Error Handling Analyzer
=================================
Durchsucht den gesamten Veritas-Codebase nach:
- Logger-Definitionen
- Log-Aufrufe (info, warn, error, debug)
- Exception Handling (try/except, try/catch)
- Error-Klassen
- Console.log/warn/error
- Raise/Throw statements
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Veritas Root
ROOT = Path(__file__).parent

# Patterns to search for
PATTERNS = {
    # Python Logging
    "py_logger_def": r"(logger\s*=\s*.*|getLogger\(.*\)|get_logger\(.*\))",
    "py_log_call": r"(logger\.(debug|info|warning|warn|error|critical|exception)\s*\(.*)",
    "py_logging_import": r"(import logging|from.*log.*import)",
    "py_try_except": r"(try:|except.*:|except:)",
    "py_raise": r"(raise\s+\w+)",
    "py_print_error": r"(print\s*\(.*[Ee]rror.*\)|print\s*\(.*[Ff]ail.*\))",

    # TypeScript/JavaScript
    "ts_console": r"(console\.(log|warn|error|debug|info)\s*\(.*)",
    "ts_try_catch": r"(try\s*\{|catch\s*\(|finally\s*\{)",
    "ts_throw": r"(throw\s+new\s+\w+|throw\s+\w+)",
    "ts_error_class": r"(class\s+\w*Error|new\s+Error\()",

    # Generic error patterns
    "error_string": r"['\"].*([Ee]rror|[Ff]ailed|[Ff]ailure).*['\"]",
}

# File extensions to scan
EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx"}

# Directories to skip
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "target", "dist", ".venv", "venv"}

def scan_file(filepath: Path) -> dict:
    """Scan a single file for logging patterns."""
    results = defaultdict(list)

    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern_name, pattern in PATTERNS.items():
                # Skip Python patterns for TS files and vice versa
                if pattern_name.startswith("py_") and filepath.suffix in {".ts", ".tsx", ".js", ".jsx"}:
                    continue
                if pattern_name.startswith("ts_") and filepath.suffix == ".py":
                    continue

                matches = re.findall(pattern, line)
                if matches:
                    results[pattern_name].append({
                        "line": line_num,
                        "content": line.strip()[:200],  # Truncate long lines
                        "match": str(matches[0]) if matches else ""
                    })
    except Exception as e:
        results["_scan_error"] = [{"error": str(e)}]

    return results

def main():
    output_lines = []
    stats = defaultdict(int)
    files_by_type = defaultdict(list)

    output_lines.append("=" * 80)
    output_lines.append("LOGGING & ERROR HANDLING ANALYSIS - LUTUM VERITAS")
    output_lines.append("=" * 80)
    output_lines.append("")

    # Scan all files
    all_results = {}

    for root, dirs, files in os.walk(ROOT):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in files:
            filepath = Path(root) / filename

            if filepath.suffix not in EXTENSIONS:
                continue

            rel_path = filepath.relative_to(ROOT)
            results = scan_file(filepath)

            if results:
                all_results[str(rel_path)] = results

                # Count stats
                for pattern_name, matches in results.items():
                    if not pattern_name.startswith("_"):
                        stats[pattern_name] += len(matches)
                        files_by_type[pattern_name].append(str(rel_path))

    # Summary Statistics
    output_lines.append("=" * 80)
    output_lines.append("SUMMARY STATISTICS")
    output_lines.append("=" * 80)
    output_lines.append("")

    output_lines.append("Pattern Counts:")
    output_lines.append("-" * 40)
    for pattern, count in sorted(stats.items(), key=lambda x: -x[1]):
        output_lines.append(f"  {pattern}: {count}")
    output_lines.append("")

    # Problems identified
    output_lines.append("=" * 80)
    output_lines.append("IDENTIFIED PROBLEMS")
    output_lines.append("=" * 80)
    output_lines.append("")

    problems = []

    # Check for inconsistent logging
    if stats.get("py_logger_def", 0) > 0:
        problems.append(f"- {stats['py_logger_def']} verschiedene Logger-Definitionen (sollte zentral sein)")

    if stats.get("ts_console", 0) > 0:
        problems.append(f"- {stats['ts_console']} console.log/warn/error Aufrufe im Frontend (kein persistentes Logging)")

    if stats.get("py_print_error", 0) > 0:
        problems.append(f"- {stats['py_print_error']} print() statements für Errors (sollte logger sein)")

    # Check for generic error messages
    generic_errors = 0
    for filepath, results in all_results.items():
        for matches in results.get("error_string", []):
            if any(x in matches.get("content", "").lower() for x in ["failed", "error", "geht nicht", "fehlgeschlagen"]):
                generic_errors += 1

    if generic_errors > 0:
        problems.append(f"- {generic_errors} generische Error-Strings ohne spezifische Details")

    for problem in problems:
        output_lines.append(problem)

    output_lines.append("")
    output_lines.append("HAUPTPROBLEME:")
    output_lines.append("1. KEINE zentrale Log-Datei die geschrieben wird")
    output_lines.append("2. KEINE strukturierte Error-Klassen")
    output_lines.append("3. Frontend zeigt nur generische Meldungen")
    output_lines.append("4. Exceptions werden oft nur geloggt, nicht behandelt")
    output_lines.append("5. Kein Error-Export für User-Support")
    output_lines.append("")

    # Detailed dump per file
    output_lines.append("=" * 80)
    output_lines.append("DETAILED CODE DUMP BY FILE")
    output_lines.append("=" * 80)
    output_lines.append("")

    for filepath in sorted(all_results.keys()):
        results = all_results[filepath]

        output_lines.append("")
        output_lines.append("=" * 80)
        output_lines.append(f"FILE: {filepath}")
        output_lines.append("=" * 80)

        for pattern_name, matches in sorted(results.items()):
            if pattern_name.startswith("_"):
                continue

            output_lines.append("")
            output_lines.append(f"  [{pattern_name}] ({len(matches)} hits)")
            output_lines.append("  " + "-" * 40)

            for match in matches:
                line_num = match.get("line", "?")
                content = match.get("content", "")
                output_lines.append(f"    L{line_num}: {content}")

    # Write output
    output_file = ROOT / "LOGGING_ANALYSIS_DUMP.txt"
    output_file.write_text("\n".join(output_lines), encoding="utf-8")

    print(f"Analysis complete!")
    print(f"Output written to: {output_file}")
    print(f"")
    print(f"Quick Stats:")
    print(f"  - Files scanned: {len(all_results)}")
    print(f"  - Total logging/error patterns found: {sum(stats.values())}")
    print(f"  - Logger definitions: {stats.get('py_logger_def', 0)}")
    print(f"  - Console.log calls: {stats.get('ts_console', 0)}")
    print(f"  - Try/Except blocks (Python): {stats.get('py_try_except', 0)}")
    print(f"  - Try/Catch blocks (TS): {stats.get('ts_try_catch', 0)}")

if __name__ == "__main__":
    main()
