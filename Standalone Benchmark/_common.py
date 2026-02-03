import argparse
import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

MODEL = "google/gemini-2.5-flash-lite-preview-09-2025"
OPENROUTER_API_KEY = "sk-REPLACE_WITH_OPENROUTER_KEY"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

MAX_SCRAPE_CONCURRENCY = 10


@dataclass
class RunContext:
    run_id: str
    output_root: Path
    stage: str
    log_file: Path


class JsonStore:
    def __init__(self, base_dir: Path, logger: logging.Logger) -> None:
        self.base_dir = base_dir
        self.logger = logger
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        backup_path = path.with_suffix(path.suffix + ".bak")
        with backup_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        self.logger.debug("Saved JSON %s", path)

    def write(self, name: str, payload: Any) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        path = self.base_dir / f"{name}_{timestamp}.json"
        self._atomic_write(path, payload)
        return path

    def write_named(self, filename: str, payload: Any) -> Path:
        path = self.base_dir / filename
        self._atomic_write(path, payload)
        return path


def setup_logger(log_file: Path) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(log_file.stem + str(time.time()))
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def ensure_run_context(run_id: str, output_root: Path, stage: str) -> RunContext:
    stage_dir = output_root / run_id / stage
    log_file = stage_dir / "run.log"
    return RunContext(run_id=run_id, output_root=output_root, stage=stage, log_file=log_file)


def parse_numbered_list(text: str) -> List[str]:
    lines = text.strip().splitlines()
    items: List[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d+[\.:\)]", line) or re.match(r"^[A-Za-z]+\s+\d+:", line):
            content = re.sub(r"^(\d+[\.:\)]|[A-Za-z]+\s+\d+:)\s*", "", line).strip()
            if content:
                items.append(content)
        elif line.startswith("-"):
            items.append(line.lstrip("- ").strip())
    return items


def call_openrouter(prompt: str, stage: str, store: JsonStore, logger: logging.Logger) -> str:
    logger.info("Calling OpenRouter stage=%s", stage)
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    store.write(
        f"request_{stage}",
        {
            "stage": stage,
            "timestamp": datetime.utcnow().isoformat(),
            "prompt": prompt,
            "model": MODEL,
        },
    )

    response = requests.post(
        OPENROUTER_BASE_URL,
        headers=headers,
        json=payload,
        timeout=90,
    )
    if response.status_code != 200:
        logger.error("OpenRouter error %s: %s", response.status_code, response.text)
        raise RuntimeError(f"OpenRouter API Error: {response.status_code} - {response.text}")

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    store.write(
        f"response_{stage}",
        {
            "stage": stage,
            "timestamp": datetime.utcnow().isoformat(),
            "content": content,
            "usage": data.get("usage", {}),
        },
    )

    logger.info("OpenRouter response stored (%s chars)", len(content))
    return content


async def search_ddg(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    from ddgs import DDGS

    clean_query = query.strip().replace('"', "").replace("'", "")

    def _search() -> List[Dict[str, str]]:
        with DDGS() as ddgs:
            return list(
                ddgs.text(clean_query, region="wt-wt", safesearch="moderate", max_results=max_results)
            )

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _search)
    formatted = []
    for result in results:
        formatted.append(
            {
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "snippet": result.get("body", ""),
            }
        )
    return formatted


async def scrape_urls(
    urls: Iterable[str],
    logger: logging.Logger,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> List[Dict[str, Any]]:
    from camoufox.async_api import AsyncCamoufox

    semaphore = semaphore or asyncio.Semaphore(MAX_SCRAPE_CONCURRENCY)

    async def _scrape(url: str, index: int, total: int) -> Dict[str, Any]:
        async with semaphore:
            logger.info("Scraping %s/%s: %s", index, total, url)
            browser = None
            try:
                browser = await AsyncCamoufox(headless=True).start()
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1.0)
                text = await page.evaluate("document.body?.innerText || ''")
                if text and len(text.strip()) > 100:
                    return {"url": url, "content": text[:10000], "success": True}
                return {"url": url, "content": "", "success": False, "error": "Empty content"}
            except Exception as exc:
                return {"url": url, "content": "", "success": False, "error": str(exc)}
            finally:
                if browser:
                    try:
                        await asyncio.wait_for(browser.close(), timeout=5.0)
                    except Exception:
                        logger.warning("Browser close failed for %s", url)

    url_list = list(urls)
    total = len(url_list)
    tasks = [
        _scrape(url, index + 1, total)
        for index, url in enumerate(url_list)
    ]
    return await asyncio.gather(*tasks)


def update_status(store: JsonStore, status: str, data: Optional[Dict[str, Any]] = None) -> None:
    payload = {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if data:
        payload.update(data)
    store.write_named("status.json", payload)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_checkpoint(store: JsonStore, checkpoint: Dict[str, Any]) -> None:
    store.write_named("checkpoint.json", checkpoint)


def build_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--id", required=True, help="Run identifier used to store outputs")
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent / "outputs"),
        help="Base directory for outputs",
    )
    parser.add_argument("--resume", action="store_true", help="Skip steps that already exist")
    return parser
