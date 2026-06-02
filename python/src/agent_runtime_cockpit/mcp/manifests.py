"""MCP manifest pinning and drift detection.

Stores a content hash of each MCP server's tool manifest so that unexpected
changes are surfaced before execution.  All operations are read-only and local;
no network calls are made here.

Usage:
    from agent_runtime_cockpit.mcp.manifests import ManifestStore
    store = ManifestStore(workspace=Path.cwd())
    store.pin("my-server", tools)         # record current manifest
    drift = store.check_drift("my-server", tools)  # detect changes
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class McpToolRisk(BaseModel):
    """Risk classification for a single MCP tool."""

    tool_name: str
    can_write: bool = False
    can_network: bool = False
    can_read_secrets: bool = False
    accesses_outside_workspace: bool = False
    risk_level: str = "low"  # "low" | "medium" | "high"

    @classmethod
    def from_tool_meta(cls, name: str, meta: dict[str, Any]) -> "McpToolRisk":
        desc = (meta.get("description") or "").lower()
        schema = json.dumps(meta.get("inputSchema") or {}).lower()
        can_write = any(
            kw in desc + schema for kw in ("write", "create", "delete", "modify", "edit")
        )
        can_network = any(
            kw in desc + schema for kw in ("http", "url", "fetch", "request", "network")
        )
        can_read_secrets = any(
            kw in desc + schema for kw in ("secret", "password", "credential", "token", "key")
        )
        accesses_outside_workspace = any(
            kw in desc for kw in ("system", "root", "absolute", "/etc", "/usr")
        )
        level = "low"
        if can_write or can_read_secrets:
            level = "high"
        elif can_network or accesses_outside_workspace:
            level = "medium"
        return cls(
            tool_name=name,
            can_write=can_write,
            can_network=can_network,
            can_read_secrets=can_read_secrets,
            accesses_outside_workspace=accesses_outside_workspace,
            risk_level=level,
        )


class McpServerManifest(BaseModel):
    """Pinned snapshot of an MCP server's tool list."""

    server_id: str
    manifest_hash: str
    pinned_at: float = Field(default_factory=time.time)
    tool_names: list[str] = Field(default_factory=list)
    tool_risks: list[McpToolRisk] = Field(default_factory=list)

    @property
    def has_high_risk_tools(self) -> bool:
        return any(t.risk_level == "high" for t in self.tool_risks)

    @property
    def high_risk_tool_names(self) -> list[str]:
        return [t.tool_name for t in self.tool_risks if t.risk_level == "high"]


def _hash_tools(tools: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        sorted(tools, key=lambda t: t.get("name", "")), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _build_manifest(server_id: str, tools: list[dict[str, Any]]) -> McpServerManifest:
    risks = [McpToolRisk.from_tool_meta(t.get("name", ""), t) for t in tools]
    return McpServerManifest(
        server_id=server_id,
        manifest_hash=_hash_tools(tools),
        tool_names=[t.get("name", "") for t in tools],
        tool_risks=risks,
    )


class ManifestStore:
    """Persist and compare MCP server manifest pins.

    Pins are stored under: <workspace>/.arc/mcp/pins/<server_id>.json
    """

    def __init__(self, workspace: Path | None = None) -> None:
        self._root = (workspace or Path.cwd()) / ".arc" / "mcp" / "pins"
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, server_id: str) -> Path:
        safe = server_id.replace("/", "_").replace("..", "_")
        return self._root / f"{safe}.json"

    def pin(self, server_id: str, tools: list[dict[str, Any]]) -> McpServerManifest:
        """Record the current tool manifest for a server."""
        manifest = _build_manifest(server_id, tools)
        self._path(server_id).write_text(manifest.model_dump_json(indent=2))
        return manifest

    def load(self, server_id: str) -> McpServerManifest | None:
        p = self._path(server_id)
        if not p.exists():
            return None
        try:
            return McpServerManifest.model_validate_json(p.read_text())
        except Exception:
            return None

    def check_drift(self, server_id: str, current_tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Compare current tools against the pinned manifest.

        Returns a drift report: {'drifted': bool, 'pinned_hash': ..., 'current_hash': ...,
        'added': [...], 'removed': [...]}.
        """
        pinned = self.load(server_id)
        current_hash = _hash_tools(current_tools)
        current_names = {t.get("name", "") for t in current_tools}
        if pinned is None:
            return {
                "drifted": False,
                "pinned": False,
                "current_hash": current_hash,
                "message": "No pin on file; run 'arc mcp pin' to record.",
            }
        pinned_names = set(pinned.tool_names)
        added = list(current_names - pinned_names)
        removed = list(pinned_names - current_names)
        drifted = pinned.manifest_hash != current_hash
        return {
            "drifted": drifted,
            "pinned": True,
            "pinned_hash": pinned.manifest_hash,
            "current_hash": current_hash,
            "added": added,
            "removed": removed,
            "message": "Manifest drift detected." if drifted else "Manifest matches pin.",
        }

    def list_servers(self) -> list[str]:
        return [p.stem for p in sorted(self._root.glob("*.json"))]
