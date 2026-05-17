# 15 — Implementation Slices

## Slice 1: Schema Contracts (PR 1)

**Goal:** Implement all 5 cockpit primitive schemas in Python + TypeScript.
**Who:** Any Python + TS-capable model

**Files to create:**
- `python/src/agent_runtime_cockpit/protocol/run_contract.py` — `RunContract` Pydantic model
- `python/src/agent_runtime_cockpit/protocol/run_receipt.py` — `RunReceipt` Pydantic model
- `python/src/agent_runtime_cockpit/protocol/failure_autopsy.py` — `FailureAutopsy` Pydantic model
- `python/src/agent_runtime_cockpit/protocol/evidence_refs.py` — `EvidenceRef` Pydantic model
- `python/src/agent_runtime_cockpit/protocol/trust_diff.py` — `TrustDiff` Pydantic model

**Files to extend:**
- `packages/arc-extension/src/common/arc-protocol.ts` — Add all 5 TypeScript interfaces

**Tests:** `tests/test_run_contract.py`, `tests/test_run_receipt.py`, `tests/test_failure_autopsy.py`, `tests/test_evidence_refs.py`, `tests/test_trust_diff.py`

**AC:** All 5 schemas validate, serialize, deserialize. No runtime behavior.

## Slice 2: Policy Loader + TrustDiff (PR 2)

**Goal:** Approval policy loader that computes TrustDiff on trust changes.
**Who:** Python-capable model

**Files to create:**
- `python/src/agent_runtime_cockpit/config/policy.py` — `PolicyConfig`, `ApprovalPolicy`, `load_policy()`

**Files to extend:**
- `python/src/agent_runtime_cockpit/security/trust.py` — `ensure_trusted()` returns `TrustDiff`

**Tests:** `tests/test_policy.py`, `tests/test_trust_diff.py`

**AC:** Policy loads from `.arc/policy.yaml` and `~/.config/arc-studio/policy.yaml`. Project policy cannot weaken user policy for `shell_exec` and `trust_changes`. TrustDiff computed on UNTRUSTED → TRUSTED.

## Slice 3: EventBroker SSE Extensions (PR 3)

**Goal:** New event types for cockpit primitives. SSE streams contract/receipt/autopsy events.
**Who:** Python-capable model

**Files to extend:**
- `python/src/agent_runtime_cockpit/protocol/events.py` — Add `CONTRACT_*`, `RECEIPT_GENERATED`, `FAILURE_AUTOPSY_GENERATED`, `EVIDENCE_REF_CREATED`
- `python/src/agent_runtime_cockpit/orchestration/event_broker.py` — No changes needed (generic publish)

**Tests:** `python/tests/test_event_broker.py`

**AC:** New event types registered. SSE endpoint streams them.

## Slice 4: RunReceipt CLI + Storage (PR 4)

**Goal:** Receipt generated on run completion, stored, `arc-studio receipt show/verify` works.
**Who:** Python-capable model

**Files to extend:**
- `python/src/agent_runtime_cockpit/orchestration/supervisor.py` — Generate receipt on completion/failure
- `python/src/agent_runtime_cockpit/storage/jsonl.py` — `save_receipt()`, `load_receipt()`
- `python/src/agent_runtime_cockpit/storage/sqlite.py` — Store `receipt_id` in runs table
- `python/src/agent_runtime_cockpit/cli.py` — `arc receipt` subcommand group

**Tests:** `tests/test_run_receipt.py`, `tests/test_storage_receipt.py`

**AC:** Receipt stored alongside trace. `arc-studio receipt show <run-id>` works. `arc-studio receipt verify <file>` validates HMAC.

## Slice 5: FailureAutopsy Generation (PR 5)

**Goal:** Autopsy generated on run failure, rendered in FailureCard.
**Who:** Python-capable model

**Files to extend:**
- `python/src/agent_runtime_cockpit/orchestration/supervisor.py` — `_generate_autopsy()` method

**Tests:** `tests/test_failure_autopsy.py`

**AC:** Autopsy generated on FAILED transition. `knows` vs `guesses` distinction preserved. Retry options include safe defaults.

