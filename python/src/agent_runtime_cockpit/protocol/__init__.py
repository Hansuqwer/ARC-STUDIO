"""ARC Protocol — envelope, errors, capabilities, methods, schemas.

Canonical home for all cross-language schemas (ADR-018). Schemas that are
mirrored to TypeScript (event envelope, RuntimeCapability, CostRecord)
live under ``protocol/`` so the sync script has one source directory.

Python-only schemas (e.g., ChatSession v3, which is never transmitted
across the language boundary) stay in their domain packages.
"""

from .cache_breakpoints import (
    MAX_BREAKPOINTS,
    CacheBreakpoint,
    CacheBreakpointInput,
    MessageTokenInfo,
    compute_breakpoints,
    estimate_cache_savings,
)
from .capabilities import RuntimeCapabilities
from .capability_snapshot import (
    CapabilityDiff,
    CapabilitySnapshot,
    DegradationValidation,
    diff_capabilities,
    get_cockpit_readiness,
    snapshot_capabilities,
    validate_capability_claims,
)
from .cost_record import CostRecord, migrate_v1_to_v2, migrate_v2_to_v3
from .errors import ArcErrorCode
from .event_envelope import ArcEnvelope, ArcError, ArcMeta, err, ok
from .evidence_refs import EvidenceKind, EvidenceRef
from .failure_autopsy import FailureAutopsy, RetryOption
from .run_contract import ContractStatus, RunContract
from .run_receipt import FileChange, RunReceipt
from .runtime_capability import RuntimeCapability
from .stable_ids import (
    DegradationManifest,
    ensure_stable_id,
    generate_edge_id,
    generate_node_id,
    generate_stable_id,
    is_valid_stable_id,
    parse_stable_id,
)

__all__ = [
    "ArcEnvelope",
    "ArcError",
    "ArcMeta",
    "ok",
    "err",
    "RuntimeCapabilities",
    "RuntimeCapability",
    "ArcErrorCode",
    "CacheBreakpoint",
    "CacheBreakpointInput",
    "MessageTokenInfo",
    "compute_breakpoints",
    "estimate_cache_savings",
    "CostRecord",
    "migrate_v1_to_v2",
    "migrate_v2_to_v3",
    "MAX_BREAKPOINTS",
    "generate_stable_id",
    "generate_node_id",
    "generate_edge_id",
    "ensure_stable_id",
    "parse_stable_id",
    "is_valid_stable_id",
    "DegradationManifest",
    "CapabilitySnapshot",
    "CapabilityDiff",
    "DegradationValidation",
    "snapshot_capabilities",
    "diff_capabilities",
    "validate_capability_claims",
    "get_cockpit_readiness",
    "EvidenceKind",
    "EvidenceRef",
    "FailureAutopsy",
    "RetryOption",
    "ContractStatus",
    "RunContract",
    "FileChange",
    "RunReceipt",
]
