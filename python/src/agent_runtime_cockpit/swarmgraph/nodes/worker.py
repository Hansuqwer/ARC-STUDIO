from __future__ import annotations

import asyncio
import os
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol

from ...cli_repl.cancellation import never_cancelled
from ...providers.base import ProviderMessage, ProviderRequest, ProviderResponse
from ...providers.registry import get as get_provider
from ..config import ExecutionMode
from ..models import (
    SwarmTask,
    TaskStatus,
    WorkerResult,
)


class CancellationTokenLike(Protocol):
    is_cancelled: Any

    def raise_if_cancelled(self) -> None: ...


def worker_execute(
    task: SwarmTask,
    mode: ExecutionMode = ExecutionMode.fake_offline,
    timeout: float = 30.0,
) -> WorkerResult:
    if mode == ExecutionMode.gated_local:
        return _run_coro_sync(worker_execute_async(task, mode=mode, timeout=timeout))

    return _worker_execute_sync(task, mode=mode, timeout=timeout)


async def worker_execute_async(
    task: SwarmTask,
    mode: ExecutionMode = ExecutionMode.fake_offline,
    timeout: float = 30.0,
    cancellation_token: CancellationTokenLike | None = None,
) -> WorkerResult:
    if mode == ExecutionMode.gated_local:
        return await _worker_execute_gated_local(
            task,
            timeout=timeout,
            cancellation_token=cancellation_token,
        )
    return _worker_execute_sync(task, mode=mode, timeout=timeout)


def _worker_execute_sync(
    task: SwarmTask,
    mode: ExecutionMode = ExecutionMode.fake_offline,
    timeout: float = 30.0,
) -> WorkerResult:
    started = datetime.now(timezone.utc)
    t0 = time.time()

    if mode == ExecutionMode.fake_offline:
        output = f"Fake deterministic response for: {task.prompt[:80]}"
        elapsed = time.time() - t0
        if elapsed > timeout:
            return WorkerResult(
                worker_id=task.assigned_agent_id or "unknown",
                task_id=task.id,
                output="",
                error="timeout",
                duration_seconds=elapsed,
                started_at=started,
            )
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output=output,
            duration_seconds=elapsed,
            started_at=started,
            completed_at=datetime.now(timezone.utc),
        )

    elapsed = time.time() - t0
    return WorkerResult(
        worker_id=task.assigned_agent_id or "unknown",
        task_id=task.id,
        output="",
        error=f"unsupported mode: {mode}",
        duration_seconds=elapsed,
        started_at=started,
    )


async def _worker_execute_gated_local(
    task: SwarmTask,
    timeout: float,
    cancellation_token: CancellationTokenLike | None,
) -> WorkerResult:
    started = datetime.now(timezone.utc)
    t0 = time.time()
    provider_id = os.environ.get("ARC_SWARMGRAPH_PROVIDER", "anthropic")

    try:
        client = get_provider(provider_id)
    except KeyError:
        client = None

    if client is None:
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="",
            error=f"provider not available: {provider_id}",
            duration_seconds=time.time() - t0,
            started_at=started,
        )

    try:
        model = os.environ.get("ARC_SWARMGRAPH_MODEL") or client.capabilities().default_model
        request = ProviderRequest(
            model=model,
            messages=[ProviderMessage(role="user", content=task.prompt)],
            max_tokens=1024,
        )
        provider_token = cancellation_token or never_cancelled()
        response = await _complete_provider_with_timeout(
            client,
            request,
            provider_token,
            timeout,
        )
        elapsed = time.time() - t0
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output=response.content[:65536],
            duration_seconds=elapsed,
            cost_usd=_response_cost_usd(client, response, model),
            token_count=_response_token_count(response),
            started_at=started,
            completed_at=datetime.now(timezone.utc),
        )
    except TimeoutError:
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="",
            error="timeout",
            duration_seconds=time.time() - t0,
            started_at=started,
        )
    except Exception as exc:
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="",
            error=f"gated_local error: {exc}",
            duration_seconds=time.time() - t0,
            started_at=started,
        )


def _response_token_count(response: Any) -> int:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0
    return sum(
        int(getattr(usage, field, 0) or 0)
        for field in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        )
    )


def _response_cost_usd(client: Any, response: Any, requested_model: str) -> float:
    extract_cost = getattr(client, "extract_cost", None)
    if callable(extract_cost):
        try:
            return float(extract_cost(response).cost_usd)
        except Exception:
            pass

    usage = getattr(response, "usage", None)
    if usage is None:
        return 0.0
    try:
        capability = client.capabilities()
        rates = capability.cost_rates.get(getattr(response, "model", requested_model))
        if rates is None:
            rates = capability.cost_rates.get(requested_model)
        if rates is None:
            return 0.0
        cost = Decimal(str(getattr(usage, "input_tokens", 0) or 0)) * Decimal(
            str(rates.input_per_million)
        )
        cost += Decimal(str(getattr(usage, "output_tokens", 0) or 0)) * Decimal(
            str(rates.output_per_million)
        )
        if rates.cache_write_per_million is not None:
            cost += Decimal(str(getattr(usage, "cache_creation_input_tokens", 0) or 0)) * Decimal(
                str(rates.cache_write_per_million)
            )
        if rates.cache_read_per_million is not None:
            cost += Decimal(str(getattr(usage, "cache_read_input_tokens", 0) or 0)) * Decimal(
                str(rates.cache_read_per_million)
            )
        return float(cost / Decimal("1000000"))
    except Exception:
        return 0.0


async def _complete_provider_with_timeout(
    client: Any,
    request: ProviderRequest,
    cancellation_token: CancellationTokenLike,
    timeout: float,
) -> ProviderResponse:
    loop = asyncio.get_running_loop()
    done = asyncio.Event()
    result: dict[str, ProviderResponse | BaseException] = {}

    def run_complete() -> None:
        try:
            result["response"] = asyncio.run(
                client.complete(request, cancellation_token=cancellation_token)
            )
        except BaseException as exc:
            result["error"] = exc
        finally:
            try:
                loop.call_soon_threadsafe(done.set)
            except RuntimeError:
                pass

    threading.Thread(target=run_complete, daemon=True).start()
    await asyncio.wait_for(done.wait(), timeout=timeout)
    error = result.get("error")
    if isinstance(error, BaseException):
        raise error
    response = result.get("response")
    if not isinstance(response, ProviderResponse):
        raise RuntimeError("provider returned no response")
    return response


def process_worker_results(
    tasks: list[SwarmTask],
    results: list[WorkerResult],
) -> list[SwarmTask]:
    result_map = {r.task_id: r for r in results}
    for task in tasks:
        if task.id in result_map:
            task.result = result_map[task.id]
            if result_map[task.id].error:
                task.status = TaskStatus.failed
            else:
                task.status = TaskStatus.completed
            task.updated_at = datetime.now(timezone.utc)
    return tasks


def _run_coro_sync(coro) -> WorkerResult:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: WorkerResult | None = None
    error: BaseException | None = None

    def run_in_thread() -> None:
        nonlocal result, error
        try:
            result = asyncio.run(coro)
        except BaseException as exc:
            error = exc

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    if error is not None:
        raise error
    if result is None:
        raise RuntimeError("worker coroutine returned no result")
    return result
