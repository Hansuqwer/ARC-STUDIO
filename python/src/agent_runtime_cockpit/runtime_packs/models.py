"""Typed models for the Runtime Pack SDK.

A *runtime pack* is a static, inspectable bundle of metadata that describes how a
runtime adapter integrates with ARC, without ARC having to hard-code that runtime
into the core repository. The canonical artifact is a single deterministic JSON
file named ``arc-runtime-pack.json`` (see ``MANIFEST_FILENAME``).

Design notes (mirrors ``capabilities/models.py`` and ``swarmgraph_ir/models.py``):

* Schema versions are integers. ``schema_version`` gates migrations so older
  readers can refuse manifests they do not understand.
* All risk-bearing flags default to ``False`` so that *missing data is safe*
  (fail-closed). A capability is assumed not to touch the network, paid models,
  secrets, shell, or anything outside the workspace unless it explicitly says so.
* Models use ``extra="ignore"`` so that loading never crashes on forward-compatible
  extra keys. Fail-closed semantics are enforced by ``validation.py``, not by the
  pydantic layer (consistent with the Capability Card models).

This module performs **no** I/O, executes **no** pack code, and opens **no**
network connections. It only declares shapes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# The current Runtime Pack manifest schema version. Bump on breaking changes.
RUNTIME_PACK_SCHEMA_VERSION = 1

# Canonical on-disk filename for a runtime pack manifest.
MANIFEST_FILENAME = "arc-runtime-pack.json"


# ─── Enums ───────────────────────────────────────────────────────────────────


class PermissionKind(str, Enum):
    """Known permission kinds a runtime pack may request.

    ``validation.py`` treats any permission ``kind`` that is *not* one of these
    values as an error (unknown permissions fail closed). The string values are
    deliberately stable and lowercase.
    """

    NETWORK = "network"
    FILESYSTEM = "filesystem"
    SHELL = "shell"
    MCP = "mcp"
    SECRETS = "secrets"
    MEMORY = "memory"
    SEARCH = "search"
    PAID_MODELS = "paid_models"
    OUTSIDE_WORKSPACE = "outside_workspace"
    BACKGROUND = "background"
    OBSERVABILITY = "observability"


# The canonical set of permission kinds, as plain strings, for fail-closed checks.
KNOWN_PERMISSION_KINDS: frozenset[str] = frozenset(k.value for k in PermissionKind)

# Permission kinds considered dangerous: a capability that asserts the matching
# flag MUST declare one of these permissions, and such permissions MUST carry a
# reason. Expanding any of these is what "capability expansion" refers to.
DANGEROUS_PERMISSION_KINDS: frozenset[str] = frozenset(
    {
        PermissionKind.NETWORK.value,
        PermissionKind.PAID_MODELS.value,
        PermissionKind.SECRETS.value,
        PermissionKind.SHELL.value,
        PermissionKind.OUTSIDE_WORKSPACE.value,
    }
)


class DefaultDecision(str, Enum):
    """Default policy decision for a permission when no explicit approval exists.

    ``DENY`` is the fail-closed default. ``ALLOW`` for a dangerous permission is a
    validation warning because it grants capability without explicit approval.
    """

    DENY = "deny"
    PROMPT = "prompt"
    ALLOW = "allow"


class RuntimeKind(str, Enum):
    """Coarse classification of a runtime's execution model."""

    GRAPH = "graph"
    AGENT = "agent"
    PIPELINE = "pipeline"
    SWARM = "swarm"
    TOOLED_LLM = "tooled_llm"
    UNKNOWN = "unknown"


class ToolKind(str, Enum):
    """Kind of a declared tool. ``SHELL`` tools are never executed in the MVP."""

    FUNCTION = "function"
    MCP = "mcp"
    HTTP = "http"
    SHELL = "shell"
    NATIVE = "native"
    UNKNOWN = "unknown"


class OpaqueNodePolicy(str, Enum):
    """How an IR exporter must treat nodes it cannot fully classify.

    Required when ``RuntimeIrDeclaration.can_export_ir`` is true: any exporter may
    encounter unknown nodes, so a fail-closed pack must state its policy.
    """

    REJECT = "reject"
    MARK_OPAQUE = "mark_opaque"
    REQUIRE_REVIEW = "require_review"


# ─── Sub-models ──────────────────────────────────────────────────────────────


