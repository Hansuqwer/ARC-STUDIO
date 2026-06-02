"""Tests for the three research-sprint features:
1. swarmgraph/policy_linter.py
2. mcp/manifests.py + mcp/registry.py
3. evals/policy_recommend.py
"""

from __future__ import annotations


from agent_runtime_cockpit.protocol.schemas import (
    NodeType,
    WorkflowEdge,
    WorkflowInfo,
    WorkflowNode,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_workflow(
    *,
    nodes: list[WorkflowNode] | None = None,
    edges: list[WorkflowEdge] | None = None,
    metadata: dict | None = None,
) -> WorkflowInfo:
    return WorkflowInfo(
        id="wf-test",
        name="test workflow",
        runtime="swarmgraph",
        nodes=nodes or [],
        edges=edges or [],
        metadata=metadata or {},
    )


def _node(label: str, ntype: NodeType = NodeType.TOOL, **meta) -> WorkflowNode:
    return WorkflowNode(id=f"n-{label}", label=label, type=ntype, metadata=meta)


# ── PolicyLinter ──────────────────────────────────────────────────────────────


class TestPolicyLinter:
    def test_clean_workflow_passes(self, tmp_path):
        from agent_runtime_cockpit.security.policy_linter import lint_workflow

        wf = _make_workflow(nodes=[_node("read files", NodeType.TOOL)])
        report = lint_workflow(wf, workspace_root=tmp_path)
        assert report.workflow_id == "wf-test"
        assert isinstance(report.issues, list)
        # No errors expected for a simple read-only workflow
        assert report.errors == [] or report.can_run  # can_run is True when no errors

    def test_write_outside_workspace_flagged(self, tmp_path):
        from agent_runtime_cockpit.security.policy_linter import lint_workflow

        node = _node("write", NodeType.TOOL, write_path="/etc/passwd")
        wf = _make_workflow(nodes=[node])
        report = lint_workflow(wf, workspace_root=tmp_path)
        error_rules = [i.rule for i in report.errors]
        assert "write_outside_workspace" in error_rules
        assert not report.can_run

    def test_write_inside_workspace_ok(self, tmp_path):
        from agent_runtime_cockpit.security.policy_linter import lint_workflow

        node = _node("write", NodeType.TOOL, write_path=str(tmp_path / "output.txt"))
        wf = _make_workflow(nodes=[node])
        report = lint_workflow(wf, workspace_root=tmp_path)
        error_rules = [i.rule for i in report.errors]
        assert "write_outside_workspace" not in error_rules

    def test_privileged_node_without_trust_flagged(self, tmp_path):
        from agent_runtime_cockpit.security.policy_linter import lint_workflow

        node = _node("sudo", NodeType.TOOL, privileged=True)
        wf = _make_workflow(nodes=[node])
        report = lint_workflow(wf, workspace_root=tmp_path)
        error_rules = [i.rule for i in report.errors]
        assert "privileged_node" in error_rules

    def test_mcp_tool_without_pin_warns(self, tmp_path):
        from agent_runtime_cockpit.security.policy_linter import lint_workflow

        node = _node("mcp-file-tool", NodeType.TOOL)
        wf = _make_workflow(nodes=[node])
        report = lint_workflow(wf, workspace_root=tmp_path)
        warning_rules = [i.rule for i in report.warnings]
        assert "untrusted_mcp_tool" in warning_rules

    def test_report_schema_stable(self, tmp_path):
        from agent_runtime_cockpit.security.policy_linter import PolicyReport, lint_workflow

        wf = _make_workflow()
        report = lint_workflow(wf, workspace_root=tmp_path)
        assert isinstance(report, PolicyReport)
        dumped = report.model_dump()
        assert "workflow_id" in dumped
        assert "issues" in dumped
        assert "can_run" in dumped


# ── MCP Manifests ─────────────────────────────────────────────────────────────


class TestMcpManifests:
    _TOOLS = [
        {"name": "read_file", "description": "read a file", "inputSchema": {}},
        {"name": "write_file", "description": "write to a file", "inputSchema": {}},
    ]

    def test_pin_and_load(self, tmp_path):
        from agent_runtime_cockpit.mcp.manifests import ManifestStore

        store = ManifestStore(workspace=tmp_path)
        manifest = store.pin("test-server", self._TOOLS)
        loaded = store.load("test-server")
        assert loaded is not None
        assert loaded.manifest_hash == manifest.manifest_hash
        assert set(loaded.tool_names) == {"read_file", "write_file"}

    def test_no_drift_when_same(self, tmp_path):
        from agent_runtime_cockpit.mcp.manifests import ManifestStore

        store = ManifestStore(workspace=tmp_path)
        store.pin("srv", self._TOOLS)
        result = store.check_drift("srv", self._TOOLS)
        assert result["drifted"] is False

    def test_drift_detected_on_change(self, tmp_path):
        from agent_runtime_cockpit.mcp.manifests import ManifestStore

        store = ManifestStore(workspace=tmp_path)
        store.pin("srv", self._TOOLS)
        new_tools = self._TOOLS + [
            {"name": "delete_file", "description": "delete", "inputSchema": {}}
        ]
        result = store.check_drift("srv", new_tools)
        assert result["drifted"] is True
        assert "delete_file" in result["added"]

    def test_no_pin_returns_not_pinned(self, tmp_path):
        from agent_runtime_cockpit.mcp.manifests import ManifestStore

        store = ManifestStore(workspace=tmp_path)
        result = store.check_drift("unknown-srv", self._TOOLS)
        assert result["pinned"] is False

    def test_high_risk_tool_detection(self, tmp_path):
        from agent_runtime_cockpit.mcp.manifests import ManifestStore

        tools = [{"name": "write_file", "description": "write to file", "inputSchema": {}}]
        store = ManifestStore(workspace=tmp_path)
        manifest = store.pin("srv", tools)
        assert manifest.has_high_risk_tools
        assert "write_file" in manifest.high_risk_tool_names


# ── MCP Registry ──────────────────────────────────────────────────────────────


class TestMcpRegistry:
    def test_register_and_get(self, tmp_path):
        from agent_runtime_cockpit.mcp.registry import McpRegistryStore

        store = McpRegistryStore(path=tmp_path / "servers.json")
        store.register("my-srv", transport="stdio", command=["python", "srv.py"])
        loaded = store.get("my-srv")
        assert loaded is not None
        assert loaded.server_id == "my-srv"
        assert loaded.command == ["python", "srv.py"]

    def test_approve_tool(self, tmp_path):
        from agent_runtime_cockpit.mcp.registry import McpRegistryStore

        store = McpRegistryStore(path=tmp_path / "servers.json")
        store.register("srv")
        store.approve_tool("srv", "read_file", reason="reviewed")
        assert store.is_tool_approved("srv", "read_file")
        assert not store.is_tool_blocked("srv", "read_file")

    def test_block_tool(self, tmp_path):
        from agent_runtime_cockpit.mcp.registry import McpRegistryStore

        store = McpRegistryStore(path=tmp_path / "servers.json")
        store.register("srv")
        store.block_tool("srv", "delete_db")
        assert store.is_tool_blocked("srv", "delete_db")
        assert not store.is_tool_approved("srv", "delete_db")

    def test_list_servers(self, tmp_path):
        from agent_runtime_cockpit.mcp.registry import McpRegistryStore

        store = McpRegistryStore(path=tmp_path / "servers.json")
        store.register("srv-a")
        store.register("srv-b")
        names = [r.server_id for r in store.list_servers()]
        assert "srv-a" in names
        assert "srv-b" in names


# ── Eval Policy Recommend ─────────────────────────────────────────────────────


class TestPolicyRecommend:
    def _make_results(self, n_pass: int, n_fail_status: int, n_fail_event: int):
        from agent_runtime_cockpit.evals.golden import EvalResult

        results = []
        for i in range(n_pass):
            results.append(
                EvalResult(
                    run_id=f"r-pass-{i}",
                    golden_id="g1",
                    passed=True,
                    status_match=True,
                    event_type_match=True,
                    output_contains_match=True,
                    score=1.0,
                )
            )
        for i in range(n_fail_status):
            results.append(
                EvalResult(
                    run_id=f"r-fstatus-{i}",
                    golden_id="g1",
                    passed=False,
                    status_match=False,
                    event_type_match=True,
                    output_contains_match=True,
                    score=0.5,
                )
            )
        for i in range(n_fail_event):
            results.append(
                EvalResult(
                    run_id=f"r-fevent-{i}",
                    golden_id="g1",
                    passed=False,
                    status_match=True,
                    event_type_match=False,
                    output_contains_match=True,
                    score=0.5,
                )
            )
        return results

    def test_no_recommendations_below_threshold(self):
        from agent_runtime_cockpit.evals.policy_recommend import recommend_policy

        results = self._make_results(n_pass=10, n_fail_status=0, n_fail_event=0)
        report = recommend_policy(results)
        assert not report.has_recommendations

    def test_recommends_consensus_on_high_failure(self):
        from agent_runtime_cockpit.evals.policy_recommend import recommend_policy

        results = self._make_results(n_pass=3, n_fail_status=4, n_fail_event=0)
        report = recommend_policy(results)
        assert report.has_recommendations
        categories = [r.category for r in report.recommendations]
        assert "consensus" in categories or "hitl" in categories

    def test_recommends_hitl_on_status_failures(self):
        from agent_runtime_cockpit.evals.policy_recommend import recommend_policy

        results = self._make_results(n_pass=1, n_fail_status=5, n_fail_event=0)
        report = recommend_policy(results)
        assert report.has_recommendations
        categories = [r.category for r in report.recommendations]
        assert "hitl" in categories

    def test_too_few_samples_returns_empty(self):
        from agent_runtime_cockpit.evals.policy_recommend import recommend_policy

        results = self._make_results(n_pass=1, n_fail_status=1, n_fail_event=0)
        report = recommend_policy(results, min_sample=5)
        assert not report.has_recommendations

    def test_report_schema_stable(self):
        from agent_runtime_cockpit.evals.policy_recommend import (
            PolicyRecommendationReport,
            recommend_policy,
        )

        results = self._make_results(n_pass=2, n_fail_status=3, n_fail_event=2)
        report = recommend_policy(results)
        assert isinstance(report, PolicyRecommendationReport)
        dumped = report.model_dump()
        assert "recommendations" in dumped
        assert "failure_rate" in dumped

    def test_save_recommendations(self, tmp_path):
        from agent_runtime_cockpit.evals.policy_recommend import (
            recommend_policy,
            save_recommendations,
        )

        results = self._make_results(n_pass=2, n_fail_status=4, n_fail_event=0)
        report = recommend_policy(results)
        path = save_recommendations(report, tmp_path, run_id="test-batch")
        assert path.exists()
        import json

        data = json.loads(path.read_text())
        assert "recommendations" in data
