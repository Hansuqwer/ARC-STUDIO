"""ARC HTTP Routes.

All routes return ArcEnvelope JSON.
CORS is restricted to localhost only (security boundary).
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiohttp.web as web

from ..adapters.registry import default_registry
from ..arena.models import ArenaAdoptRequest, ArenaMode, ArenaRequest, ArenaVote
from ..arena.service import (
    adopt_candidate,
    arena_request,
    get_vote_rankings,
    list_models,
    list_tags,
    store_arena_run,
)
from ..context.pack import ContextPackGenerator
from ..evals.diff import diff_runs
from ..events.bus import get_bus
from ..events.persistence import get_writer
from ..events.types import ArcEvent, SessionChanged
from ..gating import GatingError
from ..orchestration import runtime_router
from ..orchestration.cross_linker import CrossLinker
from ..orchestration.event_broker import EventBroker
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..protocol.schemas import RunEvent, RunStatus, WorkspaceInfo
from ..provider_action import (
    PROVIDERS,
    ProviderAccountStore,
    ProviderRequest,
    ProviderRoutingPolicy,
    ProviderRoutingStore,
    dry_run_proxy,
    provider_statuses,
    redacted_diagnostics,
)
from ..security.profiles import enforce_profile, resolve_profile
from ..security.redaction import Redactor
from ..security.validation import validate_workspace_path
from ..security.enforcement import TrustEnforcementError, enforce_workspace_trust
from ..storage.advisory_lock import AdvisoryLockUnavailable, advisory_lock
from ..storage.jsonl import JsonlTraceStore
from ..telemetry.otlp_exporter import export_run_to_otlp, validate_otlp_endpoint
from ..workspace import iter_workspace_files
from .keys import EVENT_BROKER_KEY, WORKSPACE_KEY

log = logging.getLogger(__name__)
redactor = Redactor()
ctx_gen = ContextPackGenerator()
RUNTIME_IDS = set(runtime_router.KNOWN_RUNTIMES) | {"auto", "lmarena"}
START_TIME = time.time()


def _workspace(request: web.Request) -> Path:
    ws = request.headers.get("X-ARC-Workspace", "") or request.query.get("workspace", "")
    if not ws:
        return request.app[WORKSPACE_KEY]
    try:
        return validate_workspace_path(ws)
    except ValueError:
        return request.app[WORKSPACE_KEY]


def _json(data: dict, status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps(data, default=str),
        content_type="application/json",
        status=status,
        headers={"Access-Control-Allow-Origin": _cors_origin()},
    )


def _cors_origin() -> str:
    return os.environ.get("ARC_CORS_ORIGIN", "http://127.0.0.1:3000")


def _trace_store(request: web.Request) -> JsonlTraceStore:
    return JsonlTraceStore(_workspace(request) / ".arc" / "traces")


SESSION_WRITE_PAYLOAD_LIMIT_BYTES = 512 * 1024
SESSION_HISTORY_LIMIT = 200
SESSION_UPDATE_ALLOWED_FIELDS = frozenset({"mode", "runtime_mode", "profile_id", "isolation_id"})


def _session_error(exc: Exception, status: int) -> web.Response:
    if isinstance(exc, TrustEnforcementError):
        return _json(err(ArcErrorCode.PERMISSION_DENIED, str(exc)).model_dump(), 403)
    if isinstance(exc, AdvisoryLockUnavailable):
        return _json(err(ArcErrorCode.LOCK_CONTENTION, str(exc)).model_dump(), 429)
    return _json(err(ArcErrorCode.INTERNAL_ERROR, str(exc)).model_dump(), status)


def _emit_session_changed(session_id: str, operation: str, workspace: Path) -> None:
    get_bus().publish(
        SessionChanged(
            session_id=session_id,
            operation=operation,  # type: ignore[arg-type]
            workspace=str(workspace),
            payload={
                "session_id": session_id,
                "operation": operation,
                "workspace": str(workspace),
                "coverage_class": "session_lifecycle_ephemeral",
                "audit_persistence": "excluded",
                "exclusion_reason": "in-memory event bus only; not part of per-run audit chain",
            },
        )
    )


async def sessions_write(request: web.Request) -> web.Response:
    """POST /api/sessions/write — daemon write bridge for IDE session import."""
    from ..cli_repl.session import ChatSession, is_valid_session_id
    from ..cli_repl.session_bundle import _contains_secret

    workspace = _workspace(request)
    raw = await request.text()
    if len(raw.encode("utf-8")) > SESSION_WRITE_PAYLOAD_LIMIT_BYTES:
        return _json(
            err(ArcErrorCode.INVALID_INPUT, "payload exceeds 512 KB limit").model_dump(), 400
        )
    try:
        body = json.loads(raw)
    except Exception:
        return _json(err(ArcErrorCode.INVALID_INPUT, "Invalid JSON body").model_dump(), 400)
    if not isinstance(body, dict):
        return _json(
            err(ArcErrorCode.INVALID_INPUT, "Session payload must be an object").model_dump(), 400
        )
    if _contains_secret(body):
        return _json(
            err(ArcErrorCode.INVALID_INPUT, "payload contains secret-looking data").model_dump(),
            400,
        )
    if isinstance(body.get("history"), list) and len(body["history"]) > SESSION_HISTORY_LIMIT:
        body["history"] = body["history"][-SESSION_HISTORY_LIMIT:]
    try:
        session = ChatSession.model_validate(body)
    except Exception as exc:
        return _json(
            err(ArcErrorCode.INVALID_INPUT, f"invalid session payload: {exc}").model_dump(), 400
        )
    if not is_valid_session_id(session.id):
        return _json(
            err(ArcErrorCode.INVALID_INPUT, f"unsafe session id: {session.id!r}").model_dump(), 400
        )
    try:
        enforce_workspace_trust(workspace, "session_write", "daemon-session-write", 0)
        session.save()
    except (TrustEnforcementError, AdvisoryLockUnavailable) as exc:
        return _session_error(exc, 500)
    except Exception as exc:
        return _json(err(ArcErrorCode.INTERNAL_ERROR, str(exc)).model_dump(), 500)
    _emit_session_changed(session.id, "write", workspace)
    return _json(ok({"session_id": session.id, "messages": len(session.history)}).model_dump())


async def sessions_delete(request: web.Request) -> web.Response:
    """DELETE /api/sessions/{session_id} — daemon delete bridge for IDE sessions."""
    from ..cli_repl.session import _get_sessions_dir, is_valid_session_id

    workspace = _workspace(request)
    session_id = request.match_info["session_id"]
    if not is_valid_session_id(session_id):
        return _json(
            err(ArcErrorCode.INVALID_INPUT, f"unsafe session id: {session_id!r}").model_dump(), 400
        )
    try:
        enforce_workspace_trust(workspace, "session_delete", "daemon-session-delete", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    session_path = _get_sessions_dir() / session_id / "session.json"
    if not session_path.exists():
        return _json(
            err(ArcErrorCode.RUN_NOT_FOUND, f"session not found: {session_id}").model_dump(), 404
        )
    try:
        with advisory_lock(session_path):
            session_path.unlink(missing_ok=True)
            try:
                session_path.parent.rmdir()
            except OSError:
                pass
    except (TrustEnforcementError, AdvisoryLockUnavailable) as exc:
        return _session_error(exc, 500)
    except Exception as exc:
        return _json(err(ArcErrorCode.INTERNAL_ERROR, str(exc)).model_dump(), 500)
    _emit_session_changed(session_id, "delete", workspace)
    return _json(ok({"session_id": session_id, "deleted": True}).model_dump())


async def sessions_update(request: web.Request) -> web.Response:
    """PATCH /api/sessions/{session_id} — daemon safe-field update bridge."""
    from ..cli_repl.session import ChatSession, is_valid_session_id
    from ..cli_repl.session_bundle import _contains_secret

    workspace = _workspace(request)
    session_id = request.match_info["session_id"]
    if not is_valid_session_id(session_id):
        return _json(
            err(ArcErrorCode.INVALID_INPUT, f"unsafe session id: {session_id!r}").model_dump(), 400
        )
    try:
        body = await request.json()
    except Exception:
        return _json(err(ArcErrorCode.INVALID_INPUT, "Invalid JSON body").model_dump(), 400)
    field = str(body.get("field", "")) if isinstance(body, dict) else ""
    value = body.get("value") if isinstance(body, dict) else None
    if field not in SESSION_UPDATE_ALLOWED_FIELDS:
        return _json(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"field {field!r} is not updatable via daemon bridge; allowed: {sorted(SESSION_UPDATE_ALLOWED_FIELDS)}",
            ).model_dump(),
            400,
        )
    if _contains_secret(value):
        return _json(
            err(ArcErrorCode.INVALID_INPUT, "value contains secret-looking data").model_dump(), 400
        )
    try:
        enforce_workspace_trust(workspace, "session_update", "daemon-session-update", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    session = ChatSession.load(session_id)
    if session is None:
        return _json(
            err(ArcErrorCode.RUN_NOT_FOUND, f"session not found: {session_id}").model_dump(), 404
        )
    try:
        data = session.model_dump(mode="json")
        data[field] = str(value)
        updated = ChatSession.model_validate(data)
        updated.save()
    except (TrustEnforcementError, AdvisoryLockUnavailable) as exc:
        return _session_error(exc, 500)
    except ValueError as exc:
        return _json(err(ArcErrorCode.INVALID_INPUT, str(exc)).model_dump(), 400)
    except Exception as exc:
        return _json(err(ArcErrorCode.INTERNAL_ERROR, str(exc)).model_dump(), 500)
    _emit_session_changed(session_id, "update", workspace)
    return _json(ok({"session_id": session_id, "field": field, "updated": True}).model_dump())


async def health(request: web.Request) -> web.Response:
    """Health check endpoint with daemon status."""
    store = _trace_store(request)
    all_runs = store.list_runs()
    active_runs = [r for r in all_runs if r.status in ("running", "pending")]

    return _json(
        {
            "status": "healthy",
            "version": "0.1.0-alpha",
            "uptime_seconds": int(time.time() - START_TIME),
            "active_runs": len(active_runs),
            "arc": True,
        }
    )


async def inspect(request: web.Request) -> web.Response:
    t0 = time.time()
    workspace = _workspace(request)
    registry = default_registry()
    runtimes = registry.detect_all(workspace)

    py_count = len(iter_workspace_files(workspace, (".py",)))
    ts_count = len(iter_workspace_files(workspace, (".ts",)))

    info = WorkspaceInfo(
        path=str(workspace),
        runtimes=runtimes,
        files_scanned=py_count + ts_count,
        detection_warnings=[] if runtimes else ["No runtimes detected in workspace"],
    )

    envelope = ok(
        info.model_dump(), workspace=str(workspace), duration_ms=(time.time() - t0) * 1000
    )
    return _json(envelope.model_dump())


async def runtimes(request: web.Request) -> web.Response:
    t0 = time.time()
    workspace = _workspace(request)
    registry = default_registry()
    detected = registry.detect_all(workspace)
    envelope = ok(
        [r.model_dump() for r in detected],
        workspace=str(workspace),
        duration_ms=(time.time() - t0) * 1000,
    )
    return _json(envelope.model_dump())


async def runtime_capabilities(request: web.Request) -> web.Response:
    workspace = _workspace(request)
    payload = {
        "workspace": str(workspace),
        "auto_priority": list(runtime_router.AUTO_PRIORITY),
        "runtimes": [report.model_dump() for report in runtime_router.list_runtimes(workspace)],
    }
    return _json(ok(payload, workspace=str(workspace)).model_dump())


async def workflows(request: web.Request) -> web.Response:
    t0 = time.time()
    workspace = _workspace(request)
    runtime_id = request.query.get("runtime")
    registry = default_registry()
    detected = registry.detect_all(workspace)

    results = []
    for rt in detected:
        if runtime_id and not rt.adapter == runtime_id:
            continue
        adapter = registry.get(rt.adapter)
        if adapter and adapter.capabilities().can_export_workflow:
            try:
                wfs = adapter.export_workflow(workspace)
                results.extend(w.model_dump() for w in wfs)
            except Exception as e:
                log.warning("Workflow export failed for %s: %s", rt.adapter, e)

    envelope = ok(results, workspace=str(workspace), duration_ms=(time.time() - t0) * 1000)
    return _json(envelope.model_dump())


async def schemas(request: web.Request) -> web.Response:
    t0 = time.time()
    workspace = _workspace(request)
    runtime_id = request.query.get("runtime")
    registry = default_registry()
    detected = registry.detect_all(workspace)

    results = []
    for rt in detected:
        if runtime_id and not rt.adapter == runtime_id:
            continue
        adapter = registry.get(rt.adapter)
        if adapter and adapter.capabilities().can_export_schema:
            try:
                ss = adapter.export_schemas(workspace)
                results.extend(s.model_dump_api() for s in ss)
            except Exception as e:
                log.warning("Schema export failed for %s: %s", rt.adapter, e)

    envelope = ok(results, workspace=str(workspace), duration_ms=(time.time() - t0) * 1000)
    return _json(envelope.model_dump())


async def start_run(request: web.Request) -> web.Response:
    """Start a run. GET is legacy; POST JSON is canonical. Both share runtime routing."""
    t0 = time.time()
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "start_run", "daemon-start-run", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    body: dict = {}
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return _json(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Invalid JSON request body",
                    details={"code": "invalid_json"},
                ).model_dump(),
                400,
            )
    workflow_id = str(
        body.get("workflow_id") or request.query.get("workflow_id", "wf-swarmgraph-fixture")
    )
    raw_runtime = body.get("runtime") if "runtime" in body else request.query.get("runtime", "auto")
    runtime = (
        [str(item) for item in raw_runtime] if isinstance(raw_runtime, list) else str(raw_runtime)
    )
    runtime_ids = runtime if isinstance(runtime, list) else [runtime]
    if any(runtime_id not in RUNTIME_IDS for runtime_id in runtime_ids):
        return _json(err("invalid_runtime", f"Invalid runtime: {runtime}").model_dump(), 400)
    allow_paid_calls = bool(body.get("allow_paid_calls")) or request.query.get(
        "allow_paid_calls", ""
    ).lower() in {"1", "true", "yes"}
    paid_calls_explicit = "allow_paid_calls" in body or "allow_paid_calls" in request.query
    profile_id = str(body.get("profile_id") or request.query.get("profile_id", ""))
    if not profile_id:
        # Auto-select profile based on allow_paid_calls
        profile_id = "local-paid" if paid_calls_explicit and allow_paid_calls else "local-safe"
    profile = resolve_profile(profile_id)
    # Profile's allow_paid_calls overrides if not explicitly set in request
    if not paid_calls_explicit:
        allow_paid_calls = profile.allow_paid_calls
    inputs = body.get("inputs") if isinstance(body.get("inputs"), dict) else {}
    try:
        routed = runtime_router.resolve(workspace, runtime, allow_paid_calls=allow_paid_calls)
    except runtime_router.UnknownRuntime as exc:
        return _json(
            err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": exc.code}).model_dump(), 400
        )
    except runtime_router.RuntimeRouterError as exc:
        return _json(
            err(ArcErrorCode.NOT_IMPLEMENTED, str(exc), details={"code": exc.code}).model_dump(),
            501,
        )

    # Enforce profile for the selected runtime
    try:
        if allow_paid_calls and not profile.allow_paid_calls:
            raise GatingError(f"Profile '{profile.id}' does not allow paid calls.")
        enforce_profile(profile, routed.adapter.adapter_id)
    except GatingError as exc:
        return _json(
            err(
                ArcErrorCode.INVALID_INPUT, str(exc), details={"code": "PROFILE_ENFORCEMENT_FAILED"}
            ).model_dump(),
            403,
        )

    try:
        run = await routed.adapter.run_workflow(
            workflow_id,
            {
                **inputs,
                "workspace": str(workspace),
                "allow_paid_calls": allow_paid_calls,
                "profile_id": profile_id,
            },
        )
        _trace_store(request).save(run)
        envelope = ok(
            run.model_dump(),
            adapter=routed.adapter.adapter_id,
            duration_ms=(time.time() - t0) * 1000,
        )
        envelope.data["runtime_selection"] = {
            "runtime": routed.adapter.adapter_id,
            "chosen_by": routed.chosen_by,
            "availability": routed.report.availability,
        }
        return _json(envelope.model_dump())
    except Exception as e:
        return _json(err(ArcErrorCode.RUN_FAILED, str(e)).model_dump(), 500)


async def get_run(request: web.Request) -> web.Response:
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "get_run", "daemon-get-run", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    run_id = request.match_info["run_id"]
    run = _trace_store(request).load(run_id)
    if not run:
        return _json(err(ArcErrorCode.RUN_NOT_FOUND, f"Run {run_id} not found").model_dump(), 404)
    return _json(ok(run.model_dump()).model_dump())


async def list_runs(request: web.Request) -> web.Response:
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "list_runs", "daemon-list-runs", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    store = _trace_store(request)
    run_ids = store.list_runs()
    runs = [r for rid in run_ids if (r := store.load(rid)) is not None]
    runtime_filter = request.query.get("runtime")
    if runtime_filter:
        runs = [r for r in runs if r.runtime == runtime_filter]
    return _json(ok([r.model_dump() for r in runs]).model_dump())


async def context_pack(request: web.Request) -> web.Response:
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "context_pack", "daemon-context-pack", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    task = request.query.get("task", "agent runtime inspection")
    entries = ctx_gen.generate(task, workspace, save=True)
    # Redact before sending to frontend
    safe = [redactor.redact_dict(e.model_dump()) for e in entries]
    return _json(ok(safe).model_dump())


async def providers(request: web.Request) -> web.Response:
    return _json(ok([provider.model_dump() for provider in PROVIDERS]).model_dump())


async def providers_status(request: web.Request) -> web.Response:
    return _json(ok([status.model_dump() for status in provider_statuses(os.environ)]).model_dump())


async def providers_routing(request: web.Request) -> web.Response:
    store = ProviderRoutingStore()
    if request.method == "PUT":
        workspace = _workspace(request)
        try:
            enforce_workspace_trust(workspace, "providers_routing", "daemon-providers-routing", 0)
        except TrustEnforcementError as exc:
            return _session_error(exc, 500)
        body = await request.json()
        policy = ProviderRoutingPolicy.model_validate(body)
        return _json(ok(store.set(policy).model_dump()).model_dump())
    return _json(ok(store.get().model_dump()).model_dump())


async def providers_accounts(request: web.Request) -> web.Response:
    store = ProviderAccountStore()
    if request.method == "POST":
        workspace = _workspace(request)
        try:
            enforce_workspace_trust(workspace, "providers_accounts", "daemon-providers-accounts", 0)
        except TrustEnforcementError as exc:
            return _session_error(exc, 500)
        body = await request.json()
        if body.get("api_key"):
            return _json(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Direct key storage requires secure keychain; use api_key_env.",
                ).model_dump(),
                400,
            )
        account = store.add_env_account(
            body.get("provider", "openai"),
            body.get("label", "provider account"),
            body.get("api_key_env", "OPENAI_API_KEY"),
            body.get("default_model"),
            body.get("base_url"),
        )
        return _json(ok(account.model_dump()).model_dump())
    return _json(ok([account.model_dump() for account in store.list_accounts()]).model_dump())


async def providers_account(request: web.Request) -> web.Response:
    store = ProviderAccountStore()
    account_id = request.match_info["account_id"]

    if request.method in ("PATCH", "DELETE"):
        workspace = _workspace(request)
        action = (
            "providers_account_patch" if request.method == "PATCH" else "providers_account_delete"
        )
        try:
            enforce_workspace_trust(workspace, action, f"daemon-{action}", 0)
        except TrustEnforcementError as exc:
            return _session_error(exc, 500)

    if request.method == "DELETE":
        return _json(
            ok({"deleted": store.delete(account_id), "account_id": account_id}).model_dump()
        )
    body = await request.json()
    if "enabled" in body:
        account = store.set_enabled(account_id, bool(body["enabled"]))
        if account:
            return _json(ok(account.model_dump()).model_dump())
    return _json(
        err(ArcErrorCode.INVALID_INPUT, f"Provider account not found: {account_id}").model_dump(),
        404,
    )


async def providers_account_test(request: web.Request) -> web.Response:
    if os.environ.get("ARC_ALLOW_LIVE_PROVIDER_TESTS") != "true":
        return _json(
            ok(
                {
                    "account_id": request.match_info["account_id"],
                    "dry_run": True,
                    "status": "not_checked",
                    "message": "Live provider tests disabled.",
                }
            ).model_dump()
        )
    return _json(
        err(
            ArcErrorCode.NOT_IMPLEMENTED, "Live provider health checks are not implemented yet."
        ).model_dump(),
        501,
    )


async def providers_proxy_chat(request: web.Request) -> web.Response:
    body = await request.json()
    proxy_request = ProviderRequest(
        provider=body.get("provider"),
        model=body.get("model"),
        prompt=body.get("prompt") or "",
        dry_run=body.get("dry_run", True),
        allow_paid_calls=body.get("allow_paid_calls", False),
    )
    try:
        response = dry_run_proxy(proxy_request)
    except RuntimeError as exc:
        return _json(err(ArcErrorCode.INVALID_INPUT, str(exc)).model_dump(), 400)
    return _json(ok(response.model_dump()).model_dump())


async def providers_diagnostics(request: web.Request) -> web.Response:
    return _json(ok(redacted_diagnostics(os.environ)).model_dump())


async def sse_proof(request: web.Request) -> web.StreamResponse:
    """Manual SSE proof endpoint — streams fake events with heartbeats.

    Proves that manual ``aiohttp.web.StreamResponse`` works for SSE
    without the ``aiohttp-sse`` package. Delivers 3 fake events plus
    heartbeats, then ends with STREAM_END.
    """
    import asyncio

    # Allow tests to override sleep intervals (0 in tests means fastest path).
    event_delay = float(request.query.get("event_delay", "0.01"))
    heartbeat_interval = float(request.query.get("heartbeat_interval", "0.1"))
    heartbeat_count = int(request.query.get("heartbeat_count", "2"))

    response = web.StreamResponse(
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": _cors_origin(),
        }
    )
    await response.prepare(request)

    events = [
        {
            "type": "RUN_STARTED",
            "timestamp": time.time(),
            "data": {"workflow_id": "proof", "runtime": "sse-proof"},
        },
        {
            "type": "STEP_STARTED",
            "timestamp": time.time(),
            "data": {"step_id": "s1", "step_name": "SSE proof step"},
        },
        {"type": "RUN_COMPLETED", "timestamp": time.time(), "data": {"duration_ms": 42}},
    ]

    for i, event in enumerate(events):
        event["sequence"] = i
        event["run_id"] = "proof-run"
        payload = json.dumps(event, default=str)
        await response.write(f"data: {payload}\n\n".encode())
        if event_delay > 0:
            await asyncio.sleep(event_delay)

    # Heartbeat cycle
    for i in range(heartbeat_count):
        if heartbeat_interval > 0:
            await asyncio.sleep(heartbeat_interval)
        heartbeat = {"type": "HEARTBEAT", "timestamp": time.time(), "sequence": len(events) + i}
        await response.write(
            f": heartbeat {i + 1}\ndata: {json.dumps(heartbeat, default=str)}\n\n".encode()
        )

    await response.write(b'data: {"type": "STREAM_END"}\n\n')
    return response


async def run_events_sse(request: web.Request) -> web.StreamResponse:
    """AG-UI-compatible SSE stream for run events.

    ``mode=live`` subscribes to the active in-memory stream and closes on
    RUN_COMPLETED/RUN_FAILED/RUN_CANCELLED with STREAM_END. Default replay
    streams the stored trace and marks STREAM_END as replay.
    """
    mode = request.query.get("mode", "replay")
    if mode == "live":
        # Get or create broker without triggering deprecation warning
        try:
            broker = request.app[EVENT_BROKER_KEY]
        except KeyError:
            import warnings

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="Changing state of started or joined application is deprecated",
                    category=DeprecationWarning,
                )
                broker = EventBroker(_trace_store(request))
                request.app[EVENT_BROKER_KEY] = broker
        run_id = request.match_info["run_id"]
        run = _trace_store(request).load(run_id)
        if run and run.status not in {RunStatus.PENDING, RunStatus.RUNNING}:
            response = web.StreamResponse(
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": _cors_origin(),
                }
            )
            await response.prepare(request)
            for event in run.events:
                event_data = event.model_dump()
                await response.write(
                    f"event: {event_data.get('type', 'message')}\n"
                    f"data: {json.dumps(event_data, default=str)}\n\n".encode()
                )
            await response.write(
                b'event: stream_end\ndata: {"type": "STREAM_END", "mode": "live"}\n\n'
            )
            return response
        if run and not broker.is_active(run_id):
            response = web.StreamResponse(
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": _cors_origin(),
                }
            )
            await response.prepare(request)
            event = broker.degraded_event(run_id, "no_active_local_producer")
            await response.write(
                f"event: {event['type']}\ndata: {json.dumps(event, default=str)}\n\n".encode()
            )
            await response.write(
                b'event: stream_end\ndata: {"type": "STREAM_END", "mode": "live", "degraded": true}\n\n'
            )
            return response
        return await broker.sse_handler(request)

    run_id = request.match_info["run_id"]
    response = web.StreamResponse(
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": _cors_origin(),
        }
    )
    await response.prepare(request)

    run = _trace_store(request).load(run_id)
    if not run:
        error = {
            "type": "RUN_ERROR",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "run_id": run_id,
            "sequence": 0,
            "data": {
                "code": "RUN_NOT_FOUND",
                "error": f"Run not found: {run_id}",
            },
        }
        await response.write(f"data: {json.dumps(error)}\n\n".encode())
    else:
        for event in run.events:
            data = json.dumps(event.model_dump(), default=str)
            await response.write(f"data: {data}\n\n".encode())

    await response.write(b'data: {"type": "STREAM_END", "mode": "replay"}\n\n')
    return response


async def run_links(request: web.Request) -> web.Response:
    """GET /api/runs/{id}/links — return linked event chains for a run.

    Query params:
      - ``filter``: ``"node_id"``, ``"message_id"``, ``"tool_call_id"``,
        ``"evidence_id"``, or ``"all_ids"`` (default). Returns chains keyed
        by the chosen stable ID type.
      - ``stable_id``: optional single ID to narrow results.
    """
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "run_links", "daemon-run-links", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    run_id = request.match_info["run_id"]
    run = _trace_store(request).load(run_id)
    if not run:
        return _json(err(ArcErrorCode.RUN_NOT_FOUND, f"Run {run_id} not found").model_dump(), 404)

    linker = CrossLinker()
    linker.index_all(run.events)

    filter_by = request.query.get("filter", "all_ids")
    single_id = request.query.get("stable_id")
    if filter_by not in {"all_ids", "node_id", "message_id", "tool_call_id", "evidence_id"}:
        return _json(
            err(ArcErrorCode.INVALID_INPUT, f"Invalid links filter: {filter_by}").model_dump(), 400
        )
    try:
        limit = min(max(int(request.query.get("limit", "100")), 1), 500)
        offset = max(int(request.query.get("offset", "0")), 0)
    except ValueError:
        return _json(
            err(ArcErrorCode.INVALID_INPUT, "limit and offset must be integers").model_dump(), 400
        )

    def _ids(field: str) -> list[str]:
        ids = [single_id] if single_id else linker.get_ids(field)
        return [item for item in ids if item][offset : offset + limit]

    result: dict[str, list[dict]] = {}

    if filter_by in ("all_ids", "node_id"):
        for nid in _ids("node_id"):
            chain = linker.get_node_chain(nid)
            if chain:
                result.setdefault("node_chains", {})[nid] = [e.model_dump() for e in chain]

    if filter_by in ("all_ids", "message_id"):
        for mid in _ids("message_id"):
            chain = linker.get_message_chain(mid)
            if chain:
                result.setdefault("message_chains", {})[mid] = [e.model_dump() for e in chain]

    if filter_by in ("all_ids", "tool_call_id"):
        for tid in _ids("tool_call_id"):
            chain = linker.get_tool_call_chain(tid)
            if chain:
                result.setdefault("tool_call_chains", {})[tid] = [e.model_dump() for e in chain]

    if filter_by in ("all_ids", "evidence_id"):
        for eid in _ids("evidence_id"):
            chain = linker.get_evidence_events(eid)
            if chain:
                result.setdefault("evidence_chains", {})[eid] = [e.model_dump() for e in chain]

    result["has_stable_ids"] = linker.has_stable_ids()
    result["stable_id_count"] = len(linker.get_run_event_ids())
    result["limit"] = limit
    result["offset"] = offset

    return _json(ok(result).model_dump())


async def export_trace(request: web.Request) -> web.Response:
    """Export run trace to OTLP endpoint."""
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "export_trace", "daemon-export-trace", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    run_id = request.match_info["run_id"]

    try:
        body = await request.json()
        endpoint = body.get("endpoint", "")
    except Exception:
        return _json(err(ArcErrorCode.INVALID_INPUT, "Invalid JSON body").model_dump(), 400)

    # Validate endpoint
    is_valid, warning = validate_otlp_endpoint(endpoint)
    if not is_valid:
        return _json(
            err(ArcErrorCode.INVALID_INPUT, warning or "Invalid endpoint").model_dump(), 400
        )

    # Load run
    run = _trace_store(request).load(run_id)
    if not run:
        return _json(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}").model_dump(), 404)

    # Export
    try:
        success = export_run_to_otlp(run, endpoint)
        result = {"exported": success}
        if warning:
            result["warning"] = warning
        return _json(ok(result).model_dump())
    except Exception as e:
        log.error(f"OTLP export failed: {e}")
        return _json(err(ArcErrorCode.INTERNAL_ERROR, f"Export failed: {str(e)}").model_dump(), 500)


# ─── Diff ──────────────────────────────────────────────────────────────────────


async def runs_diff(request: web.Request) -> web.Response:
    """Compare two runs by run IDs: GET /api/runs/diff?run_a=...&run_b=..."""
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "runs_diff", "daemon-runs-diff", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    run_a_id = request.query.get("run_a", "")
    run_b_id = request.query.get("run_b", "")
    if not run_a_id or not run_b_id:
        return _json(err("missing_params", "Both run_a and run_b are required").model_dump(), 400)
    store = _trace_store(request)
    run_a = store.load(run_a_id)
    run_b = store.load(run_b_id)
    if run_a is None or run_b is None:
        return _json(err("not_found", "One or both runs not found").model_dump(), 404)
    result = diff_runs(run_a, run_b)
    return _json(ok(result.model_dump()).model_dump())


async def runs_eval(request: web.Request) -> web.Response:
    """Evaluate a run against a golden trace: POST /api/evals/run."""
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "runs_eval", "daemon-runs-eval", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    from ..evals.golden import GoldenTrace, eval_run

    body = await request.json()
    run_id = body.get("run_id", "")
    golden = GoldenTrace.model_validate(body.get("golden", {}))
    store = _trace_store(request)
    run = store.load(run_id)
    if run is None:
        return _json(err("not_found", f"Run {run_id} not found").model_dump(), 404)
    result = eval_run(run, golden)
    return _json(ok(result.model_dump()).model_dump())


# ─── Arena (LM Arena) ───────────────────────────────────────────────────────


async def arena_models(request: web.Request) -> web.Response:
    """GET /api/arena/models — list available Arena models."""
    tags_raw = request.query.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None
    models = list_models(tags)
    return _json(ok([m.model_dump() for m in models]).model_dump())


async def arena_tags(request: web.Request) -> web.Response:
    """GET /api/arena/tags — list model tag descriptions."""
    return _json(ok(list_tags()).model_dump())


async def arena_chat(request: web.Request) -> web.Response:
    """POST /api/arena/chat — main entry point for all Arena modes.

    Body accepts ArenaRequest JSON.
    Returns ArenaResponse with candidates for battle/direct/code/agent-arena-preview.
    """
    t0 = time.time()
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "arena_chat", "daemon-arena-chat", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    try:
        body = await request.json()
    except Exception:
        return _json(err(ArcErrorCode.INVALID_INPUT, "Invalid JSON body").model_dump(), 400)

    try:
        req = ArenaRequest.model_validate(body)
    except Exception as exc:
        return _json(err(ArcErrorCode.INVALID_INPUT, str(exc)).model_dump(), 400)
    req.workspace = str(workspace)

    # Validate mode
    try:
        mode = ArenaMode(req.mode) if isinstance(req.mode, str) else req.mode
    except ValueError:
        return _json(err(ArcErrorCode.INVALID_INPUT, f"Invalid mode: {req.mode}").model_dump(), 400)

    req.mode = mode

    # Enforce profile
    try:
        profile = resolve_profile(req.profile_id)
        if req.allow_paid_calls and not profile.allow_paid_calls:
            raise GatingError(f"Profile '{profile.id}' does not allow paid calls.")
        enforce_profile(profile, "lmarena")
    except GatingError as exc:
        return _json(
            err(
                ArcErrorCode.INVALID_INPUT, str(exc), details={"code": "PROFILE_ENFORCEMENT_FAILED"}
            ).model_dump(),
            403,
        )

    # Process request
    response = arena_request(workspace, req)
    if not response.run_id:
        response.run_id = f"arena-{uuid.uuid4().hex[:12]}"

    # Store as ARC run
    store = _trace_store(request)
    store_arena_run(store, response, req)

    envelope = ok(
        response.model_dump(), workspace=str(workspace), duration_ms=(time.time() - t0) * 1000
    )
    envelope.data["_run_id"] = response.run_id
    return _json(envelope.model_dump())


async def arena_vote(request: web.Request) -> web.Response:
    """POST /api/arena/vote — record a vote for a battle candidate."""
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "arena_vote", "daemon-arena-vote", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    try:
        body = await request.json()
    except Exception:
        return _json(err(ArcErrorCode.INVALID_INPUT, "Invalid JSON body").model_dump(), 400)

    vote = ArenaVote.model_validate(body)
    # Store vote in arena runs metadata
    store = _trace_store(request)
    run = store.load(vote.run_id)
    if run is None:
        return _json(
            err(ArcErrorCode.RUN_NOT_FOUND, f"Run {vote.run_id} not found").model_dump(), 404
        )

    # Add vote event to existing run record
    events = list(run.events)
    events.append(
        RunEvent(
            type="LMARENA_VOTE_RECORDED",
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            run_id=vote.run_id,
            sequence=len(events),
            data={
                "winner_candidate_id": vote.winner_candidate_id,
                "loser_candidate_id": vote.loser_candidate_id,
                "voter": vote.voter,
            },
        )
    )
    run.events = events
    run.metadata["vote"] = vote.winner_candidate_id
    store.save(run)

    return _json(ok({"recorded": True, "run_id": vote.run_id}).model_dump())


async def arena_adopt(request: web.Request) -> web.Response:
    """POST /api/arena/adopt — adopt a candidate's code patch."""
    ws = _workspace(request)
    try:
        enforce_workspace_trust(ws, "arena_adopt", "daemon-arena-adopt", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)
    try:
        body = await request.json()
    except Exception:
        return _json(err(ArcErrorCode.INVALID_INPUT, "Invalid JSON body").model_dump(), 400)
    req = ArenaAdoptRequest.model_validate(body)
    req.workspace = str(ws)
    result = adopt_candidate(ws, req)
    return _json(ok(result.model_dump()).model_dump())


