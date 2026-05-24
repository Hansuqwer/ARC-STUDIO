"""Tests for enforcement context and dry-run mode (Phase 23.1)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from agent_runtime_cockpit.security.context import (
    DryRunAbort,
    EnforcementContext,
    get_enforcement_context,
    set_enforcement_context,
)
from agent_runtime_cockpit.security.enforcement import (
    PaidCallEnforcementError,
    TrustEnforcementError,
    enforce_network_gate,
    enforce_paid_call_gate,
    enforce_shell_gate,
    enforce_workspace_trust,
)
from agent_runtime_cockpit.security.profiles import BackendMode, RunProfile


class TestEnforcementContext:
    """Test EnforcementContext dataclass."""

    def test_context_default_values(self):
        """EnforcementContext has correct default values."""
        ctx = EnforcementContext()
        assert ctx.allow_paid is False
        assert ctx.trust_workspace is False
        assert ctx.dry_run is False

    def test_context_with_values(self):
        """EnforcementContext can be created with custom values."""
        ctx = EnforcementContext(
            allow_paid=True,
            trust_workspace=True,
            dry_run=False,
        )
        assert ctx.allow_paid is True
        assert ctx.trust_workspace is True
        assert ctx.dry_run is False

    def test_context_copy_with(self):
        """EnforcementContext.copy_with() creates modified copy."""
        ctx = EnforcementContext(allow_paid=True, trust_workspace=False, dry_run=False)

        # Copy with updated dry_run
        ctx2 = ctx.copy_with(dry_run=True)
        assert ctx2.allow_paid is True  # Preserved
        assert ctx2.trust_workspace is False  # Preserved
        assert ctx2.dry_run is True  # Updated

        # Original unchanged
        assert ctx.dry_run is False

    def test_context_immutable(self):
        """EnforcementContext is immutable (frozen dataclass)."""
        ctx = EnforcementContext()
        with pytest.raises(AttributeError):
            ctx.allow_paid = True  # type: ignore


class TestContextVariableManagement:
    """Test context variable get/set functions."""

    def test_get_default_context(self):
        """get_enforcement_context() returns default context initially."""
        ctx = get_enforcement_context()
        assert ctx.allow_paid is False
        assert ctx.trust_workspace is False
        assert ctx.dry_run is False

    def test_set_and_get_context(self):
        """set_enforcement_context() updates the global context."""
        custom_ctx = EnforcementContext(allow_paid=True, dry_run=True)
        set_enforcement_context(custom_ctx)

        retrieved_ctx = get_enforcement_context()
        assert retrieved_ctx.allow_paid is True
        assert retrieved_ctx.trust_workspace is False
        assert retrieved_ctx.dry_run is True

        # Reset to default for other tests
        set_enforcement_context(EnforcementContext())


class TestDryRunMode:
    """Test dry-run mode with all enforcement helpers."""

    def test_dry_run_trust_enforcement_raises_abort(self, tmp_path: Path):
        """Dry-run mode raises DryRunAbort for trust enforcement."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust.json"

        ctx = EnforcementContext(dry_run=True)
        emit_event = Mock()

        with pytest.raises(DryRunAbort) as exc_info:
            enforce_workspace_trust(
                workspace=workspace,
                action="run_execution",
                run_id="run-001",
                sequence=0,
                emit_event=emit_event,
                trust_db=trust_db,
                ctx=ctx,
            )

        # Verify DryRunAbort has denial_event
        assert exc_info.value.denial_event is not None
        assert exc_info.value.denial_event["type"] == "TRUST_DENIED"
        assert exc_info.value.denial_event["data"]["reason"] == "dry_run"

        # Verify event was emitted
        emit_event.assert_called_once()
        event_data = emit_event.call_args[0][2]
        assert event_data["type"] == "TRUST_DENIED"

    def test_dry_run_paid_call_enforcement_raises_abort(self):
        """Dry-run mode raises DryRunAbort for paid-call enforcement."""
        profile = RunProfile(
            id="local-paid",
            name="Local Paid",
            allow_paid_calls=True,
            backend=BackendMode.LOCAL,
        )

        ctx = EnforcementContext(dry_run=True)
        emit_event = Mock()

        with pytest.raises(DryRunAbort) as exc_info:
            enforce_paid_call_gate(
                profile=profile,
                action="provider_call",
                run_id="run-002",
                sequence=1,
                emit_event=emit_event,
                ctx=ctx,
            )

        assert exc_info.value.denial_event["type"] == "PAID_CALL_DENIED"
        assert exc_info.value.denial_event["data"]["reason"] == "dry_run"

    def test_dry_run_shell_enforcement_raises_abort(self):
        """Dry-run mode raises DryRunAbort for shell enforcement."""
        profile = RunProfile(
            id="gateway",
            name="Gateway",
            allow_shell=True,
            backend=BackendMode.GATEWAY,
        )

        ctx = EnforcementContext(dry_run=True)
        emit_event = Mock()

        with pytest.raises(DryRunAbort) as exc_info:
            enforce_shell_gate(
                profile=profile,
                action="shell_command",
                run_id="run-003",
                sequence=2,
                emit_event=emit_event,
                command="ls -la",
                ctx=ctx,
            )

        assert exc_info.value.denial_event["type"] == "SHELL_DENIED"
        assert exc_info.value.denial_event["data"]["reason"] == "dry_run"

    def test_dry_run_network_enforcement_raises_abort(self):
        """Dry-run mode raises DryRunAbort for network enforcement."""
        profile = RunProfile(
            id="local-safe",
            name="Local Safe",
            allow_network=True,
            backend=BackendMode.STUB,
        )

        ctx = EnforcementContext(dry_run=True)
        emit_event = Mock()

        with pytest.raises(DryRunAbort) as exc_info:
            enforce_network_gate(
                profile=profile,
                action="http_request",
                run_id="run-004",
                sequence=3,
                emit_event=emit_event,
                url="https://example.com",
                ctx=ctx,
            )

        assert exc_info.value.denial_event["type"] == "NETWORK_DENIED"
        assert exc_info.value.denial_event["data"]["reason"] == "dry_run"


