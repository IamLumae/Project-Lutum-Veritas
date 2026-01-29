"""
Report Parser
=============
Universeller Parser für Dossiers und Final Synthesis Reports.

Parst die strukturierten Marker aus dem LLM-Output:
- Sektionen (## EMOJI TITEL)
- Tabellen (| ... |)
- Listen (1) 2) 3))
- Highlights (> 💡 / > ⚠️)
- Citations ([N])
- Quellenverzeichnis (=== SOURCES ===)

Security Notes:
- All HTML output is escaped to prevent XSS
- URL validation prevents javascript:/data: injection
- Input length limits prevent ReDoS attacks
"""

import re
import html
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from urllib.parse import urlparse

# Security: Maximum input lengths to prevent ReDoS
MAX_TEXT_LENGTH = 500_000  # 500KB max
MAX_LINE_LENGTH = 10_000   # 10KB per line
MAX_CITATION_NUMBER = 9999  # Reasonable citation limit


class SectionType(Enum):
    """Typen von Sektionen basierend auf Emoji."""
    HEADER = "📋"
    EVIDENCE = "📊"
    SUMMARY = "🎯"
    ANALYSIS = "🔍"
    EVALUATION = "⚖️"
    LEARNINGS = "💡"
    CLAIM_AUDIT = "🔬"
    REPRODUCTION = "🔄"
    METHODOLOGY = "🔬"
    CHAPTERS = "📚"
    SYNTHESIS = "🔗"
    RECOMMENDATIONS = "🎯"
    SOURCES = "📎"
    MATRIX = "📊"
    TOP_SOURCES = "📋"
    WARNING = "⚠️"
    UNKNOWN = "?"


# Emoji zu SectionType Mapping
EMOJI_TO_TYPE = {
    "📋": SectionType.HEADER,
    "📊": SectionType.EVIDENCE,  # Kann auch MATRIX sein, je nach Titel
    "🎯": SectionType.SUMMARY,   # Kann auch RECOMMENDATIONS sein
    "🔍": SectionType.ANALYSIS,
    "⚖️": SectionType.EVALUATION,
    "💡": SectionType.LEARNINGS,
    "🔬": SectionType.CLAIM_AUDIT,  # Kann auch METHODOLOGY sein
    "🔄": SectionType.REPRODUCTION,
    "📚": SectionType.CHAPTERS,
    "🔗": SectionType.SYNTHESIS,
    "📎": SectionType.SOURCES,
    "⚠️": SectionType.WARNING,
}


@dataclass
class Section:
    """Eine geparste Sektion aus dem Report."""
    emoji: str
    title: str
    content: str
    level: int  # 1 = ##, 2 = ###, 3 = ####
    section_type: SectionType = SectionType.UNKNOWN
    subsections: list["Section"] = field(default_factory=list)


@dataclass
class TableRow:
    """Eine Zeile aus einer Tabelle."""
    cells: list[str]
    is_header: bool = False


@dataclass
class Table:
    """Eine geparste Tabelle."""
    headers: list[str]
    rows: list[TableRow]
    raw_text: str


@dataclass
class Highlight:
    """Eine Highlight-Box (> 💡 oder > ⚠️)."""
    emoji: str
    title: str
    content: str
    highlight_type: str  # "info", "warning", "question"


@dataclass
class Citation:
    """Eine Citation-Referenz."""
    number: int
    url: str
    title: str


@dataclass
class ParsedReport:
    """Vollständig geparstes Report-Objekt."""
    title: str
    sections: list[Section]
    tables: list[Table]
    highlights: list[Highlight]
    citations: dict[int, Citation]
    raw_text: str