async def arena_rankings(request: web.Request) -> web.Response:
    """GET /api/arena/rankings — retrieve vote history and model rankings."""
    store = _trace_store(request)
    rankings = get_vote_rankings(store)
    return _json(ok(rankings).model_dump())


# ─── Task daemon routes (Phase 54) ──────────────────────────────────────────


def _get_task_executor(request: web.Request):
    """Get or create the TaskExecutor bound to this workspace."""
    from ..tasks.executor import TaskExecutor
    from ..tasks.storage import TaskStorage

    workspace = _workspace(request)
    db_path = workspace / ".arc" / "tasks.db"
    storage = TaskStorage(db_path)
    executor = TaskExecutor(storage)
    return executor


async def tasks_list(request: web.Request) -> web.Response:
    """GET /api/tasks — list tasks with optional status/type filters."""
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "tasks_list", "daemon-tasks-list", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)

    from ..tasks.models import TaskStatus, TaskType

    status_raw = request.query.get("status")
    task_type_raw = request.query.get("type")
    limit_raw = request.query.get("limit", "100")

    status = (
        TaskStatus(status_raw)
        if status_raw and status_raw in {s.value for s in TaskStatus}
        else None
    )
    task_type = (
        TaskType(task_type_raw)
        if task_type_raw and task_type_raw in {t.value for t in TaskType}
        else None
    )
    try:
        limit = max(1, min(int(limit_raw), 500))
    except ValueError:
        limit = 100

    executor = _get_task_executor(request)
    tasks = executor.list_tasks(status=status, task_type=task_type, limit=limit)
    return _json(ok([t.to_dict() for t in tasks]).model_dump())


