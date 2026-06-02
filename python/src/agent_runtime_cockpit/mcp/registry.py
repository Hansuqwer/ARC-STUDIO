"""MCP server registry — inventory, risk summary, and approval records.

Stores a shared server inventory under ~/.arc/mcp/servers.json and
workspace-local pins under .arc/mcp/pins/<server_id>.json (via manifests.py).

Usage:
    store = McpRegistryStore()
    store.register("my-server", transport="stdio", command=["python", "server.py"])
    store.approve_tool("my-server", "write_file", reason="explicitly reviewed")
    info = store.get("my-server")
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import BaseModel, Field


_SHARED_DIR = Path.home() / ".arc" / "mcp"


class McpServerRecord(BaseModel):
    """Persistent inventory record for one MCP server."""

    server_id: str
    transport: str = "stdio"  # "stdio" | "http" (future)
    command: list[str] = Field(default_factory=list)
    manifest_hash: str | None = None
    approved_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    last_seen: float = Field(default_factory=time.time)
    notes: str = ""


class McpRegistryStore:
    """Inventory of known MCP servers with approval records."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (_SHARED_DIR / "servers.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, McpServerRecord]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text())
            return {k: McpServerRecord.model_validate(v) for k, v in raw.items()}
        except Exception:
            return {}

    def _save(self, records: dict[str, McpServerRecord]) -> None:
        self._path.write_text(json.dumps({k: v.model_dump() for k, v in records.items()}, indent=2))

    def register(
        self,
        server_id: str,
        transport: str = "stdio",
        command: list[str] | None = None,
        manifest_hash: str | None = None,
    ) -> McpServerRecord:
        """Add or update a server record."""
        records = self._load()
        existing = records.get(server_id)
        record = McpServerRecord(
            server_id=server_id,
            transport=transport,
            command=command or (existing.command if existing else []),
            manifest_hash=manifest_hash or (existing.manifest_hash if existing else None),
            approved_tools=existing.approved_tools if existing else [],
            blocked_tools=existing.blocked_tools if existing else [],
            last_seen=time.time(),
        )
        records[server_id] = record
        self._save(records)
        return record

    def approve_tool(self, server_id: str, tool_name: str, reason: str = "") -> None:
        """Mark a tool as explicitly approved for a server."""
        records = self._load()
        if server_id not in records:
            records[server_id] = McpServerRecord(server_id=server_id)
        r = records[server_id]
        if tool_name not in r.approved_tools:
            r.approved_tools.append(tool_name)
        if tool_name in r.blocked_tools:
            r.blocked_tools.remove(tool_name)
        if reason:
            r.notes = (r.notes + f"; approved {tool_name}: {reason}").strip("; ")
        self._save(records)

    def block_tool(self, server_id: str, tool_name: str, reason: str = "") -> None:
        """Mark a tool as blocked for a server."""
        records = self._load()
        if server_id not in records:
            records[server_id] = McpServerRecord(server_id=server_id)
        r = records[server_id]
        if tool_name not in r.blocked_tools:
            r.blocked_tools.append(tool_name)
        if tool_name in r.approved_tools:
            r.approved_tools.remove(tool_name)
        if reason:
            r.notes = (r.notes + f"; blocked {tool_name}: {reason}").strip("; ")
        self._save(records)

    def get(self, server_id: str) -> McpServerRecord | None:
        return self._load().get(server_id)

    def list_servers(self) -> list[McpServerRecord]:
        return list(self._load().values())

    def is_tool_approved(self, server_id: str, tool_name: str) -> bool:
        r = self.get(server_id)
        return bool(r and tool_name in r.approved_tools)

    def is_tool_blocked(self, server_id: str, tool_name: str) -> bool:
        r = self.get(server_id)
        return bool(r and tool_name in r.blocked_tools)
