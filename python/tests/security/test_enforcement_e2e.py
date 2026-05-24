from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.security.context import (
    DryRunAbort,
    EnforcementContext,
    set_enforcement_context,
)
from agent_runtime_cockpit.security.enforcement import (
    PaidCallEnforcementError,
    TrustEnforcementError,
    enforce_paid_call_gate,
    enforce_workspace_trust,
)
from agent_runtime_cockpit.security.profiles import BackendMode, RunProfile


class TestCorrelationIdGeneration:
    def test_generates_unique_ids(self):
        id1 = EnforcementContext.generate_correlation_id()
        id2 = EnforcementContext.generate_correlation_id()
        assert id1 != id2
        assert len(id1) == 12
        assert len(id2) == 12

    def test_id_is_hex_string(self):
        cid = EnforcementContext.generate_correlation_id()
        int(cid, 16)  # raises ValueError if not valid hex


class TestCorrelationIdInDenialEvents:
    def test_dry_run_denial_includes_correlation_id(self, tmp_path: Path):
        ctx = EnforcementContext(dry_run=True)
        set_enforcement_context(ctx)
        captured: list[dict] = []

        def capture(run_id: str, event_type: str, data: dict):
            captured.append(data)

        with pytest.raises(DryRunAbort) as exc_info:
            enforce_workspace_trust(
                workspace=tmp_path,
                action="test_action",
                run_id="test-run-123",
                sequence=1,
                emit_event=capture,
                trust_db=tmp_path / "trust.json",
                allow_if_no_db=True,
                ctx=ctx,
            )

        denial_data = exc_info.value.denial_event.get("data", {})
        cid = denial_data.get("correlation_id")
        assert cid is not None
        assert len(cid) == 12
        assert len(captured) == 1
        assert captured[0].get("data", {}).get("correlation_id") == cid

    def test_trust_denial_includes_correlation_id(self, tmp_path: Path):
        trust_db = tmp_path / "trust.json"
        trust_db.write_text("{}")
        workspace = tmp_path / "untrusted_workspace"
        workspace.mkdir()

        ctx = EnforcementContext()
        captured: list[dict] = []

        def capture(run_id: str, event_type: str, data: dict):
            captured.append(data)

        with pytest.raises(TrustEnforcementError) as exc_info:
            enforce_workspace_trust(
                workspace=workspace,
                action="test_action",
                run_id="test-run-123",
                sequence=1,
                emit_event=capture,
                trust_db=trust_db,
                ctx=ctx,
            )

        denial_data = exc_info.value.denial_event.get("data", {})
        cid = denial_data.get("correlation_id")
        assert cid is not None
        assert len(cid) == 12
        assert len(captured) == 1
        assert captured[0].get("data", {}).get("correlation_id") == cid

    def test_paid_call_denial_includes_correlation_id(self):
        profile = RunProfile(
            id="test-profile",
            name="Test",
            allow_paid_calls=False,
            backend=BackendMode.STUB,
        )
        ctx = EnforcementContext()
        captured: list[dict] = []

        def capture(run_id: str, event_type: str, data: dict):
            captured.append(data)

        with pytest.raises(PaidCallEnforcementError) as exc_info:
            enforce_paid_call_gate(
                profile=profile,
                action="test_action",
                run_id="test-run-123",
                sequence=1,
                emit_event=capture,
                provider="test-provider",
                ctx=ctx,
            )

        denial_data = exc_info.value.denial_event.get("data", {})
        cid = denial_data.get("correlation_id")
        assert cid is not None
        assert len(cid) == 12
        assert len(captured) == 1
        assert captured[0].get("data", {}).get("correlation_id") == cid


class TestRetryEndpoint:
    @pytest.mark.skip(reason="requires fastapi, httpx — not in project deps")
    def test_retry_with_http_client(self):
        pass
