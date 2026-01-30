"""
Think Prompt (Prompt 2)
=======================
LLM analyzes what information is needed and generates search queries.

Recursive: Executed for each point in the Research Plan.
"""

THINK_SYSTEM_PROMPT = """You are an experienced research strategist.

Your task: Analyze the current research point and develop a precise search strategy.
You must determine what information you need and how to find it best.

## CRITICAL: SEARCH QUERY FORMAT

ONLY GENERATE SIMPLE SEARCH TERMS - NO URLS!

WRONG: https://github.com/search?q=adaptive+chunking
WRONG: site:github.com adaptive chunking
RIGHT: adaptive chunking python implementation
RIGHT: RAG chunking strategies 2024

Each search query is a simple text string with keywords, NOT a URL!

## SEARCH STRATEGY PRINCIPLES

1. **Specific**: No generic searches. The more precise, the better the results.
2. **Current**: Include years when recency matters (2024, 2025).
3. **Source-oriented**: Deliberately include keywords like "github", "paper", "docs", "reddit".

## CRITICAL: DIVERSIFICATION (MANDATORY!)

NEVER fire 10 searches in the same direction!

Distribute your searches across AT LEAST 4 different perspectives:
- **Primary**: Official sources, documentation, original repos, papers
- **Community**: Discussions, Reddit, HN, forums, experience reports
- **Practical**: Tutorials, how-tos, implementations, examples
- **Critical**: Problems, limitations, alternatives, comparisons
- **Current**: News, "2024", "new", "latest", trends

EXAMPLE - WRONG (Monoculture):
search 1: RAG chunking techniques
search 2: RAG chunking methods
search 3: RAG chunking strategies
search 4: RAG chunking best practices
→ 4x the same thing!

EXAMPLE - RIGHT (Diversified):
search 1: RAG chunking implementation github
search 2: "chunking problems" RAG reddit
search 3: RAG chunking vs semantic splitting comparison
search 4: RAG chunking 2024 new approaches

CRITICAL - LANGUAGE: Always respond in the same language as the user's original query shown below."""

THINK_USER_PROMPT = """
# CONTEXT

## Main Task
{user_query}

## Current Research Point
{current_point}

{previous_learnings_block}

---

# TASK

Think about what information you need to thoroughly work on the research point
"{current_point}".

Develop a search strategy with concrete Google search queries.

---

# FORMAT (EXACTLY LIKE THIS - Category is MANDATORY!)

=== THINKING ===
[Your thoughts: What do you need? Why? Which aspects are important?]

=== SEARCHES ===
search 1 (Primary): [official source, docs, repo, paper]
search 2 (Primary): [official source, docs, repo, paper]
search 3 (Community): [Reddit, HN, forum, discussion]
search 4 (Community): [Reddit, HN, forum, discussion]
search 5 (Practical): [Tutorial, how-to, example, implementation]
search 6 (Practical): [Tutorial, how-to, example, implementation]
search 7 (Critical): [Problems, limitations, alternatives, comparison]
search 8 (Critical): [Problems, limitations, alternatives, comparison]
search 9 (Current): [News, 2024, 2025, new, latest, trends]
search 10 (Current): [News, 2024, 2025, new, latest, trends]
"""


def build_think_prompt(
    user_query: str,
    current_point: str,
    previous_learnings: list[str] | None = None
) -> tuple[str, str]:
    """
    Builds the Think prompt.

    Args:
        user_query: Main task
        current_point: Current research point
        previous_learnings: List of key learnings from previous points (optional)

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    # Format previous learnings block
    if previous_learnings and len(previous_learnings) > 0:
        learnings_text = "\n\n---\n".join(
            f"**Point {i+1}:**\n{learning}"
            for i, learning in enumerate(previous_learnings)
        )
        previous_learnings_block = f"""
## Previous Findings (from earlier points)

IMPORTANT: You already have this information. Do NOT search for it again!
Focus on NEW aspects relevant to "{current_point}".

{learnings_text}
"""
    else:
        previous_learnings_block = ""

    user_prompt = THINK_USER_PROMPT.format(
        user_query=user_query,
        current_point=current_point,
        previous_learnings_block=previous_learnings_block
    )

    return THINK_SYSTEM_PROMPT, user_prompt


def parse_think_response(response: str) -> tuple[str, list[str]]:
    """
    Parses the Think response.

    Args:
        response: LLM Response

    Returns:
        Tuple (thinking_block, search_list)
    """
    thinking_block = ""
    searches = []

    # Extract thinking block
    if "=== THINKING ===" in response:
        parts = response.split("=== THINKING ===")
        if len(parts) > 1:
            thinking_part = parts[1]
            if "=== SEARCHES ===" in thinking_part:
                thinking_block = thinking_part.split("=== SEARCHES ===")[0].strip()
            else:
                thinking_block = thinking_part.strip()

    # Extract searches
    if "=== SEARCHES ===" in response:
        search_part = response.split("=== SEARCHES ===")[1]
        for line in search_part.strip().split("\n"):
            line = line.strip()
            if line.lower().startswith("search"):
                if ":" in line:
                    query = line.split(":", 1)[1].strip()
                    # URL filter: If LLM generates URLs, extract keywords
                    if query:
                        if query.startswith("http://") or query.startswith("https://"):
                            # URL → try to extract keywords
                            import re
                            # Extract q= parameter or path segments
                            if "q=" in query:
                                match = re.search(r'[?&]q=([^&]+)', query)
                                if match:
                                    query = match.group(1).replace("+", " ").replace("%20", " ")
                                    query = re.sub(r'%[0-9A-Fa-f]{2}', ' ', query)  # URL decode cleanup
                            else:
                                continue  # Skip non-search URLs
                        # Remove URL-like patterns that slip through
                        if "://" in query or query.startswith("site:"):
                            continue
                        if query and len(query) > 3:
                            searches.append(query)

    return thinking_block, searches[:10]  # Max 10
