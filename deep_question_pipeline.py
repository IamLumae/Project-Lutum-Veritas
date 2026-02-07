"""
Deep Question Pipeline - 6-Stage Verification System

Architecture:
C1: Intent Analysis → C2: Knowledge Requirements → C3: Search Queries
→ Scrape → C4: Answer → C5: Claim Audit → C6: Verification → Final Response

All LLM responses formatted as first-person "thinking process" for live display.
"""

import os
import json
import re
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests

from lutum.core.log_config import get_logger
logger = get_logger("lutum.deep_question_pipeline")

# Model
MODEL = "google/gemini-2.5-flash-lite-preview-09-2025"

# Output directory
OUTPUT_DIR = Path(__file__).parent / "deep_question_runs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Lutum scrapers path
LUTUM_ROOT = Path(__file__).parent
import sys
sys.path.insert(0, str(LUTUM_ROOT))


class DeepQuestionPipeline:
    """Complete Deep Question pipeline with 6-stage verification."""

    def __init__(self, user_query: str, api_key: str):
        self.user_query = user_query
        self.api_key = api_key
        self.flow_log = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _call_openrouter(self, prompt: str, stage: str) -> str:
        """Make API call to OpenRouter with Gemini 2.5 Flash Lite."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        # Log request
        self.flow_log.append({
            "stage": stage,
            "type": "request",
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "model": MODEL
        })

        logger.info(f"[{stage}] Calling OpenRouter...")

        # Make request
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"OpenRouter API Error: {response.status_code} - {response.text}")

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Log response
        self.flow_log.append({
            "stage": stage,
            "type": "response",
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "tokens": result.get("usage", {})
        })

        logger.info(f"[{stage}] OK Response received ({len(content)} chars)")

        return content

    async def _search_ddg_async(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search DuckDuckGo and return results (copied from Veritas)."""
        try:
            from ddgs import DDGS

            clean_query = query.strip().replace('"', '').replace("'", '')

            loop = asyncio.get_event_loop()
            # Run DDG search in executor (it's sync)
            def search():
                with DDGS() as ddgs:
                    return list(ddgs.text(
                        clean_query,
                        region="wt-wt",
                        safesearch="moderate",
                        max_results=max_results
                    ))

            results = await loop.run_in_executor(None, search)

            formatted = []
            for r in results:
                formatted.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })

            return formatted

        except Exception as e:
            logger.error(f"DDG search failed: {clean_query[:30]} - {e}")
            return []

    async def _scrape_single_url_async(self, url: str, index: int, total: int) -> Dict[str, Any]:
        """
        Scrape single URL with dedicated browser instance.
        Browser opens, scrapes, closes immediately - no RAM leak!
        """
        from camoufox.async_api import AsyncCamoufox
        from camoufox import DefaultAddons

        logger.info(f"[{index}/{total}] Scraping: {url[:60]}...")

        browser = None
        try:
            # Each URL gets own browser instance
            # Exclude UBO addon - not needed for scraping, and download fails in frozen builds
            browser = await AsyncCamoufox(headless=True, exclude_addons=[DefaultAddons.UBO]).start()
            page = await browser.new_page()

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=15000  # 15s timeout (shorter for speed)
            )
            await asyncio.sleep(1.0)  # Minimal wait for JS

            text = await page.evaluate("document.body?.innerText || ''")

            if text and len(text.strip()) > 100:
                logger.info(f"[{index}/{total}] OK: {len(text)} chars")
                return {
                    "url": url,
                    "content": text[:10000],
                    "success": True
                }
            else:
                logger.warning(f"[{index}/{total}] FAIL: Empty content from {url[:60]}")
                return {
                    "url": url,
                    "content": "",
                    "success": False,
                    "error": "Empty content"
                }

        except Exception as e:
            logger.error(f"[{index}/{total}] Scrape FAIL: {url[:40]} - {e}")
            return {
                "url": url,
                "content": "",
                "success": False,
                "error": str(e)
            }

        finally:
            # CRITICAL: Close browser IMMEDIATELY after scraping!
            if browser:
                try:
                    await asyncio.wait_for(browser.close(), timeout=5.0)
                except Exception as e:
                    logger.warning(f"[{index}/{total}] Browser close failed: {str(e)[:30]}")

    async def _search_and_scrape_async(self, queries: List[str], stage: str = "SCRAPE", progress_callback=None) -> List[Dict[str, str]]:
        """
        Standalone search+scrape with PARALLEL scraping:
        1. DDG Search (get URLs from queries)
        2. Limit to exactly 10 URLs
        3. Parallel scrape with separate browsers (RAM-safe with immediate close)

        Args:
            queries: List of search queries
            stage: Stage name for logging
            progress_callback: Optional async callback(done: int, total: int) for progress updates
        """
        logger.info(f"[{stage}] DDG Search + PARALLEL Camoufox Scrape...")

        try:
            from camoufox.async_api import AsyncCamoufox

            # Step 1: Search all queries on DDG
            logger.info(f"Step 1: Searching DDG for {len(queries)} queries...")
            all_urls = []
            for i, query in enumerate(queries, 1):
                logger.debug(f"[{i}/{len(queries)}] DDG: {query[:50]}...")
                results = await self._search_ddg_async(query, max_results=3)

                # Take first URL from results
                if results and len(results) > 0:
                    url = results[0]["url"]
                    all_urls.append(url)
                    logger.debug(f"[{i}/{len(queries)}] Found: {url[:60]}...")
                else:
                    logger.warning(f"[{i}/{len(queries)}] DDG: No results for '{query[:40]}'")

                # Rate limit
                if i < len(queries):
                    await asyncio.sleep(0.3)

            # Limit to exactly 10 URLs
            all_urls = all_urls[:10]
            logger.info(f"Step 1 Done: {len(all_urls)} URLs collected (limited to 10)")

            if not all_urls:
                return []

            # Step 2: PARALLEL scrape with separate browser per URL
            logger.info(f"Step 2: Scraping {len(all_urls)} URLs in PARALLEL (15s timeout each)...")

            # Create scraping tasks (each with own browser)
            if progress_callback:
                # Track progress as each task completes
                completed = 0
                results = []

                async def scrape_with_progress(url, index, total):
                    nonlocal completed
                    result = await self._scrape_single_url_async(url, index, total)
                    completed += 1
                    if progress_callback:
                        await progress_callback(completed, total)
                    return result

                tasks = [
                    scrape_with_progress(url, i+1, len(all_urls))
                    for i, url in enumerate(all_urls)
                ]
                results = await asyncio.gather(*tasks)
            else:
                # No progress tracking
                tasks = [
                    self._scrape_single_url_async(url, i+1, len(all_urls))
                    for i, url in enumerate(all_urls)
                ]
                results = await asyncio.gather(*tasks)

            logger.info(f"Step 2 Done: {sum(1 for r in results if r['success'])}/{len(results)} successful")

            # Log
            self.flow_log.append({
                "stage": stage,
                "type": "scraping",
                "timestamp": datetime.now().isoformat(),
                "queries": queries,
                "urls": all_urls,
                "results": results,
                "success_count": sum(1 for r in results if r["success"])
            })

            return results

        except Exception as e:
            logger.error(f"Search+Scrape FAILED: {str(e)}")
            self.flow_log.append({
                "stage": stage,
                "type": "scraping",
                "timestamp": datetime.now().isoformat(),
                "queries": queries,
                "error": str(e)
            })
            return []

    def _scrape_sources(self, queries: List[str], stage: str) -> List[Dict[str, str]]:
        """Wrapper to run async search+scrape."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(self._search_and_scrape_async(queries, stage))
            return results
        finally:
            loop.close()

    def _parse_numbered_list(self, text: str, prefix: str = "") -> List[str]:
        """
        Parse numbered list from LLM response.

        Examples:
          1. Query here
          2. Another query
        OR
          Query 1: something
          Query 2: something else
        """
        lines = text.strip().split('\n')
        items = []

        for line in lines:
            line = line.strip()

            # Match patterns like "1.", "1:", "Query 1:", etc.
            if re.match(r'^\d+[\.:)]', line) or re.match(r'^(Query|Suche|Search)\s+\d+:', line, re.IGNORECASE):
                # Extract content after number/colon
                content = re.sub(r'^(\d+[\.:)]|[A-Za-z]+\s+\d+:)\s*', '', line).strip()
                if content:
                    items.append(content)

        return items

    def _format_scraped_results(self, results: List[Dict[str, str]]) -> str:
        """Format scraped results for LLM context."""
        if not results:
            return "Keine Quellen gefunden."

        formatted = []
        for i, result in enumerate(results, 1):
            if result.get("success"):
                formatted.append(f"[{i}] URL: {result.get('url', 'N/A')}\nContent: {result['content'][:2000]}...\n")
            else:
                formatted.append(f"[{i}] URL: {result.get('url', 'N/A')}\nError: {result.get('error', 'Unknown')}\n")

        return "\n".join(formatted)

    def run(self) -> Dict[str, Any]:
        """Run the complete Deep Question pipeline."""

        logger.info(f"DEEP QUESTION PIPELINE - Query: {self.user_query} - Session: {self.session_id}")

        # =====================================================================
        # C1: Intent Analysis
        # =====================================================================
        c1_prompt = f"""USER QUERY:
{self.user_query}

