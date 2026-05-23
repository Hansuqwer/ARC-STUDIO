"""Materialize a synthetic project on disk under workspace-trust rules."""

from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp


class FixtureProjectLoader:
    def __init__(self, source: Path) -> None:
        self._source = source
        self._dest: Path | None = None

    def __enter__(self) -> Path:
        self._dest = Path(mkdtemp(prefix="arc-fixture-"))
        shutil.copytree(self._source, self._dest, dirs_exist_ok=True)
        return self._dest

    def __exit__(self, *exc_info: object) -> None:
        if self._dest is not None:
            shutil.rmtree(self._dest, ignore_errors=True)
