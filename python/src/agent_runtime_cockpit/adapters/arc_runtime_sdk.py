"""ARC Runtime SDK adapter (R79 / Phase 111, Slice 110.1).

Detects standalone ARC Runtime SDK projects (`arc-sdk.json`) and reports honest,
simulator/mock-only capabilities through the standard ``RuntimeAdapter`` contract
so `arc runtimes` discovers them.

Truth constraints (see docs/phases.md Phase 111):
- Default mode is always ``fake`` (simulator/mock); there is no native bridge,
  no app-store automation, and no provider calls.
- This adapter does not yet implement a run path (`run_workflow` delegation to
  the standalone `arc-runtime` CLI is a later slice), so ``can_run`` is always
  ``False`` — we never report a runnable path we cannot honor.
- ``gated_local`` (per-capability gate approvals in `arc-sdk.json`) plus run
  delegation are deferred to Slice 110.4/110.5.

This is a clean in-repo vendor of the standalone SDK adapter; it intentionally
does not import the SDK's own (vendored) copy of ``agent_runtime_cockpit`` to
avoid import collisions.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..protocol.capabilities import RuntimeCapabilities
from .base import CapabilityReport, DoctorAction, RuntimeAdapter

_SDK_MANIFEST = "arc-sdk.json"

# Evidence weights for detect() confidence (mirrors the standalone SDK adapter).
_EVIDENCE = {
    "arc_sdk_json": 0.50,
    "arc_runtime_pack_json": 0.25,
    "capsules_dir": 0.10,
    "fixtures_dir": 0.10,
    "arc_runtime_binary": 0.05,
}
_DETECT_THRESHOLD = 0.50  # requires the primary arc-sdk.json signal


class ArcRuntimeSDKAdapter(RuntimeAdapter):
    """Adapter for standalone ARC Runtime SDK projects (simulator/mock only)."""

    @property
    def adapter_id(self) -> str:
        return "arc-runtime-sdk"

    @property
    def adapter_name(self) -> str:
        return "ARC Runtime SDK"

    def capabilities(self) -> RuntimeCapabilities:
        # Honest static report: inspect/export/stream/replay of simulator
        # artifacts are supported; can_run stays False (no run path here yet),
        # and no paid/network/secret/shell requirements in fake mode.
        return RuntimeCapabilities(
            can_inspect=True,
            can_run=False,
            can_trace=True,
            can_replay=True,
            can_export_schema=True,
            can_export_workflow=True,
            can_stream_events=True,
            can_audit=False,
            can_checkpoint=False,
            can_resume=False,
            can_fork=False,
            can_diff=False,
            can_eval=False,
            requires_paid_calls=False,
            requires_network=False,
            requires_shell=False,
            requires_secrets=False,
        )

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        ws = Path(workspace)
        conf = 0.0
        evidence: list[str] = []

        sdk_json = ws / _SDK_MANIFEST
        if sdk_json.is_file():
            try:
                data = json.loads(sdk_json.read_text(encoding="utf-8"))
                version = data.get("schema_version")
                if version == "1.0.0":
                    conf += _EVIDENCE["arc_sdk_json"]
                    evidence.append("arc-sdk.json (schema_version=1.0.0)")
                else:
                    conf += _EVIDENCE["arc_sdk_json"] * 0.3
                    evidence.append(f"arc-sdk.json (schema_version={version})")
            except (json.JSONDecodeError, OSError):
                conf += _EVIDENCE["arc_sdk_json"] * 0.1
                evidence.append("arc-sdk.json (parse error)")

        if (ws / "arc-runtime-pack.json").is_file():
            conf += _EVIDENCE["arc_runtime_pack_json"]
            evidence.append("arc-runtime-pack.json")
        if (ws / "capsules").is_dir():
            conf += _EVIDENCE["capsules_dir"]
            evidence.append("capsules/")
        if (ws / "fixtures").is_dir():
            conf += _EVIDENCE["fixtures_dir"]
            evidence.append("fixtures/")
        if shutil.which("arc-runtime"):
            conf += _EVIDENCE["arc_runtime_binary"]
            evidence.append("arc-runtime CLI")

        conf = min(conf, 1.0)
        return conf >= _DETECT_THRESHOLD, conf, evidence

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        actions: list[DoctorAction] = []
        if not shutil.which("arc-runtime"):
            actions.append(
                DoctorAction(
                    id="install-arc-runtime",
                    label="Install the arc-runtime CLI",
                    description=(
                        "The standalone arc-runtime CLI is needed to simulate/replay "
                        "SDK capsules. ARC Studio detects and inspects the project "
                        "without it, but simulation requires it."
                    ),
                    command="npm install -g @arc/runtime-sdk",
                    safe_to_auto_run=False,
                )
            )
        return actions

    def capability_report(self, workspace: Path) -> CapabilityReport:
        ws = Path(workspace)
        detected, _conf, evidence = self.detect(ws)
        sdk_json = ws / _SDK_MANIFEST

        if not detected:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=False,
                can_run=False,
                availability="not_detected",
                reason="No arc-sdk.json found in workspace.",
                detected_artifacts=evidence,
                test_level="unknown",
                fake_offline_supported=True,
                has_stable_ids=True,
                doctor_actions=self._doctor_actions(ws),
            )

        version: str | None = None
        requires_paid = False
        gate_approvals = 0
        if sdk_json.is_file():
            try:
                data = json.loads(sdk_json.read_text(encoding="utf-8"))
                version = data.get("sdk_version")
                caps = data.get("capabilities", [])
                requires_paid = any(
                    isinstance(c, dict) and c.get("category") == "paid_model" for c in caps
                )
                gate_policy = data.get("gate_policy", {})
                approved = gate_policy.get("approved", []) if isinstance(gate_policy, dict) else []
                gate_approvals = len(approved) if isinstance(approved, list) else 0
            except (json.JSONDecodeError, OSError):
                return CapabilityReport(
                    runtime_id=self.adapter_id,
                    detected=True,
                    can_run=False,
                    availability="detected_not_runnable",
                    reason="arc-sdk.json present but could not be parsed.",
                    detected_artifacts=evidence,
                    test_level="fake_offline",
                    fake_offline_supported=True,
                    has_stable_ids=True,
                    doctor_actions=self._doctor_actions(ws),
                )

        # Honest stance: detected + simulator/mock supported, but no in-repo run
        # path yet, so can_run is False even if gate approvals exist. The pending
        # gated_local + run delegation is noted in the reason.
        reason = (
            "Detected ARC Runtime SDK project (simulator/mock only). "
            "ARC Studio inspects/streams capsule artifacts in fake mode; a runnable "
            "path (gated_local execution via the standalone arc-runtime CLI) is not "
            "yet wired through this adapter."
        )
        if gate_approvals:
            reason += f" ({gate_approvals} gate_policy approval(s) present, not yet honored here.)"

        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=True,
            can_run=False,
            availability="detected_not_runnable",
            reason=reason,
            detected_artifacts=evidence,
            version=version,
            requires_paid_calls=requires_paid,
            test_level="fake_offline",
            fake_offline_supported=True,
            local_real_gated=False,
            local_real_available=False,
            provider_backed=False,
            has_stable_ids=True,
            doctor_actions=self._doctor_actions(ws),
        )


__all__ = ["ArcRuntimeSDKAdapter"]
