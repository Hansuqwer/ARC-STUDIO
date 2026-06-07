"""ARC Mobile Runtime SDK — typed models.

Schema version 1. Local-first, privacy-first, simulator-first.
All sensitive capabilities are mock-only in MVP.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

MOBILE_SCHEMA_VERSION = 1


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class MobilePlatform(str, Enum):
    IOS = "ios"
    ANDROID = "android"
    FLUTTER = "flutter"
    EXPO = "expo"
    REACT_NATIVE = "react_native"
    WEB = "web"
    ALL = "all"


class MobileDataSensitivity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MobileApprovalMode(str, Enum):
    NONE = "none"  # no approval needed
    RECOMMENDED = "recommended"
    REQUIRED = "required"
    BLOCKING = "blocking"  # blocks execution until approved


class MobileCapabilityCategory(str, Enum):
    DEVICE = "device"
    APP = "app"
    NETWORK = "network"
    STORAGE = "storage"
    UI = "ui"
    SENSOR = "sensor"
    MEDIA = "media"
    COMMUNICATION = "communication"


class MobilePermissionRequirement(_Base):
    id: str  # e.g. "ios.camera", "android.READ_CONTACTS"
    platform: MobilePlatform
    required: bool = True
    reason: Optional[str] = None
    mock_safe: bool = True  # True = mock version available, no real OS prompt needed


class MobileAuditRequirement(_Base):
    required: bool = False
    level: str = "none"  # none | arc_sha256 | full


class MobileReplayProfile(_Base):
    replayable: bool = False
    deterministic: bool = False
    requires_real_device: bool = False
    note: Optional[str] = None


class MobileCapability(_Base):
    schema_version: int = MOBILE_SCHEMA_VERSION
    id: str
    name: str
    description: str = ""
    category: MobileCapabilityCategory = MobileCapabilityCategory.DEVICE
    platforms: list[MobilePlatform] = Field(default_factory=lambda: [MobilePlatform.ALL])
    required_permissions: list[MobilePermissionRequirement] = Field(default_factory=list)
    approval_mode: MobileApprovalMode = MobileApprovalMode.NONE
    data_sensitivity: MobileDataSensitivity = MobileDataSensitivity.NONE
    reads: bool = False
    writes: bool = False
    network: bool = False
    paid: bool = False
    background: bool = False
    replayable: bool = True
    auditable: bool = True
    mcp_exposable: bool = False  # requires explicit safe flag
    simulator_supported: bool = True
    test_fixture_supported: bool = True
    requires_trust: bool = False
    requires_hitl: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    capability_hash: Optional[str] = None  # excluded from own hash computation


class MobilePlatformSupport(_Base):
    platform: MobilePlatform
    min_os_version: Optional[str] = None
    stub_only: bool = True  # True = MVP stub, no real native bridge
    framework: Optional[str] = None  # flutter | expo | react_native | native


class MobileRuntimeManifest(_Base):
    schema_version: int = MOBILE_SCHEMA_VERSION
    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    platforms: list[MobilePlatformSupport] = Field(default_factory=list)
    capabilities: list[MobileCapability] = Field(default_factory=list)
    background_execution: bool = False  # blocked in MVP
    network_by_default: bool = False  # blocked in MVP
    simulator_mode: bool = True  # True = simulator-first
    privacy_manifest_intent: bool = True  # developer declares intent; no file is generated
    manifest_hash: Optional[str] = None  # computed on seal

    @property
    def privacy_manifest(self) -> bool:
        """Deprecated alias for privacy_manifest_intent. Use privacy_manifest_intent."""
        return self.privacy_manifest_intent


class MobileActionStep(_Base):
    step_id: str
    capability_id: str
    description: str = ""
    mock: bool = True  # MVP: all steps must use mock capabilities
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: dict[str, Any] = Field(default_factory=dict)


class MobileActionPlan(_Base):
    schema_version: int = MOBILE_SCHEMA_VERSION
    plan_id: str
    name: str = ""
    steps: list[MobileActionStep] = Field(default_factory=list)
    requires_network: bool = False
    requires_background: bool = False
    plan_hash: Optional[str] = None


class MobileSimulationStepResult(_Base):
    step_id: str
    capability_id: str
    allowed: bool
    mock: bool = True
    blocked_reason: Optional[str] = None
    predicted_permissions: list[str] = Field(default_factory=list)
    predicted_approvals: list[str] = Field(default_factory=list)
    audit_required: bool = False
    replayable: bool = True


class MobileActionSimulationReport(_Base):
    schema_version: int = MOBILE_SCHEMA_VERSION
    plan_id: str
    overall_allowed: bool = True
    steps: list[MobileSimulationStepResult] = Field(default_factory=list)
    blocked_steps: list[str] = Field(default_factory=list)
    requires_permissions: list[str] = Field(default_factory=list)
    requires_approvals: list[str] = Field(default_factory=list)
    risk_level: str = "low"  # low | medium | high | critical
    warnings: list[str] = Field(default_factory=list)
    report_hash: Optional[str] = None


class MobileRuntimePackBridge(_Base):
    """Metadata linking a MobileRuntimeManifest to a RuntimePack."""

    pack_id: str
    pack_version: str = "0.1.0"
    runtime_kind: str = "mobile"
    manifest_id: str
    manifest_hash: Optional[str] = None
    capabilities_count: int = 0
    platforms: list[str] = Field(default_factory=list)
    simulator_only: bool = True
