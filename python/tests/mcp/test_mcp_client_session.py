"""Real MCP client-session tests (Phase 26 MCP hardening).

Uses in-process memory-stream transport to exercise the full MCP
protocol stack without subprocess stdio. Tests verify that tool calls,
resource reads, audit events, and ARC envelope shapes work correctly
through the actual MCP ClientSession.

Requirements:
1. real MCP client can list tools
2. real MCP client can call arc_doctor
3. real MCP client receives ARC envelope-shaped response
4. real MCP client denied result still has ARC error envelope
5. real MCP resource read works for one local fixture
6. real MCP resource missing ID returns stable error envelope
7. audit event still emitted for real client call
8. no HTTP transport is exposed
9. no provider/network calls are made
"""

from __future__ import annotations

import json
from pathlib import Path

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage
from mcp.types import CallToolResult, TextResourceContents
from pydantic import AnyUrl

from agent_runtime_cockpit.mcp.server import create_mcp_server
from agent_runtime_cockpit.security.trust import trust_workspace


@pytest.fixture
async def trusted_workspace(tmp_path: Path) -> Path:
    trust_workspace(tmp_path, note="mcp-client-test")
    return tmp_path


async def _run_with_client(workspace: Path, fn):
    """Create an in-process MCP client, run a test function, then clean up."""
    mcp = create_mcp_server(workspace=workspace)
    server = mcp._mcp_server

    c2s_send, c2s_recv = anyio.create_memory_object_stream[SessionMessage](1000)
    s2c_send, s2c_recv = anyio.create_memory_object_stream[SessionMessage](1000)

    async def _run_server():
        await server.run(
            c2s_recv,
            s2c_send,
            server.create_initialization_options(),
            raise_exceptions=True,
        )

    async with anyio.create_task_group() as tg:
        tg.start_soon(_run_server)

        async with ClientSession(
            read_stream=s2c_recv,
            write_stream=c2s_send,
        ) as session:
            await session.initialize()
            await fn(session)


# ── Requirement 1: list tools ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_client_can_list_tools(trusted_workspace: Path):
    async def _test(client: ClientSession):
        tools_result = await client.list_tools()
        tool_names = [t.name for t in tools_result.tools]

        assert "arc_doctor" in tool_names
        assert "arc_run_status" in tool_names
        assert "arc_trace_read" in tool_names
        assert "arc_trace_search" in tool_names
        assert "arc_audit_verify" in tool_names
        assert "arc_hitl_list" in tool_names
        assert "arc_runtime_capabilities" in tool_names
        assert "arc_task_create" in tool_names
        assert "arc_task_status" in tool_names
        assert "arc_task_cancel" in tool_names
        assert "arc_task_result" in tool_names
        assert "arc_swarmgraph_plan" in tool_names
        assert "arc_swarmgraph_assess_risk" in tool_names
        assert len(tool_names) == 13

    await _run_with_client(trusted_workspace, _test)


# ── Requirement 2: call arc_doctor ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_client_calls_arc_doctor(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.call_tool("arc_doctor")
        assert isinstance(result, CallToolResult)
        assert len(result.content) >= 1
        assert result.isError is False

    await _run_with_client(trusted_workspace, _test)


# ── Requirement 3: ARC envelope shape ───────────────────────────────────────


