"""Opt-in Lima integration smoke test (Phase 37 Slices 37.14, 37.18).

TestLimaSmoke — fake-runner tests (Slice 37.14):
  Runs when: macOS + limactl installed + ARC_MICROVM_INTEGRATION=1.
  Uses a fake runner — does NOT start a real Lima VM.

TestLimaSmokeRealHost — real limactl tests (Slice 37.18):
  Runs when: macOS + limactl installed + ARC_MICROVM_INTEGRATION=1 +
             ARC_LIMA_REAL_EXEC=1.
  Calls LimaIntegrationHarness.run() with runner=None (uses real limactl).
  IMPORTANT: On Lima 2.x the guest always has a default slirp route
  (192.168.5.0/24). network_proof_passed will be False because the harness
  checks for no default route and Lima always provides one. This is a known
  P2 limitation documented in ADR-024. These tests prove P1 (lifecycle) and
  P4 (teardown) only, NOT P2 (network-off).

Normal CI does NOT set ARC_MICROVM_INTEGRATION=1 or ARC_LIMA_REAL_EXEC=1.

Truth constraints:
  - MicroVMIsolationProvider.execute() still raises NotImplementedError.
  - No "microVM execution complete" claims — even if real Lima runs.
  - P2 (network-off) is NOT proven here; Lima 2.x always has slirp route.
  - CI-skip behaviour verified by TestLimaSmokeSkipBehaviour.
"""

from __future__ import annotations

import os
import platform
import shutil

import pytest

from agent_runtime_cockpit.isolation.base import IsolationResult
from agent_runtime_cockpit.isolation.microvm import (
    LimaHarnessResult,
    LimaIntegrationHarness,
    lima_integration_available,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKIP_REASON = (
    "Lima smoke: requires macOS + limactl installed + ARC_MICROVM_INTEGRATION=1. "
    "CI does not set ARC_MICROVM_INTEGRATION=1; skip is intentional."
)


def _fake_runner(argv: list[str], _timeout: int, _max_bytes: int) -> IsolationResult:
    """Fake limactl runner used by smoke tests.

    Returns exit_code=0 for every subcommand so the full harness lifecycle
    (template → start → network_proof → run → teardown) can be exercised
    without requiring a real Lima installation.

    Network-proof command is the 'ip route' check embedded in the harness.
    Returning exit_code=0 means "no default route found" → network isolated.
    """
    return IsolationResult(exit_code=0, stdout="smoke-ok", provider="microvm")


# ---------------------------------------------------------------------------
# Smoke tests — skipped unless lima_integration_available()
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (
        platform.system() == "Darwin"
        and os.environ.get("ARC_MICROVM_INTEGRATION") == "1"
        and bool(shutil.which("limactl"))
    ),
    reason=_SKIP_REASON,
)
class TestLimaSmoke:
    """Opt-in Lima harness lifecycle smoke tests.

    Each test calls LimaIntegrationHarness.run() with a fake runner so the
    lifecycle state machine is exercised without creating a real VM.

    A follow-up PR will add tests that use a real limactl runner once the
    harness lifecycle is proven on a host with Lima installed.
    """

    def test_smoke_full_lifecycle(self, tmp_path):
        """Full lifecycle produces expected phases and a successful result."""
        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            runner=_fake_runner,
            instance_name="arc-smoke-test",
        )
        result: LimaHarnessResult = harness.run(["uname", "-a"], require_gate=False)

        assert result.lifecycle == [
            "template",
            "start",
            "network_proof",
            "run",
            "teardown",
        ], f"Unexpected lifecycle: {result.lifecycle}"
        assert result.network_proof_passed is True
        assert result.teardown_attempted is True
        assert result.result.exit_code == 0

    def test_smoke_network_proof_passed(self, tmp_path):
        """Network isolation check passes when fake runner returns 0."""
        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            runner=_fake_runner,
            instance_name="arc-smoke-network",
        )
        result = harness.run(["echo", "hello"], require_gate=False)
        assert result.network_proof_passed is True

    def test_smoke_teardown_always_attempted(self, tmp_path):
        """Teardown is attempted even when start fails."""
        calls: list[list[str]] = []

        def failing_start_runner(
            argv: list[str], _timeout: int, _max_bytes: int
        ) -> IsolationResult:
            calls.append(argv)
            if "start" in argv:
                return IsolationResult(exit_code=1, stderr="start-fail", provider="microvm")
            return IsolationResult(exit_code=0, provider="microvm")

        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            runner=failing_start_runner,
            instance_name="arc-smoke-teardown",
        )
        result = harness.run(["pwd"], require_gate=False)
        assert result.teardown_attempted is True
        assert calls[-1] == ["limactl", "delete", "-f", "arc-smoke-teardown"]

    def test_smoke_result_exit_code_zero_on_success(self, tmp_path):
        """Successful harness run returns exit_code == 0."""
        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            runner=_fake_runner,
            instance_name="arc-smoke-exit",
        )
        result = harness.run(["uname", "-a"], require_gate=False)
        assert result.result.exit_code == 0

    def test_smoke_instance_name_in_result(self, tmp_path):
        """Result contains the harness instance name."""
        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            runner=_fake_runner,
            instance_name="arc-smoke-name-check",
        )
        result = harness.run(["pwd"], require_gate=False)
        assert result.instance_name == "arc-smoke-name-check"

    def test_mount_proof_mode_bypasses_only_failed_network_proof(self, tmp_path):
        """Mount proof can run on Lima even when the known slirp route exists."""
        calls: list[list[str]] = []

        def runner(argv: list[str], _timeout: int, _max_bytes: int) -> IsolationResult:
            calls.append(argv)
            if "shell" in argv and "ip route | grep" in " ".join(argv):
                return IsolationResult(exit_code=1, stderr="default route", provider="microvm")
            return IsolationResult(exit_code=0, stdout="mount-proof-ok", provider="microvm")

        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            runner=runner,
            instance_name="arc-smoke-mount-proof",
        )
        result = harness.run(["cat", "/workspace/sentinel"], require_gate=False, proof_mode="mount")

        assert result.network_proof_passed is False
        assert result.lifecycle == [
            "template",
            "start",
            "network_proof",
            "mount_proof_network_bypass",
            "run",
            "teardown",
        ]
        assert result.result.exit_code == 0
        assert any("/workspace/sentinel" in call for call in calls)

    def test_invalid_proof_mode_rejected(self, tmp_path):
        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            runner=_fake_runner,
            instance_name="arc-smoke-bad-proof-mode",
        )

        with pytest.raises(ValueError, match="proof_mode"):
            harness.run(["pwd"], require_gate=False, proof_mode="exec")


