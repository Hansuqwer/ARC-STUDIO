# Remaining Plan: 2-3 Session Workflow

Use 2 active coding sessions by default. Add a 3rd session only for review. Preserve unrelated dirty worktree changes. Do not use broad `git add .`.

## Model Routing

| Session | Role | Model |
|---|---|---|
| A | Lead/integrator/test/commit | ChatGPT 5.5 or Gemini 3.1 Pro |
| B | Backend/frontend worker | GLM 5.1 Precision for Python/backend; Qwen 3.6 Max for Theia/TS |
| C | Reviewer only | DeepSeek v4 Pro Precision |
| Docs/wiki | Documentation polish | Mimo v2.5 Pro |
| UX review | UX/copy/a11y review | Kimi 2.6 Precision |

## Current Green Gates

Run after each slice if relevant:

```bash
cd python && uv run pytest -q
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
pnpm --filter arc-extension test
```

Current known green after build-first ordering:

```bash
pnpm --filter arc-extension build && pnpm --filter arc-extension test
```

Expected: `307 passed`.

## Session A: Lead Prompt

Copy/paste into Session A:

```text
You are Session A: lead/integrator for ARC Studio v0.1 remaining implementation.

Model: ChatGPT 5.5 or Gemini 3.1 Pro.

Rules:
- Read `AGENTS.md` first.
- Preserve unrelated dirty worktree changes.
- Do not use broad `git add .`.
- Do not commit unless explicitly asked.
- Keep slices small and green.
- After worker changes, run targeted tests first, then full gates when feasible.
- If tests fail, fix before moving on.
- No paid/provider calls.
- No Trace UI default.
- No HotLoop.
- Do not overclaim features.

Read:
- `docs/wiki/implementation-cockpit/remaining-plan-sessions.md`
- `docs/wiki/implementation-cockpit/15-implementation-slices.md`
- `docs/research/ARC_STUDIO_UX_SPEC.md`
- `docs/research/CLI_IDE_REDESIGN_PLAN.md`
- relevant ADRs under `docs/adr/`

Start by checking:
- `git status --short`
- current tests/build only if needed

Then coordinate the next remaining slice in this order:
1. trust copy + receipt verify key consistency
2. policy loader + TrustDiff behavior
3. minimal `arc-studio` chat CLI
4. Theia single Studio widget shell
5. Runs tab receipts/autopsies
6. Config tab
7. Graph/Chat/Runs cross-linking
8. runtime capability diff UI
9. hide default Trace UI
10. npm/global wrapper

Return concise status:
- files changed
- tests run
- pass/fail
- next worker prompt
```

## Session B1: Python Backend Worker Prompt

Use GLM 5.1 Precision.

```text
You are Session B: Python/backend worker for ARC Studio v0.1.

Scope: implement the next smallest backend slice only.

First slice: trust copy + receipt verify key consistency.

Tasks:
1. Fix misleading trust warning in `python/src/agent_runtime_cockpit/security/trust.py`.
   Current message says execution proceeds with subprocess isolation, but `ensure_trusted()` blocks. Change copy to say execution is blocked until trusted.
2. Make `arc receipt verify` use `AuditKeyManager` by default when `--key` is omitted.
3. Keep explicit `--key` behavior unchanged.
4. Keep legacy dev-key fallback only as degraded compatibility if needed.
5. Add/update tests proving:
   - trust warning says execution is blocked until trusted
   - supervisor-generated receipt verifies via CLI without `--key`
   - explicit `--key` still works

Files likely involved:
- `python/src/agent_runtime_cockpit/security/trust.py`
- `python/src/agent_runtime_cockpit/cli.py`
- `python/tests/test_trust_resolver.py`
- `python/tests/cli/test_cockpit_receipts.py`
- maybe `python/tests/orchestration/test_supervisor.py`

Run:
```bash
cd python && uv run pytest tests/test_trust_resolver.py tests/cli/test_cockpit_receipts.py tests/orchestration/test_supervisor.py -q
cd python && uv run pytest -q
```

Forbidden:
- no frontend changes
- no policy loader in this slice
- no chat CLI
- no commits
- no broad refactors

Return:
- files changed
- exact test output
- remaining risks
```

## Session B2: Policy Loader Worker Prompt

Use GLM 5.1 Precision.

