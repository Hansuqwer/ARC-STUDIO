# Copilot Arena Integration Research

Date: 2026-06-01
Branch: feat/sandbox-lima-execution-docker-hardening-fuzzing

## Goal

Integrate the open-source [Copilot Arena](https://github.com/lmarena/copilot-arena) (Apache-2.0) backend into ARC Studio as a real arena provider, replacing ARC's current stub `arena/service.py`.

## Research Notes

| Source | Link/query | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Copilot Arena server `app.py` | https://github.com/lmarena/copilot-arena/blob/main/server/app.py | FastAPI server. Endpoints: `POST /create_pair` (autocomplete battle), `POST /create_edit_pair` (inline edit battle), `PUT /add_completion`, `PUT /add_completion_outcome` (the vote), `PUT /add_single_outcome`. Model selection is distribution-driven (`model1\|\|\|model2` pairs with probabilities). Server holds all provider API keys; client sends none. | ARC client needs only `userId`, `privacy`, `prefix/suffix`/`codeToEdit`, `modelTags`. No key management on ARC side. | High | Whether the public upstream server accepts third-party `userId`s. |
| Copilot Arena `firebase_client.py` | https://github.com/lmarena/copilot-arena/blob/main/server/src/firebase_client.py | **Hard dependency**: requires `FIREBASE_ACCOUNT_KEY` env var (base64 JSON) or `config/firebase_config.json`. Used for ALL storage: completions, outcomes, votes, user data. No local/SQLite fallback. | Upstream server cannot run without Firebase. Self-hosting requires forking and replacing storage layer with ARC's SQLite. | High | None — this is the #1 feasibility blocker. |
| Copilot Arena `gcp_client.py` | https://github.com/lmarena/copilot-arena/blob/main/server/src/gcp_client.py | Fetches global outcomes DataFrame from GCS buckets for ELO computation. | ELO scoring requires GCP access or a local replacement. | High | None. |
| Copilot Arena `scores.py` | https://github.com/lmarena/copilot-arena/blob/main/server/src/scores.py | ELO is **Bradley-Terry MLE** (logistic regression via `sklearn`), not simple ELO. Blends global + user outcomes with tunable lambda (binary search). Requires `pandas`, `numpy`, `sklearn`. | ARC's existing `battle/store.py` uses simple ELO. To match Copilot Arena's scoring, would need to port or wrap the BT-MLE logic. | High | Whether ARC's simple ELO is "good enough" for local use. |
| Copilot Arena `constants.py` | https://github.com/lmarena/copilot-arena/blob/main/server/constants.py | `MAX_TOKENS=1024`, `TEMPERATURE=0.3`, `TIMEOUT=15.0`, `MAX_INPUT_TOKENS=8192`, `PREFIX_RATIO=0.75`. | ARC client must respect these limits or risk server rejection. | High | None. |
| Copilot Arena `base_client.py` | https://github.com/lmarena/copilot-arena/blob/main/server/apis/base_client.py | `IBaseClient` protocol: `stream()`, `create()`, `generate_prompt_for_model()`, `generate_stop_tokens_for_model()`. `State` dataclass: `prefix`, `suffix`, `code_to_edit`, `user_input`, `language`. | ARC's `ArenaProvider` must map `ProviderRequest.messages` → `State(prefix=..., suffix=...)`. Chat-style prompts become FIM by treating the last user message as `prefix`. | High | Whether FIM-style completion is the right UX for SwarmGraph workers (which are chat-oriented). |
| Copilot Arena `privacy.py` | https://github.com/lmarena/copilot-arena/blob/main/server/src/privacy.py | Three levels: `Private` (strips prompts/completions from logs), `Debug`, `Research` (keeps everything). | ARC should default to `Private` unless user opts in. | High | None. |
| Copilot Arena `utils.py` | https://github.com/lmarena/copilot-arena/blob/main/server/src/utils.py | Config from `config/app_config.yaml` or base64 `APP_CONFIG_YAML` env var. `get_models_by_tags()` filters models. `get_cost()` computes token cost. | Self-hosted fork needs a static config file or env var. | High | None. |
| Context7 | (blocked — invalid API key) | Tool unavailable. | Recorded blocker; used webfetch + GitHub raw URLs. | High | Fix Context7 key before next research pass. |
| Vercel Grep | `InlineCompletionItemProvider` | Theia/Monaco uses `monaco.languages.registerInlineCompletionItemProvider`. Returns `InlineCompletions` with `items[]`. Native Monaco shows **one** ghost text; showing two stacked requires custom widget or sequential rendering. | P4 (Theia paired completion) is non-trivial. Spike required. | Medium | Whether Theia exposes a higher-level API than raw Monaco. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Server hosting | **Fork upstream → strip Firebase/GCP/Amplitude → ARC-owned SQLite stores** | (a) Use upstream public server, (b) Self-host full server w/ Firebase | Upstream hard-depends on Firebase+GCP+Amplitude; no local mode. ARC owns vote/ELO/audit; no external SaaS deps. | `vendor/copilot-arena-server/` (new) | High |
| Prompt↔FIM bridge | (a) FIM/edit only for IDE inline, (b) Wrap chat prompt as `prefix=prompt, suffix=""` for SwarmGraph workers | Chat-only (no FIM) | Server is FIM-oriented; SwarmGraph workers are chat-oriented. Bridge both. | `arena/client.py`, `providers/arena_provider.py` | High |
| Vote/ELO store | Reuse ARC's `battle/store.py` SQLite + simple ELO | Port Copilot Arena's BT-MLE | BT-MLE requires `pandas`/`sklearn`/`numpy`; simple ELO is "good enough" for local use. | `arena/elo.py` (new) | Medium |
| Worker integration | New `ArenaProvider(ProviderClient)` | New `ExecutionMode` | Drop-in to existing `worker_execute(provider=...)` path; no SDK changes. | `providers/arena_provider.py` (new) | High |
| Theia paired completion | Spike Monaco `registerInlineCompletionItemProvider`; if 2 ghosts not feasible, use sequential top/bottom | Custom Theia widget | Monaco natively shows one ghost text; 2 stacked requires custom work. | `packages/arc-extension/src/browser/arena/` (new) | Medium |

## Feasibility Verdict

### Blockers

1. **Firebase hard-dependency** — upstream server cannot run without `FIREBASE_ACCOUNT_KEY` or `config/firebase_config.json`. All storage (completions, outcomes, votes, users) goes through Firebase. No local fallback.
2. **GCP hard-dependency** — ELO scoring fetches global outcomes from GCS buckets.
3. **Amplitude** — analytics on every request (non-blocking but noisy).

### Resolution

**Option B requires forking the server** and replacing:
- `firebase_client.py` → ARC SQLite store (reuse `battle/store.py` patterns).
- `gcp_client.py` → local CSV/SQLite for global outcomes (or skip global ELO, use user-only).
- `amplitude` → remove or stub.

**P0 (ARC-side client + provider) can proceed without the fork** if:
- The upstream public server accepts third-party `userId`s (unverified — test with a dummy userId).
- ARC defaults to stub mode unless `ARC_ARENA_SERVER_URL` is set + gates pass.

### Recommended Path

1. **P0 now**: Implement `ArenaClient` (async HTTP) + `ArenaProvider(ProviderClient)` + registry wiring. Default-off; stub mode unchanged. Test against a mocked server.
2. **P1 now**: SwarmGraph battle fan-out via `ArenaProvider`. Queen spawns N=4 workers → 4 battles → 8 candidates → consensus picks winners.
3. **P3 later**: Fork server, strip Firebase/GCP/Amplitude, self-host. Document exact diff.
4. **P4 later**: Theia paired inline completion. Spike Monaco API first.

## Implementation Scope (P0 + P1)

### P0 — Real HTTP client + ArenaProvider

**Files:**
- `python/src/agent_runtime_cockpit/arena/client.py` (NEW) — async `httpx` client: `create_pair`, `create_edit_pair`, `add_completion_outcome`. Base URL from `ARC_ARENA_SERVER_URL`. Default-off.
- `python/src/agent_runtime_cockpit/arena/service.py` (EDIT) — when server URL + gates present, call real client; else keep stub. Preserve all existing stub tests.
- `python/src/agent_runtime_cockpit/providers/arena_provider.py` (NEW) — `ArenaProvider` implementing `ProviderClient` Protocol. `complete()` maps `ProviderRequest.messages` → arena `create_pair` (prompt→prefix), returns winner; stash loser + `pairId` in `metadata`.
- `python/src/agent_runtime_cockpit/providers/__init__.py` (EDIT) — register `arena` provider.

**Gates:** `ARC_ARENA_SERVER_URL`, `ARC_ALLOW_LIVE_ARENA=true`, `ARC_LMARENA_ALLOW_COSTS=true`. Default = stub, offline, deterministic.

### P1 — SwarmGraph battle fan-out

**Files:**
- `python/packages/swarmgraph-sdk/swarmgraph/nodes/worker.py` (EDIT) — when injected provider is `ArenaProvider`, a single worker yields 2 candidates; record both for consensus.
- `python/packages/swarmgraph-sdk/swarmgraph/config.py` (EDIT) — add `arena_battle: bool` flag. Queen fan-out=4 → 4 battles → 8 candidates → consensus picks winners.
- Wire `add_completion_outcome` vote emission from consensus result.

**Truth boundary:** worker arena battles are **provider-backed** = opt-in, gated, paid. Default SwarmGraph stays `fake_offline`.

## Test Requirements (no live network in CI)

1. `ArenaClient` mocks `httpx` → asserts correct `/create_pair` payload + parses `completionItems`.
2. `ArenaProvider.complete()` maps prompt→prefix, returns winner, stashes loser+pairId.
3. Stub mode unchanged — all existing `test_*arena*` green.
4. SwarmGraph: queen fan-out=4 + `ArenaProvider` → 4 battles, 8 candidates, consensus emits 4 votes.
5. Vote path: consensus winner → `add_completion_outcome(acceptedIndex)` payload correct.
6. Gates: no server URL OR no `ARC_ALLOW_LIVE_ARENA` → stub, zero network.
7. ELO store: 2 outcomes update ratings deterministically (reuse `battle/store.py`).

## Verification

```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm build && pnpm typecheck
bash scripts/check-banned-claims.sh docs/agents.md docs/roadmap.md docs/phases.md docs/release/checklist.md docs/REALITY_AUDIT.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md README.md
```

## Claim Boundaries

- "Real arena integration" **only** if a live server is contacted and tests prove it.
- "Self-hosted arena" **only** after the Firebase-stripped fork actually boots and serves `/create_pair`.
- "SwarmGraph battle mode" **only** when N workers produce N battles with recorded votes + tests.
- Keep stub default-off. No `lmarena.ai` API claim — it's the **open-source server**, not the hosted product.
- Apache-2.0: vendored server code must retain LICENSE + attribution.

## Next Steps

1. Implement P0 (client + provider + tests).
2. Implement P1 (SwarmGraph battle fan-out + tests).
3. Verify: ruff, pytest, build, typecheck, banned-claims.
4. Update roadmap/phases if status genuinely changes.
5. Defer P3 (server fork) and P4 (Theia paired completion) to future slices.
