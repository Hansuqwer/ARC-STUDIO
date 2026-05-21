"""
Tests: ARC Protocol models — envelope, errors, capabilities, schemas.
"""
from agent_runtime_cockpit.protocol.event_envelope import ok, err, ARC_PROTOCOL_VERSION
from agent_runtime_cockpit.protocol.errors import ArcErrorCode
from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities
from agent_runtime_cockpit.protocol.schemas import (
    WorkspaceInfo, RuntimeInfo, RunRecord, ContextPackEntry, ConfidenceLevel, RunStatus, SourceType
)


class TestArcEnvelope:
    def test_ok_envelope_structure(self):
        env = ok({"foo": "bar"})
        assert env.ok is True
        assert env.version == ARC_PROTOCOL_VERSION
        assert env.error is None
        assert env.data == {"foo": "bar"}
        assert env.meta is not None

    def test_err_envelope_structure(self):
        env = err("SOME_ERROR", "Something went wrong", {"detail": "x"})
        assert env.ok is False
        assert env.error is not None
        assert env.error.code == "SOME_ERROR"
        assert env.error.message == "Something went wrong"
        assert env.error.details == {"detail": "x"}
        assert env.data is None

    def test_ok_with_metadata(self):
        env = ok("data", adapter="swarmgraph", workspace="/tmp", duration_ms=42.5)
        assert env.meta.adapter == "swarmgraph"
        assert env.meta.workspace == "/tmp"
        assert env.meta.duration_ms == 42.5

    def test_envelope_json_serializable(self):
        env = ok({"key": "value"})
        json_str = env.model_dump_json()
        assert '"ok": true' in json_str or '"ok":true' in json_str

    def test_error_codes_defined(self):
        for code in ArcErrorCode:
            assert len(code.value) > 0


