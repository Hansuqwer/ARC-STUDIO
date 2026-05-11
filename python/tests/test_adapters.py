"""
Tests: Runtime adapters — SwarmGraph, LangGraph, conformance suite.
"""
import tempfile
from pathlib import Path
import pytest

from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter
from agent_runtime_cockpit.adapters.langgraph import LangGraphAdapter
from agent_runtime_cockpit.adapters.registry import default_registry
from agent_runtime_cockpit.adapters.conformance import run_conformance
from agent_runtime_cockpit.protocol.schemas import WorkflowInfo, SchemaInfo


# ─── SwarmGraph Adapter ───────────────────────────────────────────────────────

class TestSwarmGraphAdapter:
    def setup_method(self):
        self.adapter = SwarmGraphAdapter()

    def test_adapter_id(self):
        assert self.adapter.adapter_id == "swarmgraph"

    def test_capabilities_not_lying(self):
        caps = self.adapter.capabilities()
        # can_replay should be False (not yet implemented)
        assert caps.can_replay is False
        assert caps.can_run is True
        assert caps.can_trace is False
        assert caps.can_inspect is True
        assert caps.can_export_workflow is True

    def test_detect_empty_dir_false(self):
        with tempfile.TemporaryDirectory() as td:
            detected, conf, evidence = self.adapter.detect(Path(td))
            # Must not falsely claim detection in an empty dir
            assert detected is False or (detected and len(evidence) > 0), \
                "detect() returned True with no evidence"

    def test_detect_with_pyproject(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "pyproject.toml").write_text('[dependencies]\nswarmgraph = "*"\n')
            detected, conf, evidence = self.adapter.detect(tdp)
            assert detected is True
            assert conf > 0.5
            assert len(evidence) > 0

    def test_detect_with_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "swarmgraph.yaml").write_text("version: 1\n")
            detected, conf, evidence = self.adapter.detect(tdp)
            assert detected is True
            assert any("swarmgraph.yaml" in e for e in evidence)

    def test_detect_with_launcher(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            launcher = tdp / "swarmgraph"
            launcher.write_text("#!/usr/bin/env sh\n")
            detected, conf, evidence = self.adapter.detect(tdp)
            assert detected is True
            assert conf >= 0.7
            assert any("swarmgraph found" in e for e in evidence)

    def test_export_workflow_returns_list(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.adapter.export_workflow(Path(td))
            assert isinstance(result, list)
            assert len(result) > 0
            assert isinstance(result[0], WorkflowInfo)

    def test_fixture_workflow_structure(self):
        wf = self.adapter._fixture_workflow()
        assert len(wf.nodes) >= 3
        assert len(wf.entry_points) >= 1
        # Verify no duplicate node IDs
        ids = [n.id for n in wf.nodes]
        assert len(ids) == len(set(ids)), "Duplicate node IDs in fixture workflow"

    def test_fixture_edges_reference_valid_nodes(self):
        wf = self.adapter._fixture_workflow()
        node_ids = {n.id for n in wf.nodes}
        for edge in wf.edges:
            assert edge.from_node in node_ids, f"Edge from unknown node: {edge.from_node}"
            assert edge.to_node in node_ids, f"Edge to unknown node: {edge.to_node}"

    def test_export_schemas_returns_list(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.adapter.export_schemas(Path(td))
            assert isinstance(result, list)
            assert isinstance(result[0], SchemaInfo)

    def test_scan_ignores_dependency_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "swarmgraph.yaml").write_text("version: 1\n")
            venv_pkg = tdp / ".venv2" / "lib" / "python3.13" / "site-packages"
            venv_pkg.mkdir(parents=True)
            (venv_pkg / "metadata.py").write_text(
                "from pydantic import BaseModel\nclass RawMetadata(BaseModel):\n    name: str\n"
            )

            schemas = self.adapter.export_schemas(tdp)
            assert all(".venv" not in str(s.source_file) for s in schemas)
            assert all(s.name != "RawMetadata" for s in schemas)

    @pytest.mark.asyncio
    async def test_run_workflow_missing_launcher_fails_truthfully(self, monkeypatch):
        monkeypatch.setenv("ARC_SWARMGRAPH_CLI", "/definitely/missing/swarmgraph")
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(FileNotFoundError):
                await self.adapter.run_workflow("wf-test", {"workspace": td})

    @pytest.mark.asyncio
    async def test_run_workflow_uses_real_cli_json(self, monkeypatch):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            cli = tdp / "swarmgraph"
            cli.write_text(
                "#!/usr/bin/env sh\n"
                "printf '%s\\n' '{\"swarm_id\":\"sg-test\",\"status\":\"completed\",\"worker_count\":0,\"final_output\":\"ok\"}'\n"
            )
            cli.chmod(cli.stat().st_mode | 0o111)
            monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))
            run = await self.adapter.run_workflow("wf-test", {"workspace": td})
            assert run.status.value == "completed"
            assert run.metadata["swarm_id"] == "sg-test"
            assert run.metadata["final_output"] == "ok"
            assert any(event.type == "RUN_COMPLETED" for event in run.events)

    @pytest.mark.asyncio
    async def test_demo_run_workflow_returns_marked_run_record(self):
        from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus
        run = await self.adapter.demo_run_workflow("wf-test")
        assert isinstance(run, RunRecord)
        assert run.status == RunStatus.COMPLETED
        assert run.metadata.get("_mock") is True
        assert len(run.events) > 0
        # Events must be sequentially ordered
        seqs = [e.sequence for e in run.events]
        assert seqs == sorted(seqs), "Run events not in sequence order"


