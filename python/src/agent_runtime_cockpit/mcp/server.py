"""MCP server for ARC Local Control Plane (Phase 26 / R19).

Uses FastMCP with stdio transport. All tools are gated by workspace trust
enforcement (Phase 23). Exposes safe local read-only tools and resources,
no paid/provider calls, no secret output.

Usage:
    arc mcp serve --stdio
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from .. import __version__ as arc_version
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from .sandbox import (
    McpDecision,
    McpPolicy,
    decide_call,
    next_decision_sequence,
    persist_decision,
    persist_decision_event,
    to_call_decision_event,
)
from ..security.redaction import Redactor
from ..security.trust import WorkspaceUntrusted, ensure_trusted

log = logging.getLogger(__name__)

# Default workspace path (current working directory)
_DEFAULT_WORKSPACE = Path.cwd()
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_MAX_MCP_OUTPUT_BYTES = 1_048_576
_DEFAULT_TRACE_LIMIT = 500
_MAX_TRACE_LIMIT = 2_000

# R-SEC1: Explicit tool risk classification for ARC's 13 MCP tools.
# LOW: read-only; no external calls; no budget consumption.
# MEDIUM: state-mutating or cancellation; no provider calls.
# HIGH: spawns agent run; may invoke provider APIs; consumes budget.
TOOL_RISK_LEVELS: dict[str, str] = {
    "arc_doctor": "LOW",
    "arc_runtime_capabilities": "LOW",
    "arc_run_status": "LOW",
    "arc_trace_search": "LOW",
    "arc_trace_read": "LOW",
    "arc_audit_verify": "LOW",
    "arc_hitl_list": "LOW",
    "arc_task_status": "LOW",
    "arc_task_result": "LOW",
    "arc_swarmgraph_plan": "LOW",
    "arc_swarmgraph_assess_risk": "LOW",
    "arc_task_cancel": "MEDIUM",
    "arc_run_start": "HIGH",
}


class MCPServerError(Exception):
    """Base exception for MCP server errors."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _redacted_json_envelope(
    data: Any,
    *,
    workspace: Path,
    max_bytes: int = _MAX_MCP_OUTPUT_BYTES,
) -> tuple[str, bool]:
    redacted = Redactor().redact_dict(data)
    envelope = ok(redacted, workspace=str(workspace)).model_dump(mode="json")
    text = json.dumps(envelope, indent=2, default=str)
    if len(text.encode("utf-8")) <= max_bytes:
        return text, False
    truncated = {
        "truncated": True,
        "truncated_reason": "mcp_output_cap_exceeded",
        "max_bytes": max_bytes,
    }
    return json.dumps(
        ok(truncated, workspace=str(workspace)).model_dump(mode="json"), indent=2
    ), True


