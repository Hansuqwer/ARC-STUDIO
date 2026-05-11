"""
ARC HTTP Routes

All routes return ArcEnvelope JSON.
CORS is restricted to localhost only (security boundary).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import aiohttp.web as web

from ..adapters.registry import default_registry
from ..context.pack import ContextPackGenerator
from ..protocol.envelope import ok, err
from ..protocol.errors import ArcErrorCode
from ..protocol.schemas import WorkspaceInfo
from ..security.validation import validate_workspace_path
from ..security.redaction import Redactor
from ..storage.jsonl import JsonlTraceStore
from ..workspace import iter_workspace_files

log = logging.getLogger(__name__)
redactor = Redactor()
trace_store = JsonlTraceStore()
ctx_gen = ContextPackGenerator()


def _workspace(request: web.Request) -> Path:
    ws = request.query.get("workspace", "")
    if not ws:
        return request.app["workspace"]
    try:
        return validate_workspace_path(ws)
    except ValueError:
        return request.app["workspace"]


def _json(data: dict, status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps(data, default=str),
        content_type="application/json",
        status=status,
        headers={"Access-Control-Allow-Origin": "http://localhost:3000"},
    )


async def health(request: web.Request) -> web.Response:
    return _json({"status": "ok", "version": "0.1.0a0", "arc": True})


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
    t0 = time.time()
    workflow_id = request.query.get("workflow_id", "wf-swarmgraph-fixture")
    registry = default_registry()

    # Find adapter that can run
    for adapter in registry.all():
        if adapter.capabilities().can_run:
            try:
                run = await adapter.run_workflow(workflow_id)
                trace_store.save(run)
                envelope = ok(run.model_dump(), adapter=adapter.adapter_id,
                              duration_ms=(time.time() - t0) * 1000)
                return _json(envelope.model_dump())
            except Exception as e:
                return _json(err(ArcErrorCode.RUN_FAILED, str(e)).model_dump(), 500)

    return _json(
        err(ArcErrorCode.NOT_IMPLEMENTED, "No adapter supports real workflow execution yet").model_dump(),
        501,
    )


async def get_run(request: web.Request) -> web.Response:
    run_id = request.match_info["run_id"]
    run = trace_store.load(run_id)
    if not run:
        return _json(err(ArcErrorCode.RUN_NOT_FOUND, f"Run {run_id} not found").model_dump(), 404)
    return _json(ok(run.model_dump()).model_dump())


async def list_runs(request: web.Request) -> web.Response:
    run_ids = trace_store.list_runs()
    runs = [r for rid in run_ids if (r := trace_store.load(rid)) is not None]
    return _json(ok([r.model_dump() for r in runs]).model_dump())


async def context_pack(request: web.Request) -> web.Response:
    task = request.query.get("task", "agent runtime inspection")
    workspace = _workspace(request)
    entries = ctx_gen.generate(task, workspace, save=True)
    # Redact before sending to frontend
    safe = [redactor.redact_dict(e.model_dump()) for e in entries]
    return _json(ok(safe).model_dump())


async def run_events_sse(request: web.Request) -> web.StreamResponse:
    """AG-UI-compatible SSE stream for run events."""
    run_id = request.match_info["run_id"]
    response = web.StreamResponse(headers={
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "http://localhost:3000",
    })
    await response.prepare(request)

    run = trace_store.load(run_id)
    if run:
        for event in run.events:
            data = json.dumps(event.model_dump(), default=str)
            await response.write(f"data: {data}\n\n".encode())

    await response.write(b"data: {\"type\": \"STREAM_END\"}\n\n")
    return response


def setup_routes(app: web.Application) -> None:
    app.router.add_get("/health",                health)
    app.router.add_get("/api/inspect",           inspect)
    app.router.add_get("/api/runtimes",          runtimes)
    app.router.add_get("/api/workflows",         workflows)
    app.router.add_get("/api/schemas",           schemas)
    app.router.add_get("/api/runs",              list_runs)
    app.router.add_get("/api/runs/start",        start_run)
    app.router.add_get("/api/runs/{run_id}",     get_run)
    app.router.add_get("/api/runs/{run_id}/events", run_events_sse)
    app.router.add_get("/api/context/pack",      context_pack)