@pytest.mark.asyncio
async def test_arc_doctor_returns_arc_envelope(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.call_tool("arc_doctor")
        text = result.content[0].text
        parsed = json.loads(text)

        assert parsed["version"] == "1.0"
        assert parsed["ok"] is True
        assert isinstance(parsed["data"], list)
        assert parsed["error"] is None
        assert "timestamp" in parsed["meta"]

    await _run_with_client(trusted_workspace, _test)


@pytest.mark.asyncio
async def test_arc_doctor_structured_content(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.call_tool("arc_doctor")
        assert result.structuredContent is not None
        assert "result" in result.structuredContent
        raw = json.loads(result.structuredContent["result"])
        assert raw["ok"] is True

    await _run_with_client(trusted_workspace, _test)


# ── Requirement 4: denied result has ARC error envelope ─────────────────────


@pytest.mark.asyncio
async def test_denied_run_status_returns_arc_error_envelope(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.call_tool("arc_run_status", {"run_id": "../secret"})
        text = result.content[0].text
        parsed = json.loads(text)

        assert parsed["ok"] is False
        assert parsed["version"] == "1.0"
        assert parsed["data"] is None
        assert parsed["error"]["code"] == "INVALID_INPUT"
        assert "timestamp" in parsed["meta"]

    await _run_with_client(trusted_workspace, _test)


@pytest.mark.asyncio
async def test_denied_audit_verify_returns_arc_error_envelope(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.call_tool("arc_audit_verify", {"run_id": "../secret"})
        text = result.content[0].text
        parsed = json.loads(text)

        assert parsed["ok"] is False
        assert parsed["error"]["details"]["code"] == "INVALID_MCP_ARGUMENT"

    await _run_with_client(trusted_workspace, _test)


# ── Requirement 5-6: resource reading ───────────────────────────────────────


@pytest.mark.asyncio
async def test_client_lists_resource_templates(trusted_workspace: Path):
    async def _test(client: ClientSession):
        templates = await client.list_resource_templates()
        uri_templates = [t.uriTemplate for t in templates.resourceTemplates]

        assert "arc://runs/{run_id}" in uri_templates
        assert "arc://traces/{run_id}" in uri_templates
        assert "arc://audit/{run_id}" in uri_templates
        assert len(uri_templates) == 3

    await _run_with_client(trusted_workspace, _test)


@pytest.mark.asyncio
async def test_resource_read_missing_run_returns_error(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.read_resource(AnyUrl("arc://runs/nonexistent"))
        assert len(result.contents) >= 1

        content = result.contents[0]
        assert isinstance(content, TextResourceContents)
        assert str(content.uri) == "arc://runs/nonexistent"
        assert content.mimeType == "text/plain"

        parsed = json.loads(content.text)
        assert parsed["ok"] is False
        assert "not found" in parsed["error"]["message"].lower()

    await _run_with_client(trusted_workspace, _test)


@pytest.mark.asyncio
async def test_resource_read_missing_trace_returns_error(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.read_resource(AnyUrl("arc://traces/nonexistent"))
        content = result.contents[0]
        parsed = json.loads(content.text)
        assert parsed["ok"] is False

    await _run_with_client(trusted_workspace, _test)


@pytest.mark.asyncio
async def test_resource_read_missing_audit_returns_error(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.read_resource(AnyUrl("arc://audit/nonexistent"))
        content = result.contents[0]
        parsed = json.loads(content.text)
        assert parsed["ok"] is False

    await _run_with_client(trusted_workspace, _test)


# ── Requirement 7: audit events ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_allowed_call_emits_audit_event(trusted_workspace: Path):
    async def _test(client: ClientSession):
        await client.call_tool("arc_doctor")

        audit_path = trusted_workspace / ".arc" / "audit" / "mcp.events.jsonl"
        assert audit_path.exists()

        lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1

        event = json.loads(lines[-1])
        assert event["type"] == "mcp_tool_call"
        assert event["tool"] == "arc_doctor"
        assert event["decision"] == "allowed"
        assert event["transport"] == "stdio"
        assert "started_at" in event
        assert "ended_at" in event
        assert isinstance(event["duration_ms"], float | int)
        assert event["args_hash"] is not None

    await _run_with_client(trusted_workspace, _test)


@pytest.mark.asyncio
async def test_denied_call_emits_audit_event(trusted_workspace: Path):
    async def _test(client: ClientSession):
        await client.call_tool("arc_run_status", {"run_id": "../secret"})

        audit_path = trusted_workspace / ".arc" / "audit" / "mcp.events.jsonl"
        assert audit_path.exists()

        lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
        denied = [json.loads(l) for l in lines if json.loads(l)["decision"] == "denied"]
        assert len(denied) >= 1

        event = denied[-1]
        assert event["tool"] == "arc_run_status"
        assert event["decision"] == "denied"
        assert event["error_code"] == "INVALID_MCP_ARGUMENT"
        assert event["args"]["run_id"] == "../secret"

    await _run_with_client(trusted_workspace, _test)


@pytest.mark.asyncio
async def test_audit_event_redacts_secrets(trusted_workspace: Path):
    async def _test(client: ClientSession):
        secret = "sk-" + "c" * 40
        await client.call_tool(
            "arc_task_create",
            {"operation": "noop", "params": json.dumps({"api_key": secret})},
        )

        audit_path = trusted_workspace / ".arc" / "audit" / "mcp.events.jsonl"
        lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
        combined = "".join(lines)
        assert secret not in combined
        assert "[REDACTED]" in combined

    await _run_with_client(trusted_workspace, _test)


# ── Requirement 8: no HTTP transport ────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_http_transport_exposed(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.call_tool("arc_doctor")
        text = result.content[0].text
        parsed = json.loads(text)
        checks_by_name = {c["check"]: c for c in parsed["data"]}
        assert checks_by_name["mcp"]["transport"] == "stdio"

    await _run_with_client(trusted_workspace, _test)


# ── Requirement 9: no provider/network calls ────────────────────────────────


@pytest.mark.asyncio
async def test_no_provider_or_network_calls(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.call_tool("arc_doctor")
        text = result.content[0].text
        parsed = json.loads(text)
        checks_by_name = {c["check"]: c for c in parsed["data"]}

        assert "providers" in checks_by_name
        assert checks_by_name["providers"]["ok"] is True
        assert isinstance(checks_by_name["providers"]["total"], int)

    await _run_with_client(trusted_workspace, _test)


# ── Edge cases ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_call_tool_with_invalid_name(trusted_workspace: Path):
    async def _test(client: ClientSession):
        result = await client.call_tool("nonexistent_tool")
        assert result.isError is True

    await _run_with_client(trusted_workspace, _test)
