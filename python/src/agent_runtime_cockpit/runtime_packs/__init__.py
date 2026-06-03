"""ARC Runtime Pack SDK.

Discover, validate, inspect, and install *runtime packs* — static, typed,
policy-aware metadata bundles that let ARC support new agent runtimes without
hard-coding each one into the core repository.

In the MVP this package is strictly **local-first** and **inert**:

* it never imports or executes pack code,
* it never opens the network or starts a server,
* it never makes a model call, runs a tool, or starts an MCP server,
* validation is fully static and fail-closed,
* manifests are versioned, deterministic, and hashable.

The canonical artifact is ``arc-runtime-pack.json`` (``MANIFEST_FILENAME``).
"""

from __future__ import annotations

from .exporters import (
    ir_compatibility,
    to_capability_card,
    to_policy_findings,
    verify_mcp_against_registry,
)
from .hashing import canonical_json, manifest_hash, verify_manifest_hash
from .loader import (
    ManifestLoadError,
    find_manifest,
    inspect_manifest,
    load_manifest,
    load_manifest_dict,
)
from .models import (
    DANGEROUS_PERMISSION_KINDS,
    KNOWN_PERMISSION_KINDS,
    MANIFEST_FILENAME,
    RUNTIME_PACK_SCHEMA_VERSION,
    DefaultDecision,
    OpaqueNodePolicy,
    PermissionKind,
    RuntimeCapability,
    RuntimeEntrypoints,
    RuntimeIdentity,
    RuntimeIrDeclaration,
    RuntimeKind,
    RuntimeMcpDeclaration,
    RuntimeMemoryDeclaration,
    RuntimeModelsDeclaration,
    RuntimeObservabilityDeclaration,
    RuntimePackManifest,
    RuntimePackProvenance,
    RuntimePermission,
    RuntimePolicyDeclaration,
    RuntimeSearchDeclaration,
    RuntimeStorageDeclaration,
    RuntimeTestsDeclaration,
    RuntimeToolDeclaration,
    ToolKind,
)
from .redaction import find_secrets, is_safe_manifest, redact_manifest, redact_string
from .registry import (
    RuntimePackInstallError,
    RuntimePackRegistry,
    RuntimePackRegistryEntry,
    RuntimePackRegistryFile,
    create_registry,
)
from .scaffold import ScaffoldError, build_scaffold_manifest, init_pack
from .validation import (
    RuntimePackValidationReport,
    ValidationFinding,
    validate_manifest,
)

__all__ = [
    "RUNTIME_PACK_SCHEMA_VERSION",
    "MANIFEST_FILENAME",
    "KNOWN_PERMISSION_KINDS",
    "DANGEROUS_PERMISSION_KINDS",
    # enums
    "PermissionKind",
    "DefaultDecision",
    "RuntimeKind",
    "ToolKind",
    "OpaqueNodePolicy",
    # models
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
    # hashing
    "canonical_json",
    "manifest_hash",
    "verify_manifest_hash",
    # redaction
    "redact_manifest",
    "redact_string",
    "find_secrets",
    "is_safe_manifest",
    # validation
    "validate_manifest",
    "ValidationFinding",
    "RuntimePackValidationReport",
    # loader
    "load_manifest",
    "load_manifest_dict",
    "find_manifest",
    "inspect_manifest",
    "ManifestLoadError",
    # registry
    "RuntimePackRegistry",
    "RuntimePackRegistryEntry",
    "RuntimePackRegistryFile",
    "RuntimePackInstallError",
    "create_registry",
    # scaffold
    "init_pack",
    "build_scaffold_manifest",
    "ScaffoldError",
    # exporters
    "to_capability_card",
    "to_policy_findings",
    "ir_compatibility",
    "verify_mcp_against_registry",
]
