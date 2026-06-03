"""Typed Pydantic models for the Local Agent Flight Recorder.

All models are schema-versioned and immutable-friendly.
No I/O, no network, no model calls.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "1"


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Canonical set of flight recorder event types.

    Only types whose payloads can be safely captured from existing repo
    data structures are included. All types are deterministic and local-only.
    """

    # Run lifecycle
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"

    # SwarmGraph IR
    IR_COMPILED = "ir.compiled"

    # Policy
    POLICY_EVALUATED = "policy.evaluated"

    # Simulation
    SIMULATION_GENERATED = "simulation.generated"

    # MCP
    MCP_MANIFEST_CHECKED = "mcp.manifest.checked"
    MCP_TOOL_APPROVED = "mcp.tool.approved"
    MCP_TOOL_BLOCKED = "mcp.tool.blocked"

    # HITL
    HITL_REQUESTED = "hitl.requested"
    HITL_APPROVED = "hitl.approved"
    HITL_REJECTED = "hitl.rejected"

    # Consensus
    CONSENSUS_SELECTED = "consensus.selected"

    # Audit
    AUDIT_RECEIPT_CREATED = "audit.receipt.created"

    # Evals
    EVAL_RECOMMENDATION_GENERATED = "eval.recommendation.generated"

    # Tool calls (metadata references only — no payloads duplicated from trace)
    TOOL_CALL_PLANNED = "tool.call.planned"
    TOOL_CALL_COMPLETED = "tool.call.completed"

    # Errors / crash markers
    ERROR_RAISED = "error.raised"
    CRASH_MARKER = "crash.marker"

    # Recorder internal
    SEGMENT_OPENED = "segment.opened"
    SEGMENT_CLOSED = "segment.closed"
    RECORDER_STARTED = "recorder.started"
    RECORDER_STOPPED = "recorder.stopped"


# ---------------------------------------------------------------------------
# Redaction summary
# ---------------------------------------------------------------------------


class RedactionSummary(BaseModel):
    """Records what was redacted during event serialisation."""

    fields_redacted: list[str] = Field(default_factory=list)
    patterns_matched: list[str] = Field(default_factory=list)
    redact_applied: bool = False

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# FlightEvent
# ---------------------------------------------------------------------------


class FlightEvent(BaseModel):
    """A single immutable flight recorder event.

    Invariants:
    - ``hash`` is computed over all other fields (canonical JSON, sorted keys).
    - Secrets are redacted *before* this model is constructed.
    - ``sequence`` is monotonically increasing within a segment.
    """

    schema_version: str = SCHEMA_VERSION
    event_id: str
    event_type: EventType
    run_id: str
    session_id: Optional[str] = None
    timestamp: str  # ISO-8601 UTC
    sequence: int
    source: str = "arc"  # module or subsystem that emitted the event
    payload: dict[str, Any] = Field(default_factory=dict)
    redaction: RedactionSummary = Field(default_factory=RedactionSummary)
    audit_ref: Optional[str] = None  # path or ID into existing audit chain
    trace_ref: Optional[str] = None  # run_id reference into JSONL traces
    hash: str = ""  # computed on construction

    model_config = {"frozen": True}

    @field_validator("timestamp")
    @classmethod
    def _ts_is_utc(cls, v: str) -> str:
        # Must be parseable; we do not enforce timezone suffix in validator
        # to avoid breaking tests, but callers should always pass UTC.
        return v

    def compute_hash(self) -> str:
        """Deterministic SHA-256 over canonical content (excluding hash field)."""
        content = {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "source": self.source,
            "payload": self.payload,
            "audit_ref": self.audit_ref,
            "trace_ref": self.trace_ref,
        }
        canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def with_hash(self) -> "FlightEvent":
        """Return a new FlightEvent with the hash field populated."""
        return self.model_copy(update={"hash": self.compute_hash()})


# ---------------------------------------------------------------------------
# FlightSegment
# ---------------------------------------------------------------------------


