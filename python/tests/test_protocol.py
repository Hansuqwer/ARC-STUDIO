"""
Tests: ARC Protocol models — envelope, errors, capabilities, schemas.
"""
from agent_runtime_cockpit.protocol.envelope import ok, err, ARC_PROTOCOL_VERSION
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
