"""
Vercel Grep Provider

Searches public GitHub repos via grep.app for real-world usage examples.
Source: https://grep.app/
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from ...protocol.schemas import ContextPackEntry, SourceType

log = logging.getLogger(__name__)


class VercelGrepProvider:
    """Grep.app code search provider using its public search endpoint."""

    source_type = SourceType.VERCEL_GREP

    def retrieve(self, task: str, workspace: Optional[Path] = None) -> list[ContextPackEntry]:
        """Try grep.app; return no results when unavailable."""
        try:
            return self._scrape(task)
        except Exception as e:
            log.warning("VercelGrep failed: %s", e)
            return []

    def _scrape(self, task: str) -> list[ContextPackEntry]:
        """Attempt grep.app search (unofficial, may break)."""
        import httpx

        results = []
        query = task.replace(" ", "+")
        headers = {
            "User-Agent": "ARC-Studio/0.1 (context-retrieval; +https://github.com/arc-studio)"
        }

        # Known repos to search
        repos = [
            "eclipse-theia/theia",
            "eclipse-theia/theia-ide",
            "ag-ui-protocol/ag-ui",
        ]

        # enforcement: not-applicable - Internal CLI context provider, user-invoked tool
        for repo in repos[:2]:
            try:
                url = f"https://grep.app/api/search?q={query}&repo={repo}&case=false"
                resp = httpx.get(url, headers=headers, timeout=8.0, follow_redirects=True)
                if resp.status_code == 200:
                    data = resp.json()
                    for hit in data.get("hits", {}).get("hits", [])[:3]:
                        src = hit.get("_source", {})
                        results.append(
                            ContextPackEntry(
                                id=f"grep-{repo.replace('/', '-')}-{hash(src.get('path', '')) % 10000:x}",
                                task=task,
                                source=f"grep.app:{repo}",
                                source_type=SourceType.VERCEL_GREP,
                                content=f"# {src.get('path', '')}\n```\n{src.get('content', '')[:600]}\n```",
                                url=f"https://github.com/{repo}/blob/master/{src.get('path', '')}",
                                relevance_score=min(float(hit.get("_score", 1.0)) / 20.0, 1.0),
                            )
                        )
            except Exception as e:
                log.debug("grep.app request for %s failed: %s", repo, e)

        return results
