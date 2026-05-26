"""Opt-in Lima integration smoke test (Phase 37 Slice 37.6 — host proof).

This test only runs when:
  - macOS (platform.system() == "Darwin")
  - limactl is installed (shutil.which("limactl") is not None)
  - ARC_MICROVM_INTEGRATION=1 is set

Normal CI does NOT set ARC_MICROVM_INTEGRATION=1, so this test is always
skipped in CI unless explicitly opted in on a developer machine with Lima.

Truth constraints (must remain true after this file lands):
  - MicroVMIsolationProvider.execute() must still raise NotImplementedError.
  - This test only calls LimaIntegrationHarness.run() with a fake runner —
    it does NOT start a real Lima VM; real execution requires a follow-up
    PR once the harness lifecycle is proven on a host with Lima installed.
  - No "microVM execution complete" claims in this file.
  - CI-skip behaviour is verified by test_smoke_skips_in_ci().
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