async def tasks_create(request: web.Request) -> web.Response:
    """POST /api/tasks — create and submit a new task."""
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "tasks_create", "daemon-tasks-create", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)

    from ..tasks.models import Task, TaskType

    body = await request.json()
    task_type_raw = body.get("type", "run")
    try:
        task_type = TaskType(task_type_raw)
    except ValueError:
        return _json(
            err(ArcErrorCode.INVALID_INPUT, f"Invalid task type: {task_type_raw}").model_dump(), 400
        )

    task = Task(
        type=task_type,
        operation=body.get("operation", ""),
        params=body.get("params", {}),
    )
    executor = _get_task_executor(request)
    task_id = executor.submit_task(task)
    return _json(ok({"task_id": task_id, "status": task.status.value}).model_dump())


async def tasks_get(request: web.Request) -> web.Response:
    """GET /api/tasks/{task_id} — get task status."""
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "tasks_get", "daemon-tasks-get", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)

    task_id = request.match_info["task_id"]
    executor = _get_task_executor(request)
    task = executor.get_task_status(task_id)
    if task is None:
        return _json(
            err(ArcErrorCode.RUN_NOT_FOUND, f"Task not found: {task_id}").model_dump(), 404
        )
    return _json(ok(task.to_dict()).model_dump())


async def tasks_delete(request: web.Request) -> web.Response:
    """DELETE /api/tasks/{task_id} — cancel a task."""
    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "tasks_delete", "daemon-tasks-delete", 0)
    except TrustEnforcementError as exc:
        return _session_error(exc, 500)

    task_id = request.match_info["task_id"]
    executor = _get_task_executor(request)
    cancelled = executor.cancel_task(task_id)
    if not cancelled:
        return _json(
            err(
                ArcErrorCode.RUN_NOT_FOUND, f"Task not found or already terminal: {task_id}"
            ).model_dump(),
            404,
        )
    return _json(ok({"task_id": task_id, "cancelled": True}).model_dump())


