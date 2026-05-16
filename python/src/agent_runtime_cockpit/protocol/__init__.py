"""ARC Protocol — envelope, errors, capabilities, methods, schemas."""
from .envelope import ArcEnvelope, ArcError, ArcMeta, ok, err
from .capabilities import RuntimeCapabilities
from .errors import ArcErrorCode
from .stable_ids import (
    generate_stable_id,
    generate_node_id,
    generate_edge_id,
    ensure_stable_id,
    parse_stable_id,
    is_valid_stable_id,
    DegradationManifest,
)
from .capability_snapshot import (
    CapabilitySnapshot,
    CapabilityDiff,
    DegradationValidation,
    snapshot_capabilities,
    diff_capabilities,
    validate_capability_claims,
    get_cockpit_readiness,
)
from .evidence_refs import EvidenceKind, EvidenceRef
from .failure_autopsy import FailureAutopsy, RetryOption
from .run_contract import ContractStatus, RunContract
from .run_receipt import FileChange, RunReceipt

__all__ = [
    "ArcEnvelope", "ArcError", "ArcMeta", "ok", "err",
    "RuntimeCapabilities", "ArcErrorCode",
    "generate_stable_id", "generate_node_id", "generate_edge_id",
    "ensure_stable_id", "parse_stable_id", "is_valid_stable_id",
    "DegradationManifest",
    "CapabilitySnapshot", "CapabilityDiff", "DegradationValidation",
    "snapshot_capabilities", "diff_capabilities",
    "validate_capability_claims", "get_cockpit_readiness",
    "EvidenceKind", "EvidenceRef", "FailureAutopsy", "RetryOption",
    "ContractStatus", "RunContract", "FileChange", "RunReceipt",
]
