"""Opt-in Firecracker integration smoke test (Phase 37 Slice 37.21).

Pre-check result (2026-05-26):
  - `which firecracker`: not found (absent on this macOS host)
  - `ls -la /dev/kvm`: No such file or directory (Darwin, no KVM support)
  - Platform: Darwin 25.4.0

Step 4 status: HOST-SKIPPED — firecracker and /dev/kvm absent on this host.
All tests in TestFirecrackerSmokeRealHost will skip unless run on a Linux
host with firecracker installed, /dev/kvm accessible, ARC_MICROVM_INTEGRATION=1,
and ARC_FC_REAL_EXEC=1.

Truth constraints:
  - FirecrackerIntegrationHarness.run() requires a real runner or raises.
  - MicroVMIsolationProvider.execute() still raises NotImplementedError.
  - No Firecracker VM is created by any test here without ARC_FC_REAL_EXEC=1.
  - CI does NOT set ARC_FC_REAL_EXEC=1; all real-host tests are always skipped.
"""

from __future__ import annotations

import os
import platform
import shutil

import pytest

from agent_runtime_cockpit.isolation.microvm import (
    FirecrackerIntegrationHarness,
    build_firecracker_no_network_run_plan,
    firecracker_integration_available,
    firecracker_real_exec_available,
)

# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

_REAL_EXEC_REASON = (
    "Firecracker real-host: requires Linux + /dev/kvm + firecracker binary + "
    "ARC_MICROVM_INTEGRATION=1 + ARC_FC_REAL_EXEC=1. "
    "Pre-check on this host (Darwin 25.4.0): firecracker absent, /dev/kvm absent. "
    "Step 4 cannot be proven on this host."
)

_REAL_EXEC_GATE = (
    platform.system() == "Linux"
    and os.environ.get("ARC_MICROVM_INTEGRATION") == "1"
    and bool(shutil.which("firecracker"))
    and os.path.exists("/dev/kvm")
    and os.environ.get("ARC_FC_REAL_EXEC") == "1"
)


# ---------------------------------------------------------------------------
# Always-run: confirm firecracker_integration_available() returns False here
# ---------------------------------------------------------------------------


class TestFirecrackerSmokeSkipBehaviour:
    """Always-run tests confirming CI skip behaviour and host pre-check."""

    def test_firecracker_not_available_on_this_host(self):
        """Confirms firecracker is not available on this macOS host.

        Pre-check: `which firecracker` → not found, `/dev/kvm` → absent.
        firecracker_integration_available() must return False.
        """
        # On this macOS host, all Firecracker preconditions fail.
        # This test always passes and documents the host state.
        result = firecracker_integration_available()
        assert isinstance(result, bool)
        # On macOS or without /dev/kvm, must be False
        if platform.system() != "Linux":
            assert result is False

    def test_firecracker_integration_available_false_without_kvm(self, monkeypatch):
        """firecracker_integration_available() is False without /dev/kvm."""
        monkeypatch.setattr(
            shutil, "which", lambda name: "/usr/bin/firecracker" if name == "firecracker" else None
        )
        monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.platform.system", lambda: "Linux"
        )
        # /dev/kvm does not exist on this host → _kvm_available() returns False
        assert firecracker_integration_available() is False

    def test_firecracker_integration_available_false_on_darwin(self, monkeypatch):
        """firecracker_integration_available() is always False on macOS."""
        monkeypatch.setattr(
            shutil,
            "which",
            lambda name: "/usr/local/bin/firecracker" if name == "firecracker" else None,
        )
        monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.platform.system", lambda: "Darwin"
        )
        assert firecracker_integration_available() is False

    def test_firecracker_real_exec_available_requires_dual_gate_and_artifacts(self, monkeypatch):
        monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
        monkeypatch.setenv("ARC_FC_REAL_EXEC", "1")
        monkeypatch.setenv("ARC_FIRECRACKER_KERNEL", "/tmp/vmlinux")
        monkeypatch.setenv("ARC_FIRECRACKER_ROOTFS", "/tmp/rootfs.ext4")
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.firecracker_integration_available",
            lambda: False,
        )
        assert firecracker_real_exec_available() is False