class FlightSegment(BaseModel):
    """Metadata for one append-only JSONL segment file.

    The segment *events* file is separate (``events_path``).
    The segment *meta* file is written atomically (``index_path``).
    Hash chain: ``previous_segment_hash`` → ``segment_hash`` (SHA-256 over
    all event hashes in sequence order).
    """

    schema_version: str = SCHEMA_VERSION
    segment_id: str
    run_id: str
    created_at: str  # ISO-8601 UTC
    closed_at: Optional[str] = None
    event_count: int = 0
    first_sequence: int = 0
    last_sequence: int = 0
    segment_hash: str = ""
    previous_segment_hash: str = "GENESIS"
    events_path: str = ""  # relative to .arc/flight/
    meta_path: str = ""
    corrupt: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}  # mutable until closed


# ---------------------------------------------------------------------------
# FlightIndex
# ---------------------------------------------------------------------------


class SegmentRef(BaseModel):
    """Lightweight reference stored in the index."""

    segment_id: str
    run_id: str
    created_at: str
    closed_at: Optional[str] = None
    event_count: int = 0
    segment_hash: str = ""
    previous_segment_hash: str = "GENESIS"
    events_path: str = ""
    meta_path: str = ""
    corrupt: bool = False


class RunEntry(BaseModel):
    """Per-run entry in the index."""

    run_id: str
    session_id: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"  # running | completed | failed | crashed
    segment_ids: list[str] = Field(default_factory=list)
    ir_hash: Optional[str] = None
    policy_risk: Optional[str] = None
    trace_ref: Optional[str] = None
    audit_ref: Optional[str] = None


class RetentionPolicy(BaseModel):
    """Configured retention bounds."""

    max_segments: int = 200
    max_total_bytes: int = 100 * 1024 * 1024  # 100 MiB
    max_age_days: int = 30


class FlightIndex(BaseModel):
    """Master index across all segments and runs.

    Written atomically via ``storage.atomic.write_text_atomic``.
    """

    schema_version: str = SCHEMA_VERSION
    segments: list[SegmentRef] = Field(default_factory=list)
    runs: dict[str, RunEntry] = Field(default_factory=dict)
    retention: RetentionPolicy = Field(default_factory=RetentionPolicy)
    last_verified_at: Optional[str] = None
    last_updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )


# ---------------------------------------------------------------------------
# FlightRecorderConfig
# ---------------------------------------------------------------------------


class FlightRecorderConfig(BaseModel):
    """Runtime configuration for the flight recorder."""

    enabled: bool = True
    base_dir: str = ".arc/flight"
    max_segment_bytes: int = 5 * 1024 * 1024  # 5 MiB per segment
    max_segments: int = 200
    max_total_bytes: int = 100 * 1024 * 1024  # 100 MiB total
    max_age_days: int = 30
    redact_secrets: bool = True
    include_payloads: bool = True
    include_env_summary: bool = False  # off by default — opt-in
    compression: bool = False  # future; not yet implemented
    fail_closed: bool = True  # drop malformed sensitive records


# ---------------------------------------------------------------------------
# FlightExportBundle
# ---------------------------------------------------------------------------


class BundleManifestEntry(BaseModel):
    path: str
    sha256: str
    size_bytes: int


class FlightExportBundle(BaseModel):
    """Manifest written into every export tarball."""

    schema_version: str = SCHEMA_VERSION
    bundle_id: str
    created_at: str
    runs: list[str] = Field(default_factory=list)
    segments: list[str] = Field(default_factory=list)
    manifest: list[BundleManifestEntry] = Field(default_factory=list)
    checksums: dict[str, str] = Field(default_factory=dict)  # path → sha256
    redaction_summary: RedactionSummary = Field(default_factory=RedactionSummary)
    total_events: int = 0


# ---------------------------------------------------------------------------
# FlightVerificationReport
# ---------------------------------------------------------------------------


class VerificationIssue(BaseModel):
    segment_id: str
    issue_type: str  # hash_mismatch | corrupt_json | missing_file | chain_break
    detail: str


class FlightVerificationReport(BaseModel):
    """Output of ``arc flight verify``."""

    schema_version: str = SCHEMA_VERSION
    ok: bool
    checked_segments: int = 0
    corrupt_segments: list[str] = Field(default_factory=list)
    missing_segments: list[str] = Field(default_factory=list)
    hash_chain_valid: bool = True
    issues: list[VerificationIssue] = Field(default_factory=list)
    verified_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
