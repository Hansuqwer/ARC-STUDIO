# CLI Parity Priority Research Prompt

Use this prompt before implementing the next Priority 1 CLI parity phases.

```text
You are taking over ARC Studio as senior autonomous engineering orchestrator.

Repo:
https://github.com/Hansuqwer/arc-theia-studio

Branch:
<BRANCH>

Priority 1 goal:
Research, plan, implement, test, and document the next ARC CLI parity track. The target is full OpenCode/Claude Code style parity, but do not claim parity until every required behavior exists and tests prove it.

Required outcomes to research and sequence:
1. Full OpenCode/Claude Code parity.
2. Autonomous edit -> test -> repair loop.
3. Git-backed undo/redo transactions.
4. Rich IDE diff review/apply flow.
5. Real microVM execution.
6. Strict macOS no-network VM proof.
7. Firecracker real boot/run/destroy proof.
8. Full provider-backed runtime shell.
9. Complete live terminal/event streaming UX.
10. Broad CI orchestration inside CLI.

Research gate before coding:
1. Context7 docs:
   - Typer/Rich/Textual CLI subcommand, prompt, terminal UI, test patterns.
   - GitPython/Dulwich or subprocess git transaction/restore patterns.
   - Python asyncio/subprocess/process-group timeout and streaming patterns.
   - Pydantic model/config patterns for durable CLI state.
   - Theia/Monaco diff editor integration if available.
2. Vercel Grep/code search:
   - OpenCode/Claude Code style command palette, tool loop, approval UX, undo, and diff review patterns.
   - Autonomous edit/test/repair loop implementations with bounded retry and audit trails.
   - CLI live terminal/event streaming implementations.
   - Provider-backed runtime shell and tool-call orchestration patterns.
   - Firecracker/Lima/Cloud Hypervisor wrapper patterns that boot, mount workspace, run argv, collect logs, destroy VM.
   - CI orchestration command UX that runs matrices, captures artifacts, and summarizes failures.
3. Latest official docs/web sources:
   - OpenCode CLI current architecture/features.
   - Claude Code current CLI/tool/approval/diff/session behavior.
   - Lima/Apple Virtualization.framework current networking/mount/VM lifecycle constraints on macOS.
   - Firecracker current KVM/rootfs/network/jailer/API requirements and limitations.
   - Cloud Hypervisor lightweight local VM usage and constraints.
   - macOS packet filter/VM network-disable proof options.
   - Git worktree/restore/stash/reflog docs for undo/redo safety.
   - GitHub Actions/local CI docs relevant to CLI orchestration.

Record research in `docs/research/cli-parity-priority.md` before or with implementation. Each note must include:
- Source.
- Link/query.
- What was learned.
- Implementation consequence.
- Confidence.
- Unresolved questions.

Decision table required:
| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|

Repo pre-flight:
1. Read `docs/roadmap.md`, `docs/phases.md`, `docs/research/sandbox-and-microvm.md`, relevant `docs/research/*.md`, and relevant `docs/adr/*`.
2. Inspect current CLI, REPL, edit loop, sandbox, microVM, terminal/event streaming, IDE diff/review, provider, CI, and git-related code/tests.
3. Inspect worktree and preserve unrelated changes.

Implementation order:
1. Phase 97: research synthesis + acceptance matrix for CLI parity track.
2. Phase 98: autonomous edit -> test -> repair loop, bounded/offline by default.
3. Phase 99: git-backed undo/redo transactions around edit/apply/test operations.
4. Phase 100: rich IDE diff review/apply flow backed by real patch content and approval gates.
5. Phase 101: provider-backed runtime shell contract and gated implementation path.
6. Phase 102: live terminal/event streaming UX end-to-end.
7. Phase 103: broad CLI CI orchestration.
8. Phase 104: real macOS microVM execution proof with strict no-network evidence, if feasible.
9. Phase 105: real Linux Firecracker boot/run/destroy proof, if feasible.

Hard truth rules:
- Do not fake completion.
- Do not claim full OpenCode/Claude Code parity until the acceptance matrix is green.
- Do not claim autonomous repair until the CLI actually edits, tests, diagnoses, repairs, and stops under bounded retry with audit evidence.
- Do not claim git undo/redo until real repository transactions restore files safely and tests prove dirty-worktree handling.
- Do not claim rich IDE diff review/apply until the IDE renders real diffs and applies reviewed content through existing gates.
- Do not claim microVM execution until commands really run inside disposable VMs and tests or opt-in proof artifacts show create/run/collect/destroy.
- Do not claim strict macOS no-network VM proof unless a positive command succeeds, network egress fails for the right reason, and proof artifacts show network disabled rather than missing tooling.
- Do not claim Firecracker proof unless the harness boots a guest, mounts/controls workspace, runs argv, collects stdout/stderr/exit code, then destroys the VM.
- Do not broaden provider/network/destructive execution without explicit gates.
- Keep container fallback labeled as gated fallback only unless Docker/Podman provider path is explicitly enabled.

Required acceptance matrix categories:
| Capability | Required proof | Status | Evidence | Gaps |
|---|---|---|---|---|
| OpenCode/Claude Code parity | Feature-by-feature checklist vs current docs | Not Started | TBD | TBD |
| Edit -> test -> repair | Bounded loop, fail/repair/pass cases, audit | Not Started | TBD | TBD |
| Git undo/redo | Transaction log, restore, dirty-worktree tests | Not Started | TBD | TBD |
| IDE diff review/apply | Real diff UI, approve/apply/deny tests | Not Started | TBD | TBD |
| Provider-backed shell | Gated runtime, tool calls, streaming, audit | Not Started | TBD | TBD |
| Live terminal/event UX | Incremental stdout/stderr/events/cancel | Not Started | TBD | TBD |
| CLI CI orchestration | Detect/run matrix, artifacts, summaries | Not Started | TBD | TBD |
| macOS microVM | Lima/VZ run + strict no-network proof | Not Started | TBD | TBD |
| Linux Firecracker | Boot/run/destroy proof | Not Started | TBD | TBD |

Validation baseline:
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm build
pnpm typecheck
bash scripts/check-banned-claims.sh docs/agents.md docs/roadmap.md docs/phases.md docs/release/checklist.md docs/REALITY_AUDIT.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md README.md

When IDE/browser touched:
pnpm test:e2e

When real microVM proof is attempted:
- Keep default CI skipped unless runtime exists and explicit opt-in env is set.
- Capture proof artifacts under a documented local-only path.
- Report host OS, runtime version, command, network proof, mount proof, cleanup proof.

Final report:
Files changed:
- <path>: <summary>

Commands run:
- <cmd> -> pass/fail/blocked

Priority 1 matrix:
| Capability | Result | Evidence | Remaining risk |
|---|---|---|---|

Research gate:
| Source | Result | Notes |
|---|---|---|

What is real:
- <implemented + tested>

Design-only / preflight-only / gated-only:
- <honest limits>

Blocked:
- <exact blocker or none>

Next PR queue:
1. <next concrete item>
2. <next concrete item>
```
