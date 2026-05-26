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
    FirecrackerProofRunner,
    generate_firecracker_proof_artifacts,
    firecracker_proof_gates,
    parse_firecracker_guest_proof,
    render_firecracker_guest_proof_init,
    validate_firecracker_proof_manifest,
    build_cloud_hypervisor_no_network_run_plan,
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
        assert ["cat", "/workspace/arc-sentinel.txt"] in plan.proof_commands
        assert ["cat", "/workspace/arc-host-escape-link"] in plan.proof_commands
        assert "ARC_FC_REAL_EXEC=1" in plan.host_gates

    def test_cloud_hypervisor_no_network_argv_omits_net_options(self, tmp_path):
        plan = build_cloud_hypervisor_no_network_run_plan(
            ["pwd"],
            kernel_path=tmp_path / "vmlinux",
            disk_path=tmp_path / "disk.raw",
            work_dir=tmp_path,
            instance_name="arc-ch-test",
        )
        argv = plan.config.to_cloud_hypervisor_argv()
        assert "--net" not in argv
        assert all(not arg.startswith("net=") for arg in argv)
        assert plan.config.network_interfaces_configured is False
        assert plan.config.strict_network_proof == "not_proven"

    def test_cloud_hypervisor_plan_contains_required_guest_proofs(self, tmp_path):
        plan = build_cloud_hypervisor_no_network_run_plan(
            ["pwd"],
            kernel_path=tmp_path / "vmlinux",
            disk_path=tmp_path / "disk.raw",
            work_dir=tmp_path,
        )
        assert ["ip", "route"] in plan.proof_commands
        assert ["curl", "--connect-timeout", "2", "https://example.com"] in plan.proof_commands
        assert ["cat", "/workspace/arc-sentinel.txt"] in plan.proof_commands
        assert ["cat", "/workspace/arc-host-escape-link"] in plan.proof_commands
        assert "ARC_CH_REAL_EXEC=1" in plan.host_gates

    def test_blocked_real_harness_emits_audit_event(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
        harness = FirecrackerIntegrationHarness(workspace_root=tmp_path, runner=None)
        with pytest.raises(
            Exception, match="real Firecracker run is blocked|ARC_MICROVM_INTEGRATION"
        ):
            harness.run(["uname", "-a"], require_gate=False)
        assert (tmp_path / "audit" / "sandbox.events.jsonl").exists()


class TestFirecrackerProofRunner:
    """Always-run private proof-runner tests; no real VM required."""

    def test_proof_gates_block_without_linux_kvm_binary_env(self, monkeypatch):
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.platform.system", lambda: "Darwin"
        )
        monkeypatch.setattr("agent_runtime_cockpit.isolation.microvm.shutil.which", lambda _: None)
        monkeypatch.delenv("ARC_MICROVM_INTEGRATION", raising=False)
        gates = firecracker_proof_gates()
        assert gates["ready"] is False
        assert "Linux required" in gates["blockers"]
        assert "firecracker binary missing" in gates["blockers"]

    def test_proof_runner_blocked_attempt_emits_audit(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.platform.system", lambda: "Linux"
        )
        monkeypatch.setattr("agent_runtime_cockpit.isolation.microvm.shutil.which", lambda _: None)
        runner = FirecrackerProofRunner(workspace_root=tmp_path, instance_name="arc-fc-proof")
        with pytest.raises(Exception, match="firecracker binary missing"):
            runner.run(["ip", "route"])
        events = (tmp_path / "audit" / "sandbox.events.jsonl").read_text(encoding="utf-8")
        assert '"runtime":"firecracker"' in events
        assert '"public_execution_enabled":false' in events

    def test_proof_runner_generates_lifecycle_and_teardown_with_fake_start(
        self, tmp_path, monkeypatch
    ):
        kernel = tmp_path / "vmlinux"
        rootfs = tmp_path / "rootfs.ext4"
        kernel.write_text("kernel", encoding="utf-8")
        rootfs.write_text("rootfs", encoding="utf-8")
        monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
        monkeypatch.setenv("ARC_FC_REAL_EXEC", "1")
        monkeypatch.setenv("ARC_FIRECRACKER_KERNEL", str(kernel))
        monkeypatch.setenv("ARC_FIRECRACKER_ROOTFS", str(rootfs))
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.platform.system", lambda: "Linux"
        )
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm._firecracker_binary",
            lambda: "/usr/bin/firecracker",
        )
        original_exists = __import__("pathlib", fromlist=["Path"]).Path.exists
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.Path.exists",
            lambda self: True if str(self) == "/dev/kvm" else original_exists(self),
        )
        monkeypatch.setattr("agent_runtime_cockpit.isolation.microvm.os.access", lambda *_: True)

        def fake_run(argv, *, timeout_seconds, max_bytes):
            assert "--config-file" in argv
            return (
                __import__(
                    "agent_runtime_cockpit.isolation.base", fromlist=["IsolationResult"]
                ).IsolationResult(
                    exit_code=0,
                    stdout="x" * (max_bytes + 10),
                    stderr="",
                    provider="microvm",
                    stdout_truncated=True,
                ),
                None,
            )

        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm._run_firecracker_process", fake_run
        )
        runner = FirecrackerProofRunner(workspace_root=tmp_path, instance_name="arc-fc-proof")
        result = runner.run(["ip", "route"])
        assert result.teardown_attempted is True
        assert result.lifecycle == [
            "preflight",
            "create_config",
            "start_vm",
            "proof_blocked",
            "teardown",
        ]
        assert result.network_interfaces_configured is False
        assert result.public_execution_enabled is False
        assert result.result.stdout_truncated is True
        assert "guest command channel" in result.proof_blocker

    def test_guest_proof_marker_parser_accepts_success_markers(self):
        proof = parse_firecracker_guest_proof(
            "boot\n"
            "ARC_FC_PROOF no_default_route=1\n"
            "ARC_FC_PROOF curl_failed=1\n"
            "ARC_FC_PROOF sentinel_readable=1\n"
            "ARC_FC_PROOF symlink_escape_blocked=1\n"
        )
        assert proof.marker_seen is True
        assert proof.network_proof_passed is True
        assert proof.workspace_proof_passed is True

    def test_guest_proof_marker_parser_rejects_default_route(self):
        proof = parse_firecracker_guest_proof(
            "ARC_FC_PROOF no_default_route=0\nARC_FC_PROOF curl_failed=1\n"
        )
        assert proof.marker_seen is True
        assert proof.network_proof_passed is False

    def test_guest_proof_init_snippet_is_proof_only(self):
        snippet = render_firecracker_guest_proof_init()
        assert "ARC_FC_PROOF no_default_route" in snippet
        assert "ARC_FC_PROOF curl_failed" in snippet
        assert "ARC_FC_PROOF sentinel_readable" in snippet
        assert "ARC_FC_PROOF symlink_escape_blocked" in snippet
        assert "curl --connect-timeout 2 https://example.com" in snippet
        assert "/workspace/arc-sentinel.txt" in snippet
        assert "/workspace/arc-host-escape-link" in snippet

    def test_proof_artifact_generator_writes_init_and_manifest_only_by_default(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.delenv("ARC_FC_BUILD_PROOF_ROOTFS", raising=False)
        report = generate_firecracker_proof_artifacts(tmp_path)
        assert report.built_rootfs is False
        assert "ARC_FC_BUILD_PROOF_ROOTFS=1 not set" in "; ".join(report.blockers)
        init_text = (tmp_path / "arc-fc-proof-init.sh").read_text(encoding="utf-8")
        assert "ARC_FC_PROOF no_default_route=1" in init_text
        manifest = validate_firecracker_proof_manifest(tmp_path / "rootfs-manifest.json")
        assert manifest.build_status == "init_manifest_only"
        assert manifest.rootfs_path is None

    def test_proof_artifact_builder_reports_missing_tools_gracefully(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARC_FC_BUILD_PROOF_ROOTFS", "1")
        monkeypatch.setattr("agent_runtime_cockpit.isolation.microvm.shutil.which", lambda _: None)
        report = generate_firecracker_proof_artifacts(tmp_path)
        assert report.built_rootfs is False
        assert "missing tool: busybox" in report.blockers
        assert "missing tool: mkfs.ext4" in report.blockers
        assert "missing tool: truncate" in report.blockers

    def test_proof_manifest_gate_rejects_invalid_manifest(self, tmp_path, monkeypatch):
        manifest = tmp_path / "rootfs-manifest.json"
        manifest.write_text('{"version":1}', encoding="utf-8")
        monkeypatch.setenv("ARC_FIRECRACKER_PROOF_ROOTFS_MANIFEST", str(manifest))
        gates = firecracker_proof_gates()
        assert gates["proof_manifest_valid"] is False
        assert any("ARC_FIRECRACKER_PROOF_ROOTFS_MANIFEST invalid" in b for b in gates["blockers"])

    def test_proof_runner_consumes_guest_markers_without_public_exec(self, tmp_path, monkeypatch):
        kernel = tmp_path / "vmlinux"
        rootfs = tmp_path / "rootfs.ext4"
        kernel.write_text("kernel", encoding="utf-8")
        rootfs.write_text("rootfs", encoding="utf-8")
        monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
        monkeypatch.setenv("ARC_FC_REAL_EXEC", "1")
        monkeypatch.setenv("ARC_FIRECRACKER_KERNEL", str(kernel))
        monkeypatch.setenv("ARC_FIRECRACKER_ROOTFS", str(rootfs))
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.platform.system", lambda: "Linux"
        )
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm._firecracker_binary",
            lambda: "/usr/bin/firecracker",
        )
        original_exists = __import__("pathlib", fromlist=["Path"]).Path.exists
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.Path.exists",
            lambda self: True if str(self) == "/dev/kvm" else original_exists(self),
        )
        monkeypatch.setattr("agent_runtime_cockpit.isolation.microvm.os.access", lambda *_: True)

        def fake_run(argv, *, timeout_seconds, max_bytes):
            assert "--config-file" in argv
            return (
                __import__(
                    "agent_runtime_cockpit.isolation.base", fromlist=["IsolationResult"]
                ).IsolationResult(
                    exit_code=0,
                    stdout=(
                        "ARC_FC_PROOF no_default_route=1\n"
                        "ARC_FC_PROOF curl_failed=1\n"
                        "ARC_FC_PROOF sentinel_readable=1\n"
                        "ARC_FC_PROOF symlink_escape_blocked=1\n"
                    ),
                    provider="microvm",
                ),
                None,
            )

        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm._run_firecracker_process", fake_run
        )
        runner = FirecrackerProofRunner(workspace_root=tmp_path, instance_name="arc-fc-proof")
        result = runner.run(["ip", "route"])
        assert "guest_proof" in result.lifecycle
        assert result.network_proof_passed is True
        assert result.workspace_sentinel_readable is True
        assert result.symlink_escape_blocked is True
        assert result.proof_blocker is None
        assert result.public_execution_enabled is False


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
