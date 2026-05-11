"""Context Pack Generator — creates and saves context packs."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .engine import ContextEngine
from .cache import ContextCache
from .ranker import rank
from ..protocol.schemas import ContextPackEntry

log = logging.getLogger(__name__)


class ContextPackGenerator:
    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.engine = ContextEngine()
        self.cache = ContextCache()
        self.output_dir = output_dir or Path("docs/context-packs")

    def generate(self, task: str, workspace: Optional[Path] = None,
                 save: bool = True) -> list[ContextPackEntry]:
        ws_str = str(workspace) if workspace else None

        # Check cache
        cached = self.cache.get(task, ws_str)
        if cached:
            log.debug("Context pack served from cache for task: %s", task)
            return cached

        entries = self.engine.retrieve(task, workspace)
        entries = rank(entries, task)

        self.cache.set(task, entries, ws_str)

        if save:
            self._save(task, entries)

        return entries

    def _save(self, task: str, entries: list[ContextPackEntry]) -> None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            slug = task.lower().replace(" ", "-")[:40]
            ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            out_path = self.output_dir / f"pack-{slug}-{ts}.json"
            out_path.write_text(json.dumps(
                [e.model_dump() for e in entries], indent=2, default=str
            ))
            log.info("Context pack saved: %s", out_path)
        except Exception as e:
            log.warning("Failed to save context pack: %s", e)
