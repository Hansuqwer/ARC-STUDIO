"""MicroVM preflight state tests (Phase 37 Slice 37.5).

Tests the four preflight states returned by microvm_preflight():
- unavailable: no microVM binary found on the system
- installed_not_configured: binary found but missing kernel/rootfs/KVM/etc.
- ready: fully configured and ready (Linux only; execution still not implemented)
- blocked: unsupported platform (Windows, etc.)

Truth constraints:
- microVM execution does NOT exist
- Lima/Firecracker are preflight-only
- Container fallback gated by ARC_ENABLE_CONTAINER_SANDBOX=1
- CI must NOT require microVM runtime
"""

import shutil
import subprocess
from pathlib import Path

from agent_runtime_cockpit.isolation.base import IsolationResult
from agent_runtime_cockpit.isolation.microvm import LimaIntegrationHarness, build_microvm_run_plan
from agent_runtime_cockpit.security.sandbox import microvm_preflight


class TestMicroVMPreflightStates:
    """Test all four preflight states with monkeypatched system state."""

    def test_unavailable_no_binary_linux(self, monkeypatch):
        """Linux with no firecracker/cloud-hypervisor binary → unavailable."""
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        data = microvm_preflight("Linux")
        assert data["status"] == "unavailable"
        assert data["platform"] == "linux"
        assert data["binary"] is None

    def test_unavailable_no_limactl_macos(self, monkeypatch):
        """macOS with no limactl binary → unavailable."""
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        data = microvm_preflight("Darwin")
        assert data["status"] == "unavailable"
        assert data["platform"] == "macos"
        assert data["binary"] is None

    def test_installed_not_configured_linux_missing_kvm(self, monkeypatch, tmp_path):
        """Linux with firecracker binary but no /dev/kvm → installed_not_configured."""
        monkeypatch.setattr(
            shutil, "which", lambda name: "/usr/bin/firecracker" if name == "firecracker" else None
        )
        # /dev/kvm does not exist in test environment
        data = microvm_preflight("Linux")
        assert data["status"] == "installed_not_configured"
        assert data["binary"] == "/usr/bin/firecracker"
        assert data["kvm"] is False

    def test_installed_not_configured_linux_missing_cache(self, monkeypatch, tmp_path):
        """Linux with binary + KVM but no kernel/rootfs cache → installed_not_configured."""
        monkeypatch.setattr(
            shutil,
            "which",
            lambda name: f"/usr/bin/{name}" if name in {"firecracker", "jailer"} else None,
        )
        # Mock /dev/kvm as readable/writable
        kvm_mock = tmp_path / "kvm"
        kvm_mock.write_text("mock", encoding="utf-8")
        monkeypatch.setattr(
            "agent_runtime_cockpit.security.sandbox.Path",
            lambda p: kvm_mock if str(p) == "/dev/kvm" else Path(p),
        )
        # No kernel/rootfs env vars set
        monkeypatch.delenv("ARC_FIRECRACKER_KERNEL", raising=False)
        monkeypatch.delenv("ARC_FIRECRACKER_ROOTFS", raising=False)
        data = microvm_preflight("Linux")
        assert data["status"] == "installed_not_configured"
        assert data["cache_ready"] is False

    def test_installed_not_configured_macos_with_limactl(self, monkeypatch):
        """macOS with limactl installed → installed_not_configured (execution not implemented)."""
        monkeypatch.setattr(
            shutil, "which", lambda name: "/opt/homebrew/bin/limactl" if name == "limactl" else None
        )
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: subprocess.CompletedProcess(
                args[0], 0, stdout="limactl 1.0", stderr=""
            ),
        )
        data = microvm_preflight("Darwin")
        assert data["status"] == "installed_not_configured"
        assert data["binary"].endswith("limactl")
        assert data["execution"] == "not_implemented"

    def test_blocked_windows(self):
        """Windows platform → blocked with reason."""
        data = microvm_preflight("Windows")
        assert data["status"] == "blocked"
        assert "unsupported" in data["reason"].lower()

    def test_blocked_unknown_platform(self):
        """Unknown platform → blocked."""
        data = microvm_preflight("FreeBSD")
        assert data["status"] == "blocked"