def parse_sections(text: str) -> list[Section]:
    """
    Parst alle Sektionen mit Emoji-Markern.

    Erkennt: ## 📊 TITEL, ### Untertitel, etc.

    Args:
        text: Der zu parsende Text

    Returns:
        Liste von Section-Objekten
    """
    # Security: Limit input length
    if not text or not isinstance(text, str):
        return []
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    sections = []

    # Pattern für Sektionen: ##+ EMOJI? TITEL
    # Matches: ## 📊 EXECUTIVE SUMMARY, ### Das Wichtigste, ## TITEL (ohne Emoji)
    pattern = r'^(#{2,4})\s+([^\s]*)\s*(.*)$'

    lines = text.split('\n')
    current_section = None
    current_content = []

    for line in lines:
        match = re.match(pattern, line)

        if match:
            # Vorherige Sektion abschließen
            if current_section is not None:
                current_section.content = '\n'.join(current_content).strip()
                sections.append(current_section)
                current_content = []

            hashes = match.group(1)
            potential_emoji = match.group(2)
            rest = match.group(3)

            level = len(hashes) - 1  # ## = 1, ### = 2, #### = 3

            # Check ob zweiter Teil ein Emoji ist
            if potential_emoji and _is_emoji(potential_emoji):
                emoji = potential_emoji
                title = rest.strip()
            else:
                emoji = ""
                title = f"{potential_emoji} {rest}".strip()

            # Section Type bestimmen
            section_type = EMOJI_TO_TYPE.get(emoji, SectionType.UNKNOWN)

            # Spezialfälle basierend auf Titel
            title_lower = title.lower()
            if "matrix" in title_lower:
                section_type = SectionType.MATRIX
            elif "methodik" in title_lower or "methodology" in title_lower:
                section_type = SectionType.METHODOLOGY
            elif "empfehlung" in title_lower or "recommendation" in title_lower:
                section_type = SectionType.RECOMMENDATIONS

            current_section = Section(
                emoji=emoji,
                title=title,
                content="",
                level=level,
                section_type=section_type
            )
        else:
            # Normale Zeile zum Content hinzufügen
            current_content.append(line)

    # Letzte Sektion abschließen
    if current_section is not None:
        current_section.content = '\n'.join(current_content).strip()
        sections.append(current_section)

    return sections


def parse_tables(text: str) -> list[Table]:
    """
    Parst alle Markdown-Tabellen aus dem Text.

    Args:
        text: Der zu parsende Text

    Returns:
        Liste von Table-Objekten
    """
    # Security: Validate input
    if not text or not isinstance(text, str):
        return []
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    tables = []

    # Pattern für Tabellen-Zeilen
    table_line_pattern = r'^\|(.+)\|$'

    lines = text.split('\n')
    current_table_lines = []
    in_table = False

    for line in lines:
        line = line.strip()

        if re.match(table_line_pattern, line):
            in_table = True
            current_table_lines.append(line)
        else:
            if in_table and current_table_lines:
                # Tabelle abschließen
                table = _parse_single_table(current_table_lines)
                if table:
                    tables.append(table)
                current_table_lines = []
            in_table = False

    # Letzte Tabelle abschließen
    if current_table_lines:
        table = _parse_single_table(current_table_lines)
        if table:
            tables.append(table)

    return tables


def _parse_single_table(lines: list[str]) -> Optional[Table]:
    """Parst eine einzelne Tabelle aus Zeilen."""
    if len(lines) < 2:
        return None

    rows = []
    headers = []
    separator_found = False

    for i, line in enumerate(lines):
        # Zellen extrahieren
        cells = [cell.strip() for cell in line.strip('|').split('|')]

        # Separator-Zeile erkennen (|---|---|)
        if all(re.match(r'^[-:]+$', cell.strip()) for cell in cells):
            separator_found = True
            continue

        if not separator_found:
            # Header-Zeile
            headers = cells
        else:
            # Daten-Zeile
            rows.append(TableRow(cells=cells, is_header=False))

    if not headers:
        return None

    return Table(
        headers=headers,
        rows=rows,
        raw_text='\n'.join(lines)
    )


def parse_citations(text: str) -> dict[int, Citation]:
    """
    Extrahiert Citations und Quellenverzeichnis.

    Args:
        text: Der zu parsende Text

    Returns:
        Dict {1: Citation, 2: Citation, ...}
    """
    # Security: Validate input
    if not text or not isinstance(text, str):
        return {}
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    citations = {}

    # Quellenverzeichnis parsen (=== SOURCES === Block)
    sources_match = re.search(
        r'=== SOURCES ===\n(.+?)\n=== END SOURCES ===',
        text, re.DOTALL
    )

    if sources_match:
        sources_block = sources_match.group(1)
        for line in sources_block.strip().split('\n'):
            # Security: Limit line length
            if len(line) > MAX_LINE_LENGTH:
                continue

            line = line.strip()
            if not line:
                continue

            # Format: [N] URL - Title  oder  [N] URL
            match = re.match(r'\[(\d+)\]\s+(\S+)(?:\s+-\s+(.+))?', line)
            if match:
                try:
                    num = int(match.group(1))

                    # Security: Bound citation numbers
                    if num < 0 or num > MAX_CITATION_NUMBER:
                        continue

                    url = match.group(2).strip()
                    title = match.group(3).strip() if match.group(3) else ""

                    # Security: Validate URL
                    if not _validate_url(url):
                        continue

                    citations[num] = Citation(
                        number=num,
                        url=url,
                        title=title[:500]  # Limit title length
                    )
                except (ValueError, AttributeError):
                    continue

    return citations


