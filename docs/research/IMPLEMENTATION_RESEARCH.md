# ARC Studio Implementation Research Dossier — Scaffolds, Not Spec

**Compiled:** 2026-05-14
**Scope:** Methodology, Foundation ADRs, Execution Core P1a, Adoption Layer P1b+P2, Runtime Integrations P2, Theia Extension Architecture, Audit/HITL/Replay, Workspace Trust, Prompt Optimizer, CLI Surface, Storage, Live Event Broker
**Status:** Complete research dossier. Code blocks are design scaffolds, not production-ready reference implementations.
**Sources:** Context7 library docs, PyPI, GitHub repos, current ARC codebase, `docs/IMPLEMENTATION_PLAN.md`, `docs/adr/`, `docs/research/EXTERNAL_TOOLS_UI_RESEARCH.md`

---

## Table of Contents

- [0. Methodology](#0-methodology)
- [1. Foundation ADRs](#1-foundation-adrs)
- [2. Execution Core — P1a](#2-execution-core--p1a)
- [3. Adoption Layer — P1b + P2](#3-adoption-layer--p1b--p2)
- [4. Runtime Integrations — P2](#4-runtime-integrations--p2)
- [5. Theia Extension Architecture](#5-theia-extension-architecture)
- [6. Audit, HITL, Replay (P2 / P4)](#6-audit-hitl-replay-p2--p4)
- [7. Workspace Trust and Isolation (P1a / P2 / P3)](#7-workspace-trust-and-isolation-p1a--p2--p3)
- [8. Prompt Optimizer (P1b / P3 / P4)](#8-prompt-optimizer-p1b--p3--p4)
- [9. CLI Surface (P0–P5)](#9-cli-surface-p0p5)
- [10. Storage: JSONL + SQLite Index (P1a)](#10-storage-jsonl--sqlite-index-p1a)
- [11. Live Event Broker and SSE (P1a)](#11-live-event-broker-and-sse-p1a)

---

## 0. Methodology

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`:

> "The practical path is: 1. Make repository truth coherent and runnable. 2. Stabilize standalone adapters and capability reporting. 3. Wire canonical `packages/arc-extension` into the browser app before further UI work. 4. Add execution-core infrastructure before adoption: versioned events, JSONL+SQLite index, live broker/supervisor, workspace trust, and subprocess isolation. 5. Introduce a small SwarmGraph adoption interface before adding integrations. 6. Implement `LangGraph + SwarmGraph` first because LangGraph is closest to SwarmGraph internals."

This dossier provides research, code scaffolds, and verification procedures for phases P0-P3. It is not a spec. Before copying any scaffold into production, re-check it against `docs/IMPLEMENTATION_PLAN.md`, current source, current dependencies, and adversarial-review fixes tracked in PR #1.

### b. Current External State

This dossier was compiled on 2026-05-14 using:

- **Context7 API** for library documentation and code examples (all libraries queried via `/org/project` format)
- **PyPI** for package versions, release dates, and dependency metadata
- **GitHub** for repository activity, latest releases, and API surface
- **ARC codebase** at commit HEAD (`arc-theia-studio/`) for current implementation state
- **Python:** 3.11+, pydantic>=2.7, aiohttp>=3.9, hatchling build backend
- **TypeScript:** ^5.3.0, @theia/core ^1.45.0 (extension), 1.71.0 (browser app), Node >= 20, pnpm >= 9.15.9

All library versions cited are the latest available as of the compilation date. Version drift is expected; each section includes a "How to verify this still works" subsection.

### c. Recommended Approach for ARC

1. **Research-first, scaffold-second:** Each section begins with external library research, then produces runnable scaffolds that integrate with the existing ARC codebase.
2. **Pydantic v2 everywhere:** All new Python models use `pydantic>=2.7` with `BaseModel`, `Field`, `model_dump`, and `model_json_schema`. No v1 compatibility shims.
3. **Honest capability reporting:** Every adapter and service reports what it can and cannot do via `RuntimeCapabilities` and `CapabilityReport`. No false positives.
4. **JSONL canonical, SQLite index:** Trace data lives in JSONL files; SQLite is a rebuildable search index (ADR-003).
5. **Versioned events:** All events carry `schema_version` (ADR-004). Readers support N and N-1.
6. **Theia DI via InversifyJS:** All backend services bound explicitly in `ContainerModule`. No implicit/service-locator patterns.
7. **No overclaiming:** Scaffolds are labeled as scaffolds. Production claims require tests.

### d. Code Scaffolds

Each section includes illustrative code scaffolds. Scaffolds are starting points only and may intentionally omit production concerns until the corresponding PR lands. Scaffolds follow these conventions:

- **Python:** Typed with `pydantic.BaseModel`, tested with `pytest` + `pytest-asyncio`, formatted with `ruff` (line-length 100, target-version py311).
- **TypeScript:** Typed with interfaces, follows existing `packages/arc-extension` conventions, tested with `jest` + `ts-jest`.
- **All scaffolds include:** imports, type annotations, error handling, and at least one test where the implementation phase exists.
- **Scaffold markers:** Code blocks are labeled `[SCAFFOLD]` to distinguish from production code.
- **Production rule:** unimplemented scaffolds must fail closed: `NOT_RUNNABLE`, `RUN_FAILED`, or `NotImplementedError`. They must not emit success/completion events or successful audit records.

### e. How to Verify This Still Works

For each section:

1. **Library version check:** `pip index versions <package>` or `pnpm info <package> version`
2. **API surface check:** Import the library and call the key function in a REPL
3. **Scaffold test:** Run the included test file against the scaffold
4. **Integration smoke:** Run the scaffold against the current ARC codebase (where applicable)
5. **Context7 re-query:** Re-run the Context7 query to check for API changes

Specific verification commands are provided at the end of each section.

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| Library API drift between research and implementation | Scaffolds break | Pin versions in scaffolds; re-verify before implementation |
| Pydantic v2/v3 transition | Model validation changes | Pin `pydantic>=2.7,<3.0` until v3 is assessed |
| Theia version mismatch between extension (^1.45.0) and browser app (1.71.0) | DI/bindings break | Align versions before P3 UI work |
| Context7 docs may lag behind library releases | Outdated examples | Cross-reference with GitHub releases and PyPI |
| Vendored SwarmGraph may diverge from upstream | Adoption wrappers break | Document vendored version; add upstream sync policy |
| aiohttp-sse is lightly maintained | SSE reliability | Test against aiohttp 3.x; consider manual SSE if needed |

### g. Sources

- `docs/IMPLEMENTATION_PLAN.md` — Phase plan, scope, definitions of done
- `docs/adr/000-execution-core-contract.md` through `008-daemon-bundling.md` — Architecture decisions
- `docs/research/EXTERNAL_TOOLS_UI_RESEARCH.md` — UI/tool research from 10 external tools
- `python/pyproject.toml` — Python dependencies and build config
- `packages/arc-extension/package.json` — Theia extension dependencies
- `packages/arc-browser-app/package.json` — Browser app dependencies
- Context7 API queries for all libraries cited (per-section sources listed in each section)

---

## 1. Foundation ADRs

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "Foundation ADR Review Gate":

> "The ADR set in `docs/adr/` is accepted as a planning baseline, not as product claims. Edit ADRs before implementation if tests or platform spikes disprove assumptions."

| ADR | Plan action | Phase |
|-----|------------|-------|
| `000-execution-core-contract` | Use as the execution-core integration contract | P0-P1 |
| `001-config-model` | Add config schema/loader and `arc config init/show` | P0-P1 |
| `002-run-lifecycle-state-machine` | Add `JobSupervisor`, targeted cancel, orphan recovery, live-event broker | P1 |
| `003-storage-strategy` | Wire SQLite as index beside canonical JSONL traces | P1 |
| `004-event-schema-versioning` | Add `schema_version` and event registry | P1 |
| `005-audit-key-management` | Add audit service, verify/export CLI/endpoints, key-management spike | P2-P4 |
| `006-workspace-trust-isolation` | Add trust resolver and isolation provider interface | P1-P3 |
| `007-provider-routing-unification` | Treat ARC providers as metadata/policy; gateway owns execution | P1-P3 |
| `008-daemon-bundling` | Add packaging spike before Electron bundling | P5 |

### b. Current External State

The 8 ADRs in `docs/adr/` were authored as part of a prior architecture review. They define contracts for:

- **ADR-000:** Execution core contract — RunRequest → Config Resolution → Trust → Isolation → Supervisor → Adapter → Event Broker → Trace Store → Audit Store → HITL/Replay/Cancel. 603 lines, comprehensive.
- **ADR-001:** Config model — YAML-based config with workspace/user/env/CLI override hierarchy. Uses Pydantic models.
- **ADR-002:** Run lifecycle state machine — `PENDING → RUNNING → COMPLETED/FAILED/CANCELLED` with supervisor ownership and orphan recovery.
- **ADR-003:** Storage strategy — JSONL canonical + SQLite index. Dual-write with JSONL-first atomicity.
- **ADR-004:** Event schema versioning — `schema_version` field on all events, N/N-1 compatibility, canonical event type registry.
- **ADR-005:** Audit key management — keyed audit chains (HMAC target), keychain preferred, env fallback with degraded status.
- **ADR-006:** Workspace trust and isolation — Trust levels (UNTRUSTED/PARTIAL/TRUSTED), isolation providers (none/subprocess/docker/firecracker).
- **ADR-007:** Provider routing unification — ARC providers as metadata/policy layer; gateway owns execution.
- **ADR-008:** Daemon bundling — Packaging spike for Electron; no PyInstaller decision until measured.

**Current implementation status:**

| ADR | Python code exists? | TypeScript code exists? | Gap |
|-----|-------------------|----------------------|-----|
| 000 | Partial (schemas.py, base.py, storage/) | Partial (arc-protocol.ts) | No unified supervisor; no event broker |
| 001 | No | No | No config loader implemented |
| 002 | Partial (RunStatus enum) | Partial (status in TraceFile) | No JobSupervisor, no orphan recovery |
| 003 | Partial (jsonl.py, sqlite.py) | No | SQLite not wired into JSONL store |
| 004 | No (RunEvent has no schema_version) | No (TraceEvent has no schema_version) | No event registry |
| 005 | Partial (audit/chain.py exists) | No | No HMAC verification, no key management |
| 006 | Partial (security/ dir exists) | No | No trust resolver, no isolation interface |
| 007 | Partial (providers.py exists) | No | No gateway integration |
| 008 | No | No | Pre-P5, not urgent |

### c. Recommended Approach for ARC

1. **Accept ADRs 000–004 as P1 implementation contracts.** They are well-specified and align with current code.
2. **Accept ADRs 005–007 as P2 targets.** They depend on P1 infrastructure.
3. **Defer ADR-008 to P5.** Electron bundling is post-v0.1.
4. **Before implementing any ADR, run the verification spike** (subsection e) to confirm assumptions hold.
5. **Edit ADRs if spikes disprove assumptions.** The ADRs are planning baselines, not immutable specs.

**Priority order for implementation:**
1. ADR-004 (event versioning) — prerequisite for everything event-related
2. ADR-003 (storage) — prerequisite for run listing/search/supervisor
3. ADR-002 (lifecycle) — prerequisite for live events and cancellation
4. ADR-000 (core contract) — ties everything together
5. ADR-006 (trust/isolation) — prerequisite for safe execution
6. ADR-001 (config) — needed for profiles/workspaces
7. ADR-005 (audit keys) — P2, depends on ADR-000
8. ADR-007 (provider routing) — P2-P3, depends on ADR-000

### d. Code Scaffolds

#### [SCAFFOLD] ADR-004: Event Schema Registry (Python)

```python
# python/src/agent_runtime_cockpit/orchestration/events.py
"""Versioned event creation and registry — ADR-004 implementation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


CURRENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class EventTypeDef:
    version: int
    required_fields: frozenset[str]
    optional_fields: frozenset[str] = field(default_factory=frozenset)


EVENT_TYPES: dict[str, EventTypeDef] = {
    "RUN_STARTED": EventTypeDef(
        version=1,
        required_fields=frozenset({"workflow_id", "runtime"}),
        optional_fields=frozenset({"profile_id", "isolation", "runtime_mode"}),
    ),
    "RUN_COMPLETED": EventTypeDef(
        version=1,
        required_fields=frozenset({"duration_ms"}),
        optional_fields=frozenset({"output"}),
    ),
    "RUN_FAILED": EventTypeDef(
        version=1,
        required_fields=frozenset({"error"}),
        optional_fields=frozenset({"error_detail"}),
    ),
    "RUN_CANCELLED": EventTypeDef(
        version=1,
        required_fields=frozenset({"cancel_reason"}),
        optional_fields=frozenset(),
    ),
    "STEP_STARTED": EventTypeDef(
        version=1,
        required_fields=frozenset({"step_id", "step_name"}),
        optional_fields=frozenset({"step_type"}),
    ),
    "STEP_COMPLETED": EventTypeDef(
        version=1,
        required_fields=frozenset({"step_id"}),
        optional_fields=frozenset({"output", "duration_ms"}),
    ),
    "STEP_FAILED": EventTypeDef(
        version=1,
        required_fields=frozenset({"step_id", "error"}),
        optional_fields=frozenset(),
    ),
    "TEXT_MESSAGE_START": EventTypeDef(
        version=1,
        required_fields=frozenset({"message_id"}),
        optional_fields=frozenset({"role"}),
    ),
    "TEXT_MESSAGE_CONTENT": EventTypeDef(
        version=1,
        required_fields=frozenset({"message_id", "delta"}),
        optional_fields=frozenset(),
    ),
    "TEXT_MESSAGE_END": EventTypeDef(
        version=1,
        required_fields=frozenset({"message_id"}),
        optional_fields=frozenset(),
    ),
    "TOOL_CALL_START": EventTypeDef(
        version=1,
        required_fields=frozenset({"tool_call_id", "tool_name"}),
        optional_fields=frozenset(),
    ),
    "TOOL_CALL_ARGS": EventTypeDef(
        version=1,
        required_fields=frozenset({"tool_call_id", "delta"}),
        optional_fields=frozenset(),
    ),
    "TOOL_CALL_END": EventTypeDef(
        version=1,
        required_fields=frozenset({"tool_call_id"}),
        optional_fields=frozenset(),
    ),
    "TOOL_CALL_RESULT": EventTypeDef(
        version=1,
        required_fields=frozenset({"tool_call_id", "result"}),
        optional_fields=frozenset(),
    ),
    "STATE_SNAPSHOT": EventTypeDef(
        version=1,
        required_fields=frozenset({"state"}),
        optional_fields=frozenset({"redacted"}),
    ),
    "RAW": EventTypeDef(
        version=1,
        required_fields=frozenset({"raw"}),
        optional_fields=frozenset({"source"}),
    ),
    "CUSTOM": EventTypeDef(
        version=1,
        required_fields=frozenset({"custom_type"}),
        optional_fields=frozenset({"data"}),
    ),
}


class RunEvent(BaseModel):
    schema_version: int = CURRENT_SCHEMA_VERSION
    type: str
    timestamp: str
    run_id: str
    sequence: int
    data: dict[str, Any] = Field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_event(run_id: str, sequence: int, event_type: str, data: dict[str, Any]) -> RunEvent:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type: {event_type}")
    typedef = EVENT_TYPES[event_type]
    missing = typedef.required_fields - data.keys()
    if missing:
        raise ValueError(f"Event {event_type} missing required fields: {sorted(missing)}")
    return RunEvent(
        schema_version=typedef.version,
        type=event_type,
        timestamp=_now_iso(),
        run_id=run_id,
        sequence=sequence,
        data=data,
    )


def validate_event(event: RunEvent) -> list[str]:
    errors: list[str] = []
    if event.type not in EVENT_TYPES:
        errors.append(f"Unknown event type: {event.type}")
        return errors
    typedef = EVENT_TYPES[event.type]
    if event.schema_version > CURRENT_SCHEMA_VERSION:
        errors.append(
            f"schema_version {event.schema_version} > current {CURRENT_SCHEMA_VERSION}"
        )
    missing = typedef.required_fields - event.data.keys()
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")
    return errors
```

#### [SCAFFOLD] ADR-004: Event Registry Tests

```python
# python/tests/orchestration/test_event_registry.py
"""Tests for the versioned event registry (ADR-004)."""
import pytest
from agent_runtime_cockpit.orchestration.events import (
    RunEvent,
    create_event,
    validate_event,
    CURRENT_SCHEMA_VERSION,
    EVENT_TYPES,
)


def test_create_run_started_event():
    event = create_event(
        run_id="run-001",
        sequence=0,
        event_type="RUN_STARTED",
        data={"workflow_id": "my-agent", "runtime": "swarmgraph"},
    )
    assert event.type == "RUN_STARTED"
    assert event.schema_version == CURRENT_SCHEMA_VERSION
    assert event.run_id == "run-001"
    assert event.sequence == 0
    assert event.data["workflow_id"] == "my-agent"


def test_create_event_missing_required_field():
    with pytest.raises(ValueError, match="missing required fields"):
        create_event(
            run_id="run-001",
            sequence=0,
            event_type="RUN_STARTED",
            data={"workflow_id": "my-agent"},
        )


def test_create_unknown_event_type():
    with pytest.raises(ValueError, match="Unknown event type"):
        create_event(
            run_id="run-001",
            sequence=0,
            event_type="NONEXISTENT_TYPE",
            data={"foo": "bar"},
        )


def test_validate_valid_event():
    event = create_event(
        run_id="run-001",
        sequence=0,
        event_type="RUN_COMPLETED",
        data={"duration_ms": 1500},
    )
    errors = validate_event(event)
    assert errors == []


def test_validate_event_with_future_version():
    event = RunEvent(
        schema_version=CURRENT_SCHEMA_VERSION + 99,
        type="RUN_STARTED",
        timestamp="2026-05-14T00:00:00+00:00",
        run_id="run-001",
        sequence=0,
        data={"workflow_id": "x", "runtime": "y"},
    )
    errors = validate_event(event)
    assert len(errors) == 1
    assert "schema_version" in errors[0]


def test_all_event_types_are_creatable():
    """Every registered event type can be created with minimal data."""
    for event_type, typedef in EVENT_TYPES.items():
        minimal_data = {f: f"test_{f}" for f in typedef.required_fields}
        event = create_event("run-test", 0, event_type, minimal_data)
        assert event.type == event_type
        errors = validate_event(event)
        assert errors == [], f"{event_type} failed validation: {errors}"


def test_event_serialization_roundtrip():
    event = create_event(
        run_id="run-001",
        sequence=5,
        event_type="STEP_COMPLETED",
        data={"step_id": "step-3", "output": "hello", "duration_ms": 200},
    )
    json_str = event.model_dump_json()
    restored = RunEvent.model_validate_json(json_str)
    assert restored == event
    assert restored.schema_version == CURRENT_SCHEMA_VERSION
```

#### [SCAFFOLD] ADR-003: SQLite Index Wiring

```python
# python/src/agent_runtime_cockpit/storage/indexed_store.py
"""Dual-write store: JSONL canonical + SQLite index (ADR-003)."""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

from .jsonl import JsonlTraceStore
from .sqlite import SqliteStore
from ..protocol.schemas import RunRecord, RunStatus

log = logging.getLogger(__name__)


class IndexedTraceStore:
    """Writes JSONL first (canonical), then updates SQLite index (best-effort)."""

    def __init__(
        self,
        trace_dir: Path = Path(".arc") / "traces",
        db_path: Path = Path(".arc") / "arc.db",
    ) -> None:
        self.jsonl = JsonlTraceStore(base_dir=trace_dir)
        self.sqlite = SqliteStore(db_path=db_path)
        self._lock = threading.Lock()

    def init(self) -> None:
        self.sqlite.init_db()

    def save(self, run: RunRecord) -> None:
        """Write JSONL first (canonical), then SQLite index.

        Production note: move this write into a public JsonlTraceStore.atomic_save()
        method; do not call private _run_path(). Add crash-during-rename tests.
        """
        with self._lock:
            self.jsonl.base_dir.mkdir(parents=True, exist_ok=True)
            path = self.jsonl._run_path(run.id)
            fd, tmp_path = tempfile.mkstemp(
                dir=self.jsonl.base_dir, suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(run.model_dump_json() + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, path)
            except Exception:
                os.unlink(tmp_path)
                raise
        try:
            trace_path = str(path)
            self.sqlite.insert_run(
                run_id=run.id,
                workflow_id=run.workflow_id,
                runtime=run.runtime,
                status=run.status.value,
                started_at=run.started_at,
            )
            if run.ended_at:
                self.sqlite.update_run_status(run.id, run.status.value, run.ended_at)
        except Exception as e:
            log.warning("SQLite index update failed for run %s: %s", run.id, e)

    def load(self, run_id: str) -> Optional[RunRecord]:
        return self.jsonl.load(run_id)

    def list_runs(self) -> list[str]:
        return self.jsonl.list_runs()

    def backfill_index(self) -> tuple[int, int]:
        """Rebuild SQLite index from existing JSONL traces. Idempotent."""
        indexed = 0
        failed = 0
        for run_id in self.jsonl.list_runs():
            try:
                run = self.jsonl.load(run_id)
                if run is None:
                    continue
                self.sqlite.insert_run(
                    run_id=run.id,
                    workflow_id=run.workflow_id,
                    runtime=run.runtime,
                    status=run.status.value,
                    started_at=run.started_at,
                )
                if run.ended_at:
                    self.sqlite.update_run_status(run.id, run.status.value, run.ended_at)
                indexed += 1
            except Exception as e:
                log.warning("Backfill failed for %s: %s", run_id, e)
                failed += 1
        return indexed, failed
```

#### [SCAFFOLD] ADR-003: Indexed Store Tests

```python
# python/tests/storage/test_indexed_store.py
"""Tests for the dual-write indexed trace store (ADR-003)."""
import pytest
from pathlib import Path
from datetime import datetime, timezone
from agent_runtime_cockpit.storage.indexed_store import IndexedTraceStore
from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus


def _make_run(run_id: str = "test-run-001", status: RunStatus = RunStatus.COMPLETED) -> RunRecord:
    now = datetime.now(timezone.utc).isoformat()
    return RunRecord(
        id=run_id,
        workflow_id="test-workflow",
        runtime="swarmgraph",
        status=status,
        started_at=now,
        ended_at=now if status != RunStatus.RUNNING else None,
    )


@pytest.fixture
def store(tmp_path: Path) -> IndexedTraceStore:
    trace_dir = tmp_path / "traces"
    db_path = tmp_path / "arc.db"
    s = IndexedTraceStore(trace_dir=trace_dir, db_path=db_path)
    s.init()
    return s


def test_save_and_load(store: IndexedTraceStore):
    run = _make_run()
    store.save(run)
    loaded = store.load(run.id)
    assert loaded is not None
    assert loaded.id == run.id
    assert loaded.workflow_id == run.workflow_id
    assert loaded.status == run.status


def test_jsonl_is_canonical_when_sqlite_fails(store: IndexedTraceStore, tmp_path: Path):
    """JSONL write succeeds even if SQLite is corrupted."""
    db_path = tmp_path / "bad.db"
    db_path.write_text("not a database")
    bad_store = IndexedTraceStore(
        trace_dir=tmp_path / "traces",
        db_path=db_path,
    )
    run = _make_run("resilient-run")
    bad_store.save(run)
    loaded = bad_store.load(run.id)
    assert loaded is not None
    assert loaded.id == "resilient-run"


def test_backfill_index(store: IndexedTraceStore):
    runs = [_make_run(f"run-{i}", RunStatus.COMPLETED) for i in range(5)]
    for run in runs:
        store.jsonl.save(run)
    indexed, failed = store.backfill_index()
    assert indexed == 5
    assert failed == 0


def test_list_runs(store: IndexedTraceStore):
    run = _make_run()
    store.save(run)
    run_ids = store.list_runs()
    assert run.id in run_ids
```

### e. How to Verify This Still Works

```bash
# 1. Verify Pydantic version
cd python && uv pip show pydantic | grep Version
# Expected: 2.x

# 2. Verify event registry scaffold runs
cd python && uv run pytest tests/orchestration/test_event_registry.py -v

# 3. Verify indexed store scaffold runs
cd python && uv run pytest tests/storage/test_indexed_store.py -v

# 4. Verify ADRs are still coherent
grep -r "schema_version" python/src/agent_runtime_cockpit/
# Should show the new events.py module after scaffold is merged

# 5. Check for Pydantic v3 release
pip index versions pydantic 2>/dev/null | head -3
# If v3 exists, assess breaking changes before pinning
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| ADR-000 is 603 lines — too large to implement atomically | Implementation stalls | Split into sub-PRs: events → storage → supervisor → broker |
| SQLite corruption on crash | Index out of sync with JSONL | JSONL is canonical; `backfill_index()` rebuilds SQLite |
| Event type registry becomes stale as adapters evolve | Adapters emit unregistered events | `create_event()` raises on unknown types; adapters must register new types |
| ADR-005 (keychain) platform variability | macOS Keychain works, Linux Secret Service flaky | Env fallback with degraded status; spike before committing |
| ADR-006 trust model UX friction | Users annoyed by trust prompts | P1a is advisory-only; P2 enforcement flips behavior after UX testing |
| Theia version mismatch (extension ^1.45.0 vs browser app 1.71.0) | DI bindings may break | Align versions before P3; test with current setup first |

### g. Sources

- `docs/adr/000-execution-core-contract.md` (603 lines)
- `docs/adr/001-config-model.md`
- `docs/adr/002-run-lifecycle-state-machine.md`
- `docs/adr/003-storage-strategy.md` (202 lines)
- `docs/adr/004-event-schema-versioning.md` (290 lines)
- `docs/adr/005-audit-key-management.md`
- `docs/adr/006-workspace-trust-isolation.md`
- `docs/adr/007-provider-routing-unification.md`
- `docs/adr/008-daemon-bundling.md`
- `python/src/agent_runtime_cockpit/protocol/schemas.py` (current RunEvent, RunRecord)
- `python/src/agent_runtime_cockpit/storage/jsonl.py` (current JSONL store)
- `python/src/agent_runtime_cockpit/storage/sqlite.py` (current SQLite schema)
- Context7: `/pydantic/pydantic` — Pydantic v2 API reference

---

## 2. Execution Core — P1a

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P1a: Execution Core Infrastructure":

> "Goal: build the backend/runtime infrastructure that adoption, live UI, audit, and trust depend on. Do this before implementing runtime-specific adoption modes."

| Item | Outcome |
|------|---------|
| Add adoption capability fields | CLI/UI can show standalone vs adoption separately |
| Add event schema registry | Run/adoption/live events have versioned, validated contracts |
| Activate JSONL + SQLite index | Runs are searchable/status-queryable without scanning all trace files |
| Replace combo semantics | Sequential combo no longer confused with adoption |
| Add ARC trace/audit refs | Trace records can point to audit material without claiming HMAC signing yet |
| Add live run supervisor and event broker | Runs can be backgrounded, cancelled, streamed, and recovered |
| Split run lifecycle CLI | Safe run commands land before live-dependent commands |
| Add workspace trust resolver | Execution can distinguish trusted vs untrusted workspaces |
| Add isolation provider interface | Execution boundary becomes pluggable and honestly reported |
| Harden subprocess env allowlists | Adapter subprocesses leak fewer secrets before container isolation exists |

### b. Current External State

#### Pydantic v2 (current: 2.x, ARC uses >=2.7)

- **Library:** `/pydantic/pydantic`
- **API:** `BaseModel`, `Field`, `ConfigDict`, `model_dump()`, `model_dump_json()`, `model_validate()`, `model_json_schema()`
- **Breaking from v1:** `orm_mode` → `from_attributes`, `__fields__` → `model_fields`, `.dict()` → `.model_dump()`, validators use `@field_validator` decorator
- **Maintenance:** Active, frequent releases. v3 not yet released.
- **ARC usage:** All protocol models already use v2 patterns. No v1 compatibility needed.

#### aiohttp (current: 3.x, ARC uses >=3.9)

- **Library:** `/aio-libs/aiohttp`
- **API:** `web.Application`, `web.RouteTableDef`, `web.Response`, `web.StreamResponse`
- **SSE:** Requires `aiohttp-sse` package (2.2.0, Feb 2024) or manual `StreamResponse` with `text/event-stream` content type
- **Maintenance:** Active. aiohttp-sse is lightly maintained (last release Feb 2024).
- **ARC usage:** Daemon uses aiohttp for REST endpoints. SSE currently replays stored traces only.

#### aiohttp-sse (2.2.0, Feb 2024)

- **Library:** PyPI `aiohttp-sse`
- **API:** `sse_response()` context manager, `SSEResponse.send()` for event delivery
- **License:** Apache 2.0
- **Maintenance:** Last release Feb 2024. Works with aiohttp 3.x but may not track aiohttp 4.x if released.
- **Risk:** If aiohttp-sse falls behind, manual SSE via `StreamResponse` is straightforward.

#### anyio (current: 4.13.0, Mar 2026)

- **Library:** `/agronholm/anyio`
- **API:** `TaskGroup`, `create_task_group`, `Event`, `Lock`, `Semaphore`, `CapacityLimiter`, `move_on_after`, `fail_after`
- **License:** MIT
- **Maintenance:** Very active. Latest release Mar 2026.
- **Relevance:** Useful for the event broker and supervisor task management. ARC currently uses `asyncio` directly; anyio provides cleaner task group semantics.

#### structlog (current: 25.5.0, Oct 2025)

- **Library:** `/hynek/structlog`
- **API:** `get_logger()`, `bind()`, processors, `JSONRenderer`, stdlib integration
- **License:** MIT/Apache-2.0
- **Maintenance:** Active. Latest release Oct 2025.
- **Relevance:** ARC currently uses stdlib `logging`. structlog provides structured JSON logging that integrates well with trace/audit systems.

### c. Recommended Approach for ARC

1. **Event schema registry (ADR-004):** Implement first. All P1a items depend on versioned events. Scaffold provided in Section 1.
2. **Indexed store (ADR-003):** Wire SQLite into JSONL store. Scaffold provided in Section 1. Add `backfill_index()` CLI command.
3. **JobSupervisor:** Use `asyncio.TaskGroup` (Python 3.11+) for task management. No anyio dependency needed yet — stdlib TaskGroup is sufficient. Add anyio later if cancellation semantics prove complex.
4. **EventBroker:** In-memory publish/subscribe with SSE delivery. Before implementation, choose manual `aiohttp.web.StreamResponse` or add `aiohttp-sse` to `python/pyproject.toml` and CI. Use bounded queues plus a documented slow-client policy.
5. **Trust resolver:** P1a advisory-only. Trust state must live outside the workspace, e.g. `~/.arc/trusted-workspaces.json`, keyed by absolute path plus optional content hash. A workspace-local `.arc/trusted` file must never self-authorize a repo. Do not block execution until P2.
6. **Isolation interface:** Define `IsolationProvider` protocol with `none` and `subprocess` implementations. Docker in P2/P3.
7. **Subprocess env allowlists:** Define per-adapter env passthrough lists. Redact secret-like values from stderr/stdout before trace storage.

### d. Code Scaffolds

#### [SCAFFOLD] JobSupervisor (Python)

```python
# python/src/agent_runtime_cockpit/orchestration/supervisor.py
"""JobSupervisor — owns run lifecycle, cancellation, and orphan recovery (ADR-002)."""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional

from pydantic import BaseModel, Field

from ..protocol.schemas import RunRecord, RunStatus, RunEvent
from .events import create_event, RunEvent as VersionedRunEvent
from ..storage.indexed_store import IndexedTraceStore

log = logging.getLogger(__name__)


class RunRequest(BaseModel):
    workflow_id: str
    runtime: Optional[str] = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    prompt: Optional[str] = None
    profile_id: str = "stub"
    timeout_seconds: int = 300
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass
class ActiveRun:
    run_id: str
    task: Optional[asyncio.Task] = None
    cancelled: bool = False


class JobSupervisor:
    def __init__(self, store: IndexedTraceStore) -> None:
        self.store = store
        self._active_runs: dict[str, ActiveRun] = {}
        self._subscribers: dict[str, list[asyncio.Queue[VersionedRunEvent]]] = {}
        self._sequence_counters: dict[str, int] = {}

    async def start_run(
        self,
        request: RunRequest,
        executor_fn,
    ) -> RunRecord:
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        run = RunRecord(
            id=run_id,
            workflow_id=request.workflow_id,
            runtime=request.runtime or "unknown",
            status=RunStatus.PENDING,
            started_at=now,
            metadata=request.metadata,
        )
        self.store.save(run)
        self._sequence_counters[run_id] = 0
        active = ActiveRun(run_id=run_id)
        self._active_runs[run_id] = active
        task = asyncio.create_task(
            self._execute_run(run_id, request, executor_fn),
            name=f"run-{run_id}",
        )
        active.task = task
        return run

    async def _execute_run(self, run_id: str, request: RunRequest, executor_fn) -> None:
        start_ms = self._now_ms()
        try:
            self._emit_event(run_id, "RUN_STARTED", {
                "workflow_id": request.workflow_id,
                "runtime": request.runtime or "unknown",
            })
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.RUNNING
                self.store.save(run)
            await executor_fn(run_id, request, self._emit_event)
            duration = self._now_ms() - start_ms
            self._emit_event(run_id, "RUN_COMPLETED", {"duration_ms": duration})
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.COMPLETED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)
        except asyncio.CancelledError:
            self._emit_event(run_id, "RUN_CANCELLED", {"cancel_reason": "user_requested"})
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.CANCELLED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)
        except Exception as e:
            duration = self._now_ms() - start_ms
            self._emit_event(run_id, "RUN_FAILED", {
                "error": str(e),
                "error_detail": type(e).__name__,
            })
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.FAILED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)
        finally:
            self._close_subscribers(run_id)
            self._active_runs.pop(run_id, None)

    def _emit_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        seq = self._sequence_counters.get(run_id, 0)
        event = create_event(run_id, seq, event_type, data)
        self._sequence_counters[run_id] = seq + 1
        for queue in self._subscribers.get(run_id, []):
            # Production note: bounded queues need an explicit slow-client policy
            # before live SSE ships: drop-oldest + STREAM_LAG, or disconnect.
            queue.put_nowait(event)

    def subscribe(self, run_id: str) -> asyncio.Queue[VersionedRunEvent]:
        queue: asyncio.Queue[VersionedRunEvent] = asyncio.Queue(maxsize=1000)
        self._subscribers.setdefault(run_id, []).append(queue)
        return queue

    async def cancel_run(self, run_id: str) -> bool:
        active = self._active_runs.get(run_id)
        if active is None or active.task is None:
            return False
        active.cancelled = True
        active.task.cancel()
        try:
            await active.task
        except asyncio.CancelledError:
            pass
        return True

    async def recover_orphans(self) -> int:
        """Mark RUNNING runs from previous supervisor as FAILED."""
        recovered = 0
        for run_id in self.store.list_runs():
            run = self.store.load(run_id)
            if run and run.status == RunStatus.RUNNING:
                run.status = RunStatus.FAILED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                run.metadata["failure_reason"] = "supervisor_orphan"
                self.store.save(run)
                recovered += 1
        return recovered

    def _close_subscribers(self, run_id: str) -> None:
        for queue in self._subscribers.pop(run_id, []):
            queue.put_nowait(None)
        self._sequence_counters.pop(run_id, None)

    @staticmethod
    def _now_ms() -> int:
        import time
        return int(time.time() * 1000)
```

#### [SCAFFOLD] EventBroker with SSE (Python)

```python
# python/src/agent_runtime_cockpit/orchestration/broker.py
"""EventBroker — scaffold for SSE streaming and replay from trace store.

Requires explicit dependency decision: manual aiohttp.web.StreamResponse or declared aiohttp-sse.
Control events are out-of-band unless added to the ADR-004 registry.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from aiohttp import web
from aiohttp_sse import sse_response  # Add to pyproject.toml, or replace with StreamResponse.

from .events import RunEvent
from .supervisor import JobSupervisor
from ..storage.indexed_store import IndexedTraceStore

log = logging.getLogger(__name__)


class EventBroker:
    def __init__(self, supervisor: JobSupervisor, store: IndexedTraceStore) -> None:
        self.supervisor = supervisor
        self.store = store

    async def stream_live(self, run_id: str) -> AsyncIterator[RunEvent]:
        """Yield live events for an active run."""
        queue = self.supervisor.subscribe(run_id)
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event

    async def replay(self, run_id: str) -> AsyncIterator[RunEvent]:
        """Replay events from stored trace."""
        run = self.store.load(run_id)
        if run is None:
            return
        for event in run.events:
            yield RunEvent(
                schema_version=event.data.get("schema_version", 1),
                type=event.type,
                timestamp=event.timestamp,
                run_id=event.run_id,
                sequence=event.sequence,
                data=event.data,
            )

    async def sse_handler(self, request: web.Request) -> web.StreamResponse:
        """HTTP handler for SSE event streaming."""
        run_id = request.match_info["run_id"]
        mode = request.query.get("mode", "replay")
        async with sse_response(request) as resp:
            try:
                if mode == "live":
                    stream = self.stream_live(run_id)
                else:
                    stream = self.replay(run_id)
                async for event in stream:
                    payload = json.dumps(event.model_dump())
                    await resp.send(payload)
                await resp.send(json.dumps({"type": "STREAM_END", "out_of_band": True}))
            except asyncio.CancelledError:
                log.info("SSE stream cancelled for run %s", run_id)
                raise
            except Exception as e:
                log.error("SSE stream error for run %s: %s", run_id, e)
                await resp.send(json.dumps({
                    "type": "STREAM_ERROR",
                    "error": str(e),
                }))
        return resp
```

#### [SCAFFOLD] Trust Resolver (Python)

```python
# python/src/agent_runtime_cockpit/security/trust.py
"""Workspace trust resolver — ADR-006 P1a advisory mode.

Trust state is stored outside the workspace. A committed .arc/trusted file is ignored.
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class TrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    PARTIAL = "partial"
    TRUSTED = "trusted"


class TrustResolution(BaseModel):
    level: TrustLevel
    reason: str
    marker_path: str | None = None
    warning: str | None = None


TRUST_DB = Path.home() / ".arc" / "trusted-workspaces.json"


def resolve_trust(workspace: Path, trust_db: Path = TRUST_DB) -> TrustResolution:
    """Resolve workspace trust level. P1a: advisory only, does not block execution."""
    workspace_path = str(workspace.resolve())
    try:
        trusted = json.loads(trust_db.read_text(encoding="utf-8"))
    except FileNotFoundError:
        trusted = {}
    if trusted.get(workspace_path, {}).get("trusted") is True:
        return TrustResolution(
            level=TrustLevel.TRUSTED,
            reason="Workspace trusted in external trust database",
            marker_path=str(trust_db),
        )
    return TrustResolution(
        level=TrustLevel.UNTRUSTED,
        reason="Workspace not found in external trust database",
        warning=(
            "This workspace is not marked as trusted. "
            "Execution will proceed with subprocess isolation. "
            "Run 'arc workspace trust' to mark this workspace as trusted outside the repo."
        ),
    )
```

#### [SCAFFOLD] Isolation Provider Interface (Python)

```python
# python/src/agent_runtime_cockpit/isolation/base.py
"""Isolation provider interface — ADR-006."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class IsolationResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    pid: int | None = None
    killed: bool = False
    kill_reason: str | None = None


class IsolationProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def provider_id(self) -> str:
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        ...

    @abc.abstractmethod
    async def execute(
        self,
        command: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        ...


class NoneIsolationProvider(IsolationProvider):
    """No isolation — direct subprocess execution (trusted workspaces only)."""

    @property
    def provider_id(self) -> str:
        return "none"

    async def health_check(self) -> bool:
        return True

    async def execute(
        self,
        command: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        import asyncio
        import time
        start = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_seconds
            )
            duration = int((time.monotonic() - start) * 1000)
            return IsolationResult(
                exit_code=proc.returncode or -1,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                duration_ms=duration,
                pid=proc.pid,
            )
        except asyncio.TimeoutError:
            proc.kill()
            stdout, stderr = await proc.communicate()
            duration = int((time.monotonic() - start) * 1000)
            return IsolationResult(
                exit_code=-1,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                duration_ms=duration,
                pid=proc.pid,
                killed=True,
                kill_reason="timeout",
            )


class SubprocessIsolationProvider(IsolationProvider):
    """Subprocess with env allowlist and path restrictions."""

    SAFE_ENV_KEYS = frozenset({
        "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
        "PYTHONPATH", "VIRTUAL_ENV",
    })

    @property
    def provider_id(self) -> str:
        return "subprocess"

    async def health_check(self) -> bool:
        return True

    def _filter_env(self, env: dict[str, str] | None) -> dict[str, str]:
        import os
        base = {k: v for k, v in os.environ.items() if k in self.SAFE_ENV_KEYS}
        if env:
            base.update({k: v for k, v in env.items() if k in self.SAFE_ENV_KEYS})
        return base

    async def execute(
        self,
        command: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        filtered_env = self._filter_env(env)
        delegate = NoneIsolationProvider()
        return await delegate.execute(command, cwd, filtered_env, timeout_seconds)
```

#### [SCAFFOLD] Supervisor + Isolation Tests

```python
# python/tests/orchestration/test_supervisor.py
"""Tests for JobSupervisor lifecycle management."""
import asyncio
import pytest
from pathlib import Path
from agent_runtime_cockpit.orchestration.supervisor import JobSupervisor, RunRequest
from agent_runtime_cockpit.orchestration.events import RunEvent
from agent_runtime_cockpit.storage.indexed_store import IndexedTraceStore
from agent_runtime_cockpit.protocol.schemas import RunStatus


@pytest.fixture
def supervisor(tmp_path: Path) -> JobSupervisor:
    store = IndexedTraceStore(
        trace_dir=tmp_path / "traces",
        db_path=tmp_path / "arc.db",
    )
    store.init()
    return JobSupervisor(store=store)


async def _fake_executor(run_id: str, request, emit):
    emit(run_id, "STEP_STARTED", {"step_id": "s1", "step_name": "test"})
    emit(run_id, "STEP_COMPLETED", {"step_id": "s1"})


async def _failing_executor(run_id: str, request, emit):
    raise RuntimeError("intentional failure")


async def _slow_executor(run_id: str, request, emit):
    await asyncio.sleep(10)


@pytest.mark.asyncio
async def test_successful_run(supervisor: JobSupervisor):
    req = RunRequest(workflow_id="test-wf", runtime="swarmgraph")
    run = await supervisor.start_run(req, _fake_executor)
    assert run.status == RunStatus.PENDING
    active = supervisor._active_runs.get(run.id)
    if active and active.task:
        await active.task
    loaded = supervisor.store.load(run.id)
    assert loaded is not None
    assert loaded.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_failed_run(supervisor: JobSupervisor):
    req = RunRequest(workflow_id="test-wf", runtime="swarmgraph")
    run = await supervisor.start_run(req, _failing_executor)
    active = supervisor._active_runs.get(run.id)
    if active and active.task:
        await active.task
    loaded = supervisor.store.load(run.id)
    assert loaded is not None
    assert loaded.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_cancel_run(supervisor: JobSupervisor):
    req = RunRequest(workflow_id="test-wf", runtime="swarmgraph", timeout_seconds=30)
    run = await supervisor.start_run(req, _slow_executor)
    await asyncio.sleep(0.1)
    cancelled = await supervisor.cancel_run(run.id)
    assert cancelled is True
    loaded = supervisor.store.load(run.id)
    assert loaded is not None
    assert loaded.status == RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_orphan_recovery(supervisor: JobSupervisor):
    from datetime import datetime, timezone
    from agent_runtime_cockpit.protocol.schemas import RunRecord
    orphan = RunRecord(
        id="orphan-001",
        workflow_id="test",
        runtime="swarmgraph",
        status=RunStatus.RUNNING,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    supervisor.store.save(orphan)
    recovered = await supervisor.recover_orphans()
    assert recovered == 1
    loaded = supervisor.store.load("orphan-001")
    assert loaded is not None
    assert loaded.status == RunStatus.FAILED
    assert loaded.metadata.get("failure_reason") == "supervisor_orphan"


@pytest.mark.asyncio
async def test_live_event_subscription(supervisor: JobSupervisor):
    req = RunRequest(workflow_id="test-wf", runtime="swarmgraph")
    run = await supervisor.start_run(req, _fake_executor)
    queue = supervisor.subscribe(run.id)
    active = supervisor._active_runs.get(run.id)
    if active and active.task:
        await active.task
    events: list[RunEvent] = []
    while True:
        event = await queue.get()
        if event is None:
            break
        events.append(event)
    assert len(events) >= 2
    assert events[0].type == "RUN_STARTED"
```

```python
# python/tests/isolation/test_isolation.py
"""Tests for isolation providers."""
import pytest
from pathlib import Path
from agent_runtime_cockpit.isolation.base import (
    NoneIsolationProvider,
    SubprocessIsolationProvider,
)


@pytest.mark.asyncio
async def test_none_provider_success():
    provider = NoneIsolationProvider()
    assert await provider.health_check() is True
    result = await provider.execute(["echo", "hello"])
    assert result.exit_code == 0
    assert "hello" in result.stdout


@pytest.mark.asyncio
async def test_subprocess_provider_env_filtering():
    provider = SubprocessIsolationProvider()
    result = await provider.execute(
        ["env"],
        env={"SECRET_KEY": "should-be-filtered", "PATH": "/usr/bin"},
    )
    assert "SECRET_KEY" not in result.stdout
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_none_provider_timeout():
    provider = NoneIsolationProvider()
    result = await provider.execute(["sleep", "10"], timeout_seconds=1)
    assert result.killed is True
    assert result.kill_reason == "timeout"
```

### e. How to Verify This Still Works

```bash
# 1. Verify Python 3.11+ TaskGroup availability
python3 -c "import asyncio; print(hasattr(asyncio, 'TaskGroup'))"
# Expected: True

# 2. Verify aiohttp-sse compatibility
cd python && uv pip show aiohttp-sse
# Expected: Version 2.2.0

# 3. Run supervisor tests
cd python && uv run pytest tests/orchestration/test_supervisor.py -v

# 4. Run isolation tests
cd python && uv run pytest tests/isolation/test_isolation.py -v

# 5. Verify SSE endpoint manually (after daemon start)
# curl -N http://localhost:8080/api/runs/test-run-001/events?mode=replay

# 6. Check anyio version if considering adoption
pip index versions anyio 2>/dev/null | head -3
# Expected: 4.x
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| aiohttp-sse unmaintained | SSE breaks on aiohttp 4.x | Manual `StreamResponse` SSE is ~20 lines; easy fallback |
| asyncio.CancelledError semantics changed in Python 3.11 | Cancellation may not propagate correctly | Test cancellation path explicitly (included in scaffold tests) |
| SQLite lock contention under concurrent writes | Index updates stall | Single-writer daemon model avoids this; WAL mode if needed |
| Supervisor task leak on daemon crash | Orphaned processes | `recover_orphans()` on startup; test included |
| Env allowlist too restrictive | User workflows break | Make allowlist configurable per profile; document defaults |
| Trust resolver false positives | Untrusted code runs with too much access | P1a is advisory-only; P2 enforcement adds blocking |

### g. Sources

- Context7: `/pydantic/pydantic` — Pydantic v2 BaseModel, Field, model_dump
- Context7: `/aio-libs/aiohttp` — aiohttp web.Application, StreamResponse
- PyPI: `aiohttp-sse` 2.2.0 — sse_response() context manager
- Context7: `/agronholm/anyio` — TaskGroup, concurrency primitives
- Context7: `/hynek/structlog` — structured logging (not yet adopted, future consideration)
- `docs/adr/002-run-lifecycle-state-machine.md` — JobSupervisor contract
- `docs/adr/003-storage-strategy.md` — JSONL + SQLite dual-store
- `docs/adr/004-event-schema-versioning.md` — Event versioning
- `docs/adr/006-workspace-trust-isolation.md` — Trust levels and isolation providers
- Python 3.11 docs: `asyncio.TaskGroup` — native task groups

---

## 3. Adoption Layer — P1b + P2

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P1b: Adoption Foundation And Local Helpers":

> "Goal: add the smallest reusable adoption interface and low-risk helper UX after the execution core can carry it."

| Item | Outcome |
|------|---------|
| Define adoption protocol | Shared interface for all `runtime + SwarmGraph` modes |
| Define adoption runtime ID syntax | CLI/API/UI can refer to adoption modes consistently |
| Add adoption runner skeleton | Runtime router can resolve adoption modes honestly |
| SwarmGraph import path spike | Determine whether ARC can import vendored SwarmGraph as a library |

From "P2: Runtime + SwarmGraph Integrations":

> "Goal: implement adoption mode incrementally, starting with the runtime closest to SwarmGraph."

Approved priority: 1. LangGraph + SwarmGraph, 2. AG2 + SwarmGraph, 3. CrewAI + SwarmGraph, 4. OpenAI Agents + SwarmGraph, 5. LlamaIndex + SwarmGraph.

### b. Current External State

#### LangGraph (latest: 0.2.74 through 1.0.8)

- **Library:** `/langchain-ai/langgraph`
- **API:** `StateGraph`, `add_node`, `add_edge`, `add_conditional_edges`, `compile`, `astream_events(v2)`, `checkpoints`, `interrupts`
- **Stream modes:** `values`, `updates`, `checkpoints`, `tasks`, `debug`, `messages`, `custom`
- **Key feature:** `astream_events("v2")` yields structured events with `event` type, `name`, `data` fields — maps naturally to ARC events
- **Maintenance:** Very active. Multiple version tracks (0.2.x, 0.3.x, 1.0.x).
- **ARC relevance:** Closest to SwarmGraph internals. First adoption target.

#### CrewAI (latest versions via Context7)

- **Library:** `/crewaiinc/crewai`
- **API:** `Crew`, `Agent`, `Task`, `kickoff_async()`, `akickoff()`, streaming with `stream=True`
- **Key feature:** `Crew.kickoff_async(inputs)` returns crew output; streaming available via `stream=True` parameter
- **Maintenance:** Active. Frequent releases.
- **ARC relevance:** Third adoption priority. Task-based model maps to SwarmGraph worker tasks.

#### OpenAI Agents SDK

- **Library:** `/openai/openai-agents-python`
- **API:** `Agent`, `Runner`, `RunHooks` (`on_agent_start/end`, `on_tool_start/end`, `on_handoff`), `run_streamed`, `trace` context manager
- **Key feature:** `RunHooks` provides lifecycle callbacks that map directly to ARC trace events. `run_streamed` yields streaming events.
- **Maintenance:** Active (OpenAI-maintained).
- **ARC relevance:** Fourth adoption priority. Hooks-based tracing is clean integration point.

#### LlamaIndex

- **Library:** `/run-llama/llama_index`
- **API:** Workflows with `Event` subclasses, `AgentStream`, `ToolCall`, `ToolCallResult`, `workflow.run()`, `handler.stream_events()`
- **Key feature:** Event-based workflow system with typed events. `stream_events()` yields structured events.
- **Maintenance:** Very active. Large API surface.
- **ARC relevance:** Fifth adoption priority. Event system maps to ARC events.

#### AG2

- **Library:** `/ag2ai/ag2`
- **API:** `run_group_chat()`, `AutoPattern`, `RoundRobinPattern`, `ConversableAgent`, `LLMConfig`, `initiate_group_chat`
- **Key feature:** Multi-agent conversation patterns with async support. `run_group_chat()` returns chat results.
- **Maintenance:** Active. Package naming evolved from `pyautogen` → `ag2`.
- **ARC relevance:** Second adoption priority. Group chat maps to SwarmGraph multi-worker consensus.

### c. Recommended Approach for ARC

1. **Define adoption protocol first (P1b):** A shared Pydantic-based interface that all adoption adapters implement. This is the critical abstraction.
2. **Use `<runtime>+swarmgraph` syntax:** e.g., `langgraph+swarmgraph`, `crewai+swarmgraph`. Standalone IDs remain unchanged (`langgraph`, `crewai`).
3. **Implement LangGraph + SwarmGraph first:** LangGraph's `astream_events("v2")` provides structured events that map cleanly to ARC events. Lowest integration risk.
4. **Adoption wrapper pattern:** Each adoption adapter wraps the runtime's native execution, intercepts events via hooks/streaming, and feeds them through the ARC event broker. The SwarmGraph queen handles task decomposition and consensus.
5. **Scaffold the adoption runner skeleton before any specific runtime:** The router must be able to represent adoption modes honestly (not-runnable with doctor actions) before implementations exist.
6. **SwarmGraph import spike:** Determine if vendored SwarmGraph can be imported as a library. If not, CLI subprocess fallback for standalone, but adoption requires library access.

### d. Code Scaffolds

#### [SCAFFOLD] Adoption Protocol (Python)

```python
# python/src/agent_runtime_cockpit/adoption/protocol.py
"""Adoption protocol — shared interface for all runtime + SwarmGraph modes."""
from __future__ import annotations

import abc
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class AdoptionMode(str, Enum):
    LANGGRAPH = "langgraph+swarmgraph"
    AG2 = "ag2+swarmgraph"
    CREWAI = "crewai+swarmgraph"
    OPENAI_AGENTS = "openai_agents+swarmgraph"
    LLAMAINDEX = "llamaindex+swarmgraph"


class AdoptionSpec(BaseModel):
    mode: AdoptionMode
    runtime_config: dict[str, Any] = Field(default_factory=dict)
    swarmgraph_config: dict[str, Any] = Field(default_factory=dict)
    max_workers: int = 3
    consensus_threshold: float = 0.67


class WorkerTask(BaseModel):
    task_id: str
    worker_id: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    runtime: str


class WorkerProposal(BaseModel):
    task_id: str
    worker_id: str
    output: str
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Vote(BaseModel):
    task_id: str
    voter_id: str
    proposal_id: str
    score: float
    reason: str = ""


class ConsensusResult(BaseModel):
    task_id: str
    winning_proposal: WorkerProposal
    votes: list[Vote] = Field(default_factory=list)
    consensus_reached: bool
    confidence: float


class AdoptionStatus(str, Enum):
    NOT_IMPLEMENTED = "not_implemented"
    NOT_RUNNABLE = "not_runnable"
    RUNNABLE = "runnable"


class AdoptionCapability(BaseModel):
    mode: AdoptionMode
    status: AdoptionStatus
    reason: str = ""
    doctor_actions: list[dict[str, str]] = Field(default_factory=list)


class AdoptionRunner(abc.ABC):
    @property
    @abc.abstractmethod
    def mode(self) -> AdoptionMode:
        ...

    @abc.abstractmethod
    def check_availability(self, workspace: Path) -> AdoptionCapability:
        ...

    @abc.abstractmethod
    async def run(
        self,
        spec: AdoptionSpec,
        run_id: str,
        emit_event,
    ) -> ConsensusResult:
        ...

    @abc.abstractmethod
    async def stream_worker_events(
        self,
        run_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        yield {}
```

#### [SCAFFOLD] Adoption Registry and Router Integration (Python)

```python
# python/src/agent_runtime_cockpit/adoption/registry.py
"""Adoption registry — resolves adoption modes to runners."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .protocol import (
    AdoptionMode, AdoptionCapability, AdoptionStatus, AdoptionRunner,
)

log = logging.getLogger(__name__)


class AdoptionRegistry:
    _runners: dict[AdoptionMode, AdoptionRunner] = {}

    @classmethod
    def register(cls, runner: AdoptionRunner) -> None:
        cls._runners[runner.mode] = runner

    @classmethod
    def get(cls, mode: AdoptionMode) -> Optional[AdoptionRunner]:
        return cls._runners.get(mode)

    @classmethod
    def list_capabilities(cls, workspace: Path) -> list[AdoptionCapability]:
        caps: list[AdoptionCapability] = []
        for mode in AdoptionMode:
            runner = cls._runners.get(mode)
            if runner is None:
                caps.append(AdoptionCapability(
                    mode=mode,
                    status=AdoptionStatus.NOT_IMPLEMENTED,
                    reason="Adoption runner not yet implemented",
                    doctor_actions=[{
                        "id": "implement",
                        "label": "Implement adoption runner",
                        "description": f"Implement {mode.value} adoption adapter",
                    }],
                ))
            else:
                caps.append(runner.check_availability(workspace))
        return caps

    @classmethod
    def parse_runtime_id(cls, runtime_id: str) -> tuple[str, Optional[AdoptionMode]]:
        """Parse 'langgraph+swarmgraph' into ('langgraph', AdoptionMode.LANGGRAPH)."""
        if runtime_id.endswith("+swarmgraph"):
            base = runtime_id.removesuffix("+swarmgraph")
            mode_map = {m.value.split("+")[0]: m for m in AdoptionMode}
            mode = mode_map.get(base)
            if mode:
                return base, mode
        return runtime_id, None
```

#### [SCAFFOLD] LangGraph + SwarmGraph Adoption Runner (Skeleton)

```python
# python/src/agent_runtime_cockpit/adoption/langgraph_runner.py
"""LangGraph + SwarmGraph adoption runner — skeleton implementation."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, AsyncIterator

from .protocol import (
    AdoptionMode, AdoptionSpec, AdoptionCapability, AdoptionStatus,
    AdoptionRunner, ConsensusResult, WorkerProposal, Vote,
)

log = logging.getLogger(__name__)


class LangGraphAdoptionRunner(AdoptionRunner):
    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.LANGGRAPH

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        try:
            import langgraph
            version = getattr(langgraph, "__version__", "unknown")
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason=f"LangGraph {version} detected, but adoption runner is scaffold-only",
                doctor_actions=[{
                    "id": "implement_langgraph_adoption",
                    "label": "Implement LangGraph adoption",
                    "description": "Runner must execute real SG worker/consensus flow before RUNNABLE",
                }],
            )
        except ImportError:
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason="LangGraph not installed",
                doctor_actions=[{
                    "id": "install_langgraph",
                    "label": "Install LangGraph",
                    "description": "pip install langgraph>=0.2",
                    "command": "pip install 'langgraph>=0.2'",
                }],
            )

    async def run(
        self,
        spec: AdoptionSpec,
        run_id: str,
        emit_event,
    ) -> ConsensusResult:
        """Execute LangGraph graph as SwarmGraph worker task.

        Flow:
        1. Load LangGraph graph from workspace (via export target or detection)
        2. SG queen decomposes input into worker tasks
        3. Each worker invokes LangGraph graph with task input
        4. LangGraph events (via astream_events v2) mapped to ARC events
        5. Worker proposals collected, consensus computed
        6. Consensus result returned with audit ref
        """
        emit_event(run_id, "RUN_FAILED", {
            "error": "adoption runner not implemented",
            "mode": self.mode.value,
            "scaffold": True,
        })
        raise NotImplementedError("scaffold: LangGraph adoption runner not implemented")

    async def stream_worker_events(
        self,
        run_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}
        raise NotImplementedError("scaffold: worker event stream not implemented")
```

#### [SCAFFOLD] Adoption Protocol Tests

```python
# python/tests/adoption/test_adoption_protocol.py
"""Tests for the adoption protocol and registry."""
import pytest
from pathlib import Path
from agent_runtime_cockpit.adoption.protocol import (
    AdoptionMode, AdoptionSpec, AdoptionCapability, AdoptionStatus,
    WorkerProposal, Vote, ConsensusResult,
)
from agent_runtime_cockpit.adoption.registry import AdoptionRegistry


def test_parse_runtime_id_standalone():
    base, mode = AdoptionRegistry.parse_runtime_id("langgraph")
    assert base == "langgraph"
    assert mode is None


def test_parse_runtime_id_adoption():
    base, mode = AdoptionRegistry.parse_runtime_id("langgraph+swarmgraph")
    assert base == "langgraph"
    assert mode == AdoptionMode.LANGGRAPH


def test_parse_runtime_id_unknown():
    base, mode = AdoptionRegistry.parse_runtime_id("unknown+swarmgraph")
    assert base == "unknown"
    assert mode is None


def test_adoption_spec_defaults():
    spec = AdoptionSpec(mode=AdoptionMode.LANGGRAPH)
    assert spec.max_workers == 3
    assert spec.consensus_threshold == 0.67
    assert spec.runtime_config == {}


def test_consensus_result_serialization():
    proposal = WorkerProposal(
        task_id="t1", worker_id="w1", output="result", confidence=0.95,
    )
    vote = Vote(task_id="t1", voter_id="q1", proposal_id="t1", score=0.95)
    result = ConsensusResult(
        task_id="t1",
        winning_proposal=proposal,
        votes=[vote],
        consensus_reached=True,
        confidence=0.95,
    )
    data = result.model_dump()
    assert data["consensus_reached"] is True
    assert len(data["votes"]) == 1
    restored = ConsensusResult.model_validate(data)
    assert restored == result


def test_list_capabilities_empty_registry(tmp_path: Path):
    AdoptionRegistry._runners = {}
    caps = AdoptionRegistry.list_capabilities(tmp_path)
    assert len(caps) == len(AdoptionMode)
    for cap in caps:
        assert cap.status == AdoptionStatus.NOT_IMPLEMENTED


@pytest.mark.asyncio
async def test_langgraph_runner_skeleton(tmp_path: Path):
    from agent_runtime_cockpit.adoption.langgraph_runner import LangGraphAdoptionRunner
    runner = LangGraphAdoptionRunner()
    assert runner.mode == AdoptionMode.LANGGRAPH
    cap = runner.check_availability(tmp_path)
    assert cap.mode == AdoptionMode.LANGGRAPH
    events = []
    def emit(run_id, etype, data):
        events.append((etype, data))
    spec = AdoptionSpec(mode=AdoptionMode.LANGGRAPH)
    result = await runner.run(spec, "test-run", emit)
    assert result.consensus_reached is True
    assert len(events) >= 4
    assert events[0][0] == "STEP_STARTED"
```

### e. How to Verify This Still Works

```bash
# 1. Verify LangGraph version and API
cd python && uv pip show langgraph 2>/dev/null | grep Version
# Expected: 0.2.x or higher

# 2. Verify LangGraph astream_events v2 exists
python3 -c "
from langgraph.graph import StateGraph
import inspect
# Check if astream_events accepts version parameter
print('astream_events available')
"

# 3. Run adoption protocol tests
cd python && uv run pytest tests/adoption/test_adoption_protocol.py -v

# 4. Check CrewAI streaming API
python3 -c "
try:
    from crewai import Crew
    print('CrewAI importable')
except ImportError:
    print('CrewAI not installed — expected for scaffold')
"

# 5. Verify OpenAI Agents SDK hooks
python3 -c "
try:
    from agents import RunHooks
    print('RunHooks available')
except ImportError:
    print('OpenAI Agents SDK not installed — expected for scaffold')
"

# 6. SwarmGraph import spike
python3 -c "
import sys
sys.path.insert(0, 'runtimes/swarmgraph')
try:
    import swarm_shared
    print('SwarmGraph importable as library')
except ImportError as e:
    print(f'SwarmGraph not importable: {e}')
"
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| LangGraph API volatility (0.2→1.0 transition) | Adoption wrapper breaks | Pin LangGraph version; test against latest; abstract behind runner interface |
| SwarmGraph vendored package not importable as library | Adoption requires CLI subprocess, losing event granularity | Spike import path (included in verification); if fails, CLI subprocess with JSONL event capture |
| CrewAI `stream=True` behavior changes | Streaming events break | Test CrewAI streaming before implementation; capture output format |
| OpenAI Agents SDK `RunHooks` signature changes | Hook mapping breaks | Pin SDK version; test hook signatures before implementation |
| AG2 package naming drift (`pyautogen` → `ag2`) | Import fails | Use try/except import pattern; detect both package names |
| LlamaIndex broad API surface | Hard to find stable integration point | Focus on `workflow.run()` and `stream_events()` only |
| Adoption protocol too SwarmGraph-specific | Other runtimes don't fit the model | Keep protocol minimal; allow runtime-specific metadata in `WorkerProposal.metadata` |
| Consensus computation complexity | Performance bottleneck for multi-worker runs | Start with single-worker mode; add multi-worker after baseline works |

### g. Sources

- Context7: `/langchain-ai/langgraph` — StateGraph, astream_events(v2), checkpoints, stream modes
- Context7: `/crewaiinc/crewai` — Crew, Agent, Task, kickoff_async, streaming
- Context7: `/openai/openai-agents-python` — Agent, Runner, RunHooks, run_streamed, trace
- Context7: `/run-llama/llama_index` — Workflows, Event, AgentStream, stream_events
- Context7: `/ag2ai/ag2` — run_group_chat, AutoPattern, ConversableAgent
- `docs/IMPLEMENTATION_PLAN.md` — P1b and P2 scope, adoption priority order
- `python/src/agent_runtime_cockpit/adapters/base.py` — Current adapter interface
- `python/src/agent_runtime_cockpit/protocol/capabilities.py` — Current capability model
- `docs/adr/000-execution-core-contract.md` — Adapter/Adoption Runner contract (Section 6)

---

## 4. Runtime Integrations — P2

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P2: Runtime + SwarmGraph Integrations":

> "Goal: implement adoption mode incrementally, starting with the runtime closest to SwarmGraph."

Approved adoption priority:
1. LangGraph + SwarmGraph
2. AG2 + SwarmGraph
3. CrewAI + SwarmGraph
4. OpenAI Agents + SwarmGraph
5. LlamaIndex + SwarmGraph
6. Semantic Kernel + SwarmGraph (deferred)
7. Haystack + SwarmGraph (deferred)
8. DSPy/PydanticAI selective typed-worker adapters (future)

Also in P2:
- SwarmGraph audit verify path
- Safer daemon auth default
- Enforce workspace trust before execution
- Complete eval CLI basics
- Add trace replay + HITL persistence/CLI contracts
- Add high-assurance IDE views

### b. Current External State

#### Semantic Kernel (deferred)

- **Library:** `/microsoft/semantic-kernel`
- **API:** `@kernel_function`, `Kernel`, plugins, `ProcessBuilder`, `AutoGenConversableAgent` wrapper
- **Maintenance:** Active (Microsoft-maintained). Multiple language SDKs.
- **ARC relevance:** Deferred until core P2 adoption proves out. Enterprise plugin/workflow candidate.

#### Haystack (deferred)

- **Library:** `/deepset-ai/haystack`
- **API:** `Pipeline`, `Document`, retrievers, generators, `PromptBuilder`. Latest: v2.28.0.
- **Maintenance:** Active. v2 architecture is stable.
- **ARC relevance:** Deferred. RAG/pipeline candidate. Only add if LlamaIndex path proves retrieval/evidence UX.

#### keyring (PyPI 25.7.0, Nov 2025)

- **Library:** PyPI `keyring`
- **API:** `keyring.set_password()`, `keyring.get_password()`, `keyring.delete_password()`
- **Backends:** macOS Keychain, Freedesktop Secret Service, KDE KWallet, Windows Credential Locker
- **License:** MIT
- **Maintenance:** Active. Latest: 25.7.0 (Nov 2025).
- **ARC relevance:** ADR-005 audit key management. Preferred storage for audit keys (keyring, env fallback).

#### tiktoken (latest: 0.12.0, Oct 2025)

- **Library:** `/openai/tiktoken`
- **API:** `encoding_for_model()`, `encode()`, `decode()`, `get_encoding()`
- **License:** MIT
- **Maintenance:** Active. Latest: 0.12.0 (Oct 2025).
- **ARC relevance:** Token counting for cost estimation and prompt optimizer. Not a runtime dependency.

#### OpenTelemetry Python

- **Library:** `/open-telemetry/opentelemetry-python`
- **API:** `OTLPSpanExporter` (gRPC/HTTP), `BatchSpanProcessor`, `tracer`, spans
- **Maintenance:** Active. CNCF project.
- **ARC relevance:** Future observability integration. Not P2 scope.

#### docker (PyPI 7.1.0, May 2024)

- **Library:** PyPI `docker`
- **API:** `docker.from_env()`, `containers.run()`, `containers.list()`, `containers.get()`
- **License:** Apache 2.0
- **Maintenance:** Last release May 2024. Stable API.
- **ARC relevance:** P2/P3 isolation provider. Docker-compatible container isolation.

### c. Recommended Approach for ARC

1. **Implement standalone adapters first, then adoption wrappers.** Each runtime needs a working standalone adapter before adoption makes sense.
2. **LangGraph + SwarmGraph is the pathfinder.** It has the cleanest event mapping via `astream_events("v2")`. Learn from it before implementing others.
3. **AG2 second because group chat maps to consensus.** `run_group_chat()` produces proposals naturally. The main risk is AG2 package naming drift.
4. **CrewAI third — task-based execution maps to worker tasks.** `kickoff_async()` with `stream=True` provides event streaming.
5. **OpenAI Agents fourth — hooks-based tracing is clean but SDK is volatile.** `RunHooks` maps to ARC events, but the SDK changes frequently.
6. **LlamaIndex fifth — broad API surface makes integration harder.** Focus on workflow events only.
7. **Defer Semantic Kernel and Haystack** until core P2 adoption proves the pattern.
8. **Audit verify path:** Use `keyring` for key storage with env fallback. Verify SwarmGraph audit chains without claiming full key management UX.
9. **Docker isolation:** Implement as `DockerIsolationProvider` using the `docker` package. Detect OrbStack as Docker-compatible on macOS.

### d. Code Scaffolds

#### [SCAFFOLD] AG2 + SwarmGraph Adoption Runner (Skeleton)

```python
# python/src/agent_runtime_cockpit/adoption/ag2_runner.py
"""AG2 + SwarmGraph adoption runner — skeleton implementation."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, AsyncIterator

from .protocol import (
    AdoptionMode, AdoptionSpec, AdoptionCapability, AdoptionStatus,
    AdoptionRunner, ConsensusResult, WorkerProposal, Vote,
)

log = logging.getLogger(__name__)


class AG2AdoptionRunner(AdoptionRunner):
    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.AG2

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        try:
            import autogen
            version = getattr(autogen, "__version__", "unknown")
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason=f"AG2 {version} detected, but adoption runner is scaffold-only",
            )
        except ImportError:
            try:
                import ag2
                version = getattr(ag2, "__version__", "unknown")
                return AdoptionCapability(
                    mode=self.mode,
                    status=AdoptionStatus.NOT_RUNNABLE,
                    reason=f"AG2 (ag2 package) {version} detected, but adoption runner is scaffold-only",
                )
            except ImportError:
                return AdoptionCapability(
                    mode=self.mode,
                    status=AdoptionStatus.NOT_RUNNABLE,
                    reason="AG2 not installed (tried both 'autogen' and 'ag2' packages)",
                    doctor_actions=[{
                        "id": "install_ag2",
                        "label": "Install AG2",
                        "description": "pip install ag2",
                        "command": "pip install ag2",
                    }],
                )

    async def run(
        self,
        spec: AdoptionSpec,
        run_id: str,
        emit_event,
    ) -> ConsensusResult:
        """Execute AG2 group chat as SwarmGraph worker task.

        Flow:
        1. SG queen decomposes input into agent roles
        2. Each AG2 agent acts as a SwarmGraph worker
        3. Group chat messages mapped to worker proposals
        4. SG consensus over final proposals
        5. Audit record for consensus decision
        """
        emit_event(run_id, "RUN_FAILED", {"error": "adoption runner not implemented", "mode": self.mode.value, "scaffold": True})
        raise NotImplementedError("scaffold: AG2 adoption runner not implemented")

    async def stream_worker_events(
        self,
        run_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}
        raise NotImplementedError("scaffold: worker event stream not implemented")
```

#### [SCAFFOLD] CrewAI + SwarmGraph Adoption Runner (Skeleton)

```python
# python/src/agent_runtime_cockpit/adoption/crewai_runner.py
"""CrewAI + SwarmGraph adoption runner — skeleton implementation."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, AsyncIterator

from .protocol import (
    AdoptionMode, AdoptionSpec, AdoptionCapability, AdoptionStatus,
    AdoptionRunner, ConsensusResult, WorkerProposal, Vote,
)

log = logging.getLogger(__name__)


class CrewAIAdoptionRunner(AdoptionRunner):
    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.CREWAI

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        try:
            from crewai import Crew
            import crewai
            version = getattr(crewai, "__version__", "unknown")
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason=f"CrewAI {version} detected, but adoption runner is scaffold-only",
            )
        except ImportError:
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason="CrewAI not installed",
                doctor_actions=[{
                    "id": "install_crewai",
                    "label": "Install CrewAI",
                    "description": "pip install crewai",
                    "command": "pip install crewai",
                }],
            )

    async def run(
        self,
        spec: AdoptionSpec,
        run_id: str,
        emit_event,
    ) -> ConsensusResult:
        """Execute CrewAI crew as SwarmGraph worker task.

        Flow:
        1. SG queen maps crew tasks to worker assignments
        2. Each crew task executed as a SwarmGraph worker
        3. Task outputs become worker proposals
        4. SG consensus over task outputs
        """
        emit_event(run_id, "RUN_FAILED", {"error": "adoption runner not implemented", "mode": self.mode.value, "scaffold": True})
        raise NotImplementedError("scaffold: CrewAI adoption runner not implemented")

    async def stream_worker_events(
        self,
        run_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}
        raise NotImplementedError("scaffold: worker event stream not implemented")
```

#### [SCAFFOLD] OpenAI Agents + SwarmGraph Adoption Runner (Skeleton)

```python
# python/src/agent_runtime_cockpit/adoption/openai_agents_runner.py
"""OpenAI Agents + SwarmGraph adoption runner — skeleton implementation."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, AsyncIterator

from .protocol import (
    AdoptionMode, AdoptionSpec, AdoptionCapability, AdoptionStatus,
    AdoptionRunner, ConsensusResult, WorkerProposal, Vote,
)

log = logging.getLogger(__name__)


class OpenAIAgentsAdoptionRunner(AdoptionRunner):
    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.OPENAI_AGENTS

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        try:
            from agents import Agent, Runner
            import agents
            version = getattr(agents, "__version__", "unknown")
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason=f"OpenAI Agents SDK {version} detected, but adoption runner is scaffold-only",
            )
        except ImportError:
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason="OpenAI Agents SDK not installed",
                doctor_actions=[{
                    "id": "install_agents",
                    "label": "Install OpenAI Agents SDK",
                    "description": "pip install openai-agents",
                    "command": "pip install openai-agents",
                }],
            )

    async def run(
        self,
        spec: AdoptionSpec,
        run_id: str,
        emit_event,
    ) -> ConsensusResult:
        """Execute OpenAI Agents run as SwarmGraph worker task.

        Flow:
        1. SG queen wraps Agent execution as worker task
        2. RunHooks intercept lifecycle events → ARC trace
        3. Agent output becomes worker proposal
        4. SG consensus over agent output
        """
        emit_event(run_id, "RUN_FAILED", {"error": "adoption runner not implemented", "mode": self.mode.value, "scaffold": True})
        raise NotImplementedError("scaffold: OpenAI Agents adoption runner not implemented")

    async def stream_worker_events(
        self,
        run_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}
        raise NotImplementedError("scaffold: worker event stream not implemented")
```

#### [SCAFFOLD] Audit Key Management with keyring (Python)

```python
# python/src/agent_runtime_cockpit/audit/keys.py
"""Audit key management — HMAC key storage via keyring (ADR-005)."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)

SERVICE_NAME = "arc-studio-audit"
KEY_ID = "hmac-audit-key"


class KeyStatus(BaseModel):
    available: bool
    source: str  # "keychain", "env", "none"
    degraded: bool = False
    warning: str = ""


def get_audit_key() -> tuple[Optional[bytes], KeyStatus]:
    """Retrieve HMAC audit key from keychain or env fallback."""
    try:
        import keyring
        key_str = keyring.get_password(SERVICE_NAME, KEY_ID)
        if key_str:
            return key_str.encode("utf-8"), KeyStatus(
                available=True, source="keychain",
            )
    except Exception as e:
        log.debug("Keychain access failed: %s", e)
    env_key = os.environ.get("ARC_AUDIT_HMAC_KEY")
    if env_key:
        return env_key.encode("utf-8"), KeyStatus(
            available=True, source="env", degraded=True,
            warning="Using env fallback for audit key — keychain preferred",
        )
    return None, KeyStatus(
        available=False, source="none", degraded=True,
        warning="No audit key available — audit signing disabled",
    )


def set_audit_key(key: str) -> bool:
    """Store HMAC audit key in keychain."""
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, KEY_ID, key)
        return True
    except Exception as e:
        log.warning("Failed to store audit key in keychain: %s", e)
        return False


def sign_audit_record(data: dict, key: bytes) -> str:
    """Sign audit record data with HMAC-SHA256."""
    import json
    payload = json.dumps(data, sort_keys=True).encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_audit_signature(data: dict, signature: str, key: bytes) -> bool:
    """Verify HMAC-SHA256 signature of audit record."""
    expected = sign_audit_record(data, key)
    return hmac.compare_digest(expected, signature)
```

#### [SCAFFOLD] Audit Key Tests

```python
# python/tests/audit/test_audit_keys.py
"""Tests for audit key management."""
import os
import pytest
from unittest.mock import patch


def test_get_audit_key_from_env():
    with patch.dict(os.environ, {"ARC_AUDIT_HMAC_KEY": "test-key-123"}):
        with patch("keyring.get_password", side_effect=Exception("no keychain")):
            from agent_runtime_cockpit.audit.keys import get_audit_key
            key, status = get_audit_key()
            assert key == b"test-key-123"
            assert status.source == "env"
            assert status.degraded is True


def test_sign_and_verify():
    from agent_runtime_cockpit.audit.keys import sign_audit_record, verify_audit_signature
    key = b"test-hmac-key"
    data = {"run_id": "run-001", "action": "completed", "timestamp": "2026-05-14T00:00:00Z"}
    signature = sign_audit_record(data, key)
    assert verify_audit_signature(data, signature, key) is True
    assert verify_audit_signature(data, signature, b"wrong-key") is False
    tampered = {**data, "action": "failed"}
    assert verify_audit_signature(tampered, signature, key) is False


def test_no_key_available():
    with patch.dict(os.environ, {}, clear=True):
        with patch("keyring.get_password", side_effect=Exception("no keychain")):
            from agent_runtime_cockpit.audit.keys import get_audit_key
            key, status = get_audit_key()
            assert key is None
            assert status.available is False
            assert status.source == "none"
```

### e. How to Verify This Still Works

```bash
# 1. Verify AG2 import paths
python3 -c "
try:
    import autogen; print(f'autogen: {autogen.__version__}')
except ImportError:
    try:
        import ag2; print(f'ag2: {ag2.__version__}')
    except ImportError:
        print('Neither autogen nor ag2 installed')
"

# 2. Verify CrewAI Crew import
python3 -c "
try:
    from crewai import Crew, Agent, Task; print('CrewAI OK')
except ImportError:
    print('CrewAI not installed')
"

# 3. Verify OpenAI Agents SDK
python3 -c "
try:
    from agents import Agent, Runner, RunHooks; print('OpenAI Agents SDK OK')
except ImportError:
    print('OpenAI Agents SDK not installed')
"

# 4. Verify keyring on current platform
python3 -c "
import keyring
backend = keyring.get_keyring()
print(f'Keyring backend: {type(backend).__name__}')
"

# 5. Run audit key tests
cd python && uv run pytest tests/audit/test_audit_keys.py -v

# 6. Verify docker package
python3 -c "
try:
    import docker; print(f'docker: {docker.__version__}')
except ImportError:
    print('docker package not installed')
"

# 7. Run adoption runner skeleton tests
cd python && uv run pytest tests/adoption/ -v
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| AG2 dual package naming (`autogen` vs `ag2`) | Import confusion | Try both imports; document which is canonical |
| CrewAI side effects during execution | Unintended API calls | Paid-call gating before any crew execution |
| OpenAI Agents SDK requires live API key for testing | Cannot test without credentials | Fake SDK tests with mocked Runner; real tests opt-in |
| LlamaIndex API surface too broad | Integration scope creep | Focus on workflow events only; defer retrievers/generators |
| keyring fails on headless Linux | Audit key storage broken | Env fallback with degraded status; document platform support |
| Docker isolation requires daemon access | Security implications | P2/P3 only; workspace trust must be enforced first |
| HMAC audit key management UX | Users don't set up keys | Degraded mode works without signing; UI shows warning |
| Semantic Kernel/Haystack deferred | Missing enterprise/RAG use cases | Intentional deferral; core adoption must prove pattern first |

### g. Sources

- Context7: `/langchain-ai/langgraph` — StateGraph, astream_events(v2)
- Context7: `/crewaiinc/crewai` — Crew, kickoff_async, streaming
- Context7: `/openai/openai-agents-python` — Agent, Runner, RunHooks
- Context7: `/run-llama/llama_index` — Workflows, Event, stream_events
- Context7: `/ag2ai/ag2` — run_group_chat, ConversableAgent
- Context7: `/microsoft/semantic-kernel` — kernel_function, Kernel, ProcessBuilder (deferred)
- Context7: `/deepset-ai/haystack` — Pipeline, Document, PromptBuilder (deferred)
- PyPI: `keyring` 25.7.0 — cross-platform keychain access
- PyPI: `tiktoken` 0.12.0 — token counting
- PyPI: `docker` 7.1.0 — Docker SDK for Python
- Context7: `/open-telemetry/opentelemetry-python` — OTLP tracing (future)
- `docs/IMPLEMENTATION_PLAN.md` — P2 scope and adoption priority
- `docs/adr/005-audit-key-management.md` — Audit key management

---

## 5. Theia Extension Architecture

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`:

> "Wire canonical `packages/arc-extension` into the browser app before further UI work."

> "Port useful UI-only widgets into `packages/arc-extension`; archive or delete duplicate backend/protocol/stub packages."

From the Theia Extension Migration Policy:

| Extension | Default action |
|-----------|---------------|
| `arc-event-stream` | Port |
| `arc-runs` | Port |
| `arc-workflows` | Port |
| `arc-schemas` | Port |
| `arc-adapters` | Port |
| `arc-health` | Port small pieces |
| `arc-context` | Port if context UX remains in scope |
| `arc-settings` | Port prefs only |
| `arc-audit` | Archive or rewrite |
| `arc-arena` | Archive |
| `arc-product` | Archive/delete |
| `arc-core` | Archive/delete after salvage |

### b. Current External State

#### Eclipse Theia (ARC uses @theia/core ^1.45.0 for extension, 1.71.0 for browser app)

- **Library:** `/eclipse-theia/theia`
- **API:** `ContainerModule`, `WidgetFactory`, `CommandContribution`, `MenuContribution`, `FrontendApplicationContribution`, `PreferenceContribution`, `StatusBar`
- **DI:** InversifyJS via `@theia/core/shared/inversify`
- **Widgets:** `ReactWidget`, `BaseWidget`, `TreeWidget`, `WidgetManager`, `AbstractViewContribution`
- **Communication:** JSON-RPC over Theia connection infrastructure
- **Maintenance:** Active. Latest versions in 1.70+ range. ARC extension uses ^1.45.0 (behind).
- **ARC usage:** `packages/arc-extension` is canonical. Uses `ContainerModule` with explicit DI bindings. Frontend widget is `ReactWidget`-based.

#### InversifyJS

- **Library:** `/inversify/inversifyjs`
- **API:** `@injectable`, `@inject`, `Container`, `ContainerModule`, `BindingScopeEnum`
- **Binding scopes:** `Transient`, `Singleton`, `Request`
- **Maintenance:** Stable. Used internally by Theia.
- **ARC usage:** Backend services bound via `ContainerModule` in `arc-extension-backend-module.ts`. Uses `toDynamicValue` for factory injection.

#### Current ARC Extension Architecture

```
packages/arc-extension/
├── src/
│   ├── common/
│   │   └── arc-protocol.ts      # Protocol types (438 lines)
│   ├── node/
│   │   ├── arc-extension-backend-module.ts  # DI module (38 lines)
│   │   ├── arc-backend-service.ts           # Orchestration (276 lines)
│   │   └── services/
│   │       ├── workflow-executor.ts         # SwarmGraph execution
│   │       ├── trace-parser.ts              # JSONL parsing
│   │       ├── workflow-detector.ts         # Runtime detection
│   │       └── file-manager.ts              # Trace file management
│   └── browser/
│       ├── arc-widget.tsx                   # Main widget (~450 lines)
│       ├── arc-extension-frontend-module.ts # Frontend DI
│       └── components/
│           ├── ProgressBar.tsx
│           ├── ToastContainer.tsx
│           ├── ShortcutsModal.tsx
│           ├── ExecutionSteps.tsx
│           ├── ErrorBanner.tsx
│           ├── WorkflowExecutionSection.tsx
│           ├── TraceViewerSection.tsx
│           └── WorkflowDetectionSection.tsx
```

#### Duplicate Theia Extensions (to be ported/archived)

```
theia-extensions/
├── arc-adapters/      # Runtime readiness UI → PORT
├── arc-audit/         # Stub audit → ARCHIVE
├── arc-context/       # Context management → PORT if needed
├── arc-core/          # Duplicate canonical → ARCHIVE/DELETE
├── arc-event-stream/  # Event stream visualization → PORT
├── arc-health/        # Health monitoring → PORT small pieces
├── arc-product/       # Product UI → ARCHIVE/DELETE
├── arc-runs/          # Run timeline → PORT
├── arc-schemas/       # Schema inspector → PORT
├── arc-settings/      # Preferences → PORT prefs only
├── arc-workflows/     # Workflow graph → PORT
```

### c. Recommended Approach for ARC

1. **Align Theia versions before P3.** Extension uses ^1.45.0, browser app uses 1.71.0. Align to a single version range.
2. **Port in priority order:** `arc-adapters` → `arc-runs` → `arc-workflows` → `arc-event-stream` → `arc-schemas` → `arc-health` (small pieces) → `arc-settings` (prefs only).
3. **Archive stubs:** `arc-audit`, `arc-arena`, `arc-product`, `arc-core` — archive or delete after useful code is salvaged.
4. **Protocol migration:** Duplicate extensions may have conflicting protocol types. Migrate all to `arc-protocol.ts` in `packages/arc-extension/src/common/`.
5. **DI pattern:** Follow existing `arc-extension-backend-module.ts` pattern — explicit `toDynamicValue` bindings, singleton scope for services.
6. **Widget pattern:** `ReactWidget` for all custom UI. `AbstractViewContribution` for view menu integration. `WidgetFactory` for widget creation.
7. **Status bar:** Use `StatusBar` contribution for active run status, daemon connection status.
8. **Command palette:** Register commands via `CommandContribution` for all ARC actions.

### d. Code Scaffolds

#### [SCAFFOLD] Frontend Module with Ported Contributions (TypeScript)

```typescript
// packages/arc-extension/src/browser/arc-extension-frontend-module.ts
import { ContainerModule } from '@theia/core/shared/inversify';
import {
    CommandContribution,
    MenuContribution,
    WidgetFactory,
    OpenHandler,
} from '@theia/core/lib/browser';
import { ArcWidget } from './arc-widget';
import { ArcFrontendContribution } from './arc-frontend-contribution';
import { ArcService, ArcServicePath } from '../common/arc-protocol';
import { WebSocketConnectionProvider } from '@theia/core/lib/browser/messaging/ws-connection-provider';

export const ARC_WIDGET_FACTORY_ID = 'arc-studio';

export default new ContainerModule((bind, unbind, isBound, rebind) => {
    bind(ArcWidget).toSelf();
    bind<WidgetFactory>(WidgetFactory).toDynamicValue(ctx => ({
        id: ARC_WIDGET_FACTORY_ID,
        createWidget: () => ctx.container.get(ArcWidget),
    })).inSingletonScope();

    bind(ArcFrontendContribution).toSelf().inSingletonScope();
    bind(CommandContribution).toService(ArcFrontendContribution);
    bind(MenuContribution).toService(ArcFrontendContribution);

    bind(ArcService).toDynamicValue(ctx => {
        const connection = ctx.container.get(WebSocketConnectionProvider);
        return connection.createProxy<ArcService>(ArcServicePath);
    }).inSingletonScope();
});
```

#### [SCAFFOLD] Frontend Contribution with Commands and Menu (TypeScript)

```typescript
// packages/arc-extension/src/browser/arc-frontend-contribution.ts
import { inject, injectable } from '@theia/core/shared/inversify';
import {
    Command,
    CommandContribution,
    CommandRegistry,
    MenuContribution,
    MenuModelRegistry,
    MenuPath,
} from '@theia/core';
import {
    AbstractViewContribution,
    OpenViewArguments,
} from '@theia/core/lib/browser';
import { ArcWidget } from './arc-widget';
import { ARC_WIDGET_FACTORY_ID } from './arc-extension-frontend-module';

export const ARC_COMMANDS = {
    OPEN: Command.toDefaultLocalizedCommand({
        id: 'arc.open',
        label: 'Open ARC Studio',
        category: 'ARC',
    }),
    DETECT_WORKFLOWS: Command.toDefaultLocalizedCommand({
        id: 'arc.detectWorkflows',
        label: 'Detect Workflows',
        category: 'ARC',
    }),
    RUN_WORKFLOW: Command.toDefaultLocalizedCommand({
        id: 'arc.runWorkflow',
        label: 'Run Workflow',
        category: 'ARC',
    }),
    CANCEL_RUN: Command.toDefaultLocalizedCommand({
        id: 'arc.cancelRun',
        label: 'Cancel Run',
        category: 'ARC',
    }),
};

export const ARC_MENU_PATH: MenuPath = ['menubar', '5_arc'];

@injectable()
export class ArcFrontendContribution
    extends AbstractViewContribution<ArcWidget>
    implements CommandContribution, MenuContribution
{
    constructor() {
        super({
            widgetId: ARC_WIDGET_FACTORY_ID,
            widgetName: 'ARC Studio',
            defaultWidgetOptions: { area: 'main' },
            toggleCommandId: ARC_COMMANDS.OPEN.id,
        });
    }

    registerCommands(registry: CommandRegistry): void {
        super.registerCommands(registry);
        registry.registerCommand(ARC_COMMANDS.DETECT_WORKFLOWS, {
            execute: () => this.openView({ activate: true }),
        });
        registry.registerCommand(ARC_COMMANDS.RUN_WORKFLOW, {
            execute: () => this.openView({ activate: true }),
        });
        registry.registerCommand(ARC_COMMANDS.CANCEL_RUN, {
            execute: () => this.openView({ activate: true }),
        });
    }

    registerMenus(registry: MenuModelRegistry): void {
        registry.registerMenuAction(ARC_MENU_PATH, {
            commandId: ARC_COMMANDS.OPEN.id,
            label: 'Open ARC Studio',
            order: '0',
        });
        registry.registerMenuAction(ARC_MENU_PATH, {
            commandId: ARC_COMMANDS.DETECT_WORKFLOWS.id,
            label: 'Detect Workflows',
            order: '1',
        });
    }

    async openView(args?: Partial<OpenViewArguments>): Promise<ArcWidget> {
        const widget = await super.openView(args);
        return widget;
    }
}
```

#### [SCAFFOLD] Status Bar Contribution for Run Status (TypeScript)

```typescript
// packages/arc-extension/src/browser/arc-status-bar-contribution.ts
import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { FrontendApplicationContribution, StatusBar, StatusBarAlignment } from '@theia/core/lib/browser';
import { ArcService } from '../common/arc-protocol';

@injectable()
export class ArcStatusBarContribution implements FrontendApplicationContribution {
    @inject(StatusBar)
    protected readonly statusBar: StatusBar;

    @inject(ArcService)
    protected readonly arcService: ArcService;

    @postConstruct()
    protected init(): void {
        this.updateStatus();
    }

    protected async updateStatus(): Promise<void> {
        try {
            const traces = await this.arcService.getTraces();
            const runningCount = traces.filter(t => t.status === 'unknown').length;
            this.statusBar.setElement('arc-status', {
                text: `ARC: ${traces.length} traces${runningCount > 0 ? ` (${runningCount} running)` : ''}`,
                alignment: StatusBarAlignment.LEFT,
                priority: 100,
                tooltip: 'ARC Studio — Agent Runtime Cockpit',
                command: 'arc.open',
            });
        } catch {
            this.statusBar.setElement('arc-status', {
                text: 'ARC: disconnected',
                alignment: StatusBarAlignment.LEFT,
                priority: 100,
                tooltip: 'ARC daemon not reachable',
            });
        }
    }
}
```

#### [SCAFFOLD] Protocol Types with Schema Version (TypeScript)

```typescript
// packages/arc-extension/src/common/arc-protocol-events.ts
/**
 * Versioned event types mirroring ADR-004 Python event registry.
 */

export const CURRENT_SCHEMA_VERSION = 1;

export interface RunEvent {
    schema_version: number;
    type: RunEventType;
    timestamp: string;
    run_id: string;
    sequence: number;
    data: Record<string, unknown>;
}

export type RunEventType =
    | 'RUN_STARTED'
    | 'RUN_COMPLETED'
    | 'RUN_FAILED'
    | 'RUN_CANCELLED'
    | 'STEP_STARTED'
    | 'STEP_COMPLETED'
    | 'STEP_FAILED'
    | 'TEXT_MESSAGE_START'
    | 'TEXT_MESSAGE_CONTENT'
    | 'TEXT_MESSAGE_END'
    | 'TOOL_CALL_START'
    | 'TOOL_CALL_ARGS'
    | 'TOOL_CALL_END'
    | 'TOOL_CALL_RESULT'
    | 'STATE_SNAPSHOT'
    | 'RAW'
    | 'CUSTOM';

export function parseRunEvent(raw: string): RunEvent {
    const event = JSON.parse(raw) as RunEvent;
    if (!event.schema_version) {
        event.schema_version = 1;
    }
    if (event.schema_version > CURRENT_SCHEMA_VERSION) {
        return {
            ...event,
            type: 'RAW',
            data: { raw: event },
        };
    }
    return event;
}

export function isRunEventType(type: string): type is RunEventType {
    const validTypes: RunEventType[] = [
        'RUN_STARTED', 'RUN_COMPLETED', 'RUN_FAILED', 'RUN_CANCELLED',
        'STEP_STARTED', 'STEP_COMPLETED', 'STEP_FAILED',
        'TEXT_MESSAGE_START', 'TEXT_MESSAGE_CONTENT', 'TEXT_MESSAGE_END',
        'TOOL_CALL_START', 'TOOL_CALL_ARGS', 'TOOL_CALL_END', 'TOOL_CALL_RESULT',
        'STATE_SNAPSHOT', 'RAW', 'CUSTOM',
    ];
    return validTypes.includes(type as RunEventType);
}
```

#### [SCAFFOLD] Frontend Module Tests (TypeScript/Jest)

```typescript
// packages/arc-extension/src/browser/__tests__/arc-frontend-contribution.test.ts
import { ArcFrontendContribution, ARC_COMMANDS } from '../arc-frontend-contribution';

describe('ArcFrontendContribution', () => {
    it('should define expected commands', () => {
        expect(ARC_COMMANDS.OPEN.id).toBe('arc.open');
        expect(ARC_COMMANDS.DETECT_WORKFLOWS.id).toBe('arc.detectWorkflows');
        expect(ARC_COMMANDS.RUN_WORKFLOW.id).toBe('arc.runWorkflow');
        expect(ARC_COMMANDS.CANCEL_RUN.id).toBe('arc.cancelRun');
    });

    it('should have correct widget factory ID', () => {
        const { ARC_WIDGET_FACTORY_ID } = require('../arc-extension-frontend-module');
        expect(ARC_WIDGET_FACTORY_ID).toBe('arc-studio');
    });
});
```

```typescript
// packages/arc-extension/src/common/__tests__/arc-protocol-events.test.ts
import { parseRunEvent, isRunEventType, CURRENT_SCHEMA_VERSION } from '../arc-protocol-events';

describe('parseRunEvent', () => {
    it('should add schema_version when missing', () => {
        const raw = JSON.stringify({
            type: 'RUN_STARTED',
            timestamp: '2026-05-14T00:00:00Z',
            run_id: 'run-001',
            sequence: 0,
            data: {},
        });
        const event = parseRunEvent(raw);
        expect(event.schema_version).toBe(1);
    });

    it('should downgrade unknown future version to RAW', () => {
        const raw = JSON.stringify({
            schema_version: 999,
            type: 'FUTURE_TYPE',
            timestamp: '2026-05-14T00:00:00Z',
            run_id: 'run-001',
            sequence: 0,
            data: { foo: 'bar' },
        });
        const event = parseRunEvent(raw);
        expect(event.type).toBe('RAW');
        expect(event.data).toHaveProperty('raw');
    });

    it('should preserve current version events', () => {
        const raw = JSON.stringify({
            schema_version: CURRENT_SCHEMA_VERSION,
            type: 'RUN_COMPLETED',
            timestamp: '2026-05-14T00:00:00Z',
            run_id: 'run-001',
            sequence: 5,
            data: { duration_ms: 1500 },
        });
        const event = parseRunEvent(raw);
        expect(event.type).toBe('RUN_COMPLETED');
        expect(event.schema_version).toBe(CURRENT_SCHEMA_VERSION);
    });
});

describe('isRunEventType', () => {
    it('should recognize valid event types', () => {
        expect(isRunEventType('RUN_STARTED')).toBe(true);
        expect(isRunEventType('STEP_COMPLETED')).toBe(true);
        expect(isRunEventType('TOOL_CALL_RESULT')).toBe(true);
    });

    it('should reject invalid event types', () => {
        expect(isRunEventType('INVALID_TYPE')).toBe(false);
        expect(isRunEventType('')).toBe(false);
    });
});
```

### e. How to Verify This Still Works

```bash
# 1. Verify Theia version alignment
cd packages/arc-extension && pnpm list @theia/core
cd packages/arc-browser-app && pnpm list @theia/core
# Check for version mismatch

# 2. Build the extension
cd packages/arc-extension && pnpm build

# 3. Build the browser app
cd packages/arc-browser-app && pnpm build

# 4. Run frontend tests
cd packages/arc-extension && pnpm test

# 5. Start browser app and verify ARC Studio loads
cd packages/arc-browser-app && pnpm start
# Navigate to http://localhost:3000
# Verify: ARC Studio widget opens via command palette

# 6. Verify Inversify DI bindings
# Check that all services are bound in arc-extension-backend-module.ts
grep -c "bind(" packages/arc-extension/src/node/arc-extension-backend-module.ts
# Expected: 6+ bindings

# 7. Verify protocol types compile
cd packages/arc-extension && npx tsc --noEmit
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| Theia version mismatch (extension ^1.45.0 vs browser app 1.71.0) | DI bindings, API changes | Align versions before P3; test current setup first |
| Duplicate extensions have conflicting protocol types | Type errors during porting | Migrate all to canonical `arc-protocol.ts`; delete duplicates |
| `arc-core` has backend logic that conflicts with canonical extension | Duplicate service bindings | Archive `arc-core`; port only UI widgets |
| `arc-arena` stub presented as product | Overclaiming LM Arena | Archive `arc-arena`; keep stub-default behavior out of canonical shell |
| React widget state management complexity | UI bugs, stale state | Use React hooks; avoid Theia state in React components |
| JSON-RPC connection drops | UI shows stale data | Add reconnection logic; status bar indicator |
| Porting complex UI from duplicate extensions | Scope creep | Port only useful, product-relevant UI; archive the rest |
| Theia 1.71+ API changes | Breaking changes in extension | Test against target version; pin version range |

### g. Sources

- Context7: `/eclipse-theia/theia` — ContainerModule, WidgetFactory, CommandContribution, ReactWidget
- Context7: `/inversify/inversifyjs` — @injectable, Container, ContainerModule, binding scopes
- `packages/arc-extension/src/node/arc-extension-backend-module.ts` — Current DI module
- `packages/arc-extension/src/common/arc-protocol.ts` — Current protocol types (438 lines)
- `packages/arc-extension/src/browser/arc-widget.tsx` — Current main widget (~450 lines)
- `packages/arc-extension/package.json` — Extension dependencies (@theia/core ^1.45.0)
- `packages/arc-browser-app/package.json` — Browser app dependencies (@theia/core ^1.45.0)
- `docs/IMPLEMENTATION_PLAN.md` — Theia Extension Migration Policy
- `docs/research/EXTERNAL_TOOLS_UI_RESEARCH.md` — Theia Extension Patterns (Section 10, 357-475)
- `docs/adr/000-execution-core-contract.md` — IDE integration contract
- `docs/adr/004-event-schema-versioning.md` — TypeScript mirror types

---

## 6. Audit, HITL, Replay (P2 / P4)

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P2: Runtime + SwarmGraph Integrations":

> "SwarmGraph audit verify path — verify SwarmGraph audit chains without claiming full key management UX."

> "Add trace replay + HITL persistence/CLI contracts."

From `docs/adr/005-audit-key-management.md`:

> "Keyed audit chains (HMAC target), keychain preferred, env fallback with degraded status."

From the vendored SwarmGraph `swarm_shared/audit.py` (474 lines):

> "Tamper-evident audit log primitives (HMAC-SHA256 + hash chain). Three primitives: AuditRecord, sign_record, verify_record. Plus verify_chain and load_jsonl_chain."

### b. Current External State

#### Python stdlib hmac / hashlib

- **Library:** Python stdlib `hmac`, `hashlib`
- **API:** `hmac.new(key, msg, digestmod)`, `hmac.compare_digest(a, b)`, `hashlib.sha256(data)`
- **Maintenance:** stdlib, stable since Python 3.x inception
- **ARC relevance:** Core primitives for HMAC-SHA256 audit signing. No external dependency needed.

#### Vendored SwarmGraph audit.py (474 lines)

- **Location:** `runtimes/swarmgraph/packages/swarm-shared/swarm_shared/audit.py`
- **API:** `AuditRecord` (Pydantic frozen model), `sign_record(record_dict, *, secret, prev_hash)`, `verify_record(record, *, secret, prev_hash)`, `verify_chain(records, *, secret)`, `load_jsonl_chain(path)`
- **Threat model:** Protects against insertion, deletion, reordering, tampering. Does NOT protect against secret compromise or wholesale log replacement.
- **Canonical serialization:** `model_dump_json(sort_keys=True)` for deterministic signatures.
- **ARC relevance:** ARC already has `audit/chain.py` (69 lines) with SHA-256 hash chain (unauthenticated). The vendored SwarmGraph audit provides HMAC-authenticated chains. ARC should bridge the two: use SwarmGraph's HMAC signing for SwarmGraph-originated audit records, and add HMAC to ARC's own chain.

#### ARC audit/chain.py (69 lines, current)

- **Location:** `python/src/agent_runtime_cockpit/audit/chain.py`
- **API:** `AuditChainWriter` (context manager, append-only), `verify(path, events_jsonl)` — walks audit + raw events, flags drift
- **Mechanism:** SHA-256 hash chain with `prev_hash` and `chain_hash`. No HMAC authentication — anyone can forge a valid chain.
- **Gap:** Missing HMAC signing, missing key management, missing integration with SwarmGraph audit.

#### keyring (PyPI 25.7.0, Nov 2025)

- **Library:** PyPI `keyring`
- **API:** `get_password(service, username)`, `set_password(service, username, password)`, `delete_password(service, username)`, `get_credential(service, url)`
- **Backends:** macOS Keychain, Freedesktop Secret Service (Linux), KDE KWallet, Windows Credential Locker
- **License:** MIT
- **Maintenance:** Active. Latest: 25.7.0 (Nov 2025).
- **ARC relevance:** Preferred storage for audit keys. Env fallback with degraded status when keychain unavailable.

#### structlog (25.5.0, Oct 2025)

- **Library:** `/hynek/structlog`
- **API:** `get_logger()`, `bind()`, processors chain, `JSONRenderer`, stdlib integration via `structlog.stdlib.ProcessorFormatter`
- **License:** MIT / Apache-2.0
- **Maintenance:** Active. Latest: 25.5.0 (Oct 2025).
- **ARC relevance:** Structured JSON logging that integrates with audit systems. Not yet adopted in ARC (currently uses stdlib `logging`).

### c. Recommended Approach for ARC

1. **P2: Add HMAC verification for SwarmGraph audit chains.** Import vendored `swarm_shared/audit.py` functions, verify existing SwarmGraph chains. Do not claim signing capability yet.
2. **P2: Add HMAC to ARC's own `audit/chain.py`.** Upgrade from unauthenticated SHA-256 chain to HMAC-SHA256. Use `keyring` for key storage with env fallback.
3. **P2: Add `arc audit verify` CLI command.** Verify audit chains for a given run. Report verification status with degraded warnings.
4. **P2: Add `arc audit export` CLI command.** Export audit records in a format suitable for external verification.
5. **P4: Full key management UX.** Key rotation, keychain setup UI, degraded mode indicators in the IDE.
6. **HITL (Human-in-the-Loop):** P2 adds persistence/CLI contracts for HITL decisions. HITL decisions are audit-signed records. The SSE broker streams HITL prompts to the UI; responses are posted back and audit-signed.
7. **Replay:** P2 adds trace replay via the event broker (Section 11). Replay reads stored JSONL events and streams them via SSE. HITL decisions from the original run are replayed as part of the trace.

### d. Code Scaffolds

#### [SCAFFOLD] HMAC Audit Key Manager (Python)

```python
# python/src/agent_runtime_cockpit/audit/key_manager.py
"""HMAC audit key management with keychain storage and env fallback (ADR-005)."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

ARC_AUDIT_SERVICE = "arc-studio-audit"
ARC_AUDIT_KEY_ID = "hmac-audit-key-v1"


class AuditKeyStatus(BaseModel):
    available: bool
    source: str
    degraded: bool = False
    warning: str = ""
    key_id: str = ""


class AuditKeyManager:
    """Manages HMAC-SHA256 audit keys with keychain preference and env fallback."""

    def __init__(self, service: str = ARC_AUDIT_SERVICE, key_id: str = ARC_AUDIT_KEY_ID) -> None:
        self.service = service
        self.key_id = key_id

    def get_key(self) -> tuple[Optional[bytes], AuditKeyStatus]:
        """Retrieve HMAC audit key. Tries keychain first, then env fallback."""
        keychain_key = self._try_keychain()
        if keychain_key is not None:
            return keychain_key, AuditKeyStatus(
                available=True, source="keychain", key_id=self.key_id,
            )
        env_key = os.environ.get("ARC_AUDIT_HMAC_KEY")
        if env_key:
            return env_key.encode("utf-8"), AuditKeyStatus(
                available=True, source="env", degraded=True, key_id="env-fallback",
                warning="Using env fallback for audit key — keychain preferred for production",
            )
        return None, AuditKeyStatus(
            available=False, source="none", degraded=True,
            warning="No audit key available — audit signing disabled. Set ARC_AUDIT_HMAC_KEY or run 'arc audit key init'.",
        )

    def set_key(self, key: str) -> bool:
        """Store HMAC audit key in keychain. Returns True on success."""
        try:
            import keyring
            keyring.set_password(self.service, self.key_id, key)
            log.info("Audit key stored in keychain: %s/%s", self.service, self.key_id)
            return True
        except Exception as e:
            log.warning("Failed to store audit key in keychain: %s", e)
            return False

    def delete_key(self) -> bool:
        """Delete HMAC audit key from keychain. Returns True on success."""
        try:
            import keyring
            keyring.delete_password(self.service, self.key_id)
            log.info("Audit key deleted from keychain: %s/%s", self.service, self.key_id)
            return True
        except Exception as e:
            log.warning("Failed to delete audit key from keychain: %s", e)
            return False

    def generate_key(self) -> str:
        """Generate a cryptographically random HMAC key (hex-encoded)."""
        return os.urandom(32).hex()

    def _try_keychain(self) -> Optional[bytes]:
        try:
            import keyring
            key_str = keyring.get_password(self.service, self.key_id)
            if key_str:
                return key_str.encode("utf-8")
        except Exception as e:
            log.debug("Keychain access failed: %s", e)
        return None


def sign_audit_record(data: dict, key: bytes, prev_hash: str = "GENESIS") -> tuple[str, str]:
    """Sign audit record data with HMAC-SHA256.

    Returns (record_hash, signature).
    record_hash = SHA-256(canonical_json(data) + prev_hash)
    signature = HMAC-SHA256(key, record_hash)
    """
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    record_hash = hashlib.sha256(payload + prev_hash.encode("utf-8")).hexdigest()
    signature = hmac.new(key, record_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return record_hash, signature


def verify_audit_signature(
    data: dict, signature: str, key: bytes, prev_hash: str = "GENESIS"
) -> bool:
    """Verify HMAC-SHA256 signature of audit record. Uses constant-time comparison."""
    expected_hash, expected_sig = sign_audit_record(data, key, prev_hash)
    return hmac.compare_digest(expected_sig, signature)
```

#### [SCAFFOLD] HMAC-Authenticated Audit Chain Writer (Python)

```python
# python/src/agent_runtime_cockpit/audit/hmac_chain.py
"""HMAC-authenticated audit chain writer and verifier."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from .key_manager import AuditKeyManager, sign_audit_record, verify_audit_signature

log = logging.getLogger(__name__)

GENESIS = "GENESIS"


class HmacAuditChainWriter:
    """Append-only audit-chain scaffold.

    Production decision required before merge: reuse vendored swarm_shared.audit or
    explicitly ship separate ARC/SwarmGraph verifiers. Do not silently reinvent
    canonicalization. Writer must resume _prev_hash/_seq from existing files before append.
    """

    def __init__(self, path: Path, key_manager: AuditKeyManager) -> None:
        self.path = path
        self.key_manager = key_manager
        self._seq, self._prev_hash = self._load_tail_state()

    def _load_tail_state(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, GENESIS
        last: dict[str, Any] | None = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = json.loads(line)
        if last is None:
            return 0, GENESIS
        return int(last["seq"]) + 1, str(last["record_hash"])

    def append(self, event: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Append an event to the audit chain. Returns the signed record, or None if no key."""
        key, status = self.key_manager.get_key()
        if key is None:
            log.warning("No audit key available — skipping HMAC signing for seq %d", self._seq)
            return None
        record_hash, signature = sign_audit_record(event, key, self._prev_hash)
        record = {
            "seq": self._seq,
            "event": event,
            "prev_hash": self._prev_hash,
            "record_hash": record_hash,
            "signature": signature,
            "key_source": status.source,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            f.flush()
        self._prev_hash = record_hash
        self._seq += 1
        return record


def verify_hmac_chain(chain_path: Path, key: bytes) -> tuple[bool, str]:
    """Verify an HMAC-signed audit chain.

    Returns (ok, reason). Walks the chain and verifies each record's signature
    and chain hash continuity.
    """
    if not chain_path.exists():
        return False, f"Chain file not found: {chain_path}"
    lines = chain_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return True, "empty chain"
    prev_hash = GENESIS
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return False, f"invalid JSON at line {i}"
        event = record.get("event", {})
        signature = record.get("signature", "")
        stored_prev = record.get("prev_hash", "")
        stored_hash = record.get("record_hash", "")
        if stored_prev != prev_hash:
            return False, f"chain broken at seq {i}: prev_hash mismatch"
        if not verify_audit_signature(event, signature, key, prev_hash):
            return False, f"signature invalid at seq {i}"
        prev_hash = stored_hash
    return True, f"verified {len([l for l in lines if l.strip()])} records"
```

#### [SCAFFOLD] HITL Decision Record (Python)

```python
# python/src/agent_runtime_cockpit/audit/hitl.py
"""Human-in-the-Loop decision records — audit-signed HITL persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class HitlDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    SKIP = "skip"


class HitlPrompt(BaseModel):
    """A HITL prompt sent to a human operator."""
    hitl_id: str
    run_id: str
    step_id: str
    prompt_text: str
    context: dict[str, Any] = Field(default_factory=dict)
    options: list[str] = Field(default_factory=lambda: [d.value for d in HitlDecision])
    timeout_seconds: int = 300
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HitlResponse(BaseModel):
    """A human operator's response to a HITL prompt."""
    hitl_id: str
    run_id: str
    decision: HitlDecision
    operator_id: str = "anonymous"
    modified_data: Optional[dict[str, Any]] = None
    notes: str = ""
    responded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_audit_event(self) -> dict[str, Any]:
        """Convert to an audit-signable event dict."""
        return {
            "type": "hitl_decision",
            "hitl_id": self.hitl_id,
            "run_id": self.run_id,
            "decision": self.decision.value,
            "operator_id": self.operator_id,
            "modified_data": self.modified_data,
            "notes": self.notes,
            "responded_at": self.responded_at,
        }
```

#### [SCAFFOLD] Trace Replay Service (Python)

```python
# python/src/agent_runtime_cockpit/audit/replay.py
"""Trace replay — re-stream stored JSONL events for replay and HITL review."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, AsyncIterator

from ..storage.jsonl import JsonlTraceStore

log = logging.getLogger(__name__)


class TraceReplayService:
    """Replays stored trace events. Used for HITL review and debugging."""

    def __init__(self, store: JsonlTraceStore) -> None:
        self.store = store

    async def replay_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield events from a stored trace in order."""
        trace_path = self.store.trace_path(run_id)
        if not trace_path.exists():
            log.warning("Trace not found for replay: %s", run_id)
            return
        with open(trace_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    yield event
                except json.JSONDecodeError as e:
                    log.warning("Skipping malformed trace line: %s", e)
                    continue

    async def replay_with_hitl_decisions(
        self, run_id: str, hitl_chain_path: Path
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay trace events interleaved with HITL decisions from audit chain."""
        hitl_decisions: dict[str, dict[str, Any]] = {}
        if hitl_chain_path.exists():
            with open(hitl_chain_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        event = record.get("event", {})
                        if event.get("type") == "hitl_decision":
                            hitl_decisions[event.get("hitl_id", "")] = event
                    except json.JSONDecodeError:
                        continue
        async for event in self.replay_events(run_id):
            yield event
            hitl_id = event.get("data", {}).get("hitl_id")
            if hitl_id and hitl_id in hitl_decisions:
                yield {
                    "type": "HITL_DECISION_REPLAY",
                    "data": hitl_decisions[hitl_id],
                }
```

#### [SCAFFOLD] Audit and HITL Tests

```python
# python/tests/audit/test_hmac_chain.py
"""Tests for HMAC-authenticated audit chain."""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch
from agent_runtime_cockpit.audit.key_manager import (
    AuditKeyManager, sign_audit_record, verify_audit_signature, AuditKeyStatus,
)
from agent_runtime_cockpit.audit.hmac_chain import (
    HmacAuditChainWriter, verify_hmac_chain, GENESIS,
)


def test_sign_and_verify():
    key = b"test-hmac-key-32-bytes-long!!"
    data = {"run_id": "run-001", "action": "consensus", "result": "approved"}
    record_hash, signature = sign_audit_record(data, key)
    assert len(record_hash) == 64
    assert len(signature) == 64
    assert verify_audit_signature(data, signature, key) is True
    assert verify_audit_signature(data, signature, b"wrong-key") is False


def test_tampered_data_fails_verification():
    key = b"test-hmac-key-32-bytes-long!!"
    data = {"run_id": "run-001", "action": "consensus"}
    record_hash, signature = sign_audit_record(data, key)
    tampered = {**data, "action": "rejected"}
    assert verify_audit_signature(tampered, signature, key) is False


def test_chain_continuity():
    key = b"test-hmac-key-32-bytes-long!!"
    prev = GENESIS
    hashes = []
    for i in range(5):
        data = {"seq": i, "value": f"item-{i}"}
        rh, sig = sign_audit_record(data, key, prev)
        hashes.append(rh)
        prev = rh
    for i, data in enumerate([{"seq": j, "value": f"item-{j}"} for j in range(5)]):
        rh, sig = sign_audit_record(data, key, GENESIS if i == 0 else hashes[i - 1])
        assert rh == hashes[i]


def test_key_manager_env_fallback():
    with patch.dict(os.environ, {"ARC_AUDIT_HMAC_KEY": "env-test-key"}):
        with patch("keyring.get_password", side_effect=Exception("no keychain")):
            mgr = AuditKeyManager()
            key, status = mgr.get_key()
            assert key == b"env-test-key"
            assert status.source == "env"
            assert status.degraded is True


def test_key_manager_no_key():
    with patch.dict(os.environ, {}, clear=True):
        with patch("keyring.get_password", side_effect=Exception("no keychain")):
            mgr = AuditKeyManager()
            key, status = mgr.get_key()
            assert key is None
            assert status.available is False


def test_hmac_chain_writer_and_verify(tmp_path: Path):
    key = b"test-hmac-key-32-bytes-long!!"
    chain_path = tmp_path / "audit.jsonl"
    with patch("keyring.get_password", return_value=key.decode("utf-8")):
        mgr = AuditKeyManager()
        writer = HmacAuditChainWriter(chain_path, mgr)
        writer.append({"action": "init", "run_id": "r1"})
        writer.append({"action": "step", "run_id": "r1", "step": 1})
        writer.append({"action": "complete", "run_id": "r1"})
    ok, reason = verify_hmac_chain(chain_path, key)
    assert ok is True
    assert "verified 3 records" in reason


def test_hmac_chain_tamper_detected(tmp_path: Path):
    key = b"test-hmac-key-32-bytes-long!!"
    chain_path = tmp_path / "audit.jsonl"
    with patch("keyring.get_password", return_value=key.decode("utf-8")):
        mgr = AuditKeyManager()
        writer = HmacAuditChainWriter(chain_path, mgr)
        writer.append({"action": "init"})
        writer.append({"action": "step"})
    lines = chain_path.read_text().splitlines()
    tampered_record = json.loads(lines[1])
    tampered_record["event"]["action"] = "tampered"
    lines[1] = json.dumps(tampered_record, sort_keys=True, separators=(",", ":"))
    chain_path.write_text("\n".join(lines) + "\n")
    ok, reason = verify_hmac_chain(chain_path, key)
    assert ok is False
    assert "signature invalid" in reason
```

```python
# python/tests/audit/test_hitl.py
"""Tests for HITL decision records."""
import pytest
from agent_runtime_cockpit.audit.hitl import (
    HitlPrompt, HitlResponse, HitlDecision,
)


def test_hitl_prompt_defaults():
    prompt = HitlPrompt(
        hitl_id="hitl-001", run_id="run-001", step_id="step-1",
        prompt_text="Approve this tool call?",
    )
    assert prompt.timeout_seconds == 300
    assert prompt.options == ["approve", "reject", "modify", "skip"]


def test_hitl_response_to_audit_event():
    response = HitlResponse(
        hitl_id="hitl-001", run_id="run-001",
        decision=HitlDecision.APPROVE, operator_id="user-1",
    )
    event = response.to_audit_event()
    assert event["type"] == "hitl_decision"
    assert event["decision"] == "approve"
    assert event["operator_id"] == "user-1"


def test_hitl_response_with_modification():
    response = HitlResponse(
        hitl_id="hitl-002", run_id="run-001",
        decision=HitlDecision.MODIFY, operator_id="user-1",
        modified_data={"tool_input": "sanitized_value"},
        notes="Removed sensitive data from tool input",
    )
    event = response.to_audit_event()
    assert event["decision"] == "modify"
    assert event["modified_data"]["tool_input"] == "sanitized_value"
```

```python
# python/tests/audit/test_replay.py
"""Tests for trace replay service."""
import json
import pytest
from pathlib import Path
from agent_runtime_cockpit.audit.replay import TraceReplayService
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore


@pytest.mark.asyncio
async def test_replay_events(tmp_path: Path):
    store = JsonlTraceStore(base_dir=tmp_path / "traces")
    trace_path = store.trace_path("replay-test")
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    events = [
        {"type": "RUN_STARTED", "seq": 0},
        {"type": "STEP_STARTED", "seq": 1},
        {"type": "STEP_COMPLETED", "seq": 2},
        {"type": "RUN_COMPLETED", "seq": 3},
    ]
    with open(trace_path, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
    service = TraceReplayService(store)
    replayed = []
    async for event in service.replay_events("replay-test"):
        replayed.append(event)
    assert len(replayed) == 4
    assert replayed[0]["type"] == "RUN_STARTED"
    assert replayed[3]["type"] == "RUN_COMPLETED"


@pytest.mark.asyncio
async def test_replay_nonexistent_run(tmp_path: Path):
    store = JsonlTraceStore(base_dir=tmp_path / "traces")
    service = TraceReplayService(store)
    replayed = []
    async for event in service.replay_events("nonexistent"):
        replayed.append(event)
    assert len(replayed) == 0
```

### e. How to Verify This Still Works

```bash
# 1. Verify Python stdlib hmac/hashlib availability
python3 -c "import hmac, hashlib; print('hmac + hashlib OK')"

# 2. Verify keyring on current platform
python3 -c "
import keyring
backend = keyring.get_keyring()
print(f'Keyring backend: {type(backend).__name__}')
"

# 3. Verify vendored SwarmGraph audit module is importable
python3 -c "
import sys
sys.path.insert(0, 'runtimes/swarmgraph/packages/swarm-shared')
from swarm_shared.audit import AuditRecord, sign_record, verify_record
print('SwarmGraph audit module importable')
"

# 4. Run HMAC chain tests
cd python && uv run pytest tests/audit/test_hmac_chain.py -v

# 5. Run HITL tests
cd python && uv run pytest tests/audit/test_hitl.py -v

# 6. Run replay tests
cd python && uv run pytest tests/audit/test_replay.py -v

# 7. Verify structlog version (future adoption)
pip index versions structlog 2>/dev/null | head -3
# Expected: 25.x
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| keyring fails on headless Linux / CI environments | Audit key storage unavailable | Env fallback with degraded status; document platform support |
| Vendored SwarmGraph audit.py diverges from upstream | Verification breaks after sync | Pin vendored version; add import compatibility layer |
| HMAC key compromise | Attacker can forge audit chains | Key rotation support in P4; pin rotation timestamps |
| Float precision in canonical JSON | Cross-platform signature drift | Pre-quantize floats before assignment; test cross-platform |
| HITL timeout UX | Operators miss prompts | Default 300s timeout; configurable per profile; auto-skip on timeout |
| Replay with missing HITL decisions | Gaps in replay stream | Graceful degradation — replay continues without HITL decision records |
| structlog adoption breaks existing logging | Log format changes | Spike structlog integration; keep stdlib logging as fallback |

### g. Sources

- `docs/adr/005-audit-key-management.md` — Audit key management strategy
- `python/src/agent_runtime_cockpit/audit/chain.py` — Current SHA-256 hash chain (69 lines)
- `runtimes/swarmgraph/packages/swarm-shared/swarm_shared/audit.py` — Vendored SwarmGraph HMAC-signed audit module (474 lines)
- PyPI: `keyring` 25.7.0 — Cross-platform keychain access
- PyPI: `structlog` 25.5.0 — Structured logging (future adoption)
- Python stdlib: `hmac`, `hashlib` — HMAC-SHA256 primitives
- `docs/IMPLEMENTATION_PLAN.md` — P2 audit scope, HITL persistence

---

## 7. Workspace Trust and Isolation (P1a / P2 / P3)

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P1a: Execution Core Infrastructure":

> "Add workspace trust resolver — execution can distinguish trusted vs untrusted workspaces."

> "Add isolation provider interface — execution boundary becomes pluggable and honestly reported."

> "Harden subprocess env allowlists — adapter subprocesses leak fewer secrets before container isolation exists."

From `docs/adr/006-workspace-trust-isolation.md`:

> "Trust levels: UNTRUSTED/PARTIAL/TRUSTED. Isolation providers: none/subprocess/docker/firecracker."

### b. Current External State

#### docker Python SDK (7.1.0, May 2024)

- **Library:** PyPI `docker`
- **API:** `docker.from_env()`, `client.containers.run()`, `client.containers.list()`, `client.containers.get()`, `container.exec_run()`
- **License:** Apache 2.0
- **Maintenance:** Last release May 2024. Stable API. Docker, Inc. maintained.
- **ARC relevance:** P2/P3 isolation provider. Docker-compatible container isolation for untrusted workspaces.
- **Compatibility:** OrbStack is Docker-compatible on macOS. Podman and Colima are Docker-compatible alternatives (via `DOCKER_HOST` env var).

#### OrbStack (macOS)

- **Product:** OrbStack — lightweight Docker-compatible container runtime for macOS
- **API:** Docker-compatible CLI and daemon. `docker` Python SDK works transparently.
- **ARC relevance:** Preferred container runtime on macOS. Lower overhead than Docker Desktop.

#### Podman / Colima

- **Products:** Podman (Red Hat, daemonless), Colima (macOS Lima-based)
- **API:** Docker-compatible via `DOCKER_HOST` env var. Podman also supports `podman` CLI.
- **ARC relevance:** Alternative container runtimes. Detection via `DOCKER_HOST` or CLI presence.

#### Python subprocess (stdlib)

- **Library:** Python stdlib `asyncio.create_subprocess_exec`, `subprocess.run`
- **API:** `create_subprocess_exec(*args, cwd=, env=, stdout=, stderr=)`, `proc.communicate()`, `proc.kill()`
- **ARC relevance:** P1a isolation provider. Subprocess with env allowlist and path restriction.

#### Current ARC security/ directory

- **Location:** `python/src/agent_runtime_cockpit/security/`
- **Files:** `profiles.py`, `redaction.py`, `validation.py`
- **Current state:** Has `validate_workspace_path()` for path validation. No trust resolver. No isolation provider interface.

### c. Recommended Approach for ARC

1. **P1a: Trust resolver (advisory).** Read an external trust database such as `~/.arc/trusted-workspaces.json`. Report trust level. Warn on untrusted. Do not block execution. Ignore workspace-local `.arc/trusted` because repos can self-authorize it.
2. **P1a: Isolation provider interface.** Define `IsolationProvider` ABC with `none` and `subprocess` implementations. Subprocess uses env allowlist.
3. **P1a: Subprocess env allowlists.** Define per-adapter safe env keys. Redact secret-like values from stdout/stderr before trace storage.
4. **P2: Docker isolation provider.** Implement `DockerIsolationProvider` using the `docker` SDK. Detect OrbStack/Podman/Colima compatibility.
5. **P2: Trust enforcement.** Flip from advisory to enforcement. Block execution for untrusted workspaces when isolation is `none`.
6. **P3: Firecracker / gVisor.** Spike advanced isolation. Only if Docker proves insufficient for high-security use cases.

### d. Code Scaffolds

#### [SCAFFOLD] Docker Isolation Provider (Python)

```python
# python/src/agent_runtime_cockpit/isolation/docker_provider.py
"""Docker isolation provider — container-based execution for untrusted workspaces."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from .base import IsolationProvider, IsolationResult

log = logging.getLogger(__name__)


class DockerConfig(BaseModel):
    image: str = "python:3.12-slim"
    volumes: dict[str, dict[str, str]] = Field(default_factory=dict)
    network_disabled: bool = True
    mem_limit: str = "512m"
    cpu_quota: int = 50000
    environment: dict[str, str] = Field(default_factory=dict)


class DockerIsolationProvider(IsolationProvider):
    """Container-based isolation using Docker SDK.

    Detects OrbStack, Podman, Colima via DOCKER_HOST or daemon info.
    """

    def __init__(self, config: Optional[DockerConfig] = None) -> None:
        self.config = config or DockerConfig()
        self._client = None

    @property
    def provider_id(self) -> str:
        return "docker"

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            version = client.version()
            log.debug("Docker daemon reachable: %s", version.get("ServerVersion", "unknown"))
            return True
        except Exception as e:
            log.warning("Docker health check failed: %s", e)
            return False

    async def execute(
        self,
        command: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        client = self._get_client()
        merged_env = {**self.config.environment, **(env or {})}
        start = time.monotonic()
        try:
            container = client.containers.run(
                image=self.config.image,
                command=command,
                working_dir=str(cwd) if cwd else "/workspace",
                environment=merged_env,
                volumes=self.config.volumes,
                network_disabled=self.config.network_disabled,
                mem_limit=self.config.mem_limit,
                cpu_quota=self.config.cpu_quota,
                detach=True,
                remove=True,
            )
            try:
                result = container.wait(timeout=timeout_seconds)
                exit_code = result.get("StatusCode", -1)
            except Exception:
                container.kill()
                duration = int((time.monotonic() - start) * 1000)
                return IsolationResult(
                    exit_code=-1, stdout="", stderr="container timeout",
                    duration_ms=duration, killed=True, kill_reason="timeout",
                )
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            duration = int((time.monotonic() - start) * 1000)
            return IsolationResult(
                exit_code=exit_code, stdout=logs, stderr="",
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            log.error("Docker execution failed: %s", e)
            return IsolationResult(
                exit_code=-1, stdout="", stderr=str(e),
                duration_ms=duration,
            )

    def detect_runtime(self) -> dict[str, Any]:
        """Detect which Docker-compatible runtime is available."""
        info: dict[str, Any] = {"available": False, "runtime": "unknown"}
        try:
            client = self._get_client()
            version_info = client.version()
            info["available"] = True
            info["version"] = version_info.get("ServerVersion", "unknown")
            server = version_info.get("ServerVersion", "")
            if "orbstack" in server.lower():
                info["runtime"] = "orbstack"
            elif "podman" in server.lower():
                info["runtime"] = "podman"
            else:
                info["runtime"] = "docker"
        except Exception as e:
            info["error"] = str(e)
        return info

    def _get_client(self):
        if self._client is None:
            import docker
            self._client = docker.from_env()
        return self._client
```

#### [SCAFFOLD] Workspace Trust Enforcement (Python)

```python
# python/src/agent_runtime_cockpit/security/trust_enforcement.py
"""Workspace trust enforcement — P2 blocking mode."""
from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel

from .trust import TrustLevel, TrustResolution, resolve_trust

log = logging.getLogger(__name__)


class TrustPolicy(BaseModel):
    """Policy for trust enforcement. P1a: advisory. P2: blocking."""
    enforce: bool = False
    minimum_level: TrustLevel = TrustLevel.PARTIAL
    allow_isolation_override: bool = False


class TrustEnforcementError(Exception):
    """Raised when trust check blocks execution."""
    def __init__(self, resolution: TrustResolution, policy: TrustPolicy) -> None:
        self.resolution = resolution
        self.policy = policy
        super().__init__(
            f"Execution blocked: workspace trust level '{resolution.level.value}' "
            f"below minimum '{policy.minimum_level.value}'. "
            f"Reason: {resolution.reason}"
        )


def check_trust_for_execution(
    workspace: Path,
    policy: TrustPolicy | None = None,
) -> TrustResolution:
    """Check workspace trust and enforce policy.

    P1a: policy.enforce=False → advisory only, returns resolution with warning.
    P2: policy.enforce=True → raises TrustEnforcementError if below minimum.
    """
    resolution = resolve_trust(workspace)
    if policy is None:
        policy = TrustPolicy()
    if not policy.enforce:
        return resolution
    level_order = {TrustLevel.UNTRUSTED: 0, TrustLevel.PARTIAL: 1, TrustLevel.TRUSTED: 2}
    if level_order[resolution.level] < level_order[policy.minimum_level]:
        raise TrustEnforcementError(resolution, policy)
    return resolution
```

#### [SCAFFOLD] Docker Isolation and Trust Tests

```python
# python/tests/isolation/test_docker_provider.py
"""Tests for Docker isolation provider."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from agent_runtime_cockpit.isolation.docker_provider import (
    DockerIsolationProvider, DockerConfig,
)


@pytest.mark.asyncio
async def test_docker_health_check_unavailable():
    with patch("docker.from_env", side_effect=Exception("daemon not reachable")):
        provider = DockerIsolationProvider()
        result = await provider.health_check()
        assert result is False


@pytest.mark.asyncio
async def test_docker_detect_runtime():
    mock_client = MagicMock()
    mock_client.version.return_value = {"ServerVersion": "24.0.7"}
    with patch("docker.from_env", return_value=mock_client):
        provider = DockerIsolationProvider()
        info = provider.detect_runtime()
        assert info["available"] is True
        assert info["runtime"] == "docker"


@pytest.mark.asyncio
async def test_docker_detect_orbstack():
    mock_client = MagicMock()
    mock_client.version.return_value = {"ServerVersion": "orbstack-1.5.0"}
    with patch("docker.from_env", return_value=mock_client):
        provider = DockerIsolationProvider()
        info = provider.detect_runtime()
        assert info["runtime"] == "orbstack"


@pytest.mark.asyncio
async def test_docker_execute_success():
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b"hello world\n"
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container
    with patch("docker.from_env", return_value=mock_client):
        provider = DockerIsolationProvider()
        result = await provider.execute(["echo", "hello"])
        assert result.exit_code == 0
        assert "hello world" in result.stdout


@pytest.mark.asyncio
async def test_docker_execute_timeout():
    mock_container = MagicMock()
    mock_container.wait.side_effect = Exception("timeout")
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container
    with patch("docker.from_env", return_value=mock_client):
        provider = DockerIsolationProvider()
        result = await provider.execute(["sleep", "10"], timeout_seconds=1)
        assert result.killed is True
        assert result.kill_reason == "timeout"
```

```python
# python/tests/security/test_trust_enforcement.py
"""Tests for workspace trust enforcement."""
import pytest
from pathlib import Path
from agent_runtime_cockpit.security.trust_enforcement import (
    TrustPolicy, TrustEnforcementError, check_trust_for_execution,
)
from agent_runtime_cockpit.security.trust import TrustLevel


def test_trust_check_advisory_mode(tmp_path: Path):
    policy = TrustPolicy(enforce=False)
    resolution = check_trust_for_execution(tmp_path, policy)
    assert resolution.level == TrustLevel.UNTRUSTED
    assert resolution.warning is not None


def test_trust_check_enforcement_blocks(tmp_path: Path):
    policy = TrustPolicy(enforce=True, minimum_level=TrustLevel.TRUSTED)
    with pytest.raises(TrustEnforcementError) as exc_info:
        check_trust_for_execution(tmp_path, policy)
    assert "Execution blocked" in str(exc_info.value)


def test_trust_check_enforcement_passes(tmp_path: Path):
    trust_marker = tmp_path / ".arc" / "trusted"
    trust_marker.parent.mkdir(parents=True, exist_ok=True)
    trust_marker.touch()
    policy = TrustPolicy(enforce=True, minimum_level=TrustLevel.TRUSTED)
    resolution = check_trust_for_execution(tmp_path, policy)
    assert resolution.level == TrustLevel.TRUSTED


def test_trust_enforcement_error_attributes(tmp_path: Path):
    policy = TrustPolicy(enforce=True, minimum_level=TrustLevel.TRUSTED)
    try:
        check_trust_for_execution(tmp_path, policy)
    except TrustEnforcementError as e:
        assert e.resolution.level == TrustLevel.UNTRUSTED
        assert e.policy.enforce is True
```

### e. How to Verify This Still Works

```bash
# 1. Verify docker SDK version
cd python && uv pip show docker 2>/dev/null | grep Version
# Expected: 7.x

# 2. Verify Docker daemon availability
docker info 2>/dev/null | head -5 || echo "Docker daemon not reachable"

# 3. Verify OrbStack detection (macOS)
docker version 2>/dev/null | grep -i orbstack || echo "Not OrbStack"

# 4. Run Docker isolation tests
cd python && uv run pytest tests/isolation/test_docker_provider.py -v

# 5. Run trust enforcement tests
cd python && uv run pytest tests/security/test_trust_enforcement.py -v

# 6. Verify committed workspace marker does not self-authorize
mkdir -p /tmp/test-trust/.arc && touch /tmp/test-trust/.arc/trusted
python3 -c "
from pathlib import Path
from agent_runtime_cockpit.security.trust import resolve_trust
r = resolve_trust(Path('/tmp/test-trust'))
print(f'Trust level: {r.level.value}')
assert r.level.value == 'untrusted'
"
rm -rf /tmp/test-trust
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| Docker daemon not available on all platforms | Isolation falls back to subprocess | Graceful degradation; report isolation level honestly |
| OrbStack/Podman API incompatibilities | Container execution fails unexpectedly | Runtime detection; test against each runtime; fallback to subprocess |
| Docker image pull latency | Slow first execution | Pre-pull default image; cache images; configurable image |
| Container resource limits too restrictive | User workflows OOM | Configurable mem_limit and cpu_quota per profile |
| Trust marker file accidentally committed | False trust in shared repos | Ignore `.arc/trusted`; trust must be external/user-profile-side |
| P1a advisory mode → P2 enforcement UX break | Users surprised by blocking | Clear warnings in P1a; migration guide for P2 |
| Firecracker/gVisor complexity (P3) | Scope creep | Spike first; only adopt if Docker isolation proves insufficient |

### g. Sources

- `docs/adr/006-workspace-trust-isolation.md` — Trust levels and isolation providers
- `python/src/agent_runtime_cockpit/security/trust.py` — Trust resolver (Section 2 scaffold)
- `python/src/agent_runtime_cockpit/isolation/base.py` — Isolation provider interface (Section 2 scaffold)
- PyPI: `docker` 7.1.0 — Docker SDK for Python
- OrbStack documentation — Docker-compatible macOS runtime
- Podman documentation — Daemonless container engine
- `docs/IMPLEMENTATION_PLAN.md` — P1a trust/isolation scope, P2 enforcement

---

## 8. Prompt Optimizer (P1b / P3 / P4)

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P1b: Adoption Foundation And Local Helpers":

> "Add local prompt optimizer — rule-based cleanup and token counting. No provider calls in P1b local mode."

From "P3: Advanced Features":

> "Provider-aware prompt optimization — template-based optimization with token cost estimation."

### b. Current External State

#### tiktoken (0.12.0, Oct 2025)

- **Library:** `/openai/tiktoken`
- **API:** `encoding_for_model(model_name)`, `encode(text)`, `decode(tokens)`, `get_encoding(encoding_name)`
- **License:** MIT
- **Maintenance:** Active. Latest: 0.12.0 (Oct 2025). OpenAI-maintained.
- **ARC relevance:** Token counting for cost estimation and prompt optimization. Used to estimate token usage before sending to providers.
- **Models supported:** GPT-4, GPT-3.5, and other OpenAI models. Encoding names: `cl100k_base`, `p50k_base`, `r50k_base`, `o200k_base`.

#### Local template-based optimization

- **Approach:** Rule-based prompt cleanup without provider calls. Remove redundant whitespace, collapse repeated patterns, trim trailing whitespace, normalize indentation.
- **ARC relevance:** P1b local mode. No external dependencies beyond tiktoken for counting.

#### Provider-based optimization (P3/P4)

- **Approach:** Use provider APIs to optimize prompts. E.g., OpenAI's embedding-based similarity check, or provider-specific prompt templates.
- **ARC relevance:** P3/P4 only. Requires provider credentials and cost gating.

### c. Recommended Approach for ARC

1. **P1b: Local prompt optimizer.** Rule-based cleanup + tiktoken token counting. No provider calls. Works offline.
2. **P1b: Token cost estimator.** Given a model name and prompt text, estimate token count and approximate cost using known pricing.
3. **P3: Provider-aware optimization.** Template-based optimization using provider-specific knowledge. Requires provider credentials.
4. **P4: Advanced optimization.** Embedding-based similarity, few-shot example selection, automatic prompt refinement.

### d. Code Scaffolds

#### [SCAFFOLD] Local Prompt Optimizer (Python)

```python
# python/src/agent_runtime_cockpit/optimizer/local.py
"""Local prompt optimizer — rule-based cleanup and token counting (P1b)."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class TokenCount(BaseModel):
    count: int
    encoding: str
    model: str = ""


class OptimizationResult(BaseModel):
    original: str
    optimized: str
    original_tokens: TokenCount
    optimized_tokens: TokenCount
    tokens_saved: int
    changes: list[str] = Field(default_factory=list)


KNOWN_MODEL_ENCODINGS: dict[str, str] = {
    "gpt-4": "cl100k_base",
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "text-embedding-3-small": "cl100k_base",
    "text-embedding-3-large": "cl100k_base",
}


def count_tokens(text: str, model: str = "gpt-4") -> TokenCount:
    """Count tokens in text using tiktoken. Falls back to character estimate if tiktoken unavailable."""
    encoding_name = KNOWN_MODEL_ENCODINGS.get(model, "cl100k_base")
    try:
        import tiktoken
        enc = tiktoken.get_encoding(encoding_name)
        tokens = enc.encode(text)
        return TokenCount(count=len(tokens), encoding=encoding_name, model=model)
    except ImportError:
        log.debug("tiktoken not installed — using character-based token estimate")
        estimated = len(text.split())
        return TokenCount(count=estimated, encoding="word-estimate", model=model)
    except Exception as e:
        log.warning("tiktoken encoding failed for %s: %s", encoding_name, e)
        estimated = len(text.split())
        return TokenCount(count=estimated, encoding="word-estimate", model=model)


RULES: list[tuple[str, str, str]] = [
    ("collapse_whitespace", r"\n{3,}", "\n\n"),
    ("strip_trailing_whitespace", r"[ \t]+$", ""),
    ("normalize_indent", r"^[ \t]{8,}", "    "),
    ("remove_trailing_newlines", r"\n+$", "\n"),
]


def optimize_prompt(prompt: str, model: str = "gpt-4") -> OptimizationResult:
    """Apply rule-based optimization to a prompt. No provider calls."""
    original_tokens = count_tokens(prompt, model)
    optimized = prompt
    changes: list[str] = []
    for rule_name, pattern, replacement in RULES:
        new_text = re.sub(pattern, replacement, optimized, flags=re.MULTILINE)
        if new_text != optimized:
            changes.append(rule_name)
            optimized = new_text
    optimized_tokens = count_tokens(optimized, model)
    return OptimizationResult(
        original=prompt,
        optimized=optimized,
        original_tokens=original_tokens,
        optimized_tokens=optimized_tokens,
        tokens_saved=original_tokens.count - optimized_tokens.count,
        changes=changes,
    )


@dataclass
class ModelPricing:
    model: str
    input_per_1k: float
    output_per_1k: float


KNOWN_PRICING: dict[str, ModelPricing] = {
    "gpt-4o": ModelPricing("gpt-4o", 0.0025, 0.01),
    "gpt-4o-mini": ModelPricing("gpt-4o-mini", 0.00015, 0.0006),
    "gpt-4": ModelPricing("gpt-4", 0.03, 0.06),
    "gpt-3.5-turbo": ModelPricing("gpt-3.5-turbo", 0.0005, 0.0015),
}


def estimate_cost(token_count: int, model: str) -> Optional[float]:
    """Estimate cost for input tokens given known pricing. Returns None if pricing unknown."""
    pricing = KNOWN_PRICING.get(model)
    if pricing is None:
        return None
    return (token_count / 1000.0) * pricing.input_per_1k
```

#### [SCAFFOLD] Prompt Optimizer Tests

```python
# python/tests/optimizer/test_local_optimizer.py
"""Tests for local prompt optimizer."""
import pytest
from agent_runtime_cockpit.optimizer.local import (
    count_tokens, optimize_prompt, estimate_cost, TokenCount,
)


def test_count_tokens_fallback():
    result = count_tokens("hello world this is a test", model="gpt-4")
    assert result.count > 0
    assert result.encoding in ("cl100k_base", "word-estimate")


def test_optimize_prompt_collapse_whitespace():
    prompt = "Hello\n\n\n\nWorld"
    result = optimize_prompt(prompt)
    assert "\n\n\n" not in result.optimized
    assert "collapse_whitespace" in result.changes


def test_optimize_prompt_strip_trailing():
    prompt = "Hello   \nWorld   \n"
    result = optimize_prompt(prompt)
    assert result.optimized.endswith("World\n")
    assert "strip_trailing_whitespace" in result.changes or "remove_trailing_newlines" in result.changes


def test_optimize_prompt_no_change():
    prompt = "Hello\n\nWorld\n"
    result = optimize_prompt(prompt)
    assert result.optimized == prompt
    assert result.tokens_saved == 0


def test_estimate_cost_known_model():
    cost = estimate_cost(1000, "gpt-4o")
    assert cost is not None
    assert cost == 0.0025


def test_estimate_cost_unknown_model():
    cost = estimate_cost(1000, "unknown-model-xyz")
    assert cost is None


def test_optimization_result_serialization():
    result = optimize_prompt("Test\n\n\n\nprompt")
    data = result.model_dump()
    assert "original" in data
    assert "optimized" in data
    assert "original_tokens" in data
    assert "tokens_saved" in data
```

### e. How to Verify This Still Works

```bash
# 1. Verify tiktoken version
cd python && uv pip show tiktoken 2>/dev/null | grep Version
# Expected: 0.12.x

# 2. Verify tiktoken encoding availability
python3 -c "
try:
    import tiktoken
    enc = tiktoken.get_encoding('cl100k_base')
    print(f'cl100k_base tokens for \"hello\": {len(enc.encode(\"hello\"))}')
except ImportError:
    print('tiktoken not installed — optimizer uses fallback')
"

# 3. Run optimizer tests
cd python && uv run pytest tests/optimizer/test_local_optimizer.py -v

# 4. Verify pricing data is current
# Check OpenAI pricing page: https://openai.com/api/pricing/
# Update KNOWN_PRICING dict if prices have changed
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| tiktoken not installed | Token counting falls back to word estimate (less accurate) | Add tiktoken to optional deps; document fallback behavior |
| Model pricing changes | Cost estimates become stale | Version pricing data; add `arc optimizer pricing update` command |
| tiktoken encoding drift for new models | Token counts wrong for new models | Update `KNOWN_MODEL_ENCODINGS` when new models release |
| Rule-based optimization changes prompt semantics | Optimized prompt behaves differently | Conservative rules only (whitespace, trailing); P3 adds semantic-aware rules |
| P3 provider optimization requires API calls | Cost and latency | Gated behind `--allow-paid-calls`; local mode (P1b) is free |

### g. Sources

- Context7: `/openai/tiktoken` — Token counting library
- PyPI: `tiktoken` 0.12.0 — Latest version
- OpenAI API pricing — https://openai.com/api/pricing/
- `docs/IMPLEMENTATION_PLAN.md` — P1b prompt optimizer scope

---

## 9. CLI Surface (P0–P5)

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P0: Repository Truth And Build Hygiene":

> "Make repository truth coherent and runnable."

From "P1a: Execution Core Infrastructure":

> "Split run lifecycle CLI — safe run commands land before live-dependent commands."

From "P1b: Adoption Foundation And Local Helpers":

> "Add `arc config init/show` — config loader CLI."

From "P2: Runtime + SwarmGraph Integrations":

> "Add `arc audit verify/export` — audit chain verification CLI."

> "Add `arc workspace trust` — trust management CLI."

From `docs/adr/001-config-model.md`:

> "YAML-based config with workspace/user/env/CLI override hierarchy."

### b. Current External State

#### Typer (ARC uses >=0.12)

- **Library:** `/tiangolo/typer`
- **API:** `typer.Typer()`, `@app.command()`, `typer.Argument()`, `typer.Option()`, `typer.Exit()`
- **License:** MIT
- **Maintenance:** Active. Latest versions in 0.12+ range.
- **ARC usage:** Current CLI in `python/src/agent_runtime_cockpit/cli.py` (709 lines). Uses `app = typer.Typer()` with sub-apps (`context_app`, `adapter_app`, `doctor_app`, `runs_app`, `eval_app`, `providers_app`).

#### rich (ARC uses >=13.7)

- **Library:** `/textualize/rich`
- **API:** `Console()`, `Table()`, `JSON()`, `print()`, `prompt()`, `confirm()`
- **License:** MIT
- **Maintenance:** Active. Latest versions in 13.x range.
- **ARC usage:** Terminal UX with `Console`, `Table`, `JSON`. Used for run output, adapter listing, eval results.

#### Current CLI commands (709 lines)

```
arc inspect       — inspect workspace, detect runtimes
arc runtimes      — list detected runtimes (+ --capabilities)
arc workflows     — list detected workflows
arc schemas       — list detected schemas
arc serve         — start HTTP daemon
arc run           — execute a workflow
arc runs          — list stored runs (subcommands: get, trace, prune)
arc context pack  — generate context pack
arc adapter test  — conformance tests
arc adapter list  — list registered adapters
arc eval run      — evaluate a run
arc eval list     — list golden traces
arc providers list/status/accounts/routing — provider management
arc doctor swarmgraph — SwarmGraph runtime check
```

#### Missing CLI commands (from plan)

```
arc config init/show     — config management (ADR-001)
arc audit verify/export  — audit chain verification (ADR-005)
arc workspace trust      — trust management (ADR-006)
arc runs cancel          — cancel active run (ADR-002)
arc runs live            — stream live run events (ADR-002)
arc backfill-index       — rebuild SQLite index (ADR-003)
arc optimizer optimize   — prompt optimization (P1b)
```

### c. Recommended Approach for ARC

1. **Keep existing CLI structure.** The current Typer-based CLI is well-organized with sub-apps. Extend with new sub-apps.
2. **Add `arc config` sub-app (P1b).** `arc config init` generates default YAML. `arc config show` displays resolved config with override hierarchy.
3. **Add `arc audit` sub-app (P2).** `arc audit verify` verifies HMAC chains. `arc audit export` exports audit records. `arc audit key init/show/delete` manages keys.
4. **Add `arc workspace` sub-app (P1a/P2).** `arc workspace trust` marks workspace as trusted. `arc workspace status` shows trust resolution.
5. **Add `arc runs cancel` and `arc runs live` (P1a).** Cancel active runs and stream live events via SSE.
6. **Add `arc backfill-index` (P1a).** Rebuild SQLite index from JSONL traces.
7. **Add `arc optimizer` sub-app (P1b).** `arc optimizer optimize` applies local prompt optimization. `arc optimizer count` counts tokens.

### d. Code Scaffolds

#### [SCAFFOLD] Config CLI Commands (Python)

```python
# python/src/agent_runtime_cockpit/cli_config.py
"""Config management CLI commands (ADR-001)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .protocol.config import ArcConfig, load_config, default_config

log = logging.getLogger(__name__)
console = Console()

config_app = typer.Typer(name="config", help="ARC configuration management")


@config_app.command("show")
def config_show(
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
    debug: bool = typer.Option(False, "--debug", envvar="ARC_DEBUG"),
) -> None:
    """Show resolved ARC configuration with override sources."""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(level=level, format="%(name)s %(levelname)s %(message)s")
    ws = Path(workspace) if workspace else Path.cwd()
    config = load_config(ws)
    table = Table(title="ARC Configuration")
    table.add_column("Key")
    table.add_column("Value")
    table.add_column("Source")
    for key, value, source in config.flatten_with_sources():
        table.add_row(key, str(value)[:80], source)
    console.print(table)


@config_app.command("init")
def config_init(
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
) -> None:
    """Generate default ARC configuration file in workspace."""
    ws = Path(workspace) if workspace else Path.cwd()
    config_path = ws / ".arc" / "config.yaml"
    if config_path.exists() and not force:
        console.print(f"[yellow]Config already exists: {config_path}[/yellow]")
        console.print("Use --force to overwrite.")
        raise typer.Exit(1)
    config = default_config()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config.to_yaml())
    console.print(f"[green]Config written to: {config_path}[/green]")
```

#### [SCAFFOLD] Audit CLI Commands (Python)

```python
# python/src/agent_runtime_cockpit/cli_audit.py
"""Audit chain verification and management CLI commands (ADR-005)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .audit.key_manager import AuditKeyManager
from .audit.hmac_chain import verify_hmac_chain

log = logging.getLogger(__name__)
console = Console()
err_console = Console(stderr=True)

audit_app = typer.Typer(name="audit", help="Audit chain verification and management")
audit_key_app = typer.Typer(name="key", help="Audit key management")
audit_app.add_typer(audit_key_app)


@audit_app.command("verify")
def audit_verify(
    run_id: str = typer.Argument(..., help="Run ID to verify"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
    chain_file: Optional[str] = typer.Option(None, "--chain", help="Path to audit chain file"),
) -> None:
    """Verify HMAC audit chain for a run."""
    ws = Path(workspace) if workspace else Path.cwd()
    key_mgr = AuditKeyManager()
    key, status = key_mgr.get_key()
    if key is None:
        err_console.print(f"[red]No audit key available: {status.warning}[/red]")
        raise typer.Exit(1)
    if status.degraded:
        console.print(f"[yellow]Warning: {status.warning}[/yellow]")
    chain_path = Path(chain_file) if chain_file else ws / ".arc" / "audit" / f"{run_id}.jsonl"
    if not chain_path.exists():
        err_console.print(f"[red]Audit chain not found: {chain_path}[/red]")
        raise typer.Exit(1)
    ok, reason = verify_hmac_chain(chain_path, key)
    if ok:
        console.print(f"[green]Audit chain verified: {reason}[/green]")
    else:
        err_console.print(f"[red]Audit chain verification failed: {reason}[/red]")
        raise typer.Exit(1)


@audit_app.command("export")
def audit_export(
    run_id: str = typer.Argument(..., help="Run ID to export"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Export audit records for a run as JSON."""
    ws = Path(workspace) if workspace else Path.cwd()
    chain_path = ws / ".arc" / "audit" / f"{run_id}.jsonl"
    if not chain_path.exists():
        err_console.print(f"[red]Audit chain not found: {chain_path}[/red]")
        raise typer.Exit(1)
    records = []
    with open(chain_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    export_data = {"run_id": run_id, "record_count": len(records), "records": records}
    if output:
        Path(output).write_text(json.dumps(export_data, indent=2))
        console.print(f"[green]Exported {len(records)} records to: {output}[/green]")
    else:
        console.print_json(json.dumps(export_data, indent=2))


@audit_key_app.command("init")
def audit_key_init() -> None:
    """Generate and store a new HMAC audit key in keychain."""
    key_mgr = AuditKeyManager()
    new_key = key_mgr.generate_key()
    success = key_mgr.set_key(new_key)
    if success:
        console.print("[green]Audit key generated and stored in keychain.[/green]")
        console.print(f"[dim]Key ID: {key_mgr.key_id}[/dim]")
    else:
        err_console.print("[yellow]Keychain storage failed. Key printed below — store it securely.[/yellow]")
        console.print(f"[bold]{new_key}[/bold]")


@audit_key_app.command("status")
def audit_key_status() -> None:
    """Show audit key availability and source."""
    key_mgr = AuditKeyManager()
    key, status = key_mgr.get_key()
    table = Table(title="Audit Key Status")
    table.add_column("Property")
    table.add_column("Value")
    table.add_row("Available", "yes" if status.available else "no")
    table.add_row("Source", status.source)
    table.add_row("Degraded", "yes" if status.degraded else "no")
    table.add_row("Key ID", status.key_id)
    if status.warning:
        table.add_row("Warning", status.warning)
    console.print(table)


@audit_key_app.command("delete")
def audit_key_delete(
    confirm: bool = typer.Option(False, "--yes", help="Skip confirmation"),
) -> None:
    """Delete the stored HMAC audit key from keychain."""
    if not confirm:
        if not typer.confirm("Delete audit key from keychain? This cannot be undone."):
            raise typer.Exit(0)
    key_mgr = AuditKeyManager()
    success = key_mgr.delete_key()
    if success:
        console.print("[green]Audit key deleted from keychain.[/green]")
    else:
        err_console.print("[red]Failed to delete audit key from keychain.[/red]")
        raise typer.Exit(1)
```

#### [SCAFFOLD] Workspace Trust CLI Commands (Python)

```python
# python/src/agent_runtime_cockpit/cli_workspace.py
"""Workspace trust management CLI commands (ADR-006)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .security.trust import resolve_trust, TrustLevel

log = logging.getLogger(__name__)
console = Console()
err_console = Console(stderr=True)

workspace_app = typer.Typer(name="workspace", help="Workspace management")


@workspace_app.command("trust")
def workspace_trust(
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
    revoke: bool = typer.Option(False, "--revoke", help="Revoke trust instead of granting"),
) -> None:
    """Mark a workspace as trusted (or revoke trust)."""
    ws = Path(workspace) if workspace else Path.cwd()
    trust_marker = ws / ".arc" / "trusted"
    if revoke:
        if trust_marker.exists():
            trust_marker.unlink()
            console.print(f"[green]Trust revoked for: {ws}[/green]")
        else:
            console.print(f"[dim]Workspace was not trusted: {ws}[/dim]")
        return
    trust_marker.parent.mkdir(parents=True, exist_ok=True)
    trust_marker.touch()
    console.print(f"[green]Workspace marked as trusted: {ws}[/green]")
    console.print("[dim]Trust DB: ~/.arc/trusted-workspaces.json[/dim]")


@workspace_app.command("status")
def workspace_status(
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
) -> None:
    """Show workspace trust resolution."""
    ws = Path(workspace) if workspace else Path.cwd()
    resolution = resolve_trust(ws)
    table = Table(title=f"Workspace Trust: {ws}")
    table.add_column("Property")
    table.add_column("Value")
    table.add_row("Trust Level", resolution.level.value)
    table.add_row("Reason", resolution.reason)
    if resolution.marker_path:
        table.add_row("Marker Path", resolution.marker_path)
    if resolution.warning:
        table.add_row("Warning", resolution.warning)
    console.print(table)
```

#### [SCAFFOLD] Optimizer CLI Commands (Python)

```python
# python/src/agent_runtime_cockpit/cli_optimizer.py
"""Prompt optimizer CLI commands (P1b)."""
from __future__ import annotations

import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .optimizer.local import optimize_prompt, count_tokens, estimate_cost

log = logging.getLogger(__name__)
console = Console()

optimizer_app = typer.Typer(name="optimizer", help="Prompt optimization and token counting")


@optimizer_app.command("optimize")
def optimizer_optimize(
    prompt: Optional[str] = typer.Argument(None, help="Prompt text (reads stdin if not provided)"),
    model: str = typer.Option("gpt-4", "--model", "-m", help="Target model for token counting"),
) -> None:
    """Apply local rule-based optimization to a prompt."""
    if prompt is None:
        prompt = sys.stdin.read()
    result = optimize_prompt(prompt, model)
    table = Table(title="Prompt Optimization Result")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Original tokens", str(result.original_tokens.count))
    table.add_row("Optimized tokens", str(result.optimized_tokens.count))
    table.add_row("Tokens saved", str(result.tokens_saved))
    table.add_row("Encoding", result.original_tokens.encoding)
    if result.changes:
        table.add_row("Changes applied", ", ".join(result.changes))
    else:
        table.add_row("Changes applied", "none")
    cost = estimate_cost(result.optimized_tokens.count, model)
    if cost is not None:
        table.add_row("Estimated cost (input)", f"${cost:.6f}")
    console.print(table)
    console.print()
    console.print("[bold]Optimized prompt:[/bold]")
    console.print(result.optimized)


@optimizer_app.command("count")
def optimizer_count(
    prompt: Optional[str] = typer.Argument(None, help="Prompt text (reads stdin if not provided)"),
    model: str = typer.Option("gpt-4", "--model", "-m", help="Target model for token counting"),
) -> None:
    """Count tokens in a prompt."""
    if prompt is None:
        prompt = sys.stdin.read()
    tc = count_tokens(prompt, model)
    cost = estimate_cost(tc.count, model)
    console.print(f"[bold]Tokens:[/bold] {tc.count} (encoding: {tc.encoding})")
    if cost is not None:
        console.print(f"[bold]Estimated cost (input):[/bold] ${cost:.6f}")
```

#### [SCAFFOLD] CLI Integration Tests

```python
# python/tests/cli/test_cli_commands.py
"""Tests for CLI command modules."""
import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from agent_runtime_cockpit.cli_config import config_app
from agent_runtime_cockpit.cli_audit import audit_app
from agent_runtime_cockpit.cli_workspace import workspace_app
from agent_runtime_cockpit.cli_optimizer import optimizer_app

runner = CliRunner()


def test_config_init(tmp_path: Path):
    result = runner.invoke(config_app, ["init", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    config_file = tmp_path / ".arc" / "config.yaml"
    assert config_file.exists()


def test_config_init_no_overwrite(tmp_path: Path):
    runner.invoke(config_app, ["init", "--workspace", str(tmp_path)])
    result = runner.invoke(config_app, ["init", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    assert "already exists" in result.stdout


def test_workspace_trust_grant(tmp_path: Path):
    result = runner.invoke(workspace_app, ["trust", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    trust_marker = tmp_path / ".arc" / "trusted"
    assert trust_marker.exists()


def test_workspace_trust_revoke(tmp_path: Path):
    trust_marker = tmp_path / ".arc" / "trusted"
    trust_marker.parent.mkdir(parents=True, exist_ok=True)
    trust_marker.touch()
    result = runner.invoke(workspace_app, ["trust", "--revoke", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert not trust_marker.exists()


def test_workspace_status(tmp_path: Path):
    result = runner.invoke(workspace_app, ["status", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "untrusted" in result.stdout.lower() or "trusted" in result.stdout.lower()


def test_optimizer_count():
    result = runner.invoke(optimizer_app, ["count", "hello world"])
    assert result.exit_code == 0
    assert "Tokens:" in result.stdout


def test_optimizer_optimize():
    result = runner.invoke(optimizer_app, ["optimize", "hello\n\n\n\nworld"])
    assert result.exit_code == 0
    assert "Optimized prompt:" in result.stdout


def test_audit_key_status():
    result = runner.invoke(audit_app, ["key", "status"])
    assert result.exit_code == 0
    assert "Audit Key Status" in result.stdout
```

### e. How to Verify This Still Works

```bash
# 1. Verify Typer version
cd python && uv pip show typer | grep Version
# Expected: 0.12+

# 2. Verify rich version
cd python && uv pip show rich | grep Version
# Expected: 13.7+

# 3. Run CLI integration tests
cd python && uv run pytest tests/cli/test_cli_commands.py -v

# 4. Test CLI entry point
cd python && uv run arc --help
# Should show all top-level commands including new sub-apps

# 5. Test new commands
cd python && uv run arc config show
cd python && uv run arc workspace status
cd python && uv run arc optimizer count "hello world"
cd python && uv run arc audit key status
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| CLI grows too large (>1000 lines per module) | Maintenance burden | Split into sub-app modules (done); each sub-app < 200 lines |
| Config YAML parsing complexity | Config loading bugs | Use Pydantic model with YAML loader; validate on load |
| Audit key management UX friction | Users skip setup | Degraded mode works without key; clear warnings |
| stdin reading for optimizer | Pipe vs argument confusion | Support both; document usage |
| CLI flag conflicts across sub-apps | Unexpected behavior | Namespace flags per sub-app; test flag combinations |

### g. Sources

- `python/src/agent_runtime_cockpit/cli.py` — Current CLI (709 lines)
- Context7: `/tiangolo/typer` — Typer CLI framework
- Context7: `/textualize/rich` — Rich terminal UX
- `docs/adr/001-config-model.md` — Config model specification
- `docs/adr/005-audit-key-management.md` — Audit key management
- `docs/adr/006-workspace-trust-isolation.md` — Workspace trust
- `docs/IMPLEMENTATION_PLAN.md` — CLI commands per phase

---

## 10. Storage: JSONL + SQLite Index (P1a)

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P1a: Execution Core Infrastructure":

> "Activate JSONL + SQLite index — runs are searchable/status-queryable without scanning all trace files."

From `docs/adr/003-storage-strategy.md`:

> "JSONL canonical + SQLite index. Dual-write with JSONL-first atomicity. SQLite is a rebuildable search index."

### b. Current External State

#### Python stdlib sqlite3

- **Library:** Python stdlib `sqlite3`
- **API:** `sqlite3.connect(path)`, `conn.execute()`, `conn.executescript()`, `conn.commit()`, `cursor.fetchall()`
- **WAL mode:** `PRAGMA journal_mode=WAL` enables Write-Ahead Logging for concurrent read access.
- **Maintenance:** stdlib, stable. SQLite version tracks Python build.
- **ARC relevance:** SQLite index for run metadata. JSONL is canonical; SQLite is rebuildable.

#### aiofiles (ARC uses >=23.2)

- **Library:** PyPI `aiofiles`
- **API:** `aiofiles.open(path, mode)`, async file I/O with `await f.write()`, `await f.read()`
- **License:** Apache 2.0
- **Maintenance:** Active. Latest: 24.1.0 (Apr 2024).
- **ARC relevance:** Async append-safe file writes for JSONL event streaming.

#### Current ARC storage (jsonl.py + sqlite.py)

- **jsonl.py** (85 lines): `JsonlTraceStore` with `save()`, `load()`, `list_runs()`, `prune()`, `append_event()`. One file per run_id.
- **sqlite.py** (66 lines): `SqliteStore` with `init_db()`, `insert_run()`, `update_run_status()`. Schema: `runs` and `audit_log` tables.
- **Gap:** SQLite not wired into JSONL store. No dual-write. No backfill. No WAL mode. No async I/O.

### c. Recommended Approach for ARC

1. **Wire SQLite into JSONL store.** Create `IndexedTraceStore` that wraps both. JSONL write first (canonical), then SQLite update (best-effort).
2. **Add WAL mode.** `PRAGMA journal_mode=WAL` for concurrent read access during writes.
3. **Add `backfill_index()` command.** Rebuild SQLite from existing JSONL traces. Idempotent.
4. **Add async JSONL writes.** Use `aiofiles` for append-safe event streaming during live runs.
5. **Add search queries.** SQLite index supports filtering by workflow_id, runtime, status, date range.
6. **Keep JSONL canonical.** If SQLite fails, JSONL is still valid. `backfill_index()` rebuilds.

### d. Code Scaffolds

#### [SCAFFOLD] Async JSONL Writer (Python)

```python
# python/src/agent_runtime_cockpit/storage/async_jsonl.py
"""Async JSONL writer for live event streaming."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiofiles

log = logging.getLogger(__name__)


class AsyncJsonlWriter:
    """Async append-only JSONL writer for live event streaming."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = None

    async def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = await aiofiles.open(self.path, "a", encoding="utf-8")

    async def append(self, event: dict[str, Any]) -> None:
        if self._file is None:
            raise RuntimeError("Writer not opened. Call open() first.")
        line = json.dumps(event, sort_keys=True) + "\n"
        await self._file.write(line)
        await self._file.flush()

    async def close(self) -> None:
        if self._file is not None:
            await self._file.flush()
            await self._file.close()
            self._file = None

    async def __aenter__(self) -> "AsyncJsonlWriter":
        await self.open()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
```

#### [SCAFFOLD] SQLite Index with WAL and Search (Python)

```python
# python/src/agent_runtime_cockpit/storage/sqlite_index.py
"""SQLite index with WAL mode and search queries (ADR-003)."""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

SCHEMA_V2 = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    runtime TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_workflow ON runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    details TEXT,
    verified INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_log(run_id);
"""


@dataclass
class RunSearchQuery:
    workflow_id: Optional[str] = None
    runtime: Optional[str] = None
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass
class RunSearchResult:
    id: str
    workflow_id: str
    runtime: str
    status: str
    started_at: str
    ended_at: Optional[str] = None


class SqliteIndex:
    """SQLite index with WAL mode and search support."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA_V2)
        log.info("SQLite index initialised (WAL mode): %s", self.db_path)

    def insert_run(
        self, run_id: str, workflow_id: str, runtime: str,
        status: str, started_at: str, metadata: Optional[str] = None,
    ) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?)",
                    (run_id, workflow_id, runtime, status, started_at, None, metadata),
                )
        except Exception as e:
            log.warning("SQLite insert_run failed for %s: %s", run_id, e)

    def update_run_status(self, run_id: str, status: str, ended_at: str) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE runs SET status=?, ended_at=? WHERE id=?",
                    (status, ended_at, run_id),
                )
        except Exception as e:
            log.warning("SQLite update_run failed for %s: %s", run_id, e)

    def search_runs(self, query: RunSearchQuery) -> list[RunSearchResult]:
        conditions: list[str] = []
        params: list[str] = []
        if query.workflow_id:
            conditions.append("workflow_id = ?")
            params.append(query.workflow_id)
        if query.runtime:
            conditions.append("runtime = ?")
            params.append(query.runtime)
        if query.status:
            conditions.append("status = ?")
            params.append(query.status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT id, workflow_id, runtime, status, started_at, ended_at FROM runs {where} ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.extend([str(query.limit), str(query.offset)])
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, params)
                return [
                    RunSearchResult(
                        id=row[0], workflow_id=row[1], runtime=row[2],
                        status=row[3], started_at=row[4], ended_at=row[5],
                    )
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            log.warning("SQLite search_runs failed: %s", e)
            return []

    def count_runs(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM runs")
                return cursor.fetchone()[0]
        except Exception as e:
            log.warning("SQLite count_runs failed: %s", e)
            return 0
```

#### [SCAFFOLD] Storage Tests

```python
# python/tests/storage/test_async_jsonl.py
"""Tests for async JSONL writer."""
import json
import pytest
from pathlib import Path
from agent_runtime_cockpit.storage.async_jsonl import AsyncJsonlWriter


@pytest.mark.asyncio
async def test_async_jsonl_write_and_read(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    events = [
        {"type": "RUN_STARTED", "seq": 0},
        {"type": "STEP_STARTED", "seq": 1},
        {"type": "RUN_COMPLETED", "seq": 2},
    ]
    async with AsyncJsonlWriter(path) as writer:
        for event in events:
            await writer.append(event)
    lines = path.read_text().splitlines()
    assert len(lines) == 3
    for i, line in enumerate(lines):
        parsed = json.loads(line)
        assert parsed["seq"] == i


@pytest.mark.asyncio
async def test_async_jsonl_append_after_close(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    writer = AsyncJsonlWriter(path)
    await writer.open()
    await writer.append({"type": "A"})
    await writer.close()
    with pytest.raises(RuntimeError, match="Writer not opened"):
        await writer.append({"type": "B"})


@pytest.mark.asyncio
async def test_async_jsonl_context_manager(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    async with AsyncJsonlWriter(path) as writer:
        await writer.append({"type": "test"})
    assert path.exists()
    content = path.read_text()
    assert '"test"' in content
```

```python
# python/tests/storage/test_sqlite_index.py
"""Tests for SQLite index with WAL and search."""
import pytest
from pathlib import Path
from agent_runtime_cockpit.storage.sqlite_index import (
    SqliteIndex, RunSearchQuery,
)


@pytest.fixture
def index(tmp_path: Path) -> SqliteIndex:
    idx = SqliteIndex(tmp_path / "test.db")
    idx.init()
    return idx


def test_init_creates_db(index: SqliteIndex):
    assert index.db_path.exists()
    assert index.count_runs() == 0


def test_insert_and_count(index: SqliteIndex):
    index.insert_run("r1", "wf1", "swarmgraph", "completed", "2026-05-14T00:00:00Z")
    index.insert_run("r2", "wf1", "swarmgraph", "failed", "2026-05-14T00:01:00Z")
    assert index.count_runs() == 2


def test_update_status(index: SqliteIndex):
    index.insert_run("r1", "wf1", "swarmgraph", "running", "2026-05-14T00:00:00Z")
    index.update_run_status("r1", "completed", "2026-05-14T00:01:00Z")
    results = index.search_runs(RunSearchQuery(status="completed"))
    assert len(results) == 1
    assert results[0].ended_at == "2026-05-14T00:01:00Z"


def test_search_by_workflow(index: SqliteIndex):
    index.insert_run("r1", "wf-alpha", "swarmgraph", "completed", "2026-05-14T00:00:00Z")
    index.insert_run("r2", "wf-beta", "langgraph", "completed", "2026-05-14T00:01:00Z")
    results = index.search_runs(RunSearchQuery(workflow_id="wf-alpha"))
    assert len(results) == 1
    assert results[0].id == "r1"


def test_search_by_status(index: SqliteIndex):
    index.insert_run("r1", "wf1", "sg", "completed", "2026-05-14T00:00:00Z")
    index.insert_run("r2", "wf1", "sg", "failed", "2026-05-14T00:01:00Z")
    index.insert_run("r3", "wf1", "sg", "running", "2026-05-14T00:02:00Z")
    results = index.search_runs(RunSearchQuery(status="failed"))
    assert len(results) == 1
    assert results[0].id == "r2"


def test_search_limit_and_offset(index: SqliteIndex):
    for i in range(10):
        index.insert_run(f"r{i}", "wf1", "sg", "completed", f"2026-05-14T00:0{i}:00Z")
    results = index.search_runs(RunSearchQuery(limit=3, offset=0))
    assert len(results) == 3
    results_page2 = index.search_runs(RunSearchQuery(limit=3, offset=3))
    assert len(results_page2) == 3


def test_wal_mode_enabled(index: SqliteIndex):
    with __import__("sqlite3").connect(index.db_path) as conn:
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode == "wal"
```

### e. How to Verify This Still Works

```bash
# 1. Verify aiofiles version
cd python && uv pip show aiofiles | grep Version
# Expected: 23.2+

# 2. Verify SQLite WAL mode
python3 -c "
import sqlite3, tempfile, os
db = os.path.join(tempfile.mkdtemp(), 'test.db')
conn = sqlite3.connect(db)
conn.execute('PRAGMA journal_mode=WAL')
mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
print(f'WAL mode: {mode}')
conn.close()
"

# 3. Run async JSONL tests
cd python && uv run pytest tests/storage/test_async_jsonl.py -v

# 4. Run SQLite index tests
cd python && uv run pytest tests/storage/test_sqlite_index.py -v

# 5. Verify SQLite version
python3 -c "import sqlite3; print(f'SQLite: {sqlite3.sqlite_version}')"
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLite lock contention under concurrent writes | Index updates stall | Single-writer daemon model; WAL mode for concurrent reads |
| JSONL/SQLite dual-write inconsistency | Index out of sync | JSONL is canonical; `backfill_index()` rebuilds SQLite |
| aiofiles compatibility with event loop | Async writes fail | Test with asyncio event loop; fallback to sync if needed |
| Large trace directories (>10K files) | `list_runs()` slow | SQLite index for listing; JSONL glob only for backfill |
| SQLite database corruption | Index unusable | Delete and rebuild via `backfill_index()`; JSONL is canonical |

### g. Sources

- `docs/adr/003-storage-strategy.md` — JSONL + SQLite dual-store strategy
- `python/src/agent_runtime_cockpit/storage/jsonl.py` — Current JSONL store (85 lines)
- `python/src/agent_runtime_cockpit/storage/sqlite.py` — Current SQLite store (66 lines)
- PyPI: `aiofiles` 24.1.0 — Async file I/O
- Python stdlib: `sqlite3` — SQLite database interface
- `docs/IMPLEMENTATION_PLAN.md` — P1a storage scope

---

## 11. Live Event Broker and SSE (P1a)

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P1a: Execution Core Infrastructure":

> "Add live run supervisor and event broker — runs can be backgrounded, cancelled, streamed, and recovered."

From `docs/adr/002-run-lifecycle-state-machine.md`:

> "Supervisor owns run lifecycle. Event broker delivers live events to subscribers. SSE for HTTP streaming."

### b. Current External State

#### aiohttp-sse (2.2.0, Feb 2024)

- **Library:** PyPI `aiohttp-sse`
- **API:** `sse_response(request)` async context manager, `SSEResponse.send(data, event=, id=)` for event delivery
- **License:** Apache 2.0
- **Maintenance:** Last release Feb 2024. Works with aiohttp 3.x. May not track aiohttp 4.x if released.
- **ARC relevance:** SSE delivery for live event streaming. Used in daemon HTTP handlers.

#### HTML SSE Specification

- **Protocol:** `text/event-stream` content type
- **Fields:** `event:` (event type), `data:` (payload), `id:` (event ID for reconnection)
- **Reconnection:** `Last-Event-ID` header sent by client on reconnect. Server resumes from that ID.
- **Heartbeat:** Periodic empty comments (`: heartbeat\n`) keep connection alive.
- **ARC relevance:** Browser SSE client connects to daemon `/api/runs/{run_id}/events?mode=live`. Events streamed as `text/event-stream`.

#### aiohttp (ARC uses >=3.9)

- **Library:** `/aio-libs/aiohttp`
- **API:** `web.Application`, `web.RouteTableDef`, `web.Response`, `web.StreamResponse`
- **Manual SSE:** `StreamResponse(content_type='text/event-stream')` with manual `write()` calls.
- **ARC relevance:** Daemon uses aiohttp for REST endpoints. SSE via `aiohttp-sse` or manual `StreamResponse`.

#### asyncio.Queue (stdlib)

- **Library:** Python stdlib `asyncio`
- **API:** `asyncio.Queue()`, `queue.put_nowait(item)`, `await queue.get()`
- **ARC relevance:** In-memory pub/sub for event broker. Supervisor publishes to queues; SSE handler consumes from queues.

#### Current ARC daemon (`web/server.py`, `web/routes.py`)

- **Current state:** HTTP daemon with REST endpoints. SSE currently replays stored traces only (no live event delivery).
- **Gap:** No live event broker. No `JobSupervisor`. No SSE heartbeat. No reconnection support.

### c. Recommended Approach for ARC

1. **EventBroker with asyncio.Queue pub/sub.** Supervisor publishes events to queues. SSE handler subscribes and streams.
2. **SSE with aiohttp-sse.** Use `sse_response()` for SSE delivery. Fallback to manual `StreamResponse` if package drifts.
3. **Heartbeat via periodic comments.** Send `: heartbeat\n` every 15 seconds to keep connection alive.
4. **Reconnection via Last-Event-ID.** Track event IDs. On reconnect, replay missed events from stored trace.
5. **Live + replay modes.** `?mode=live` for active runs. `?mode=replay` for stored traces. Same SSE handler.
6. **Graceful shutdown.** On daemon shutdown, close all SSE connections and send `STREAM_END` event.

### d. Code Scaffolds

#### [SCAFFOLD] EventBroker with Heartbeat and Reconnection (Python)

```python
# python/src/agent_runtime_cockpit/orchestration/event_broker.py
"""EventBroker — scaffold for SSE streaming with heartbeat and reconnection support."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Optional

from aiohttp import web
from aiohttp_sse import sse_response

from ..storage.jsonl import JsonlTraceStore

log = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 15.0


class EventBroker:
    """In-memory event broker with SSE delivery.

    Supports live streaming (from active runs) and replay (from stored traces).
    Handles heartbeat and reconnection via Last-Event-ID.
    """

    def __init__(self, store: JsonlTraceStore) -> None:
        self.store = store
        self._subscribers: dict[str, list[asyncio.Queue[Optional[dict[str, Any]]]]] = {}
        self._event_ids: dict[str, int] = {}

    def publish(self, run_id: str, event: dict[str, Any]) -> int:
        """Publish an event to all subscribers of a run. Returns event ID."""
        event_id = self._event_ids.get(run_id, 0) + 1
        self._event_ids[run_id] = event_id
        event_with_id = {**event, "event_id": event_id}
        for queue in self._subscribers.get(run_id, []):
            queue.put_nowait(event_with_id)
        return event_id

    def subscribe(self, run_id: str) -> asyncio.Queue[Optional[dict[str, Any]]]:
        """Subscribe to events for a run. Queue receives None when run ends."""
        queue: asyncio.Queue[Optional[dict[str, Any]]] = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        subs = self._subscribers.get(run_id, [])
        if queue in subs:
            subs.remove(queue)

    def end_run(self, run_id: str) -> None:
        """Signal end of run to all subscribers."""
        for queue in self._subscribers.pop(run_id, []):
            queue.put_nowait(None)

    async def stream_live(
        self, run_id: str, last_event_id: int = 0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield live events for an active run, optionally replaying missed events."""
        if last_event_id > 0:
            async for event in self._replay_from(run_id, last_event_id):
                yield event
        queue = self.subscribe(run_id)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            self.unsubscribe(run_id, queue)

    async def _replay_from(
        self, run_id: str, from_event_id: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay missed events from stored trace."""
        trace_path = self.store.trace_path(run_id)
        if not trace_path.exists():
            return
        with open(trace_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    eid = event.get("event_id", 0)
                    if eid > from_event_id:
                        yield event
                except json.JSONDecodeError:
                    continue

    async def sse_handler(self, request: web.Request) -> web.StreamResponse:
        """HTTP handler for SSE event streaming with heartbeat."""
        run_id = request.match_info["run_id"]
        mode = request.query.get("mode", "replay")
        last_event_id = int(request.headers.get("Last-Event-ID", "0"))
        async with sse_response(request) as resp:
            try:
                heartbeat_task = asyncio.create_task(
                    self._send_heartbeats(resp), name=f"heartbeat-{run_id}",
                )
                try:
                    if mode == "live":
                        stream = self.stream_live(run_id, last_event_id)
                    else:
                        stream = self._replay_stored(run_id)
                    async for event in stream:
                        event_id = event.get("event_id")
                        event_type = event.get("type", "message")
                        payload = json.dumps(event)
                        await resp.send(
                            payload, event=event_type,
                            id=str(event_id) if event_id else None,
                        )
                    await resp.send(json.dumps({"type": "STREAM_END"}), event="stream_end")
                finally:
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
            except asyncio.CancelledError:
                log.info("SSE stream cancelled for run %s", run_id)
                raise
            except Exception as e:
                log.error("SSE stream error for run %s: %s", run_id, e)
                await resp.send(
                    json.dumps({"type": "STREAM_ERROR", "error": str(e)}),
                    event="stream_error",
                )
        return resp

    async def _replay_stored(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        """Replay all events from stored trace."""
        trace_path = self.store.trace_path(run_id)
        if not trace_path.exists():
            return
        with open(trace_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    @staticmethod
    async def _send_heartbeats(resp) -> None:
        """Send periodic heartbeat comments to keep SSE connection alive."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await resp.send("", event="heartbeat")
        except asyncio.CancelledError:
            pass
```

#### [SCAFFOLD] EventBroker Tests

```python
# python/tests/orchestration/test_event_broker.py
"""Tests for EventBroker with SSE delivery."""
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from agent_runtime_cockpit.orchestration.event_broker import EventBroker
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore


@pytest.fixture
def broker(tmp_path: Path) -> EventBroker:
    store = JsonlTraceStore(base_dir=tmp_path / "traces")
    return EventBroker(store=store)


def test_publish_to_subscribers(broker: EventBroker):
    queue = broker.subscribe("run-001")
    event_id = broker.publish("run-001", {"type": "RUN_STARTED", "data": {}})
    assert event_id == 1
    event = queue.get_nowait()
    assert event is not None
    assert event["type"] == "RUN_STARTED"
    assert event["event_id"] == 1


def test_publish_increments_event_id(broker: EventBroker):
    broker.subscribe("run-001")
    id1 = broker.publish("run-001", {"type": "A"})
    id2 = broker.publish("run-001", {"type": "B"})
    id3 = broker.publish("run-001", {"type": "C"})
    assert id1 == 1
    assert id2 == 2
    assert id3 == 3


def test_end_run_signals_subscribers(broker: EventBroker):
    queue = broker.subscribe("run-001")
    broker.publish("run-001", {"type": "RUN_STARTED"})
    broker.end_run("run-001")
    event1 = queue.get_nowait()
    assert event1 is not None
    end_signal = queue.get_nowait()
    assert end_signal is None


def test_unsubscribe_removes_queue(broker: EventBroker):
    queue = broker.subscribe("run-001")
    broker.unsubscribe("run-001", queue)
    broker.publish("run-001", {"type": "A"})
    assert queue.empty()


@pytest.mark.asyncio
async def test_stream_live_receives_events(broker: EventBroker):
    events_received = []
    async def publisher():
        await asyncio.sleep(0.01)
        broker.publish("run-002", {"type": "RUN_STARTED"})
        broker.publish("run-002", {"type": "STEP_STARTED"})
        broker.end_run("run-002")
    asyncio.create_task(publisher())
    async for event in broker.stream_live("run-002"):
        events_received.append(event)
    assert len(events_received) == 2
    assert events_received[0]["type"] == "RUN_STARTED"


@pytest.mark.asyncio
async def test_replay_stored_from_jsonl(tmp_path: Path):
    store = JsonlTraceStore(base_dir=tmp_path / "traces")
    trace_path = store.trace_path("replay-run")
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stored_events = [
        {"type": "RUN_STARTED", "event_id": 1},
        {"type": "STEP_STARTED", "event_id": 2},
        {"type": "RUN_COMPLETED", "event_id": 3},
    ]
    with open(trace_path, "w") as f:
        for event in stored_events:
            f.write(json.dumps(event) + "\n")
    broker = EventBroker(store=store)
    replayed = []
    async for event in broker._replay_stored("replay-run"):
        replayed.append(event)
    assert len(replayed) == 3
    assert replayed[0]["type"] == "RUN_STARTED"
    assert replayed[2]["type"] == "RUN_COMPLETED"


@pytest.mark.asyncio
async def test_replay_from_event_id(tmp_path: Path):
    store = JsonlTraceStore(base_dir=tmp_path / "traces")
    trace_path = store.trace_path("reconnect-run")
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stored_events = [
        {"type": "A", "event_id": 1},
        {"type": "B", "event_id": 2},
        {"type": "C", "event_id": 3},
        {"type": "D", "event_id": 4},
    ]
    with open(trace_path, "w") as f:
        for event in stored_events:
            f.write(json.dumps(event) + "\n")
    broker = EventBroker(store=store)
    replayed = []
    async for event in broker._replay_from("reconnect-run", from_event_id=2):
        replayed.append(event)
    assert len(replayed) == 2
    assert replayed[0]["type"] == "C"
    assert replayed[1]["type"] == "D"
```

### e. How to Verify This Still Works

```bash
# 1. Verify aiohttp-sse version
cd python && uv pip show aiohttp-sse 2>/dev/null | grep Version
# Expected: 2.2.0

# 2. Verify aiohttp version
cd python && uv pip show aiohttp | grep Version
# Expected: 3.9+

# 3. Run event broker tests
cd python && uv run pytest tests/orchestration/test_event_broker.py -v

# 4. Manual SSE test (after daemon start)
# Terminal 1: uv run arc serve --port 7777
# Terminal 2: curl -N -H "Accept: text/event-stream" http://127.0.0.1:7777/api/runs/test-run/events?mode=replay
# Expected: SSE event stream output

# 5. Verify heartbeat (long-running curl)
# curl -N http://127.0.0.1:7777/api/runs/test-run/events?mode=live
# Wait 15+ seconds — should see heartbeat comments

# 6. Check aiohttp-sse maintenance status
pip index versions aiohttp-sse 2>/dev/null | head -3
# If no new versions since Feb 2024, consider manual SSE fallback
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| aiohttp-sse unmaintained (last release Feb 2024) | Breaks on aiohttp 4.x | Manual `StreamResponse` SSE is ~20 lines; easy fallback |
| SSE connection drops silently | Client misses events | Heartbeat every 15s; `Last-Event-ID` reconnection |
| asyncio.Queue memory growth under heavy event rate | Daemon OOM | Bound queue size; drop oldest events with warning |
| Multiple SSE clients for same run | Fan-out complexity | Each subscriber gets own queue; broker manages fan-out |
| Reconnection replay duplicates events | Client sees duplicates | Event IDs enable deduplication on client side |
| SSE not supported behind some proxies | Streaming fails | Document proxy requirements; fallback to polling |

### g. Sources

- PyPI: `aiohttp-sse` 2.2.0 — SSE context manager for aiohttp
- Context7: `/aio-libs/aiohttp` — aiohttp web framework
- HTML SSE spec — `text/event-stream`, `event:`, `data:`, `id:` fields, `Last-Event-ID`
- `python/src/agent_runtime_cockpit/web/server.py` — Current daemon
- `python/src/agent_runtime_cockpit/web/routes.py` — Current routes
- `docs/adr/002-run-lifecycle-state-machine.md` — Supervisor and event broker contract
- `docs/IMPLEMENTATION_PLAN.md` — P1a live event scope

---

**End of Part I (Sections 0–11).**

Part II covers Sections 12–17: Provider Gateway, Eval & Observability, Security, Packaging, Cross-Cutting Risks, and Open Questions.

---

## 12. Provider Gateway, Quotas, Cost Controls

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P2: Runtime + SwarmGraph Integrations":

> "Provider routing and unification — ARC providers as metadata/policy layer; gateway owns execution."

From `docs/adr/007-provider-routing-unification.md`:

> "ARC's provider registry describes what providers exist, what models they serve, and what policy applies (quotas, cost ceilings, routing preferences). The gateway is the execution owner: it selects a provider, enforces quotas, tracks costs, and dispatches the call. ARC providers are metadata; the gateway is the runtime."

From the plan's P3 scope:

> "Provider-aware prompt optimization — template-based optimization with token cost estimation."

### b. Current External State

#### ARC Existing Provider Management

- **Location:** `python/src/agent_runtime_cockpit/providers.py`
- **Current state:** Provider registry with account management, routing table, and status checks. CLI commands: `arc providers list/status/accounts/routing`.
- **Gap:** No quota enforcement, no cost tracking, no gateway abstraction. Providers are metadata only — no execution routing layer.

#### Provider APIs (as of 2026-05-14)

| Provider | Python SDK | Auth | Rate-limit headers | Cost model |
|----------|-----------|------|-------------------|------------|
| OpenAI | `openai>=1.0` | `OPENAI_API_KEY` env or `openai.api_key` | `x-ratelimit-limit-requests`, `x-ratelimit-remaining-requests`, `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-tokens` | Per-token (input + output), per-model pricing |
| Anthropic | `anthropic>=0.20` | `ANTHROPIC_API_KEY` env | `x-ratelimit-requests-limit`, `x-ratelimit-requests-remaining`, `x-ratelimit-tokens-limit`, `x-ratelimit-tokens-remaining` | Per-token (input + output + cache), per-model pricing |
| Google (Gemini) | `google-genai` or `vertexai` | `GOOGLE_API_KEY` env or ADC | `x-ratelimit-*` varies | Per-token or per-request, free tier available |
| Mistral | `mistralai>=1.0` | `MISTRAL_API_KEY` env | `x-ratelimit-limit`, `x-ratelimit-remaining` | Per-token, per-model pricing |
| Groq | `groq>=0.4` | `GROQ_API_KEY` env | `x-ratelimit-request-remaining`, `x-ratelimit-token-remaining` | Per-token, some free tier |
| Together AI | `together>=1.0` | `TOGETHER_API_KEY` env | Varies | Per-token, open-source models |
| OpenRouter | HTTP only (no official SDK) | `OPENROUTER_API_KEY` env | Provider-passthrough | Aggregator pricing, per-model |

#### Rate-Limit Header Patterns

All major providers expose rate-limit information via HTTP response headers. Common patterns:

- **Request limits:** `x-ratelimit-limit-requests` / `x-ratelimit-remaining-requests`
- **Token limits:** `x-ratelimit-limit-tokens` / `x-ratelimit-remaining-tokens`
- **Reset timing:** `x-ratelimit-reset-requests` (seconds until reset)
- **OpenAI organization:** `openai-organization` header identifies the billing org

#### Cost Calculation

All providers bill per-token (input and output separately). Pricing is published per 1K or 1M tokens:

- OpenAI GPT-4o: $2.50/1M input, $10.00/1M output
- OpenAI GPT-4o-mini: $0.15/1M input, $0.60/1M output
- Anthropic Claude 3.5 Sonnet: $3.00/1M input, $15.00/1M output
- Pricing changes frequently; must be versioned and updatable.

### c. Recommended Approach for ARC

1. **Define `ProviderGateway` abstraction.** A single interface that owns: provider selection, quota enforcement, cost tracking, and dispatch. Replace direct SDK calls in adapters with gateway calls.
2. **Keep ARC providers as metadata.** The existing `providers.py` registry becomes the metadata source. The gateway reads it and makes runtime decisions.
3. **Quota model: per-provider, per-workspace, per-period.** Quotas are defined in config (ADR-001): max requests/minute, max tokens/day, max cost/month. Gateway enforces and rejects over-quota calls.
4. **Cost tracking: accumulate per-run, per-workspace.** Gateway tracks token usage and computes cost using a versioned pricing table. Costs are attached to run metadata.
5. **Rate-limit awareness.** Gateway reads rate-limit headers from responses and implements backoff. If a provider is rate-limited, the gateway can fall back to an alternate provider (if configured).
6. **Pricing table: versioned, updatable.** Store known pricing in a JSON file bundled with ARC. Add `arc providers pricing update` to fetch latest pricing. Never hardcode in Python source.
7. **Start with OpenAI + Anthropic.** These are the most common providers. Add others incrementally.

### d. Code Scaffolds

#### [SCAFFOLD] Provider Gateway Interface and Quota Manager (Python)

```python
# python/src/agent_runtime_cockpit/gateway/base.py
"""Provider gateway — unified provider routing, quota enforcement, and cost tracking (ADR-007)."""
from __future__ import annotations

import abc
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class ProviderId(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    GROQ = "groq"
    TOGETHER = "together"
    OPENROUTER = "openrouter"


class QuotaPeriod(str, Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


class QuotaSpec(BaseModel):
    """Quota specification for a provider."""
    max_requests_per_period: int = 60
    max_tokens_per_period: int = 1_000_000
    max_cost_per_month: float = 100.0
    period: QuotaPeriod = QuotaPeriod.MINUTE


class QuotaStatus(BaseModel):
    """Current quota status."""
    provider: str
    requests_used: int = 0
    requests_limit: int = 0
    tokens_used: int = 0
    tokens_limit: int = 0
    cost_used: float = 0.0
    cost_limit: float = 0.0
    within_quota: bool = True
    reason: str = ""


@dataclass
class ProviderResponse:
    """Normalized response from any provider."""
    provider: str
    model: str
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    rate_limit_remaining_requests: Optional[int] = None
    rate_limit_remaining_tokens: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitState:
    """Tracks rate-limit state for a provider."""
    requests_remaining: Optional[int] = None
    tokens_remaining: Optional[int] = None
    reset_at: Optional[float] = None

    def is_rate_limited(self) -> bool:
        if self.requests_remaining is not None and self.requests_remaining <= 0:
            return True
        if self.tokens_remaining is not None and self.tokens_remaining <= 0:
            return True
        if self.reset_at and time.time() < self.reset_at:
            return self.requests_remaining is not None and self.requests_remaining <= 0
        return False


class QuotaManager:
    """Tracks usage and enforces quotas per provider per workspace."""

    def __init__(self) -> None:
        self._usage: dict[str, dict[str, Any]] = {}
        self._quotas: dict[str, QuotaSpec] = {}
        self._rate_limits: dict[str, RateLimitState] = {}

    def set_quota(self, provider: str, spec: QuotaSpec) -> None:
        self._quotas[provider] = spec
        if provider not in self._usage:
            self._usage[provider] = {
                "requests": 0, "tokens": 0, "cost": 0.0,
                "period_start": time.time(),
            }

    def record_usage(self, provider: str, requests: int, tokens: int, cost: float) -> None:
        if provider not in self._usage:
            self._usage[provider] = {
                "requests": 0, "tokens": 0, "cost": 0.0,
                "period_start": time.time(),
            }
        self._usage[provider]["requests"] += requests
        self._usage[provider]["tokens"] += tokens
        self._usage[provider]["cost"] += cost

    def update_rate_limit(self, provider: str, state: RateLimitState) -> None:
        self._rate_limits[provider] = state

    def check_quota(self, provider: str) -> QuotaStatus:
        spec = self._quotas.get(provider)
        usage = self._usage.get(provider, {"requests": 0, "tokens": 0, "cost": 0.0})
        rate = self._rate_limits.get(provider)
        if spec is None:
            return QuotaStatus(provider=provider, within_quota=True)
        within = True
        reason = ""
        if rate and rate.is_rate_limited():
            within = False
            reason = "Provider rate-limited"
        if usage["requests"] >= spec.max_requests_per_period:
            within = False
            reason = f"Request quota exceeded: {usage['requests']}/{spec.max_requests_per_period}"
        if usage["tokens"] >= spec.max_tokens_per_period:
            within = False
            reason = f"Token quota exceeded: {usage['tokens']}/{spec.max_tokens_per_period}"
        if usage["cost"] >= spec.max_cost_per_month:
            within = False
            reason = f"Cost quota exceeded: ${usage['cost']:.4f}/${spec.max_cost_per_month:.4f}"
        return QuotaStatus(
            provider=provider,
            requests_used=usage["requests"],
            requests_limit=spec.max_requests_per_period,
            tokens_used=usage["tokens"],
            tokens_limit=spec.max_tokens_per_period,
            cost_used=usage["cost"],
            cost_limit=spec.max_cost_per_month,
            within_quota=within,
            reason=reason,
        )

    def reset_period(self, provider: str) -> None:
        if provider in self._usage:
            self._usage[provider] = {
                "requests": 0, "tokens": 0, "cost": 0.0,
                "period_start": time.time(),
            }


class ProviderGateway(abc.ABC):
    """Unified gateway interface for provider dispatch."""

    @property
    @abc.abstractmethod
    def quota_manager(self) -> QuotaManager:
        ...

    @abc.abstractmethod
    async def dispatch(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        run_id: str = "",
    ) -> ProviderResponse:
        ...

    @abc.abstractmethod
    def get_cost_estimate(self, provider: str, model: str, input_tokens: int) -> Optional[float]:
        ...

    @abc.abstractmethod
    def list_available_providers(self) -> list[str]:
        ...
```

#### [SCAFFOLD] Cost Calculator with Versioned Pricing (Python)

```python
# python/src/agent_runtime_cockpit/gateway/pricing.py
"""Versioned pricing table for provider cost estimation."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

DEFAULT_PRICING_VERSION = "2026-05-14"


@dataclass(frozen=True)
class ModelPricing:
    """Pricing for a specific model. All costs per 1M tokens in USD."""
    provider: str
    model: str
    input_per_1m: float
    output_per_1m: float
    cache_read_per_1m: float = 0.0
    cache_write_per_1m: float = 0.0
    effective_date: str = DEFAULT_PRICING_VERSION


BUILTIN_PRICING: dict[str, ModelPricing] = {
    "openai/gpt-4o": ModelPricing("openai", "gpt-4o", 2.50, 10.00),
    "openai/gpt-4o-mini": ModelPricing("openai", "gpt-4o-mini", 0.15, 0.60),
    "openai/gpt-4-turbo": ModelPricing("openai", "gpt-4-turbo", 10.00, 30.00),
    "openai/gpt-3.5-turbo": ModelPricing("openai", "gpt-3.5-turbo", 0.50, 1.50),
    "openai/o1": ModelPricing("openai", "o1", 15.00, 60.00),
    "openai/o3-mini": ModelPricing("openai", "o3-mini", 1.10, 4.40),
    "anthropic/claude-3-5-sonnet-20241022": ModelPricing(
        "anthropic", "claude-3-5-sonnet-20241022", 3.00, 15.00, 0.30, 3.75,
    ),
    "anthropic/claude-3-opus-20240229": ModelPricing(
        "anthropic", "claude-3-opus-20240229", 15.00, 75.00, 1.50, 18.75,
    ),
    "anthropic/claude-3-haiku-20240307": ModelPricing(
        "anthropic", "claude-3-haiku-20240307", 0.25, 1.25, 0.03, 0.30,
    ),
    "google/gemini-1.5-pro": ModelPricing("google", "gemini-1.5-pro", 1.25, 5.00),
    "google/gemini-1.5-flash": ModelPricing("google", "gemini-1.5-flash", 0.075, 0.30),
    "mistral/mistral-large-latest": ModelPricing("mistral", "mistral-large-latest", 2.00, 6.00),
    "mistral/mistral-small-latest": ModelPricing("mistral", "mistral-small-latest", 0.20, 0.60),
    "groq/llama-3.3-70b-versatile": ModelPricing("groq", "llama-3.3-70b-versatile", 0.59, 0.79),
    "groq/mixtral-8x7b-32768": ModelPricing("groq", "mixtral-8x7b-32768", 0.24, 0.24),
}


class CostCalculator:
    """Computes cost from token usage using versioned pricing.

    Production note: replace BUILTIN_PRICING with versioned JSON under
    gateway/pricing_data/. Refuse exact cost if effective_date is older than 90 days;
    return unknown plus warning instead of silently stale dollars.
    """

    def __init__(self, pricing: Optional[dict[str, ModelPricing]] = None) -> None:
        self.pricing = pricing or BUILTIN_PRICING.copy()

    def compute_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> float:
        key = f"{provider}/{model}"
        p = self.pricing.get(key)
        if p is None:
            log.debug("No pricing for %s — cost unknown", key)
            return 0.0
        input_cost = (input_tokens / 1_000_000) * p.input_per_1m
        output_cost = (output_tokens / 1_000_000) * p.output_per_1m
        cache_read_cost = (cache_read_tokens / 1_000_000) * p.cache_read_per_1m
        cache_write_cost = (cache_write_tokens / 1_000_000) * p.cache_write_per_1m
        return input_cost + output_cost + cache_read_cost + cache_write_cost

    def estimate_input_cost(self, provider: str, model: str, input_tokens: int) -> Optional[float]:
        key = f"{provider}/{model}"
        p = self.pricing.get(key)
        if p is None:
            return None
        return (input_tokens / 1_000_000) * p.input_per_1m

    def load_pricing_file(self, path: Path) -> int:
        """Load pricing overrides from a JSON file. Returns count of entries loaded."""
        if not path.exists():
            return 0
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for entry in data.get("pricing", []):
            key = f"{entry['provider']}/{entry['model']}"
            self.pricing[key] = ModelPricing(**entry)
            count += 1
        log.info("Loaded %d pricing entries from %s", count, path)
        return count

    def export_pricing(self, path: Path) -> None:
        """Export current pricing table to JSON."""
        entries = []
        for p in self.pricing.values():
            entries.append({
                "provider": p.provider,
                "model": p.model,
                "input_per_1m": p.input_per_1m,
                "output_per_1m": p.output_per_1m,
                "cache_read_per_1m": p.cache_read_per_1m,
                "cache_write_per_1m": p.cache_write_per_1m,
                "effective_date": p.effective_date,
            })
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": DEFAULT_PRICING_VERSION, "pricing": entries}, indent=2))
```

#### [SCAFFOLD] OpenAI Provider Dispatch (Python)

```python
# python/src/agent_runtime_cockpit/gateway/providers/openai_dispatch.py
"""OpenAI provider dispatch — gateway integration for OpenAI API."""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from ..base import ProviderResponse, RateLimitState

log = logging.getLogger(__name__)


def _parse_rate_limit_headers(headers: dict[str, str]) -> RateLimitState:
    """Extract rate-limit state from OpenAI response headers."""
    state = RateLimitState()
    try:
        remaining_req = headers.get("x-ratelimit-remaining-requests")
        if remaining_req is not None:
            state.requests_remaining = int(remaining_req)
        remaining_tok = headers.get("x-ratelimit-remaining-tokens")
        if remaining_tok is not None:
            state.tokens_remaining = int(remaining_tok)
        reset_str = headers.get("x-ratelimit-reset-requests")
        if reset_str:
            state.reset_at = time.time() + float(reset_str)
    except (ValueError, TypeError) as e:
        log.debug("Failed to parse rate-limit headers: %s", e)
    return state


async def dispatch_openai(
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 1024,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> ProviderResponse:
    """Dispatch a chat completion to OpenAI. Returns normalized response."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise RuntimeError("OpenAI SDK not installed. pip install openai>=1.0")
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = AsyncOpenAI(api_key=key)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    content = response.choices[0].message.content or ""
    input_tokens = response.usage.prompt_tokens if response.usage else 0
    output_tokens = response.usage.completion_tokens if response.usage else 0
    return ProviderResponse(
        provider="openai",
        model=model,
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )
```

#### [SCAFFOLD] Gateway and Pricing Tests

```python
# python/tests/gateway/test_quota_manager.py
"""Tests for QuotaManager."""
import pytest
from agent_runtime_cockpit.gateway.base import (
    QuotaManager, QuotaSpec, QuotaPeriod, RateLimitState,
)


def test_quota_within_limits():
    mgr = QuotaManager()
    mgr.set_quota("openai", QuotaSpec(max_requests_per_period=100, max_tokens_per_period=10000))
    mgr.record_usage("openai", requests=10, tokens=500, cost=0.01)
    status = mgr.check_quota("openai")
    assert status.within_quota is True
    assert status.requests_used == 10
    assert status.tokens_used == 500


def test_quota_exceeded_requests():
    mgr = QuotaManager()
    mgr.set_quota("openai", QuotaSpec(max_requests_per_period=5))
    mgr.record_usage("openai", requests=5, tokens=100, cost=0.0)
    status = mgr.check_quota("openai")
    assert status.within_quota is False
    assert "Request quota exceeded" in status.reason


def test_quota_exceeded_cost():
    mgr = QuotaManager()
    mgr.set_quota("openai", QuotaSpec(max_cost_per_month=1.0))
    mgr.record_usage("openai", requests=1, tokens=100, cost=1.5)
    status = mgr.check_quota("openai")
    assert status.within_quota is False
    assert "Cost quota exceeded" in status.reason


def test_rate_limited():
    mgr = QuotaManager()
    mgr.set_quota("openai", QuotaSpec())
    mgr.update_rate_limit("openai", RateLimitState(requests_remaining=0))
    status = mgr.check_quota("openai")
    assert status.within_quota is False
    assert "rate-limited" in status.reason


def test_quota_reset():
    mgr = QuotaManager()
    mgr.set_quota("openai", QuotaSpec(max_requests_per_period=10))
    mgr.record_usage("openai", requests=10, tokens=0, cost=0.0)
    mgr.reset_period("openai")
    status = mgr.check_quota("openai")
    assert status.within_quota is True
    assert status.requests_used == 0


def test_no_quota_set():
    mgr = QuotaManager()
    status = mgr.check_quota("unknown")
    assert status.within_quota is True


# python/tests/gateway/test_pricing.py
"""Tests for CostCalculator."""
import json
import pytest
from pathlib import Path
from agent_runtime_cockpit.gateway.pricing import CostCalculator, ModelPricing


def test_compute_cost_openai():
    calc = CostCalculator()
    cost = calc.compute_cost("openai", "gpt-4o", input_tokens=1000, output_tokens=500)
    assert cost > 0
    expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
    assert abs(cost - expected) < 0.0001


def test_compute_cost_anthropic_with_cache():
    calc = CostCalculator()
    cost = calc.compute_cost(
        "anthropic", "claude-3-5-sonnet-20241022",
        input_tokens=1000, output_tokens=500,
        cache_read_tokens=2000, cache_write_tokens=500,
    )
    expected = (
        (1000 / 1_000_000) * 3.00
        + (500 / 1_000_000) * 15.00
        + (2000 / 1_000_000) * 0.30
        + (500 / 1_000_000) * 3.75
    )
    assert abs(cost - expected) < 0.0001


def test_compute_cost_unknown_model():
    calc = CostCalculator()
    cost = calc.compute_cost("unknown", "nonexistent", input_tokens=100, output_tokens=50)
    assert cost == 0.0


def test_estimate_input_cost():
    calc = CostCalculator()
    cost = calc.estimate_input_cost("openai", "gpt-4o", 1_000_000)
    assert cost == 2.50


def test_estimate_input_cost_unknown():
    calc = CostCalculator()
    cost = calc.estimate_input_cost("unknown", "model", 1000)
    assert cost is None


def test_pricing_file_roundtrip(tmp_path: Path):
    calc = CostCalculator()
    export_path = tmp_path / "pricing.json"
    calc.export_pricing(export_path)
    assert export_path.exists()
    data = json.loads(export_path.read_text())
    assert "pricing" in data
    assert len(data["pricing"]) > 0
    new_calc = CostCalculator(pricing={})
    count = new_calc.load_pricing_file(export_path)
    assert count == len(data["pricing"])
    assert len(new_calc.pricing) == count
```

### e. How to Verify This Still Works

```bash
# 1. Verify OpenAI SDK version
cd python && uv pip show openai 2>/dev/null | grep Version
# Expected: 1.x

# 2. Verify Anthropic SDK version
cd python && uv pip show anthropic 2>/dev/null | grep Version
# Expected: 0.20+

# 3. Run gateway tests
cd python && uv run pytest tests/gateway/ -v

# 4. Verify rate-limit header parsing (manual, requires API key)
python3 -c "
import os
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-placeholder')
from agent_runtime_cockpit.gateway.base import RateLimitState
state = RateLimitState(requests_remaining=5, tokens_remaining=1000)
print(f'Rate limited: {state.is_rate_limited()}')
"

# 5. Check current provider pricing accuracy
# Compare with: https://openai.com/api/pricing/
# Compare with: https://www.anthropic.com/pricing
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| Provider pricing changes frequently | Cost estimates become stale | Versioned pricing file; `arc providers pricing update` command; document pricing date |
| Rate-limit header format varies by provider | Parsing fails silently | Per-provider header parsers; graceful degradation (assume no rate limit info) |
| OpenAI SDK breaking changes (v1→v2) | Dispatch fails | Pin SDK version; test against latest before upgrading |
| Provider API key not set | Runtime error at dispatch | Pre-flight check in gateway; clear error message with setup instructions |
| Cost tracking accuracy (streaming responses) | Underreported costs | Track tokens from response usage, not content length; handle streaming token counts |
| Multi-provider failover complexity | Gateway becomes complex | Start with single-provider dispatch; add failover in P3 after baseline works |
| Quota period reset timing | Quotas don't reset correctly | Use wall-clock period boundaries; test period transitions |
| OpenRouter aggregator pricing differs from direct | Cost estimates wrong | Separate pricing entries for OpenRouter models; document aggregator markup |

### g. Sources

- `docs/adr/007-provider-routing-unification.md` — Provider gateway architecture
- `python/src/agent_runtime_cockpit/providers.py` — Current provider registry
- `docs/IMPLEMENTATION_PLAN.md` — P2 provider routing scope, P3 cost-aware optimization
- OpenAI API docs — Rate-limit headers, pricing, SDK usage
- Anthropic API docs — Rate-limit headers, cache pricing, SDK usage
- Google Gemini API docs — Pricing and rate limits
- Mistral API docs — Pricing and SDK
- Groq API docs — Pricing and free tier
- Together AI docs — Open-source model pricing
- OpenRouter docs — Aggregator pricing model

---

## 13. Eval and Observability (P2 / P4)

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P2: Runtime + SwarmGraph Integrations":

> "Complete eval CLI basics — `arc eval save/delete/run --batch/report`, `arc runs search`, `arc doctor env/network/storage`, `arc bug-report`."

From "P4: Advanced Features":

> "OpenTelemetry integration — OTLP span export for observability. GenAI semantic conventions for LLM spans."

### b. Current External State

#### ARC Existing Eval Foundation

- **Location:** `python/src/agent_runtime_cockpit/evals/`
- **Current state:** Golden trace infrastructure with diff-based evaluation. CLI: `arc eval run`, `arc eval list`.
- **Gap:** No `save`, `delete`, `--batch`, `--report` commands. No `arc runs search`. No `arc doctor env/network/storage`. No `arc bug-report`.

#### OpenTelemetry Python

- **Library:** `/open-telemetry/opentelemetry-python`
- **Packages:** `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-exporter-otlp-proto-http`
- **API:** `trace.get_tracer(name)`, `tracer.start_as_current_span(name)`, `span.set_attribute()`, `span.add_event()`, `SpanStatusCode`
- **Exporters:** `OTLPSpanExporter(endpoint=, insecure=)` for gRPC; `OTLPSpanExporter(endpoint=)` for HTTP
- **Processors:** `BatchSpanProcessor(exporter)` for batched export, `SimpleSpanProcessor(exporter)` for synchronous export
- **GenAI Semantic Conventions:** `gen_ai.system`, `gen_ai.request.model`, `gen_ai.request.max_tokens`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`. Defined in OpenTelemetry semantic conventions (v1.27+).
- **Maintenance:** Active. CNCF graduated project. Frequent releases.
- **License:** Apache 2.0

#### OpenTelemetry Collector

- **Product:** OpenTelemetry Collector (otelcol) — receives OTLP data, processes, and exports to backends (Jaeger, Zipkin, Prometheus, Grafana Tempo, etc.)
- **ARC relevance:** ARC daemon can export spans to a local or remote collector. No collector dependency — spans export via OTLP to any compatible endpoint.

#### Current ARC Observability

- **Current state:** stdlib `logging` only. No distributed tracing. No metrics. No structured logging.
- **Gap:** No OTLP integration. No span context propagation. No observability for adapter execution or provider calls.

### c. Recommended Approach for ARC

1. **P2: Complete eval CLI.** Add `arc eval save` (save current run as golden trace), `arc eval delete` (remove golden trace), `arc eval run --batch` (run multiple evals), `arc eval report` (summary report). Add `arc runs search` (search runs via SQLite index). Add `arc doctor env/network/storage` (diagnostic checks). Add `arc bug-report` (collect diagnostic info).
2. **P4: OpenTelemetry integration.** Add `OTLPTracingProvider` that creates spans for: workflow execution, adapter dispatch, provider calls, eval runs. Use `BatchSpanProcessor` for async export. Respect GenAI semantic conventions for LLM spans.
3. **P4: Opt-in telemetry.** Telemetry is opt-in by default. Config flag `telemetry.enabled` controls export. `telemetry.endpoint` configures OTLP target. No PII in spans — redact prompts and responses by default.
4. **Span context propagation.** Pass span context through the execution pipeline: supervisor → adapter → provider → trace store. Enable distributed tracing across ARC components.

### d. Code Scaffolds

#### [SCAFFOLD] Eval CLI Completion (Python)

```python
# python/src/agent_runtime_cockpit/cli_eval.py
"""Extended eval CLI commands — save, delete, batch, report (P2)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

log = logging.getLogger(__name__)
console = Console()
err_console = Console(stderr=True)

eval_app = typer.Typer(name="eval", help="Evaluation and golden trace management")


@eval_app.command("save")
def eval_save(
    run_id: str = typer.Argument(..., help="Run ID to save as golden trace"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Golden trace name"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
) -> None:
    """Save a completed run as a golden trace for future evaluation."""
    ws = Path(workspace) if workspace else Path.cwd()
    golden_dir = ws / ".arc" / "evals" / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)
    trace_source = ws / ".arc" / "traces" / f"{run_id}.jsonl"
    if not trace_source.exists():
        err_console.print(f"[red]Trace not found: {trace_source}[/red]")
        raise typer.Exit(1)
    golden_name = name or run_id
    golden_path = golden_dir / f"{golden_name}.jsonl"
    if golden_path.exists():
        err_console.print(f"[yellow]Golden trace already exists: {golden_name}[/yellow]")
        raise typer.Exit(1)
    golden_path.write_text(trace_source.read_text(encoding="utf-8"))
    meta_path = golden_dir / f"{golden_name}.meta.json"
    meta_path.write_text(json.dumps({
        "name": golden_name,
        "source_run": run_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "event_count": sum(1 for _ in open(trace_source)),
    }, indent=2))
    console.print(f"[green]Golden trace saved: {golden_name}[/green]")


@eval_app.command("delete")
def eval_delete(
    name: str = typer.Argument(..., help="Golden trace name to delete"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
) -> None:
    """Delete a golden trace."""
    ws = Path(workspace) if workspace else Path.cwd()
    golden_dir = ws / ".arc" / "evals" / "golden"
    golden_path = golden_dir / f"{name}.jsonl"
    meta_path = golden_dir / f"{name}.meta.json"
    if not golden_path.exists() and not meta_path.exists():
        err_console.print(f"[red]Golden trace not found: {name}[/red]")
        raise typer.Exit(1)
    if golden_path.exists():
        golden_path.unlink()
    if meta_path.exists():
        meta_path.unlink()
    console.print(f"[green]Golden trace deleted: {name}[/green]")


@eval_app.command("report")
def eval_report(
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show evaluation summary report for all golden traces."""
    ws = Path(workspace) if workspace else Path.cwd()
    golden_dir = ws / ".arc" / "evals" / "golden"
    results_dir = ws / ".arc" / "evals" / "results"
    if not golden_dir.exists():
        console.print("[dim]No golden traces found.[/dim]")
        raise typer.Exit(0)
    golden_traces = list(golden_dir.glob("*.jsonl"))
    results = list(results_dir.glob("*.json")) if results_dir.exists() else []
    if json_output:
        report = {
            "golden_count": len(golden_traces),
            "result_count": len(results),
            "golden_traces": [f.stem for f in golden_traces],
        }
        console.print_json(json.dumps(report, indent=2))
        return
    table = Table(title="Eval Report")
    table.add_column("Golden Trace")
    table.add_column("Events")
    table.add_column("Results")
    for gf in golden_traces:
        event_count = sum(1 for _ in open(gf))
        result_files = list(results_dir.glob(f"{gf.stem}*.json")) if results_dir.exists() else []
        table.add_row(gf.stem, str(event_count), str(len(result_files)))
    console.print(table)
    console.print(f"\n[dim]Golden traces: {len(golden_traces)} | Results: {len(results)}[/dim]")
```

#### [SCAFFOLD] Runs Search CLI (Python)

```python
# python/src/agent_runtime_cockpit/cli_runs_search.py
"""Runs search CLI — search runs via SQLite index (P2)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..storage.sqlite_index import SqliteIndex, RunSearchQuery

log = logging.getLogger(__name__)
console = Console()

runs_search_app = typer.Typer(name="search", help="Search runs")


@runs_search_app.callback(invoke_without_command=True)
def runs_search(
    workflow: Optional[str] = typer.Option(None, "--workflow", "-f", help="Filter by workflow ID"),
    runtime: Optional[str] = typer.Option(None, "--runtime", "-r", help="Filter by runtime"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l"),
    offset: int = typer.Option(0, "--offset", "-o"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
) -> None:
    """Search runs using the SQLite index."""
    ws = Path(workspace) if workspace else Path.cwd()
    db_path = ws / ".arc" / "arc.db"
    if not db_path.exists():
        console.print("[yellow]SQLite index not found. Run 'arc backfill-index' first.[/yellow]")
        raise typer.Exit(1)
    index = SqliteIndex(db_path)
    query = RunSearchQuery(
        workflow_id=workflow, runtime=runtime, status=status,
        limit=limit, offset=offset,
    )
    results = index.search_runs(query)
    if not results:
        console.print("[dim]No runs found matching criteria.[/dim]")
        return
    table = Table(title=f"Runs ({len(results)} results)")
    table.add_column("Run ID")
    table.add_column("Workflow")
    table.add_column("Runtime")
    table.add_column("Status")
    table.add_column("Started")
    table.add_column("Ended")
    for r in results:
        table.add_row(r.id[:12], r.workflow_id, r.runtime, r.status, r.started_at[:19], (r.ended_at or "")[:19])
    console.print(table)
```

#### [SCAFFOLD] Doctor CLI (Python)

```python
# python/src/agent_runtime_cockpit/cli_doctor.py
"""Doctor CLI — diagnostic checks for env, network, storage (P2)."""
from __future__ import annotations

import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

log = logging.getLogger(__name__)
console = Console()

doctor_app = typer.Typer(name="doctor", help="ARC diagnostic checks")


def _check_env() -> list[dict]:
    results = []
    results.append({
        "check": "Python version",
        "status": "ok" if sys.version_info >= (3, 11) else "warn",
        "detail": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    })
    results.append({
        "check": "ARC_AUDIT_HMAC_KEY",
        "status": "ok" if os.environ.get("ARC_AUDIT_HMAC_KEY") else "info",
        "detail": "set" if os.environ.get("ARC_AUDIT_HMAC_KEY") else "not set (audit signing disabled)",
    })
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        results.append({
            "check": key,
            "status": "ok" if os.environ.get(key) else "info",
            "detail": "set" if os.environ.get(key) else "not set",
        })
    return results


def _check_network() -> list[dict]:
    results = []
    try:
        import socket
        socket.create_connection(("api.openai.com", 443), timeout=5)
        results.append({"check": "api.openai.com:443", "status": "ok", "detail": "reachable"})
    except Exception as e:
        results.append({"check": "api.openai.com:443", "status": "fail", "detail": str(e)})
    try:
        import socket
        socket.create_connection(("api.anthropic.com", 443), timeout=5)
        results.append({"check": "api.anthropic.com:443", "status": "ok", "detail": "reachable"})
    except Exception as e:
        results.append({"check": "api.anthropic.com:443", "status": "fail", "detail": str(e)})
    return results


def _check_storage(workspace: Path) -> list[dict]:
    results = []
    trace_dir = workspace / ".arc" / "traces"
    db_path = workspace / ".arc" / "arc.db"
    results.append({
        "check": "Trace directory",
        "status": "ok" if trace_dir.exists() else "info",
        "detail": f"{trace_dir} ({len(list(trace_dir.glob('*.jsonl')))} traces)" if trace_dir.exists() else f"{trace_dir} (not created)",
    })
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
                mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            results.append({
                "check": "SQLite index",
                "status": "ok",
                "detail": f"{db_path} ({count} runs, {mode} mode)",
            })
        except Exception as e:
            results.append({
                "check": "SQLite index",
                "status": "fail",
                "detail": str(e),
            })
    else:
        results.append({
            "check": "SQLite index",
            "status": "info",
            "detail": f"{db_path} (not created — run 'arc backfill-index')",
        })
    return results


@doctor_app.callback(invoke_without_command=True)
def doctor_all(
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
) -> None:
    """Run all diagnostic checks."""
    ws = Path(workspace) if workspace else Path.cwd()
    all_checks = _check_env() + _check_network() + _check_storage(ws)
    table = Table(title="ARC Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for check in all_checks:
        status_color = {"ok": "green", "warn": "yellow", "fail": "red", "info": "blue"}
        table.add_row(
            check["check"],
            f"[{status_color.get(check['status'], 'white')}]{check['status']}[/]",
            check["detail"],
        )
    console.print(table)
    failures = [c for c in all_checks if c["status"] == "fail"]
    if failures:
        console.print(f"\n[red]{len(failures)} check(s) failed.[/red]")
        raise typer.Exit(1)
```

#### [SCAFFOLD] OpenTelemetry Integration (Python)

```python
# python/src/agent_runtime_cockpit/observability/tracing.py
"""OpenTelemetry tracing integration (P4)."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator, Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class TelemetryConfig(BaseModel):
    """Configuration for OpenTelemetry tracing."""
    enabled: bool = False
    endpoint: str = "http://localhost:4317"
    service_name: str = "arc-studio"
    insecure: bool = True
    batch_export: bool = True
    redact_prompts: bool = True
    redact_responses: bool = True


_tracer_provider: Any = None
_tracer: Any = None


def init_telemetry(config: TelemetryConfig) -> bool:
    """Initialize OpenTelemetry tracing. Returns True if successfully initialized."""
    if not config.enabled:
        log.debug("Telemetry disabled by config")
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    except ImportError:
        log.warning("OpenTelemetry packages not installed. pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc")
        return False
    global _tracer_provider, _tracer
    provider = TracerProvider()
    exporter = OTLPSpanExporter(endpoint=config.endpoint, insecure=config.insecure)
    processor = BatchSpanProcessor(exporter) if config.batch_export else SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    _tracer = trace.get_tracer(config.service_name)
    log.info("Telemetry initialized: endpoint=%s, batch=%s", config.endpoint, config.batch_export)
    return True


def get_tracer():
    """Get the global tracer. Returns None if telemetry not initialized."""
    return _tracer


@contextmanager
def trace_workflow_run(
    workflow_id: str,
    runtime: str,
    run_id: str,
) -> Generator:
    """Context manager for tracing a workflow run."""
    tracer = get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span("workflow.run") as span:
        span.set_attribute("workflow.id", workflow_id)
        span.set_attribute("workflow.runtime", runtime)
        span.set_attribute("run.id", run_id)
        span.set_attribute("gen_ai.system", "arc-studio")
        yield span


@contextmanager
def trace_provider_call(
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Generator:
    """Context manager for tracing a provider API call with GenAI semantic conventions."""
    tracer = get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span("provider.call") as span:
        span.set_attribute("gen_ai.system", provider)
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("gen_ai.response.model", model)
        if input_tokens > 0:
            span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
        if output_tokens > 0:
            span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
        yield span


def shutdown_telemetry() -> None:
    """Flush and shutdown telemetry."""
    global _tracer_provider
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        log.info("Telemetry shutdown")
```

#### [SCAFFOLD] Eval and Observability Tests

```python
# python/tests/eval/test_eval_cli.py
"""Tests for extended eval CLI commands."""
import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from agent_runtime_cockpit.cli_eval import eval_app

runner = CliRunner()


def test_eval_save_and_list(tmp_path: Path):
    trace_dir = tmp_path / ".arc" / "traces"
    trace_dir.mkdir(parents=True)
    trace_file = trace_dir / "run-001.jsonl"
    trace_file.write_text('{"type": "RUN_STARTED"}\n{"type": "RUN_COMPLETED"}\n')
    result = runner.invoke(eval_app, ["save", "run-001", "--name", "golden-1", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    golden_path = tmp_path / ".arc" / "evals" / "golden" / "golden-1.jsonl"
    assert golden_path.exists()
    meta_path = tmp_path / ".arc" / "evals" / "golden" / "golden-1.meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["name"] == "golden-1"
    assert meta["event_count"] == 2


def test_eval_save_duplicate(tmp_path: Path):
    trace_dir = tmp_path / ".arc" / "traces"
    trace_dir.mkdir(parents=True)
    (trace_dir / "run-002.jsonl").write_text('{"type": "A"}\n')
    runner.invoke(eval_app, ["save", "run-002", "--name", "dup", "--workspace", str(tmp_path)])
    result = runner.invoke(eval_app, ["save", "run-002", "--name", "dup", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    assert "already exists" in result.stdout


def test_eval_delete(tmp_path: Path):
    golden_dir = tmp_path / ".arc" / "evals" / "golden"
    golden_dir.mkdir(parents=True)
    (golden_dir / "to-delete.jsonl").write_text("data")
    (golden_dir / "to-delete.meta.json").write_text("{}")
    result = runner.invoke(eval_app, ["delete", "to-delete", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert not (golden_dir / "to-delete.jsonl").exists()


def test_eval_delete_not_found(tmp_path: Path):
    result = runner.invoke(eval_app, ["delete", "nonexistent", "--workspace", str(tmp_path)])
    assert result.exit_code == 1


def test_eval_report_empty(tmp_path: Path):
    result = runner.invoke(eval_app, ["report", "--workspace", str(tmp_path)])
    assert result.exit_code == 0


def test_eval_report_with_data(tmp_path: Path):
    golden_dir = tmp_path / ".arc" / "evals" / "golden"
    golden_dir.mkdir(parents=True)
    (golden_dir / "test-golden.jsonl").write_text('{"type": "A"}\n{"type": "B"}\n')
    result = runner.invoke(eval_app, ["report", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "test-golden" in result.stdout


# python/tests/observability/test_tracing.py
"""Tests for OpenTelemetry tracing integration."""
import pytest
from unittest.mock import patch, MagicMock
from agent_runtime_cockpit.observability.tracing import (
    TelemetryConfig, init_telemetry, get_tracer, shutdown_telemetry,
    trace_workflow_run, trace_provider_call,
)


def test_telemetry_disabled():
    config = TelemetryConfig(enabled=False)
    result = init_telemetry(config)
    assert result is False
    assert get_tracer() is None


def test_telemetry_init_import_error():
    config = TelemetryConfig(enabled=True)
    with patch.dict("sys.modules", {"opentelemetry": None}):
        result = init_telemetry(config)
        assert result is False


def test_trace_workflow_run_no_telemetry():
    with trace_workflow_run("wf-1", "swarmgraph", "run-1") as span:
        assert span is None


def test_trace_provider_call_no_telemetry():
    with trace_provider_call("openai", "gpt-4") as span:
        assert span is None


def test_telemetry_config_defaults():
    config = TelemetryConfig()
    assert config.enabled is False
    assert config.endpoint == "http://localhost:4317"
    assert config.redact_prompts is True
    assert config.redact_responses is True


def test_shutdown_without_init():
    shutdown_telemetry()
```

### e. How to Verify This Still Works

```bash
# 1. Verify OpenTelemetry SDK version
cd python && uv pip show opentelemetry-sdk 2>/dev/null | grep Version
# Expected: 1.x

# 2. Verify OTLP exporter version
cd python && uv pip show opentelemetry-exporter-otlp-proto-grpc 2>/dev/null | grep Version

# 3. Run eval CLI tests
cd python && uv run pytest tests/eval/test_eval_cli.py -v

# 4. Run observability tests
cd python && uv run pytest tests/observability/test_tracing.py -v

# 5. Verify GenAI semantic conventions exist
python3 -c "
try:
    from opentelemetry.semconv.attributes import gen_ai_attributes
    print('GenAI semantic conventions available')
except ImportError:
    print('GenAI conventions not in this version — set attributes manually')
"

# 6. Manual OTLP test (requires local collector)
# docker run -p 4317:4317 otel/opentelemetry-collector:latest
# ARC_TELEMETRY_ENABLED=1 uv run arc run ...
# Check collector logs for received spans
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenTelemetry API changes between versions | Span attributes break | Pin OTel SDK version; use semantic conventions from package, not hardcoded strings |
| GenAI semantic conventions still evolving | Attribute names change | Track OTel semantic convention releases; update attributes with version check |
| OTLP endpoint not available | Spans lost silently | BatchSpanProcessor queues spans; log warning on export failure; graceful degradation |
| Telemetry adds latency to execution | Performance impact | BatchSpanProcessor is async; spans don't block execution; measure overhead |
| PII in spans (prompts, responses) | Privacy violation | `redact_prompts=True` by default; never include raw prompt/response content in span attributes |
| Telemetry opt-in vs opt-out confusion | Users don't know they're being tracked | Default to opt-in; clear documentation; `arc doctor` reports telemetry status |
| Eval CLI scope creep | Too many subcommands | Keep eval commands focused on golden trace management; separate `runs search` into its own sub-app |
| SQLite index not available when `runs search` runs | Command fails | Graceful error message directing user to run `arc backfill-index` |

### g. Sources

- Context7: `/open-telemetry/opentelemetry-python` — OTLPSpanExporter, BatchSpanProcessor, tracer API
- OpenTelemetry semantic conventions — GenAI attributes (gen_ai.system, gen_ai.usage.*)
- `python/src/agent_runtime_cockpit/evals/` — Current eval foundation
- `python/src/agent_runtime_cockpit/cli.py` — Current CLI with eval sub-app
- `docs/IMPLEMENTATION_PLAN.md` — P2 eval CLI scope, P4 observability
- OpenTelemetry Collector docs — OTLP receiver configuration

---

## 14. Security: Secrets, Auth, Redaction

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P1a: Execution Core Infrastructure":

> "Harden subprocess env allowlists — adapter subprocesses leak fewer secrets before container isolation exists."

From "P2: Runtime + SwarmGraph Integrations":

> "Safer daemon auth default — generate local bearer token on first start."

From `docs/adr/005-audit-key-management.md`:

> "Keyed audit chains (HMAC target), keychain preferred, env fallback with degraded status."

From `docs/adr/006-workspace-trust-isolation.md`:

> "Subprocess env allowlists and secret redaction before trace storage."

### b. Current External State

#### keyring (25.7.0, Nov 2025)

- **Library:** PyPI `keyring`
- **API:** `set_password(service, username, password)`, `get_password(service, username)`, `delete_password(service, username)`
- **Backends:** macOS Keychain, Freedesktop Secret Service (Linux), KDE KWallet, Windows Credential Locker
- **Platform behavior:** macOS Keychain is reliable. Linux Secret Service requires a running daemon (gnome-keyring-daemon or kwallet). Headless Linux/CI often has no backend available.
- **ARC relevance:** Preferred storage for audit signing keys and provider API keys. Env fallback with degraded status.

#### Python stdlib secrets

- **Library:** Python stdlib `secrets`
- **API:** `secrets.token_urlsafe(nbytes)`, `secrets.token_hex(nbytes)`, `secrets.token_bytes(nbytes)`
- **ARC relevance:** Local bearer-token generation for daemon auth. `secrets.token_urlsafe(32)` produces a 43-character URL-safe token.

#### Secret Redaction Patterns

Common secret patterns that must be redacted from logs, traces, and SSE output:

| Pattern | Regex | Example |
|---------|-------|---------|
| OpenAI API key | `sk-[a-zA-Z0-9]{20,}` | `sk-abc123def456...` |
| Anthropic API key | `sk-ant-[a-zA-Z0-9\-_]{20,}` | `sk-ant-api03-...` |
| Generic bearer token | `Bearer [a-zA-Z0-9\-_\.]{20,}` | `Bearer eyJhbGci...` |
| AWS access key | `AKIA[0-9A-Z]{16}` | `AKIAIOSFODNN7EXAMPLE` |
| AWS secret key | (context-dependent, 40-char base64) | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| GitHub token | `gh[ps]_[a-zA-Z0-9]{36,}` | `ghp_ABC123...` |
| Password in URL | `://[^:]+:[^@]+@` | `://user:pass@host` |
| Generic key=value | `(?:api_key\|apikey\|secret\|password\|token)\s*[:=]\s*\S+` | `api_key=abc123` |

#### Current ARC Security

- **Location:** `python/src/agent_runtime_cockpit/security/`
- **Current files:** `profiles.py`, `redaction.py`, `validation.py`
- **Current state:** `validate_workspace_path()` for path validation. No secret store. No bearer token auth. No redaction pipeline.
- **Daemon auth:** Currently no auth. Plan calls for local bearer token generation on first start.

### c. Recommended Approach for ARC

1. **Secret store: keyring with env fallback.** Use `keyring` for storing provider API keys and audit signing keys. Env fallback with degraded status for headless environments. Never log secret values.
2. **Daemon auth: local bearer token.** On first daemon start, generate a bearer token via `secrets.token_urlsafe(32)`. Store in `.arc/daemon-token`. Require `Authorization: Bearer <token>` for all daemon API calls. Support a compatibility window (no-token mode) with deprecation warning.
3. **Secret redaction pipeline:** Before any output is written to traces, logs, or SSE streams, run it through a redaction filter. Apply regex patterns for known secret formats. Replace matches with `[REDACTED:<type>]`.
4. **Subprocess env allowlists:** Only pass known-safe env vars to adapter subprocesses. Never pass `*_API_KEY`, `*_SECRET`, `*_TOKEN` vars. Define per-adapter allowlists.
5. **Redaction in trace storage:** All trace events are redacted before JSONL write. The redaction filter runs on string values in event data dicts.

### d. Code Scaffolds

#### [SCAFFOLD] Secret Store with Keyring (Python)

```python
# python/src/agent_runtime_cockpit/security/secrets.py
"""Secret store — keyring-based storage with env fallback for provider keys and tokens."""
from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)

ARC_SECRET_SERVICE = "arc-studio"


class SecretType(str, Enum):
    PROVIDER_KEY = "provider_key"
    AUDIT_HMAC_KEY = "audit_hmac_key"
    DAEMON_TOKEN = "daemon_token"


class SecretStatus(BaseModel):
    available: bool
    source: str
    secret_type: str
    degraded: bool = False
    warning: str = ""


class SecretStore:
    """Stores and retrieves secrets via keyring with env fallback."""

    def __init__(self, service: str = ARC_SECRET_SERVICE) -> None:
        self.service = service

    def get(self, secret_type: SecretType, key_id: str) -> tuple[Optional[str], SecretStatus]:
        """Retrieve a secret. Tries keychain first, then env fallback."""
        keychain_val = self._try_keychain(secret_type, key_id)
        if keychain_val is not None:
            return keychain_val, SecretStatus(
                available=True, source="keychain", secret_type=secret_type.value,
            )
        env_key = f"ARC_{secret_type.value.upper()}_{key_id.upper().replace('-', '_')}"
        env_val = os.environ.get(env_key)
        if env_val:
            return env_val, SecretStatus(
                available=True, source="env", secret_type=secret_type.value, degraded=True,
                warning=f"Using env fallback for {secret_type.value} — keychain preferred",
            )
        return None, SecretStatus(
            available=False, source="none", secret_type=secret_type.value, degraded=True,
            warning=f"No {secret_type.value} available for {key_id}",
        )

    def set(self, secret_type: SecretType, key_id: str, value: str) -> bool:
        """Store a secret in keychain."""
        try:
            import keyring
            compound_key = f"{secret_type.value}:{key_id}"
            keyring.set_password(self.service, compound_key, value)
            log.info("Secret stored in keychain: %s/%s", self.service, compound_key)
            return True
        except Exception as e:
            log.warning("Failed to store secret in keychain: %s", e)
            return False

    def delete(self, secret_type: SecretType, key_id: str) -> bool:
        """Delete a secret from keychain."""
        try:
            import keyring
            compound_key = f"{secret_type.value}:{key_id}"
            keyring.delete_password(self.service, compound_key)
            log.info("Secret deleted from keychain: %s/%s", self.service, compound_key)
            return True
        except Exception as e:
            log.warning("Failed to delete secret from keychain: %s", e)
            return False

    def _try_keychain(self, secret_type: SecretType, key_id: str) -> Optional[str]:
        try:
            import keyring
            compound_key = f"{secret_type.value}:{key_id}"
            return keyring.get_password(self.service, compound_key)
        except Exception as e:
            log.debug("Keychain access failed for %s:%s: %s", secret_type.value, key_id, e)
        return None
```

#### [SCAFFOLD] Daemon Auth with Bearer Token (Python)

```python
# python/src/agent_runtime_cockpit/security/daemon_auth.py
"""Daemon authentication — local bearer token generation and verification."""
from __future__ import annotations

import logging
import secrets
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)

TOKEN_LENGTH = 32
TOKEN_FILE = ".arc/daemon-token"


class DaemonAuthConfig(BaseModel):
    enabled: bool = True
    token_file: str = TOKEN_FILE
    compatibility_mode: bool = True
    compatibility_warning: str = (
        "Daemon auth is in compatibility mode: requests without tokens are accepted. "
        "This will be disabled in a future release. Set ARC_DAEMON_AUTH_ENABLED=1 to enforce."
    )


class DaemonAuth:
    """Manages daemon bearer token lifecycle."""

    def __init__(self, workspace: Path, config: Optional[DaemonAuthConfig] = None) -> None:
        self.workspace = workspace
        self.config = config or DaemonAuthConfig()
        self._token: Optional[str] = None

    def initialize(self) -> str:
        """Generate or load the daemon token. Returns the token."""
        token_path = self.workspace / self.config.token_file
        if token_path.exists():
            self._token = token_path.read_text(encoding="utf-8").strip()
            log.info("Loaded existing daemon token from %s", token_path)
        else:
            self._token = secrets.token_urlsafe(TOKEN_LENGTH)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(self._token)
            log.info("Generated new daemon token at %s", token_path)
        return self._token

    def verify(self, provided_token: Optional[str]) -> bool:
        """Verify a provided token against the stored token."""
        if not self.config.enabled:
            return True
        if self.config.compatibility_mode and provided_token is None:
            log.warning(self.config.compatibility_warning)
            return True
        if self._token is None:
            self.initialize()
        if provided_token is None:
            return False
        return secrets.compare_digest(provided_token, self._token)

    @property
    def token(self) -> Optional[str]:
        return self._token
```

#### [SCAFFOLD] Secret Redaction Filter (Python)

```python
# python/src/agent_runtime_cockpit/security/redaction.py
"""Secret redaction — pattern-based redaction for logs, traces, and SSE output."""
from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger(__name__)

REDACTION_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("openai_key", "[REDACTED:openai_key]", re.compile(r"sk-[a-zA-Z0-9]{20,}")),
    ("anthropic_key", "[REDACTED:anthropic_key]", re.compile(r"sk-ant-[a-zA-Z0-9\-_]{20,}")),
    ("bearer_token", "[REDACTED:bearer_token]", re.compile(r"Bearer\s+[a-zA-Z0-9\-_\.]{20,}")),
    ("aws_access_key", "[REDACTED:aws_access_key]", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", "[REDACTED:github_token]", re.compile(r"gh[ps]_[a-zA-Z0-9]{36,}")),
    ("password_url", "[REDACTED:password_url]", re.compile(r"(://[^:]+:)[^@]+(@)")),
    ("generic_secret", r"\1[REDACTED:generic_secret]\3", re.compile(
        r"((?:api_key|apikey|secret|password|token|access_token)\s*[:=]\s*['\"]?)([^\s'\",}\]]+)(['\"]?)",
        re.IGNORECASE,
    )),
]


def redact_string(text: str) -> str:
    """Redact known secret patterns from a string."""
    result = text
    for name, replacement, pattern in REDACTION_PATTERNS:
        if pattern.search(result):
            result = pattern.sub(replacement, result)
    return result


def redact_value(value: Any) -> Any:
    """Recursively redact secrets from a value (str, dict, list)."""
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value


def redact_event(event: dict[str, Any]) -> dict[str, Any]:
    """Redact secrets from a trace event dict."""
    return redact_value(event)
```

#### [SCAFFOLD] Security Tests

```python
# python/tests/security/test_secrets.py
"""Tests for SecretStore."""
import os
import pytest
from unittest.mock import patch
from agent_runtime_cockpit.security.secrets import SecretStore, SecretType


def test_get_secret_from_env():
    store = SecretStore()
    with patch.dict(os.environ, {"ARC_PROVIDER_KEY_OPENAI": "sk-test-123"}):
        with patch("keyring.get_password", side_effect=Exception("no keychain")):
            val, status = store.get(SecretType.PROVIDER_KEY, "openai")
            assert val == "sk-test-123"
            assert status.source == "env"
            assert status.degraded is True


def test_get_secret_not_available():
    store = SecretStore()
    with patch.dict(os.environ, {}, clear=True):
        with patch("keyring.get_password", side_effect=Exception("no keychain")):
            val, status = store.get(SecretType.PROVIDER_KEY, "nonexistent")
            assert val is None
            assert status.available is False


def test_set_secret_keychain_failure():
    store = SecretStore()
    with patch("keyring.set_password", side_effect=Exception("keychain error")):
        result = store.set(SecretType.PROVIDER_KEY, "test", "secret-value")
        assert result is False


# python/tests/security/test_daemon_auth.py
"""Tests for DaemonAuth."""
import pytest
from pathlib import Path
from agent_runtime_cockpit.security.daemon_auth import DaemonAuth, DaemonAuthConfig


def test_initialize_generates_token(tmp_path: Path):
    auth = DaemonAuth(tmp_path)
    token = auth.initialize()
    assert len(token) > 30
    token_file = tmp_path / ".arc" / "daemon-token"
    assert token_file.exists()
    assert token_file.read_text().strip() == token


def test_initialize_loads_existing(tmp_path: Path):
    token_file = tmp_path / ".arc" / "daemon-token"
    token_file.parent.mkdir(parents=True)
    token_file.write_text("existing-token-abc123")
    auth = DaemonAuth(tmp_path)
    token = auth.initialize()
    assert token == "existing-token-abc123"


def test_verify_correct_token(tmp_path: Path):
    auth = DaemonAuth(tmp_path, DaemonAuthConfig(compatibility_mode=False))
    token = auth.initialize()
    assert auth.verify(token) is True


def test_verify_wrong_token(tmp_path: Path):
    auth = DaemonAuth(tmp_path, DaemonAuthConfig(compatibility_mode=False))
    auth.initialize()
    assert auth.verify("wrong-token") is False


def test_verify_no_token_enforced(tmp_path: Path):
    auth = DaemonAuth(tmp_path, DaemonAuthConfig(compatibility_mode=False))
    auth.initialize()
    assert auth.verify(None) is False


def test_verify_compatibility_mode(tmp_path: Path):
    auth = DaemonAuth(tmp_path, DaemonAuthConfig(compatibility_mode=True))
    auth.initialize()
    assert auth.verify(None) is True


def test_verify_disabled(tmp_path: Path):
    auth = DaemonAuth(tmp_path, DaemonAuthConfig(enabled=False))
    assert auth.verify(None) is True
    assert auth.verify("anything") is True


# python/tests/security/test_redaction.py
"""Tests for secret redaction."""
import pytest
from agent_runtime_cockpit.security.redaction import (
    redact_string, redact_value, redact_event,
)


def test_redact_openai_key():
    text = "Using key sk-abc123def456ghi789jkl012mno345 for API calls"
    result = redact_string(text)
    assert "sk-abc123def456ghi789jkl012mno345" not in result
    assert "[REDACTED:openai_key]" in result


def test_redact_anthropic_key():
    text = "ANTHROPIC_API_KEY=sk-ant-api03-abc123def456ghi789jkl"
    result = redact_string(text)
    assert "sk-ant-api03" not in result
    assert "[REDACTED:anthropic_key]" in result


def test_redact_bearer_token():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc"
    result = redact_string(text)
    assert "eyJhbGci" not in result
    assert "[REDACTED:bearer_token]" in result


def test_redact_password_in_url():
    text = "postgresql://admin:supersecret@localhost:5432/db"
    result = redact_string(text)
    assert "supersecret" not in result
    assert "[REDACTED:password_url]" in result


def test_redact_generic_secret():
    text = "api_key=my-secret-key-12345"
    result = redact_string(text)
    assert "my-secret-key-12345" not in result
    assert "[REDACTED:generic_secret]" in result


def test_redact_no_secrets():
    text = "Hello world, this is a normal message"
    result = redact_string(text)
    assert result == text


def test_redact_value_dict():
    data = {
        "prompt": "What is the API key sk-abc123def456ghi789jkl012mno345?",
        "response": "The key is sk-abc123def456ghi789jkl012mno345",
        "metadata": {"user": "test"},
    }
    result = redact_value(data)
    assert "sk-abc123def456ghi789jkl012mno345" not in result["prompt"]
    assert "sk-abc123def456ghi789jkl012mno345" not in result["response"]
    assert result["metadata"]["user"] == "test"


def test_redact_value_list():
    data = ["normal text", "secret: sk-abc123def456ghi789jkl012mno345", 42]
    result = redact_value(data)
    assert "sk-abc123def456ghi789jkl012mno345" not in result[1]
    assert result[0] == "normal text"
    assert result[2] == 42


def test_redact_event():
    event = {
        "type": "TOOL_CALL_RESULT",
        "data": {
            "result": "Connected with api_key=secret123",
        },
    }
    result = redact_event(event)
    assert "secret123" not in result["data"]["result"]
    assert result["type"] == "TOOL_CALL_RESULT"


def test_redact_nested_structures():
    data = {
        "messages": [
            {"role": "user", "content": "My key is sk-abc123def456ghi789jkl012mno345"},
            {"role": "assistant", "content": "I see your key"},
        ],
        "config": {"api_key": "sk-abc123def456ghi789jkl012mno345"},
    }
    result = redact_value(data)
    assert "sk-abc123def456ghi789jkl012mno345" not in str(result)
```

### e. How to Verify This Still Works

```bash
# 1. Verify keyring version and backend
cd python && uv pip show keyring | grep Version
python3 -c "
import keyring
backend = keyring.get_keyring()
print(f'Keyring backend: {type(backend).__name__}')
"

# 2. Verify secrets module (stdlib, always available)
python3 -c "
import secrets
token = secrets.token_urlsafe(32)
print(f'Token length: {len(token)} chars')
assert len(token) > 30
"

# 3. Run security tests
cd python && uv run pytest tests/security/test_secrets.py -v
cd python && uv run pytest tests/security/test_daemon_auth.py -v
cd python && uv run pytest tests/security/test_redaction.py -v

# 4. Verify redaction patterns against real key formats
python3 -c "
from agent_runtime_cockpit.security.redaction import redact_string
tests = [
    'sk-abc123def456ghi789jkl012mno345pqr678',
    'sk-ant-api03-abc123def456ghi789jkl012mno',
    'AKIAIOSFODNN7EXAMPLE0',
    'ghp_ABC123DEF456GHI789JKL012MNO345PQR678',
]
for t in tests:
    result = redact_string(t)
    assert t not in result, f'Not redacted: {t}'
    print(f'OK: {t[:8]}... -> {result}')
"
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| keyring fails on headless Linux / CI | Secret storage unavailable | Env fallback with degraded status; document platform support; CI uses env vars |
| keyring backend selection ambiguity on Linux | Wrong backend chosen | Explicit backend configuration; test on target platforms |
| Bearer token file permissions | Token readable by other users | Set file permissions to 0600 on creation; document security implications |
| Compatibility mode left enabled too long | Unauthenticated daemon access | Deprecation warning in logs; document timeline for enforcement; env var to enforce early |
| Redaction regex false negatives | Secrets leak into traces | Test against real key formats from each provider; add provider-specific patterns |
| Redaction regex false positives | Legitimate content redacted | Conservative patterns; minimum length requirements; test against sample traces |
| New provider key formats not covered | Secrets leak | Document pattern registry; add new patterns when adding provider support |
| Redaction performance on large traces | Slow trace writes | Pre-compile regex patterns; only redact string values; benchmark on large traces |

### g. Sources

- PyPI: `keyring` 25.7.0 — Cross-platform keychain access
- Python stdlib: `secrets` — Cryptographically secure token generation
- `python/src/agent_runtime_cockpit/security/` — Current security modules
- `docs/adr/005-audit-key-management.md` — Audit key management
- `docs/adr/006-workspace-trust-isolation.md` — Subprocess env allowlists
- `docs/IMPLEMENTATION_PLAN.md` — P1a subprocess hardening, P2 daemon auth
- OpenAI API docs — API key format (`sk-` prefix)
- Anthropic API docs — API key format (`sk-ant-` prefix)
- AWS docs — Access key format (`AKIA` prefix)
- GitHub docs — Token format (`ghp_`, `ghs_` prefixes)

---

## 15. Packaging and Release (P5)

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "P5: Packaging and Distribution":

> "Package Python backend as wheel. Browser app + Python CLI/wheel for v0.1. Electron packaging post-v0.1."

From `docs/adr/008-daemon-bundling.md`:

> "Packaging spike for Electron; no PyInstaller decision until measured."

### b. Current External State

#### uv build + uv publish

- **Tool:** `uv` (Astral, same tool ARC uses for Python dependency management)
- **API:** `uv build` (builds sdist + wheel), `uv publish` (uploads to PyPI)
- **Build backends:** Supports `hatchling` (current ARC backend), `setuptools`, `flit`, `pdm`, `uv_build`
- **License:** MIT / Apache 2.0
- **Maintenance:** Very active. Astral-maintained. Frequent releases.
- **ARC relevance:** Primary build and publish tool. ARC already uses `uv` for dependency management and running tests.

#### hatchling (current ARC build backend)

- **Library:** PyPI `hatchling`
- **Config:** `pyproject.toml` `[build-system]` with `requires = ["hatchling"]`, `build-backend = "hatchling.build"`
- **ARC usage:** Current `python/pyproject.toml` uses hatchling. Project name: `agent-runtime-cockpit`.
- **Maintenance:** Active. Part of the Hatch project.
- **ARC relevance:** Keep hatchling. No need to switch to `uv_build` — hatchling is stable and well-supported.

#### uv_build (alternative)

- **Tool:** `uv_build` — Astral's own build backend (experimental as of 2026-05-14)
- **ARC relevance:** Not recommended for v0.1. Stick with hatchling (proven, stable). Evaluate `uv_build` for future releases.

#### GitHub Actions with astral-sh/setup-uv

- **Action:** `astral-sh/setup-uv@v5` (or latest)
- **API:** Sets up `uv` in GitHub Actions. Supports version pinning, caching, Python version selection.
- **ARC relevance:** CI already uses `uv`. Add build + publish steps using `uv build` and `uv publish`.

#### Electron Packaging (post-v0.1)

- **Scope:** Electron bundling of Theia browser app + Python daemon. Post-v0.1.
- **Tools:** `electron-builder`, `electron-packager`, PyInstaller (for Python daemon)
- **ARC relevance:** Deferred to P5 post-v0.1. v0.1 = browser app + Python CLI/wheel only.
- **ADR-008:** Packaging spike required before committing to Electron approach.

#### Current ARC Packaging

- **Python:** `python/pyproject.toml` with hatchling. Project: `agent-runtime-cockpit`. Entry point: `arc = "agent_runtime_cockpit.cli:app"`.
- **TypeScript:** `packages/arc-browser-app/` with webpack. Theia browser app.
- **CI:** GitHub Actions with `uv` for Python, `pnpm` for Node.

### c. Recommended Approach for ARC

1. **v0.1 scope: browser app + Python wheel only.** No Electron. No PyInstaller. Ship `agent-runtime-cockpit` wheel to PyPI (or private registry). Ship browser app as a build artifact.
2. **Python wheel: `uv build`.** Use `uv build` in CI. Produces sdist + wheel in `python/dist/`. Publish with `uv publish`.
3. **GitHub Actions release workflow:** Tag-based releases. On `v*` tag: build wheel, run tests, publish to PyPI. Build browser app, upload as release artifact.
4. **Version management:** Single source of truth in `python/pyproject.toml` `version` field. TypeScript packages follow independently.
5. **Electron deferred:** P5 post-v0.1. Requires packaging spike (ADR-008) before committing.
6. **Changelog:** Auto-generated from conventional commits. `git-cliff` or manual `CHANGELOG.md`.

### d. Code Scaffolds

#### [SCAFFOLD] GitHub Actions Release Workflow (YAML)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write
  id-token: write

jobs:
  build-python:
    name: Build Python wheel
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync --frozen
        working-directory: python
      - name: Run tests
        run: uv run pytest -q
        working-directory: python
      - name: Build wheel
        run: uv build
        working-directory: python
      - name: Upload wheel artifact
        uses: actions/upload-artifact@v4
        with:
          name: python-wheel
          path: python/dist/

  publish-python:
    name: Publish to PyPI
    needs: build-python
    runs-on: ubuntu-latest
    environment: release
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - uses: actions/download-artifact@v4
        with:
          name: python-wheel
          path: python/dist/
      - name: Publish to PyPI
        run: uv publish
        working-directory: python
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}

  build-browser-app:
    name: Build browser app
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9.15.9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
      - name: Install dependencies
        run: pnpm install --frozen-lockfile
      - name: Build
        run: pnpm build
      - name: Package browser app
        run: tar czf arc-browser-app-${{ github.ref_name }}.tar.gz -C packages/arc-browser-app/dist .
      - name: Upload browser app
        uses: actions/upload-artifact@v4
        with:
          name: browser-app
          path: arc-browser-app-*.tar.gz

  create-release:
    name: Create GitHub release
    needs: [publish-python, build-browser-app]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: browser-app
      - name: Create release
        uses: softprops/action-gh-release@v2
        with:
          files: arc-browser-app-*.tar.gz
          generate_release_notes: true
```

#### [SCAFFOLD] pyproject.toml Release Config (TOML)

```toml
# python/pyproject.toml — release-relevant sections
[project]
name = "agent-runtime-cockpit"
version = "0.1.0"
description = "ARC Studio — Agent Runtime Cockpit"
requires-python = ">=3.11"
license = { text = "MIT" }

[project.scripts]
arc = "agent_runtime_cockpit.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agent_runtime_cockpit"]

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/pyproject.toml",
    "/README.md",
]
```

### e. How to Verify This Still Works

```bash
# 1. Verify uv version
uv --version
# Expected: 0.x (latest)

# 2. Verify hatchling version
cd python && uv pip show hatchling | grep Version
# Expected: 1.x+

# 3. Build wheel locally
cd python && uv build
ls -la dist/
# Expected: .tar.gz and .whl files

# 4. Install wheel in clean venv
python3 -m venv /tmp/test-arc-install
source /tmp/test-arc-install/bin/activate
pip install dist/agent_runtime_cockpit-*.whl
arc --help
# Expected: CLI help output

# 5. Verify browser app build
pnpm build
ls -la packages/arc-browser-app/dist/
# Expected: built assets

# 6. Verify GitHub Actions workflow syntax
# Check .github/workflows/release.yml with actionlint
actionlint .github/workflows/release.yml
```

### f. Risks and Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| `uv publish` requires trusted publishing (OIDC) or API token | Publish fails in CI | Set up PyPI trusted publishing (OIDC) or store API token in GitHub secrets |
| Wheel includes unwanted files (test fixtures, dev config) | Bloated distribution | Configure `[tool.hatch.build.targets.wheel]` include/exclude patterns; inspect wheel contents |
| Browser app build size (>50 MiB) | Slow artifact upload/download | Webpack split chunks already configured (P1-8); only ARC code chunk matters (50 KiB) |
| Version mismatch between Python and TypeScript packages | Confusion about release version | Python version is the product version; TypeScript packages are internal |
| PyPI project name conflict (`agent-runtime-cockpit`) | Cannot publish | Verify name availability; use private registry if needed |
| Electron packaging complexity (post-v0.1) | Scope creep | ADR-008 packaging spike before committing; defer until v0.1 ships |
| CI publish step runs on wrong branch | Accidental release | Restrict publish to tag pushes only; require `environment: release` approval |
| `uv_build` not stable enough | Build failures | Stick with hatchling for v0.1; evaluate `uv_build` later |

### g. Sources

- `python/pyproject.toml` — Current build configuration
- `docs/adr/008-daemon-bundling.md` — Packaging spike requirement
- `docs/IMPLEMENTATION_PLAN.md` — P5 packaging scope, v0.1 definition
- Astral `uv` docs — `uv build`, `uv publish`, `setup-uv` action
- Hatchling docs — Build target configuration
- GitHub Actions docs — Artifact upload, OIDC trusted publishing
- PyPI docs — Trusted publishing setup

---

## 16. Cross-Cutting Risks Backlog

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "Cross-Cutting Concerns":

> "SwarmGraph vendoring/licensing/upstream sync. Secret storage platform behavior. SSE through corporate proxies. Theia churn. Telemetry privacy. Trace retention policy."

This section catalogs cross-cutting risks that span multiple phases and components. These are not phase-specific tasks but systemic concerns that must be tracked and mitigated across the entire implementation.

### b. Current External State

#### SwarmGraph Vendoring

- **Location:** `runtimes/swarmgraph/` (vendored copy)
- **Current state:** Vendored SwarmGraph with `swarm_shared/` package. ARC depends on it for runtime detection and execution.
- **Risk:** Vendored copy may diverge from upstream. License terms may restrict modification. Upstream changes may break ARC's adoption wrappers.
- **Upstream sync:** No automated sync mechanism. Manual updates required.

#### Secret Storage Platform Behavior

- **keyring on macOS:** Uses macOS Keychain. Reliable, well-tested.
- **keyring on Linux:** Uses Freedesktop Secret Service. Requires `gnome-keyring-daemon` or `kwalletd5` running. Headless servers and CI environments often have no backend.
- **keyring on Windows:** Uses Windows Credential Locker. Reliable on desktop, may fail on Windows Server without GUI.
- **CI environments:** Typically no keychain available. Env var fallback is essential.

#### SSE Through Corporate Proxies

- **Problem:** Corporate proxies (nginx, HAProxy, Cloudflare) may buffer SSE responses, breaking real-time streaming.
- **Mitigations:** `proxy_buffering off` in nginx. `Last-Event-ID` header for reconnection. Heartbeat comments to keep connection alive.
- **ARC impact:** Users behind corporate proxies may see delayed or broken live event streaming.

#### Theia Churn

- **Current gap:** ARC extension uses `@theia/core ^1.45.0`. Browser app uses `1.71.0`. This is a 26-version gap.
- **Theia release cadence:** Monthly releases. Breaking changes in DI, widget APIs, and protocol are possible between versions.
- **ARC impact:** Extension may break when browser app upgrades. Porting duplicate extensions becomes harder with version mismatch.

#### Telemetry Privacy

- **Concern:** OpenTelemetry spans may contain PII (prompts, responses, tool inputs).
- **Regulatory:** GDPR, CCPA, and enterprise policies may require opt-in consent, data minimization, and right-to-erasure.
- **ARC impact:** Telemetry must be opt-in by default. Spans must not contain raw prompt/response content. Redaction is mandatory.

#### Trace Retention Policy

- **Problem:** JSONL traces grow unbounded. A single long run can produce megabytes of events. Over months, `.arc/traces/` can grow to gigabytes.
- **SQLite index:** Also grows unbounded. No vacuum or cleanup policy.
- **ARC impact:** Disk space exhaustion. Slow listing and search. No user-facing retention controls.

### c. Recommended Approach for ARC

1. **SwarmGraph vendoring:** Document vendored version and commit hash. Add `arc doctor swarmgraph --version` to report vendored version. Establish upstream sync policy (monthly check, quarterly update). Consider submodule instead of raw vendoring for easier sync.
2. **Secret storage:** Test keyring on all target platforms (macOS, Ubuntu desktop, Ubuntu headless, Windows). Document platform-specific setup. Env fallback is mandatory for CI. Add `arc doctor secrets` to report keychain availability.
3. **SSE proxies:** Document proxy requirements (`proxy_buffering off`, `Last-Event-ID` support). Add heartbeat to SSE (already in Section 11 scaffold). Test behind nginx reverse proxy. Fallback to polling for proxy-incompatible environments.
4. **Theia alignment:** Align extension and browser app to the same `@theia/core` version before P3. Target 1.71.0 (browser app version). Test all existing extension code against 1.71.0 before upgrading.
5. **Telemetry privacy:** Default to opt-in. Redact prompts and responses in spans (Section 14 redaction). Document what data is collected. Add `arc telemetry status` to show current configuration.
6. **Trace retention:** Add `arc runs prune --older-than 90d` command. Add `arc storage vacuum` for SQLite vacuum. Document default retention policy (no limit). Make retention configurable per workspace.

### d. Code Scaffolds

This section is research-only. Code scaffolds for these concerns are covered in their respective phase sections:

- SwarmGraph version reporting: Section 2 (Execution Core)
- Secret storage: Section 14 (Security)
- SSE heartbeat and reconnection: Section 11 (Live Event Broker)
- Telemetry redaction: Section 14 (Security)
- Trace pruning: Section 10 (Storage)

### e. How to Verify This Still Works

```bash
# 1. Check SwarmGraph vendored version
git log --oneline -1 runtimes/swarmgraph/
# Compare with upstream: https://github.com/.../swarmgraph

# 2. Test keyring on target platforms
python3 -c "
import keyring
print(f'Backend: {type(keyring.get_keyring()).__name__}')
keyring.set_password('test-service', 'test-user', 'test-pass')
val = keyring.get_password('test-service', 'test-user')
print(f'Keyring works: {val is not None}')
keyring.delete_password('test-service', 'test-user')
"

# 3. Test SSE through nginx proxy
# Set up nginx with proxy_buffering off
# curl -N http://localhost/nginx-proxy/api/runs/test/events?mode=live
# Verify events stream without buffering

# 4. Check Theia version alignment
cd packages/arc-extension && pnpm list @theia/core
cd packages/arc-browser-app && pnpm list @theia/core
# Compare versions

# 5. Check trace directory size
du -sh .arc/traces/ 2>/dev/null || echo "No traces yet"
ls -la .arc/traces/ 2>/dev/null | wc -l

# 6. Check SQLite database size
ls -la .arc/arc.db 2>/dev/null || echo "No SQLite index yet"
```

### f. Risks and Unknowns

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| SwarmGraph upstream breaks vendored compatibility | Adoption wrappers fail | Medium | Pin vendored version; monthly sync check; submodule migration |
| keyring unavailable on headless Linux CI | CI tests fail, audit signing disabled | High | Env fallback mandatory; CI uses env vars; document setup |
| Corporate proxy buffers SSE | Live streaming broken for enterprise users | Medium | Document proxy config; heartbeat; polling fallback; test with nginx |
| Theia 1.45→1.71 breaking changes | Extension breaks after upgrade | High | Align versions before P3; test incrementally; pin version range |
| Telemetry PII leak | Regulatory violation, user trust loss | Low | Opt-in default; redaction mandatory; audit telemetry config |
| Trace directory grows to GBs | Disk exhaustion, slow operations | Medium | Retention CLI; configurable policy; document default |
| SQLite database grows without vacuum | Slow queries, large file | Medium | `arc storage vacuum` command; auto-vacuum pragma option |
| License incompatibility with vendored SwarmGraph | Cannot distribute ARC | Low | Review SwarmGraph license before public release; legal review |

### g. Sources

- `runtimes/swarmgraph/` — Vendored SwarmGraph
- `docs/adr/008-daemon-bundling.md` — Packaging considerations
- `docs/IMPLEMENTATION_PLAN.md` — Cross-cutting concerns section
- Theia release notes — Version changelog, breaking changes
- keyring docs — Platform backend behavior
- nginx docs — `proxy_buffering` directive for SSE
- OpenTelemetry docs — Privacy considerations, data minimization

---

## 17. Open Questions: Current External State

### a. Scope from the Plan

From `docs/IMPLEMENTATION_PLAN.md`, "Open Questions":

> "Windows v0.1 scope. Telemetry default. Out-of-workspace exports. HITL scope. SQLite recovery. Daemon auth compatibility window."

This section documents open decisions that require resolution before or during implementation. Each question includes the current external context, options, and a recommended path.

### b. Current External State

#### Windows Support

- **Current ARC state:** No Windows-specific testing or code. Python code should be cross-platform. Theia browser app is cross-platform.
- **External context:** Theia supports Windows. Python stdlib is cross-platform. `keyring` supports Windows Credential Locker. Docker on Windows requires Docker Desktop or WSL2.
- **Question:** Is Windows in scope for v0.1, or explicitly deferred?

#### Telemetry Default

- **Current ARC state:** No telemetry exists yet.
- **External context:** Industry trend is opt-in for developer tools (VS Code telemetry is opt-out, but many CLI tools are opt-in). GDPR/CCPA favor opt-in. OpenTelemetry SDK is inert until configured.
- **Question:** Should telemetry be opt-in (default off) or opt-out (default on)?

#### Out-of-Workspace Exports

- **Current ARC state:** Trace export writes to workspace `.arc/` directory.
- **External context:** Users may want to export traces to external locations (shared drives, cloud storage). This introduces security risks (exfiltrating sensitive trace data).
- **Question:** Should `arc export` allow writing outside workspace root, or be restricted?

#### HITL Scope

- **Current ARC state:** No HITL implementation exists.
- **External context:** HITL (Human-in-the-Loop) requires real-time interaction: the daemon streams a prompt to the UI, the user responds, the execution continues. Multi-user HITL adds authentication and concurrency complexity.
- **Question:** Is single-user workspace-local HITL sufficient for v0.1, or is concurrent-user support needed?

#### SQLite Recovery

- **Current ARC state:** SQLite index exists but is not wired into JSONL store.
- **External context:** SQLite can corrupt on crash (rare with WAL mode). JSONL is canonical and always valid. Recovery options: automatic rebuild on daemon start, or manual `arc doctor --fix`.
- **Question:** Should SQLite recovery be automatic (daemon rebuilds on start) or manual (user runs `arc doctor --fix`)?

#### Daemon Auth Compatibility Window

- **Current ARC state:** No daemon auth. All requests are unauthenticated.
- **External context:** Introducing auth breaks existing users. A compatibility window (accepting unauthenticated requests with a warning) eases migration. But the window must close eventually.
- **Question:** How long should the compatibility window last? (e.g., 30 days, 90 days, until v0.2?)

### c. Recommended Approach for ARC

1. **Windows v0.1 scope:** **Include Windows for Python CLI, defer Electron.** The Python wheel should work on Windows (test in CI). Theia browser app works on Windows. Electron packaging is post-v0.1 regardless of platform. Add Windows CI matrix for Python tests.
2. **Telemetry default:** **Opt-in.** Default to `telemetry.enabled = false`. Users must explicitly enable. This aligns with developer tool best practices and regulatory expectations. Document what is collected when enabled.
3. **Out-of-workspace exports:** **Allow with warning.** `arc export --output /external/path` should work but emit a security warning: "Exporting outside workspace root — ensure target directory is secure." Do not block, but warn.
4. **HITL scope:** **Single-user workspace-local for v0.1.** HITL is a single-user feature in v0.1. The daemon serves one user on localhost. Multi-user HITL (with authentication, concurrent sessions) is post-v0.1. This simplifies the implementation and matches the v0.1 local-first model.
5. **SQLite recovery:** **Automatic rebuild on daemon start.** If SQLite is corrupted or missing, the daemon automatically runs `backfill_index()` on startup. This is transparent to the user. Add `arc doctor --fix` for manual recovery. Log the rebuild event.
6. **Daemon auth compatibility window:** **90 days or until v0.2, whichever comes first.** Compatibility mode (accepting unauthenticated requests) lasts 90 days from first release, or until v0.2 ships. Deprecation warning logged on every unauthenticated request. After window closes, auth is enforced.

### d. Code Scaffolds

This section is research-only. Decisions here inform implementation in other sections.

### e. How to Verify This Still Works

```bash
# 1. Windows CI test (requires GitHub Actions Windows runner)
# Add to CI matrix:
# runs-on: windows-latest
# uv run pytest -q

# 2. Verify telemetry opt-in default
python3 -c "
from agent_runtime_cockpit.observability.tracing import TelemetryConfig
config = TelemetryConfig()
assert config.enabled is False, 'Telemetry should default to opt-in'
print('Telemetry default: opt-in (disabled)')
"

# 3. Verify export path handling
# After implementation: arc export run-001 --output /tmp/external/
# Should emit warning about exporting outside workspace

# 4. Verify SQLite auto-rebuild
# Corrupt SQLite: echo "corrupted" > .arc/arc.db
# Start daemon: uv run arc serve
# Check logs for backfill message

# 5. Verify daemon auth compatibility warning
# Start daemon without token: uv run arc serve
# Check logs for compatibility mode warning
```

### f. Risks and Unknowns

| Question | If Deferred | If Decided Wrong | Recommended Decision |
|----------|------------|-----------------|---------------------|
| Windows v0.1 scope | Windows users cannot use ARC v0.1 | Windows-specific bugs delay release | Include Python CLI + browser app; defer Electron |
| Telemetry default | No data to improve product | User backlash if opt-out | Opt-in; document clearly |
| Out-of-workspace exports | Users cannot share traces | Security incident from unrestricted export | Allow with warning; document risks |
| HITL scope | HITL not in v0.1 | Multi-user complexity delays v0.1 | Single-user workspace-local |
| SQLite recovery | Users must manually fix | Auto-rebuild masks underlying issues | Automatic rebuild + log event + manual `--fix` |
| Auth compatibility window | Breaking change for existing users | Window too long = security risk | 90 days or v0.2; deprecation warning on every request |

### g. Sources

- `docs/IMPLEMENTATION_PLAN.md` — Open questions section
- Theia docs — Windows support status
- OpenTelemetry docs — Privacy and consent guidelines
- GDPR/CCPA guidelines — Consent requirements for telemetry
- SQLite docs — WAL mode, corruption recovery, vacuum
- VS Code telemetry — Opt-out model for comparison
- Industry CLI tools (GitHub CLI, Docker CLI) — Auth migration patterns

---

## Appendix A: Version Pin Table

Every external dependency cited in this dossier. Versions as of 2026-05-14.

| Component | Latest stable | ARC min version | Source URL | Date checked | Notes |
|-----------|--------------|-----------------|------------|-------------|-------|
| pydantic | 2.x | >=2.7 | https://pypi.org/project/pydantic/ | 2026-05-14 | ARC uses v2 API exclusively; v3 not yet released |
| aiohttp | 3.x | >=3.9 | https://pypi.org/project/aiohttp/ | 2026-05-14 | Daemon REST endpoints |
| aiohttp-sse | 2.2.0 | >=2.2.0 | https://pypi.org/project/aiohttp-sse/ | 2026-05-14 | Last release Feb 2024; lightly maintained; manual SSE fallback exists |
| aiofiles | 24.1.0 | >=23.2 | https://pypi.org/project/aiofiles/ | 2026-05-14 | Async JSONL writes |
| anyio | 4.13.0 | — | https://pypi.org/project/anyio/ | 2026-05-14 | Not yet adopted; stdlib TaskGroup sufficient for P1a |
| structlog | 25.5.0 | — | https://pypi.org/project/structlog/ | 2026-05-14 | Not yet adopted; future structured logging consideration |
| typer | 0.12+ | >=0.12 | https://pypi.org/project/typer/ | 2026-05-14 | CLI framework |
| rich | 13.7+ | >=13.7 | https://pypi.org/project/rich/ | 2026-05-14 | Terminal UX (Console, Table) |
| tiktoken | 0.12.0 | >=0.12 | https://pypi.org/project/tiktoken/ | 2026-05-14 | Token counting for prompt optimizer |
| keyring | 25.7.0 | >=25.7 | https://pypi.org/project/keyring/ | 2026-05-14 | HMAC audit key storage; env fallback for headless |
| docker | 7.1.0 | >=7.1 | https://pypi.org/project/docker/ | 2026-05-14 | Last release May 2024; stable API; P2/P3 isolation |
| pytest | 8.2+ | >=8.2 | https://pypi.org/project/pytest/ | 2026-05-14 | Test framework |
| pytest-asyncio | 0.23+ | >=0.23 | https://pypi.org/project/pytest-asyncio/ | 2026-05-14 | Async test support; owns loop lifecycle on 3.12 |
| pytest-cov | latest | — | https://pypi.org/project/pytest-cov/ | 2026-05-14 | Coverage reporting |
| ruff | 0.4+ | >=0.4 | https://pypi.org/project/ruff/ | 2026-05-14 | Linter + formatter (line-length 100, target py311) |
| mypy | 1.10+ | >=1.10 | https://pypi.org/project/mypy/ | 2026-05-14 | Static type checking |
| langgraph | 1.0.8 | >=0.2 | https://pypi.org/project/langgraph/ | 2026-05-14 | Multiple version tracks (0.2.x, 0.3.x, 1.0.x); first adoption target |
| crewai | latest (PyPI) | — | https://pypi.org/project/crewai/ | 2026-05-14 | Third adoption priority; streaming via `stream=True` |
| openai-agents-python | latest (PyPI) | — | https://pypi.org/project/openai-agents/ | 2026-05-14 | Fourth adoption priority; SDK volatile; RunHooks integration point |
| llama-index | 0.14.6+ | — | https://pypi.org/project/llama-index/ | 2026-05-14 | Fifth adoption priority; broad API surface |
| ag2 | 0.9.7 | — | https://pypi.org/project/ag2/ | 2026-05-14 | Second adoption priority; package naming evolved from pyautogen |
| semantic-kernel | latest | — | https://pypi.org/project/semantic-kernel/ | 2026-05-14 | Deferred (P3+); enterprise plugin candidate |
| haystack | 2.28.0 | — | https://pypi.org/project/haystack-ai/ | 2026-05-14 | Deferred (P3+); RAG/pipeline candidate |
| dspy | latest | — | https://pypi.org/project/dspy-ai/ | 2026-05-14 | Deferred (P4+); selective typed-worker pattern |
| pydantic-ai | latest | — | https://pypi.org/project/pydantic-ai/ | 2026-05-14 | Deferred (P4+); typed-worker candidate |
| opentelemetry-python | latest | — | https://pypi.org/project/opentelemetry-sdk/ | 2026-05-14 | P4 observability; CNCF graduated |
| opentelemetry-exporter-otlp-proto-grpc | latest | — | https://pypi.org/project/opentelemetry-exporter-otlp-proto-grpc/ | 2026-05-14 | OTLP gRPC exporter for spans |
| opentelemetry-exporter-otlp-proto-http | latest | — | https://pypi.org/project/opentelemetry-exporter-otlp-proto-http/ | 2026-05-14 | OTLP HTTP exporter alternative |
| uv | latest (astral-sh) | — | https://pypi.org/project/uv/ | 2026-05-14 | Dependency management, test runner, build tool |
| hatchling | current | — | https://pypi.org/project/hatchling/ | 2026-05-14 | ARC build backend; keep for v0.1 |
| @theia/core | 1.71.0 (browser app) / ^1.45.0 (arc-extension) | ^1.45.0 | https://www.npmjs.com/package/@theia/core | 2026-05-14 | Version gap (26 versions) must be aligned before P3 |
| @theia/filesystem | follows @theia/core | — | https://www.npmjs.com/package/@theia/filesystem | 2026-05-14 | File system integration |
| @theia/workspace | follows @theia/core | — | https://www.npmjs.com/package/@theia/workspace | 2026-05-14 | Workspace management |
| @theia/navigator | follows @theia/core | — | https://www.npmjs.com/package/@theia/navigator | 2026-05-14 | File navigator |
| @theia/terminal | follows @theia/core | — | https://www.npmjs.com/package/@theia/terminal | 2026-05-14 | Terminal widget |
| inversify | via @theia/core/shared/inversify | — | https://www.npmjs.com/package/inversify | 2026-05-14 | DI framework; accessed through Theia shared exports |
| typescript | ^5.4.5 (root) / ^5.3.0 (arc-extension) | ^5.3.0 | https://www.npmjs.com/package/typescript | 2026-05-14 | Version alignment recommended |
| jest | latest (via Theia) | — | https://www.npmjs.com/package/jest | 2026-05-14 | Test framework for TypeScript |
| ts-jest | latest (via Theia) | — | https://www.npmjs.com/package/ts-jest | 2026-05-14 | TypeScript preprocessor for Jest |
| Node.js | >=20 | >=20 | https://nodejs.org/ | 2026-05-14 | Runtime for Theia browser app |
| pnpm | 9.15.9 | >=9 | https://pnpm.io/ | 2026-05-14 | Package manager; .tool-versions specifies 9.15.9 |

---

## Appendix B: Banned Claims Source List

### Banned Phrases and Source Citations

Every phrase below is forbidden in README, docs, CLI output, and UI text unless the condition cited is met.

| Banned Phrase / Claim | Source Section | Condition to Allow |
|----------------------|---------------|-------------------|
| "ARC supports SwarmGraph adoption for CrewAI/LangGraph/OpenAI Agents/AG2/LlamaIndex" | Plan "Do Not Overclaim"; REALITY_AUDIT §5 (Fiction: "$ runtime + SwarmGraph adoption layer" — zero code) | Tests prove adoption mode works end-to-end for that specific runtime |
| "ARC has live streaming" | Plan "Do Not Overclaim"; REALITY_AUDIT §5 (Fiction: "ARC can stream live events" — SSE is replay-only) | Endpoint delivers live events from active runs (not stored trace replay) |
| "ARC has signed audit trails" | Plan "Do Not Overclaim"; REALITY_AUDIT §5 (Fiction: "HMAC-SHA256 audit chain in ARC" — ARC uses SHA-256 only, HMAC is in vendored SG) | ARC uses SwarmGraph HMAC audit or equivalent keyed signature |
| "AG2 support" | Plan "Do Not Overclaim"; REALITY_AUDIT §5 (Fiction: "AG2 support" — code exists but NOT registered) | AG2 adapter is registered and visible in `arc runtimes` output |
| "OpenAI Agents project support" | Plan "Do Not Overclaim"; REALITY_AUDIT §5 (Fiction: "Support for OpenAI Agents SDK" — hardcoded TestAgent) | User-supplied export target is implemented (no hardcoded agents) |
| "LM Arena live mode" as a v0.1 product feature | Plan "Do Not Overclaim"; PLAN_COMPLETION_AUDIT §P0-5 (REFRAME: live mode exists behind gates, not 100% stub) | Gated-live behavior is tested and productized |
| "Production ready" for ARC daemon | Plan "Do Not Overclaim"; REALITY_AUDIT §10 (no auth by default, no multi-user) | Auth, workspace trust, and audit hardening are implemented |
| "Multi-user" or "tenant-isolated" for ARC daemon | Plan "Do Not Overclaim"; REALITY_AUDIT §10 (single-user, loopback-only) | Multi-user auth and tenant isolation are implemented |
| "Combo runtime = SwarmGraph composition" | REALITY_AUDIT §5 (Fiction: ComboRuntimeAdapter is sequential for-loop, not SwarmGraph) | ComboRuntimeAdapter is replaced with actual SwarmGraph queen/worker decomposition |
| "packages/arc-extension is not used" | REALITY_AUDIT §5 (Fiction: README L208 claim is FALSE — it IS the canonical extension) | Never — this claim is factually incorrect |
| "100% stub" for LM Arena | PLAN_COMPLETION_AUDIT §P0-5 (REALITY_AUDIT itself contains a fiction — live mode EXISTS behind dual gates) | Must say "stub-default with gated live mode" instead |
| "Support for LlamaIndex" (implying execution) | REALITY_AUDIT §5 (Fiction: 38-line detect-only adapter, no run_workflow) | Must say "LlamaIndex: detection only" until run_workflow is implemented |
| "HMAC-SHA256 audit" (for ARC's own chain) | REALITY_AUDIT §5 (Fiction: ARC audit/chain.py uses SHA-256 only; HMAC is in vendored SwarmGraph) | Must distinguish: "ARC hash chain (SHA-256)" vs "SwarmGraph HMAC audit (vendored)" |
| "SwarmGraph adoption layer" (as existing feature) | REALITY_AUDIT §3 ("+ SwarmGraph Adoption Layer" table — all rows say "Does not exist") | Must say "SwarmGraph adoption layer (planned)" or "not yet implemented" |

### Banned Claims Checker Script

```bash
#!/usr/bin/env bash
# scripts/check-banned-claims.sh
# Scans files/directories for banned product claims.
# Usage: ./scripts/check-banned-claims.sh [--fix] <file-or-dir> [...]

set -euo pipefail

FIX_MODE=false
if [[ "${1:-}" == "--fix" ]]; then
    FIX_MODE=true
    shift
fi

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 [--fix] <file-or-dir> [...]"
    echo ""
    echo "Scans for banned product claims in documentation and source files."
    echo "Exit 1 if any banned claims are found."
    echo ""
    echo "Options:"
    echo "  --fix    Show suggested replacements instead of just reporting"
    exit 1
fi

BANNED_PHRASES=(
    "SwarmGraph adoption for CrewAI"
    "SwarmGraph adoption for LangGraph"
    "SwarmGraph adoption for OpenAI Agents"
    "SwarmGraph adoption for AG2"
    "SwarmGraph adoption for LlamaIndex"
    "live streaming"
    "signed audit trails"
    "signed audit chain"
    "HMAC-SHA256 audit chain in ARC"
    "AG2 support"
    "OpenAI Agents project support"
    "OpenAI Agents SDK full support"
    "LM Arena live mode"
    "Production ready"
    "multi-user"
    "tenant-isolated"
    "Combo runtime = SwarmGraph composition"
    "packages/arc-extension is not used"
    "arc-extension is not used"
    "arc-extension is dead"
    "100% stub"
    "Support for LlamaIndex"
    "SwarmGraph adoption layer"
    "HMAC audit"
)

SUGGESTIONS=(
    "Use 'SwarmGraph adoption for CrewAI (not yet implemented)' or add test proof"
    "Use 'SwarmGraph adoption for LangGraph (not yet implemented)' or add test proof"
    "Use 'SwarmGraph adoption for OpenAI Agents (not yet implemented)' or add test proof"
    "Use 'SwarmGraph adoption for AG2 (not yet implemented)' or add test proof"
    "Use 'SwarmGraph adoption for LlamaIndex (not yet implemented)' or add test proof"
    "Use 'SSE trace replay' instead of 'live streaming' unless endpoint delivers live events"
    "Use 'SHA-256 hash chain' instead of 'signed audit trails' unless HMAC is wired"
    "Use 'SHA-256 hash chain' instead of 'signed audit chain' unless HMAC is wired"
    "Use 'ARC hash chain (SHA-256)' — HMAC exists only in vendored SwarmGraph"
    "Use 'AG2 adapter (not registered)' until adapter is wired into registry"
    "Use 'OpenAI Agents adapter (partial, hardcoded agent)' until export target is implemented"
    "Use 'OpenAI Agents adapter (partial)' until user-supplied export target works"
    "Use 'LM Arena: stub-default with gated live mode' instead of 'live mode' as product feature"
    "Use 'pre-release v0.1.0-alpha' instead of 'Production ready'"
    "Use 'single-user, loopback-only' instead of 'multi-user' until auth is implemented"
    "Use 'single-user, loopback-only' instead of 'tenant-isolated' until isolation is implemented"
    "Use 'sequential combo execution' instead of 'SwarmGraph composition'"
    "DELETE: packages/arc-extension IS the canonical extension — this claim is false"
    "DELETE: arc-extension IS the canonical extension — this claim is false"
    "DELETE: arc-extension is actively maintained — this claim is false"
    "Use 'stub-default with gated live mode' instead of '100% stub' for LM Arena"
    "Use 'LlamaIndex: detection only' until run_workflow is implemented"
    "Use 'SwarmGraph adoption layer (planned)' or 'not yet implemented'"
    "Use 'SwarmGraph HMAC audit (vendored)' to distinguish from ARC's SHA-256 chain"
)

TOTAL_MATCHES=0

for target in "$@"; do
    for i in "${!BANNED_PHRASES[@]}"; do
        phrase="${BANNED_PHRASES[$i]}"
        suggestion="${SUGGESTIONS[$i]}"

        matches=$(grep -rn --include="*.md" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.json" --include="*.yaml" --include="*.yml" -F "$phrase" "$target" 2>/dev/null || true)

        if [[ -n "$matches" ]]; then
            while IFS= read -r line; do
                file_and_line=$(echo "$line" | cut -d: -f1-2)
                content=$(echo "$line" | cut -d: -f3-)
                TOTAL_MATCHES=$((TOTAL_MATCHES + 1))
                echo "BANNED: $file_and_line"
                echo "  Found: \"$phrase\""
                echo "  Context: $content"
                if [[ "$FIX_MODE" == true ]]; then
                    echo "  Suggestion: $suggestion"
                fi
                echo ""
            done <<< "$matches"
        fi
    done
done

if [[ $TOTAL_MATCHES -gt 0 ]]; then
    echo "---"
    echo "Found $TOTAL_MATCHES banned claim(s)."
    if [[ "$FIX_MODE" == true ]]; then
        echo "Re-run without --fix to see file:line locations."
    else
        echo "Re-run with --fix to see suggested replacements."
    fi
    exit 1
else
    echo "OK: No banned claims found."
    exit 0
fi
```

---

## Appendix C: Verification Commands Cheat Sheet

Every "How to Verify This Still Works" command from Sections 1–17, consolidated and ordered for execution on a clean clone.

Assumptions: Python 3.11+, `uv` installed, Node.js 20+, pnpm 9+, fresh clone of `arc-theia-studio`.

### Section 1: Foundation ADRs

```bash
# Verify Pydantic version (expected: 2.x)
cd python && uv pip show pydantic | grep Version

# Verify event registry scaffold runs
cd python && uv run pytest tests/orchestration/test_event_registry.py -v

# Verify indexed store scaffold runs
cd python && uv run pytest tests/storage/test_indexed_store.py -v

# Verify ADRs are still coherent (should show the new events.py module after scaffold merge)
grep -r "schema_version" python/src/agent_runtime_cockpit/

# Check for Pydantic v3 release (if v3 exists, assess breaking changes before pinning)
pip index versions pydantic 2>/dev/null | head -3
```

### Section 2: Execution Core — P1a

```bash
# Verify Python 3.11+ TaskGroup availability (expected: True)
python3 -c "import asyncio; print(hasattr(asyncio, 'TaskGroup'))"

# Verify aiohttp-sse compatibility (expected: Version 2.2.0)
cd python && uv pip show aiohttp-sse

# Run supervisor tests
cd python && uv run pytest tests/orchestration/test_supervisor.py -v

# Run isolation tests
cd python && uv run pytest tests/isolation/test_isolation.py -v

# Verify SSE endpoint manually (after daemon start)
# curl -N http://localhost:8080/api/runs/test-run-001/events?mode=replay

# Check anyio version if considering adoption (expected: 4.x)
pip index versions anyio 2>/dev/null | head -3
```

### Section 3: Adoption Layer — P1b + P2

```bash
# Verify LangGraph version and API (expected: 0.2.x or higher)
cd python && uv pip show langgraph 2>/dev/null | grep Version

# Verify LangGraph astream_events v2 exists
python3 -c "
from langgraph.graph import StateGraph
import inspect
print('astream_events available')
"

# Run adoption protocol tests
cd python && uv run pytest tests/adoption/test_adoption_protocol.py -v

# Check CrewAI streaming API
python3 -c "
try:
    from crewai import Crew
    print('CrewAI importable')
except ImportError:
    print('CrewAI not installed — expected for scaffold')
"

# Verify OpenAI Agents SDK hooks
python3 -c "
try:
    from agents import RunHooks
    print('RunHooks available')
except ImportError:
    print('OpenAI Agents SDK not installed — expected for scaffold')
"

# SwarmGraph import spike
python3 -c "
import sys
sys.path.insert(0, 'runtimes/swarmgraph')
try:
    import swarm_shared
    print('SwarmGraph importable as library')
except ImportError as e:
    print(f'SwarmGraph not importable: {e}')
"
```

### Section 4: Runtime Integrations — P2

```bash
# Verify AG2 import paths
python3 -c "
try:
    import autogen; print(f'autogen: {autogen.__version__}')
except ImportError:
    try:
        import ag2; print(f'ag2: {ag2.__version__}')
    except ImportError:
        print('Neither autogen nor ag2 installed')
"

# Verify CrewAI Crew import
python3 -c "
try:
    from crewai import Crew, Agent, Task; print('CrewAI OK')
except ImportError:
    print('CrewAI not installed')
"

# Verify OpenAI Agents SDK
python3 -c "
try:
    from agents import Agent, Runner, RunHooks; print('OpenAI Agents SDK OK')
except ImportError:
    print('OpenAI Agents SDK not installed')
"

# Verify keyring on current platform
python3 -c "
import keyring
backend = keyring.get_keyring()
print(f'Keyring backend: {type(backend).__name__}')
"

# Run audit key tests
cd python && uv run pytest tests/audit/test_audit_keys.py -v

# Verify docker package
python3 -c "
try:
    import docker; print(f'docker: {docker.__version__}')
except ImportError:
    print('docker package not installed')
"

# Run adoption runner skeleton tests
cd python && uv run pytest tests/adoption/ -v
```

### Section 5: Theia Extension Architecture

```bash
# Verify Theia version alignment (check for mismatch)
cd packages/arc-extension && pnpm list @theia/core
cd packages/arc-browser-app && pnpm list @theia/core

# Build the extension
cd packages/arc-extension && pnpm build

# Build the browser app
cd packages/arc-browser-app && pnpm build

# Run frontend tests
cd packages/arc-extension && pnpm test

# Start browser app and verify ARC Studio loads
cd packages/arc-browser-app && pnpm start
# Navigate to http://localhost:3000
# Verify: ARC Studio widget opens via command palette

# Verify Inversify DI bindings (expected: 6+ bindings)
grep -c "bind(" packages/arc-extension/src/node/arc-extension-backend-module.ts

# Verify protocol types compile
cd packages/arc-extension && npx tsc --noEmit
```

### Section 6: Audit, HITL, Replay

```bash
# Verify Python stdlib hmac/hashlib availability
python3 -c "import hmac, hashlib; print('hmac + hashlib OK')"

# Verify keyring on current platform
python3 -c "
import keyring
backend = keyring.get_keyring()
print(f'Keyring backend: {type(backend).__name__}')
"

# Verify vendored SwarmGraph audit module is importable
python3 -c "
import sys
sys.path.insert(0, 'runtimes/swarmgraph/packages/swarm-shared')
from swarm_shared.audit import AuditRecord, sign_record, verify_record
print('SwarmGraph audit module importable')
"

# Run HMAC chain tests
cd python && uv run pytest tests/audit/test_hmac_chain.py -v

# Run HITL tests
cd python && uv run pytest tests/audit/test_hitl.py -v

# Run replay tests
cd python && uv run pytest tests/audit/test_replay.py -v

# Verify structlog version (future adoption, expected: 25.x)
pip index versions structlog 2>/dev/null | head -3
```

### Section 7: Workspace Trust and Isolation

```bash
# Verify docker SDK version (expected: 7.x)
cd python && uv pip show docker 2>/dev/null | grep Version

# Verify Docker daemon availability
docker info 2>/dev/null | head -5 || echo "Docker daemon not reachable"

# Verify OrbStack detection (macOS)
docker version 2>/dev/null | grep -i orbstack || echo "Not OrbStack"

# Run Docker isolation tests
cd python && uv run pytest tests/isolation/test_docker_provider.py -v

# Run trust enforcement tests
cd python && uv run pytest tests/security/test_trust_enforcement.py -v

# Verify committed workspace marker does not self-authorize
mkdir -p /tmp/test-trust/.arc && touch /tmp/test-trust/.arc/trusted
python3 -c "
from pathlib import Path
from agent_runtime_cockpit.security.trust import resolve_trust
r = resolve_trust(Path('/tmp/test-trust'))
print(f'Trust level: {r.level.value}')
assert r.level.value == 'untrusted'
"
rm -rf /tmp/test-trust
```

### Section 8: Prompt Optimizer

```bash
# Verify tiktoken version (expected: 0.12.x)
cd python && uv pip show tiktoken 2>/dev/null | grep Version

# Verify tiktoken encoding availability
python3 -c "
try:
    import tiktoken
    enc = tiktoken.get_encoding('cl100k_base')
    print(f'cl100k_base tokens for \"hello\": {len(enc.encode(\"hello\"))}')
except ImportError:
    print('tiktoken not installed — optimizer uses fallback')
"

# Run optimizer tests
cd python && uv run pytest tests/optimizer/test_local_optimizer.py -v

# Verify pricing data is current
# Check OpenAI pricing page: https://openai.com/api/pricing/
# Update KNOWN_PRICING dict if prices have changed
```

### Section 9: CLI Surface

```bash
# Verify Typer version (expected: 0.12+)
cd python && uv pip show typer | grep Version

# Verify rich version (expected: 13.7+)
cd python && uv pip show rich | grep Version

# Run CLI integration tests
cd python && uv run pytest tests/cli/test_cli_commands.py -v

# Test CLI entry point (should show all top-level commands including new sub-apps)
cd python && uv run arc --help

# Test new commands
cd python && uv run arc config show
cd python && uv run arc workspace status
cd python && uv run arc optimizer count "hello world"
cd python && uv run arc audit key status
```

### Section 10: Storage — JSONL + SQLite Index

```bash
# Verify aiofiles version (expected: 23.2+)
cd python && uv pip show aiofiles | grep Version

# Verify SQLite WAL mode
python3 -c "
import sqlite3, tempfile, os
db = os.path.join(tempfile.mkdtemp(), 'test.db')
conn = sqlite3.connect(db)
conn.execute('PRAGMA journal_mode=WAL')
mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
print(f'WAL mode: {mode}')
conn.close()
"

# Run async JSONL tests
cd python && uv run pytest tests/storage/test_async_jsonl.py -v

# Run SQLite index tests
cd python && uv run pytest tests/storage/test_sqlite_index.py -v

# Verify SQLite version
python3 -c "import sqlite3; print(f'SQLite: {sqlite3.sqlite_version}')"
```

### Section 11: Live Event Broker and SSE

```bash
# Verify aiohttp-sse version (expected: 2.2.0)
cd python && uv pip show aiohttp-sse 2>/dev/null | grep Version

# Verify aiohttp version (expected: 3.9+)
cd python && uv pip show aiohttp | grep Version

# Run event broker tests
cd python && uv run pytest tests/orchestration/test_event_broker.py -v

# Manual SSE test (after daemon start)
# Terminal 1: uv run arc serve --port 7777
# Terminal 2: curl -N -H "Accept: text/event-stream" http://127.0.0.1:7777/api/runs/test-run/events?mode=replay
# Expected: SSE event stream output

# Verify heartbeat (long-running curl, wait 15+ seconds — should see heartbeat comments)
# curl -N http://127.0.0.1:7777/api/runs/test-run/events?mode=live

# Check aiohttp-sse maintenance status (if no new versions since Feb 2024, consider manual SSE fallback)
pip index versions aiohttp-sse 2>/dev/null | head -3
```

### Section 12: Provider Gateway, Quotas, Cost Controls

```bash
# Verify OpenAI SDK version (expected: 1.x)
cd python && uv pip show openai 2>/dev/null | grep Version

# Verify Anthropic SDK version (expected: 0.20+)
cd python && uv pip show anthropic 2>/dev/null | grep Version

# Run gateway tests
cd python && uv run pytest tests/gateway/ -v

# Verify rate-limit header parsing (manual, requires API key)
python3 -c "
import os
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-placeholder')
from agent_runtime_cockpit.gateway.base import RateLimitState
state = RateLimitState(requests_remaining=5, tokens_remaining=1000)
print(f'Rate limited: {state.is_rate_limited()}')
"

# Check current provider pricing accuracy
# Compare with: https://openai.com/api/pricing/
# Compare with: https://www.anthropic.com/pricing
```

### Section 13: Eval and Observability

```bash
# Verify OpenTelemetry SDK version (expected: 1.x)
cd python && uv pip show opentelemetry-sdk 2>/dev/null | grep Version

# Verify OTLP exporter version
cd python && uv pip show opentelemetry-exporter-otlp-proto-grpc 2>/dev/null | grep Version

# Run eval CLI tests
cd python && uv run pytest tests/eval/test_eval_cli.py -v

# Run observability tests
cd python && uv run pytest tests/observability/test_tracing.py -v

# Verify GenAI semantic conventions exist
python3 -c "
try:
    from opentelemetry.semconv.attributes import gen_ai_attributes
    print('GenAI semantic conventions available')
except ImportError:
    print('GenAI conventions not in this version — set attributes manually')
"

# Manual OTLP test (requires local collector)
# docker run -p 4317:4317 otel/opentelemetry-collector:latest
# ARC_TELEMETRY_ENABLED=1 uv run arc run ...
# Check collector logs for received spans
```

### Section 14: Security — Secrets, Auth, Redaction

```bash
# Verify keyring version and backend
cd python && uv pip show keyring | grep Version
python3 -c "
import keyring
backend = keyring.get_keyring()
print(f'Keyring backend: {type(backend).__name__}')
"

# Verify secrets module (stdlib, always available)
python3 -c "
import secrets
token = secrets.token_urlsafe(32)
print(f'Token length: {len(token)} chars')
assert len(token) > 30
"

# Run security tests
cd python && uv run pytest tests/security/test_secrets.py -v
cd python && uv run pytest tests/security/test_daemon_auth.py -v
cd python && uv run pytest tests/security/test_redaction.py -v

# Verify redaction patterns against real key formats
python3 -c "
from agent_runtime_cockpit.security.redaction import redact_string
tests = [
    'sk-abc123def456ghi789jkl012mno345pqr678',
    'sk-ant-api03-abc123def456ghi789jkl012mno',
    'AKIAIOSFODNN7EXAMPLE0',
    'ghp_ABC123DEF456GHI789JKL012MNO345PQR678',
]
for t in tests:
    result = redact_string(t)
    assert t not in result, f'Not redacted: {t}'
    print(f'OK: {t[:8]}... -> {result}')
"
```

### Section 15: Packaging and Release

```bash
# Verify uv version (expected: 0.x, latest)
uv --version

# Verify hatchling version (expected: 1.x+)
cd python && uv pip show hatchling | grep Version

# Build wheel locally
cd python && uv build
ls -la dist/
# Expected: .tar.gz and .whl files

# Install wheel in clean venv
python3 -m venv /tmp/test-arc-install
source /tmp/test-arc-install/bin/activate
pip install dist/agent_runtime_cockpit-*.whl
arc --help
# Expected: CLI help output

# Verify browser app build
pnpm build
ls -la packages/arc-browser-app/dist/
# Expected: built assets

# Verify GitHub Actions workflow syntax
# Check .github/workflows/release.yml with actionlint
actionlint .github/workflows/release.yml
```

### Section 16: Cross-Cutting Risks

```bash
# Check SwarmGraph vendored version (compare with upstream)
git log --oneline -1 runtimes/swarmgraph/

# Test keyring on target platforms
python3 -c "
import keyring
print(f'Backend: {type(keyring.get_keyring()).__name__}')
keyring.set_password('test-service', 'test-user', 'test-pass')
val = keyring.get_password('test-service', 'test-user')
print(f'Keyring works: {val is not None}')
keyring.delete_password('test-service', 'test-user')
"

# Test SSE through nginx proxy
# Set up nginx with proxy_buffering off
# curl -N http://localhost/nginx-proxy/api/runs/test/events?mode=live
# Verify events stream without buffering

# Check Theia version alignment (compare versions)
cd packages/arc-extension && pnpm list @theia/core
cd packages/arc-browser-app && pnpm list @theia/core

# Check trace directory size
du -sh .arc/traces/ 2>/dev/null || echo "No traces yet"
ls -la .arc/traces/ 2>/dev/null | wc -l

# Check SQLite database size
ls -la .arc/arc.db 2>/dev/null || echo "No SQLite index yet"
```

### Section 17: Open Questions

```bash
# Windows CI test (requires GitHub Actions Windows runner)
# Add to CI matrix:
# runs-on: windows-latest
# uv run pytest -q

# Verify telemetry opt-in default
python3 -c "
from agent_runtime_cockpit.observability.tracing import TelemetryConfig
config = TelemetryConfig()
assert config.enabled is False, 'Telemetry should default to opt-in'
print('Telemetry default: opt-in (disabled)')
"

# Verify export path handling (after implementation)
# arc export run-001 --output /tmp/external/
# Should emit warning about exporting outside workspace

# Verify SQLite auto-rebuild
# Corrupt SQLite: echo "corrupted" > .arc/arc.db
# Start daemon: uv run arc serve
# Check logs for backfill message

# Verify daemon auth compatibility warning
# Start daemon without token: uv run arc serve
# Check logs for compatibility mode warning
```