_SSE_PUSH_EVENT_TYPES = frozenset(
    {
        "session_changed",
        "hitl_required",
        "audit_verified",
        "run_completed",
        "run_failed",
        "quota_warning",
        "task_state_changed",
        "task_completed",
        "task_failed",
    }
)


async def events_stream(request: web.Request) -> web.StreamResponse:
    """GET /api/events/stream — local SSE push for session/run/audit events.

    Pushes: session_changed, hitl_required, audit_verified, run_completed,
    run_failed, quota_warning.

    Requires workspace trust at connect time (returns 403 before streaming).

    Supports ``Last-Event-ID`` header: client sends the last event_id it saw;
    persisted events with seq > last_seen_id are replayed first.

    No WebSocket. No shared-server. No remote-sync. Local daemon only.
    """
    import asyncio

    workspace = _workspace(request)
    try:
        enforce_workspace_trust(workspace, "events_stream", "daemon-events-stream", 0)
    except TrustEnforcementError as exc:
        return _json(err(ArcErrorCode.PERMISSION_DENIED, str(exc)).model_dump(), 403)

    response = web.StreamResponse(
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": _cors_origin(),
        }
    )
    await response.prepare(request)

    # Parse Last-Event-ID for resume
    last_seen_raw = request.headers.get("Last-Event-ID", "").strip()
    last_seen_id: int | None = None
    if last_seen_raw:
        try:
            last_seen_id = int(last_seen_raw)
        except ValueError:
            pass

    # Replay persisted events first (within last 500)
    log_path = workspace / ".arc" / "events" / "event-log.jsonl"
    writer = get_writer(log_path)
    for seq, event in writer.replay_from(last_seen_id):
        if event.event_type not in _SSE_PUSH_EVENT_TYPES:
            continue
        payload = json.dumps(event.model_dump(mode="json"), default=str)
        await response.write(f"id: {seq}\nevent: {event.event_type}\ndata: {payload}\n\n".encode())

    # Subscribe to live events
    bus = get_bus()
    queue = bus.stream("*")

    # Also subscribe to bus to persist new events
    def _persist_and_publish(ev: "ArcEvent") -> None:  # noqa: F821
        writer.write(ev)

    bus.subscribe_all(_persist_and_publish)

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await response.write(b": heartbeat\n\n")
                if response.task is None or response.task.done():
                    break
                continue

            if event is None:
                # Bus closed
                break

            if event.event_type not in _SSE_PUSH_EVENT_TYPES:
                continue

            # Get seq from writer (written by _persist_and_publish)
            payload = json.dumps(event.model_dump(mode="json"), default=str)
            await response.write(f"event: {event.event_type}\ndata: {payload}\n\n".encode())

            # Check if client disconnected
            if response.task is not None and response.task.done():
                break

    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        bus.close_stream("*", queue)
        bus.unsubscribe_all(_persist_and_publish)

    return response