## Slice 6: EvidenceRefs Throughout (PR 6)

**Goal:** Events carry evidence refs. Chat messages, failures, and graph nodes can reference evidence.
**Who:** Python + TS-capable model

**Files to extend:**
- `python/src/agent_runtime_cockpit/protocol/schemas.py` — `RunEvent.data` carries `evidence_refs`
- `packages/arc-extension/src/common/arc-protocol.ts` — `EvidenceRef` in all relevant interfaces

**Tests:** `tests/test_evidence_refs.py`

**AC:** EvidenceRef attaches to events. Invalid refs stripped server-side. `file` and `tool_output` kinds supported.

## Slice 7: Runtime Capabilities Negotiation (PR 7)

**Goal:** Capability report includes cockpit primitive flags. Runtime switch shows diff.
**Who:** Python-capable model

**Files to extend:**
- `python/src/agent_runtime_cockpit/protocol/capabilities.py` — Add `can_emit_*` flags
- `python/src/agent_runtime_cockpit/adapters/base.py` — `CapabilityReport` extended

**Tests:** `tests/test_capability_negotiation.py`

**AC:** `GET /api/runtimes` returns full capability reports. Diff shown on runtime switch.

## Slice 8: CrossLinker Service (PR 8)

**Goal:** Events indexed for cross-referencing. Graph/Chat linking works.
**Who:** Python + TS-capable model

**Files to create:**
- `python/src/agent_runtime_cockpit/orchestration/cross_linker.py` — `CrossLinker` class

**Files to extend:**
- `python/src/agent_runtime_cockpit/orchestration/event_broker.py` — Feed events to CrossLinker

**Tests:** `tests/test_cross_linker.py`

**AC:** CrossLinker builds correct index. Selecting graph node highlights related messages.

## Slice 9: CLI Chat REPL (PR 9)

**Goal:** `arc-studio` launches interactive chat with startup banner, message processing, session management.
**Who:** Python-capable model (rich/Textual)

**Files to create:**
- `python/src/agent_runtime_cockpit/cli/__init__.py`
- `python/src/agent_runtime_cockpit/cli/chat_repl.py` — `ChatREPL`
- `python/src/agent_runtime_cockpit/cli/slash_commands.py` — `SlashCommandRouter`
- `python/src/agent_runtime_cockpit/cli/session.py` — `SessionManager`

**Files to extend:**
- `python/src/agent_runtime_cockpit/config/model.py` — Add `CliConfig` sub-model

**Tests:** `tests/test_chat_repl.py`, `tests/test_slash_commands.py`, `tests/test_session.py`

**AC:** `arc-studio` (no args) → banner. User message → response. `/help` → 22 commands. `/config` opens TUI. Session persists.

## Slice 10: Theia Tab Reboot (PR 10)

**Goal:** Single ArcStudioWidget with 4 tabs replaces 5 old widgets. Status bar shows runtime/model/mode.
**Who:** TypeScript/React-capable model

**Files to create:**
- `packages/arc-extension/src/browser/arc-studio-widget.tsx` — Main tabbed widget
- `packages/arc-extension/src/browser/tabs/ChatTab.tsx` — Chat panel
- `packages/arc-extension/src/browser/tabs/RunsTab.tsx` — Run list + detail
- `packages/arc-extension/src/browser/tabs/WorkflowsTab.tsx` — Workflow cards
- `packages/arc-extension/src/browser/tabs/ConfigTab.tsx` — Config form

**Files to extend:**
- `packages/arc-extension/src/common/arc-protocol.ts` — Extend `ArcService` with new methods
- `packages/arc-extension/src/node/arc-backend-service.ts` — Implement new methods
- `packages/arc-extension/src/node/arc-extension-backend-module.ts` — Register new widget

**Tests:** `__tests__/arc-studio-widget.test.ts`, `__tests__/chat-tab.test.ts`

**AC:** Single widget with 4 tabs renders. Chat sends/receives messages. Runs list loads from SQLite. Config saves `.arc/config.yaml`. Status bar shows runtime/model/mode.