class RuntimeIdentity(BaseModel):
    """Who/what the runtime is."""

    model_config = ConfigDict(extra="ignore")

    runtime_name: str
    runtime_kind: RuntimeKind = RuntimeKind.UNKNOWN
    language: str = "python"
    framework: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None


class RuntimeEntrypoints(BaseModel):
    """Declared, *non-executed* entrypoint references.

    Each value is an opaque reference string (for example ``my_pack.adapter:inspect``
    or a relative path). In the MVP these are recorded and validated statically but
    never imported or executed. Absolute filesystem paths and shell entrypoints are
    rejected by ``validation.py``.
    """

    model_config = ConfigDict(extra="ignore")

    inspect: Optional[str] = None
    export: Optional[str] = None
    compile_to_ir: Optional[str] = None
    simulate: Optional[str] = None
    validate: Optional[str] = None
    run: Optional[str] = None
    eval: Optional[str] = None

    def as_mapping(self) -> dict[str, str]:
        """Return only the declared (non-null) entrypoints."""
        return {k: v for k, v in self.model_dump().items() if isinstance(v, str) and v}


class RuntimePermission(BaseModel):
    """A single permission the pack requests.

    ``kind`` is a free-form string (not a strict enum) so that *unknown* permission
    kinds are surfaced as validation errors rather than crashing the loader.
    """

    model_config = ConfigDict(extra="ignore")

    kind: str
    required: bool = True
    scope: Optional[str] = None
    reason: Optional[str] = None
    default_decision: DefaultDecision = DefaultDecision.DENY


