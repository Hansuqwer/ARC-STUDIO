"""Built-in mock capability catalog for ARC Mobile Runtime MVP.

All capabilities are mock/simulator-only. No real native bridges exist.
"""

from __future__ import annotations

from .models import (
    MobileApprovalMode,
    MobileCapability,
    MobileCapabilityCategory,
    MobileDataSensitivity,
    MobilePlatform,
    MobilePermissionRequirement,
)
from .hashing import capability_hash as _hash


def _seal(cap: MobileCapability) -> MobileCapability:
    return cap.model_copy(update={"capability_hash": _hash(cap)})


def _perm(id: str, platform: MobilePlatform = MobilePlatform.ALL) -> MobilePermissionRequirement:
    return MobilePermissionRequirement(id=id, platform=platform, mock_safe=True)


MOCK_CAPABILITIES: list[MobileCapability] = [
    _seal(
        MobileCapability(
            id="device.camera.capture.mock",
            name="Camera Capture (Mock)",
            description="Simulated camera capture; returns a fixture image. No real camera access.",
            category=MobileCapabilityCategory.MEDIA,
            platforms=[
                MobilePlatform.IOS,
                MobilePlatform.ANDROID,
                MobilePlatform.FLUTTER,
                MobilePlatform.EXPO,
            ],
            required_permissions=[
                _perm("ios.camera", MobilePlatform.IOS),
                _perm("android.CAMERA", MobilePlatform.ANDROID),
            ],
            approval_mode=MobileApprovalMode.REQUIRED,
            data_sensitivity=MobileDataSensitivity.HIGH,
            reads=True,
            writes=False,
            network=False,
            background=False,
            simulator_supported=True,
            test_fixture_supported=True,
            requires_trust=True,
        )
    ),
    _seal(
        MobileCapability(
            id="device.microphone.transcribe.mock",
            name="Microphone Transcription (Mock)",
            description="Simulated audio transcription; returns fixture transcript. No real microphone access.",
            category=MobileCapabilityCategory.MEDIA,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            required_permissions=[
                _perm("ios.microphone", MobilePlatform.IOS),
                _perm("android.RECORD_AUDIO", MobilePlatform.ANDROID),
            ],
            approval_mode=MobileApprovalMode.BLOCKING,
            data_sensitivity=MobileDataSensitivity.CRITICAL,
            reads=True,
            writes=False,
            network=False,
            background=False,
            simulator_supported=True,
            test_fixture_supported=True,
            requires_trust=True,
            requires_hitl=True,
        )
    ),
    _seal(
        MobileCapability(
            id="device.location.current.mock",
            name="Location (Mock)",
            description="Simulated GPS coordinates; returns fixture location. No real GPS access.",
            category=MobileCapabilityCategory.SENSOR,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            required_permissions=[
                _perm("ios.location.whenInUse", MobilePlatform.IOS),
                _perm("android.ACCESS_FINE_LOCATION", MobilePlatform.ANDROID),
            ],
            approval_mode=MobileApprovalMode.REQUIRED,
            data_sensitivity=MobileDataSensitivity.HIGH,
            reads=True,
            writes=False,
            network=False,
            background=False,
            simulator_supported=True,
            test_fixture_supported=True,
            requires_trust=True,
        )
    ),
    _seal(
        MobileCapability(
            id="device.calendar.read.mock",
            name="Calendar Read (Mock)",
            description="Simulated calendar events; returns fixture events. No real calendar access.",
            category=MobileCapabilityCategory.COMMUNICATION,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            required_permissions=[
                _perm("ios.calendars", MobilePlatform.IOS),
                _perm("android.READ_CALENDAR", MobilePlatform.ANDROID),
            ],
            approval_mode=MobileApprovalMode.REQUIRED,
            data_sensitivity=MobileDataSensitivity.HIGH,
            reads=True,
            writes=False,
            network=False,
            background=False,
            simulator_supported=True,
            test_fixture_supported=True,
            requires_trust=True,
        )
    ),
    _seal(
        MobileCapability(
            id="device.calendar.write.mock",
            name="Calendar Write (Mock)",
            description="Simulated calendar write; no real events created.",
            category=MobileCapabilityCategory.COMMUNICATION,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            required_permissions=[
                _perm("ios.calendars", MobilePlatform.IOS),
                _perm("android.WRITE_CALENDAR", MobilePlatform.ANDROID),
            ],
            approval_mode=MobileApprovalMode.BLOCKING,
            data_sensitivity=MobileDataSensitivity.HIGH,
            reads=False,
            writes=True,
            network=False,
            background=False,
            auditable=True,
            requires_trust=True,
            requires_hitl=True,
            simulator_supported=True,
            test_fixture_supported=True,
        )
    ),
    _seal(
        MobileCapability(
            id="device.contacts.search.mock",
            name="Contacts Search (Mock)",
            description="Simulated contacts search; returns fixture contacts. No real contacts access.",
            category=MobileCapabilityCategory.COMMUNICATION,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            required_permissions=[
                _perm("ios.contacts", MobilePlatform.IOS),
                _perm("android.READ_CONTACTS", MobilePlatform.ANDROID),
            ],
            approval_mode=MobileApprovalMode.BLOCKING,
            data_sensitivity=MobileDataSensitivity.CRITICAL,
            reads=True,
            writes=False,
            network=False,
            background=False,
            simulator_supported=True,
            test_fixture_supported=True,
            requires_trust=True,
            requires_hitl=True,
        )
    ),
    _seal(
        MobileCapability(
            id="device.files.pick.mock",
            name="File Picker (Mock)",
            description="Simulated file picker; returns fixture file reference.",
            category=MobileCapabilityCategory.STORAGE,
            platforms=[MobilePlatform.ALL],
            approval_mode=MobileApprovalMode.RECOMMENDED,
            data_sensitivity=MobileDataSensitivity.MEDIUM,
            reads=True,
            writes=False,
            network=False,
            background=False,
            simulator_supported=True,
            test_fixture_supported=True,
        )
    ),
    _seal(
        MobileCapability(
            id="device.photos.pick.mock",
            name="Photo Picker (Mock)",
            description="Simulated photo picker; returns fixture image metadata. No real PhotoKit access.",
            category=MobileCapabilityCategory.MEDIA,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            required_permissions=[
                _perm("ios.photoLibrary", MobilePlatform.IOS),
                _perm("android.READ_MEDIA_IMAGES", MobilePlatform.ANDROID),
            ],
            approval_mode=MobileApprovalMode.REQUIRED,
            data_sensitivity=MobileDataSensitivity.HIGH,
            reads=True,
            writes=False,
            network=False,
            background=False,
            simulator_supported=True,
            test_fixture_supported=True,
            requires_trust=True,
        )
    ),
    _seal(
        MobileCapability(
            id="device.notifications.schedule.mock",
            name="Notifications (Mock)",
            description="Simulated local notification scheduling; no real notification sent.",
            category=MobileCapabilityCategory.COMMUNICATION,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            approval_mode=MobileApprovalMode.RECOMMENDED,
            data_sensitivity=MobileDataSensitivity.LOW,
            reads=False,
            writes=True,
            network=False,
            background=False,
            auditable=True,
            simulator_supported=True,
            test_fixture_supported=True,
        )
    ),
    _seal(
        MobileCapability(
            id="app.memory.write.mock",
            name="App Memory Write (Mock)",
            description="Simulated in-app memory write; stored locally in mock store.",
            category=MobileCapabilityCategory.APP,
            platforms=[MobilePlatform.ALL],
            approval_mode=MobileApprovalMode.NONE,
            data_sensitivity=MobileDataSensitivity.LOW,
            reads=False,
            writes=True,
            network=False,
            background=False,
            auditable=True,
            replayable=True,
            simulator_supported=True,
            test_fixture_supported=True,
        )
    ),
    _seal(
        MobileCapability(
            id="app.memory.retrieve.mock",
            name="App Memory Retrieve (Mock)",
            description="Simulated in-app memory retrieval from mock store.",
            category=MobileCapabilityCategory.APP,
            platforms=[MobilePlatform.ALL],
            approval_mode=MobileApprovalMode.NONE,
            data_sensitivity=MobileDataSensitivity.LOW,
            reads=True,
            writes=False,
            network=False,
            background=False,
            replayable=True,
            simulator_supported=True,
            test_fixture_supported=True,
        )
    ),
    _seal(
        MobileCapability(
            id="app.local_search.query.mock",
            name="Local Search (Mock)",
            description="Simulated local app search; returns fixture results.",
            category=MobileCapabilityCategory.APP,
            platforms=[MobilePlatform.ALL],
            approval_mode=MobileApprovalMode.NONE,
            data_sensitivity=MobileDataSensitivity.LOW,
            reads=True,
            writes=False,
            network=False,
            background=False,
            replayable=True,
            simulator_supported=True,
            test_fixture_supported=True,
        )
    ),
    _seal(
        MobileCapability(
            id="app.ui.action_plan.mock",
            name="UI Action Plan (Mock)",
            description="Simulated UI automation plan; describes steps without executing native UI.",
            category=MobileCapabilityCategory.UI,
            platforms=[MobilePlatform.ALL],
            approval_mode=MobileApprovalMode.RECOMMENDED,
            data_sensitivity=MobileDataSensitivity.NONE,
            reads=False,
            writes=False,
            network=False,
            background=False,
            replayable=True,
            auditable=True,
            simulator_supported=True,
            test_fixture_supported=True,
        )
    ),
]

_CATALOG: dict[str, MobileCapability] = {c.id: c for c in MOCK_CAPABILITIES}

# Fail fast at import if the catalog has duplicate IDs (programming error)
assert len(_CATALOG) == len(MOCK_CAPABILITIES), (
    f"Duplicate capability IDs in MOCK_CAPABILITIES: "
    f"{[c.id for c in MOCK_CAPABILITIES if MOCK_CAPABILITIES.count(c) > 1]}"
)


def get_capability(capability_id: str) -> MobileCapability | None:
    return _CATALOG.get(capability_id)


def list_capabilities() -> list[MobileCapability]:
    return list(MOCK_CAPABILITIES)