def setup_routes(app: web.Application) -> None:
    app.router.add_get("/health", health)
    app.router.add_get("/api/inspect", inspect)
    app.router.add_get("/api/runtimes", runtimes)
    app.router.add_get("/api/runtimes/capabilities", runtime_capabilities)
    app.router.add_get("/api/workflows", workflows)
    app.router.add_get("/api/schemas", schemas)
    app.router.add_get("/api/runs", list_runs)
    app.router.add_get("/api/runs/start", start_run)
    app.router.add_post("/api/runs/start", start_run)
    app.router.add_get("/api/runs/{run_id}", get_run)
    app.router.add_get("/api/runs/{run_id}/events", run_events_sse)
    app.router.add_get("/api/runs/{run_id}/links", run_links)
    app.router.add_post("/api/sessions/write", sessions_write)
    app.router.add_delete("/api/sessions/{session_id}", sessions_delete)
    app.router.add_patch("/api/sessions/{session_id}", sessions_update)
    app.router.add_get("/api/sse/proof", sse_proof)
    app.router.add_get("/api/events/stream", events_stream)
    app.router.add_post("/api/telemetry/export/{run_id}", export_trace)
    app.router.add_get("/api/context/pack", context_pack)
    app.router.add_get("/api/providers", providers)
    app.router.add_get("/api/providers/status", providers_status)
    app.router.add_get("/api/providers/accounts", providers_accounts)
    app.router.add_post("/api/providers/accounts", providers_accounts)
    app.router.add_patch("/api/providers/accounts/{account_id}", providers_account)
    app.router.add_delete("/api/providers/accounts/{account_id}", providers_account)
    app.router.add_post("/api/providers/accounts/{account_id}/test", providers_account_test)
    app.router.add_get("/api/providers/routing", providers_routing)
    app.router.add_put("/api/providers/routing", providers_routing)
    app.router.add_post("/api/providers/proxy/chat", providers_proxy_chat)
    app.router.add_post("/api/providers/proxy/responses", providers_proxy_chat)
    app.router.add_post("/api/providers/diagnostics/redacted", providers_diagnostics)
    app.router.add_get("/api/runs/diff", runs_diff)
    app.router.add_post("/api/evals/run", runs_eval)
    app.router.add_get("/api/tasks", tasks_list)
    app.router.add_post("/api/tasks", tasks_create)
    app.router.add_get("/api/tasks/{task_id}", tasks_get)
    app.router.add_delete("/api/tasks/{task_id}", tasks_delete)
    app.router.add_get("/api/arena/models", arena_models)
    app.router.add_get("/api/arena/tags", arena_tags)
    app.router.add_post("/api/arena/chat", arena_chat)
    app.router.add_post("/api/arena/vote", arena_vote)
    app.router.add_post("/api/arena/adopt", arena_adopt)
    app.router.add_get("/api/arena/rankings", arena_rankings)