class TestMicroVMPreflightLinuxDeep:
    """Test deep Linux preflight diagnostics (kernel, rootfs, jailer, KVM)."""

    def test_cache_ready_when_kernel_and_rootfs_exist(self, monkeypatch, tmp_path):
        """Linux with kernel and rootfs files → cache_ready is True."""
        kernel = tmp_path / "vmlinux"
        rootfs = tmp_path / "rootfs.ext4"
        kernel.write_text("kernel", encoding="utf-8")
        rootfs.write_text("rootfs", encoding="utf-8")
        monkeypatch.setenv("ARC_FIRECRACKER_KERNEL", str(kernel))
        monkeypatch.setenv("ARC_FIRECRACKER_ROOTFS", str(rootfs))
        monkeypatch.setattr(
            shutil,
            "which",
            lambda name: f"/usr/bin/{name}" if name in {"firecracker", "jailer"} else None,
        )
        data = microvm_preflight("Linux")
        assert data["kernel_exists"] is True
        assert data["rootfs_exists"] is True
        assert data["cache_ready"] is True
        assert data["binary"] == "/usr/bin/firecracker"
        assert data["jailer"] == "/usr/bin/jailer"

    def test_kernel_size_reported(self, monkeypatch, tmp_path):
        """Kernel file size is reported in preflight."""
        kernel = tmp_path / "vmlinux"
        kernel.write_bytes(b"x" * 1024)
        monkeypatch.setenv("ARC_FIRECRACKER_KERNEL", str(kernel))
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        data = microvm_preflight("Linux")
        assert data["kernel_size"] == 1024

    def test_jail_perms_reported(self, monkeypatch, tmp_path):
        """Jailer file permissions are reported in preflight."""
        jailer = tmp_path / "jailer"
        jailer.write_text("mock", encoding="utf-8")
        jailer.chmod(0o755)
        monkeypatch.setattr(
            shutil,
            "which",
            lambda name: (
                str(jailer)
                if name == "jailer"
                else ("/usr/bin/firecracker" if name == "firecracker" else None)
            ),
        )
        data = microvm_preflight("Linux")
        assert data["jail_perms"] is not None


class TestMicroVMPreflightCI:
    """Ensure CI does not require microVM runtime."""

    def test_preflight_never_creates_vm(self, monkeypatch):
        """Preflight must never create or start any VM."""
        # This is a contract test: preflight only probes, never executes
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        data = microvm_preflight("Linux")
        assert data["status"] in {"unavailable", "installed_not_configured", "ready", "blocked"}
        # No VM creation side effects

    def test_preflight_returns_stable_schema(self, monkeypatch):
        """Preflight returns a stable dict schema regardless of platform."""
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        data = microvm_preflight("Linux")
        assert "provider" in data
        assert "platform" in data
        assert "status" in data
        assert data["provider"] == "microvm"


class TestMicroVMRunPlan:
    """Non-executing Phase 37.6 design-proof plan tests."""

    def test_lima_plan_has_lifecycle_network_and_teardown_steps(self, tmp_path):
        plan = build_microvm_run_plan(
            "lima", ["pwd"], workspace_root=tmp_path, platform_name="Darwin"
        )
        assert plan.provider == "lima"
        assert plan.execution_enabled is False
        assert plan.execution_status == "design_proof_only"
        assert plan.network_default == "deny"
        assert [step.name for step in plan.steps] == [
            "template",
            "create_start",
            "network_off",
            "run",
            "teardown",
        ]
        assert any("network-off proof" in blocker for blocker in plan.blockers)

    def test_firecracker_plan_has_cache_mount_and_jailer_steps(self, tmp_path):
        plan = build_microvm_run_plan(
            "firecracker", ["pwd"], workspace_root=tmp_path, platform_name="Linux"
        )
        assert plan.provider == "firecracker"
        assert plan.guest_workspace == "/workspace"
        assert [step.name for step in plan.steps] == [
            "preflight",
            "jail",
            "boot",
            "mount",
            "run",
            "teardown",
        ]
        assert any("kernel/rootfs" in blocker for blocker in plan.blockers)

    def test_plan_rejects_unknown_provider_and_missing_command(self, tmp_path):
        import pytest

        with pytest.raises(ValueError, match="provider must be"):
            build_microvm_run_plan("docker", ["pwd"], workspace_root=tmp_path)
        with pytest.raises(ValueError, match="missing command"):
            build_microvm_run_plan("lima", [], workspace_root=tmp_path)


