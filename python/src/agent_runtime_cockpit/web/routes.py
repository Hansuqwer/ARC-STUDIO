"""
ARC HTTP Routes

All routes return ArcEnvelope JSON.
CORS is restricted to localhost only (security boundary).
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import aiohttp.web as web

from ..adapters.registry import default_registry
from ..context.pack import ContextPackGenerator
from ..orchestration import runtime_router
from ..protocol.envelope import ok, err
from ..protocol.errors import ArcErrorCode
from ..protocol.schemas import WorkspaceInfo
from ..security.validation import validate_workspace_path
from ..security.redaction import Redactor
from ..storage.jsonl import JsonlTraceStore
from ..telemetry.otlp_exporter import export_run_to_otlp, validate_otlp_endpoint
from ..workspace import iter_workspace_files
from ..providers import (
    PROVIDERS,
    ProviderAccountStore,
    ProviderRequest,
    ProviderRoutingPolicy,
    ProviderRoutingStore,
    dry_run_proxy,
    provider_statuses,
    redacted_diagnostics,
)
from .keys import WORKSPACE_KEY

log = logging.getLogger(__name__)
redactor = Redactor()
ctx_gen = ContextPackGenerator()
RUNTIME_IDS = set(runtime_router.KNOWN_RUNTIMES) | {"auto"}
START_TIME = time.time()


def _workspace(request: web.Request) -> Path:
    ws = request.query.get("workspace", "")
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


async def health(request: web.Request) -> web.Response:
    """Health check endpoint with daemon status."""
    store = _trace_store(request)
    all_runs = store.list_runs()
    active_runs = [r for r in all_runs if r.status in ('running', 'pending')]
    
    return _json({
        "status": "healthy",
        "version": "0.1.0-alpha",
        "uptime_seconds": int(time.time() - START_TIME),
        "active_runs": len(active_runs),
        "arc": True,
    })


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

    envelope = ok(info.model_dump(), workspace=str(workspace),
                  duration_ms=(time.time() - t0) * 1000)
    return _json(envelope.model_dump())


async def runtimes(request: web.Request) -> web.Response:
    t0 = time.time()
    workspace = _workspace(request)
    registry = default_registry()
    detected = registry.detect_all(workspace)
    envelope = ok([r.model_dump() for r in detected], workspace=str(workspace),
                  duration_ms=(time.time() - t0) * 1000)
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

    envelope = ok(results, workspace=str(workspace),
                  duration_ms=(time.time() - t0) * 1000)
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

    envelope = ok(results, workspace=str(workspace),
                  duration_ms=(time.time() - t0) * 1000)
    return _json(envelope.model_dump())


async def start_run(request: web.Request) -> web.Response:
    """Start a run. GET is legacy; POST JSON is canonical. Both share runtime routing."""
    t0 = time.time()
    body: dict = {}
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return _json(err(ArcErrorCode.INVALID_INPUT, "Invalid JSON request body", details={"code": "invalid_json"}).model_dump(), 400)
    workflow_id = str(body.get("workflow_id") or request.query.get("workflow_id", "wf-swarmgraph-fixture"))
    raw_runtime = body.get("runtime") if "runtime" in body else request.query.get("runtime", "auto")
    runtime = [str(item) for item in raw_runtime] if isinstance(raw_runtime, list) else str(raw_runtime)
    runtime_ids = runtime if isinstance(runtime, list) else [runtime]
    if any(runtime_id not in RUNTIME_IDS for runtime_id in runtime_ids):
        return _json(err("invalid_runtime", f"Invalid runtime: {runtime}").model_dump(), 400)
    workspace = _workspace(request)
    allow_paid_calls = bool(body.get("allow_paid_calls")) or request.query.get("allow_paid_calls", "").lower() in {"1", "true", "yes"}
    inputs = body.get("inputs") if isinstance(body.get("inputs"), dict) else {}
    try:
        routed = runtime_router.resolve(workspace, runtime, allow_paid_calls=allow_paid_calls)
    except runtime_router.UnknownRuntime as exc:
        return _json(err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": exc.code}).model_dump(), 400)
    except runtime_router.RuntimeRouterError as exc:
        return _json(err(ArcErrorCode.NOT_IMPLEMENTED, str(exc), details={"code": exc.code}).model_dump(), 501)

    try:
        run = await routed.adapter.run_workflow(workflow_id, {**inputs, "workspace": str(workspace), "allow_paid_calls": allow_paid_calls})
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
    run_id = request.match_info["run_id"]
    run = _trace_store(request).load(run_id)
    if not run:
        return _json(err(ArcErrorCode.RUN_NOT_FOUND, f"Run {run_id} not found").model_dump(), 404)
    return _json(ok(run.model_dump()).model_dump())


async def list_runs(request: web.Request) -> web.Response:
    store = _trace_store(request)
    run_ids = store.list_runs()
    runs = [r for rid in run_ids if (r := store.load(rid)) is not None]
    runtime_filter = request.query.get("runtime")
    if runtime_filter:
        runs = [r for r in runs if r.runtime == runtime_filter]
    return _json(ok([r.model_dump() for r in runs]).model_dump())


async def context_pack(request: web.Request) -> web.Response:
    task = request.query.get("task", "agent runtime inspection")
    workspace = _workspace(request)
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
        body = await request.json()
        policy = ProviderRoutingPolicy.model_validate(body)
        return _json(ok(store.set(policy).model_dump()).model_dump())
    return _json(ok(store.get().model_dump()).model_dump())


async def providers_accounts(request: web.Request) -> web.Response:
    store = ProviderAccountStore()
    if request.method == "POST":
        body = await request.json()
        if body.get("api_key"):
            return _json(err(ArcErrorCode.INVALID_INPUT, "Direct key storage requires secure keychain; use api_key_env.").model_dump(), 400)
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
    if request.method == "DELETE":
        return _json(ok({"deleted": store.delete(account_id), "account_id": account_id}).model_dump())
    body = await request.json()
    if "enabled" in body:
        account = store.set_enabled(account_id, bool(body["enabled"]))
        if account:
            return _json(ok(account.model_dump()).model_dump())
    return _json(err(ArcErrorCode.INVALID_INPUT, f"Provider account not found: {account_id}").model_dump(), 404)


async def providers_account_test(request: web.Request) -> web.Response:
    if os.environ.get("ARC_ALLOW_LIVE_PROVIDER_TESTS") != "true":
        return _json(ok({"account_id": request.match_info["account_id"], "dry_run": True, "status": "not_checked", "message": "Live provider tests disabled."}).model_dump())
    return _json(err(ArcErrorCode.NOT_IMPLEMENTED, "Live provider health checks are not implemented yet.").model_dump(), 501)


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


async def run_events_sse(request: web.Request) -> web.StreamResponse:
    """AG-UI-compatible SSE stream for run events."""
    run_id = request.match_info["run_id"]
    response = web.StreamResponse(headers={
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": _cors_origin(),
    })
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

    await response.write(b"data: {\"type\": \"STREAM_END\"}\n\n")
    return response


async def export_trace(request: web.Request) -> web.Response:
    """Export run trace to OTLP endpoint."""
    run_id = request.match_info["run_id"]
    
    try:
        body = await request.json()
        endpoint = body.get("endpoint", "")
    except Exception:
        return _json(err(ArcErrorCode.INVALID_INPUT, "Invalid JSON body").model_dump(), 400)
    
    # Validate endpoint
    is_valid, warning = validate_otlp_endpoint(endpoint)
    if not is_valid:
        return _json(err(ArcErrorCode.INVALID_INPUT, warning or "Invalid endpoint").model_dump(), 400)
    
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


def setup_routes(app: web.Application) -> None:
    app.router.add_get("/health",                health)
    app.router.add_get("/api/inspect",           inspect)
    app.router.add_get("/api/runtimes",          runtimes)
    app.router.add_get("/api/runtimes/capabilities", runtime_capabilities)
    app.router.add_get("/api/workflows",         workflows)
    app.router.add_get("/api/schemas",           schemas)
    app.router.add_get("/api/runs",              list_runs)
    app.router.add_get("/api/runs/start",        start_run)
    app.router.add_post("/api/runs/start",       start_run)
    app.router.add_get("/api/runs/{run_id}",     get_run)
    app.router.add_get("/api/runs/{run_id}/events", run_events_sse)
    app.router.add_post("/api/telemetry/export/{run_id}", export_trace)
    app.router.add_get("/api/context/pack",      context_pack)
    app.router.add_get("/api/providers",         providers)
    app.router.add_get("/api/providers/status",  providers_status)
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
