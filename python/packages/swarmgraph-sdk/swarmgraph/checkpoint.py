from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .state import SwarmCheckpoint


class CheckpointStore(Protocol):
    def save(self, checkpoint: SwarmCheckpoint) -> Path: ...

    def load(self, checkpoint_id: str) -> SwarmCheckpoint: ...

    def list_ids(self) -> list[str]: ...


class JsonFileCheckpointStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: SwarmCheckpoint) -> Path:
        path = self._path(checkpoint.id)
        path.write_text(checkpoint.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, checkpoint_id: str) -> SwarmCheckpoint:
        path = self._path(checkpoint_id)
        return SwarmCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))

    def list_ids(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))

    def _path(self, checkpoint_id: str) -> Path:
        if "/" in checkpoint_id or "\\" in checkpoint_id or checkpoint_id in {"", ".", ".."}:
            raise ValueError(f"invalid checkpoint id: {checkpoint_id!r}")
        return self.root / f"{checkpoint_id}.json"


__all__ = ["CheckpointStore", "JsonFileCheckpointStore"]
