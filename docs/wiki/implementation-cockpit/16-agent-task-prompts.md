# 16 — Agent Task Prompts and Model Assignment

## Recommended First 10 Implementation PRs

| # | PR | Files | Dependencies | Estimated Effort | Best Model |
|---|-----|-------|-------------|-----------------|------------|
| 1 | Schema contracts (5 Pydantic + TS interfaces) | 6 create, 1 extend | None | 2-4 hrs | Qwen (strong schema work) |
| 2 | Policy loader + TrustDiff | 1 create, 1 extend | PR 1 | 3-5 hrs | Qwen (schema + logic) |
| 3 | EventBroker SSE extensions | 1 extend | None | 1-2 hrs | Mimo (concise, focused) |
| 4 | RunReceipt CLI + storage | 4 extend | PR 1 | 4-6 hrs | Kimi (CLI + storage) |
| 5 | FailureAutopsy generation | 1 extend | PR 1 | 3-5 hrs | Qwen (logic + analysis) |
| 6 | EvidenceRefs throughout | 2 extend | PR 1 | 2-3 hrs | Mimo (cross-cutting) |
| 7 | Runtime capabilities negotiation | 2 extend | PR 1 | 3-4 hrs | Kimi (adapter + protocol) |
| 8 | CrossLinker service | 1 create, 1 extend | PR 3, PR 6 | 3-5 hrs | DeepSeek (index + state) |
| 9 | CLI chat REPL | 4 create, 1 extend | PR 4, PR 5, PR 6 | 8-12 hrs | Gemini (UI-heavy Python) |
| 10 | Theia tab reboot | 5 create, 3 extend | PR 9 | 10-16 hrs | DeepSeek (React + Theia) |

## Dependency Graph

```
PR 1: Schema contracts
  ├── PR 2: Policy + TrustDiff
  ├── PR 4: RunReceipt CLI
  │   └── PR 9: CLI Chat REPL (depends on PR 4, PR 5, PR 6)
  ├── PR 5: FailureAutopsy
  │   └── PR 9
  ├── PR 6: EvidenceRefs
  │   ├── PR 8: CrossLinker
  │   │   └── PR 10: Theia Tab Reboot (depends on PR 9)
  │   └── PR 9
  └── PR 7: Runtime Capabilities

PR 3: EventBroker SSE
  └── PR 8
```

```
PR 1 ─┬─┬ PR 2
      │ └─ PR 4 ──┐
      ├── PR 5 ───┤
      ├── PR 6 ───┤
      │           ├── PR 9 ── PR 10
      └── PR 7 ───┘
PR 3 ────────── PR 8 ── PR 10
```

## Model Assignment Plan

| Model | Strength | Assigned PRs | Rationale |
|-------|----------|-------------|-----------|
| **Qwen** | Python schema + logic | PR 1 (schemas), PR 2 (policy), PR 5 (autopsy) | Strong at Pydantic models, validation logic, enum-based state machines |
| **Mimo** | Concise, cross-cutting | PR 3 (SSE events), PR 6 (evidence refs) | Small, focused changes across multiple files; Mimo excels at small surgical edits |
| **Kimi** | CLI + storage patterns | PR 4 (receipt CLI), PR 7 (capabilities) | Good at CLI command patterns and storage integration |
| **DeepSeek** | Complex state + React | PR 8 (cross-linker), PR 10 (Theia tabs) | Strong at state management, React components, and complex index structures |
| **Gemini** | UI-heavy Python | PR 9 (chat REPL) | Best at rich TUI/UI code, user-facing interfaces with rich formatting |
| **Claude (review)** | Review + integration | All → review PRs 7-10 | Best at integration testing, catching regressions, verifying cross-surface behavior |

## Agent Task Prompts

### Prompt for PR 1 (Schema Contracts)