```text
You are Session B: Python/backend worker for ARC Studio v0.1.

Scope: implement Slice 2: Policy Loader + TrustDiff.

Read:
- `docs/wiki/implementation-cockpit/15-implementation-slices.md` Slice 2
- `docs/wiki/implementation-cockpit/12-trust-diff-policy.md`
- `python/src/agent_runtime_cockpit/config/model.py`
- `python/src/agent_runtime_cockpit/config/loader.py`
- `python/src/agent_runtime_cockpit/security/trust.py`
- `python/src/agent_runtime_cockpit/protocol/trust_diff.py`

Implement:
- `python/src/agent_runtime_cockpit/config/policy.py`
- `PolicyConfig`
- `ApprovalPolicy`
- `load_policy()`
- merge user policy and workspace policy
- project policy cannot weaken user policy for `shell_exec` and `trust_changes`
- helper to compute `TrustDiff` for UNTRUSTED -> TRUSTED or policy widening

Add tests:
- `python/tests/test_policy.py`
- update `python/tests/test_trust_diff.py` if needed

Acceptance:
- loads `.arc/policy.yaml`
- loads `~/.config/arc-studio/policy.yaml` or injected user path in tests
- user policy wins on restrictive fields
- TrustDiff includes added capabilities/removed restrictions/affected runtimes/reason

Run:
```bash
cd python && uv run pytest tests/test_policy.py tests/test_trust_diff.py -q
cd python && uv run pytest -q
```

Forbidden:
- no frontend changes
- no chat CLI
- no runtime behavior beyond policy/trust helpers
- no commits

Return files changed and test output.
```

## Session B3: Chat CLI Worker Prompt

Use GLM 5.1 Precision.

```text
You are Session B: Python/backend worker for ARC Studio v0.1.

Scope: implement minimal `arc-studio` chat-first CLI entrypoint. Keep it honest and local/offline.

Read:
- `docs/research/ARC_STUDIO_UX_SPEC.md` v0.1 CLI sections
- `docs/research/CLI_IDE_REDESIGN_PLAN.md` sections 2.2-2.5
- `docs/wiki/implementation-cockpit/15-implementation-slices.md` Slice 9
- `python/src/agent_runtime_cockpit/cli.py`
- `python/pyproject.toml`

Implement minimal v0.1 shell:
- add script: `arc-studio = "agent_runtime_cockpit.cli_studio:app"`
- create `python/src/agent_runtime_cockpit/cli_studio.py`
- create minimal session store if needed
- no args -> banner + prompt loop
- one arg/message -> one-shot local response or command dispatch, no provider calls
- slash commands:
  - `/help`
  - `/status`
  - `/doctor`
  - `/runs`
  - `/plan`
  - `/build`
  - `/auto`
  - `/exit`
- persist simple session transcript locally
- do not fake agent execution

Tests:
- `python/tests/test_cli_studio.py`
- no-arg banner using CLI runner
- `/help` lists commands
- mode switches update session state
- one-shot mode exits 0

Run:
```bash
cd python && uv run pytest tests/test_cli_studio.py -q
cd python && uv run pytest -q
```

Forbidden:
- no paid/provider calls
- no complex TUI dependency unless already declared
- no frontend changes
- no hidden runtime claims
- no commits

Return files changed and test output.
```

## Session B4: Theia Studio Widget Worker Prompt

Use Qwen 3.6 Max.

```text
You are Session B: Theia/TypeScript worker for ARC Studio v0.1.

Scope: implement the smallest Theia single Studio widget shell. No backend behavior beyond existing ArcService calls.

Read:
- `docs/research/ARC_STUDIO_UX_SPEC.md` IDE sections
- `docs/research/CLI_IDE_REDESIGN_PLAN.md` IDE sections
- `docs/wiki/implementation-cockpit/15-implementation-slices.md` Slice 10
- `packages/arc-extension/src/browser/arc-extension-frontend-module.ts`
- `packages/arc-extension/src/browser/arc-widget.tsx`
- existing widgets/components under `packages/arc-extension/src/browser/`

Implement:
- `packages/arc-extension/src/browser/arc-studio-widget.tsx`
- tabs folder:
  - `tabs/ChatTab.tsx`
  - `tabs/RunsTab.tsx`
  - `tabs/WorkflowsTab.tsx`
  - `tabs/ConfigTab.tsx`
- contribution if needed: `arc-studio-widget-contribution.ts`
- bind `ArcStudioWidget` in frontend module
- keep old widgets available, but make Studio widget the primary/default contribution

Minimum UI:
- Chat tab placeholder with input and mode indicator
- Runs tab placeholder/list shell, no Trace Viewer default
- Workflows tab can reuse detection/list shell
- Config tab placeholder for runtime/mode/trust
- status strip: runtime/model/mode/workspace

Forbidden:
- no Trace Viewer default in Studio widget
- no HotLoop
- no fake live graph claims
- no backend refactor
- no commits

Tests:
- update/add static contract tests under `packages/arc-extension/src/browser/__tests__/`
- assert Studio widget exports/registers
- assert tabs exist
- assert no `TraceViewerSection` import in Studio widget

Run in this order:
```bash
pnpm --filter arc-extension build
pnpm --filter arc-extension test
```

Return files changed and exact test/build output.
```