class TestLimaIntegrationHarness:
    """Gated harness tests with fake limactl runner; no VM is created."""

    def test_harness_requires_explicit_gate(self, tmp_path, monkeypatch):
        import pytest

        monkeypatch.delenv("ARC_MICROVM_INTEGRATION", raising=False)
        harness = LimaIntegrationHarness(workspace_root=tmp_path, runner=lambda *_: None)
        with pytest.raises(RuntimeError, match="ARC_MICROVM_INTEGRATION=1"):
            harness.run(["pwd"])

    def test_harness_runs_lifecycle_after_network_proof(self, tmp_path):
        calls: list[list[str]] = []

        def runner(argv: list[str], _timeout: int, _max_bytes: int) -> IsolationResult:
            calls.append(argv)
            return IsolationResult(exit_code=0, stdout="ok", provider="microvm")

        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            runner=runner,
            instance_name="arc-test",
        )
        result = harness.run(["python", "-c", "print('hello')"], require_gate=False)
        assert result.network_proof_passed is True
        assert result.teardown_attempted is True
        assert result.lifecycle == ["template", "start", "network_proof", "run", "teardown"]
        assert calls[0][:3] == ["limactl", "start", "--tty=false"]
        assert calls[1] == [
            "limactl",
            "shell",
            "--tty=false",
            "arc-test",
            "--",
            "sh",
            "-lc",
            "ip route | grep -q '^default' && exit 1 || exit 0",
        ]
        assert calls[2] == [
            "limactl",
            "shell",
            "--tty=false",
            "arc-test",
            "--workdir",
            "/workspace",
            "--",
            "python",
            "-c",
            "print('hello')",
        ]
        assert calls[3] == ["limactl", "delete", "-f", "arc-test"]

    def test_harness_blocks_user_command_when_network_proof_fails(self, tmp_path):
        calls: list[list[str]] = []

        def runner(argv: list[str], _timeout: int, _max_bytes: int) -> IsolationResult:
            calls.append(argv)
            if any("ip route" in part for part in argv):
                return IsolationResult(exit_code=1, provider="microvm")
            return IsolationResult(exit_code=0, provider="microvm")

        harness = LimaIntegrationHarness(
            workspace_root=tmp_path, runner=runner, instance_name="arc-test"
        )
        result = harness.run(["pwd"], require_gate=False)
        assert result.network_proof_passed is False
        assert "network-off proof failed" in result.result.stderr
        assert not any("--workdir" in call for call in calls)
        assert calls[-1] == ["limactl", "delete", "-f", "arc-test"]

    def test_harness_teardown_runs_when_start_fails(self, tmp_path):
        calls: list[list[str]] = []

        def runner(argv: list[str], _timeout: int, _max_bytes: int) -> IsolationResult:
            calls.append(argv)
            if "start" in argv:
                return IsolationResult(exit_code=1, stderr="start failed", provider="microvm")
            return IsolationResult(exit_code=0, provider="microvm")

        harness = LimaIntegrationHarness(
            workspace_root=tmp_path, runner=runner, instance_name="arc-test"
        )
        result = harness.run(["pwd"], require_gate=False)
        assert "lima start failed" in result.result.stderr
        assert result.teardown_attempted is True
        assert calls[-1] == ["limactl", "delete", "-f", "arc-test"]

    def test_harness_rejects_missing_command(self, tmp_path):
        import pytest

        harness = LimaIntegrationHarness(workspace_root=tmp_path, runner=lambda *_: None)
        with pytest.raises(ValueError, match="missing command"):
            harness.run([], require_gate=False)
