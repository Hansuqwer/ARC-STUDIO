# Phase 106 — SwarmGraph Runtime Hardening: Execution Handover

**Created:** 2026-05-29
**For:** New agent session executing Phase 106
**Branch:** `build/no-mockups-handoff` (current working branch)
**Pre-read required:** This document is self-contained. Do not read other handover docs.

---

## Session Prompt (copy-paste to start)

```
Execute Phase 106 — SwarmGraph Runtime Hardening from docs/handover/PHASE-106-SWARMGRAPH-HARDENING.md.

Before writing any code:
1. Read this handover doc completely
2. Read the files listed in "Key Files to Modify"
3. Read docs/roadmap.md section R77
4. Read docs/phases.md section Phase 106

Implementation order: Slice 106.1 → 106.5 → 106.4 → 106.3 → 106.2 → 106.6

After each slice:
- Run: cd python && uv run ruff check src tests
- Run: cd python && uv run pytest tests/swarmgraph/ tests/test_swarmgraph_native.py -q
- Run: cd python && uv run pytest tests/ -q
- Fix any failures before proceeding

Do not:
- Break existing fake_offline tests
- Add provider network calls to default test paths
- Claim provider-backed execution until tests prove it
- Modify files outside the listed scope without justification
- Remove existing test coverage
```

---

## What Exists Today

### SwarmGraph Runtime (`python/src/agent_runtime_cockpit/swarmgraph/`)

| File | Purpose | Lines |
|------|---------|-------|
| `__init__.py` | Public API re-exports | 95 |
| `config.py` | `SwarmGraphConfig` (frozen Pydantic), `ExecutionMode` enum (`fake_offline`, `gated_local`, `provider_backed`) | 74 |
| `models.py` | `AgentSpec`, `AgentState`, `AgentVote`, `ApprovalDecision`, `WorkerResult`, `QueenDirective`, `SwarmTask` | 147 |
| `state.py` | `SwarmState` (mutable), `SwarmCheckpoint` (frozen), checkpoint/restore/fork | 93 |
| `graph.py` | `build_swarm_graph()`, `SwarmGraphTopology`, `GraphNode`, `GraphEdge` | 85 |
| `runner.py` | `SwarmGraphRunner.run()` — main orchestration loop (SYNCHRONOUS, SEQUENTIAL) | 170 |
| `consensus.py` | 10 consensus protocol implementations + `run_consensus()` dispatcher | 746 |
| `consensus_escrow.py` | Commit-reveal cryptographic voting | 355 |
| `risk_assessment.py` | Deterministic heuristic risk assessor + 100 fixtures | 931 |
| `adaptive_consensus.py` | Context-aware risk escalation wrapper | 284 |
| `events.py` | `SwarmGraphEvent` + 7 event kinds + factory functions | 184 |
| `fixtures.py` | `run_deterministic_swarm()`, `run_hitl_swarm()`, `run_budget_swarm()` | 52 |
| `nodes/__init__.py` | Empty | 0 |
| `nodes/queen.py` | `queen_prepare_agents()`, `queen_decompose()`, `queen_assign()` | 102 |
| `nodes/worker.py` | `worker_execute()` (fake_offline ONLY), `process_worker_results()` | 67 |
| `nodes/consensus.py` | `run_consensus_round_with_results()`, adaptive per-task selection | 354 |
| `nodes/approval.py` | `require_hitl_approval()`, `approve_hitl()`, `reject_hitl()` | 69 |

### Provider Infrastructure (Phase 20, already exists)

| File | Purpose |
|------|---------|
| `providers/__init__.py` | Exports |
| `providers/base.py` | `ProviderClient` protocol: `complete()`, `stream()`, `cancel()` |
| `providers/registry.py` | `get(provider_id)`, `known()`, auto-registration |
| `providers/anthropic.py` | `AnthropicClient` implementing ProviderClient |
| `providers/openai_compatible.py` | `OpenAICompatibleClient` for 6 vendors |
| `providers/budget_preflight.py` | `preflight_with_estimator()` |
| `budget.py` | `BudgetEnforcer` with Decimal arithmetic |
| `runtime/turn_manager.py` | `TurnManager` — drives request→response→tool loops |

