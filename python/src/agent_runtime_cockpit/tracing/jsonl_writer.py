"""JSONL trace writer for run event persistence."""
from __future__ import annotations

import json
import pathlib
from typing import Any


class JsonlTraceWriter:
    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self._fp = None

    def __enter__(self) -> "JsonlTraceWriter":
        self._fp = self.path.open("a", encoding="utf-8")
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._fp:
            self._fp.flush()
            self._fp.close()

    def write(self, event: dict[str, Any]) -> None:
        if self._fp:
            self._fp.write(json.dumps(event, separators=(",", ":")) + "\n")
