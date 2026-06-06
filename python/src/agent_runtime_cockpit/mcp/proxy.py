"""MCP stdio<->stdio proxy with per-call risk gating.

Spawns upstream MCP server as asyncio subprocess. Intercepts tool_call
requests, scores risk, and applies policy before forwarding.

1MB output cap per response. Uses asyncio.subprocess (not raw Popen).
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from .sandbox import McpCallDecision, McpDecision, McpPolicy, decide_call, persist_decision
from .manifests import ManifestStore

log = logging.getLogger(__name__)

_MAX_OUTPUT_BYTES = 1_048_576  # 1 MB

_SECRET_KEY_PATTERNS = (
    "_API_KEY",
    "_TOKEN",
    "_SECRET",
    "_PASSWORD",
    "_CREDENTIAL",
    "OPENAI_",
    "ANTHROPIC_",
    "AWS_",
    "GOOGLE_API",
)


def _sanitise_env(env: dict[str, str] | None) -> dict[str, str] | None:
    """Strip secret env vars before passing to upstream subprocess."""
    if env is None:
        return None
    clean = {}
    for k, v in env.items():
        if any(pat in k.upper() for pat in _SECRET_KEY_PATTERNS):
            log.debug("mcp.proxy: stripped secret key %s from upstream env", k)
        else:
            clean[k] = v
    return clean


class McpProxy:
    """Async stdio MCP proxy with risk gating."""

    def __init__(
        self,
        upstream_cmd: list[str],
        *,
        workspace: Path | None = None,
        policy: McpPolicy = McpPolicy.STRICT,
        env: dict[str, str] | None = None,
    ) -> None:
        self._cmd = upstream_cmd
        self._workspace = workspace or Path.cwd()
        self._policy = policy
        self._env = env
        self._proc: asyncio.subprocess.Process | None = None
        self._manifest_store = ManifestStore(workspace=self._workspace)
        self._decisions: list[McpCallDecision] = []

    async def start(self) -> None:
        """Start the upstream MCP server subprocess."""
        self._proc = await asyncio.create_subprocess_exec(
            *self._cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_sanitise_env(self._env),
            start_new_session=True,
        )

    async def stop(self) -> None:
        """Terminate upstream subprocess."""
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._proc.kill()
                await self._proc.wait()

    async def send_raw(self, msg: bytes) -> bytes | None:
        """Send raw JSONRPC message to upstream and read response."""
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            return None
        self._proc.stdin.write(msg + b"\n")
        await self._proc.stdin.drain()
        line = await asyncio.wait_for(self._proc.stdout.readline(), timeout=30.0)
        if len(line) > _MAX_OUTPUT_BYTES:
            line = line[:_MAX_OUTPUT_BYTES]
        return line

    async def handle_message(self, raw: bytes) -> bytes:
        """Intercept and gate tool_call requests."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            # Pass through unparseable messages
            resp = await self.send_raw(raw)
            return resp or b""

        method = msg.get("method", "")

        # Intercept tools/call
        if method == "tools/call":
            return await self._handle_tool_call(msg, raw)

        # Pass through everything else
        resp = await self.send_raw(raw)
        return resp or b""

    async def _handle_tool_call(self, msg: dict[str, Any], raw: bytes) -> bytes:
        """Apply risk gate to a tools/call request."""
        params = msg.get("params", {})
        tool_name = params.get("name", "unknown")
        arguments = params.get("arguments")
        server_id = "upstream"

        # Get manifest risk for tool
        manifest = self._manifest_store.load(server_id)
        manifest_risk = "low"
        if manifest:
            for tr in manifest.tool_risks:
                if tr.tool_name == tool_name:
                    manifest_risk = tr.risk_level
                    break

        decision = decide_call(
            server_id=server_id,
            tool_name=tool_name,
            arguments=arguments,
            manifest_risk=manifest_risk,
            policy=self._policy,
        )
        self._decisions.append(decision)
        persist_decision(self._workspace, decision)

        if decision.decision == McpDecision.DENY:
            # Return JSONRPC error
            error_resp = {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "error": {
                    "code": -32600,
                    "message": f"Denied by ARC risk gate: {decision.reason}",
                },
            }
            return json.dumps(error_resp).encode("utf-8")

        # Allow or warn: forward to upstream
        resp = await self.send_raw(raw)
        return resp or b""

    @property
    def decisions(self) -> list[McpCallDecision]:
        return list(self._decisions)


async def run_proxy(
    upstream_cmd: list[str],
    *,
    workspace: Path | None = None,
    policy: McpPolicy = McpPolicy.STRICT,
    env: dict[str, str] | None = None,
    stdin: asyncio.StreamReader | None = None,
    stdout: asyncio.StreamWriter | None = None,
) -> None:
    """Run the proxy loop: read from stdin, gate, forward, write to stdout."""
    proxy = McpProxy(upstream_cmd, workspace=workspace, policy=policy, env=env)
    await proxy.start()

    reader = stdin or asyncio.StreamReader()
    writer = stdout

    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            resp = await proxy.handle_message(line.rstrip(b"\n"))
            if writer:
                writer.write(resp + b"\n")
                await writer.drain()
    finally:
        await proxy.stop()