### Key Tests

| File | Tests | Purpose |
|------|-------|---------|
| `tests/test_swarmgraph_native.py` | ~57 | Core runtime: config, models, consensus, state, graph, events, nodes, runner |
| `tests/swarmgraph/test_consensus_differentiators.py` | 5 | Extended consensus protocols |
| `tests/swarmgraph/test_consensus_escrow.py` | 26 | Commit-reveal voting |
| `tests/swarmgraph/test_risk_assessment.py` | ~20 | Risk assessment fixtures |
| `tests/swarmgraph/test_adaptive_consensus.py` | ~15 | Context-aware escalation |
| `tests/test_swarmgraph_topology.py` | 7 | Adapter event mapping |
| `tests/adapters/swarmgraph/` | ~20 | Adapter security, mapping, gateway |

---

## What's Wrong (from analysis)

1. **`worker_execute()` only handles `fake_offline`** — `gated_local` returns an error string
2. **Workers execute sequentially** — no asyncio, no parallelism
3. **No fan-out gate** — always creates N tasks regardless of prompt complexity
4. **Workers see the full prompt** — no context isolation between workers
5. **Events are memory-only** — no streaming callback, adapter must poll after completion
6. **No failure detection** — 0 of 13 ADR-013 failure modes are detected
7. **Consensus protocols are identical in practice** — fake_offline produces 1 auto-approved vote per task, making all 10 protocols return the same result

---

## Implementation Plan (Recommended Order)

### Why this order: 106.1 → 106.5 → 106.4 → 106.3 → 106.2 → 106.6

- **106.1** (ProviderClient worker) — smallest meaningful change, enables real execution
- **106.5** (event callback) — tiny change, immediately useful for testing
- **106.4** (context isolation) — small, independent, security value
- **106.3** (decomposition + fan-out) — medium, creates differentiated tasks for multiple workers
- **106.2** (async parallel) — largest change, benefits from all prior slices
- **106.6** (failure detectors) — only meaningful once real execution can fail

---

## Slice 106.1 — Wire ProviderClient into gated_local Worker

### Goal
Make `worker_execute(task, mode=ExecutionMode.gated_local)` produce real LLM output.

### Implementation

**File: `python/src/agent_runtime_cockpit/swarmgraph/nodes/worker.py`**

```python
# Add import at top
from ...providers.registry import get as get_provider

# Add new branch in worker_execute():
if mode == ExecutionMode.gated_local:
    try:
        provider_id = os.environ.get("ARC_SWARMGRAPH_PROVIDER", "anthropic")
        model = os.environ.get("ARC_SWARMGRAPH_MODEL", "claude-sonnet-4-20250514")
        client = get_provider(provider_id)
        if client is None:
            return WorkerResult(
                worker_id=task.assigned_agent_id or "unknown",
                task_id=task.id,
                output="",
                error=f"provider not available: {provider_id}",
                duration_seconds=time.time() - t0,
                started_at=started,
            )
        # Use sync wrapper (providers are async)
        import asyncio
        response = asyncio.run(client.complete(
            messages=[{"role": "user", "content": task.prompt}],
            model=model,
            max_tokens=1024,
        ))
        elapsed = time.time() - t0
        if elapsed > timeout:
            return WorkerResult(...)  # timeout
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output=response.content[:65536],
            duration_seconds=elapsed,
            cost_usd=response.cost_usd if hasattr(response, 'cost_usd') else 0.0,
            token_count=response.usage.total_tokens if hasattr(response, 'usage') else 0,
            started_at=started,
            completed_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        elapsed = time.time() - t0
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="",
            error=f"gated_local error: {e}",
            duration_seconds=elapsed,
            started_at=started,
        )
```

### Tests to add (`tests/swarmgraph/test_provider_worker.py`)