```
You are implementing the cockpit primitive schemas for ARC Studio.

FILES TO CREATE:
1. python/src/agent_runtime_cockpit/protocol/run_contract.py — RunContract Pydantic model
2. python/src/agent_runtime_cockpit/protocol/run_receipt.py — RunReceipt Pydantic model  
3. python/src/agent_runtime_cockpit/protocol/failure_autopsy.py — FailureAutopsy Pydantic model
4. python/src/agent_runtime_cockpit/protocol/evidence_refs.py — EvidenceRef Pydantic model
5. python/src/agent_runtime_cockpit/protocol/trust_diff.py — TrustDiff Pydantic model

FILES TO EXTEND:
6. packages/arc-extension/src/common/arc-protocol.ts — Add TypeScript interfaces

SCHEMA SPECS (from docs/research/ARC_STUDIO_UX_SPEC.md):
- RunContract: contractId, runId?, sessionId, objective, runtime, mode (plan/build/auto), allowedTools[], writeScope[], costCeilingUsd (number|unknown), rollbackPlan (git-revert/manual/none), evidenceExpected[], status (proposed/accepted/fulfilled/violated)
- RunReceipt: receiptVersion=1, receiptId, sessionId, runId, contractId?, status (completed/failed/cancelled), summary, costUsd?, filesChanged[], approvals[], evidenceRefs[], rollbackCommand?, trustBoundariesCrossed[], unresolvedRisks[], auditChainRef, signature
- FailureAutopsy: runId, probableCause (string|unknown), confidence (high/medium/low/unknown), failedNode?, lastSafeState?, retryOptions[] (label, command?, risk), knows[], guesses[], evidenceRefs[]
- EvidenceRef: evidenceId, kind (file/tool_output/run/node/ledger/receipt/frame_receipt), target, range?, redacted
- TrustDiff: diffId, before[], after[], addedCapabilities[], removedRestrictions[], affectedRuntimes[], requiresConfirmation (default true)

CONSTRAINTS:
- Use Pydantic v2 BaseModel
- Use Literal types for enums
- All classes must serialize to clean JSON
- TypeScript interfaces must mirror Python models exactly
- Read AGENTS.md and existing schemas in protocol/schemas.py for conventions
- Run cd python && uv run pytest -q after implementation
- Run pnpm --filter @arc-studio/protocol build && pnpm --filter arc-extension build after TS changes
```

### Prompt for PR 9 (Chat REPL)

```
You are implementing the CLI chat REPL for ARC Studio.

FILES TO CREATE:
1. python/src/agent_runtime_cockpit/cli/__init__.py
2. python/src/agent_runtime_cockpit/cli/chat_repl.py — ChatREPL class
3. python/src/agent_runtime_cockpit/cli/slash_commands.py — SlashCommandRouter class
4. python/src/agent_runtime_cockpit/cli/session.py — SessionManager class

FILES TO EXTEND:
5. python/src/agent_runtime_cockpit/config/model.py — Add CliConfig sub-model with fields: default_model, default_runtime, default_mode (plan/build/auto), session_history (bool), max_session_age_days (int)
6. python/src/agent_runtime_cockpit/cli.py — Add chat-repl command group

SPEC: See docs/research/CLI_IDE_REDESIGN_PLAN.md sections 2.3-2.5 and docs/research/ARC_STUDIO_UX_SPEC.md sections 7.1-7.9

KEY REQUIREMENTS:
- ChatREPL.run() starts with startup banner (workspace, runtime, model, mode)
- Message processing loop uses rich for formatting
- /help shows flat command list (22 commands)
- /config opens interactive TUI (rich Table + Panel)
- /runtime <id> switches runtime for session
- /runs lists from SQLite index
- Session persists to ~/.arc/sessions/<session_id>/transcript.jsonl
- arc-studio -c resumes last session (latest symlink)
- Ctrl+C saves session and exits cleanly

CONSTRAINTS:
- Use rich for TUI, NOT Textual (no extra dependency)
- Session ID format: ULID (26 chars)
- Read AGENTS.md for build/test commands
- Read existing cli.py for conventions
- Run cd python && uv run pytest -q after implementation
```

## Verification Checklist (all PRs)

Before considering any PR done, verify:

- [ ] `cd python && uv run pytest -q` passes
- [ ] `pnpm --filter @arc-studio/protocol build` passes (if TS changes)
- [ ] `pnpm --filter arc-extension build` passes (if TS changes)
- [ ] All new tests pass
- [ ] No leaked secrets in output/events
- [ ] v0.1 scope boundaries respected (no v0.2 features)
- [ ] Schema matches spec exactly
- [ ] No scope creep (Feature A does not implement Feature B)
- [ ] Bad file/content reading errors handled gracefully

## Scope Prevention Rules

| Feature | Stops at | Do not add |
|---------|----------|------------|
| RunContract | Pre-run proposal only | Post-run fulfillment |
| RunReceipt | Generation + CLI show/verify/export | Receipt comparison |
| FailureAutopsy | Knows + guesses from last N events | LLM-based diagnosis |
| EvidenceRefs | file + tool_output kinds | frame_receipt, ledger |
| TrustDiff | First workspace trust only | Key/policy/runtime diffs |
| CLI Chat | Basic REPL + slash commands | @mentions, queue, fuzzy autocomplete |
| Theia Tab | 4 tabs + status bar | Trace UI, replay scrubber, inline diff |
| Graph/Chat | Stable IDs + event enrichment | Graph explorer commands |
