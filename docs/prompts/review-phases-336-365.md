# Review Prompt — Phases 336–365 Implementation Audit

You are reviewing the ARC Studio implementation claimed for Phases 336–365. Treat every claim as untrusted until verified against the repo, git history, tests, docs, and diffs.

## Goal

Perform a comprehensive code review of the 30-phase implementation track from Phase 336 through Phase 365. Identify correctness bugs, security gaps, DoD evidence gaps, regressions, overclaims, missing tests, docs inconsistencies, and any mismatch between the execution prompt and the actual repository state.

Do not rubber-stamp. Findings first. If you fix issues, use `apply_patch` only, keep changes minimal, rerun affected tests, and report exact evidence.

## Required Tools

Use these tools explicitly during review:

- `Context7`: Resolve and query docs for external libraries touched by the diffs. Use pinned versions where possible from `python/uv.lock`, `python/pyproject.toml`, `package.json`, or `pnpm-lock.yaml`. Max 3 Context7 queries total.
- Local `Grep` / `Glob`: Search repo paths, symbols, CLI commands, tests, docs status rows, and phase ledger entries. Prefer these over shell grep/find.
- GitHub code grep (`grep_searchGitHub`): Search real-world usage patterns for at least 2 relevant implementation areas, such as Typer confirmation gates, Pydantic envelopes, Theia widget ARIA patterns, aiohttp connector pool stats, mmap thresholds, or CLI JSON error envelopes.
- `webfetch`: Fetch at least 1 authoritative external spec/page relevant to changed behavior. Good candidates: Debug Adapter Protocol, WAI-ARIA authoring guidance, Python `mmap`, Typer docs, SQLite FTS5, aiohttp connector docs.
- Vercel tools only if the review touches Vercel deployment/build/runtime behavior. Otherwise state: `Vercel tools not applicable; repo has no Vercel deployment issue in this review.`
- `apply_patch`: Required for any manual file edit. Do not use shell redirection, Python write scripts, or ad-hoc file rewriting.

If any research tool fails or returns irrelevant results, record: `no usable results — proceeding on repo conventions`.

## Source Of Truth

Read these first:

- `AGENTS.md`
- `docs/roadmap.md`
- `docs/phases.md`
- `docs/prompts/execute-phases-336-365-v2.md`
- `docs/prompts/comprehensive-session-review-phases-336-344.md` if present

Repo state wins over prompts and summaries. If a prompt says 30 phases were completed but `docs/phases.md` or git history only proves fewer, report that as a finding. Do not infer missing commits.

## Initial Re-Anchor

Run and record:

```bash
git rev-parse --abbrev-ref HEAD
git status --porcelain
git log --oneline -40
git diff --stat dc2dd819..HEAD || true
git diff --name-only dc2dd819..HEAD || true
```

Then verify phase ledger coverage:

```bash
grep -n "^## Phase 3\(3[6-9]\|[4-5][0-9]\|6[0-5]\)" docs/phases.md
```

If the base SHA `dc2dd819` does not exist, find the actual pre-phase base from the execution prompt, git merge-base, or the earliest phase commit. State what anchor you used.

## Phase Map To Review

Review all phases 336–365. For each phase, compare planned work from `docs/prompts/execute-phases-336-365-v2.md` against actual code, tests, docs, and commits.