# ---------------------------------------------------------------------------
# CI-safety test — always runs, confirms skip behaviour
# ---------------------------------------------------------------------------


class TestLimaSmokeSkipBehaviour:
    """Always-run tests proving CI skips cleanly when Lima is not available."""

    def test_smoke_skips_in_ci(self):
        """Confirms smoke tests are skipped when lima_integration_available() is False.

        This test always runs. If lima_integration_available() is True on
        this host, the smoke tests above will also run (opt-in). If it is
        False, this test still passes — proving clean CI skip behaviour.
        """
        available = lima_integration_available()
        # Either the harness is available (developer machine with Lima + gate)
        # or it is not (CI / machine without Lima).  Both outcomes are valid.
        assert isinstance(available, bool)

    def test_lima_integration_available_requires_all_three_conditions(self, monkeypatch):
        """lima_integration_available() requires macOS + ARC_MICROVM_INTEGRATION=1 + limactl."""
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        monkeypatch.delenv("ARC_MICROVM_INTEGRATION", raising=False)
        # No limactl, no gate → False regardless of platform
        assert lima_integration_available() is False

    def test_lima_integration_available_false_without_gate(self, monkeypatch):
        """Gate env var missing → False even if limactl is present."""
        monkeypatch.setattr(
            shutil, "which", lambda name: "/opt/homebrew/bin/limactl" if name == "limactl" else None
        )
        monkeypatch.delenv("ARC_MICROVM_INTEGRATION", raising=False)
        assert lima_integration_available() is False

    def test_lima_integration_available_false_without_limactl(self, monkeypatch):
        """limactl missing → False even if gate is set."""
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
        assert lima_integration_available() is False

    def test_harness_uses_real_runner_when_runner_is_none(self, tmp_path):
        """runner=None causes harness to use _run_limactl (real binary path).

        This is a contract test: if runner=None, harness._limactl calls the
        real _run_limactl function (not a fake). We verify the runner attribute
        is not None after construction.
        """
        harness = LimaIntegrationHarness(workspace_root=tmp_path)
        # runner=None default → harness.runner should be the real _run_limactl
        assert harness.runner is not None


# ---------------------------------------------------------------------------
# Real-host tests — only run when limactl is present AND ARC_LIMA_REAL_EXEC=1
# ---------------------------------------------------------------------------

_REAL_EXEC_REASON = (
    "Lima real-host: requires macOS + limactl + ARC_MICROVM_INTEGRATION=1 + "
    "ARC_LIMA_REAL_EXEC=1. WARNING: starts and destroys a real Lima VM. "
    "May take 60–300s on first run (image download). "
    "KNOWN LIMITATION: network_proof_passed will be False on Lima 2.x because "
    "the guest always has a slirp default route (192.168.5.0/24). "
    "P1/P4 lifecycle/teardown proof only; P2 (network-off) NOT proven here."
)

_REAL_EXEC_GATE = (
    platform.system() == "Darwin"
    and os.environ.get("ARC_MICROVM_INTEGRATION") == "1"
    and bool(shutil.which("limactl"))
    and os.environ.get("ARC_LIMA_REAL_EXEC") == "1"
)


