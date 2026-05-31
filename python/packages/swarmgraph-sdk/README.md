# SwarmGraph SDK

Deterministic multi-agent orchestration primitives, packaged as a standalone
Python distribution (`swarmgraph-sdk`, import name `swarmgraph`).

> Status: **local alpha**. The wheel builds and runs in isolation, but is **not
> published to PyPI** yet. There is no production provider-backed runtime in this
> package — paid provider execution is gated and disabled by default.

## Install / build

```bash
# Build wheel + sdist from the monorepo
uv build python/packages/swarmgraph-sdk

# Import + run in an isolated environment (no monorepo on the path)
WHL=python/packages/swarmgraph-sdk/dist/*.whl
uv run --isolated --with "$WHL" swarmgraph run "Explain consensus" --json
```

## Quickstart

```python
from swarmgraph import SwarmGraphRunner, SwarmGraphConfig

runner = SwarmGraphRunner(config=SwarmGraphConfig(max_rounds=1))
result = runner.run("Explain consensus")
print(result["status"])  # "completed"
```

### Typed event stream

```python
async for event in runner.stream("Explain consensus"):
    print(event.kind, event.id)
```

### Durable checkpoints + resume

```python
from swarmgraph import JsonFileCheckpointStore, SwarmGraphRunner

store = JsonFileCheckpointStore("./checkpoints")
runner = SwarmGraphRunner(checkpoint_store=store)
runner.run("Explain consensus")

# Resume continues from the saved round/tasks, not from round 0.
checkpoint_id = store.list_ids()[-1]
runner.resume(checkpoint_id)
```

CLI:

```bash
swarmgraph run "Explain consensus" --checkpoint-dir ./ckpts --json
swarmgraph run --resume <checkpoint-id> --checkpoint-dir ./ckpts --json
```

### Provider-backed execution

`provider_backed` runs each worker through an injected `Provider`. With the
offline `EchoProvider` it stays deterministic and network-free, which is the
default for tests:

```python
from swarmgraph import EchoProvider, SwarmGraphConfig, SwarmGraphRunner
from swarmgraph.config import ExecutionMode

cfg = SwarmGraphConfig(execution_mode=ExecutionMode.provider_backed)
runner = SwarmGraphRunner(config=cfg, provider=EchoProvider())
runner.run("Explain consensus")
```

`gated_local` still denies paid provider calls unless `allow_paid_calls=True`.
`provider_backed` only requires a provider to be injected. To gate a *paid*
provider in `provider_backed`, wrap it in `GatedProvider`:

```python
from swarmgraph import GatedProvider, HTTPChatProvider

paid = HTTPChatProvider(base_url="https://api.example.com/v1", model="gpt-test", transport=transport)
runner = SwarmGraphRunner(config=cfg, provider=GatedProvider(paid))            # denied by default
runner = SwarmGraphRunner(config=cfg, provider=GatedProvider(paid, allow_paid_calls=True))  # opt-in
```

A denied call surfaces as a failed task (raising `PaidCallDeniedError` inside the
worker), never a silent paid request.

## Provider adapters

The SDK ships provider adapters that implement `swarmgraph.providers.Provider`
with **no ARC coupling**:

- `EchoProvider` — fully deterministic, offline. Echoes the last user message.
- `HTTPChatProvider` — OpenAI-style chat-completions *shape*. It performs **no
  network I/O on its own**; the caller injects an async `transport`. Without a
  transport, `complete()` raises, so tests can never make a surprise live call.

```python
from swarmgraph import EchoProvider, HTTPChatProvider

provider = EchoProvider()

async def transport(url, headers, json_body):
    ...  # back with httpx / aiohttp / a recorded fixture

http_provider = HTTPChatProvider(
    base_url="https://api.example.com/v1",
    model="gpt-test",
    transport=transport,
)
```

Paid provider execution still requires `allow_paid_calls=True` and is denied by
default.

## Consensus

Multiple deterministic consensus protocols are available
(`majority`, `quorum`, `raft`, `bft`, `confidence_weighted`, `critic_verifier`,
`gossip`, `selective_debate`, `hitl_signoff`). For fan-out worker groups,
per-worker vote confidence is derived from observable worker-result signals
(output substance, artifacts, errors) rather than a fixed value, so
confidence-weighted protocols can differentiate strong and weak outputs.

## Event history and checkpoint continuity

Events emitted during a run are persisted in `SwarmCheckpoint.events` (as
serializable dicts) and mirrored on `SwarmState.events`. On resume, the runner
seeds its event list from the checkpoint before emitting the resume audit event,
so `runner.get_events()` provides a continuous audit trail across
checkpoint/resume boundaries:

```python
from swarmgraph import JsonFileCheckpointStore, SwarmGraphConfig, SwarmGraphRunner

store = JsonFileCheckpointStore("./checkpoints")
cfg = SwarmGraphConfig(max_rounds=2)
runner = SwarmGraphRunner(config=cfg, checkpoint_store=store)
runner.run("Explain consensus")

checkpoint_id = store.list_ids()[-1]
checkpoint = store.load(checkpoint_id)
# checkpoint.events contains all events emitted during the original run.

runner2 = SwarmGraphRunner(config=cfg, checkpoint_store=store)
runner2.resume(checkpoint_id)
# runner2.get_events() starts with the checkpoint events, then adds the resume
# audit event and any new events from the resumed run.
```



Source ownership lives **here**. ARC (`agent_runtime_cockpit.swarmgraph`) is a
thin compatibility bridge that re-exports this package so existing
`agent_runtime_cockpit.swarmgraph.*` imports keep working unchanged. The repo is
a uv workspace, so `uv run --package swarmgraph-sdk ...` targets this member
directly while sharing one lockfile with ARC.

## Release

See `.github/workflows/swarmgraph-sdk-release.yml`. The release workflow builds,
verifies isolated import/CLI, and runs `twine check` as a **dry run only**.
Publishing is intentionally disabled until external release is approved.