```python
import pytest
from unittest.mock import AsyncMock, patch
from agent_runtime_cockpit.swarmgraph.nodes.worker import worker_execute
from agent_runtime_cockpit.swarmgraph.config import ExecutionMode
from agent_runtime_cockpit.swarmgraph.models import SwarmTask

def test_gated_local_calls_provider(monkeypatch):
    """gated_local mode calls ProviderClient.complete()."""
    mock_client = AsyncMock()
    mock_client.complete.return_value = MockResponse(content="real output", cost_usd=0.001)
    monkeypatch.setattr("...registry.get", lambda _: mock_client)

    task = SwarmTask(prompt="test prompt")
    task.assigned_agent_id = "worker-1"
    result = worker_execute(task, mode=ExecutionMode.gated_local)
    assert result.output == "real output"
    assert result.cost_usd == 0.001
    assert result.error is None

def test_gated_local_provider_unavailable(monkeypatch):
    """gated_local mode returns error when provider not found."""
    monkeypatch.setattr("...registry.get", lambda _: None)
    task = SwarmTask(prompt="test")
    task.assigned_agent_id = "worker-1"
    result = worker_execute(task, mode=ExecutionMode.gated_local)
    assert result.error is not None
    assert "not available" in result.error

def test_gated_local_provider_exception(monkeypatch):
    """gated_local mode returns error on provider exception."""
    mock_client = AsyncMock()
    mock_client.complete.side_effect = RuntimeError("API error")
    monkeypatch.setattr("...registry.get", lambda _: mock_client)
    task = SwarmTask(prompt="test")
    task.assigned_agent_id = "worker-1"
    result = worker_execute(task, mode=ExecutionMode.gated_local)
    assert result.error is not None
    assert "API error" in result.error
```

### Acceptance check
- `fake_offline` tests still pass unchanged
- `gated_local` tests use mocked provider (no real network)
- No test requires `ARC_SWARMGRAPH_PROVIDER_TESTS=1` unless it makes real calls

---

## Slice 106.5 — Event Streaming Callback

### Goal
Runner accepts an optional callback that fires on every event emission.

### Implementation

**File: `python/src/agent_runtime_cockpit/swarmgraph/runner.py`**

```python
class SwarmGraphRunner:
    def __init__(self, config: SwarmGraphConfig | None = None, on_event: Callable[[SwarmGraphEvent], None] | None = None):
        self.config = config or SwarmGraphConfig()
        self.state: SwarmState | None = None
        self.events: list[SwarmGraphEvent] = []
        self._on_event = on_event

    def _emit(self, event: SwarmGraphEvent) -> None:
        """Append event to internal list and invoke callback if set."""
        self.events.append(event)
        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:
                pass  # callback errors must not crash the runner
```

Then replace all `self.events.append(...)` calls in `run()` with `self._emit(...)`.

### Tests

```python
def test_on_event_callback_fires():
    received = []
    runner = SwarmGraphRunner(on_event=received.append)
    runner.run("test prompt")
    assert len(received) > 0
    assert received == runner.events

def test_on_event_callback_error_does_not_crash():
    def bad_callback(e): raise RuntimeError("boom")
    runner = SwarmGraphRunner(on_event=bad_callback)
    result = runner.run("test prompt")
    assert result["status"] == "completed"  # did not crash
```

---

## Slice 106.4 — Worker Context Isolation

### Goal
Workers receive only their assigned task's prompt, not the full state or sibling tasks.

### Implementation

**File: `python/src/agent_runtime_cockpit/swarmgraph/nodes/worker.py`**

The current `worker_execute()` already only receives a `SwarmTask` object — it doesn't have access to `SwarmState`. The isolation gap is in `queen_decompose()` which copies the SAME prompt to all workers in star topology.

**Real fix in `nodes/queen.py`:**
- Add a `context` field to the task metadata that contains ONLY the sub-task description
- For star topology: each task gets a unique perspective instruction (e.g., "Worker 1 of 3: provide your independent analysis of: {prompt}")
- For chain topology: each step gets only the previous step's output (already partially done via parent_task_id)

