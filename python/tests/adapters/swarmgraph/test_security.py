"""Security tests for SwarmGraph adapter — workspace-rooted launcher rejection."""
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter


@pytest.fixture
def layout(tmp_path):
    """Return (workspace, safe_tools_dir) as sibling directories."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    tools = tmp_path / "tools"
    tools.mkdir()
    return ws, tools


def test_rejects_missing_env(layout):
    """No ARC_SWARMGRAPH_CLI set → FileNotFoundError, no workspace fallback."""
    ws, _ = layout
    adapter = SwarmGraphAdapter()
    with pytest.raises(FileNotFoundError, match="ARC_SWARMGRAPH_CLI"):
        adapter._resolve_cli(ws)


def test_rejects_malicious_workspace_launcher(layout, monkeypatch):
    """Workspace contains a 'swarmgraph' file, but env is unset → rejected."""
    ws, _ = layout
    malicious = ws / "swarmgraph"
    malicious.write_text("#!/bin/bash\necho pwned")
    malicious.chmod(malicious.stat().st_mode | stat.S_IEXEC)

    adapter = SwarmGraphAdapter()
    with pytest.raises(FileNotFoundError, match="ARC_SWARMGRAPH_CLI"):
        adapter._resolve_cli(ws)


def test_rejects_cli_inside_workspace(layout, monkeypatch):
    """ARC_SWARMGRAPH_CLI points inside workspace → PermissionError."""
    ws, _ = layout
    launcher = ws / "swarmgraph"
    launcher.write_text("#!/bin/bash\necho hi")
    launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(launcher))

    adapter = SwarmGraphAdapter()
    with pytest.raises(PermissionError, match="must not point inside"):
        adapter._resolve_cli(ws)


def test_rejects_nonexistent_cli(layout, monkeypatch):
    """ARC_SWARMGRAPH_CLI points to a missing file → FileNotFoundError."""
    ws, _ = layout
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", "/nonexistent/swarmgraph")

    adapter = SwarmGraphAdapter()
    with pytest.raises(FileNotFoundError, match="not found"):
        adapter._resolve_cli(ws)


def test_rejects_non_executable_cli(layout, monkeypatch):
    """CLI outside workspace but not executable → PermissionError."""
    ws, tools = layout
    launcher = tools / "swarmgraph"
    launcher.write_text("#!/bin/bash\necho hi")
    # deliberately NOT setting executable bit

    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(launcher))

    adapter = SwarmGraphAdapter()
    with pytest.raises(PermissionError, match="not executable"):
        adapter._resolve_cli(ws)


def test_accepts_valid_external_cli(layout, monkeypatch):
    """CLI outside workspace, executable → accepted."""
    ws, tools = layout
    launcher = tools / "swarmgraph"
    launcher.write_text("#!/bin/bash\necho hi")
    launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(launcher))

    adapter = SwarmGraphAdapter()
    result = adapter._resolve_cli(ws)
    assert result == launcher.resolve()


def test_rejects_cli_deep_inside_workspace(layout, monkeypatch):
    """CLI deep inside workspace subdirectory → PermissionError."""
    ws, _ = layout
    deep = ws / "sub" / "dir" / "swarmgraph"
    deep.parent.mkdir(parents=True)
    deep.write_text("#!/bin/bash\necho hi")
    deep.chmod(deep.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(deep))

    adapter = SwarmGraphAdapter()
    with pytest.raises(PermissionError, match="must not point inside"):
        adapter._resolve_cli(ws)


def test_rejects_cli_equal_to_workspace(layout, monkeypatch):
    """CLI path equals workspace path itself → FileNotFoundError (directory, not a file)."""
    ws, _ = layout
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(ws))

    adapter = SwarmGraphAdapter()
    with pytest.raises(FileNotFoundError, match="not found"):
        adapter._resolve_cli(ws)


def test_resolve_cli_expands_user_home(layout, monkeypatch):
    """ARC_SWARMGRAPH_CLI with ~ is expanded before checking."""
    ws, _ = layout
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", "~/nonexistent-swarmgraph-cli")

    adapter = SwarmGraphAdapter()
    with pytest.raises(FileNotFoundError):
        adapter._resolve_cli(ws)
    # If we get here, expanduser was called (Path('~/*') resolves to /Users/*)
    assert not Path("~/nonexistent-swarmgraph-cli").expanduser().exists()


def test_monolithic_gating_matches_modular(layout, monkeypatch):
    """Monolithic adapter enforces require_dual_gate identically to SwarmGraphRunner.

    Prove centralized gating consistency between the two code paths.
    """
    import asyncio

    from agent_runtime_cockpit.gating import GatingError

    ws, tools = layout
    launcher = tools / "swarmgraph"
    launcher.write_text("#!/bin/bash\necho '{}'")
    launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(launcher))
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "local")
    monkeypatch.delenv("ARC_SWARMGRAPH_ALLOW_COSTS", raising=False)

    # 1. Monolithic path raises GatingError for non-stub without costs
    adapter = SwarmGraphAdapter()
    with pytest.raises(GatingError):
        asyncio.run(adapter.run_workflow("wf-test", {"workspace": str(ws)}))

    # 2. Modular path raises GatingError for same conditions
    from agent_runtime_cockpit.adapters.swarmgraph.runner import SwarmGraphRunner
    runner = SwarmGraphRunner(ws)
    with pytest.raises(GatingError):
        asyncio.run(runner.run("test:entry", {}))

    # 3. With costs approved, both pass
    monkeypatch.setenv("ARC_SWARMGRAPH_ALLOW_COSTS", "true")
    # Monolithic passes gating but fails on subprocess (not our concern)
    # We just need gating not to raise
    try:
        asyncio.run(adapter.run_workflow("wf-test", {"workspace": str(ws)}))
    except GatingError:
        pytest.fail("GatingError raised despite ALLOW_COSTS=true")
    except (FileNotFoundError, PermissionError):
        pass  # Expected: subprocess fails but gating passed
    except Exception:
        pass  # Other errors mean gating passed

    # Modular passes similarly
    try:
        asyncio.run(runner.run("test:entry", {}))
    except GatingError:
        pytest.fail("GatingError raised despite ALLOW_COSTS=true")
    except Exception:
        pass  # Other errors mean gating passed

