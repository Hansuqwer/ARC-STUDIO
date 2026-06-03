"""FlightRecorder — primary public API for recording flight events.

Usage (library-first, CLI integration is optional):

    from agent_runtime_cockpit.flight_recorder import FlightRecorder, FlightRecorderConfig

    cfg = FlightRecorderConfig(base_dir=".arc/flight")
    recorder = FlightRecorder(config=cfg)

    run_id = "run-abc123"
    recorder.start_run(run_id)
    recorder.record(run_id, EventType.RUN_STARTED, payload={"workflow": "my_wf"})
    recorder.record(run_id, EventType.IR_COMPILED, payload={"ir_hash": "abcd..."})
    recorder.stop_run(run_id, status="completed")

Hard constraints:
  - No network I/O.
  - No subprocess or process execution.
  - No model calls.
  - No MCP server startup.
  - Redaction BEFORE persistence.
  - Fail closed on malformed sensitive records (if fail_closed=True).
  - Bounded retention enforced.
  - Segment files are crash-safe.
  - Does NOT duplicate existing JSONL traces — stores references only.
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import index as _index
from .models import (
    EventType,
    FlightEvent,
    FlightRecorderConfig,
    FlightSegment,
    RedactionSummary,
    RunEntry,
    SegmentRef,
)
from .redaction import redact_payload
from .segments import SegmentWriter, open_segment

log = logging.getLogger(__name__)

_GENESIS = "GENESIS"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# FlightRecorder
# ---------------------------------------------------------------------------


class _RunState:
    """Mutable state for one active run."""

    def __init__(self, run_id: str, session_id: Optional[str]) -> None:
        self.run_id = run_id
        self.session_id = session_id
        self.sequence: int = 0
        self.segment_number: int = 0
        self.writer: Optional[SegmentWriter] = None
        self.previous_segment_hash: str = _GENESIS
        self.lock = threading.Lock()

    def next_seq(self) -> int:
        s = self.sequence
        self.sequence += 1
        return s


class FlightRecorder:
    """Thread-safe, local-first flight recorder.

    One ``FlightRecorder`` instance can manage multiple concurrent runs.
    Each run has its own segment chain under ``base_dir/segments/<run_id>/``.
    """

    def __init__(self, config: Optional[FlightRecorderConfig] = None) -> None:
        self._config = config or FlightRecorderConfig()
        self._base_dir = Path(self._config.base_dir)
        self._runs: dict[str, _RunState] = {}
        self._global_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def start_run(
        self,
        run_id: str,
        session_id: Optional[str] = None,
        trace_ref: Optional[str] = None,
        audit_ref: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Register a new run and emit ``run.started`` event."""
        if not self._config.enabled:
            return
        with self._global_lock:
            if run_id in self._runs:
                log.warning("flight_recorder: run %s already active — ignoring start_run", run_id)
                return
            state = _RunState(run_id, session_id)
            self._runs[run_id] = state

        # Register in index
        run_entry = RunEntry(
            run_id=run_id,
            session_id=session_id,
            started_at=_utc_now(),
            trace_ref=trace_ref,
            audit_ref=audit_ref,
        )
        _index.upsert_run(self._base_dir, run_entry)

        # Emit recorder-started event
        self.record(
            run_id,
            EventType.RUN_STARTED,
            payload={"metadata": metadata or {}},
            trace_ref=trace_ref,
            audit_ref=audit_ref,
        )

    def stop_run(
        self,
        run_id: str,
        status: str = "completed",
        error: Optional[str] = None,
    ) -> None:
        """Finalise a run, close its active segment, update index."""
        if not self._config.enabled:
            return
        with self._global_lock:
            state = self._runs.get(run_id)

        if state is None:
            log.warning("flight_recorder: stop_run called for unknown run %s", run_id)
            return

        event_type = EventType.RUN_COMPLETED if status == "completed" else EventType.RUN_FAILED
        payload: dict[str, Any] = {"status": status}
        if error:
            payload["error"] = error

        self.record(run_id, event_type, payload=payload)

        with state.lock:
            if state.writer:
                closed_seg = state.writer.close()
                self._sync_segment_to_index(closed_seg)
                state.writer = None

        _index.close_run(self._base_dir, run_id, status=status)

        with self._global_lock:
            self._runs.pop(run_id, None)

    def record(
        self,
        run_id: str,
        event_type: EventType,
        *,
        payload: Optional[dict[str, Any]] = None,
        source: str = "arc",
        session_id: Optional[str] = None,
        audit_ref: Optional[str] = None,
        trace_ref: Optional[str] = None,
    ) -> Optional[FlightEvent]:
        """Record a single event. Returns the recorded FlightEvent or None.

        Redaction is applied before persistence.
        If ``fail_closed=True`` and redaction fails, the event is dropped.
        """
        if not self._config.enabled:
            return None

        raw_payload = payload or {}

        # Redact before any persistence
        try:
            clean_payload, redaction_summary = redact_payload(
                raw_payload, redact_secrets=self._config.redact_secrets
            )
        except Exception as exc:
            if self._config.fail_closed:
                log.warning(
                    "flight_recorder: redaction failed for %s/%s, dropping event: %s",
                    run_id,
                    event_type.value,
                    exc,
                )
                return None
            clean_payload = {"_redaction_error": str(exc)}
            redaction_summary = RedactionSummary(
                fields_redacted=["*"], patterns_matched=["error"], redact_applied=True
            )

        with self._global_lock:
            state = self._runs.get(run_id)

        if state is None:
            # Auto-create ephemeral run state (e.g., for crash markers)
            log.debug("flight_recorder: auto-creating state for run %s", run_id)
            with self._global_lock:
                state = _RunState(run_id, session_id)
                self._runs[run_id] = state

        with state.lock:
            seq = state.next_seq()

            # Open segment if needed
            if state.writer is None:
                state.writer = open_segment(
                    self._base_dir,
                    run_id,
                    state.segment_number,
                    state.previous_segment_hash,
                    self._config,
                )
                # Register segment in index immediately
                seg_ref = self._segment_to_ref(state.writer.segment)
                _index.add_segment_ref(self._base_dir, seg_ref)

            event = FlightEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                run_id=run_id,
                session_id=session_id or state.session_id,
                timestamp=_utc_now(),
                sequence=seq,
                source=source,
                payload=clean_payload if self._config.include_payloads else {},
                redaction=redaction_summary,
                audit_ref=audit_ref,
                trace_ref=trace_ref,
            ).with_hash()

            try:
                state.writer.append(event)
            except Exception as exc:
                log.error(
                    "flight_recorder: failed to append event %s/%s: %s",
                    run_id,
                    event_type.value,
                    exc,
                )
                if self._config.fail_closed:
                    return None

            # Rotate segment if full
            if state.writer.is_full:
                closed_seg = state.writer.close()
                self._sync_segment_to_index(closed_seg)
                state.previous_segment_hash = closed_seg.segment_hash
                state.segment_number += 1
                state.writer = None

        return event

    # ------------------------------------------------------------------
    # Crash marker — can be called even without a registered run
    # ------------------------------------------------------------------

    def crash_marker(
        self,
        run_id: str,
        reason: str,
        *,
        source: str = "arc",
    ) -> Optional[FlightEvent]:
        """Record a crash marker for a run (even if the run is not registered)."""
        return self.record(
            run_id,
            EventType.CRASH_MARKER,
            payload={"reason": reason},
            source=source,
        )

    def record_error(
        self,
        run_id: str,
        error_type: str,
        message: str,
        *,
        source: str = "arc",
    ) -> Optional[FlightEvent]:
        """Convenience method to record an error event."""
        return self.record(
            run_id,
            EventType.ERROR_RAISED,
            payload={"error_type": error_type, "message": message},
            source=source,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _segment_to_ref(self, seg: FlightSegment) -> SegmentRef:
        return SegmentRef(
            segment_id=seg.segment_id,
            run_id=seg.run_id,
            created_at=seg.created_at,
            closed_at=seg.closed_at,
            event_count=seg.event_count,
            segment_hash=seg.segment_hash,
            previous_segment_hash=seg.previous_segment_hash,
            events_path=seg.events_path,
            meta_path=seg.meta_path,
            corrupt=seg.corrupt,
        )

    def _sync_segment_to_index(self, seg: FlightSegment) -> None:
        _index.update_segment_ref(self._base_dir, self._segment_to_ref(seg))

    def flush(self, run_id: str) -> None:
        """Flush the active segment for a run without closing."""
        with self._global_lock:
            state = self._runs.get(run_id)
        if state:
            with state.lock:
                if state.writer:
                    state.writer.flush()

    def status(self) -> dict[str, Any]:
        """Return a status dict (for ``arc flight status``)."""
        idx = _index.load_index(self._base_dir)
        total_bytes = self._total_segment_bytes()
        return {
            "enabled": self._config.enabled,
            "base_dir": str(self._base_dir),
            "active_runs": list(self._runs.keys()),
            "total_segments": len(idx.segments),
            "total_runs": len(idx.runs),
            "total_bytes": total_bytes,
            "last_verified_at": idx.last_verified_at,
            "last_updated_at": idx.last_updated_at,
            "retention": {
                "max_segments": self._config.max_segments,
                "max_total_bytes": self._config.max_total_bytes,
                "max_age_days": self._config.max_age_days,
            },
        }

    def _total_segment_bytes(self) -> int:
        total = 0
        seg_root = self._base_dir / "segments"
        if not seg_root.exists():
            return 0
        for p in seg_root.rglob("*.events.jsonl"):
            try:
                total += p.stat().st_size
            except OSError:
                pass
        return total