class RuntimeCapability(BaseModel):
    """A named capability the runtime claims, with fail-closed boolean flags.

    All risk-bearing flags default to ``False``. ``replayable`` and ``auditable``
    also default to ``False`` because the safe assumption is that we cannot replay
    or audit a capability unless the pack proves otherwise.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str = ""
    reads: bool = False
    writes: bool = False
    network: bool = False
    paid: bool = False
    secrets: bool = False
    shell: bool = False
    mcp: bool = False
    outside_workspace: bool = False
    background: bool = False
    replayable: bool = False
    auditable: bool = False


class RuntimeToolDeclaration(BaseModel):
    """A tool the runtime exposes. Schemas are recorded but tools are never run."""

    model_config = ConfigDict(extra="ignore")

    name: str
    kind: ToolKind = ToolKind.UNKNOWN
    schema: Optional[dict[str, Any]] = None
    side_effects: list[str] = Field(default_factory=list)
    requires_hitl: bool = False
    requires_trust: bool = False
    paid: bool = False


class RuntimeMcpDeclaration(BaseModel):
    """An MCP server the runtime depends on. No server is ever started."""

    model_config = ConfigDict(extra="ignore")

    server_id: str
    tools: list[str] = Field(default_factory=list)
    manifest_hash: Optional[str] = None
    required: bool = False
    approved_by_default: bool = False


class RuntimeModelsDeclaration(BaseModel):
    """Model/provider usage. ``requires_paid_models`` gates the paid-call concern."""

    model_config = ConfigDict(extra="ignore")

    requires_paid_models: bool = False
    providers: list[str] = Field(default_factory=list)
    default_mode: str = "fake"


class RuntimeStorageDeclaration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    scope: str = "workspace"
    outside_workspace: bool = False


class RuntimeMemoryDeclaration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    persistent: bool = False


class RuntimeSearchDeclaration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    network: bool = False


class RuntimeObservabilityDeclaration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    otel: bool = False
    exporters: list[str] = Field(default_factory=list)


class RuntimeIrDeclaration(BaseModel):
    """SwarmGraph IR export claims.

    If ``can_export_ir`` is true, ``supported_ir_version`` and ``opaque_node_policy``
    are required by ``validation.py``.
    """

    model_config = ConfigDict(extra="ignore")

    can_export_ir: bool = False
    supported_ir_version: Optional[int] = None
    opaque_node_policy: Optional[OpaqueNodePolicy] = None
    provenance_required: bool = True


class RuntimePolicyDeclaration(BaseModel):
    """Policy/preflight integration claims."""

    model_config = ConfigDict(extra="ignore")

    supports_preflight: bool = False
    fail_closed: bool = True
    required_rules: list[str] = Field(default_factory=list)


class RuntimeTestsDeclaration(BaseModel):
    """Pointers to example workflows / golden traces shipped with the pack."""

    model_config = ConfigDict(extra="ignore")

    examples: list[str] = Field(default_factory=list)
    golden_traces: list[str] = Field(default_factory=list)


class RuntimePackProvenance(BaseModel):
    """Where the manifest came from. ``created_at`` is volatile (excluded from hash)."""

    model_config = ConfigDict(extra="ignore")

    source_path: Optional[str] = None
    created_at: Optional[str] = None
    generated_by: Optional[str] = None
    git_commit: Optional[str] = None


# ─── Root manifest ─────────────────────────────────────────────────────────────


class RuntimePackManifest(BaseModel):
    """The canonical, deterministic, hashable runtime pack manifest.

    Answers, for a CLI agent inspecting a pack without running any code:

    * What runtime is this and what kind of execution model does it use?
    * What capabilities does it expose and which are dangerous?
    * What permissions, tools, MCP servers, models, and policies does it need?
    * Can it call paid models / network / filesystem / shell / secrets / MCP?
    * Can it export to SwarmGraph IR, and at which IR version?
    * Is the manifest hash-pinned and free of secrets?
    """

    model_config = ConfigDict(extra="ignore")

    schema_version: int = RUNTIME_PACK_SCHEMA_VERSION

    # Identity
    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""

    runtime: RuntimeIdentity
    adapter: Optional[str] = None

    entrypoints: RuntimeEntrypoints = Field(default_factory=RuntimeEntrypoints)
    permissions: list[RuntimePermission] = Field(default_factory=list)
    capabilities: list[RuntimeCapability] = Field(default_factory=list)
    tools: list[RuntimeToolDeclaration] = Field(default_factory=list)
    mcp: list[RuntimeMcpDeclaration] = Field(default_factory=list)
    models: RuntimeModelsDeclaration = Field(default_factory=RuntimeModelsDeclaration)
    storage: RuntimeStorageDeclaration = Field(default_factory=RuntimeStorageDeclaration)
    memory: RuntimeMemoryDeclaration = Field(default_factory=RuntimeMemoryDeclaration)
    search: RuntimeSearchDeclaration = Field(default_factory=RuntimeSearchDeclaration)
    observability: RuntimeObservabilityDeclaration = Field(
        default_factory=RuntimeObservabilityDeclaration
    )
    ir: RuntimeIrDeclaration = Field(default_factory=RuntimeIrDeclaration)
    policy: RuntimePolicyDeclaration = Field(default_factory=RuntimePolicyDeclaration)
    tests: RuntimeTestsDeclaration = Field(default_factory=RuntimeTestsDeclaration)
    provenance: RuntimePackProvenance = Field(default_factory=RuntimePackProvenance)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Stable content hash. Computed and verified by ``hashing.py``; excluded from
    # the hash input itself.
    manifest_hash: Optional[str] = None

    # ── Convenience accessors used by inspection/exporters ──────────────────

    def permission_kinds(self) -> set[str]:
        return {p.kind for p in self.permissions}

    def declares_paid(self) -> bool:
        """True if the pack admits it may make paid model calls anywhere."""
        return (
            self.models.requires_paid_models
            or any(c.paid for c in self.capabilities)
            or any(t.paid for t in self.tools)
        )

    def declares_network(self) -> bool:
        return (
            any(c.network for c in self.capabilities)
            or self.search.network
            or PermissionKind.NETWORK.value in self.permission_kinds()
        )


__all__ = [
    "RUNTIME_PACK_SCHEMA_VERSION",
    "MANIFEST_FILENAME",
    "KNOWN_PERMISSION_KINDS",
    "DANGEROUS_PERMISSION_KINDS",
    "PermissionKind",
    "DefaultDecision",
    "RuntimeKind",
    "ToolKind",
    "OpaqueNodePolicy",
    "RuntimeIdentity",
    "RuntimeEntrypoints",
    "RuntimePermission",
    "RuntimeCapability",
    "RuntimeToolDeclaration",
    "RuntimeMcpDeclaration",
    "RuntimeModelsDeclaration",
    "RuntimeStorageDeclaration",
    "RuntimeMemoryDeclaration",
    "RuntimeSearchDeclaration",
    "RuntimeObservabilityDeclaration",
    "RuntimeIrDeclaration",
    "RuntimePolicyDeclaration",
    "RuntimeTestsDeclaration",
    "RuntimePackProvenance",
    "RuntimePackManifest",
]
