"""MCP Python SDK detection logic.

T1 detection is import/config/static-file based only. It never executes user code.

MCP Python SDK package: ``mcp`` (``import mcp``, ``from mcp.server.fastmcp import FastMCP``).

Key detected constructs:
- FastMCP(...)           -- high-level server definition (mcp.server.fastmcp)
- @mcp.tool()            -- tool decorator on FastMCP instance
- @mcp.resource(...)     -- resource decorator on FastMCP instance
- @mcp.prompt()          -- prompt decorator on FastMCP instance
- mcp.server.Server(...) -- low-level server (mcp.server.lowlevel)
- ClientSession(...)     -- client session (mcp.client.session)
- StdioServerParameters  -- stdio client config
- stdio_client / sse_client / streamablehttp_client -- client transports
"""

from __future__ import annotations

import importlib.util
import logging
import warnings
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class MCPSDKDetectionResult(NamedTuple):
    """Result of MCP Python SDK detection probe."""

    detected: bool
    confidence: float
    evidence: list[str]
    version: str | None
    has_fastmcp: bool
    has_tool: bool
    has_resource: bool
    has_prompt: bool
    has_low_level_server: bool
    has_client: bool


def detect_mcp_sdk_import() -> tuple[bool, str | None]:
    """Check whether ``mcp`` is importable and return its version.

    ``importlib.util.find_spec("mcp")`` is used for a side-effect-free probe.
    We avoid actually importing ``mcp`` because the package may trigger
    event-loop or asyncio machinery on import in some versions.
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            spec = importlib.util.find_spec("mcp")
    except (ModuleNotFoundError, ValueError):
        return False, None
    if spec is None:
        return False, None
    try:
        import mcp  # noqa: PLC0415

        return True, getattr(mcp, "__version__", None)
    except Exception as exc:  # noqa: BLE001
        log.debug("mcp import failed: %s", exc)
        return False, None


def scan_workspace_for_mcp_sdk(
    workspace: Path,
) -> tuple[list[str], bool, bool, bool, bool, bool, bool]:
    """Scan workspace for MCP Python SDK usage patterns without executing code.

    Returns:
        (evidence, has_fastmcp, has_tool, has_resource, has_prompt,
         has_low_level_server, has_client)
    """
    evidence: list[str] = []
    has_fastmcp = False
    has_tool = False
    has_resource = False
    has_prompt = False
    has_low_level_server = False
    has_client = False

    # Import markers that identify an MCP SDK file
    import_patterns = (
        "from mcp.server.fastmcp",
        "from mcp.server import",
        "from mcp import",
        "import mcp",
        "from mcp.client",
        "from mcp.server.lowlevel",
        "mcp.server.fastmcp",
    )

    fastmcp_patterns = (
        "FastMCP(",
        "FastMCP(",
    )
    tool_patterns = (
        "@mcp.tool(",
        "@mcp.tool()",
        "@server.tool(",
        ".tool()",
        ".tool(",
    )
    resource_patterns = (
        "@mcp.resource(",
        "@server.resource(",
        ".resource(",
    )
    prompt_patterns = (
        "@mcp.prompt(",
        "@mcp.prompt()",
        "@server.prompt(",
        ".prompt(",
    )
    low_level_patterns = (
        "from mcp.server.lowlevel",
        "mcp.server.Server(",
        "from mcp.server import Server",
        "Server(",
    )
    client_patterns = (
        "ClientSession(",
        "StdioServerParameters(",
        "stdio_client(",
        "sse_client(",
        "streamablehttp_client(",
        "from mcp.client",
        "from mcp import ClientSession",
    )

    for py_file in workspace.rglob("*.py"):
        if _skip_path(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            log.debug("Failed to read %s: %s", py_file, exc)
            continue
        # Only consider files with mcp import markers
        if not any(pattern in content for pattern in import_patterns):
            continue
        rel_path = str(py_file.relative_to(workspace))
        evidence.append(rel_path)
        has_fastmcp = has_fastmcp or any(p in content for p in fastmcp_patterns)
        has_tool = has_tool or any(p in content for p in tool_patterns)
        has_resource = has_resource or any(p in content for p in resource_patterns)
        has_prompt = has_prompt or any(p in content for p in prompt_patterns)
        has_low_level_server = has_low_level_server or any(p in content for p in low_level_patterns)
        has_client = has_client or any(p in content for p in client_patterns)

    # Check dependency files
    for req_file in ("requirements.txt", "requirements-dev.txt", "pyproject.toml"):
        req_path = workspace / req_file
        if not req_path.exists():
            continue
        try:
            content = req_path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError as exc:
            log.debug("Failed to read %s: %s", req_path, exc)
            continue
        # Match standalone "mcp" dep (not e.g. "mcp-server-X" third-party)
        if (
            '"mcp"' in content
            or "'mcp'" in content
            or "mcp[" in content
            or "\nmcp\n" in content
            or "\nmcp\r" in content
            or "mcp>=".lower() in content
            or "mcp ==" in content
        ):
            evidence.append(req_file)

    return (
        evidence,
        has_fastmcp,
        has_tool,
        has_resource,
        has_prompt,
        has_low_level_server,
        has_client,
    )


def detect_mcp_sdk(workspace: Path) -> MCPSDKDetectionResult:
    """Detect MCP Python SDK usage in workspace without executing workspace code."""
    installed, version = detect_mcp_sdk_import()
    (
        workspace_evidence,
        has_fastmcp,
        has_tool,
        has_resource,
        has_prompt,
        has_low_level_server,
        has_client,
    ) = scan_workspace_for_mcp_sdk(workspace)

    evidence: list[str] = []
    if installed:
        evidence.append(f"mcp installed (version: {version or 'unknown'})")
    evidence.extend(workspace_evidence)

    detected = installed or bool(workspace_evidence)
    confidence = 0.0
    if installed:
        confidence += 0.3
    if workspace_evidence:
        confidence += 0.25
    if has_fastmcp:
        confidence += 0.2
    if has_tool:
        confidence += 0.1
    if has_resource:
        confidence += 0.05
    if has_prompt:
        confidence += 0.05
    if has_low_level_server:
        confidence += 0.05
    if has_client:
        confidence += 0.05

    if not detected:
        confidence = 0.0

    return MCPSDKDetectionResult(
        detected=detected,
        confidence=round(min(confidence, 1.0), 4),
        evidence=evidence,
        version=version,
        has_fastmcp=has_fastmcp,
        has_tool=has_tool,
        has_resource=has_resource,
        has_prompt=has_prompt,
        has_low_level_server=has_low_level_server,
        has_client=has_client,
    )


def _skip_path(path: Path) -> bool:
    ignored = {".venv", "venv", "node_modules", "__pycache__", ".git"}
    return any(part in ignored for part in path.parts)