def _error_json(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> str:
    return json.dumps(err(code, message, details).model_dump(mode="json"), indent=2)


def _redacted_args(args: dict[str, Any]) -> dict[str, Any]:
    return Redactor().redact_dict(args)


def _args_hash(args: dict[str, Any]) -> str:
    raw = json.dumps(_redacted_args(args), sort_keys=True, default=str, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def _persist_mcp_audit_event(workspace: Path, event: dict[str, Any]) -> None:
    """Best-effort MCP audit JSONL writer; never fails a tool call."""
    try:
        audit_dir = workspace / ".arc" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        path = audit_dir / "mcp.events.jsonl"
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(event, sort_keys=True, separators=(",", ":"), default=str) + "\n")
    except Exception:
        log.exception("failed to persist MCP audit event")


def _safe_id(value: str, field: str) -> str:
    if not _SAFE_ID_RE.fullmatch(value):
        raise ValueError(f"invalid {field}: must match {_SAFE_ID_RE.pattern}")
    return value


def _resolve_workspace_child(base: Path, filename: str) -> Path:
    root = base.resolve()
    path = (base / filename).resolve()
    if root != path and root not in path.parents:
        raise ValueError("path escapes workspace data directory")
    return path


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

    def _trusted() -> None:
        ensure_trusted(ws)

    def _tool_result(
        tool_name: str, callback: Callable[[], Any], args: dict[str, Any] | None = None
    ) -> str:
        started = time.perf_counter()
        started_at = _utc_now()
        audit_args = args or {}
        base_audit = {
            "type": "mcp_tool_call",
            "tool": tool_name,
            "workspace": str(ws),
            "transport": "stdio",
            "args": _redacted_args(audit_args),
            "args_hash": _args_hash(audit_args),
            "started_at": started_at,
        }
        try:
            _trusted()
            # D-02: Outbound per-call risk gate (LLM-free; deterministic).
            try:
                policy_value = os.environ.get("ARC_MCP_POLICY", McpPolicy.STRICT.value)
                policy = McpPolicy(policy_value)
            except ValueError:
                policy = McpPolicy.STRICT
            mcp_decision = decide_call(
                server_id="arc-local",
                tool_name=tool_name,
                arguments=audit_args,
                manifest_risk="low",
                roots_violation=False,
                drift=None,
                policy=policy,
            )
            try:
                persist_decision(ws, mcp_decision)
                # CR-043: also emit the typed MCP_CALL_DECISION run-event (was never written).
                persist_decision_event(
                    ws,
                    to_call_decision_event(
                        mcp_decision,
                        run_id="mcp-stdio",
                        sequence=next_decision_sequence(),
                        timestamp=base_audit.get("started_at"),
                        correlation_id=base_audit.get("args_hash"),
                    ),
                )
            except Exception:  # pragma: no cover
                pass
            if mcp_decision.decision == McpDecision.DENY:
                _persist_mcp_audit_event(
                    ws,
                    {
                        **base_audit,
                        "decision": "denied",
                        "error_code": "MCP_RISK_DENIED",
                        "error_reason": mcp_decision.reason,
                        "risk_level": mcp_decision.risk_score.level.value,
                        "policy": policy.value,
                        "ended_at": _utc_now(),
                        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                        "truncated": False,
                    },
                )
                return _error_json(
                    ArcErrorCode.PERMISSION_DENIED,
                    f"MCP outbound call denied: {mcp_decision.reason}",
                    details={
                        "tool": tool_name,
                        "code": "MCP_RISK_DENIED",
                        "risk": mcp_decision.risk_score.level.value,
                        "policy": policy.value,
                    },
                )
            text, truncated = _redacted_json_envelope(callback(), workspace=ws)
            _persist_mcp_audit_event(
                ws,
                {
                    **base_audit,
                    "decision": "allowed",
                    "risk_level": mcp_decision.risk_score.level.value,
                    "policy": policy.value,
                    "ended_at": _utc_now(),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "truncated": truncated,
                },
            )
            return text
        except WorkspaceUntrusted as e:
            message = f"MCP tool blocked: {e}"
            _persist_mcp_audit_event(
                ws,
                {
                    **base_audit,
                    "decision": "denied",
                    "error_code": "WORKSPACE_UNTRUSTED",
                    "error_reason": message,
                    "ended_at": _utc_now(),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "truncated": False,
                },
            )
            return _error_json(
                ArcErrorCode.PERMISSION_DENIED,
                message,
                details={"tool": tool_name, "code": "WORKSPACE_UNTRUSTED"},
            )
        except ValueError as e:
            _persist_mcp_audit_event(
                ws,
                {
                    **base_audit,
                    "decision": "denied",
                    "error_code": "INVALID_MCP_ARGUMENT",
                    "error_reason": str(e),
                    "ended_at": _utc_now(),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "truncated": False,
                },
            )
            return _error_json(
                ArcErrorCode.INVALID_INPUT,
                str(e),
                details={"tool": tool_name, "code": "INVALID_MCP_ARGUMENT"},
            )
        except Exception as e:
            log.exception("MCP tool failed: %s", tool_name)
            _persist_mcp_audit_event(
                ws,
                {
                    **base_audit,
                    "decision": "error",
                    "error_code": "MCP_TOOL_FAILED",
                    "error_reason": str(e),
                    "ended_at": _utc_now(),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "truncated": False,
                },
            )
            return _error_json(
                ArcErrorCode.INTERNAL_ERROR,
                str(e),
                details={"tool": tool_name, "code": "MCP_TOOL_FAILED"},
            )

    # ── Tools ──────────────────────────────────────────────────────────────

    @mcp.tool()
    def arc_doctor() -> str:
        """Run ARC diagnostic checks and return health status.

        Returns versions, daemon status, adapters, trust, isolation,
        paid-call gates, MCP support, and known blockers.
        """

        def run() -> list[dict[str, Any]]:
            import os
            import sys

            from ..adapters.registry import default_registry
            from ..provider_action import provider_statuses

            checks: list[dict[str, Any]] = []

            checks.append({"check": "python", "ok": True, "version": sys.version.split()[0]})

            checks.append({"check": "cli", "ok": True, "version": arc_version})

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

            checks.append(
                {
                    "check": "mcp",
                    "ok": True,
                    "version": "1.0.0",
                    "transport": "stdio",
                    "status": "active",
                }
            )

            from ..security.trust import resolve_trust

            trust = resolve_trust(ws)
            checks.append(
                {"check": "trust", "ok": trust.level.value == "trusted", "level": trust.level.value}
            )
            return checks

        return _tool_result("arc_doctor", run, {})

    @mcp.tool()
    def arc_runtime_capabilities() -> str:
        """List runtime capabilities for the current workspace.

        Returns detected runtimes, their availability, and whether
        they require paid calls.
        """

        def run() -> dict[str, Any]:
            from ..adapters.registry import default_registry
            from ..orchestration import runtime_router

            registry = default_registry()
            registry.detect_all(ws)
            reports = runtime_router.list_runtimes(ws)

            return {
                "workspace": str(ws),
                "auto_priority": list(runtime_router.AUTO_PRIORITY),
                "runtimes": [report.model_dump() for report in reports],
            }

        return _tool_result("arc_runtime_capabilities", run, {})

    @mcp.tool()
    def arc_run_status(run_id: str) -> str:
        """Get the status of a stored run by its run ID.

        Args:
            run_id: The run ID to look up.

        Returns:
            JSON string with run status, workflow, runtime, timing, and event count.

        """

        def run() -> dict[str, Any]:
            run = _safe_id(run_id, "run_id")
            trace_dir = ws / ".arc" / "traces"
            _resolve_workspace_child(trace_dir, f"{run}.jsonl")
            from ..storage.jsonl import JsonlTraceStore

            store = JsonlTraceStore(trace_dir)
            run_record = store.load(run)
            if run_record is None:
                raise ValueError(f"Run not found: {run}")

            return {
                "run_id": run_record.id,
                "status": run_record.status.value,
                "workflow_id": run_record.workflow_id,
                "runtime": run_record.runtime,
                "started_at": run_record.started_at,
                "ended_at": run_record.ended_at,
                "event_count": len(run_record.events),
            }

        return _tool_result("arc_run_status", run, {"run_id": run_id})

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

        def run() -> dict[str, Any]:
            if limit < 1 or limit > 100:
                raise ValueError("limit must be between 1 and 100")
            from ..storage.sqlite import SqliteStore

            db_path = ws / ".arc" / "arc.db"
            if not db_path.exists():
                raise ValueError("SQLite index not found. Run 'arc runs backfill' first.")

            store = SqliteStore(db_path)
            results = store.list_runs(
                status=status, runtime=runtime, workflow_id=workflow, limit=limit, offset=0
            )
            total = store.count_runs()
            return {
                "results": results,
                "count": len(results),
                "total_indexed": total,
            }

        return _tool_result(
            "arc_trace_search",
            run,
            {"workflow": workflow, "runtime": runtime, "status": status, "limit": limit},
        )

    @mcp.tool()
    def arc_trace_read(run_id: str, limit: int = _DEFAULT_TRACE_LIMIT, offset: int = 0) -> str:
        """Read the full trace of a stored run.

        Args:
            run_id: The run ID to read.

        Returns:
            JSON string with run record and events.

        """

        def run() -> dict[str, Any]:
            safe_run_id = _safe_id(run_id, "run_id")
            if offset < 0:
                raise ValueError("offset must be >= 0")
            if limit < 1 or limit > _MAX_TRACE_LIMIT:
                raise ValueError(f"limit must be between 1 and {_MAX_TRACE_LIMIT}")
            trace_dir = ws / ".arc" / "traces"
            _resolve_workspace_child(trace_dir, f"{safe_run_id}.jsonl")
            from ..storage.jsonl import JsonlTraceStore

            store = JsonlTraceStore(trace_dir)
            run_record = store.load(safe_run_id)
            if run_record is None:
                raise ValueError(f"Run not found: {safe_run_id}")
            total_events = len(run_record.events)
            events = run_record.events[offset : offset + limit]

            return {
                "run_id": run_record.id,
                "status": run_record.status.value,
                "workflow_id": run_record.workflow_id,
                "runtime": run_record.runtime,
                "started_at": run_record.started_at,
                "ended_at": run_record.ended_at,
                "event_count": total_events,
                "offset": offset,
                "limit": limit,
                "truncated": offset + limit < total_events,
                "events": [e.model_dump() for e in events],
            }

        return _tool_result(
            "arc_trace_read", run, {"run_id": run_id, "limit": limit, "offset": offset}
        )

    @mcp.tool()
    def arc_audit_verify(run_id: str, mode: str = "sha256") -> str:
        """Verify the audit chain for a run.

        Args:
            run_id: The run ID to verify.
            mode: Verification mode - "sha256", "hmac", or "auto" (default "sha256").

        Returns:
            JSON string with verification result.

        """

        def run() -> dict[str, Any]:
            safe_run_id = _safe_id(run_id, "run_id")
            from ..audit.key_manager import AuditKeyManager
            from ..audit.streaming_verifier import StreamingAuditVerifier

            if mode not in ("auto", "sha256", "hmac"):
                raise ValueError(f"Invalid mode: {mode}. Must be auto, sha256, or hmac.")
            verifier = StreamingAuditVerifier(max_memory_mb=8)

            audit_dir = ws / ".arc" / "audit"
            new_chain = _resolve_workspace_child(audit_dir, f"{safe_run_id}.audit.jsonl")
            old_chain = _resolve_workspace_child(audit_dir, f"{safe_run_id}.jsonl")
            if new_chain.exists():
                chain = new_chain
            elif old_chain.exists():
                chain = old_chain
            else:
                raise ValueError(f"Audit chain not found for run {safe_run_id}")

            key = None
            if mode in ("hmac", "auto"):
                mgr = AuditKeyManager()
                key, key_status = mgr.get_key()
                if mode == "hmac" and not key_status.available:
                    raise ValueError(key_status.warning or "HMAC audit key unavailable")

            if mode == "auto":
                result = verifier.verify_auto(chain, key)
            elif mode == "hmac":
                result = verifier.verify_hmac(chain, key)
            else:
                result = verifier.verify_sha256(chain)
            return {
                "run_id": safe_run_id,
                "ok": result.ok,
                "mode": result.mode,
                "records_checked": result.records_checked,
                "reason": result.reason,
                "duration_ms": result.duration_ms,
            }

        return _tool_result("arc_audit_verify", run, {"run_id": run_id, "mode": mode})

    @mcp.tool()
    def arc_hitl_list() -> str:
        """List pending HITL prompts.

        Returns:
            JSON string with pending HITL prompts.

        """

        def run() -> list[dict[str, Any]]:
            from ..audit.hitl_store import list_prompts

            return [prompt.model_dump() for prompt in list_prompts(ws)]

        return _tool_result("arc_hitl_list", run, {})

    @mcp.tool()
    def arc_task_create(
        operation: str,
        task_type: str = "run",
        params: str = "{}",
        max_retries: int = 3,
    ) -> str:
        """Create a new async task for execution.

        Args:
            operation: Operation to execute (e.g., 'run', 'trace', 'audit').
            task_type: Task type - "run", "trace", or "audit" (default "run").
            params: JSON string with parameters for the operation (default "{}").
            max_retries: Maximum retry attempts (default 3).

        Returns:
            JSON string with task ID and initial status.

        """

        def run() -> dict[str, Any]:
            if max_retries < 0 or max_retries > 10:
                raise ValueError("max_retries must be between 0 and 10")
            from ..tasks import Task, TaskExecutor, TaskStorage, TaskType

            try:
                task_type_enum = TaskType(task_type)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid task type: {task_type}. Must be run, trace, or audit."
                ) from exc

            try:
                params_dict = json.loads(params)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON params: {exc}") from exc

            task = Task(
                type=task_type_enum,
                operation=operation,
                params=params_dict,
                max_retries=max_retries,
            )
            storage = TaskStorage(ws / ".arc" / "tasks.db")
            executor = TaskExecutor(storage)
            task_id = executor.submit_task(task)

            return {
                "task_id": task_id,
                "type": task.type.value,
                "operation": task.operation,
                "status": task.status.value,
                "created_at": task.created_at,
                "expires_at": task.expires_at,
            }

        return _tool_result(
            "arc_task_create",
            run,
            {
                "operation": operation,
                "task_type": task_type,
                "params": params,
                "max_retries": max_retries,
            },
        )

    @mcp.tool()
    def arc_task_status(task_id: str) -> str:
        """Get the status of a task.

        Args:
            task_id: The task ID to check.

        Returns:
            JSON string with task status, metadata, and result if completed.

        """

        def run() -> dict[str, Any]:
            safe_task_id = _safe_id(task_id, "task_id")
            from ..tasks import TaskExecutor, TaskStorage

            storage = TaskStorage(ws / ".arc" / "tasks.db")
            executor = TaskExecutor(storage)
            task = executor.get_task_status(safe_task_id)

            if not task:
                raise ValueError(f"Task not found: {safe_task_id}")

            return {
                "task_id": task.id,
                "type": task.type.value,
                "operation": task.operation,
                "status": task.status.value,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "ended_at": task.ended_at,
                "expires_at": task.expires_at,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "result": task.result,
                "error": task.error,
            }

        return _tool_result("arc_task_status", run, {"task_id": task_id})

    @mcp.tool()
    def arc_task_cancel(task_id: str) -> str:
        """Cancel a running or pending task.

        Args:
            task_id: The task ID to cancel.

        Returns:
            JSON string with cancellation result.

        """

        def run() -> dict[str, Any]:
            safe_task_id = _safe_id(task_id, "task_id")
            from ..tasks import TaskExecutor, TaskStorage

            storage = TaskStorage(ws / ".arc" / "tasks.db")
            executor = TaskExecutor(storage)
            cancelled = executor.cancel_task(safe_task_id)

            if not cancelled:
                task = executor.get_task_status(safe_task_id)
                if not task:
                    raise ValueError(f"Task not found: {safe_task_id}")
                raise ValueError(f"Task cannot be cancelled (status: {task.status.value})")

            return {"task_id": safe_task_id, "cancelled": True}

        return _tool_result("arc_task_cancel", run, {"task_id": task_id})

    @mcp.tool()
    def arc_task_result(task_id: str) -> str:
        """Get the result of a completed task.

        Args:
            task_id: The task ID to get result for.

        Returns:
            JSON string with task result, or error if not completed.

        """

        def run() -> dict[str, Any]:
            safe_task_id = _safe_id(task_id, "task_id")
            from ..tasks import TaskExecutor, TaskStatus, TaskStorage

            storage = TaskStorage(ws / ".arc" / "tasks.db")
            executor = TaskExecutor(storage)
            task = executor.get_task_status(safe_task_id)

            if not task:
                raise ValueError(f"Task not found: {safe_task_id}")

            if task.status != TaskStatus.COMPLETED:
                raise ValueError(f"Task not completed (status: {task.status.value})")

            return {
                "task_id": task.id,
                "status": task.status.value,
                "result": task.result,
                "ended_at": task.ended_at,
            }

        return _tool_result("arc_task_result", run, {"task_id": task_id})

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

    @mcp.tool()
    def arc_swarmgraph_plan(task: str, max_nodes: int | None = None) -> str:
        """Deterministically decompose a task into a SwarmGraph DAG plan (no provider calls).

        Args:
            task: Task text to decompose.
            max_nodes: Optional maximum number of plan nodes.

        Returns:
            JSON with the DAG nodes + topological order (planner='deterministic').
        """

        def run() -> dict[str, Any]:
            from ..swarmgraph.decomposition import plan_dag

            plan = plan_dag(task, max_nodes=max_nodes)
            return {
                "strategy": "dag",
                "planner": "deterministic",
                "provider_backed": False,
                "nodes": [node.model_dump(mode="json") for node in plan.nodes],
                "topological_order": plan.topological_order(),
            }

        return _tool_result("arc_swarmgraph_plan", run, {"task": task, "max_nodes": max_nodes})

    @mcp.tool()
    def arc_swarmgraph_assess_risk(task: str, target_runtime: str | None = None) -> str:
        """Deterministically assess a task's consensus risk (LLM-free; no provider calls).

        Args:
            task: Task text to assess.
            target_runtime: Optional target-runtime hint (e.g. 'production').

        Returns:
            JSON with risk_level, recommended_protocol, worker_count, hitl_required.
        """

        def run() -> dict[str, Any]:
            from ..security.adaptive_confirmation import evaluate_confirmation
            from ..swarmgraph.adaptive_consensus import assess_risk

            assessment = assess_risk(task_text=task, target_runtime=target_runtime)
            # Surface the SAME deterministic confirmation verdict the CLI assess-risk surfaces
            # (read-only here; the actionable CLI path audits via enforce_confirmation).
            confirmation = evaluate_confirmation(assessment.risk_level, assessment.hitl_required)
            return {
                "task": task,
                "risk_level": assessment.risk_level,
                "recommended_protocol": assessment.recommended_protocol.value,
                "worker_count": assessment.worker_count,
                "hitl_required": assessment.hitl_required,
                "confirmation": confirmation.as_dict(),
                "provider_backed": False,
            }

        return _tool_result(
            "arc_swarmgraph_assess_risk", run, {"task": task, "target_runtime": target_runtime}
        )

    @mcp.tool()
    def arc_run_start(workflow_id: str, run_id: str = "") -> str:
        """Start an agent workflow run via subprocess isolation (HIGH-risk tool).

        Delegates execution to the arc CLI via SubprocessIsolationProvider so the
        run is env-filtered, secret-stripped, and path-confined. Does NOT run the
        agent in-process.

        Returns JSON with run_id and status.
        """
        import asyncio
        import sys

        from ..isolation.selector import build_execution_provider
        from ..security.validation import SAFE_ENV_KEYS

        eid = run_id or f"mcp-{workflow_id}-{int(time.time())}"

        def _run() -> dict[str, Any]:
            provider = build_execution_provider(
                "subprocess",
                workspace_root=ws,
                env_allowlist=frozenset(SAFE_ENV_KEYS),
                max_output_bytes=65_536,
            )
            result = asyncio.run(
                provider.execute(
                    [
                        sys.executable,
                        "-m",
                        "agent_runtime_cockpit.cli",
                        "run",
                        workflow_id,
                        "--json",
                    ],
                    cwd=ws,
                    timeout_seconds=300,
                )
            )
            return {
                "run_id": eid,
                "workflow_id": workflow_id,
                "status": "started" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "output_preview": (result.stdout or "")[:512],
            }

        return _tool_result("arc_run_start", _run, {"workflow_id": workflow_id})

    return mcp