class TestRuntimeCapabilities:
    def test_default_all_false(self):
        caps = RuntimeCapabilities()
        assert caps.can_inspect is False
        assert caps.can_run is False
        assert caps.can_trace is False

    def test_can_set_individual(self):
        caps = RuntimeCapabilities(can_inspect=True, can_export_workflow=True)
        assert caps.can_inspect is True
        assert caps.can_export_workflow is True
        assert caps.can_run is False

    def test_serializable(self):
        caps = RuntimeCapabilities(can_inspect=True)
        d = caps.model_dump()
        assert isinstance(d, dict)
        assert "can_inspect" in d

    # ── Schema versioning ──────────────────────────────────────────────────

    def test_schema_version_default(self):
        caps = RuntimeCapabilities()
        assert caps.schema_version == 1

    def test_schema_version_exported(self):
        caps = RuntimeCapabilities()
        d = caps.model_dump()
        assert d["schema_version"] == 1

    def test_schema_version_custom(self):
        caps = RuntimeCapabilities(schema_version=2)
        assert caps.schema_version == 2

    # ── Support level ──────────────────────────────────────────────────────

    def test_support_level_default(self):
        caps = RuntimeCapabilities()
        from agent_runtime_cockpit.protocol.capabilities import SupportLevel
        assert caps.support_level == SupportLevel.EXPERIMENTAL

    def test_support_level_custom(self):
        from agent_runtime_cockpit.protocol.capabilities import SupportLevel
        caps = RuntimeCapabilities(support_level=SupportLevel.BETA)
        assert caps.support_level == SupportLevel.BETA

    def test_support_level_stable(self):
        from agent_runtime_cockpit.protocol.capabilities import SupportLevel
        caps = RuntimeCapabilities(support_level=SupportLevel.STABLE)
        assert caps.support_level == SupportLevel.STABLE

    # ── Execution modes ────────────────────────────────────────────────────

    def test_execution_modes_default(self):
        caps = RuntimeCapabilities()
        from agent_runtime_cockpit.protocol.capabilities import ExecutionMode
        assert ExecutionMode.STANDALONE in caps.execution_modes
        assert len(caps.execution_modes) == 1

    def test_execution_modes_custom(self):
        from agent_runtime_cockpit.protocol.capabilities import ExecutionMode
        caps = RuntimeCapabilities(execution_modes=[ExecutionMode.STANDALONE, ExecutionMode.SEQUENCE])
        assert len(caps.execution_modes) == 2
        assert ExecutionMode.STANDALONE in caps.execution_modes
        assert ExecutionMode.SEQUENCE in caps.execution_modes

    def test_execution_modes_serialized(self):
        caps = RuntimeCapabilities()
        d = caps.model_dump()
        assert d["execution_modes"] == ["standalone"]

    # ── Adoption modes ─────────────────────────────────────────────────────

    def test_adoption_modes_default_empty(self):
        caps = RuntimeCapabilities()
        assert caps.adoption_modes == []

    def test_adoption_modes_custom(self):
        caps = RuntimeCapabilities(adoption_modes=["langgraph+swarmgraph"])
        assert "langgraph+swarmgraph" in caps.adoption_modes

    # ── Audit level ────────────────────────────────────────────────────────

    def test_audit_level_default(self):
        from agent_runtime_cockpit.protocol.capabilities import AuditLevel
        caps = RuntimeCapabilities()
        assert caps.audit_level == AuditLevel.NONE

    def test_audit_level_custom(self):
        from agent_runtime_cockpit.protocol.capabilities import AuditLevel
        caps = RuntimeCapabilities(audit_level=AuditLevel.ARC_SHA256)
        assert caps.audit_level == AuditLevel.ARC_SHA256

    # ── HITL level ─────────────────────────────────────────────────────────

    def test_hitl_level_default(self):
        from agent_runtime_cockpit.protocol.capabilities import HitlLevel
        caps = RuntimeCapabilities()
        assert caps.hitl_level == HitlLevel.NONE

    def test_hitl_level_custom(self):
        from agent_runtime_cockpit.protocol.capabilities import HitlLevel
        caps = RuntimeCapabilities(hitl_level=HitlLevel.ADVISORY)
        assert caps.hitl_level == HitlLevel.ADVISORY

    # ── Full serialization round-trip ──────────────────────────────────────

    def test_full_serialization_roundtrip(self):
        from agent_runtime_cockpit.protocol.capabilities import (
            SupportLevel, ExecutionMode, AuditLevel, HitlLevel,
        )
        caps = RuntimeCapabilities(
            schema_version=1,
            support_level=SupportLevel.ALPHA,
            execution_modes=[ExecutionMode.STANDALONE, ExecutionMode.SEQUENCE],
            adoption_modes=["langgraph+swarmgraph"],
            audit_level=AuditLevel.ARC_SHA256,
            hitl_level=HitlLevel.ADVISORY,
            can_inspect=True,
            can_run=True,
            can_export_workflow=True,
        )
        json_str = caps.model_dump_json()
        restored = RuntimeCapabilities.model_validate_json(json_str)
        assert restored.schema_version == 1
        assert restored.support_level == SupportLevel.ALPHA
        assert ExecutionMode.STANDALONE in restored.execution_modes
        assert "langgraph+swarmgraph" in restored.adoption_modes
        assert restored.audit_level == AuditLevel.ARC_SHA256
        assert restored.hitl_level == HitlLevel.ADVISORY
        assert restored.can_inspect is True
        assert restored.can_run is True


class TestDomainModels:
    def test_runtime_info_valid(self):
        from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities
        rt = RuntimeInfo(
            id="sg-001", name="SwarmGraph", adapter="swarmgraph",
            confidence=ConfidenceLevel.HIGH,
            evidence=["graph.py found"],
            capabilities=RuntimeCapabilities(can_inspect=True),
        )
        assert rt.confidence == ConfidenceLevel.HIGH
        assert rt.adapter == "swarmgraph"

    def test_workspace_info_empty(self):
        ws = WorkspaceInfo(path="/tmp", runtimes=[], files_scanned=0)
        assert ws.runtimes == []
        assert ws.detection_warnings == []

    def test_run_record_status(self):
        import datetime
        run = RunRecord(
            id="run-001", workflow_id="wf-001", runtime="swarmgraph",
            status=RunStatus.COMPLETED, started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        assert run.status == RunStatus.COMPLETED
        assert run.events == []

    def test_context_pack_entry_source_types(self):
        for st in SourceType:
            e = ContextPackEntry(
                id=f"test-{st}", task="test", source=st.value,
                source_type=st, content="test content", relevance_score=0.5,
            )
            assert e.source_type == st