## Session B5: Runs Tab Receipts/Autopsies Worker Prompt

Use Qwen 3.6 Max for TS, GLM 5.1 Precision if backend methods are needed.

```text
You are Session B: ARC Studio Runs tab worker.

Scope: wire existing cockpit cards into Runs tab with minimal service methods. Do not implement Trace UI.

Read:
- `docs/wiki/implementation-cockpit/08-run-receipt.md`
- `docs/wiki/implementation-cockpit/09-failure-autopsy.md`
- `docs/wiki/implementation-cockpit/10-evidence-refs.md`
- `packages/arc-extension/src/browser/components/RunReceiptCard.tsx`
- `packages/arc-extension/src/browser/components/FailureAutopsyCard.tsx`
- `packages/arc-extension/src/browser/components/RunContractCard.tsx`
- `packages/arc-extension/src/common/arc-protocol.ts`
- `packages/arc-extension/src/node/arc-backend-service.ts`

Implement minimum:
- Runs tab lists runs
- selected run can load/render:
  - receipt card
  - failure autopsy card if failed
  - contract card if available
- add ArcService methods only if needed:
  - `getRunReceipt(runId)`
  - `getRunAutopsy(runId)`
  - `getRunContract(runId)`
- graceful empty/missing states
- no event JSON viewer

Tests:
- protocol method source tests
- backend service source/unit tests if methods added
- RunsTab static tests assert cards are used

Run:
```bash
pnpm --filter arc-extension build
pnpm --filter arc-extension test
```

If Python daemon route changes are needed, stop and ask Session A before editing backend.

Return files changed and test output.
```

## Session B6: Config Tab Worker Prompt

Use Qwen 3.6 Max.

```text
You are Session B: ARC Studio Config tab worker.

Scope: minimal v0.1 config UI. No secret rendering.

Read:
- `docs/research/ARC_STUDIO_UX_SPEC.md` config/provider/trust sections
- `python/src/agent_runtime_cockpit/config/model.py`
- `packages/arc-extension/src/common/arc-protocol.ts`
- `packages/arc-extension/src/node/arc-backend-service.ts`
- current `ConfigTab.tsx` if present

Implement:
- Config tab displays runtime, mode, workspace, trust state, provider key status
- save safe config fields only
- secrets are shown only as source/status, never raw value
- env override labels visible
- graceful unavailable backend state

Tests:
- static tests: no `api_key` raw value rendering patterns
- mode/routing fields present
- config save method exists if added

Run:
```bash
pnpm --filter arc-extension build
pnpm --filter arc-extension test
```

Forbidden:
- no provider calls
- no key entry storage unless already available and tested
- no HotLoop/Trace UI
- no commits

Return files changed and test output.
```

## Session B7: Cross-Linking Worker Prompt

Use GLM 5.1 Precision for backend; Qwen 3.6 Max for Theia.

```text
You are Session B: cross-linking worker.

Scope: make existing CrossLinker visible to Graph/Chat/Runs without broad redesign.

Read:
- `python/src/agent_runtime_cockpit/orchestration/cross_linker.py`
- `python/src/agent_runtime_cockpit/web/routes.py` run links endpoint
- `packages/arc-extension/src/common/arc-protocol.ts` CrossLinkState
- `packages/arc-extension/src/browser/arc-workflow-graph-widget.tsx`
- `packages/arc-extension/src/browser/components/EvidenceChip.tsx`

Implement minimal:
- expose run links through ArcService if not already exposed
- selecting a graph node updates CrossLinkState
- opening EvidenceChip emits structured selection event or callback with `EvidenceRef`
- missing IDs show degraded/empty state, not crash

Tests:
- Python route tests already exist; extend only if needed
- TS static tests for CrossLinkState consumption and EvidenceChip callback path

Run:
```bash
cd python && uv run pytest tests/web/test_runs_endpoints.py tests/orchestration/test_cross_linker.py -q
pnpm --filter arc-extension build
pnpm --filter arc-extension test
```

Forbidden:
- no Trace UI default
- no replay scrubber
- no HotLoop
- no commits

Return files changed and test output.
```

