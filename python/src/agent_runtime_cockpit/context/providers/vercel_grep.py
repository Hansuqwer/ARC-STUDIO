"""
Vercel Grep Provider

Searches public GitHub repos via grep.app for real-world usage examples.
Source: https://grep.app/

MOCK_REASON: grep.app has no official public API. This uses scraping heuristics.
REAL_IMPLEMENTATION_PATH: If grep.app exposes an API, replace _scrape() with proper calls.
LOCAL_FIX_STEPS: Check https://grep.app/ for API availability; implement OAuth if required.
OWNER: Context Retrieval Agent
REMOVE_BEFORE: Beta
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from ...protocol.schemas import ContextPackEntry, SourceType

log = logging.getLogger(__name__)

MOCK_REASON = "grep.app has no official public API"
REAL_IMPLEMENTATION_PATH = "context/providers/vercel_grep.py → _scrape()"
LOCAL_FIX_STEPS = "Check https://grep.app/ for an official API"
OWNER = "Context Retrieval Agent"
REMOVE_BEFORE = "Beta"


class VercelGrepProvider:
    """Grep.app code search provider. Falls back to mock when unavailable."""

    source_type = SourceType.VERCEL_GREP

    def retrieve(self, task: str, workspace: Optional[Path] = None) -> list[ContextPackEntry]:
        """Try real grep.app, fall back to mock."""
        try:
            return self._scrape(task)
        except Exception as e:
            log.warning("VercelGrep: failed (%s) — returning mock", e)
            return self._mock_retrieve(task)

    def _scrape(self, task: str) -> list[ContextPackEntry]:
        """Attempt grep.app search (unofficial, may break)."""
        import httpx
        results = []
        query = task.replace(" ", "+")
        headers = {"User-Agent": "ARC-Studio/0.1 (context-retrieval; +https://github.com/arc-studio)"}

        # Known repos to search
        repos = [
            "eclipse-theia/theia",
            "eclipse-theia/theia-ide",
            "ag-ui-protocol/ag-ui",
        ]

        for repo in repos[:2]:
            try:
                url = f"https://grep.app/api/search?q={query}&repo={repo}&case=false"
                resp = httpx.get(url, headers=headers, timeout=8.0, follow_redirects=True)
                if resp.status_code == 200:
                    data = resp.json()
                    for hit in data.get("hits", {}).get("hits", [])[:3]:
                        src = hit.get("_source", {})
                        results.append(ContextPackEntry(
                            id=f"grep-{repo.replace('/', '-')}-{hash(src.get('path',''))%10000:x}",
                            task=task,
                            source=f"grep.app:{repo}",
                            source_type=SourceType.VERCEL_GREP,
                            content=f"# {src.get('path', '')}\n```\n{src.get('content', '')[:600]}\n```",
                            url=f"https://github.com/{repo}/blob/master/{src.get('path','')}",
                            relevance_score=min(float(hit.get("_score", 1.0)) / 20.0, 1.0),
                        ))
            except Exception as e:
                log.debug("grep.app request for %s failed: %s", repo, e)

        return results if results else self._mock_retrieve(task)

    def _mock_retrieve(self, task: str) -> list[ContextPackEntry]:
        return [
            ContextPackEntry(
                id="grep-mock-theia-001",
                task=task,
                source="grep.app:eclipse-theia/theia [MOCK]",
                source_type=SourceType.VERCEL_GREP,
                content=(
                    "[MOCK — grep.app API unavailable]\n\n"
                    "# ReactWidget pattern from eclipse-theia/theia (fixture)\n\n"
                    "```ts\n"
                    "@injectable()\nexport class MyWidget extends ReactWidget {\n"
                    "  protected render(): React.ReactNode {\n"
                    "    return <div>Hello ARC</div>;\n  }\n}\n```\n\n"
                    "Real source: https://github.com/eclipse-theia/theia"
                ),
                url="https://github.com/eclipse-theia/theia",
                relevance_score=0.35,
            )
        ]