Analyze the language of the user query above and respond in that same language.

---

Explain in first person what you understand they want to know.

Format your response naturally, starting with:
"Der Nutzer möchte..." (if German) or "The user wants to know..." (if English)

Explain in 3-5 sentences:
- What exactly they are asking
- What they want to know
- What kind of answer they expect

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c1_response = self._call_openrouter(c1_prompt, "C1_Intent_Analysis")

        # =====================================================================
        # C2: Knowledge Requirements
        # =====================================================================
        c2_prompt = f"""USER QUERY:
{self.user_query}

Analyze the language of the user query above and respond in that same language.

---

Based on the user query and intent analysis below, explain in first person what information you need to answer comprehensively.

Intent Analysis:
{c1_response}

---

Format your response naturally, starting with:
"Um diese Frage zu beantworten, benötige ich..." (if German) or "To answer this question, I need..." (if English)

List in bullet points:
- What specific information you need from the internet
- What data sources would be most reliable
- What aspects need to be researched

Remember: Your training data is irrelevant. Only assess what information is NEEDED, not what you think you already know.

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c2_response = self._call_openrouter(c2_prompt, "C2_Knowledge_Requirements")

        # =====================================================================
        # C3: Search Query Formulation
        # =====================================================================
        c3_prompt = f"""USER QUERY:
{self.user_query}