class TestFirecrackerNoNetworkDesignProof:
    """Always-run no-NIC design-proof tests."""

    def test_no_network_config_omits_network_interfaces(self, tmp_path):
        plan = build_firecracker_no_network_run_plan(
            ["uname", "-a"],
            kernel_path=tmp_path / "vmlinux",
            rootfs_path=tmp_path / "rootfs.ext4",
            work_dir=tmp_path,
            instance_name="arc-fc-test",
        )
        config = plan.config.to_firecracker_config()
        assert "network-interfaces" not in config
        assert plan.config.network_interfaces_configured is False
        assert plan.config.strict_network_candidate is True
        assert plan.config.strict_network_proof == "not_proven"
        assert plan.real_boot_attempted is False

    def test_no_network_plan_contains_required_guest_proofs(self, tmp_path):
        plan = build_firecracker_no_network_run_plan(
            ["pwd"],
            kernel_path=tmp_path / "vmlinux",
            rootfs_path=tmp_path / "rootfs.ext4",
            work_dir=tmp_path,
        )
        assert ["ip", "route"] in plan.proof_commands
        assert ["curl", "--connect-timeout", "2", "https://example.com"] in plan.proof_commands
        assert "ARC_FC_REAL_EXEC=1" in plan.host_gates

    def test_blocked_real_harness_emits_audit_event(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
        harness = FirecrackerIntegrationHarness(workspace_root=tmp_path, runner=None)
        with pytest.raises(
            Exception, match="real Firecracker run is blocked|ARC_MICROVM_INTEGRATION"
        ):
            harness.run(["uname", "-a"], require_gate=False)
        assert (tmp_path / "audit" / "sandbox.events.jsonl").exists()


# ---------------------------------------------------------------------------
# Real-host tests — only run with full Linux + KVM + binary + dual gate
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _REAL_EXEC_GATE, reason=_REAL_EXEC_REASON)
class TestFirecrackerSmokeRealHost:
    """Real Firecracker lifecycle tests.

    These tests require a Linux host with:
      - firecracker binary installed
      - /dev/kvm accessible (user in kvm group or root)
      - ARC_MICROVM_INTEGRATION=1
      - ARC_FC_REAL_EXEC=1

    NOTE: FirecrackerIntegrationHarness._run() raises FirecrackerHarnessError
    when runner=None and real Firecracker execution is not yet implemented
    (ADR-024). These tests will fail with FirecrackerHarnessError until the
    real Firecracker runner is implemented. They are structured as a
    placeholder proving the test gate works correctly.

    What is proven by these tests (when Firecracker execution is implemented):
      P1 — Lifecycle: preflight → create_vm → mount_workspace → network_proof
               → exec → stop_vm → teardown completes.
      P4 — Teardown: harness.teardown_attempted=True after any outcome.

    What is NOT proven (pending implementation):
      P2 — Network-off: no TAP/NAT configured; guest isolation proof pending.
      P3 — Workspace-mount: virtiofs/block device mapping not yet implemented.
      P5 — Symlink escape: requires guest-side traversal test.
    """

    def test_firecracker_harness_requires_real_runner_or_implementation(self, tmp_path):
        """Firecracker harness raises when no runner and binary not implemented.

        This test documents the current state: FirecrackerIntegrationHarness
        requires either an injected runner or a real Firecracker implementation.
        Until the real runner is implemented, this test verifies the harness
        raises a clear error rather than silently failing.
        """
        from agent_runtime_cockpit.isolation.microvm import FirecrackerHarnessError

        harness = FirecrackerIntegrationHarness(
            workspace_root=tmp_path,
            runner=None,  # no fake runner and no real impl yet
            instance_name="arc-fc-real-test",
        )
        # Will raise FirecrackerHarnessError because runner=None and real impl missing
        with pytest.raises(FirecrackerHarnessError):
            harness.run(["uname", "-a"], timeout_seconds=300, require_gate=True)
