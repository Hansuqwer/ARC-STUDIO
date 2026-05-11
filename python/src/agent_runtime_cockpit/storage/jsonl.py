"""JSONL trace store — persists RunRecords as newline-delimited JSON."""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Optional
from ..protocol.schemas import RunRecord

log = logging.getLogger(__name__)
DEFAULT_STORE_PATH = Path(".arc") / "traces"


class JsonlTraceStore:
    """Appends run events to JSONL files; one file per run_id."""

    def __init__(self, base_dir: Path = DEFAULT_STORE_PATH) -> None:
        self.base_dir = base_dir
        self._lock = threading.Lock()

    def _run_path(self, run_id: str) -> Path:
        return self.base_dir / f"{run_id}.jsonl"

    def trace_path(self, run_id: str) -> Path:
        """Return the trace path used for a run ID."""
        return self._run_path(run_id)

    def save(self, run: RunRecord) -> None:
        """Persist a completed RunRecord."""
        try:
            with self._lock:
                self.base_dir.mkdir(parents=True, exist_ok=True)
                path = self._run_path(run.id)
                with open(path, "w") as f:
                    f.write(run.model_dump_json() + "\n")
            log.debug("Saved run trace: %s", path)
        except Exception as e:
            log.warning("Failed to save run trace %s: %s", run.id, e)

    def load(self, run_id: str) -> Optional[RunRecord]:
        """Load a run record from disk."""
        try:
            path = self._run_path(run_id)
            if not path.exists():
                return None
            data = json.loads(path.read_text().splitlines()[0])
            return RunRecord.model_validate(data)
        except Exception as e:
            log.warning("Failed to load run trace %s: %s", run_id, e)
            return None

    def list_runs(self) -> list[str]:
        """Return all stored run IDs."""
        if not self.base_dir.exists():
            return []
        paths = sorted(self.base_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [p.stem for p in paths]

    def prune(self, keep: int, dry_run: bool = True) -> list[Path]:
        """Delete oldest trace files beyond keep count, or return would-delete paths."""
        if keep < 0:
            raise ValueError("keep must be >= 0")
        if not self.base_dir.exists():
            return []
        root = self.base_dir.resolve()
        paths = sorted(self.base_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        victims = paths[keep:]
        for path in victims:
            resolved = path.resolve()
            if root not in resolved.parents:
                raise ValueError(f"refusing to delete outside trace dir: {path}")
            if not dry_run:
                resolved.unlink()
        return victims

    def append_event(self, run_id: str, event: dict) -> None:
        """Append a single event to a run's JSONL file (streaming mode)."""
        try:
            with self._lock:
                self.base_dir.mkdir(parents=True, exist_ok=True)
                with open(self._run_path(f"{run_id}-events"), "a") as f:
                    f.write(json.dumps(event) + "\n")
        except Exception as e:
            log.warning("Failed to append event for run %s: %s", run_id, e)
