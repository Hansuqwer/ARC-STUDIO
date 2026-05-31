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

### Durable checkpoints

```python
from swarmgraph import JsonFileCheckpointStore

store = JsonFileCheckpointStore("./checkpoints")
runner = SwarmGraphRunner(checkpoint_store=store)
runner.run("Explain consensus")
```

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

## Relationship to ARC

Source ownership lives **here**. ARC (`agent_runtime_cockpit.swarmgraph`) is a
thin compatibility bridge that re-exports this package so existing
`agent_runtime_cockpit.swarmgraph.*` imports keep working unchanged.

## Release

See `.github/workflows/swarmgraph-sdk-release.yml`. The release workflow builds,
verifies isolated import/CLI, and runs `twine check` as a **dry run only**.
Publishing is intentionally disabled until external release is approved.
