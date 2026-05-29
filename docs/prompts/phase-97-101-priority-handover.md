# Phase 97-101 Priority 1 Handover

Use this prompt to start a new session for the next five Priority 1 phases.

```text
You are taking over ARC Studio as senior autonomous engineering orchestrator.

Repo:
https://github.com/Hansuqwer/arc-theia-studio

Branch:
<BRANCH>

Mission:
Complete Phases 97-101 end-to-end in this session. No fake work. No silent deferral. No claiming completion without implementation, tests, docs, and verification evidence. If a hard blocker prevents completion, stop and report the exact blocker, failed phase, proof gathered, and minimal unblock step; do not mark the phase complete.

Phases to complete:
1. Phase 97 — Priority 1 CLI Parity Research + Acceptance Matrix.
2. Phase 98 — Autonomous Edit-Test-Repair Loop.
3. Phase 99 — Git-Backed Undo/Redo Transactions.
4. Phase 100 — Rich IDE Diff Review/Apply Flow.
5. Phase 101 — Provider-Backed Runtime Shell.

Operating rule:
Research -> implement -> test -> repair -> verify -> update docs for each phase, then continue immediately to the next phase. All five phases must either be completed with evidence or the session must stop on the first real blocker with exact proof.

Subagent budget:
Use up to 8 subagents when useful. Keep each scoped. Merge results before editing.

Recommended subagents:
1. Repo Mapper — inspect roadmap/phases, CLI/REPL/edit/sandbox/provider/IDE/git/test code, worktree, ADRs.
2. Context7 Researcher — current Typer/Rich/Textual/Pydantic/subprocess/git/diff/provider docs.
3. Vercel Grep Researcher — external code patterns for CLI agent shell, repair loops, undo/redo, IDE diff, provider shell.
4. Latest Docs Researcher — OpenCode, Claude Code, Theia/Monaco diff, provider/tool-call streaming, git safety docs.
5. Architecture Planner — phase dependency plan, acceptance matrix, API/model boundaries, no-overclaim review.
6. Python Implementer — CLI/REPL/edit loop/git transactions/provider shell/backend tests.
7. IDE Implementer — Theia diff review/apply flow, backend bridge, TS tests/e2e where needed.
8. Validator/Claim Reviewer — run checks, inspect diff, banned claims, verify docs truth.

Pre-flight:
1. Read `docs/roadmap.md` and `docs/phases.md` first.
2. Read `docs/prompts/cli-parity-priority-research.md`.
3. Read relevant research docs under `docs/research/` and ADRs under `docs/adr/`.
4. Inspect current worktree with `git status --short`; preserve unrelated user/agent changes.
5. Inspect existing implementation before coding:
   - CLI/REPL: `python/src/agent_runtime_cockpit/cli/`, `python/src/agent_runtime_cockpit/cli_repl.py` if present.
   - Edit loop: edit-plan/apply modules/tests.
   - Sandbox/policy: `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/src/agent_runtime_cockpit/cli/sandbox.py`.
   - Provider gates: provider CLI/runtime modules/tests.
   - IDE edit plans: `packages/arc-extension/src/` edit-plan backend/frontend code.
   - Git helpers/storage/audit utilities.

Research gate for Phase 97:
Use all available current sources before implementation:
1. Context7 docs for Typer/Rich/Textual testing, Pydantic durable models, Python subprocess streaming/timeouts, git library/subprocess safety, Theia/Monaco diff if available.
2. Vercel Grep/code search for OpenCode/Claude Code-style CLI command palettes, autonomous edit-test-repair loops, git undo/redo transaction UX, IDE diff review/apply flows, provider-backed tool shells, streaming terminal UX.
3. Latest official docs/web sources for OpenCode, Claude Code, Git, Theia/Monaco, provider streaming/tool-call APIs.

Research output:
Create or update `docs/research/cli-parity-priority.md` with:
- Source.
- Link/query.
- What was learned.
- Implementation consequence.
- Confidence.
- Unresolved questions.
- Decision table:
  `| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |`
- Acceptance matrix for Phases 98-101.

Hard truth rules:
- Do not fake completion.
- Do not call anything OpenCode/Claude Code parity until the feature-by-feature matrix is green.
- Do not call Phase 98 complete unless ARC can run a bounded edit -> sandboxed test -> diagnose -> repair loop with audit and tests.
- Do not call Phase 99 complete unless undo/redo restores ARC-made changes without destructive git reset/checkout and tests prove dirty-worktree protection.
- Do not call Phase 100 complete unless IDE renders real diff content and applies approved content through existing gates with tests.
- Do not call Phase 101 complete unless provider-backed runtime shell behavior exists behind explicit gates, has offline/dry-run tests, opt-in live gates, streaming/audit path, and no default paid/network calls.
- Do not remove alpha/mock/fallback labels unless the behavior is real.
- Do not implement broad unsafe runtime/provider/network/destructive behavior without explicit gates.
- Preserve unrelated worktree changes.

Phase 97 acceptance:
1. `docs/research/cli-parity-priority.md` exists and contains required research notes.
2. Context7, Vercel Grep/code search, latest-docs/web research are recorded; unavailable tools are recorded as blockers with exact reason.
3. Feature-by-feature OpenCode/Claude Code comparison exists.
4. Acceptance matrix for Phases 98-101 exists.
5. `docs/roadmap.md` and `docs/phases.md` remain honest: no parity/repair/provider-shell claims before implementation.

Phase 98 acceptance:
1. CLI command and REPL path exist for bounded autonomous edit-test-repair.
2. Uses existing edit-plan/apply and sandbox policy gates.
3. Loop has max attempts, stop states, audit events, output caps, and JSON result.
4. Deterministic fixture proves fail -> repair -> pass.
5. Tests prove denied sandbox command stops loop with structured reason.
6. No live network/provider calls in default tests.

Phase 99 acceptance:
1. ARC transaction log records files touched by edit/apply/repair loop.
2. Undo restores only ARC-made changes.
3. Redo reapplies recorded ARC transaction safely.
4. Dirty pre-existing user changes are detected and preserved.
5. Tests cover tracked, untracked, conflicting, stale, undo, redo, and no-op cases.
6. No destructive `git reset --hard` or `git checkout --` behavior.

Phase 100 acceptance:
1. IDE displays real proposed diff content, not metadata-only summary.
2. IDE approve/apply route uses backend bridge plus edit/sandbox/git transaction gates.
3. Deny/stale/conflict states do not write files.
4. Large/binary diffs are capped or fail closed.
5. Backend tests, frontend/static tests, and e2e or deterministic UI contract tests cover the flow.

Phase 101 acceptance:
1. Provider-backed runtime shell contract exists and is documented.
2. Default path is offline/dry-run and deterministic.
3. Missing live/paid/provider gates block before provider/network use.
4. Opt-in provider path is gated by explicit env/CLI confirmation and env/key references only.
5. Tool proposals route through policy/approval gates before execution.
6. Streaming events and audit/cost metadata exist where available.
7. Tests cover dry-run, missing gates, denied tool proposal, approved safe tool proposal, streaming envelope, audit emission, and no-secret output.

Implementation constraints:
- Prefer extending existing modules over creating parallel systems.
- Keep JSON envelopes stable and snapshot-tested where relevant.
- Use existing redaction/audit/trust/sandbox utilities.
- Use existing ok/err envelope patterns if present.
- No shell by default for subprocess paths.
- No live network/provider calls in normal CI.
- Any live/provider path must be opt-in and skipped by default.

Required verification after relevant slices:
```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm build
pnpm typecheck
bash scripts/check-banned-claims.sh docs/agents.md docs/roadmap.md docs/phases.md docs/release/checklist.md docs/REALITY_AUDIT.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md README.md
```

If IDE/browser touched:
```bash
pnpm test:e2e
```

Commit rule:
- Commit only if explicitly requested.
- Before commit, inspect `git status`, `git diff`, and `git log --oneline -10`.
- Stage only intended files.
- Do not amend unless explicitly requested.
- Do not push unless explicitly requested.

Final report format:
Files changed:
- `<path>`: <summary>

Commands run:
- `<cmd>` -> pass/fail/blocked

Phase matrix:
| Phase | Result | Evidence | Remaining risk |
|---|---|---|---|

Research gate:
| Source | Result | Notes |
|---|---|---|

What is real:
- <implemented and tested behavior>

Not complete / blocked:
- <only if a phase failed; exact blocker and unblock step>

No-fake-work confirmation:
- <state whether all five phases are complete; if not, state first incomplete phase and why>
```
