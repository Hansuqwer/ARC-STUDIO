# Phase 42 Completion Prompt

You are a senior autonomous software engineering orchestrator working in this repo.

Goal: complete the remaining Phase 42 interactive CLI/REPL UX work after Phase 42.1-42.3 P0 landed.

Current completed foundation:
- Phase 42.1 P0: explicit no-shell REPL pipelines for `|`, `&&`, `||`.
- Phase 42.2 P0: `/dashboard` and `arc dashboard` using real local status producers.
- Phase 42.3 P0: `/alias list|show|set|remove|run` with visible expansion and recursion guard.

Target scope:

1. Phase 42.4 Batch Mode
- Add deterministic batch command files.
- Reuse the explicit Phase 42 parser.
- Do not invoke a shell.
- Support fail-fast and continue-on-error modes.
- Require explicit approval policy for batch execution.
- Show alias expansion before execution.
- Ensure dangerous expanded commands still hit sandbox/policy gates.
- Add tests for parse errors, ordering, denied commands, fail-fast, continue mode, and no-shell behavior.

2. Phase 42.5 Session Export/Import + IDE Connection
- Add session export/import bundles with schema/version metadata.
- Preserve session state, history, runtime mode, profile, isolation, tools config, and timestamps.
- Validate imports before writing.
- Reject malformed/unsafe bundles.
- Do not include secrets.
- Implement only local/read-only IDE session bridge pieces if protocol and locking are clear.
- Do not claim daemon, shared-server, remote sync, or tenant support unless fully implemented and tested.

3. Phase 42 Closure / Acceptance Hardening
- Add alias scope flags if still missing: `--user`, `--workspace`.
- Add atomic alias/session writes where feasible.
- Improve dashboard output using existing Rich/table conventions without inventing data.
- Harden pipe semantics with adapter-specific contracts only where safe.
- Update docs/roadmap/phases only when status genuinely changes.
- Produce Phase 42 acceptance report.

Hard constraints:
- Do not fake progress.
- Do not claim validation passed unless executed.
- Do not broaden sandbox capabilities.
- Do not enable public microVM execution.
- Do not bypass policy, audit, approval, or sandbox boundaries.
- Do not use destructive git commands without explicit approval.
- Do not modify unrelated user changes.

Operating model:
- Use an orchestrator-led workflow with up to 6 subagents when useful.
- If subagents are unavailable, simulate structured workstreams.
- Inspect repo state before edits.
- Print a concise plan and exact file scope before coding.
- Proceed after printing the file scope unless materially blocked.

Validation:
- Run discovered applicable checks.
- Prefer:
  - `cd python && uv run ruff check src tests`
  - `cd python && uv run pytest tests/ -q`
  - `pnpm typecheck`
  - `pnpm build`
- If a check fails, fix targeted issues and rerun failed checks plus relevant full checks.
- Do not skip hooks/tests or weaken assertions.

Commit and push:
- Commit only after validation passes.
- Commit only relevant files.
- Do not commit generated `.arc/*.db`, secrets, lockfiles, or unrelated dirty files.
- Use conventional commit style, e.g. `feat(cli): complete Phase 42 batch and session UX`.
- Push current branch after commit.

Final response format:

Summary
- Completed objective:
- Implemented features:
- Architecture impact:

Phase 42.4 Batch Mode
- Implemented:
- Safety behavior:
- Tests:

Phase 42.5 Session Export/Import + IDE Connection
- Implemented:
- Protocol/locking status:
- Tests:

Phase 42 Closure
- Hardened:
- Docs updated:
- Deferred:

Validation Results
- lint:
- typecheck:
- tests:
- build/package:
- E2E:

Commit Information
- Commit:
- Message:
- Branch:
- Push status:

Remaining Risks
- Known limitations:
- Next recommended phase:
