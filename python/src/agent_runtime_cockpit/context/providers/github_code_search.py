"""GitHub Code Search Provider.

Uses the GitHub REST API code search endpoint.
Source: https://docs.github.com/en/search-github/github-code-search/understanding-github-code-search-syntax
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from ...protocol.schemas import ContextPackEntry, SourceType

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubCodeSearchProvider:
    """GitHub REST API code search when GITHUB_TOKEN is configured."""

    source_type = SourceType.GITHUB_SEARCH

    def __init__(self) -> None:
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self._offline = not bool(self.token)
        if self._offline:
            log.info("GitHub search disabled: GITHUB_TOKEN not set.")

    def retrieve(self, task: str, workspace: Optional[Path] = None) -> list[ContextPackEntry]:
        if self._offline:
            return []
        try:
            return self._real_search(task)
        except Exception as e:
            log.warning("GitHub search failed: %s", e)
            return []

    def _real_search(self, task: str) -> list[ContextPackEntry]:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Build a focused query for Theia/agent framework patterns
        # enforcement: not-applicable - Internal CLI context provider, user-invoked tool
        query = f"{task} repo:eclipse-theia/theia language:TypeScript"
        resp = httpx.get(
            f"{GITHUB_API}/search/code",
            params={"q": query, "per_page": 5},
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("items", []):
            # Fetch file content
            try:
                # enforcement: not-applicable - Internal CLI context provider
                content_resp = httpx.get(item["url"], headers=headers, timeout=5.0)
                if content_resp.status_code == 200:
                    import base64

                    raw = base64.b64decode(content_resp.json().get("content", "")).decode(
                        errors="ignore"
                    )
                    snippet = raw[:800]
                else:
                    snippet = f"[Could not fetch content: {content_resp.status_code}]"
            except Exception:
                snippet = "[Content fetch failed]"

            results.append(
                ContextPackEntry(
                    id=f"gh-{item['sha'][:8]}",
                    task=task,
                    source=f"github:{item['repository']['full_name']}/{item['path']}",
                    source_type=SourceType.GITHUB_SEARCH,
                    content=f"# {item['path']}\n```ts\n{snippet}\n```",
                    url=item.get("html_url"),
                    relevance_score=0.7,
                )
            )
        return results
