"""Run Diff / Time Travel - local-first deterministic run comparison and timeline inspection."""

from __future__ import annotations

from .diff_capabilities import diff_capability_cards, diff_capability_cards_from_paths
from .diff_events import diff_run_records, diff_run_records_from_ids
from .diff_flight import diff_flight_events, diff_flight_segments
from .diff_ir import diff_ir_from_paths, diff_ir_graphs
from .diff_mcp import diff_mcp_manifests
from .diff_policy import diff_policy_from_paths, diff_policy_reports
from .diff_simulation import diff_simulation_reports
from .export import from_json, load_report, summary_text, to_dict, to_json, write_json
from .loaders import (
    LoadError,
    LoadResult,
    load_any,
    load_capability_card_from_path,
    load_ir_from_path,
    load_jsonl_events,
    load_policy_from_path,
    load_run_from_json,
    load_run_from_store,
    load_simulation_from_path,
)
from .models import (
    RUN_DIFF_SCHEMA_VERSION,
    CapabilityDiff,
    ChangeType,
    DiffMode,
    DiffSubject,
    DiffSubjectKind,
    DiffSummary,
    EventDiff,
    EventEntry,
    FirstDivergence,
    FlightDiff,
    GraphDiff,
    McpManifestDiff,
    NodeDiff,
    NodeDiffField,
    PolicyDiff,
    PolicyIssueDiff,
    RiskDiff,
    RunDiffReport,
    SimulationDiff,
    TimelineFrame,
)
from .redaction import is_safe, redact_dict, redact_report, redact_text
from .models import CostDiff  # noqa: F401
from .timeline import (
    TimeTravelCursor,
    build_timeline_from_report,
    build_timeline_from_run_events,
)

__all__ = [
    "RUN_DIFF_SCHEMA_VERSION",
    "RunDiffReport",
    "DiffSubject",
    "DiffSubjectKind",
    "DiffSummary",
    "DiffMode",
    "ChangeType",
    "GraphDiff",
    "NodeDiff",
    "NodeDiffField",
    "EventDiff",
    "EventEntry",
    "PolicyDiff",
    "PolicyIssueDiff",
    "SimulationDiff",
    "CapabilityDiff",
    "FlightDiff",
    "McpManifestDiff",
    "RiskDiff",
    "FirstDivergence",
    "TimelineFrame",
    "TimeTravelCursor",
    "build_timeline_from_report",
    "build_timeline_from_run_events",
    "diff_ir_graphs",
    "diff_ir_from_paths",
    "diff_policy_reports",
    "diff_policy_from_paths",
    "diff_run_records",
    "diff_run_records_from_ids",
    "diff_mcp_manifests",
    "diff_simulation_reports",
    "diff_capability_cards",
    "diff_capability_cards_from_paths",
    "diff_flight_segments",
    "diff_flight_events",
    "LoadResult",
    "LoadError",
    "load_ir_from_path",
    "load_policy_from_path",
    "load_run_from_store",
    "load_run_from_json",
    "load_jsonl_events",
    "load_simulation_from_path",
    "load_capability_card_from_path",
    "load_any",
    "to_json",
    "to_dict",
    "from_json",
    "write_json",
    "load_report",
    "summary_text",
    "redact_text",
    "redact_dict",
    "redact_report",
    "is_safe",
]