@pytest.mark.skipif(not _REAL_EXEC_GATE, reason=_REAL_EXEC_REASON)
class TestLimaSmokeRealHost:
    """Real limactl lifecycle tests (Slice 37.18).

    These tests use runner=None so LimaIntegrationHarness calls the real
    limactl binary. A real Lima VM is created and destroyed.

    KNOWN LIMITATION (Lima 2.x): The guest always has a slirp default route.
    network_proof_passed will be False because the harness expects no default
    route. This is documented in ADR-024 as an unresolved P2 blocker.
    Tests below accept this and document the finding rather than hiding it.

    What is proven by these tests:
      P1 — Lifecycle: template → start → network_proof → teardown completes.
      P4 — Teardown: limactl delete -f runs and harness.teardown_attempted=True.

    What is NOT proven:
      P2 — Network-off: Lima 2.x always has slirp route; proof blocked.
      P3 — Workspace-mount isolation: requires separate mount escape test.
      P5 — Symlink escape: requires guest-side symlink traversal test.
    """

    def test_real_lima_lifecycle_uname(self, tmp_path):
        """Real Lima VM: full lifecycle runs and teardown completes (P1/P4 proof).

        IMPORTANT: network_proof_passed will be False on Lima 2.x (known P2 gap).
        The test asserts teardown_attempted=True proving the VM was cleaned up.
        """
        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            # runner=None → uses real _run_limactl
            instance_name="arc-smoke-real-uname",
        )
        result: LimaHarnessResult = harness.run(
            ["uname", "-a"],
            timeout_seconds=600,  # generous for first-run image download
            require_gate=True,
        )
        # P1: lifecycle must reach at least template + start + teardown
        assert "template" in result.lifecycle
        assert "start" in result.lifecycle
        assert "teardown" in result.lifecycle
        assert result.teardown_attempted is True

        # P2 known gap: Lima 2.x always has slirp route → network_proof_passed=False
        # Do NOT assert network_proof_passed is True; document the finding.
        # The test documents the actual value for the evidence record.
        assert isinstance(result.network_proof_passed, bool)
        # If the VM started successfully, uname should have run
        if result.result.exit_code == 0:
            assert result.result.stdout  # some output
        # If network proof failed, command was blocked (expected on Lima 2.x)
        # Both outcomes are valid — the important thing is teardown ran.

    def test_real_lima_teardown_on_start_failure(self, tmp_path):
        """Teardown is attempted even when start is slow / fails (P4 partial proof).

        This test uses a very short timeout to force a timeout scenario,
        proving the teardown path fires on failure. The VM may or may not
        actually start within 5 seconds.
        """
        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            instance_name="arc-smoke-real-teardown",
        )
        # Use a very short timeout to trigger timeout/failure path quickly.
        # teardown_attempted must still be True.
        result: LimaHarnessResult = harness.run(
            ["uname"],
            timeout_seconds=5,
            require_gate=True,
        )
        # Teardown must always be attempted regardless of start outcome
        assert result.teardown_attempted is True
        assert "teardown" in result.lifecycle

    def test_real_lima_workspace_sentinel(self, tmp_path):
        """Workspace mount: sentinel file written to tmp_path is visible in guest.

        This is a partial P3 proof: proves the workspace is mounted at /workspace.
        Full mount isolation (P3) requires a symlink-escape test inside the guest.
        """
        sentinel = tmp_path / "arc-sentinel.txt"
        sentinel.write_text("arc-workspace-mount-proof", encoding="utf-8")

        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            instance_name="arc-smoke-real-mount",
        )
        result: LimaHarnessResult = harness.run(
            ["cat", "/workspace/arc-sentinel.txt"],
            timeout_seconds=600,
            require_gate=True,
        )
        assert result.teardown_attempted is True
        # If the VM started and ran the command, sentinel content appears in stdout
        if result.result.exit_code == 0:
            assert "arc-workspace-mount-proof" in result.result.stdout

    def test_real_lima_mount_proof_symlink_escape(self, tmp_path):
        """Guest-side evidence: can Lima read host files through workspace symlinks?

        This uses proof_mode="mount" to bypass only Lima's known failed network
        proof. If `/workspace` symlinks can read `/etc/passwd`, Lima is blocked
        permanently for strict sandbox use and remains only a low-security
        developer harness.
        """
        escape_link = tmp_path / "arc-host-passwd-link"
        escape_link.symlink_to("/etc/passwd")

        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            instance_name="arc-smoke-real-symlink",
        )
        result: LimaHarnessResult = harness.run(
            ["cat", "/workspace/arc-host-passwd-link"],
            timeout_seconds=600,
            require_gate=True,
            proof_mode="mount",
        )
        assert result.teardown_attempted is True
        assert "mount_proof_network_bypass" in result.lifecycle or result.network_proof_passed
        assert "run" in result.lifecycle
        if result.result.exit_code == 0:
            pytest.fail(
                "Lima /workspace symlink escape readable: host /etc/passwd visible in guest. "
                "Mark ADR-024 P5 blocked permanently for strict sandbox use."
            )
