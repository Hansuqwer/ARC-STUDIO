# ARC v2 — Q10 Fixture Expansion Report (Sprint-7 prep)

Date: 2026-06-11 · Branch: `arc-v2/sprint-1-protocol-bridge` · Executes checkpoint #1
decision 4 (Q10 priority families) + blocking issue #8 (ordered sequences for the
replay scrubber).

## What was added (all additive; nothing overwritten — generator refuses)

### 1. Per-instance fixtures: 21 new kinds → coverage 17/69 ⇒ **38/69**

| Family | Kinds added |
|---|---|
| TOOL_CALL_* | TOOL_CALL, TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END, TOOL_CALL_RESULT, TOOL_CALL_ERROR, TOOL_END |
| MESSAGE / TEXT_MESSAGE_* | MESSAGE, MESSAGE_CHUNK, TEXT_MESSAGE_START, TEXT_MESSAGE_CONTENT, TEXT_MESSAGE_END, TEXT_MESSAGE_CHUNK |
| STATE_SNAPSHOT | STATE_SNAPSHOT |
| *_DENIED (deterministic security) | TRUST_DENIED, PAID_CALL_DENIED, SHELL_DENIED, NETWORK_DENIED, PERMISSION_DENIED |
| Runs-timeline stragglers | STEP_STARTED, HANDOFF |

### 2. Ordered scenario: `protocol/fixtures/run-event-seq/tool-use-streaming/`

18 events, `001-RUN_STARTED.json` … `018-RUN_COMPLETED.json` (naming per brief §5.6),
one coherent run: streamed assistant message → streamed tool call (ARGS deltas) →
STATE_SNAPSHOT → SHELL_DENIED → HITL_PROMPT → HITL_RESPONSE(reject) → HANDOFF →
AGENT_END → RUN_COMPLETED. Contiguous `sequence` 1–18 (gap-free is asserted at
generation time AND at test time).

### 3. Generator: `scripts/generate-priority-fixtures.py`

Daemon-side authoring per checkpoint #1: every fixture must pass the canonical
registry validator (`validate_event_data`) and the canonical Pydantic model
(`RunEvent.model_validate`) before being written. **The guard fired during
authoring**: my first HITL_RESPONSE draft (`response` field) was rejected —
canonical shape requires `decision`/`operator_id`/`responded_at`. Fixed from the
registry, not by relaxing the guard. Generator also refuses to overwrite any
existing file (additive rule, mechanically enforced).

### 4. Consumers updated (additive)

- `rust/arc-daemon-client` replay test `ordered_scenario_replays_gap_free_through_panel_path`:
  replays the scenario through the same `on_event` path panels will use; asserts
  gap-free, lifecycle brackets first/last, and presence of every specially-rendered
  family. This is the Sprint-7 Event Stream parity oracle, live today.
- `protocol/fixtures/README.md`: documents `run-event-seq/` and corrects the F2
  drift note (aspirational dirs).

## Evidence

| Check | Result |
|---|---|
| Rust fixture conformance (decode + semantic re-encode, incl. 21 new) | 7/7 tests green; coverage test reports **38/69**, regenerated `reports/fixture-coverage.md` |
| Rust replay (per-instance + ordered scenario) | 8/8 tests green; scenario: 18 events, 0 gaps |
| Python canonical validation | every fixture passed `validate_event_data` + `RunEvent.model_validate` at generation (hard gate) |
| JSON-Schema leg (`docs/schemas/RunEvent.json`, Draft 2020-12) | **56/56 ok** (38 per-instance + 18 scenario) |
| v1 regression (`tests/protocol` + `tests/web`) | **220 passed** — includes `test_event_type_parity` (every fixture type ∈ Python EVENT_TYPES) |
| clippy workspace | 0 warnings |

## Findings

- **F8 (pre-existing, recorded not fixed):** TS `KNOWN_RUN_EVENT_TYPES`
  (`packages/arc-protocol-ts/src/run-events.ts`) is a 38-kind subset that already
  excluded long-fixtured kinds (AGENT_START/AGENT_END) before this change; unknown
  kinds route to its RAW handling, mirroring Rust's `KnownRunEvent::Unknown`. The
  existing parity test only asserts TS ⊆ Python, so this is by design — but the
  Sprint-9 Chat/Event panels should extend the TS list additively *if* the v1
  Theia surfaces are still alive then (owner call; v1 freeze policy may make it moot).
- Remaining uncovered kinds: **31/69**, dominated by BATTLE_* (7, deferred surface),
  CONSENSUS_*/EVAL_* (5), CONTRACT_PROPOSED/ACCEPTED/FULFILLED (3), NODE_* (3),
  observability/budget singletons. None feed retirement-critical panels per the
  current ledger split; next tranche owner-gated as before.

## Rollback

Delete: 21 files in `protocol/fixtures/run-event/`, `protocol/fixtures/run-event-seq/`,
`scripts/generate-priority-fixtures.py`, the README section, the one replay test,
this report. No existing file was modified except the README (append-only).
