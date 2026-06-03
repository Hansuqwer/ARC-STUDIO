"""ARC Mobile Runtime SDK.

Local-first, privacy-first, simulator-first mobile agent runtime foundation.
All sensitive capabilities are mock-only in MVP. No real native bridges.
"""

from .capabilities import get_capability, list_capabilities
from .hashing import capability_hash, manifest_hash, plan_hash, report_hash
from .manifest import MobileManifestLoadError, build_default_manifest, load_manifest
from .models import (
    MOBILE_SCHEMA_VERSION,
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
    "list_capabilities",
    "get_capability",
    "load_manifest",
    "build_default_manifest",
]
