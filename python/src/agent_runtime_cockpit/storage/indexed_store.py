"""Dual-write store: JSONL canonical + SQLite index (ADR-003)."""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..protocol.failure_autopsy import FailureAutopsy
from ..protocol.run_contract import RunContract
from ..protocol.run_receipt import RunReceipt
from ..protocol.schemas import RunRecord
from .jsonl import JsonlTraceStore
from .sqlite import SqliteStore

log = logging.getLogger(__name__)


class IndexedTraceStore:
    """Writes JSONL first (canonical), then SQLite index (best-effort)."""

    def __init__(
        self,
        trace_dir: Path = Path(".arc") / "traces",
        db_path: Path = Path(".arc") / "arc.db",
    ) -> None:
        self.jsonl = JsonlTraceStore(base_dir=trace_dir)
        self.sqlite = SqliteStore(db_path=db_path)

    def init(self) -> None:
        """Initialise SQLite tables."""
        self.sqlite.init_db()

    def save(self, run: RunRecord) -> None:
        """Write JSONL first (canonical), then SQLite index.

        JSONL write uses atomic temp-file + replace for crash safety.
        SQLite write is best-effort; failures are logged but not re-raised.
        """
        # 1. Atomic JSONL write (canonical)
        path = self.jsonl._run_path(run.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(run.model_dump_json() + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # 2. Best-effort SQLite index update
        try:
            trace_path_str = str(path.resolve())
            self.sqlite.insert_run(
                run_id=run.id,
                workflow_id=run.workflow_id,
                runtime=run.runtime,
                status=run.status.value,
                started_at=run.started_at,
                trace_path=trace_path_str,
                audit_path=run.audit_path,
                metadata=run.metadata,
            )
            if run.ended_at:
                duration_ms = _compute_duration_ms(run.started_at, run.ended_at)
                cancel_reason = run.metadata.get("cancel_reason") if run.metadata else None
                error_detail = run.metadata.get("error") if run.metadata else None
                self.sqlite.update_run_status(
                    run.id,
                    run.status.value,
                    run.ended_at,
                    duration_ms=duration_ms,
                    cancel_reason=cancel_reason,
                    error_detail=error_detail,
                )
        except Exception as e:
            log.warning("SQLite index update failed for run %s: %s", run.id, e)

    def load(self, run_id: str) -> Optional[RunRecord]:
        """Load full RunRecord from canonical JSONL."""
        return self.jsonl.load(run_id)

    def list_runs(self) -> list[str]:
        """List all run IDs (from filesystem)."""
        return self.jsonl.list_runs()

    def trace_path(self, run_id: str) -> Path:
        """Return the trace path used for a run ID (delegates to JSONL store)."""
        return self.jsonl.trace_path(run_id)

    def save_contract(self, contract: RunContract) -> None:
        self.jsonl.save_contract(contract)

    def load_contract(self, run_id: str) -> Optional[RunContract]:
        return self.jsonl.load_contract(run_id)

    def save_receipt(self, receipt: RunReceipt) -> None:
        self.jsonl.save_receipt(receipt)

    def load_receipt(self, run_id: str) -> Optional[RunReceipt]:
        return self.jsonl.load_receipt(run_id)

    def save_autopsy(self, autopsy: FailureAutopsy) -> None:
        self.jsonl.save_autopsy(autopsy)

    def load_autopsy(self, run_id: str) -> Optional[FailureAutopsy]:
        return self.jsonl.load_autopsy(run_id)

    def backfill_index(self) -> tuple[int, int, int]:
        """Rebuild SQLite index from existing JSONL traces. Idempotent."""
        indexed = 0
        skipped = 0
        failed = 0
        for run_id in self.jsonl.list_runs():
            try:
                if self.sqlite.run_exists(run_id):
                    skipped += 1
                    continue
                run = self.jsonl.load(run_id)
                if run is None:
                    failed += 1
                    continue
                # Save will write JSONL + SQLite
                self.save(run)
                indexed += 1
            except Exception as e:
                log.warning("Backfill failed for %s: %s", run_id, e)
                failed += 1
        return indexed, skipped, failed


def _compute_duration_ms(started_at: str, ended_at: str) -> Optional[int]:
    """Compute duration in ms between two ISO-8601 timestamps."""
    try:
        # Handle both Z and +00:00 suffixes
        start = _parse_iso(started_at)
        end = _parse_iso(ended_at)
        if start and end:
            return int((end - start).total_seconds() * 1000)
    except Exception:
        pass
    return None


def _parse_iso(s: str) -> Optional[datetime]:
    """Parse ISO-8601 string with optional Z suffix."""
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None