class TestBypassFlags:
    """Test bypass flags (allow_paid, trust_workspace)."""

    def test_trust_workspace_flag_bypasses_gate(self, tmp_path: Path):
        """trust_workspace flag bypasses trust enforcement."""
        workspace = tmp_path / "untrusted-workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust.json"

        # Without flag, should raise
        with pytest.raises(TrustEnforcementError):
            enforce_workspace_trust(
                workspace=workspace,
                action="run_execution",
                run_id="run-001",
                sequence=0,
                trust_db=trust_db,
            )

        # With flag, should pass
        ctx = EnforcementContext(trust_workspace=True)
        enforce_workspace_trust(
            workspace=workspace,
            action="run_execution",
            run_id="run-001",
            sequence=0,
            trust_db=trust_db,
            ctx=ctx,
        )  # Should not raise

    def test_allow_paid_flag_bypasses_gate(self):
        """allow_paid flag bypasses paid-call enforcement."""
        profile = RunProfile(
            id="stub",
            name="Stub",
            allow_paid_calls=False,
            backend=BackendMode.STUB,
        )

        # Without flag, should raise
        with pytest.raises(PaidCallEnforcementError):
            enforce_paid_call_gate(
                profile=profile,
                action="provider_call",
                run_id="run-002",
                sequence=1,
            )

        # With flag, should pass
        ctx = EnforcementContext(allow_paid=True)
        enforce_paid_call_gate(
            profile=profile,
            action="provider_call",
            run_id="run-002",
            sequence=1,
            ctx=ctx,
        )  # Should not raise


class TestDryRunCannotBeBypassed:
    """Test that dry-run mode cannot be bypassed by other flags."""

    def test_dry_run_blocks_despite_trust_workspace(self, tmp_path: Path):
        """Dry-run blocks even with trust_workspace=True."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust.json"

        # Both flags set, but dry-run should win
        ctx = EnforcementContext(dry_run=True, trust_workspace=True)

        with pytest.raises(DryRunAbort):
            enforce_workspace_trust(
                workspace=workspace,
                action="run_execution",
                run_id="run-001",
                sequence=0,
                trust_db=trust_db,
                ctx=ctx,
            )

    def test_dry_run_blocks_despite_allow_paid(self):
        """Dry-run blocks even with allow_paid=True."""
        profile = RunProfile(
            id="local-paid",
            name="Local Paid",
            allow_paid_calls=True,
            backend=BackendMode.LOCAL,
        )

        # Both flags set, but dry-run should win
        ctx = EnforcementContext(dry_run=True, allow_paid=True)

        with pytest.raises(DryRunAbort):
            enforce_paid_call_gate(
                profile=profile,
                action="provider_call",
                run_id="run-002",
                sequence=1,
                ctx=ctx,
            )

    def test_dry_run_blocks_despite_profile_permissions(self):
        """Dry-run blocks even when profile allows the operation."""
        # Profile allows shell execution
        profile = RunProfile(
            id="gateway",
            name="Gateway",
            allow_shell=True,
            backend=BackendMode.GATEWAY,
        )

        ctx = EnforcementContext(dry_run=True)

        # Should still raise DryRunAbort despite profile permission
        with pytest.raises(DryRunAbort):
            enforce_shell_gate(
                profile=profile,
                action="shell_command",
                run_id="run-003",
                sequence=2,
                ctx=ctx,
            )


class TestContextPropagation:
    """Test context propagation through helpers."""

    def test_helper_uses_global_context_when_none_provided(self, tmp_path: Path):
        """Helpers use global context when ctx parameter is None."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust.json"

        # Set global context with trust_workspace=True
        set_enforcement_context(EnforcementContext(trust_workspace=True))

        # Call without ctx parameter - should use global context
        enforce_workspace_trust(
            workspace=workspace,
            action="run_execution",
            run_id="run-001",
            sequence=0,
            trust_db=trust_db,
            # ctx=None (implicit)
        )  # Should not raise because global context has trust_workspace=True

        # Reset global context
        set_enforcement_context(EnforcementContext())

    def test_explicit_context_overrides_global(self, tmp_path: Path):
        """Explicit ctx parameter overrides global context."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust.json"

        # Set global context with trust_workspace=True
        set_enforcement_context(EnforcementContext(trust_workspace=True))

        # Call with explicit ctx that has trust_workspace=False
        explicit_ctx = EnforcementContext(trust_workspace=False)

        with pytest.raises(TrustEnforcementError):
            enforce_workspace_trust(
                workspace=workspace,
                action="run_execution",
                run_id="run-001",
                sequence=0,
                trust_db=trust_db,
                ctx=explicit_ctx,  # Explicit context overrides global
            )

        # Reset global context
        set_enforcement_context(EnforcementContext())
