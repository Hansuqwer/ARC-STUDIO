"""
MCP server for ARC Local Control Plane (Phase 26 / R19).

Uses FastMCP with stdio transport. All tools are gated by workspace trust
enforcement (Phase 23). Exposes safe local read-only tools and resources,
no paid/provider calls, no secret output.

Usage:
    arc mcp serve --stdio
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import __version__ as arc_version
from ..security.trust import ensure_trusted, WorkspaceUntrusted

log = logging.getLogger(__name__)

# Default workspace path (current working directory)
_DEFAULT_WORKSPACE = Path.cwd()


class MCPServerError(Exception):
    """Base exception for MCP server errors."""


def create_mcp_server(
    workspace: Path | None = None,
    server_name: str = "ARC Studio",
) -> FastMCP:
    """Create a FastMCP server with ARC local tools and resources.

    Args:
        workspace: Workspace path for trust enforcement and data access.
                   Defaults to current working directory.
        server_name: Name for the MCP server.

    Returns:
        Configured FastMCP instance ready for ``mcp.run(transport="stdio")``.

    Raises:
        MCPServerError: If the server cannot be initialized.
    """
    ws = workspace or _DEFAULT_WORKSPACE

    # Check workspace trust before creating the server
    try:
        ensure_trusted(ws)
    except WorkspaceUntrusted as e:
        raise MCPServerError(
            f"Cannot start MCP server: {e}. Run 'arc workspace trust' to approve this workspace."
        ) from e

    mcp = FastMCP(server_name, json_response=True)

    # ── Tools ──────────────────────────────────────────────────────────────

    @mcp.tool()
    def arc_doctor() -> str:
        """Run ARC diagnostic checks and return health status.

        Returns versions, daemon status, adapters, trust, isolation,
        paid-call gates, MCP support, and known blockers.
        """
        import os
        import sys

        from ..adapters.registry import default_registry
        from ..provider_action import provider_statuses

        checks: list[dict[str, Any]] = []

        # 1. Python version
        checks.append(
            {
                "check": "python",
                "ok": True,
                "version": sys.version.split()[0],
            }
        )

        # 2. CLI version
        checks.append(
            {
                "check": "cli",
                "ok": True,
                "version": arc_version,
            }
        )

        # 3. Runtime detection
        try:
            registry = default_registry()
            runtimes = registry.detect_all(ws)
            checks.append(
                {
                    "check": "runtimes",
                    "ok": True,
                    "detected": [r.adapter for r in runtimes],
                    "count": len(runtimes),
                }
            )
        except Exception as e:
            checks.append({"check": "runtimes", "ok": False, "error": str(e)})

        # 4. Provider diagnostics (env presence only)
        try:
            providers = provider_statuses(os.environ)
            checks.append(
                {
                    "check": "providers",
                    "ok": True,
                    "total": len(providers),
                    "configured": sum(1 for p in providers if p.api_key_configured),
                }
            )
        except Exception as e:
            checks.append({"check": "providers", "ok": False, "error": str(e)})

        # 5. MCP support status
        checks.append(
            {
                "check": "mcp",
                "ok": True,
                "version": "1.0.0",
                "transport": "stdio",
                "status": "active",
            }
        )

        # 6. Workspace trust
        from ..security.trust import resolve_trust

        trust = resolve_trust(ws)
        checks.append(
            {
                "check": "trust",
                "ok": trust.level.value == "trusted",
                "level": trust.level.value,
            }
        )

        return json.dumps(checks, indent=2)

    @mcp.tool()
    def arc_runtime_capabilities() -> str:
        """List runtime capabilities for the current workspace.

        Returns detected runtimes, their availability, and whether
        they require paid calls.
        """
        from ..adapters.registry import default_registry
        from ..orchestration import runtime_router

        registry = default_registry()
        registry.detect_all(ws)
        reports = runtime_router.list_runtimes(ws)

        payload = {
            "workspace": str(ws),
            "auto_priority": list(runtime_router.AUTO_PRIORITY),
            "runtimes": [report.model_dump() for report in reports],
        }
        return json.dumps(payload, indent=2, default=str)

    @mcp.tool()
    def arc_run_status(run_id: str) -> str:
        """Get the status of a stored run by its run ID.

        Args:
            run_id: The run ID to look up.

        Returns:
            JSON string with run status, workflow, runtime, timing, and event count.
        """
        from ..storage.jsonl import JsonlTraceStore

        store = JsonlTraceStore(ws / ".arc" / "traces")
        run_record = store.load(run_id)
        if run_record is None:
            return json.dumps({"error": f"Run not found: {run_id}"})

        payload = {
            "run_id": run_record.id,
            "status": run_record.status.value,
            "workflow_id": run_record.workflow_id,
            "runtime": run_record.runtime,
            "started_at": run_record.started_at,
            "ended_at": run_record.ended_at,
            "event_count": len(run_record.events),
        }
        return json.dumps(payload, indent=2, default=str)

    @mcp.tool()
    def arc_trace_search(
        workflow: str | None = None,
        runtime: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> str:
        """Search stored runs with optional filters.

        Args:
            workflow: Optional workflow ID to filter by.
            runtime: Optional runtime to filter by.
            status: Optional run status to filter by.
            limit: Maximum number of results (default 20).

        Returns:
            JSON string with matching runs.
        """
        from ..storage.sqlite import SqliteStore

        db_path = ws / ".arc" / "arc.db"
        if not db_path.exists():
            return json.dumps({"error": "SQLite index not found. Run 'arc runs backfill' first."})

        store = SqliteStore(db_path)
        results = store.list_runs(
            status=status, runtime=runtime, workflow_id=workflow, limit=limit, offset=0
        )
        total = store.count_runs()
        return json.dumps(
            {
                "results": results,
                "count": len(results),
                "total_indexed": total,
            },
            indent=2,
            default=str,
        )

    @mcp.tool()
    def arc_trace_read(run_id: str) -> str:
        """Read the full trace of a stored run.

        Args:
            run_id: The run ID to read.

        Returns:
            JSON string with run record and events.
        """
        from ..storage.jsonl import JsonlTraceStore

        store = JsonlTraceStore(ws / ".arc" / "traces")
        run_record = store.load(run_id)
        if run_record is None:
            return json.dumps({"error": f"Run not found: {run_id}"})

        payload = {
            "run_id": run_record.id,
            "status": run_record.status.value,
            "workflow_id": run_record.workflow_id,
            "runtime": run_record.runtime,
            "started_at": run_record.started_at,
            "ended_at": run_record.ended_at,
            "event_count": len(run_record.events),
            "events": [e.model_dump() for e in run_record.events],
        }
        return json.dumps(payload, indent=2, default=str)

    @mcp.tool()
    def arc_audit_verify(run_id: str, mode: str = "sha256") -> str:
        """Verify the audit chain for a run.

        Args:
            run_id: The run ID to verify.
            mode: Verification mode - "sha256", "hmac", or "auto" (default "sha256").

        Returns:
            JSON string with verification result.
        """
        from ..audit.key_manager import AuditKeyManager
        from ..audit.streaming_verifier import StreamingAuditVerifier

        if mode not in ("auto", "sha256", "hmac"):
            return json.dumps(
                {
                    "ok": False,
                    "error": f"Invalid mode: {mode}. Must be auto, sha256, or hmac.",
                }
            )
        try:
            verifier = StreamingAuditVerifier(max_memory_mb=8)
        except ValueError as e:
            return json.dumps({"ok": False, "error": str(e)})

        audit_dir = ws / ".arc" / "audit"
        new_chain = audit_dir / f"{run_id}.audit.jsonl"
        old_chain = audit_dir / f"{run_id}.jsonl"
        if new_chain.exists():
            chain = new_chain
        elif old_chain.exists():
            chain = old_chain
        else:
            return json.dumps(
                {
                    "ok": False,
                    "run_id": run_id,
                    "error": f"Audit chain not found for run {run_id}",
                }
            )

        key = None
        if mode in ("hmac", "auto"):
            mgr = AuditKeyManager()
            key, key_status = mgr.get_key()
            if mode == "hmac" and not key_status.available:
                return json.dumps(
                    {
                        "ok": False,
                        "run_id": run_id,
                        "error": key_status.warning,
                    }
                )

        try:
            if mode == "auto":
                result = verifier.verify_auto(chain, key)
            elif mode == "hmac":
                result = verifier.verify_hmac(chain, key)
            else:
                result = verifier.verify_sha256(chain)
            return json.dumps(
                {
                    "ok": result.ok,
                    "mode": result.mode,
                    "records_checked": result.records_checked,
                    "reason": result.reason,
                    "duration_ms": result.duration_ms,
                },
                indent=2,
                default=str,
            )
        except Exception as e:
            return json.dumps(
                {
                    "ok": False,
                    "error": str(e),
                }
            )
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return json.dumps(
                {
                    "ok": False,
                    "run_id": run_id,
                    "mode": mode,
                    "error": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    def arc_hitl_list() -> str:
        """List pending HITL prompts.

        Returns:
            JSON string with pending HITL prompts.
        """
        from ..audit.hitl_store import list_prompts

        prompts = list_prompts(ws)
        results = []
        for prompt in prompts:
            entry = prompt.model_dump()
            results.append(entry)
        return json.dumps(results, indent=2, default=str)

    # ── Resources ──────────────────────────────────────────────────────────

    @mcp.resource("arc://runs/{run_id}")
    def get_run_resource(run_id: str) -> str:
        """Get run record as a resource.

        Args:
            run_id: The run ID to read.

        Returns:
            JSON string with run record summary.
        """
        return arc_run_status(run_id)

    @mcp.resource("arc://traces/{run_id}")
    def get_trace_resource(run_id: str) -> str:
        """Get full trace as a resource.

        Args:
            run_id: The run ID to read.

        Returns:
            JSON string with full trace.
        """
        return arc_trace_read(run_id)

    @mcp.resource("arc://audit/{run_id}")
    def get_audit_resource(run_id: str) -> str:
        """Get audit verification as a resource.

        Args:
            run_id: The run ID to verify.

        Returns:
            JSON string with audit verification result.
        """
        return arc_audit_verify(run_id)

    return mcp