```python
def queen_decompose(state: SwarmState, prompt: str) -> list[SwarmTask]:
    tasks: list[SwarmTask] = []
    num_workers = state.config.num_workers

    if state.config.topology == SwarmTopology.star:
        for i in range(num_workers):
            # Context isolation: each worker gets a scoped perspective
            scoped_prompt = (
                f"You are worker {i + 1} of {num_workers}. "
                f"Provide your independent analysis. Do not assume knowledge of other workers' outputs.\n\n"
                f"{prompt}"
            )
            task = SwarmTask(
                prompt=scoped_prompt,
                priority=TaskPriority.medium,
                metadata={"worker_index": i, "total_workers": num_workers, "isolated": True},
            )
            tasks.append(task)
    # ... chain stays the same
```

### Tests

```python
def test_star_workers_get_isolated_prompts():
    """Star topology gives each worker a unique scoped prompt."""
    cfg = SwarmGraphConfig(num_workers=3, topology=SwarmTopology.star)
    state = SwarmState(config=cfg)
    queen_prepare_agents(state, 3)
    tasks = queen_decompose(state, "analyze this data")
    # Each task has a unique prompt
    prompts = [t.prompt for t in tasks]
    assert len(set(prompts)) == 3  # all unique
    # Each mentions worker index
    assert "worker 1 of 3" in prompts[0].lower()
    assert "worker 2 of 3" in prompts[1].lower()
    # Metadata marks isolation
    assert all(t.metadata.get("isolated") for t in tasks)
```

---

## Slice 106.3 — DecompositionStrategy + Fan-Out Gate

### Goal
Pluggable decomposition and a gate that decides 1-worker vs N-worker execution.

### Implementation

**New file: `python/src/agent_runtime_cockpit/swarmgraph/decomposition.py`**

```python
from __future__ import annotations
from typing import Protocol
from .config import SwarmGraphConfig
from .models import SwarmTask

class DecompositionStrategy(Protocol):
    def decompose(self, prompt: str, num_workers: int, config: SwarmGraphConfig) -> list[SwarmTask]: ...

class TrivialDecomposition:
    """Copy prompt to all workers (star) or step-number (chain)."""
    def decompose(self, prompt: str, num_workers: int, config: SwarmGraphConfig) -> list[SwarmTask]:
        # Current behavior extracted from queen.py
        ...

def parallelizability_score(prompt: str) -> float:
    """Heuristic: 0.0 (single task) to 1.0 (highly parallelizable)."""
    sentences = prompt.count('.') + prompt.count('!') + prompt.count('?')
    words = len(prompt.split())
    # Multiple sentences/clauses suggest decomposable work
    if words < 10:
        return 0.1
    if sentences <= 1:
        return 0.3
    # Commas, "and", "then", numbered lists suggest parallel steps
    connectors = prompt.lower().count(' and ') + prompt.lower().count(' then ') + prompt.count(',')
    score = min(1.0, 0.3 + (sentences * 0.15) + (connectors * 0.1))
    return round(score, 2)
```

**File: `python/src/agent_runtime_cockpit/swarmgraph/config.py`**

Add:
```python
fan_out_threshold: float = Field(default=0.6, ge=0, le=1.0)
max_parallel_workers: int = Field(default=3, ge=1, le=50)
```

**File: `python/src/agent_runtime_cockpit/swarmgraph/runner.py`**

In `run()`, before `queen_decompose()`:
```python
from .decomposition import parallelizability_score
score = parallelizability_score(prompt)
effective_workers = cfg.num_workers if score >= cfg.fan_out_threshold else 1
# Emit fan-out decision audit event
self._emit(SwarmGraphEvent(
    kind=SwarmGraphEventKind.audit,
    swarm_id=self.state.id,
    data={"fan_out_score": score, "fan_out_threshold": cfg.fan_out_threshold, "effective_workers": effective_workers, "decision": "fan_out" if effective_workers > 1 else "single"},
    round=0,
))
# Use effective_workers instead of cfg.num_workers for decomposition
```

