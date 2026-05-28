"""Tests for Plan/Apply/Review models and CLI (Phase 75)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.security.plan import (
    PlanStepStatus,
    build_plan,
    build_plan_audit_event,
)
from agent_runtime_cockpit.security.sandbox import CommandClassification, SandboxPolicy

runner = CliRunner()


class TestPlanModels:
    def test_plan_step_status_values(self) -> None:
        assert PlanStepStatus.PENDING.value == "pending"
        assert PlanStepStatus.APPROVED.value == "approved"
        assert PlanStepStatus.DENIED.value == "denied"
        assert PlanStepStatus.APPLIED.value == "applied"
        assert PlanStepStatus.FAILED.value == "failed"

    def test_build_plan_single_readonly(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["ls", "-la"]], policy)
        assert plan.total_steps == 1
        assert plan.approved_steps == 1
        assert plan.denied_steps == 0
        assert plan.overall_allowed is True
        assert plan.steps[0].classification == CommandClassification.READ_ONLY
        assert plan.steps[0].cost_estimate == "none"
        assert plan.steps[0].risk_estimate == "low"

    def test_build_plan_destructive_denied(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["rm", "-rf", "."]], policy)
        assert plan.total_steps == 1
        assert plan.denied_steps == 1
        assert plan.overall_allowed is False
        assert plan.has_destructive is True
        assert plan.steps[0].classification == CommandClassification.DESTRUCTIVE
        assert plan.steps[0].risk_estimate == "critical"

    def test_build_plan_network_denied_by_default(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["curl", "https://example.com"]], policy)
        assert plan.total_steps == 1
        assert plan.overall_allowed is False
        assert plan.has_network is True
        assert plan.steps[0].classification == CommandClassification.NETWORK
        assert plan.steps[0].approval_required is True

    def test_build_plan_network_allowed_when_policy_permits(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test", allow_network=True)
        plan = build_plan([["curl", "https://example.com"]], policy)
        assert plan.overall_allowed is True
        assert plan.steps[0].decision.allowed is True

    def test_build_plan_install_denied_by_default(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["pip", "install", "requests"]], policy)
        assert plan.has_install is True
        assert plan.overall_allowed is False
        assert plan.steps[0].classification == CommandClassification.INSTALL

    def test_build_plan_privileged_always_denied(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["sudo", "ls"]], policy)
        assert plan.has_privileged is True
        assert plan.overall_allowed is False
        assert plan.steps[0].classification == CommandClassification.PRIVILEGED

    def test_build_plan_mixed_commands(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan(
            [["ls", "-la"], ["cat", "file.txt"], ["curl", "https://example.com"]],
            policy,
        )
        assert plan.total_steps == 3
        assert plan.approved_steps == 2
        assert plan.has_network is True
        assert plan.overall_allowed is False

    def test_build_plan_file_intents_extracted(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["cat", "src/main.py"]], policy)
        assert "src/main.py" in plan.steps[0].file_intents

    def test_build_plan_write_escape_denied(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["touch", "../escape.txt"]], policy)
        assert plan.total_steps == 1
        assert plan.denied_steps == 1
        assert plan.overall_allowed is False
        assert plan.steps[0].decision.allowed is False
        assert "escapes workspace" in plan.steps[0].decision.reason

    def test_build_plan_cost_risk_estimates(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["ls"], ["touch", "file.txt"], ["pip", "install", "x"]], policy)
        assert plan.steps[0].cost_estimate == "none"
        assert plan.steps[0].risk_estimate == "low"
        assert plan.steps[1].cost_estimate == "none"
        assert plan.steps[1].risk_estimate == "medium"
        assert plan.steps[2].cost_estimate == "unknown"
        assert plan.steps[2].risk_estimate == "high"

    def test_build_plan_serialization(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["ls", "-la"]], policy, plan_id="test-plan-1")
        data = plan.model_dump(mode="json")
        assert data["plan_id"] == "test-plan-1"
        assert data["total_steps"] == 1
        assert len(data["steps"]) == 1
        assert data["steps"][0]["classification"] == "read_only"

    def test_build_plan_audit_event(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([["ls"]], policy, plan_id="test-plan-audit")
        event = build_plan_audit_event(plan)
        assert event["type"] == "plan_decision"
        assert event["plan_id"] == "test-plan-audit"
        assert event["overall_allowed"] is True
        assert event["steps"] == [
            {
                "step_index": 0,
                "command": ["ls"],
                "classification": "read_only",
                "allowed": True,
                "approval_required": False,
                "reason": "read-only command",
            }
        ]

    def test_build_plan_empty_commands(self) -> None:
        policy = SandboxPolicy(workspace_root="/tmp/test")
        plan = build_plan([], policy)
        assert plan.total_steps == 0
        assert plan.overall_allowed is True


class TestPlanCli:
    def test_plan_explain_help(self) -> None:
        result = runner.invoke(app, ["plan", "explain", "--help"])
        assert result.exit_code == 0
        assert "plan" in result.output.lower() or "explain" in result.output.lower()

    def test_plan_explain_readonly(self) -> None:
        result = runner.invoke(app, ["plan", "explain", "--json", "--", "ls", "-la"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["total_steps"] == 1
        assert data["data"]["overall_allowed"] is True
        assert data["data"]["steps"][0]["classification"] == "read_only"
        assert data["data"]["audit_path"].endswith(".arc/audit/plan.events.jsonl")

    def test_plan_explain_destructive(self) -> None:
        result = runner.invoke(app, ["plan", "explain", "--json", "--", "rm", "-rf", "."])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["overall_allowed"] is False
        assert data["data"]["has_destructive"] is True
        assert data["data"]["steps"][0]["classification"] == "destructive"

    def test_plan_explain_network(self) -> None:
        result = runner.invoke(
            app, ["plan", "explain", "--json", "--", "curl", "https://example.com"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["has_network"] is True
        assert data["data"]["steps"][0]["approval_required"] is True

    def test_plan_explain_denies_workspace_escape(self, tmp_path) -> None:
        result = runner.invoke(
            app,
            [
                "plan",
                "explain",
                "--json",
                "--workspace",
                str(tmp_path),
                "--",
                "touch",
                "../escape.txt",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["overall_allowed"] is False
        assert data["data"]["steps"][0]["decision"]["allowed"] is False
        assert "escapes workspace" in data["data"]["steps"][0]["decision"]["reason"]

    def test_plan_explain_multi_command(self) -> None:
        result = runner.invoke(
            app,
            [
                "plan",
                "explain",
                "--json",
                "--",
                "ls",
                "-la",
                "--",
                "cat",
                "file.txt",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["total_steps"] == 2

    def test_plan_explain_missing_command(self) -> None:
        result = runner.invoke(app, ["plan", "explain", "--json"])
        assert result.exit_code != 0

    def test_plan_explain_with_policy(self) -> None:
        result = runner.invoke(
            app,
            [
                "plan",
                "explain",
                "--json",
                "--policy",
                "local-safe",
                "--",
                "ls",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["policy"] == "local-safe"