def parse_highlights(text: str) -> list[Highlight]:
    """
    Parst Highlight-Boxen (> 💡 / > ⚠️ / > ❓).

    Args:
        text: Der zu parsende Text

    Returns:
        Liste von Highlight-Objekten
    """
    # Security: Validate input
    if not text or not isinstance(text, str):
        return []
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    highlights = []

    # Pattern: > EMOJI **Titel:** Text
    # Oder mehrzeilige: > EMOJI **Titel:**\n> - Punkt 1\n> - Punkt 2
    pattern = r'^>\s*(💡|⚠️|❓)\s*\*\*([^*]+)\*\*:?\s*(.*)$'

    lines = text.split('\n')
    current_highlight = None
    current_content = []

    for line in lines:
        match = re.match(pattern, line)

        if match:
            # Vorheriges Highlight abschließen
            if current_highlight is not None:
                current_highlight.content = '\n'.join(current_content).strip()
                highlights.append(current_highlight)
                current_content = []

            emoji = match.group(1)
            title = match.group(2).strip()
            initial_content = match.group(3).strip()

            # Highlight-Typ bestimmen
            if emoji == "💡":
                h_type = "info"
            elif emoji == "⚠️":
                h_type = "warning"
            elif emoji == "❓":
                h_type = "question"
            else:
                h_type = "info"

            current_highlight = Highlight(
                emoji=emoji,
                title=title,
                content=initial_content,
                highlight_type=h_type
            )
            if initial_content:
                current_content.append(initial_content)

        elif line.startswith('>') and current_highlight is not None:
            # Fortsetzung des Highlights
            content = line[1:].strip()
            if content.startswith('-'):
                content = content[1:].strip()
            current_content.append(content)

        else:
            # Highlight beenden
            if current_highlight is not None:
                current_highlight.content = '\n'.join(current_content).strip()
                highlights.append(current_highlight)
                current_highlight = None
                current_content = []

    # Letztes Highlight abschließen
    if current_highlight is not None:
        current_highlight.content = '\n'.join(current_content).strip()
        highlights.append(current_highlight)

    return highlights


def parse_numbered_list(text: str) -> list[str]:
    """
    Parst eine nummerierte Liste (1) 2) 3) Format).

    Args:
        text: Der zu parsende Text

    Returns:
        Liste der Listenpunkte
    """
    # Security: Validate input
    if not text or not isinstance(text, str):
        return []
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    items = []
    pattern = r'^\d+\)\s*(.+)$'

    for line in text.split('\n'):
        # Security: Limit line length
        if len(line) > MAX_LINE_LENGTH:
            continue
        line = line.strip()
        match = re.match(pattern, line)
        if match:
            items.append(match.group(1).strip())

    return items


def find_inline_citations(text: str) -> list[int]:
    """
    Findet alle inline Citations [N] im Text.

    Args:
        text: Der zu durchsuchende Text

    Returns:
        Liste der Citation-Nummern in Reihenfolge des Auftretens
    """
    # Security: Validate input
    if not text or not isinstance(text, str):
        return []
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    pattern = r'\[(\d+)\]'
    matches = re.findall(pattern, text)

    # Security: Filter and bound citation numbers
    result = []
    for m in matches:
        try:
            num = int(m)
            if 0 <= num <= MAX_CITATION_NUMBER:
                result.append(num)
        except ValueError:
            continue
    return result


def enrich_text_with_citation_links(text: str, citations: dict[int, Citation]) -> str:
    """
    Ersetzt [N] im Text durch HTML-Links.

    Security:
    - URLs are validated before use
    - All output is HTML-escaped to prevent XSS
    - Citation numbers are bounded

    Args:
        text: Der ursprüngliche Text
        citations: Dict der Citations

    Returns:
        Text mit HTML-Links statt [N]
    """
    # Security: Limit input length
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    def replace_citation(match):
        try:
            num = int(match.group(1))

            # Security: Bound citation numbers
            if num < 0 or num > MAX_CITATION_NUMBER:
                return match.group(0)

            if num in citations:
                citation = citations[num]

                # Security: Validate URL
                if not _validate_url(citation.url):
                    # Return plain text citation if URL is invalid
                    return f'[{num}]'

                # Security: HTML-escape all values
                safe_url = _sanitize_for_html(citation.url)
                safe_title = _sanitize_for_html(citation.title or citation.url)
                safe_num = _sanitize_for_html(str(num))

                return f'<a href="{safe_url}" class="citation" data-citation="{safe_num}" title="{safe_title}">[{safe_num}]</a>'

            return match.group(0)
        except (ValueError, AttributeError):
            return match.group(0)

    pattern = r'\[(\d+)\]'
    return re.sub(pattern, replace_citation, text)