---

## Slice 106.2 — Async Parallel Worker Execution

### Goal
Workers run concurrently bounded by `max_parallel_workers`.

### Implementation

This is the largest slice. Key changes:

1. Add `async def run_async()` to `SwarmGraphRunner` — new async entry point
2. Keep `def run()` as sync wrapper: `return asyncio.run(self.run_async(prompt, config, cancellation_token))`
3. Convert worker loop to `asyncio.gather()` with semaphore
4. Convert `worker_execute()` to `async def worker_execute_async()` for `gated_local`; keep sync path for `fake_offline` wrapped in executor

**Critical constraint:** `SwarmState` mutation must be sequential AFTER gather completes. Do not mutate state inside concurrent tasks.

```python
async def _execute_workers_parallel(self, pending, cfg, cancellation_token):
    sem = asyncio.Semaphore(cfg.max_parallel_workers)

    async def bounded_execute(task):
        async with sem:
            if cancellation_token and cancellation_token.is_cancelled():
                return None
            return await worker_execute_async(task, mode=cfg.execution_mode, timeout=cfg.worker_timeout_seconds)

    results = await asyncio.gather(*[bounded_execute(t) for t in pending], return_exceptions=True)
    # Process results sequentially after all complete
    worker_results = []
    for r in results:
        if isinstance(r, Exception):
            # Log but don't crash
            continue
        if r is not None:
            worker_results.append(r)
    return worker_results
```

### Backward compat
- `run()` (sync) must still work for all existing callers
- `fake_offline` can use `asyncio.to_thread(worker_execute_sync, ...)` or just run sync since it's instant
- Tests that call `runner.run(prompt)` must not break

---

## Slice 106.6 — Failure Mode Detectors

### Goal
Detect 3 of 13 ADR-013 failure modes and emit typed events.

### Implementation

**New file: `python/src/agent_runtime_cockpit/swarmgraph/detectors.py`**

```python
from __future__ import annotations
from .events import SwarmGraphEvent, SwarmGraphEventKind
from .models import SwarmStatus
from .state import SwarmState
from .nodes.consensus import ConsensusRoundOutcome

def detect_consensus_failure(outcomes: list[ConsensusRoundOutcome], state: SwarmState) -> SwarmGraphEvent | None:
    """Fires when >50% of tasks in a round are rejected."""
    if not outcomes:
        return None
    rejected = sum(1 for o in outcomes if not o.decision.approved)
    if rejected > len(outcomes) / 2:
        return SwarmGraphEvent(
            kind=SwarmGraphEventKind.error,
            swarm_id=state.id,
            data={"failure_mode": "consensus_failure", "rejected_count": rejected, "total": len(outcomes)},
            round=state.current_round,
        )
    return None

def detect_resource_exhaustion(state: SwarmState, budget_limit: float | None) -> SwarmGraphEvent | None:
    """Fires when accumulated cost > 80% of budget limit."""
    if budget_limit is None or budget_limit <= 0:
        return None
    ratio = state.accumulated_cost_usd / budget_limit
    if ratio >= 0.8:
        return SwarmGraphEvent(
            kind=SwarmGraphEventKind.error,
            swarm_id=state.id,
            data={"failure_mode": "resource_exhaustion", "ratio": round(ratio, 3), "accumulated": state.accumulated_cost_usd, "limit": budget_limit},
            round=state.current_round,
        )
    return None

def detect_coordination_deadlock(state: SwarmState, previous_pending_count: int) -> SwarmGraphEvent | None:
    """Fires when same number of tasks remain pending for 2+ rounds."""
    current_pending = len(state.get_pending_tasks())
    if current_pending > 0 and current_pending == previous_pending_count and state.current_round >= 1:
        return SwarmGraphEvent(
            kind=SwarmGraphEventKind.error,
            swarm_id=state.id,
            data={"failure_mode": "coordination_deadlock", "stuck_tasks": current_pending, "rounds_stuck": 2},
            round=state.current_round,
        )
    return None
```