| Phase | Track | Expected Area |
|---|---|---|
| 336 | R94 Advisor | Advisor error handling, JSON envelopes, empty/degraded states, tests |
| 337 | R95 Dashboard | Theia dashboard UX states, ARIA roles/labels, keyboard reachability, TS tests |
| 338 | R96 Voice | Voice error/degraded state, optional Whisper behavior, CLI envelopes, tests |
| 339 | R97 Policies | Policy templates, deterministic errors, `template-apply --yes`, security tests, scoped mypy |
| 340 | R98 Composer | Composer errors, invalid graph handling, overwrite `--yes`, CLI tests |
| 341 | R99 Debug | Debug errors, state enum, loopback defaults, unreachable/degraded states, DAP behavior |
| 342 | R100 Notebook | Notebook errors, export validation, schema/version behavior, overwrite `--yes` |
| 343 | R101 Time Travel | Time-travel errors, end-of-session state, branch confirmation, empty session |
| 344 | R102 Migrate | Migration errors, dry-run, actual migration `--yes`, strict validation |
| 345 | R83 Predict | Explicit file/line errors, degraded state, JSON output, research-grade labeling |
| 346 | R84 Index | Index errors/results, empty workspace, unbuilt index degraded search, FTS tests |
| 347 | R85 Context | `list`/`clear`, `--yes`, unbuilt index degraded state, empty context |
| 348 | R90 Memory | `list`/`clear`, `--yes`, key-not-found/empty memory states |
| 349 | R-PERF7 | Incremental index result schema, batch cap, timeout, tests |
| 350 | R-SEC2 | PromptGuard batch scan, `to_dict`, CLI scan command, deterministic security |
| 351 | R-SEC3 | SBOM integrity exit codes, `--strict`, CI warning step, tests |
| 352 | R-PERF6 | mmap trace result, threshold constant/env override, small/large tests |
| 353 | R-PERF8 | Provider pool constant, pool stats schema, aiohttp reuse behavior |
| 354 | R-PERF9 | WASM parser config, benchmark result, optional wasmtime, honest research label |
| 355 | R-PROC1 | Release intelligence error/degraded git behavior, markdown output, CLI |
| 356 | R-PROC2 | Snapshot error, immutability error, release snapshot CLI, tests |
| 357 | Cross-cutting | CLI parity audit for missing `list`/`clear` |
| 358 | Cross-cutting | `--json` envelope audit across new modules |
| 359 | Cross-cutting | Mutating command confirmation-gate audit |
| 360 | Cross-cutting | Bounded in-memory buffers and warning behavior |
| 361 | Cross-cutting | Timeouts/cancellation for long-running paths |
| 362 | Cross-cutting | Ruff/type annotation/mypy sweep |
| 363 | Docs | `docs/roadmap.md`, `docs/phases.md`, `AGENTS.md` sweep |
| 364 | Release gate | Full verification evidence |
| 365 | Process | Release snapshot generation/evidence |

## Files To Enumerate

Generate the touched-file list from git, not from memory:

```bash
git diff --name-only <base>..HEAD
git log --oneline <base>..HEAD --name-status
```

Also inspect these likely files if present:

- `docs/roadmap.md`
- `docs/phases.md`
- `AGENTS.md`
- `python/src/agent_runtime_cockpit/advisor/__init__.py`
- `python/src/agent_runtime_cockpit/cli/advisor.py`
- `python/tests/advisor/test_advisor_r94.py`
- `packages/arc-extension/src/browser/arc-dashboard-widget.tsx`
- `packages/arc-extension/src/browser/__tests__/arc-dashboard-widget.test.tsx`
- `python/src/agent_runtime_cockpit/voice/__init__.py`
- `python/src/agent_runtime_cockpit/cli/voice.py`
- `python/tests/voice/test_voice_r96.py`
- `python/src/agent_runtime_cockpit/security/policy_templates/__init__.py`
- `python/src/agent_runtime_cockpit/cli/sandbox.py`
- `python/tests/security/policy_templates/test_policy_templates_r97.py`
- `python/src/agent_runtime_cockpit/composer/__init__.py`
- `python/src/agent_runtime_cockpit/cli/composer.py`
- `python/tests/composer/test_composer_r98.py`
- `python/src/agent_runtime_cockpit/debug/__init__.py`
- `python/src/agent_runtime_cockpit/cli/debug.py`
- `python/tests/debug/test_debug_r99.py`
- `python/src/agent_runtime_cockpit/notebook/__init__.py`
- `python/src/agent_runtime_cockpit/cli/notebook.py`
- `python/tests/notebook/test_notebook_r100.py`
- `python/src/agent_runtime_cockpit/time_travel/__init__.py`
- `python/src/agent_runtime_cockpit/cli/time_travel.py`
- `python/tests/time_travel/test_time_travel_r101.py`
- `python/src/agent_runtime_cockpit/migrate/__init__.py`
- `python/src/agent_runtime_cockpit/cli/migrate.py`
- `python/tests/migrate/test_migrate_r102.py`
- `python/src/agent_runtime_cockpit/cli/predict_cmd.py`
- `python/tests/test_predict_r83.py`
- `python/src/agent_runtime_cockpit/index/__init__.py`
- `python/src/agent_runtime_cockpit/cli/index_cmd.py`
- `python/tests/test_index_r84.py`
- `python/src/agent_runtime_cockpit/cli/context_cmd.py`
- `python/tests/test_context_r85.py`
- `python/src/agent_runtime_cockpit/cli/memory_cmd.py`
- `python/tests/test_memory_r90.py`
- `python/tests/index/test_incremental_index_r_perf7.py`
- `python/src/agent_runtime_cockpit/security/prompt_guard.py`
- `python/tests/security/test_prompt_guard.py`
- `scripts/check-sbom-integrity.sh`
- `.github/workflows/python.yml`
- `python/src/agent_runtime_cockpit/orchestration/event_broker.py`
- `python/tests/test_perf_r85_r86_r87.py`
- `python/src/agent_runtime_cockpit/providers/agentrouter_proxy.py`
- `python/src/agent_runtime_cockpit/wasm_parser/__init__.py`
- `python/tests/wasm_parser/test_wasm_parser_r_perf9.py`
- `python/src/agent_runtime_cockpit/release_intelligence/__init__.py`
- `python/tests/release_intelligence/test_release_intelligence_r_proc1.py`
- `python/src/agent_runtime_cockpit/release_snapshots/__init__.py`
- `python/tests/release_snapshots/test_release_snapshots_r_proc2.py`