Analyze the language of the user query above and respond in that same language.

---

Based on all previous analysis, explain in first person which search queries you will use to gather information.

Intent Analysis:
{c1_response}

Knowledge Requirements:
{c2_response}

---

Format your response naturally, starting with:
"Ich sollte nun Quellen suchen um die Frage zu beantworten. Ich entscheide mich für folgende 10 Suchbegriffe:" (if German)
or
"I should now search for sources to answer the question. I will use these 10 search terms:" (if English)

Then list exactly 10 search queries as a numbered list:
1. [first search query]
2. [second search query]
...
10. [tenth search query]

The first 5 queries should target direct information.
The last 5 queries should diversify or verify the information.

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c3_response = self._call_openrouter(c3_prompt, "C3_Search_Queries")

        # Parse search queries
        search_queries = self._parse_numbered_list(c3_response)
        logger.info(f"[Parser] Extracted {len(search_queries)} search queries")

        # =====================================================================
        # SCRAPING PHASE 1: Main Research
        # =====================================================================
        scraped_results = self._scrape_sources(search_queries, "Scraping_Phase_1")
        scraped_formatted = self._format_scraped_results(scraped_results)

        # =====================================================================
        # C4: Answer Synthesis
        # =====================================================================
        c4_prompt = f"""USER QUERY:
{self.user_query}

Analyze the language of the user query above and respond in that same language.

---

Based on all information gathered, compose a comprehensive answer.

Intent Analysis:
{c1_response}

Knowledge Requirements:
{c2_response}

Scraped Sources:
{scraped_formatted}

---

Format your response naturally, starting with:
"Ich habe nun die Quellen analysiert. Basierend auf den gefundenen Daten kann ich folgendes beantworten:" (if German)
or
"I have analyzed the sources. Based on the data found, I can answer as follows:" (if English)

Then provide your answer:
- Start with a brief introduction (1-2 sentences)
- Answer thoroughly but concisely
- No filler sentences - only substantial information
- Use citations [1], [2], [3] etc. for every factual claim from the sources
- Data from internet sources ALWAYS takes precedence over your training data

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c4_response = self._call_openrouter(c4_prompt, "C4_Answer_Synthesis")

        # =====================================================================
        # C5: Claim Audit
        # =====================================================================
        c5_prompt = f"""USER QUERY:
{self.user_query}

Analyze the language of the user query above and respond in that same language.

---

Analyze the AI answer below and explain in first person which claims need fact-checking.

AI Answer to Verify:
{c4_response}

