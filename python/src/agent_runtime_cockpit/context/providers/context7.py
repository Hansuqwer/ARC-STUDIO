"""
Context7 Provider

Retrieves current, version-specific library documentation via the Context7 API.
Source: https://context7.com/docs/api-guide

MOCK_REASON: Context7 API key not available in sandbox environment.
REAL_IMPLEMENTATION_PATH: Set ARC_CONTEXT7_API_KEY env var or arc.context.context7ApiKey preference.
LOCAL_FIX_STEPS:
    1. Get API key from https://context7.com/
    2. Set env: export ARC_CONTEXT7_API_KEY=your_key
    3. Or set in ARC settings: arc.context.context7ApiKey
OWNER: Context Retrieval Agent
REMOVE_BEFORE: Beta
"""
from __future__ import annotations

import logging
import os
from typing import Optional
from pathlib import Path
from ...protocol.schemas import ContextPackEntry, SourceType

log = logging.getLogger(__name__)

MOCK_REASON = "Context7 API key not set"
REAL_IMPLEMENTATION_PATH = "context/providers/context7.py → _real_retrieve()"
LOCAL_FIX_STEPS = "export ARC_CONTEXT7_API_KEY=<your_key>"
OWNER = "Context Retrieval Agent"
REMOVE_BEFORE = "Beta"

CONTEXT7_BASE_URL = "https://api.context7.com/v1"

# Well-known Context7 library IDs (verified against context7.com)
KNOWN_LIBRARY_IDS = {
    "theia": "/eclipse-theia/theia",
    "langgraph": "/langchain-ai/langgraph",
    "pydantic": "/pydantic/pydantic",
    "ag-ui": "/ag-ui-protocol/ag-ui",
    "textual": "/Textualize/textual",
    "typer": "/tiangolo/typer",
    "aiohttp": "/aio-libs/aiohttp",
}


class Context7Provider:
    """Retrieves docs from Context7 API. Falls back to mock when key absent."""

    source_type = SourceType.CONTEXT7

    def __init__(self) -> None:
        self.api_key = os.environ.get("ARC_CONTEXT7_API_KEY", "")
        self._mock = not bool(self.api_key)
        if self._mock:
            log.warning("Context7: API key not set — using mock provider. Set ARC_CONTEXT7_API_KEY.")

    def retrieve(self, task: str, workspace: Optional[Path] = None) -> list[ContextPackEntry]:
        if self._mock:
            return self._mock_retrieve(task)
        return self._real_retrieve(task)

    def _real_retrieve(self, task: str) -> list[ContextPackEntry]:
        """Real Context7 API call."""
        try:
            import httpx
            results = []
            keywords = task.lower().split()

            # Determine which library IDs are relevant to the task
            relevant_libs = [
                (name, lib_id) for name, lib_id in KNOWN_LIBRARY_IDS.items()
                if any(name in kw or kw in name for kw in keywords)
            ] or list(KNOWN_LIBRARY_IDS.items())[:2]

            for lib_name, lib_id in relevant_libs[:3]:
                try:
                    resp = httpx.get(
                        f"{CONTEXT7_BASE_URL}/search",
                        params={"libraryId": lib_id, "query": task, "tokens": 4000},
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("results", [])[:3]:
                            results.append(ContextPackEntry(
                                id=f"ctx7-{lib_name}-{hash(item.get('url',''))%10000:x}",
                                task=task,
                                source=f"context7:{lib_name}",
                                source_type=SourceType.CONTEXT7,
                                content=item.get("content", "")[:1200],
                                url=item.get("url"),
                                freshness=item.get("version"),
                                relevance_score=item.get("score", 0.5),
                            ))
                except Exception as e:
                    log.warning("Context7 request for %s failed: %s", lib_name, e)

            return results
        except ImportError:
            log.warning("httpx not installed — cannot use real Context7 provider")
            return self._mock_retrieve(task)

    def _mock_retrieve(self, task: str) -> list[ContextPackEntry]:
        """Mock retrieval — clearly marked, returns plausible fixture."""
        return [
            ContextPackEntry(
                id="ctx7-mock-theia-001",
                task=task,
                source="context7:eclipse-theia/theia [MOCK]",
                source_type=SourceType.CONTEXT7,
                content=(
                    "[MOCK — Context7 API key not set]\n\n"
                    "# Theia Extension Pattern (fixture)\n\n"
                    "```ts\n"
                    "// CommandContribution example\n"
                    "import { CommandContribution, CommandRegistry } from '@theia/core/lib/common';\n"
                    "// theiaExtensions: [{ frontend: 'lib/browser/my-module' }]\n"
                    "// bind(CommandContribution).toService(MyContribution);\n"
                    "```\n\n"
                    "Real docs: https://theia-ide.org/docs/extensions/"
                ),
                url="https://theia-ide.org/docs/extensions/",
                freshness="1.71.0",
                relevance_score=0.4,
            ),
        ]
