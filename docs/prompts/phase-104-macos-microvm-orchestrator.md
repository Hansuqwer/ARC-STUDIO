# Phase 104 macOS MicroVM Orchestrator Prompt

Use this prompt to run Phase 104 with research, implementation, verification, commit, push, and e2e gates.

```text
Implement ARC Studio Phase 104 / R75: macOS lightweight VM proof, without overclaiming.

Research first. Required sources:
- Context7 docs if available: Lima, Apple Virtualization.framework, Python subprocess, Typer testing, Pydantic models.
- Vercel Grep/code search if available: Lima wrappers, Apple VZ wrappers, no-network VM proofs, command approval UX, sandbox policy examples.
- Latest official docs/web: Lima network/mount/VZ/create/start/shell/delete docs, Apple Virtualization.framework docs, Lima source/default templates if needed.

If Context7 or Vercel Grep are unavailable in the runtime, record exact blocker in docs. Do not silently skip.

Act as orchestrator. Spawn up to 8 subagents in parallel where useful:
1. Lima networking/no-network feasibility researcher.
2. Lima VZ/mount/symlink researcher.
3. Apple Virtualization.framework feasibility researcher.
4. Existing repo microVM code/test inspector.
5. Existing docs/ADR truth-constraints inspector.
6. Test-strategy designer for normal CI skips and opt-in host proofs.
7. Implementation reviewer for claim-safety/security regressions.
8. Verification/log summarizer.

Execution rules:
- Public `MicroVMIsolationProvider.execute()` must remain blocked unless ADR-024 P1-P7 are actually satisfied by real tests.
- Do not wire `ARC_MICROVM_EXEC_ENABLED` unless P1-P7 are satisfied.
- Do not claim strict macOS microVM no-network if Lima still has default user-mode/slirp networking.
- If strict no-network is infeasible, land only blocker-safe code/docs/tests: doctor/preflight truth fields, hardened Lima template, host-gated proof tests, and research notes.
- Preserve container fallback gating.
- Preserve alpha/mock/fallback labeling.

Implementation target if feasible:
- Disposable Lima/VZ lifecycle: create/start/run/collect/delete.
- Workspace mounted only at `/workspace` via VZ/virtiofs.
- Network disabled by default with structural proof before user argv.
- Symlink escape proof.
- Opt-in tests skipped in normal CI.

Fallback if not feasible:
- Record blockers with sources.
- Keep public execution blocked.
- Improve `arc sandbox doctor --json` macOS truth fields.
- Harden generated Lima template for proof-only use.
- Add/keep host-gated Lima proof tests.
- Mark R75/Phase 104 Blocked, not complete.

Verification:
- `cd python && uv run ruff check src tests`
- `cd python && uv run pytest tests/ -q`
- `pnpm build`
- `pnpm typecheck`
- `pnpm test:e2e`
- `bash scripts/check-banned-claims.sh docs/agents.md docs/roadmap.md docs/phases.md docs/release/checklist.md docs/REALITY_AUDIT.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md README.md`

If requested to commit/push:
- Inspect `git status --short`, `git diff`, and `git log --oneline -10` before commit.
- Stage only intended files.
- Do not stage unrelated dirty work.
- Commit with concise repo-style message.
- Push current branch.
- Report exact pass/fail matrix, what is real, what is proof-only, what remains blocked.
```
