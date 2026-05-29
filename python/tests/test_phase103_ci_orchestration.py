from __future__ import annotations

import json
import sys

from typer.testing import CliRunner

from agent_runtime_cockpit.ci_orchestration import build_ci_matrix
from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.runtime.streaming import (
    StreamEventType,
    TerminalStreamEvent,
    TerminalStreamResult,
)
from agent_runtime_cockpit.security.sandbox import CommandClassification, classify_command


def _payload(output: str) -> dict:
    return json.loads(output)


def test_phase103_matrix_detects_python_pnpm_and_workflow_jobs(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "fixture",
                "packageManager": "pnpm@9.15.9",
                "scripts": {"test": "node -e 'console.log(1)'", "typecheck": "tsc -b"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='fixture'\nversion='0'\n[tool.pytest.ini_options]\ntestpaths=['tests']\n[tool.ruff]\nline-length=100\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\njobs:\n  test:\n    steps:\n      - run: pnpm typecheck\n",
        encoding="utf-8",
    )

    matrix = build_ci_matrix(tmp_path)

    assert matrix.count >= 5
    assert any(job.kind == "python" and "pytest" in job.command for job in matrix.jobs)
    assert any(job.kind == "node" and job.command == ["pnpm", "test"] for job in matrix.jobs)
    assert any(
        job.kind == "workflow" and job.command == ["pnpm", "typecheck"] for job in matrix.jobs
    )


def test_phase103_ci_matrix_cli_json(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "fixture", "scripts": {"test": "node -e 'console.log(1)'"}}),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["ci", "matrix", "--json", "--workspace", str(tmp_path)])

    assert result.exit_code == 0, result.output
    data = _payload(result.output)["data"]
    assert data["version"] == 1
    assert data["count"] >= 1
    assert any(job["command"] == ["npm", "test"] for job in data["jobs"])


def test_phase103_ci_run_detected_job_uses_sandbox_and_writes_artifact(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "fixture", "scripts": {"test": "node -e 'console.log(1)'"}}),
        encoding="utf-8",
    )
    job_id = next(
        job.id for job in build_ci_matrix(tmp_path).jobs if job.command == ["npm", "test"]
    )

    def fake_stream(command, **kwargs):
        event = TerminalStreamEvent(
            stream_id="stream-test",
            event=StreamEventType.COMPLETED,
            source="testbench",
            sequence=0,
            command=command,
            exit_code=0,
        )
        stream_result = TerminalStreamResult(
            stream_id="stream-test",
            source="testbench",
            command=command,
            exit_code=0,
            terminal_event=StreamEventType.COMPLETED,
            stdout="ok\n",
            duration_ms=12,
            event_count=1,
        )
        return [event], stream_result

    monkeypatch.setattr("agent_runtime_cockpit.cli.ci.stream_subprocess_events", fake_stream)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / ".arc" / "audit"))

    result = CliRunner().invoke(
        app,
        ["ci", "run", "--json", "--workspace", str(tmp_path), "--job", job_id],
    )

    assert result.exit_code == 0, result.output
    data = _payload(result.output)["data"]
    assert data["status"] == "passed"
    assert data["job"]["id"] == job_id
    assert data["decision"]["allowed"] is True
    assert data["decision"]["classification"] == "writes_workspace"
    assert data["artifact_paths"]
    assert (tmp_path / data["artifact_paths"][0]).exists()


def test_phase103_ci_run_denies_network_by_default(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "ci",
            "run",
            "--json",
            "--workspace",
            str(tmp_path),
            "--",
            "curl",
            "https://example.com",
        ],
    )

    assert result.exit_code == 3, result.output
    data = _payload(result.output)["data"]
    assert data["status"] == "denied"
    assert data["decision"]["classification"] == "network"
    assert data["artifact_paths"]


def test_phase103_ci_run_stream_json_emits_events_and_result(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "ci",
            "run",
            "--json",
            "--stream-json",
            "--workspace",
            str(tmp_path),
            "--",
            sys.executable,
            "-c",
            "print('ci')",
        ],
    )

    assert result.exit_code == 0, result.output
    lines = [json.loads(line) for line in result.output.splitlines() if line.strip()]
    assert [line["data"].get("event") for line in lines[:-1]][0] == "started"
    assert lines[-1]["data"]["status"] == "passed"


def test_phase103_safe_ci_command_classification():
    assert classify_command(["pnpm", "test"]) == CommandClassification.WRITES_WORKSPACE
    assert (
        classify_command(["uv", "run", "pytest", "tests/", "-q"])
        == CommandClassification.WRITES_WORKSPACE
    )
    assert classify_command(["pnpm", "install"]) == CommandClassification.INSTALL
