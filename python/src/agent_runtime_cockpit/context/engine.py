"""ARC Context Engine — orchestrates all providers."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .providers.local_repo import LocalRepoProvider
from .providers.context7 import Context7Provider
from .providers.vercel_grep import VercelGrepProvider
from .providers.github_code_search import GitHubCodeSearchProvider
from .providers.web_search import WebSearchProvider
from ..protocol.schemas import ContextPackEntry

log = logging.getLogger(__name__)


class ContextEngine:
    """Orchestrates all context providers and merges results."""

    def __init__(self) -> None:
        self.providers = [
            LocalRepoProvider(),
            Context7Provider(),
            VercelGrepProvider(),
            GitHubCodeSearchProvider(),
            WebSearchProvider(),
        ]

    def retrieve(self, task: str, workspace: Optional[Path] = None,
                 max_entries: int = 20) -> list[ContextPackEntry]:
        all_entries: list[ContextPackEntry] = []

        for provider in self.providers:
            try:
                entries = provider.retrieve(task, workspace)
                all_entries.extend(entries)
                log.debug("Provider %s returned %d entries", type(provider).__name__, len(entries))
            except Exception as e:
                log.warning("Provider %s failed: %s", type(provider).__name__, e)

        # Deduplicate by content hash
        seen: set[int] = set()
        unique: list[ContextPackEntry] = []
        for entry in all_entries:
            h = hash(entry.content[:200])
            if h not in seen:
                seen.add(h)
                unique.append(entry)

        # Sort by relevance
        unique.sort(key=lambda e: -e.relevance_score)
        return unique[:max_entries]
