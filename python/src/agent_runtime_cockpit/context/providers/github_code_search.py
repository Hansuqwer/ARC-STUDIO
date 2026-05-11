"""
GitHub Code Search Provider

Uses the GitHub REST API code search endpoint.
Source: https://docs.github.com/en/search-github/github-code-search/understanding-github-code-search-syntax

MOCK_REASON: GitHub token may not be set. Falls back to mock without token.
REAL_IMPLEMENTATION_PATH: Set GITHUB_TOKEN or arc.context.githubToken preference.
LOCAL_FIX_STEPS:
    1. Create a GitHub fine-grained token with public repo read access
    2. export GITHUB_TOKEN=your_token
    3. Or set arc.context.githubToken in ARC settings
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

MOCK_REASON = "GitHub token not set"
REAL_IMPLEMENTATION_PATH = "context/providers/github_code_search.py → _real_search()"
LOCAL_FIX_STEPS = "export GITHUB_TOKEN=<your_token>"
OWNER = "Context Retrieval Agent"
REMOVE_BEFORE = "Beta"

GITHUB_API = "https://api.github.com"


class GitHubCodeSearchProvider:
    """GitHub REST API code search. Falls back to mock when token absent."""

    source_type = SourceType.GITHUB_SEARCH

    def __init__(self) -> None:
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self._mock = not bool(self.token)
        if self._mock:
            log.warning("GitHub: GITHUB_TOKEN not set — using mock. Set GITHUB_TOKEN env var.")

    def retrieve(self, task: str, workspace: Optional[Path] = None) -> list[ContextPackEntry]:
        if self._mock:
            return self._mock_retrieve(task)
        try:
            return self._real_search(task)
        except Exception as e:
            log.warning("GitHub search failed: %s — using mock", e)
            return self._mock_retrieve(task)

    def _real_search(self, task: str) -> list[ContextPackEntry]:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Build a focused query for Theia/agent framework patterns
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
                content_resp = httpx.get(item["url"], headers=headers, timeout=5.0)
                if content_resp.status_code == 200:
                    import base64
                    raw = base64.b64decode(content_resp.json().get("content", "")).decode(errors="ignore")
                    snippet = raw[:800]
                else:
                    snippet = f"[Could not fetch content: {content_resp.status_code}]"
            except Exception:
                snippet = "[Content fetch failed]"

            results.append(ContextPackEntry(
                id=f"gh-{item['sha'][:8]}",
                task=task,
                source=f"github:{item['repository']['full_name']}/{item['path']}",
                source_type=SourceType.GITHUB_SEARCH,
                content=f"# {item['path']}\n```ts\n{snippet}\n```",
                url=item.get("html_url"),
                relevance_score=0.7,
            ))
        return results

    def _mock_retrieve(self, task: str) -> list[ContextPackEntry]:
        return [
            ContextPackEntry(
                id="gh-mock-theia-001",
                task=task,
                source="github:eclipse-theia/theia [MOCK]",
                source_type=SourceType.GITHUB_SEARCH,
                content=(
                    "[MOCK — GITHUB_TOKEN not set]\n\n"
                    "# CommandContribution pattern (fixture)\n\n"
                    "```ts\n"
                    "// Source: packages/core/src/browser/common-frontend-contribution.ts\n"
                    "// Real: https://github.com/eclipse-theia/theia\n"
                    "export class MyContribution implements CommandContribution {\n"
                    "  registerCommands(registry: CommandRegistry): void {\n"
                    "    registry.registerCommand({ id: 'my:cmd', label: 'My Command' }, {\n"
                    "      execute: () => console.log('hello')\n"
                    "    });\n  }\n}\n```"
                ),
                url="https://github.com/eclipse-theia/theia",
                relevance_score=0.35,
            )
        ]
