"""Snapshot tests for CLI JSON output (Phase 25.6).

Each test invokes a CLI command with --json and compares the output
against a golden snapshot file. Regenerate snapshots with:

    pytest tests/cli/test_cli_snapshots.py --update-snapshots

Snapshots live in tests/cli/snapshots/<command>.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
runner = CliRunner()


def _snapshot_path(command_name: str) -> Path:
    return SNAPSHOT_DIR / f"{command_name.replace(' ', '_')}.json"


DYNAMIC_KEYS = {
    "timestamp",
    "duration_ms",
    "python",
    "platform",
    "key_hint",
    "path",
    "workspace",
    "version",
}


def _normalize_json(obj):
    """Recursively sort keys and replace dynamic values with placeholders."""
    if isinstance(obj, dict):
        return {
            k: _normalize_json(v) if k not in DYNAMIC_KEYS else "<dynamic>"
            for k, v in sorted(obj.items())
        }
    if isinstance(obj, list):
        return [_normalize_json(item) for item in obj]
    return obj


@pytest.fixture
def update_snapshots(request):
    return request.config.getoption("--update-snapshots", default=False)


def _check_snapshot(
    command: list[str],
    command_name: str,
    update: bool,
    normalize: bool = True,
):
    """Compare --json output against a golden snapshot."""
    result = runner.invoke(app, command + ["--json"])
    assert result.exit_code == 0, f"Command {' '.join(command)} failed: {result.stderr}"
    actual = json.loads(result.stdout)

    snapshot_file = _snapshot_path(command_name)
    if update:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n")
        return

    if not snapshot_file.exists():
        pytest.skip(f"No snapshot file at {snapshot_file}. Run with --update-snapshots to create.")

    expected = json.loads(snapshot_file.read_text())
    if normalize:
        actual = _normalize_json(actual)
        expected = _normalize_json(expected)

    assert actual == expected, (
        f"Snapshot mismatch for '{command_name}'. Run with --update-snapshots to regenerate."
    )


# ─── Version ──────────────────────────────────────────────────────────────────


def test_version_snapshot(update_snapshots):
    _check_snapshot(["version"], "version", update_snapshots)


# ─── Health ───────────────────────────────────────────────────────────────────


def test_health_snapshot(update_snapshots):
    _check_snapshot(["health"], "health", update_snapshots)


# ─── Status (empty workspace) ─────────────────────────────────────────────────


@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Test has ordering dependency: sees 2 runtimes locally, 3 in CI full suite (crewai registered by earlier test)",
)
def test_status_snapshot(tmp_path, update_snapshots):
    _check_snapshot(["status", "--workspace", str(tmp_path)], "status_empty", update_snapshots)


# ─── Doctor ───────────────────────────────────────────────────────────────────


def test_doctor_swarmgraph_snapshot(update_snapshots):
    result = runner.invoke(app, ["doctor", "swarmgraph", "--json"])
    assert result.exit_code in (0, 1), result.stderr
    actual = json.loads(result.stdout)
    snapshot_file = _snapshot_path("doctor_swarmgraph")
    if update_snapshots:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n")
        return
    if not snapshot_file.exists():
        pytest.skip("No snapshot. Run with --update-snapshots.")
    expected = json.loads(snapshot_file.read_text())
    assert _normalize_json(actual) == _normalize_json(expected)


# ─── Help text snapshots (non-JSON, but stable) ───────────────────────────────


def test_help_text_contains_commands(update_snapshots):
    """Verify --help output contains all expected top-level commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    output = result.stdout
    expected_commands = [
        "version",
        "health",
        "status",
        "inspect",
        "runtimes",
        "workflows",
        "schemas",
        "serve",
        "run",
        "bug-report",
        "context",
        "adapter",
        "doctor",
        "workspace",
        "isolation",
        "config",
        "hitl",
        "storage",
        "studio",
        "runs",
        "eval",
        "providers",
        "receipt",
        "audit",
        "profiles",
        "prompt",
        "mcp",
    ]
    for cmd in expected_commands:
        assert cmd in output, f"Expected command '{cmd}' not found in --help output"