---

## Key Constraints

| Rule | Rationale |
|------|-----------|
| **Do not break `fake_offline` tests** | 130+ existing tests rely on deterministic fake execution |
| **Do not add real network calls to default test path** | CI must stay offline; use `monkeypatch`/`AsyncMock` for provider tests |
| **Keep `run()` sync-compatible** | REPL, adapter, and CLI all call `runner.run()` synchronously |
| **Do not mutate SwarmState inside concurrent tasks** | Race conditions; gather results, then mutate sequentially |
| **Gate provider tests behind env var** | `ARC_SWARMGRAPH_PROVIDER_TESTS=1` for real calls |
| **Do not claim "provider-backed SwarmGraph execution"** | Until real e2e test proves it with a live provider |
| **Priority 1 CLI parity (Phases 97-105) takes precedence** | If conflicts arise, defer Phase 106 work |

---

## Verification Commands

After each slice:
```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/swarmgraph/ tests/test_swarmgraph_native.py -q
cd python && uv run pytest tests/ -q
```

Full verification after all slices:
```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm build
pnpm typecheck
```

---

## Files Created/Modified Summary

### New files
- `python/src/agent_runtime_cockpit/swarmgraph/decomposition.py`
- `python/src/agent_runtime_cockpit/swarmgraph/detectors.py`
- `python/tests/swarmgraph/test_provider_worker.py`
- `python/tests/swarmgraph/test_parallel_execution.py`
- `python/tests/swarmgraph/test_decomposition.py`
- `python/tests/swarmgraph/test_detectors.py`
- `python/tests/swarmgraph/test_event_callback.py`
- `python/tests/swarmgraph/test_context_isolation.py`

### Modified files
- `python/src/agent_runtime_cockpit/swarmgraph/runner.py` (async, callback, fan-out gate, detectors)
- `python/src/agent_runtime_cockpit/swarmgraph/nodes/worker.py` (gated_local branch, async variant)
- `python/src/agent_runtime_cockpit/swarmgraph/nodes/queen.py` (context isolation in decompose)
- `python/src/agent_runtime_cockpit/swarmgraph/config.py` (fan_out_threshold, max_parallel_workers)
- `python/src/agent_runtime_cockpit/swarmgraph/__init__.py` (export new public API)

### Existing tests that MUST stay green
- `tests/test_swarmgraph_native.py` (57 tests)
- `tests/swarmgraph/test_consensus_escrow.py` (26 tests)
- `tests/swarmgraph/test_consensus_differentiators.py` (5 tests)
- `tests/swarmgraph/test_risk_assessment.py`
- `tests/swarmgraph/test_adaptive_consensus.py`
- `tests/test_swarmgraph_topology.py` (7 tests)
- `tests/adapters/swarmgraph/` (all)
- `tests/test_cli_repl.py` (uses SwarmGraphRunner)

---

## Expected Outcome

After all 6 slices:
- `worker_execute(mode=gated_local)` calls a real (mocked in tests) LLM provider
- Workers can run in parallel with configurable concurrency
- Fan-out gate decides 1-worker vs N-worker based on prompt complexity
- Workers are context-isolated (each sees only their assigned sub-task)
- Events stream live via callback during execution
- 3 failure modes are detected and emitted as events
- All existing 3406+ Python tests still pass
- ~30-50 new tests covering the 6 slices

---

## What This Does NOT Deliver

- Real provider-backed end-to-end execution (requires live API keys)
- Semantic LLM-based decomposition (requires provider calls for decomposition itself)
- All 13 failure mode detectors (only 3 of 13)
- Hierarchical multi-level orchestration (ADR-013 deferred)
- MASS topology optimization (ADR-013 Phase 6.5)
- Worker roles from prompt files (ADR-013 deferred)
- Task dependency graph (P2, deferred)
- Checkpoint auto-resume from persistent storage (P2, deferred)
