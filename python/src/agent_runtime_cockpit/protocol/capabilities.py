"""ARC runtime capability model — schema version 1."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


class SupportLevel(str, Enum):
    """Maturity level of a runtime adapter or feature."""
    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class ExecutionMode(str, Enum):
    """Execution mode a runtime supports."""
    STANDALONE = "standalone"
    SEQUENCE = "sequence"
    ADOPTION = "adoption"


class AuditLevel(str, Enum):
    """Level of audit trail a runtime can produce."""
    NONE = "none"
    ARC_SHA256 = "arc_sha256"
    SWARMGRAPH_HMAC = "swarmgraph_hmac"


class HitlLevel(str, Enum):
    """Level of human-in-the-loop support."""
    NONE = "none"
    ADVISORY = "advisory"
    ENFORCED = "enforced"


class RuntimeCapabilities(BaseModel):
    """Honest self-report of what this adapter supports."""
    # Schema versioning
    schema_version: int = SCHEMA_VERSION

    # Support level
    support_level: SupportLevel = SupportLevel.EXPERIMENTAL

    # Execution modes this runtime supports
    execution_modes: list[ExecutionMode] = Field(
        default_factory=lambda: [ExecutionMode.STANDALONE]
    )

    # Adoption modes (runtime+swarmgraph) — always empty unless implemented
    adoption_modes: list[str] = Field(default_factory=list)

    # Audit and HITL levels
    audit_level: AuditLevel = AuditLevel.NONE
    hitl_level: HitlLevel = HitlLevel.NONE

    # Inspection / export
    can_inspect: bool = False
    can_run: bool = False
    can_export_schema: bool = False
    can_export_workflow: bool = False

    # Observability
    can_trace: bool = False
    can_replay: bool = False
    can_stream_events: bool = False
    can_audit: bool = False

    # Advanced execution (Runtime Contract v2)
    can_checkpoint: bool = False
    can_resume: bool = False
    can_fork: bool = False
    can_diff: bool = False
    can_eval: bool = False

    # Permission requirements (reported by adapter, enforced by gating)
    requires_paid_calls: bool = False
    requires_network: bool = Field(default=False, description="Runtime needs external network access")
    requires_shell: bool = Field(default=False, description="Runtime spawns subprocesses")
    requires_secrets: bool = Field(default=False, description="Runtime needs API keys or tokens")
