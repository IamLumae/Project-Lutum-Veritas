"""
Pick URLs Prompt (Prompt 3)
===========================
LLM selects the most relevant URLs from search results.

Recursive: Executed for each point in the Research Plan.

Security:
- All parsed URLs are validated (SSRF protection)
- Input lengths are limited
- Response parsing has bounds
"""

from lutum.core.security import validate_url, sanitize_user_input, MAX_URL_LENGTH

PICK_URLS_SYSTEM_PROMPT = """You select URLs from search results.

═══════════════════════════════════════════════════════════════════
                    OUTPUT FORMAT (MANDATORY!)
═══════════════════════════════════════════════════════════════════

RULE 1: NO ANALYSIS. NO EXPLANATION. ONLY URLS.
RULE 2: Start IMMEDIATELY with "=== SELECTED ===" - NO text before!
RULE 3: Each line: "url N: https://..." - nothing else.
RULE 4: EXACTLY 20 URLs. Not 19, not 21.

═══════════════════════════════════════════════════════════════════
                    QUERY AWARENESS (MANDATORY!)
═══════════════════════════════════════════════════════════════════

Adapt your selection strategy to the TASK:
- "unknown/small/niche/experimental" → LESS obvious sources
- "established/enterprise/proven/production-ready" → known, highly-referenced sources
- "academic/scientific" → prioritize papers and research
- "practical/hands-on/tutorial" → prioritize code examples and guides

═══════════════════════════════════════════════════════════════════
                    DIVERSIFICATION (MANDATORY!)
═══════════════════════════════════════════════════════════════════

Select URLs from DIFFERENT perspectives:
- Not 15x GitHub, but: GitHub + Reddit + Paper + Blog + Docs
- Not 15x the same topic, but: cover different aspects

SOURCE MIX (approximate distribution for 20 URLs):
- 6-8x Primary: GitHub repos, official docs, papers (arxiv)
- 4-5x Community: Reddit, HN, forums, Stack Overflow
- 3-4x Practical: Tutorials, Medium, Dev.to, guides
- 2-3x Critical: Comparisons, benchmarks, limitations
- 2-3x Current: News, 2024/2025 releases, updates

═══════════════════════════════════════════════════════════════════
                    SOURCE RANKING
═══════════════════════════════════════════════════════════════════

**High quality:** GitHub repos, papers (arxiv), official docs, expert blogs
**Medium quality:** Medium/Dev.to, Reddit (if substantial), Stack Overflow
**Avoid:** Generic news sites, SEO spam, outdated (before 2023)"""

PICK_URLS_USER_PROMPT = """
# CONTEXT

## Main Task
{user_query}

## Current Research Point
{current_point}

## Your Thoughts (from previous step)
{thinking_block}

{previous_learnings_block}

---

# SEARCH RESULTS

{search_results}

---

# TASK

Select EXACTLY 20 URLs. NO ANALYSIS. NO EXPLANATION. ONLY URLS.

CRITICAL: Start IMMEDIATELY with "=== SELECTED ===" - NO text before!

=== SELECTED ===
url 1: https://example.com/1
url 2: https://example.com/2
...
url 20: https://example.com/20

=== REJECTED ===
rejected: X URLs due to reason
"""


def build_pick_urls_prompt(
    user_query: str,
    current_point: str,
    thinking_block: str,
    search_results: str,
    previous_learnings: list[str] | None = None
) -> tuple[str, str]:
    """
    Builds the Pick-URLs prompt.

    Args:
        user_query: Main task
        current_point: Current research point
        thinking_block: Thoughts from Think prompt
        search_results: Formatted search results
        previous_learnings: Key learnings from previous dossiers (optional)

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    # Format previous learnings block
    if previous_learnings and len(previous_learnings) > 0:
        learnings_text = "\n\n---\n".join(
            f"**Dossier {i+1}:**\n{learning}"
            for i, learning in enumerate(previous_learnings)
        )
        previous_learnings_block = f"""
## PREVIOUS FINDINGS (from earlier dossiers)

IMPORTANT:
- If URLs are recommended here → PRIORITIZE them!
- If topics are marked as "important" here → search specifically for them!
- Select URLs that provide NEW information, not the same again!
- Avoid duplicates to already scraped URLs!

{learnings_text}
"""
    else:
        previous_learnings_block = ""

    user_prompt = PICK_URLS_USER_PROMPT.format(
        user_query=user_query,
        current_point=current_point,
        thinking_block=thinking_block,
        previous_learnings_block=previous_learnings_block,
        search_results=search_results
    )

    return PICK_URLS_SYSTEM_PROMPT, user_prompt


def parse_pick_urls_response(response: str) -> list[str]:
    """
    Parses the Pick-URLs response (URLs only).

    Security:
    - Response length is limited
    - URLs are validated (SSRF protection)
    - URL length is limited

    Args:
        response: LLM Response

    Returns:
        List of URLs (only safe URLs)
    """
    # Security: Limit response length
    if len(response) > 100_000:
        response = response[:100_000]

    urls = []

    for line in response.strip().split("\n"):
        line = line.strip()
        if line.lower().startswith("url"):
            if ":" in line:
                url = line.split(":", 1)[1].strip()

                # Security: Skip URLs that are too long
                if len(url) > MAX_URL_LENGTH:
                    continue

                # Security: Validate URL (SSRF protection)
                if url.startswith("http") and validate_url(url):
                    urls.append(url)

    return urls[:20]  # Max 20


def parse_pick_urls_full(response: str) -> dict:
    """
    Parses the Pick-URLs response COMPLETELY (URLs + Rejections).

    Security:
    - Response length is limited
    - URLs are validated (SSRF protection)
    - URL length is limited

    Args:
        response: LLM Response

    Returns:
        dict with:
        - urls: List of selected URLs (only safe URLs)
        - rejections: List of rejection reasons (e.g. "5 URLs due to paywall")
    """
    # Security: Limit response length
    if len(response) > 100_000:
        response = response[:100_000]

    urls = []
    rejections = []

    for line in response.strip().split("\n"):
        line = line.strip()
        if line.lower().startswith("url"):
            if ":" in line:
                url = line.split(":", 1)[1].strip()

                # Security: Skip URLs that are too long
                if len(url) > MAX_URL_LENGTH:
                    continue

                # Security: Validate URL (SSRF protection)
                if url.startswith("http") and validate_url(url):
                    urls.append(url)

        elif line.lower().startswith("rejected:"):
            reason = line.split(":", 1)[1].strip()
            if reason and len(reason) < 500:  # Limit reason length
                rejections.append(reason)

    return {
        "urls": urls[:20],
        "rejections": rejections[:10]  # Limit rejections too
    }