---

Format your response naturally, starting with:
"Ich überprüfe nun die Aussagen auf Richtigkeit. Folgende Claims müssen verifiziert werden:" (if German)
or
"I am now checking the statements for correctness. The following claims need verification:" (if English)

Then list EXACTLY 10 main claims from the answer as a numbered list, each with a verification search query:
1. [claim] → [verification search query]
2. [claim] → [verification search query]
...
10. [claim] → [verification search query]

IMPORTANT: Always create exactly 10 verification queries, no more, no less.
Focus on the most important verifiable factual claims.

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c5_response = self._call_openrouter(c5_prompt, "C5_Claim_Audit")

        # Parse verification queries (extract after →)
        verification_queries = []
        for line in c5_response.split('\n'):
            if '→' in line:
                query = line.split('→', 1)[1].strip()
                if query:
                    verification_queries.append(query)

        if not verification_queries:
            # Fallback: parse as numbered list
            verification_queries = self._parse_numbered_list(c5_response)

        logger.info(f"[Parser] Extracted {len(verification_queries)} verification queries")

        # =====================================================================
        # SCRAPING PHASE 2: Verification
        # =====================================================================
        verification_results = self._scrape_sources(verification_queries, "Scraping_Phase_2")
        verification_formatted = self._format_scraped_results(verification_results)

        # =====================================================================
        # C6: Verification Report
        # =====================================================================
        c6_prompt = f"""USER QUERY:
{self.user_query}

Analyze the language of the user query above and respond in that same language.

---

Based on the verification sources below, fact-check the AI answer.

AI Answer:
{c4_response}

Verification Sources:
{verification_formatted}

---

FORMAT (MANDATORY - follow exactly!):

1) Start with a brief summary of what you verified.

2) For each major claim, write:
   - **Claim:** [the claim]
   - **Status:** CONFIRMED / CONTRADICTED / UNCERTAIN
   - **Evidence:** [cite with [V1], [V2] etc.]

3) END your response with EXACTLY ONE of these lines (on its own line):
   Validated: Yes
   OR
   Validated: No

Use "Validated: Yes" if the main claims are confirmed or mostly confirmed.
Use "Validated: No" if significant contradictions were found.

---

REMINDER: Respond in the same language as the user query above. The "Validated: Yes/No" line must be in English regardless of response language."""

        c6_response = self._call_openrouter(c6_prompt, "C6_Verification_Report")

        # =====================================================================
        # Final Response Assembly
        # =====================================================================
        final_response = f"""{c4_response}

---

## Verification Report

{c6_response}"""

        self.flow_log.append({
            "stage": "Final_Response",
            "type": "output",
            "timestamp": datetime.now().isoformat(),
            "content": final_response
        })

        # Save flow log
        log_path = self._save_flow_log()

        logger.info(f"PIPELINE COMPLETE - Flow log saved: {log_path}")

        return {
            "user_query": self.user_query,
            "final_response": final_response,
            "session_id": self.session_id,
            "flow_log_path": str(log_path),
            "stages": {
                "c1_intent": c1_response,
                "c2_knowledge": c2_response,
                "c3_queries": c3_response,
                "c4_answer": c4_response,
                "c5_audit": c5_response,
                "c6_verification": c6_response
            }
        }

    def _save_flow_log(self) -> Path:
        """Save complete flow log as JSON."""
        output_file = OUTPUT_DIR / f"deep_question_{self.session_id}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "session_id": self.session_id,
                "user_query": self.user_query,
                "timestamp": datetime.now().isoformat(),
                "model": MODEL,
                "flow": self.flow_log
            }, f, ensure_ascii=False, indent=2)

        return output_file


if __name__ == "__main__":
    # Test queries - CLI mode uses print for console output
    test_queries = [
        "Hat Adolf Hitler sich selbst erschossen?",
        "War die Corona Impfung Betrug?",
        "Gehört Taiwan zu China?"
    ]

    print(f"DEEP QUESTION PIPELINE - BATCH TEST RUN ({len(test_queries)} queries)")

    for i, query in enumerate(test_queries, 1):
        print(f"\n# QUERY {i}/{len(test_queries)}")
        pipeline = DeepQuestionPipeline(query, api_key=os.environ.get("OPENROUTER_API_KEY", ""))
        result = pipeline.run()
        print(f"[RESULT {i}] Session: {result['session_id']} Log: {result['flow_log_path']}")
