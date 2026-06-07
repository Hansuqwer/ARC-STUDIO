"""ARC Mobile Runtime SDK.

Local-first, privacy-first, simulator-first mobile agent runtime foundation.
All sensitive capabilities are mock-only in MVP. No real native bridges.
"""

from .capabilities import get_capability, list_capabilities
from .audit_retention import apply_retention, rotate_if_oversized
from .capability_gate import CapabilityEntryGate, FIXTURES_ROUTE, GateDecision
from .feature_flags import FeatureFlags
from .hashing import capability_hash, manifest_hash, plan_hash, report_hash
from .manifest import MobileManifestLoadError, build_default_manifest, load_manifest
from .models import (
    MOBILE_SCHEMA_VERSION,
    MOBILE_CAPABILITY_ID_PATTERN,
    MobileActionPlan,
    MobileActionSimulationReport,
    MobileActionStep,
    MobileApprovalMode,
    MobileAuditRequirement,
    MobileCapability,
    MobileCapabilityCategory,
    MobileDataSensitivity,
    MobilePlatform,
    MobilePlatformSupport,
    MobilePermissionRequirement,
    MobileReplayProfile,
    MobileRuntimeManifest,
    MobileRuntimePackBridge,
    MobileSimulationStepResult,
)
from .fixtures_registry import get_fixture, list_fixtures, register
from .mock_store import MockStore, get_default_store, reset_default_store
from .approval import ApprovalGrant, issue_grant, revoke_grant, get_grant, list_active_grants
from .policy import (
    EnterprisePolicyHook,
    MOBILE_POLICY_VERSION,
    MobilePolicyDecision,
    explain_capability_policy,
    explain_plan_policy,
)
from .policy_context import (
    OrgPolicyBundle,
    OrgPolicyContext,
    TenantPolicyHook,
    sign_org_bundle,
    verify_org_bundle,
)
from .recorder import (
    MobileRuntimeEvent,
    MobileTrace,
    append_trace,
    build_trace,
    read_trace,
    verify_trace,
)
from .offline_queue import OfflineQueue, QueueEntry
from .mcp_bridge import BridgeDecision, MobileMcpDevBridge
from .privacy_budget import EgressDecision, EgressGuard, PrivacyBudget, compute_privacy_budget
from .secure_store import (
    InMemoryKeyProvider,
    KeyProvider,
    SecureLocalStore,
    SecureStoreError,
)
from .signing import SignedPlanEnvelope, sign_plan, verify_plan
from .sbom import generate_sbom
from .siem_export import export_trace, export_trace_cef, export_trace_json
from .replay import ReplayDiff, replay_trace
from .simulator import simulate_action_plan
from .validation import (
    MobileValidationReport,
    ValidationFinding,
    validate_action_plan,
    validate_capability,
    validate_manifest,
)

__all__ = [
    "MOBILE_SCHEMA_VERSION",
    "MOBILE_CAPABILITY_ID_PATTERN",
    "MobileCapability",
    "MobileCapabilityCategory",
    "MobilePlatform",
    "MobilePlatformSupport",
    "MobileDataSensitivity",
    "MobileApprovalMode",
    "MobilePermissionRequirement",
    "MobileAuditRequirement",
    "MobileReplayProfile",
    "MobileRuntimeManifest",
    "MobileActionPlan",
    "MobileActionStep",
    "MobileActionSimulationReport",
    "MobileSimulationStepResult",
    "MobileRuntimePackBridge",
    "MobileRuntimeEvent",
    "MobileTrace",
    "MobilePolicyDecision",
    "EnterprisePolicyHook",
    "MOBILE_POLICY_VERSION",
    "OrgPolicyBundle",
    "OrgPolicyContext",
    "TenantPolicyHook",
    "sign_org_bundle",
    "verify_org_bundle",
    "PrivacyBudget",
    "compute_privacy_budget",
    "EgressGuard",
    "EgressDecision",
    "OfflineQueue",
    "QueueEntry",
    "MobileMcpDevBridge",
    "BridgeDecision",
    "SecureLocalStore",
    "InMemoryKeyProvider",
    "KeyProvider",
    "SecureStoreError",
    "SignedPlanEnvelope",
    "sign_plan",
    "verify_plan",
    "generate_sbom",
    "export_trace",
    "export_trace_cef",
    "export_trace_json",
    "ApprovalGrant",
    "issue_grant",
    "revoke_grant",
    "get_grant",
    "list_active_grants",
    "MobileManifestLoadError",
    "MobileValidationReport",
    "ValidationFinding",
    "capability_hash",
    "manifest_hash",
    "plan_hash",
    "report_hash",
    "validate_capability",
    "validate_manifest",
    "validate_action_plan",
    "simulate_action_plan",
    "build_trace",
    "append_trace",
    "read_trace",
    "verify_trace",
    "replay_trace",
    "ReplayDiff",
    "explain_capability_policy",
    "explain_plan_policy",
    "list_capabilities",
    "get_capability",
    "FeatureFlags",
    "CapabilityEntryGate",
    "GateDecision",
    "FIXTURES_ROUTE",
    "apply_retention",
    "rotate_if_oversized",
    "load_manifest",
    "build_default_manifest",
    "get_fixture",
    "list_fixtures",
    "register",
    "MockStore",
    "get_default_store",
    "reset_default_store",
    "ReplayDiff",
    "replay_trace",
]