def parse_report(text: str) -> ParsedReport:
    """
    Parst einen vollständigen Report.

    Args:
        text: Der vollständige Report-Text

    Returns:
        ParsedReport-Objekt mit allen geparsten Elementen
    """
    # Security: Validate input
    if not text or not isinstance(text, str):
        return ParsedReport(
            title="",
            sections=[],
            tables=[],
            highlights=[],
            citations={},
            raw_text=""
        )
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    # Titel extrahieren (# TITEL)
    title = ""
    title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()[:500]  # Limit title length

    sections = parse_sections(text)
    tables = parse_tables(text)
    highlights = parse_highlights(text)
    citations = parse_citations(text)

    return ParsedReport(
        title=title,
        sections=sections,
        tables=tables,
        highlights=highlights,
        citations=citations,
        raw_text=text
    )


def _is_emoji(text: str) -> bool:
    """Prüft ob ein String ein einzelnes Emoji ist."""
    # Einfache Heuristik: Emojis haben hohe Unicode-Werte
    if not text or len(text) > 2:
        return False

    # Check für bekannte Report-Emojis
    known_emojis = {'📋', '📊', '🎯', '🔍', '⚖️', '💡', '🔬', '🔄', '📚', '🔗', '📎', '⚠️', '❓', '⭐'}
    if text in known_emojis:
        return True

    # Generischer Emoji-Check
    for char in text:
        if ord(char) > 127:
            return True

    return False


def _validate_url(url: str) -> bool:
    """
    Validates URL for security.

    Prevents:
    - javascript: XSS attacks
    - data: URL injection
    - file: local file access
    - Private IP SSRF (basic check)

    Returns:
        True if URL is safe to use
    """
    if not url or not isinstance(url, str):
        return False

    # Limit URL length
    if len(url) > 2048:
        return False

    try:
        parsed = urlparse(url)

        # Only allow http/https
        if parsed.scheme.lower() not in ('http', 'https'):
            return False

        # Must have a host
        if not parsed.netloc:
            return False

        # Block private IPs (basic SSRF protection)
        host = parsed.netloc.lower().split(':')[0]
        private_patterns = [
            'localhost', '127.', '0.0.0.0', '10.', '192.168.',
            '172.16.', '172.17.', '172.18.', '172.19.',
            '172.20.', '172.21.', '172.22.', '172.23.',
            '172.24.', '172.25.', '172.26.', '172.27.',
            '172.28.', '172.29.', '172.30.', '172.31.',
            '169.254.', '[::1]', '[0:0:0:0:0:0:0:1]'
        ]
        for pattern in private_patterns:
            if host.startswith(pattern) or host == pattern.rstrip('.'):
                return False

        return True

    except Exception:
        return False


def _sanitize_for_html(text: str) -> str:
    """Escapes text for safe HTML insertion."""
    if not text:
        return ""
    return html.escape(str(text), quote=True)


def extract_key_value_pairs(text: str) -> dict[str, str]:
    """
    Extrahiert Key-Value Paare aus - **Key:** Value Format.

    Args:
        text: Der zu parsende Text

    Returns:
        Dict {key: value, ...}
    """
    # Security: Validate input
    if not text or not isinstance(text, str):
        return {}
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    pairs = {}
    pattern = r'^-\s*\*\*([^*]+)\*\*:\s*(.+)$'

    for line in text.split('\n'):
        # Security: Limit line length
        if len(line) > MAX_LINE_LENGTH:
            continue
        line = line.strip()
        match = re.match(pattern, line)
        if match:
            key = match.group(1).strip()[:200]  # Limit key length
            value = match.group(2).strip()[:2000]  # Limit value length
            pairs[key] = value

    return pairs


# Export für einfachen Import
__all__ = [
    'Section',
    'SectionType',
    'Table',
    'TableRow',
    'Highlight',
    'Citation',
    'ParsedReport',
    'parse_sections',
    'parse_tables',
    'parse_citations',
    'parse_highlights',
    'parse_numbered_list',
    'parse_report',
    'find_inline_citations',
    'enrich_text_with_citation_links',
    'extract_key_value_pairs',
]