If a listed file does not exist, record that. Missing expected files may be a finding if the corresponding phase is claimed complete.

## Review Checklist

For each phase, verify:

- Actual code exists and matches the claimed phase scope.
- All public API additions are additive only; no removals/renames unless explicitly approved.
- CLI commands use stable `ok()`/`err()` envelopes through `_out()` for JSON output.
- Mutating/destructive actions are confirmation-gated by `--yes` in JSON/noninteractive mode and `typer.confirm` where interactive.
- Security decisions are deterministic. No LLM allow/deny decisions.
- Secrets are not printed in logs, UI, JSON, or audit outputs.
- Optional dependencies are guarded by lazy imports and degraded states.
- Long-running/backend-bridged actions include timeouts and cancellation where expected.
- In-memory buffers/lists introduced or touched by phases are bounded where required.
- UI surfaces have loading, empty, error, degraded, and success states where applicable.
- Accessibility is explicit: roles, labels, focusability, keyboard reachability, color/NO_COLOR parity as relevant.
- Tests are deterministic, offline, and cover success + error/degraded states.
- Docs status follows evidence. `Polished Complete` only if all 8 DoD gates cite evidence.
- No banned claims. Run `scripts/check-banned-claims.sh`.

## Verification Commands

Run these unless blocked by environment. If any fail, capture exact command and failure summary:

```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
cd python && uv run mypy src/agent_runtime_cockpit/security/ src/agent_runtime_cockpit/protocol/ src/agent_runtime_cockpit/workspace.py src/agent_runtime_cockpit/gating.py src/agent_runtime_cockpit/ag_ui/
pnpm typecheck
pnpm build
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md
```

For targeted failures, run narrower tests for the affected phase file(s).

## Findings Format

Output findings first, ordered by severity:

```markdown
## Findings

### High
- `path/to/file.py:123` — Bug/risk. Expected vs actual. Repro/test. Suggested minimal fix.

### Medium
- `path/to/file.tsx:45` — Issue. Evidence. Impact.

### Low
- `docs/phases.md:8700` — Evidence wording/status mismatch.

## Phase Coverage

| Phase | Claimed | Evidence | Verdict |
|---|---:|---|---|
| 336 | yes/no | commit/tests/docs | pass/fail/partial/not implemented |

## Tool Research

- Context7: sources queried + findings, or no usable results.
- GitHub grep: queries + findings, or no usable results.
- Webfetch: URL + finding, or no usable results.
- Vercel: used/not applicable + reason.

## Verification

- Command: result.

## Patches Applied

- If fixes were made: list files and rationale.
- If no fixes: `No patches applied.`

## Residual Risks

- Anything not verified, skipped, or environment-blocked.
```

## Patch Protocol

If you choose to fix review findings:

1. Keep fixes minimal and local to the finding.
2. Use `apply_patch` only.
3. Do not rewrite modules or restructure APIs.
4. Do not touch unrelated dirty files.
5. Run targeted tests for every patched area.
6. Rerun full gates if practical; otherwise say exactly what was not run.
7. Do not commit unless explicitly asked.

## Stop Conditions

Stop and ask the owner before:

- destructive git operations (`reset --hard`, clean, force push)
- changing public APIs or CLI command names
- adding new dependencies
- making paid/provider calls
- publishing/deploying/releasing artifacts

## Review Objective

The ideal outcome is one of:

- `No findings`: all 30 phases are actually implemented, tested, documented, and evidence-backed.
- `Partial implementation`: some phases are claimed but absent or incomplete; list exact missing phases/files/tests.
- `Findings + patches`: concrete issues fixed with minimal patches and verified.

Do not overclaim. Repo evidence only.
