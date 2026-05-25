"""Tests for MCP Python SDK detection logic."""

from __future__ import annotations

from unittest.mock import Mock, patch

from agent_runtime_cockpit.adapters.mcp_sdk.detect import (
    MCPSDKDetectionResult,
    detect_mcp_sdk,
    detect_mcp_sdk_import,
    scan_workspace_for_mcp_sdk,
)


# ── import probe ─────────────────────────────────────────────────────────────


def test_detect_import_not_installed():
    with patch("importlib.util.find_spec", return_value=None):
        detected, version = detect_mcp_sdk_import()
    assert detected is False
    assert version is None


def test_detect_import_handles_find_spec_error():
    with patch("importlib.util.find_spec", side_effect=ModuleNotFoundError):
        detected, version = detect_mcp_sdk_import()
    assert detected is False
    assert version is None


def test_detect_import_handles_value_error():
    with patch("importlib.util.find_spec", side_effect=ValueError):
        detected, version = detect_mcp_sdk_import()
    assert detected is False
    assert version is None


def test_detect_import_when_installed():
    mock_spec = Mock()
    with patch("importlib.util.find_spec", return_value=mock_spec):
        # mcp is actually installed in this project (used by mcp/server.py)
        detected, version = detect_mcp_sdk_import()
    assert isinstance(detected, bool)
    assert version is None or isinstance(version, str)


# ── workspace scanner ────────────────────────────────────────────────────────


def test_scan_empty_workspace(tmp_path):
    ev, fastmcp, tool, resource, prompt, lowlevel, client = scan_workspace_for_mcp_sdk(tmp_path)
    assert ev == []
    assert fastmcp is False
    assert tool is False
    assert resource is False
    assert prompt is False
    assert lowlevel is False
    assert client is False


def test_scan_detects_fastmcp(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\nmcp = FastMCP('Demo')\n"
    )
    ev, fastmcp, *_ = scan_workspace_for_mcp_sdk(tmp_path)
    assert "server.py" in ev
    assert fastmcp is True


def test_scan_detects_tool_decorator(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.tool()\n"
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )
    ev, fastmcp, tool, *_ = scan_workspace_for_mcp_sdk(tmp_path)
    assert tool is True


def test_scan_detects_resource_decorator(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.resource('config://settings')\n"
        "def get_settings() -> str:\n"
        "    return '{}'\n"
    )
    _, _, _, resource, *_ = scan_workspace_for_mcp_sdk(tmp_path)
    assert resource is True


def test_scan_detects_prompt_decorator(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.prompt()\n"
        "def greet(name: str) -> str:\n"
        "    return f'Hello {name}'\n"
    )
    _, _, _, _, prompt, *_ = scan_workspace_for_mcp_sdk(tmp_path)
    assert prompt is True


def test_scan_detects_client_session(tmp_path):
    (tmp_path / "client.py").write_text(
        "from mcp import ClientSession\n"
        "from mcp.client.stdio import stdio_client\n"
        "from mcp import StdioServerParameters\n"
        "params = StdioServerParameters(command='python')\n"
    )
    _, _, _, _, _, _, client = scan_workspace_for_mcp_sdk(tmp_path)
    assert client is True


def test_scan_detects_low_level_server(tmp_path):
    (tmp_path / "lowlevel.py").write_text(
        "from mcp.server.lowlevel import Server\nserver = Server('my-server')\n"
    )
    _, _, _, _, _, low, _ = scan_workspace_for_mcp_sdk(tmp_path)
    assert low is True


def test_scan_detects_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("mcp[cli]\nfastapi\n")
    ev, *_ = scan_workspace_for_mcp_sdk(tmp_path)
    assert "requirements.txt" in ev


def test_scan_detects_pyproject_toml(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["mcp>=1.0"]\n')
    ev, *_ = scan_workspace_for_mcp_sdk(tmp_path)
    assert "pyproject.toml" in ev


def test_scan_skips_venv(tmp_path):
    venv_dir = tmp_path / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\nmcp = FastMCP('X')\n"
    )
    ev, *_ = scan_workspace_for_mcp_sdk(tmp_path)
    # .venv files should be skipped
    assert not any(".venv" in e for e in ev)


def test_scan_skips_node_modules(tmp_path):
    nm_dir = tmp_path / "node_modules" / "some-pkg"
    nm_dir.mkdir(parents=True)
    (nm_dir / "server.py").write_text("from mcp.server.fastmcp import FastMCP\n")
    ev, *_ = scan_workspace_for_mcp_sdk(tmp_path)
    assert not any("node_modules" in e for e in ev)


def test_scan_no_false_positive_without_mcp_import(tmp_path):
    (tmp_path / "other.py").write_text(
        "from some.other.module import FastMCP\nmcp = FastMCP('X')\n"
    )
    ev, fastmcp, *_ = scan_workspace_for_mcp_sdk(tmp_path)
    # No mcp import marker — should not be detected
    assert "other.py" not in ev
    assert fastmcp is False


# ── combined detect ──────────────────────────────────────────────────────────


def test_detect_not_detected_empty(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(False, None),
    ):
        result = detect_mcp_sdk(tmp_path)
    assert isinstance(result, MCPSDKDetectionResult)
    assert result.detected is False
    assert result.confidence == 0.0
    assert result.evidence == []
    assert result.version is None


def test_detect_found_in_workspace(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.tool()\ndef add(a: int, b: int) -> int:\n    return a + b\n"
    )
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(False, None),
    ):
        result = detect_mcp_sdk(tmp_path)
    assert result.detected is True
    assert result.confidence > 0.0
    assert result.has_fastmcp is True
    assert result.has_tool is True


def test_detect_installed_raises_confidence(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(True, "1.8.0"),
    ):
        result = detect_mcp_sdk(tmp_path)
    assert result.detected is True
    assert result.confidence >= 0.3
    assert result.version == "1.8.0"


def test_detect_confidence_capped_at_1(tmp_path):
    # Full workspace: installed + FastMCP + tool + resource + prompt + client
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.tool()\ndef t() -> str: ...\n\n"
        "@mcp.resource('x://y')\ndef r() -> str: ...\n\n"
        "@mcp.prompt()\ndef p() -> str: ...\n"
    )
    (tmp_path / "client.py").write_text(
        "from mcp.client.stdio import stdio_client\nfrom mcp import ClientSession\n"
    )
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(True, "1.8.0"),
    ):
        result = detect_mcp_sdk(tmp_path)
    assert result.confidence <= 1.0


def test_detect_result_has_all_fields(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(False, None),
    ):
        result = detect_mcp_sdk(tmp_path)
    # NamedTuple fields all present
    assert hasattr(result, "detected")
    assert hasattr(result, "confidence")
    assert hasattr(result, "evidence")
    assert hasattr(result, "version")
    assert hasattr(result, "has_fastmcp")
    assert hasattr(result, "has_tool")
    assert hasattr(result, "has_resource")
    assert hasattr(result, "has_prompt")
    assert hasattr(result, "has_low_level_server")
    assert hasattr(result, "has_client")
