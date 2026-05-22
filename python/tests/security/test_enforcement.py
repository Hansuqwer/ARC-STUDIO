"""Tests for typed denial events and enforcement helpers (Phase 23)."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import Mock

from agent_runtime_cockpit.security.enforcement import (
    enforce_workspace_trust,
    enforce_paid_call_gate,
    enforce_shell_gate,
    enforce_network_gate,
    TrustEnforcementError,
    PaidCallEnforcementError,
    ShellEnforcementError,
    NetworkEnforcementError,
)
from agent_runtime_cockpit.security.profiles import RunProfile, BackendMode
from agent_runtime_cockpit.security.trust import trust_workspace
from agent_runtime_cockpit.protocol.denial_events import (
    TrustDeniedEvent,
    PaidCallDeniedEvent,
)


class TestTrustEnforcement:
    """Test workspace trust enforcement with typed denial events."""

    def test_enforce_trust_allows_trusted_workspace(self, tmp_path: Path):
        """Trusted workspace passes enforcement without raising."""
        workspace = tmp_path / "trusted-workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust.json"

        # Trust the workspace
        trust_workspace(workspace, trust_db=trust_db)

        # Should not raise
        enforce_workspace_trust(
            workspace=workspace,
            action="run_execution",
            run_id="run-001",
            sequence=0,
            trust_db=trust_db,
        )

    def test_enforce_trust_blocks_untrusted_workspace(self, tmp_path: Path):
        """Untrusted workspace raises TrustEnforcementError."""
        workspace = tmp_path / "untrusted-workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust.json"

        with pytest.raises(TrustEnforcementError) as exc_info:
            enforce_workspace_trust(
                workspace=workspace,
                action="run_execution",
                run_id="run-001",
                sequence=0,
                trust_db=trust_db,
            )

        assert "untrusted" in str(exc_info.value).lower()
        assert exc_info.value.denial_event is not None
        assert exc_info.value.denial_event["type"] == "TRUST_DENIED"

    def test_enforce_trust_emits_denial_event(self, tmp_path: Path):
        """Untrusted workspace emits TRUST_DENIED event."""
        workspace = tmp_path / "untrusted-workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust.json"

        # Mock event emitter
        emit_event = Mock()

        with pytest.raises(TrustEnforcementError):
            enforce_workspace_trust(
                workspace=workspace,
                action="run_execution",
                run_id="run-001",
                sequence=0,
                emit_event=emit_event,
                trust_db=trust_db,
            )

        # Verify event was emitted
        emit_event.assert_called_once()
        call_args = emit_event.call_args
        assert call_args[0][0] == "run-001"  # run_id
        assert call_args[0][1] == "TRUST_DENIED"  # event_type
        event_data = call_args[0][2]
        assert event_data["type"] == "TRUST_DENIED"
        assert event_data["data"]["action"] == "run_execution"
        assert "trust database" in event_data["data"]["reason"].lower()

    def test_enforce_trust_denial_event_structure(self, tmp_path: Path):
        """TRUST_DENIED event has correct structure."""
        workspace = tmp_path / "untrusted-workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust.json"

        emit_event = Mock()

        with pytest.raises(TrustEnforcementError):
            enforce_workspace_trust(
                workspace=workspace,
                action="provider_call",
                run_id="run-002",
                sequence=5,
                emit_event=emit_event,
                trust_db=trust_db,
            )

        event_data = emit_event.call_args[0][2]

        # Validate event structure
        assert event_data["schema_version"] == 2
        assert event_data["type"] == "TRUST_DENIED"
        assert event_data["run_id"] == "run-002"
        assert event_data["sequence"] == 5
        assert "timestamp" in event_data

        # Validate data payload
        data = event_data["data"]
        assert data["action"] == "provider_call"
        assert data["workspace_path"] == str(workspace.resolve())
        assert data["trust_level"] == "untrusted"
        assert data["required_trust_level"] == "trusted"
        assert "remediation" in data


class TestPaidCallEnforcement:
    """Test paid-call gate enforcement with typed denial events."""

    def test_enforce_paid_call_allows_when_enabled(self):
        """Profile with allow_paid_calls=True passes enforcement."""
        profile = RunProfile(
            id="local-paid",
            name="Local Paid",
            allow_paid_calls=True,
            backend=BackendMode.LOCAL,
        )

        # Should not raise
        enforce_paid_call_gate(
            profile=profile,
            action="provider_call",
            run_id="run-001",
            sequence=0,
        )

    def test_enforce_paid_call_blocks_when_disabled(self):
        """Profile with allow_paid_calls=False raises PaidCallEnforcementError."""
        profile = RunProfile(
            id="stub",
            name="Stub",
            allow_paid_calls=False,
            backend=BackendMode.STUB,
        )

        with pytest.raises(PaidCallEnforcementError) as exc_info:
            enforce_paid_call_gate(
                profile=profile,
                action="provider_call",
                run_id="run-001",
                sequence=0,
            )

        assert "paid calls not allowed" in str(exc_info.value).lower()
        assert exc_info.value.denial_event is not None
        assert exc_info.value.denial_event["type"] == "PAID_CALL_DENIED"

    def test_enforce_paid_call_emits_denial_event(self):
        """Blocked paid call emits PAID_CALL_DENIED event."""
        profile = RunProfile(
            id="stub",
            name="Stub",
            allow_paid_calls=False,
            backend=BackendMode.STUB,
        )

        emit_event = Mock()

        with pytest.raises(PaidCallEnforcementError):
            enforce_paid_call_gate(
                profile=profile,
                action="model_invocation",
                run_id="run-003",
                sequence=2,
                emit_event=emit_event,
                provider="openai",
                model="gpt-4",
            )

        # Verify event was emitted
        emit_event.assert_called_once()
        event_data = emit_event.call_args[0][2]
        assert event_data["type"] == "PAID_CALL_DENIED"
        assert event_data["data"]["action"] == "model_invocation"
        assert event_data["data"]["provider"] == "openai"
        assert event_data["data"]["model"] == "gpt-4"
        assert event_data["data"]["profile_id"] == "stub"


class TestShellEnforcement:
    """Test shell execution gate enforcement with typed denial events."""

    def test_enforce_shell_allows_when_enabled(self):
        """Profile with allow_shell=True passes enforcement."""
        profile = RunProfile(
            id="gateway",
            name="Gateway",
            allow_shell=True,
            backend=BackendMode.GATEWAY,
        )

        # Should not raise
        enforce_shell_gate(
            profile=profile,
            action="shell_command",
            run_id="run-001",
            sequence=0,
        )

    def test_enforce_shell_blocks_when_disabled(self):
        """Profile with allow_shell=False raises ShellEnforcementError."""
        profile = RunProfile(
            id="stub",
            name="Stub",
            allow_shell=False,
            backend=BackendMode.STUB,
        )

        with pytest.raises(ShellEnforcementError) as exc_info:
            enforce_shell_gate(
                profile=profile,
                action="shell_command",
                run_id="run-001",
                sequence=0,
            )

        assert "shell execution not allowed" in str(exc_info.value).lower()
        assert exc_info.value.denial_event is not None
        assert exc_info.value.denial_event["type"] == "SHELL_DENIED"

    def test_enforce_shell_emits_denial_event(self):
        """Blocked shell command emits SHELL_DENIED event."""
        profile = RunProfile(
            id="stub",
            name="Stub",
            allow_shell=False,
            backend=BackendMode.STUB,
        )

        emit_event = Mock()

        with pytest.raises(ShellEnforcementError):
            enforce_shell_gate(
                profile=profile,
                action="subprocess_spawn",
                run_id="run-004",
                sequence=3,
                emit_event=emit_event,
                command="rm -rf /",
            )

        # Verify event was emitted
        emit_event.assert_called_once()
        event_data = emit_event.call_args[0][2]
        assert event_data["type"] == "SHELL_DENIED"
        assert event_data["data"]["action"] == "subprocess_spawn"
        assert event_data["data"]["command"] == "rm -rf /"
        assert event_data["data"]["profile_id"] == "stub"


class TestNetworkEnforcement:
    """Test network access gate enforcement with typed denial events."""

    def test_enforce_network_allows_when_enabled(self):
        """Profile with allow_network=True passes enforcement."""
        profile = RunProfile(
            id="local-safe",
            name="Local Safe",
            allow_network=True,
            backend=BackendMode.STUB,
        )

        # Should not raise
        enforce_network_gate(
            profile=profile,
            action="http_request",
            run_id="run-001",
            sequence=0,
        )

    def test_enforce_network_blocks_when_disabled(self):
        """Profile with allow_network=False raises NetworkEnforcementError."""
        profile = RunProfile(
            id="stub",
            name="Stub",
            allow_network=False,
            backend=BackendMode.STUB,
        )

        with pytest.raises(NetworkEnforcementError) as exc_info:
            enforce_network_gate(
                profile=profile,
                action="http_request",
                run_id="run-001",
                sequence=0,
            )

        assert "network access not allowed" in str(exc_info.value).lower()
        assert exc_info.value.denial_event is not None
        assert exc_info.value.denial_event["type"] == "NETWORK_DENIED"

    def test_enforce_network_emits_denial_event(self):
        """Blocked network request emits NETWORK_DENIED event."""
        profile = RunProfile(
            id="stub",
            name="Stub",
            allow_network=False,
            backend=BackendMode.STUB,
        )

        emit_event = Mock()

        with pytest.raises(NetworkEnforcementError):
            enforce_network_gate(
                profile=profile,
                action="websocket_connect",
                run_id="run-005",
                sequence=4,
                emit_event=emit_event,
                url="wss://example.com/socket",
            )

        # Verify event was emitted
        emit_event.assert_called_once()
        event_data = emit_event.call_args[0][2]
        assert event_data["type"] == "NETWORK_DENIED"
        assert event_data["data"]["action"] == "websocket_connect"
        assert event_data["data"]["url"] == "wss://example.com/socket"
        assert event_data["data"]["profile_id"] == "stub"


class TestDenialEventModels:
    """Test Pydantic models for denial events."""

    def test_trust_denied_event_construction(self):
        """TrustDeniedEvent constructs with valid data."""
        event = TrustDeniedEvent(
            type="TRUST_DENIED",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-001",
            sequence=0,
            data={
                "action": "run_execution",
                "workspace_path": "/path/to/workspace",
                "reason": "Workspace not in trust database",
                "trust_level": "untrusted",
                "required_trust_level": "trusted",
                "remediation": "Run 'arc workspace trust'",
            },
        )
        assert event.type == "TRUST_DENIED"
        assert event.data.action == "run_execution"
        assert event.data.trust_level == "untrusted"

    def test_paid_call_denied_event_construction(self):
        """PaidCallDeniedEvent constructs with valid data."""
        event = PaidCallDeniedEvent(
            type="PAID_CALL_DENIED",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-002",
            sequence=1,
            data={
                "action": "provider_call",
                "provider": "openai",
                "model": "gpt-4",
                "reason": "Profile does not allow paid calls",
                "profile_id": "stub",
                "allow_paid_calls": False,
                "remediation": "Use --allow-paid flag",
            },
        )
        assert event.type == "PAID_CALL_DENIED"
        assert event.data.provider == "openai"
        assert event.data.allow_paid_calls is False
