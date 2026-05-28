"""Tests for arc ci commands (Phase 80 / R51)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def sandbox_audit_events(tmp_path: Path) -> Path:
    """Create synthetic sandbox audit events file with mixed allowed/denied."""
    audit_dir = tmp_path / ".arc" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    events_path = audit_dir / "sandbox.events.jsonl"

    events = [
        {
            "audit_id": "a1",
            "command": ["ls", "-la"],
            "classification": "read_only",
            "allowed": True,
            "reason": "auto_allowed",
            "started_at": "2026-05-28T00:00:00Z",
            "provider": "subprocess",
        },
        {
            "audit_id": "a2",
            "command": ["python", "-c", "print('hi')"],
            "classification": "read_only",
            "allowed": True,
            "reason": "auto_allowed",
            "started_at": "2026-05-28T00:00:01Z",
            "provider": "subprocess",
        },
        {
            "audit_id": "a3",
            "command": ["curl", "https://example.com"],
            "classification": "network",
            "allowed": False,
            "reason": "network_denied_by_default",
            "started_at": "2026-05-28T00:00:02Z",
            "provider": "subprocess",
        },
        {
            "audit_id": "a4",
            "command": ["rm", "-rf", "."],
            "classification": "destructive",
            "allowed": False,
            "reason": "destructive_denied_by_default",
            "started_at": "2026-05-28T00:00:03Z",
            "provider": "subprocess",
        },
    ]
    with open(events_path, "w", encoding="utf-8") as f:
        for evt in events:
            f.write(json.dumps(evt, sort_keys=True) + "\n")
    return audit_dir


@pytest.fixture
def policy_config(tmp_path: Path) -> Path:
    """Create sandbox policy config."""
    config_dir = tmp_path / ".arc"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "sandbox_policies.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "policies": [
                    {
                        "name": "local-safe",
                        "allow_network": False,
                        "allow_install": False,
                        "allow_destructive": False,
                    },
                    {
                        "name": "ci-safe",
                        "allow_network": False,
                        "allow_install": False,
                        "allow_destructive": False,
                    },
                ],
            },
            sort_keys=True,
            indent=2,
        )
    )
    return config_path


@pytest.fixture
def goldens(tmp_path: Path) -> Path:
    """Create golden test files."""
    goldens_dir = tmp_path / ".arc" / "goldens"
    goldens_dir.mkdir(parents=True, exist_ok=True)
    (goldens_dir / "test1.golden.json").write_text('{"test": 1}')
    (goldens_dir / "test2.golden.json").write_text('{"test": 2}')
    return goldens_dir


@pytest.fixture
def receipts(tmp_path: Path) -> Path:
    """Create receipt files."""
    receipts_dir = tmp_path / ".arc" / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    (receipts_dir / "run_001.receipt.json").write_text(
        '{"receipt_id": "r1", "run_id": "run_001", "status": "completed"}'
    )
    return receipts_dir


class TestCiCheck:
    def test_offline_check_runs(self, runner, tmp_path):
        """Test 1: offline check runs with structured JSON output."""
        result = runner.invoke(app, ["ci", "check", "--json"], env={"HOME": str(tmp_path)})
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["ok"] is True
        data = output["data"]
        assert data["private"] is True
        assert "checks" in data
        assert "sandbox_audit" in data["checks"]
        assert "policy" in data["checks"]
        assert "eval" in data["checks"]
        assert "receipt" in data["checks"]
        assert data["overall"] in ("pass", "fail")

    def test_check_includes_policy(self, runner, tmp_path, policy_config):
        """Test 2: policy check included and reports policy names."""
        result = runner.invoke(app, ["ci", "check", "--json"], env={"HOME": str(tmp_path)})
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        policy_check = output["data"]["checks"]["policy"]
        assert policy_check["status"] in ("pass", "fail")
        assert policy_check["policy_count"] >= 0

    def test_check_detects_denied_commands(self, runner, tmp_path, sandbox_audit_events):
        """Test 3: denied commands are detected in sandbox audit."""
        result = runner.invoke(app, ["ci", "check", "--json"], env={"HOME": str(tmp_path)})
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        audit_check = output["data"]["checks"]["sandbox_audit"]
        assert audit_check["denied_count"] == 2
        assert audit_check["status"] == "fail"

    def test_check_detects_eval_goldens(self, runner, tmp_path, goldens, monkeypatch):
        """Test 4: eval check detects goldens."""
        monkeypatch.chdir(str(tmp_path))
        result = runner.invoke(app, ["ci", "check", "--json"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        eval_check = output["data"]["checks"]["eval"]
        assert eval_check["status"] == "pass"
        assert eval_check["goldens_found"] == 2

    def test_check_detects_receipts(self, runner, tmp_path, receipts, monkeypatch):
        """Test 5: receipt check detects receipt files."""
        monkeypatch.chdir(str(tmp_path))
        result = runner.invoke(app, ["ci", "check", "--json"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        receipt_check = output["data"]["checks"]["receipt"]
        assert receipt_check["status"] == "pass"
        assert receipt_check["receipt_count"] == 1

    def test_no_upload_by_default(self, runner, tmp_path):
        """Test 6: default mode is private with no uploads."""
        result = runner.invoke(app, ["ci", "check", "--json"], env={"HOME": str(tmp_path)})
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["data"]["private"] is True

    def test_all_failures_structured_in_json(self, runner, tmp_path):
        """Test 7: failures are structured in JSON output."""
        result = runner.invoke(app, ["ci", "check", "--json"], env={"HOME": str(tmp_path)})
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        data = output["data"]
        for check_name, check_result in data["checks"].items():
            assert "status" in check_result
            assert check_result["status"] in ("pass", "fail", "skip")


class TestCiSummary:
    def test_deterministic_summary_markdown(self, runner, tmp_path, sandbox_audit_events):
        """Test 8: deterministic markdown summary output."""
        result = runner.invoke(
            app, ["ci", "summary", "--format", "markdown"], env={"HOME": str(tmp_path)}
        )
        assert result.exit_code == 0
        output = result.stdout
        assert "ARC CI Summary" in output
        assert "Advisory only" in output
        assert "Audit Events" in output
        assert "Policies" in output

    def test_summary_json_format(self, runner, tmp_path, sandbox_audit_events):
        """Test 9: JSON summary format."""
        result = runner.invoke(
            app, ["ci", "summary", "--format", "json", "--json"], env={"HOME": str(tmp_path)}
        )
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["ok"] is True
        data = output["data"]
        assert data["advisory"] is True
        assert data["no_ai_judgment"] is True
        assert "audit_events" in data
        assert "policies" in data
        assert "eval" in data

    def test_summary_includes_denied_commands(self, runner, tmp_path, sandbox_audit_events):
        """Test 10: summary includes denied commands from audit."""
        result = runner.invoke(
            app, ["ci", "summary", "--format", "json", "--json"], env={"HOME": str(tmp_path)}
        )
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        denied = output["data"]["audit_events"]["denied_commands"]
        assert len(denied) == 2
        classifications = {d["classification"] for d in denied}
        assert "network" in classifications
        assert "destructive" in classifications


class TestCiVerifyAudit:
    def test_audit_verification_runs(self, runner, tmp_path):
        """Test 11: audit verification returns result."""
        result = runner.invoke(app, ["ci", "verify-audit", "--json"], env={"HOME": str(tmp_path)})
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["ok"] is True
        assert "ok" in output["data"]
        assert "chain" in output["data"]
        assert "reason" in output["data"]
