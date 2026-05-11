"""
Web Search Provider

Retrieves recent web content for breaking changes, release notes, deprecations.

MOCK_REASON: No search API key configured. Requires Brave, SerpAPI, or Tavily key.
REAL_IMPLEMENTATION_PATH: Set ARC_SEARCH_API_KEY + ARC_SEARCH_PROVIDER env vars.
LOCAL_FIX_STEPS:
    1. Get a Brave Search API key: https://api.search.brave.com/
    2. export ARC_SEARCH_API_KEY=your_key ARC_SEARCH_PROVIDER=brave
OWNER: Context Retrieval Agent
REMOVE_BEFORE: Beta
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional
from ...protocol.schemas import ContextPackEntry, SourceType

log = logging.getLogger(__name__)

MOCK_REASON = "No search API key configured"
REAL_IMPLEMENTATION_PATH = "context/providers/web_search.py → _real_search()"
LOCAL_FIX_STEPS = "export ARC_SEARCH_API_KEY=<key> ARC_SEARCH_PROVIDER=brave"
OWNER = "Context Retrieval Agent"
REMOVE_BEFORE = "Beta"


class WebSearchProvider:
    """Web search provider. Brave API by default; falls back to mock."""

    source_type = SourceType.WEB_SEARCH

    def __init__(self) -> None:
        self.api_key = os.environ.get("ARC_SEARCH_API_KEY", "")
        self.provider = os.environ.get("ARC_SEARCH_PROVIDER", "brave")
        self._mock = not bool(self.api_key)
        if self._mock:
            log.warning("WebSearch: ARC_SEARCH_API_KEY not set — using mock provider.")

    def retrieve(self, task: str, workspace: Optional[Path] = None) -> list[ContextPackEntry]:
        if self._mock:
            return self._mock_retrieve(task)
        try:
            return self._real_search(task)
        except Exception as e:
            log.warning("Web search failed: %s — using mock", e)
            return self._mock_retrieve(task)

    def _real_search(self, task: str) -> list[ContextPackEntry]:
        import httpx
        results = []

        if self.provider == "brave":
            resp = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": task, "count": 5, "result_filter": "web"},
                headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
                timeout=10.0,
            )
            resp.raise_for_status()
            for item in resp.json().get("web", {}).get("results", []):
                results.append(ContextPackEntry(
                    id=f"web-{hash(item.get('url',''))%10000:x}",
                    task=task,
                    source=f"web:{item.get('url','')}",
                    source_type=SourceType.WEB_SEARCH,
                    content=f"# {item.get('title','')}\n\n{item.get('description','')}",
                    url=item.get("url"),
                    relevance_score=0.6,
                ))
        return results

    def _mock_retrieve(self, task: str) -> list[ContextPackEntry]:
        return [
            ContextPackEntry(
                id="web-mock-001",
                task=task,
                source="web:search [MOCK — ARC_SEARCH_API_KEY not set]",
                source_type=SourceType.WEB_SEARCH,
                content=(
                    "[MOCK] Web search unavailable. "
                    "Set ARC_SEARCH_API_KEY and ARC_SEARCH_PROVIDER to enable.\n\n"
                    "Suggested query: \"Eclipse Theia 1.71 custom extension 2025\"\n"
                    "Suggested query: \"LangGraph StateGraph 2025 breaking changes\""
                ),
                url=None,
                relevance_score=0.1,
            )
        ]
