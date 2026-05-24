"""Web Search Provider.

Retrieves recent web content for breaking changes, release notes, deprecations.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from ...protocol.schemas import ContextPackEntry, SourceType

log = logging.getLogger(__name__)


class WebSearchProvider:
    """Web search provider. Brave API by default when configured."""

    source_type = SourceType.WEB_SEARCH

    def __init__(self) -> None:
        self.api_key = os.environ.get("ARC_SEARCH_API_KEY", "")
        self.provider = os.environ.get("ARC_SEARCH_PROVIDER", "brave")
        self._offline = not bool(self.api_key)
        if self._offline:
            log.info("WebSearch disabled: ARC_SEARCH_API_KEY not set.")

    def retrieve(self, task: str, workspace: Optional[Path] = None) -> list[ContextPackEntry]:
        if self._offline:
            return []
        try:
            return self._real_search(task)
        except Exception as e:
            log.warning("Web search failed: %s", e)
            return []

    def _real_search(self, task: str) -> list[ContextPackEntry]:
        import httpx

        results = []

        # enforcement: not-applicable - Internal CLI context provider, user-invoked tool
        if self.provider == "brave":
            resp = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": task, "count": 5, "result_filter": "web"},
                headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
                timeout=10.0,
            )
            resp.raise_for_status()
            for item in resp.json().get("web", {}).get("results", []):
                results.append(
                    ContextPackEntry(
                        id=f"web-{hash(item.get('url', '')) % 10000:x}",
                        task=task,
                        source=f"web:{item.get('url', '')}",
                        source_type=SourceType.WEB_SEARCH,
                        content=f"# {item.get('title', '')}\n\n{item.get('description', '')}",
                        url=item.get("url"),
                        relevance_score=0.6,
                    )
                )
        return results