## Session B8: Capability Diff UI Worker Prompt

Use GLM 5.1 Precision for backend; Qwen 3.6 Max for Theia.

```text
You are Session B: runtime capability diff UI worker.

Scope: show capability/trust diff on runtime switch.

Read:
- `python/src/agent_runtime_cockpit/protocol/capability_snapshot.py`
- `python/src/agent_runtime_cockpit/orchestration/capability_negotiation.py`
- `python/src/agent_runtime_cockpit/protocol/trust_diff.py`
- `packages/arc-extension/src/common/arc-protocol.ts`
- runtime/adapters widgets in `packages/arc-extension/src/browser/`

Implement minimal:
- backend/service method returns capability diff for current runtime -> target runtime
- frontend shows added/removed capabilities
- if trust boundary widens, require explicit confirmation UI state
- no fake claims: unknown capabilities render unknown/degraded

Tests:
- Python capability diff tests if backend added
- TS static tests for diff render and confirmation requirement

Run:
```bash
cd python && uv run pytest tests/orchestration/test_capability_negotiation.py tests/test_capability_snapshot.py -q
pnpm --filter arc-extension build
pnpm --filter arc-extension test
```

Forbidden:
- no provider calls
- no runtime execution
- no commits

Return files changed and test output.
```

## Session B9: Hide Default Trace UI Worker Prompt

Use Qwen 3.6 Max.

```text
You are Session B: Theia default-surface cleanup worker.

Scope: align v0.1 UX: no default Trace UI. Keep advanced/dev trace widgets available if needed.

Read:
- `docs/research/ARC_STUDIO_UX_SPEC.md` out-of-scope Trace UI lines
- `packages/arc-extension/src/browser/arc-extension-frontend-module.ts`
- `packages/arc-extension/src/browser/arc-widget.tsx`
- `packages/arc-extension/src/browser/components/TraceViewerSection.tsx`
- `packages/arc-extension/src/browser/arc-run-timeline-widget.tsx`
- `packages/arc-extension/src/browser/arc-event-stream-widget.tsx`

Implement minimal:
- Studio widget does not import/render TraceViewerSection
- trace/timeline/event stream contributions are not default-opened/default-promoted
- keep advanced command/contribution available if explicitly invoked, unless Session A says remove
- copy says advanced trace, not default cockpit

Tests:
- static tests assert no `TraceViewerSection` in `ArcStudioWidget`
- tests assert advanced trace widgets still export/build if retained

Run:
```bash
pnpm --filter arc-extension build
pnpm --filter arc-extension test
```

Forbidden:
- no backend edits
- no deleting trace code unless explicitly approved
- no commits

Return files changed and test output.
```

## Session C: Reviewer Prompt

Use DeepSeek v4 Pro Precision.

```text
You are Session C: reviewer only. Do not edit files.

Review the current diff for ARC Studio v0.1 remaining implementation.

Focus:
- correctness bugs
- test gaps
- scope drift
- overclaims
- security/privacy regressions
- frontend a11y/UX regressions
- dirty worktree/staging risk

Read relevant plan docs:
- `docs/wiki/implementation-cockpit/remaining-plan-sessions.md`
- `docs/wiki/implementation-cockpit/15-implementation-slices.md`
- `docs/research/ARC_STUDIO_UX_SPEC.md`
- `docs/research/CLI_IDE_REDESIGN_PLAN.md`

Check changed files only plus adjacent contracts.

Output format:
- HIGH / MEDIUM / LOW findings
- file:line refs
- why it matters
- smallest fix
- suggested test
- final verdict: mergeable / not mergeable

Do not implement. Do not commit.
```

## Final Release Gate Prompt

Use Session A after all slices are complete:

```text
Run final ARC Studio v0.1 cockpit verification.

Commands:
```bash
cd python && uv run pytest -q
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
pnpm --filter arc-extension test
```

Then audit claims:
- no default Trace UI claim/surface
- no HotLoop claim/surface
- no fake provider/live-call claims
- `arc-studio` exists if docs claim it
- receipts/autopsies/contracts render or are not claimed in UI
- TrustDiff/policy behavior matches docs

Return:
- verdict
- exact command results
- remaining blockers
- exact files to stage if committing
```
