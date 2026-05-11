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
        return [p.stem for p in self.base_dir.glob("*.jsonl")]

    def append_event(self, run_id: str, event: dict) -> None:
        """Append a single event to a run's JSONL file (streaming mode)."""
        try:
            with self._lock:
                self.base_dir.mkdir(parents=True, exist_ok=True)
                with open(self._run_path(f"{run_id}-events"), "a") as f:
                    f.write(json.dumps(event) + "\n")
        except Exception as e:
            log.warning("Failed to append event for run %s: %s", run_id, e)