# ─── LangGraph Adapter ────────────────────────────────────────────────────────

class TestLangGraphAdapter:
    def setup_method(self):
        self.adapter = LangGraphAdapter()

    def test_adapter_id(self):
        assert self.adapter.adapter_id == "langgraph"

    def test_capabilities_honest(self):
        caps = self.adapter.capabilities()
        # LangGraph adapter cannot run without the library
        assert caps.can_run is False

    def test_detect_empty_dir_false(self):
        with tempfile.TemporaryDirectory() as td:
            detected, conf, evidence = self.adapter.detect(Path(td))
            assert detected is False or (detected and len(evidence) > 0)

    def test_detect_with_requirements(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "requirements.txt").write_text("langgraph>=0.2\ntyper\n")
            detected, conf, evidence = self.adapter.detect(tdp)
            assert detected is True
            assert any("langgraph" in e for e in evidence)

    def test_detect_with_stategraph_import(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "agent.py").write_text("from langgraph.graph import StateGraph\n")
            detected, conf, evidence = self.adapter.detect(tdp)
            assert detected is True

    def test_export_workflow_returns_fixture_when_no_stategraph(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.adapter.export_workflow(Path(td))
            assert isinstance(result, list)
            assert len(result) > 0

    def test_run_workflow_raises_not_implemented(self):
        import asyncio
        with pytest.raises(NotImplementedError):
            asyncio.run(self.adapter.run_workflow("test"))


# ─── Registry ─────────────────────────────────────────────────────────────────

class TestAdapterRegistry:
    def test_default_registry_has_adapters(self):
        registry = default_registry()
        assert len(registry.all()) >= 2

    def test_get_by_id(self):
        registry = default_registry()
        sg = registry.get("swarmgraph")
        lg = registry.get("langgraph")
        assert sg is not None
        assert lg is not None
        assert sg.adapter_id == "swarmgraph"

    def test_get_unknown_returns_none(self):
        registry = default_registry()
        assert registry.get("nonexistent-adapter-xyz") is None

    def test_detect_all_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            registry = default_registry()
            results = registry.detect_all(Path(td))
            assert isinstance(results, list)
            # Empty dir should return empty or only low-confidence
            for r in results:
                assert len(r.evidence) > 0, "Detected runtime with no evidence"


# ─── Conformance Suite ────────────────────────────────────────────────────────

class TestConformance:
    def test_swarmgraph_conformance_passes(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # Set up a minimal swarmgraph project
            (tdp / "swarmgraph.yaml").write_text("version: 1\n")
            adapter = SwarmGraphAdapter()
            result = run_conformance(adapter, tdp)

            assert result.adapter_id == "swarmgraph"
            assert result.failed == 0, f"Conformance failures: {result.errors}"
            # Must have at least 4 passing tests
            assert result.passed >= 4

    def test_langgraph_conformance_no_false_positive(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = LangGraphAdapter()
            result = run_conformance(adapter, Path(td))
            # detect_no_false_positive MUST pass
            detect_test = next(
                (d for d in result.details if d["test"] == "detect_no_false_positive"), None
            )
            assert detect_test is not None, "detect_no_false_positive test not found"
            assert detect_test["result"] == "PASS", \
                f"detect_no_false_positive failed: {detect_test['reason']}"

    def test_conformance_result_fields(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = SwarmGraphAdapter()
            result = run_conformance(adapter, Path(td))
            assert hasattr(result, "passed")
            assert hasattr(result, "failed")
            assert hasattr(result, "skipped")
            assert hasattr(result, "details")
            assert hasattr(result, "ok")
