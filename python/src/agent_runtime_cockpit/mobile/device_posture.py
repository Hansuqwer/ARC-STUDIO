"""Device posture / MDM hook interface (R79.3 / Batch 7 T27).

A deterministic, simulator-preview interface for evaluating device posture (encryption, jailbreak,
passcode, MDM enrollment) against a policy. The only built-in source is a **fixtures** hook — this
does NOT read a real device. Real posture/MDM/attestation providers are a human-gated, out-of-scope
flip (the same hard safety boundary as native capability execution). All decisions are deterministic
(no LLM, no network).
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class DevicePosture(BaseModel):
    jailbroken: bool = False
    storage_encrypted: bool = True
    passcode_set: bool = True
    mdm_enrolled: bool = False
    os_version: str = "fixture-os/1.0"
    # Always true for any built-in source: this is never real device data.
    simulator_preview: bool = True


class PosturePolicy(BaseModel):
    forbid_jailbroken: bool = True
    require_encrypted: bool = True
    require_passcode: bool = False
    require_mdm: bool = False


class PostureDecision(BaseModel):
    allowed: bool
    violations: list[str] = Field(default_factory=list)
    posture: DevicePosture
    deterministic: bool = True
    simulator_preview: bool = True


class DevicePostureHook(Protocol):
    """Source of device posture. Real implementations are human-gated and out of scope."""

    def read(self) -> DevicePosture: ...


class FixtureDevicePostureHook:
    """Deterministic fixtures-only posture source. Never accesses a real device."""

    def __init__(self, posture: DevicePosture | None = None) -> None:
        self._posture = posture or DevicePosture()

    def read(self) -> DevicePosture:
        return self._posture


def evaluate_posture(
    posture: DevicePosture, policy: PosturePolicy | None = None
) -> PostureDecision:
    """Deterministically check a posture against a policy. Fail-closed: any violation denies."""
    pol = policy or PosturePolicy()
    violations: list[str] = []
    if pol.forbid_jailbroken and posture.jailbroken:
        violations.append("device_jailbroken")
    if pol.require_encrypted and not posture.storage_encrypted:
        violations.append("storage_not_encrypted")
    if pol.require_passcode and not posture.passcode_set:
        violations.append("no_passcode")
    if pol.require_mdm and not posture.mdm_enrolled:
        violations.append("not_mdm_enrolled")
    return PostureDecision(allowed=not violations, violations=violations, posture=posture)
