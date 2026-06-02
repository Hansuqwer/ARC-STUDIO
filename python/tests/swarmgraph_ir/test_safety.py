"""Safety checklist — prove the compiler is a pure analysis layer.

- no workflow execution / tool invocation / model call
- no network exposure
- no MCP server execution
- secrets redacted in emitted IR
- deterministic, CI-safe
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

from agent_runtime_cockpit.protocol.schemas import (
    NodeType,
    WorkflowInfo,
    WorkflowNode,
)
from agent_runtime_cockpit.swarmgraph_ir import compile_workflow, to_json

PKG = Path(__file__).resolve().parents[2] / "src" / "agent_runtime_cockpit" / "swarmgraph_ir"

# Symbols that would indicate execution / network / process launching in the core.
_FORBIDDEN = [
    r"\bsubprocess\b",
    r"\bsocket\b",
    r"\baiohttp\b",
    r"\brequests\b",
    r"\bos\.system\b",
    r"\brun_workflow\b",
    r"\bstream_events\b",
    r"\basyncio\.run\b",
]


def _source_files() -> list[Path]:
    return [p for p in PKG.rglob("*.py")]


def _code_only(text: str) -> str:
    """Return only code tokens (names/ops), excluding comments & string/docstrings."""
    out: list[str] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type in (tokenize.NAME, tokenize.OP):
                out.append(tok.string)
    except tokenize.TokenError:
        return ""
    return " ".join(out)


def test_no_execution_or_network_symbols_in_core() -> None:
    # Scan only executable code (not comments/docstrings) so prose like
    # "opens a socket" in a docstring does not trigger a false positive.
    pattern = re.compile("|".join(_FORBIDDEN))
    offenders = []
    for f in _source_files():
        if pattern.search(_code_only(f.read_text())):
            offenders.append(f.name)
    assert offenders == [], f"forbidden execution/network symbols found in: {offenders}"


def test_secrets_are_redacted_in_emitted_ir() -> None:
    wf = WorkflowInfo(
        id="wf",
        name="leaky",
        runtime="native",
        nodes=[
            WorkflowNode(
                id="n",
                label="node",
                type=NodeType.TOOL,
                metadata={"note": "api key sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"},
            )
        ],
        entry_points=["n"],
    )
    res = compile_workflow(wf, use_sdk_risk=False)
    out = to_json(res.graph)
    assert "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345" not in out


def test_compile_runs_offline_without_sdk_risk() -> None:
    # use_sdk_risk=False must never import/call the SDK and must still succeed.
    wf = WorkflowInfo(
        id="wf",
        name="x",
        runtime="native",
        nodes=[WorkflowNode(id="a", label="a", type=NodeType.AGENT)],
        entry_points=["a"],
    )
    res = compile_workflow(wf, use_sdk_risk=False)
    assert res.ok
    assert res.graph.risk.source == "heuristic"  # SDK never touched


def test_enrich_mcp_does_not_launch_server(monkeypatch, tmp_path) -> None:
    # If anything tried to start an MCP session it would import mcp.session; make
    # that explode and prove enrichment still works from local files only.
    import agent_runtime_cockpit.mcp.session as session

    def _boom(*a, **k):  # noqa: ANN001, ANN002, ANN003
        raise AssertionError("MCP server must not be launched during IR enrichment")

    for attr in dir(session):
        obj = getattr(session, attr)
        if callable(obj) and attr.lower().startswith(("connect", "launch", "start", "spawn")):
            monkeypatch.setattr(session, attr, _boom, raising=False)

    wf = WorkflowInfo(
        id="wf",
        name="mcp",
        runtime="native",
        nodes=[
            WorkflowNode(
                id="m",
                label="fs mcp",
                type=NodeType.TOOL,
                metadata={"is_mcp": True, "mcp_server_id": "fs", "mcp_tool_name": "write"},
            )
        ],
        entry_points=["m"],
    )
    res = compile_workflow(wf, workspace=str(tmp_path), use_sdk_risk=False, enrich_mcp=True)
    assert res.ok
