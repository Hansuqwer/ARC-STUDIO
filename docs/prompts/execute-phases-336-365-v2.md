# ARC Studio — Execute Phases 336–365 (v2, repo-grounded)

**Runner:** opencode + Qwen 3.7 Max (MCPs available per opencode.json: context7, grep; webfetch built in).
**Repo:** github.com/Hansuqwer/ARC-STUDIO, branch `main`.
**Facts below verified against HEAD `62c794d3` on 2026-06-10.**
**Last completed phase:** 335 (confirm in Preflight).
**You will execute Phases 336–365 sequentially in this session.**

**Owner authorization:** this prompt is the owner's explicit request to commit after each phase (satisfies AGENTS.md rule 7, "No commits unless asked"). Every other AGENTS.md rule applies unchanged.

**Critical context:** Phases 336–365 are **DoD elevations and hardening of existing code** — not new features. Every module, CLI command, and test file already exists. Your job is to read the existing code, identify gaps against the 8 DoD gates, and close them additively. **Never invent new modules, classes, or CLI commands that don't already exist in the repo.** If the v1 plan names a class or command that doesn't exist, the repo wins — note the discrepancy and proceed from what's actually there.

---

## 0. Anti-hallucination protocol (binding — re-read at every phase start)

0.1 **The working tree is the only source of truth.** Never write a path, symbol, CLI command, config key, or API signature from memory. Verify with `ls` / `grep -rn` / a file read in the same step before using it. If this prompt and the repo disagree, **the repo wins** — note the discrepancy and proceed from the repo.

0.2 **If you haven't read it this session, you don't know it.** Training-data knowledge of this repo is stale. The v1 plan for these phases contained ~20 fabricated class names and ~8 wrong CLI verbs (verified by independent audit at `docs/handover/verification-report-phases-296-335.md`). Do not repeat those mistakes.

0.3 **Show evidence before claiming.** Never state "tests pass", "file exists", or "command succeeded" without the actual command output in the same turn. If output was truncated, re-run narrower (`grep`, `tail`, `sed -n`) — never guess the missing part.

0.4 **Imports must be proven.** Before writing `import X` (Python) or adding a TS import, run `grep -n "X" python/pyproject.toml python/uv.lock` or `grep -rn "X" packages/*/package.json pnpm-lock.yaml`. Absent ⇒ it is NOT available here. Use stdlib or an existing dep.

0.5 **Research tools are best-effort.** If context7 / grep.app / webfetch errors or returns nothing relevant, write "no usable results" in your phase notes and fall back to repo conventions + stdlib. NEVER invent an API from a doc you did not actually fetch.

0.6 **No duplicate subsystems.** Before creating any new function or class, `grep` for prior art. Extend existing code; do not fork parallel implementations.

0.7 **Re-read before re-editing.** After any edit, re-read the changed region before the next edit to the same file. Never patch from a remembered version.

0.8 **Act, don't narrate.** Every reasoning step ends in a tool call until the Phase 365 summary. Do not emit plans, progress essays, or "I will now…" without immediately executing.

0.9 **Honest labels only.** "stub", "heuristic", "research-grade", "gated", "Baseline Complete" where true. Forbidden until proven by evidence: see `scripts/check-banned-claims.sh` for the full list (includes production-readiness claims, broad adoption claims, isolation claims, and unmeasured perf claims). The script is authoritative.

0.10 **When two interpretations are possible, pick the one a neighboring file already uses and name that file.**

---

## 1. Session memory protocol (context-loss defense)

**Durable memory = git history + `docs/phases.md`.** Anything not committed or ledgered will be lost. Assume your context may be compacted at any time; the ledger must always be sufficient to resume.

### Phase-start re-anchor (every phase, no exceptions):

```bash
git status --porcelain        # must be empty
git log --oneline -3
tail -n 40 docs/phases.md     # last entry must be the previous phase
```

If any check fails, reconcile (commit or revert per §3 Step 6 / §7) before writing code.

### Reading budget

`docs/roadmap.md` is ~1,900 lines and `docs/phases.md` ~8,550 and growing — **never read them whole**. Locate with `grep -n`, then `sed -n 'A,Bp'`. Same for any source file > 400 lines (`wc -l` first). Absolute line numbers go stale as you append — always re-grep, never reuse old offsets.

### Phase-end flush

After committing phase N, emit ≤ 8 lines: phase, R-ID, files touched, tests added, commit SHA, anything the next phase must know. Then treat all earlier scratch context as untrusted.

---

## 2. Preflight (run once, before Phase 336)

```bash
git rev-parse --abbrev-ref HEAD          # expect: main
git status --porcelain                   # expect: empty — STOP and report if not
tail -n 30 docs/phases.md                # expect: last entry "Phase 335"; STOP if higher (use §10 resume)
cd python && uv sync --all-extras --dev && cd ..
pnpm install
cd python && uv run ruff check src tests && cd ..
cd python && uv run pytest tests/ -q && cd ..   # record collected count (baseline: 6,438)
pnpm typecheck
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md
```

Record the pytest collected count as `BASELINE_COLLECTED`. It must **never decrease** during the session (a drop means you broke an import — fix immediately).

**Pre-existing failures:** if ruff/pytest/typecheck is red at preflight, fix it FIRST as a separate commit `fix(ci): pre-336 baseline fixups`. Do not start Phase 336 on a red baseline, and never count pre-existing failures against a phase's 3-attempt budget.

**Tool check:** make one context7 resolve-library-id call, one grep.app query, and one webfetch. Record which tools work; use documented fallbacks (§0.5) for any that don't.

---

## 3. Per-phase loop (repeat for each of the 30 phases)

### Step 0 — Re-anchor (§1 commands).

### Step 1 — Read the context kit for the phase from §6

Read the backlog spec section, the listed prior-art files, the roadmap row, and the mockup if one exists. Backlog spec lives in `docs/research-findings/competitive-feature-backlog-2026-06-09.md` — find the section with `grep -n "### R94" docs/research-findings/competitive-feature-backlog-2026-06-09.md` (adjust ID). Each spec ends with a "DoD focus" gate list.

**For DoD elevation phases (336–356):** Read the existing module and test files FIRST. The code already exists — your job is to identify what's missing against the 8 DoD gates and close the gaps additively. Do NOT rewrite or restructure existing code.

### Step 2 — Research (best-effort, ≤ 3 calls per tool, then move on)

- **context7:** resolve + query docs for the library at the version pinned in uv.lock/pnpm-lock.yaml.
- **grep.app:** real-world implementations of the pattern.
- **webfetch:** protocol/spec pages.

Output: 3–6 findings bullets with actual sources, or the literal line "no usable results — proceeding on repo conventions". Findings inform design; they are not evidence and must not be pasted into docs.

### Step 3 — Implement

Follow §5 conventions. **Read existing files before editing.** Every user-visible surface must have loading/empty/error/degraded/success states. Security decisions deterministic only. Additive changes only — never remove or rename existing public APIs.

### Step 4 — Test

Extend existing test files. New tests every phase: ≥ 3 unit tests per module being elevated, plus CLI integration tests. Deterministic, offline, no provider calls unless explicitly gated.

Gates before commit:

```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q          # full suite, every phase; collected ≥ BASELINE_COLLECTED
pnpm typecheck && pnpm build                  # required whenever packages/** or root TS config changed
```

Pure-Python phases may skip `pnpm build` (Phase 364 runs everything regardless).

**CI traps** (`.github/workflows/python.yml`): CI runs scoped mypy over `security/`, `protocol/`, `workspace.py`, `gating.py`, `ag_ui/`, and listed `mobile/` modules — if your phase touches any of those, run that exact mypy command locally first. CI runs pytest with `-W error`, so new code must not emit warnings.

**Failure budget:** 3 fix attempts per distinct failure signature, counting only failures your diff introduced. Still red after 3 → roll back (`git reset --hard && git clean -fd`), append a `## Phase NNN — BLOCKED` ledger entry to `docs/phases.md` with the exact failing command + last 20 output lines, commit that, and continue only if the next phase is independent.

### Step 5 — Update locked docs, same commit

**`docs/roadmap.md`:** flip only the status cell of the matching table row. Find it first: `grep -n "| R94 " docs/roadmap.md` → edit `| Baseline Complete |` → `| Polished Complete |`. Touch nothing else.

**`docs/phases.md`:** append in the established format (match Phases 332–334 exactly for DoD elevations):

```markdown
## Phase NNN — R-ID DoD elevation: Title → Polished Complete

**Status:** Polished Complete

**DoD gates:**
1. UX states: <evidence>
2. Accessibility: <evidence>
3. Parity: <evidence>
4. Tests: <N> tests pass (`tests/<path>`); ruff clean.
5. Performance: <evidence>
6. Security: <evidence>
7. Reliability: <evidence>
8. Docs: `--help` comprehensive; docs updated; banned claims clean.

**Evidence:** <N> tests pass; ruff clean. Full suite: <total> passed.
```

```bash
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md
```

### Step 6 — Commit and verify

```bash
git add -A
git commit -m "polish(R94): ARC Advisor DoD elevation — Phase 336"
git log --oneline -1 && git status --porcelain
```

Then flush (§1) and begin the next phase immediately.

---

## 4. Dependency policy

**Installed Python core** (`python/pyproject.toml`): pydantic≥2.7, typer, rich, aiohttp, aiofiles, idna, PyYAML, tiktoken, mcp, swarmgraph-sdk, textual, pygments.

**Existing optional groups:** langgraph, context (httpx), optimizer (tiktoken), docker, arena (openai/anthropic), vz, vision (playwright), voice (whisper/faster-whisper), debug (debugpy).

**Dev:** pytest (+asyncio/cov/benchmark/textual-snapshot), hypothesis, ruff, mypy, pip-audit, httpx.

**NOT installed (do not import unguarded):** wasmtime, PyGithub, jinja2, celery, nbformat, deepdiff, watchdog. TS: reactflow, dagre, @xyflow.

**Default order of preference:** (1) stdlib, (2) an installed dep, (3) a new optional-dependency group with lazy import + degraded state + tests that pass without it (`pytest.importorskip`). Never add to core dependencies.

---

## 5. Repo conventions — verify against the named exemplar before writing

**Output contract:** every CLI command emits the `ok()`/`err()` envelope via `ArcEnvelope` from `protocol/event_envelope.py` and the `_out()` helper from `cli/_helpers.py`. No bare `print` in commands.

**Wiring:** sub-apps are created only in `cli/_subapps.py`; command modules import their sub-app; `cli/_app.py` mounts it. Heavy/SDK imports live inside command function bodies (lazy).

**CLI namespace:** all commands for phases 336–365 already exist. **Do not add new commands.** Extend existing ones with better error handling, envelopes, and confirmation gates.

**Theia UI pattern:** `arc-<x>-widget.tsx` + `arc-<x>-contribution.ts`, registered in `arc-extension-frontend-module.ts`. Backend bridges: `src/node/services/`. Async bridges only; no sync fs in hot UI paths; bounded buffers; virtualize long lists.

**Security:** deterministic decisions; secrets redacted (exemplars: `security/redaction.py`); paid/provider calls gated; destructive actions confirmation-gated (`typer.confirm` or `--yes` flag); audit appended on allow.

**Additive protocol only:** never remove or rename existing events, CLI commands, or public APIs.

**Tests:** mirror the subsystem layout in `python/tests/<subsystem>/`; TUI parity respects `NO_COLOR`.

---

## 6. Phase assignments 336–365 — grounded context kits

Format: **Spec** (backlog § to grep) · **Prior art** (read first — these files already exist) · **Build** (what to add/change) · **Deps** · **Research**.

"DoD focus" in each spec section lists which of the 8 AGENTS.md gates the elevation must hit.

---

### Phase 336 — R94 DoD elevation: ARC Advisor → Polished Complete

**Spec:** `### R94` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/advisor/__init__.py` — `CostAdvisor`, `UsageRecord`, `Recommendation`, `AdvisorReport` classes; `__all__` already defined
- `python/src/agent_runtime_cockpit/cli/advisor.py` — `advisor_analyze`, `advisor_simulate`, `advisor_pricing` commands; `advisor_app` sub-app
- `python/tests/advisor/test_advisor_r94.py` — 19 existing tests
- `python/src/agent_runtime_cockpit/cli/_helpers.py` — `_out()` helper, `ArcEnvelope` usage pattern
- `python/src/agent_runtime_cockpit/protocol/event_envelope.py` — `ok()`, `err()` functions

**Build:** Add `AdvisorError` exception class. Wrap all CLI commands in `ok()`/`err()` envelopes via `_out()`. Add explicit empty-state handling (empty traces → empty `AdvisorReport`, not raise). Add `--json` output stability tests. Extend tests to ≥ 22 covering all 3 commands + error + empty states.

**Deps:** stdlib + tiktoken (installed). No new deps.

**Research:** context7 pydantic v2 error handling; grep.app CLI error envelope patterns.

---

### Phase 337 — R95 DoD elevation: ARC Dashboard → Polished Complete

**Spec:** `### R95` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `packages/arc-extension/src/browser/arc-dashboard-widget.tsx` — existing widget with 3 summary cards (Workspaces/Active/Total Cost)
- `packages/arc-extension/src/browser/arc-dashboard-contribution.ts` — Theia contribution
- `packages/arc-extension/src/browser/arc-extension-frontend-module.ts` — DI bindings
- `packages/arc-extension/src/browser/__tests__/arc-dashboard-widget.test.tsx` — 2 existing tests
- Exemplar for UX states: `packages/arc-extension/src/browser/arc-health-widget.tsx` (loading/empty/error patterns)

**Build:** Add explicit loading state (spinner), empty state (no workspaces message), error state (error banner with retry). Add `aria-label` to cards. Extend tests to ≥ 5 covering all UX states + a11y. `pnpm typecheck && pnpm build` required.

**Deps:** Existing Theia deps only. No new packages.

**Research:** context7 @theia/core widgets; grep.app Theia widget UX state patterns.

---

### Phase 338 — R96 DoD elevation: ARC Voice → Polished Complete

**Spec:** `### R96` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/voice/__init__.py` — `VoiceState`, `TranscriptionResult`, `VoiceDriver` (ABC), `FakeVoiceDriver`, `WhisperVoiceDriver`, `VoicePipeline`
- `python/src/agent_runtime_cockpit/cli/voice.py` — `voice_transcribe`, `voice_listen`, `voice_status` commands
- `python/tests/voice/test_voice_r96.py` — 24 existing tests

**Build:** Add `VoiceError` structured exception. Ensure `transcribe()` returns degraded `TranscriptionResult` (not raises) when driver unavailable. Wrap all CLI commands in `ok()`/`err()` envelopes. Add explicit degraded state when Whisper not installed. Extend tests to ≥ 27.

**Deps:** voice optional group (whisper) already defined. No new deps.

**Research:** context7 faster-whisper error handling; grep.app CLI degraded-state patterns.

---

### Phase 339 — R97 DoD elevation: ARC Policies → Polished Complete

**Spec:** `### R97` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/security/policy_templates/__init__.py` — `PolicyTemplate` dataclass, `load_template()`, `list_templates()`, `validate_template()`, `apply_template()` functions
- `python/src/agent_runtime_cockpit/security/policy_templates/templates/*.yaml` — 5 existing templates
- `python/src/agent_runtime_cockpit/cli/sandbox.py` — existing `policy_app` sub-app with `template-list`, `template-show`, `template-validate`, `template-apply` commands
- `python/tests/security/policy_templates/test_policy_templates_r97.py` — 25 existing tests
- **CI trap:** this phase touches `security/` — run scoped mypy: `cd python && uv run mypy src/agent_runtime_cockpit/security/`

**Build:** Add `PolicyTemplateError` exception. Ensure `load_template()` returns structured error on unknown ID. Add `--yes` confirmation gate to `template-apply` (mutating action). Wrap all commands in `ok()`/`err()` envelopes. Extend tests to ≥ 28.

**Deps:** PyYAML + pydantic (installed). No new deps.

**Research:** grep.app policy template error handling patterns.

---

### Phase 340 — R98 DoD elevation: ARC Composer → Polished Complete

**Spec:** `### R98` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/composer/__init__.py` — `CodeGenResult` dataclass, `generate_swarmgraph_code()`, `validate_composer_graph()` functions; reuses `IRGraph`/`IRNode`/`IREdge` from `swarmgraph_ir`
- `python/src/agent_runtime_cockpit/cli/composer.py` — `composer_generate`, `composer_validate` commands
- `python/tests/composer/test_composer_r98.py` — 18 existing tests

**Build:** Add `ComposerError` exception. Ensure `generate_swarmgraph_code()` returns `CodeGenResult(ok=False, ...)` on invalid graph (not raises). Add `--yes` gate when `generate` overwrites existing file. Wrap commands in `ok()`/`err()` envelopes. Extend tests to ≥ 22.

**Deps:** stdlib + swarmgraph-sdk (installed). No new deps.

**Research:** grep.app code generation error handling patterns.

---

### Phase 341 — R99 DoD elevation: ARC Debug → Polished Complete

**Spec:** `### R99` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/debug/__init__.py` — `DebugAdapter`, `DebugSession`, `DAPMessage`, `Breakpoint`, `Variable`, `StackFrame`
- `python/src/agent_runtime_cockpit/cli/debug.py` — `debug_launch`, `debug_attach`, `debug_status` commands
- `python/tests/debug/test_debug_r99.py` — 24 existing tests

**Build:** Add `DebugError` exception. Add explicit `IDLE/RUNNING/STOPPED/ERROR` state enum to `DebugSession`. Ensure `disconnect()` in `finally` block. Wrap all commands in `ok()`/`err()` envelopes. Add degraded state when session unreachable. Extend tests to ≥ 28.

**Deps:** debug optional group (debugpy) already defined. No new deps.

**Research:** webfetch DAP spec (error handling); grep.app DAP adapter error patterns.

---

### Phase 342 — R100 DoD elevation: ARC Notebook → Polished Complete

**Spec:** `### R100` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/notebook/__init__.py` — `Notebook`, `NotebookCell`, `CellOutput`, `CellType` (4 values: prompt/tool_call/code/markdown), `export_ipynb()`, `export_markdown()`, `export_python()`
- `python/src/agent_runtime_cockpit/cli/notebook.py` — `notebook_new`, `notebook_show`, `notebook_export`, `notebook_add_cell` commands
- `python/tests/notebook/test_notebook_r100.py` — 23 existing tests

**Build:** Add `NotebookError` exception. Ensure export functions return structured error on empty notebook. Add schema version validation on load. Add `--yes` gate when `export` overwrites existing file. Wrap commands in `ok()`/`err()` envelopes. Extend tests to ≥ 27.

**Deps:** stdlib only. No new deps.

**Research:** grep.app notebook export error handling.

---

### Phase 343 — R101 DoD elevation: ARC Time Travel → Polished Complete

**Spec:** `### R101` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/time_travel/__init__.py` — `TimeTravelSession`, `StateSnapshot`, `Branch`, `StepType`, `compare_paths()`
- `python/src/agent_runtime_cockpit/cli/time_travel.py` — `time_travel_record`, `time_travel_replay`, `time_travel_branch`, `time_travel_compare`, `time_travel_show` commands
- `python/tests/time_travel/test_time_travel_r101.py` — 31 existing tests

**Build:** Add `TimeTravelError` exception. Add explicit end-of-session state to `replay()`. Add `--yes` confirmation gate when branching from non-latest step. Wrap all 5 commands in `ok()`/`err()` envelopes. Add empty-session explicit state. Extend tests to ≥ 35.

**Deps:** stdlib only (json/dataclasses/pathlib). No new deps.

**Research:** grep.app event-sourcing replay error handling.

---

### Phase 344 — R102 DoD elevation: ARC Migrate → Polished Complete

**Spec:** `### R102` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/migrate/__init__.py` — `MigrationResult`, `MigrationAnalysis`, `MigrationIssue`, `FrameworkType` (includes AUTOGEN, LLAMAINDEX), `MigrationStatus`, `detect_framework()`, `analyze_migration()`, `generate_migration()`, `validate_migration()`, `migrate_workspace()`
- `python/src/agent_runtime_cockpit/cli/migrate.py` — `migrate_detect`, `migrate_analyze`, `migrate_run`, `migrate_validate` commands
- `python/tests/migrate/test_migrate_r102.py` — 23 existing tests

**Build:** Add `MigrationError` exception. Add `--dry-run` flag to `migrate_workspace()` and `run` command. Add `--yes` gate for actual migration. Add `--strict` mode to `validate_migration()`. Wrap all commands in `ok()`/`err()` envelopes. Extend tests to ≥ 27.

**Deps:** stdlib `ast` only. No new deps.

**Research:** grep.app AST migration error handling.

---

### Phase 345 — R83 DoD elevation: ARC Predict → Polished Complete

**Spec:** `### R83` in backlog. DoD focus: 1, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/cli/predict_cmd.py` — `predict_next_edit` command (heuristic regex stub, gated behind `ARC_REAL_RUNTIME_SMOKE=1`)
- `python/tests/test_predict_r83.py` — existing tests

**Build:** Wrap in `ok()`/`err()` envelopes. Add file-not-found → explicit error state. Add line out-of-range → degraded state. Add `--json` output stability. Add "research-grade stub" label to `--help`. Extend tests to ≥ 12.

**Deps:** stdlib only. No new deps.

---

### Phase 346 — R84 DoD elevation: ARC Index → Polished Complete

**Spec:** `### R84` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/index/__init__.py` — `CodebaseIndex` class (SQLite+FTS5)
- `python/src/agent_runtime_cockpit/cli/index_cmd.py` — `index_build`, `index_search`, `index_stats` commands
- `python/tests/test_index_r84.py` — existing tests

**Build:** Add `IndexError` exception. Add `IndexBuildResult` dataclass (file count, elapsed, errors). Add empty workspace → explicit empty index state. Add un-built index → degraded search state. Wrap commands in `ok()`/`err()` envelopes. Extend tests to ≥ 15.

**Deps:** stdlib sqlite3. No new deps.

---

### Phase 347 — R85 DoD elevation: ARC Context → Polished Complete

**Spec:** `### R85` in backlog. DoD focus: 1, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/cli/context_cmd.py` — `context_suggest`, `context_attach` commands (also `list` and `clear` if wired)
- `python/tests/test_context_r85.py` — existing tests

**Build:** Ensure `list` and `clear` (with `--yes`) are registered Typer commands. Wrap all commands in `ok()`/`err()` envelopes. Add un-built index → degraded state. Add empty context → explicit empty state. Extend tests to ≥ 12.

**Deps:** Reuses R84 index. No new deps.

---

### Phase 348 — R90 DoD elevation: ARC Memory → Polished Complete

**Spec:** `### R90` in backlog. DoD focus: 1, 2, 3, 4, 5, 6, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/cli/memory_cmd.py` — `memory_save`, `memory_load`, `memory_search` commands (also `list` if wired)
- `python/tests/test_memory_r90.py` — existing tests

**Build:** Ensure `list` and `clear` (with `--yes`) are registered. Wrap all commands in `ok()`/`err()` envelopes. Add key-not-found → explicit error. Add empty memory → explicit empty state. Extend tests to ≥ 15.

**Deps:** Reuses R84 FTS5. No new deps.

---

### Phase 349 — R-PERF7 DoD elevation: Incremental Index → Polished Complete

**Spec:** roadmap row. DoD focus: 4, 5, 7.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/index/__init__.py` — `update_file()`, `remove_file()`, `get_changed_files()`, `incremental_update()` methods on `CodebaseIndex`
- `python/tests/index/test_incremental_index_r_perf7.py` — 9 existing tests

**Build:** Add `IncrementalUpdateResult` dataclass (files_added, files_updated, files_removed, elapsed_ms, errors). Bound max incremental batch (1000 files/call). Add timeout to `get_changed_files()`. Extend tests to ≥ 12.

**Deps:** stdlib only. No new deps.

---

### Phase 350 — R-SEC2 DoD elevation: PromptGuard → Polished Complete

**Spec:** roadmap row. DoD focus: 4, 6, 7.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/security/prompt_guard.py` — `_BLOCKED_PATTERNS` (9), `_DEGRADED_PATTERNS` (5), `GuardResult`, `scan_prompt()` function
- `python/tests/security/test_prompt_guard.py` — existing tests
- **CI trap:** touches `security/` — run scoped mypy

**Build:** Add `scan_batch()` for multiple prompts. Add `GuardResult.to_dict()`. Add `arc security scan-prompt` CLI command (new file `cli/security_cmd.py`). Wrap in `ok()`/`err()` envelopes. Extend tests to ≥ 14 patterns tested individually + batch + CLI.

**Deps:** stdlib `re` only. No new deps.

---

### Phase 351 — R-SEC3 DoD elevation: SBOM integrity → Polished Complete

**Spec:** roadmap row. DoD focus: 4, 6, 7.

**Prior art (read first):**
- `scripts/check-sbom-integrity.sh` — 114 lines, pnpm-lock sha256 + pip-audit
- `.github/workflows/python.yml` — existing CI steps

**Build:** Add explicit exit codes (0=clean, 1=mismatch, 2=baseline-not-found). Add `--strict` flag. Improve output messages (PASS/FAIL/WARN labels). Wire as non-blocking warning step in CI. Add Python tests in new `tests/security/test_sbom_integrity.py`.

**Deps:** stdlib + pip-audit (dev). No new deps.

---

### Phase 352 — R-PERF6 DoD elevation: Memory-mapped traces → Polished Complete

**Spec:** roadmap row. DoD focus: 4, 5, 7.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/orchestration/event_broker.py` — mmap path at line ~175 (> 10 MB threshold)
- `python/tests/test_perf_r85_r86_r87.py` — existing perf tests

**Build:** Add `MmapReadResult` dataclass (line_count, elapsed_ms, mmap_used: bool). Expose threshold as `MMAP_THRESHOLD_BYTES` constant with env override `ARC_MMAP_THRESHOLD`. Extend tests for threshold env override, small/large file paths.

**Deps:** stdlib `mmap`. No new deps.

---

### Phase 353 — R-PERF8 DoD elevation: Provider connection pooling → Polished Complete

**Spec:** roadmap row. DoD focus: 4, 5, 7.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/providers/agentrouter_proxy.py` — `TCPConnector(limit_per_host=10)` at line ~130
- `python/tests/test_perf_r85_r86_r87.py` — existing perf tests

**Build:** Expose `POOL_LIMIT_PER_HOST` as module constant. Add `get_pool_stats()` returning active connection count. Extend tests for pool stats schema, reuse verification.

**Deps:** aiohttp (installed). No new deps.

---

### Phase 354 — R-PERF9 DoD elevation: WASM trace parser → Polished Complete (research milestone)

**Spec:** roadmap row — note "(research; ~10× large-trace speedup)". The 10× figure is a hypothesis — never write it in docs without your own benchmark.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/wasm_parser/__init__.py` — `TraceParser`, `WasmTraceParser`, `TraceParseResult`, `benchmark_parser()`, `generate_test_trace()`
- `python/tests/wasm_parser/test_wasm_parser_r_perf9.py` — 14 existing tests

**Build:** Add `WasmParserConfig` dataclass. Add `BenchmarkResult` with Python baseline time, WASM estimate, speedup_factor. Document `wasmtime-py` install path in module docstring. Label as "research milestone — WASM not yet wired" in phases.md. Extend tests to ≥ 16.

**Deps:** wasmtime NOT installed — keep behind optional group + default-off flag.

---

### Phase 355 — R-PROC1 DoD elevation: Release Intelligence → Polished Complete

**Spec:** roadmap row. DoD focus: 4, 7, 8.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/release_intelligence/__init__.py` — `ReleaseIntelligence`, `CommitInfo`, `generate_release_intelligence()`, `parse_git_log()`, `get_commit_stats()`, `save_release_intelligence()`, `load_release_intelligence()`
- `python/tests/release_intelligence/test_release_intelligence_r_proc1.py` — 10 existing tests

**Build:** Add `ReleaseIntelligenceError`. Ensure `generate_release_intelligence()` returns degraded report on git-not-found. Add `to_markdown()` output method. Add `arc release intelligence` CLI command in new `cli/release_cmd.py`. Wrap in `ok()`/`err()` envelopes. Extend tests to ≥ 14.

**Deps:** stdlib `subprocess` for git log. No new deps.

---

### Phase 356 — R-PROC2 DoD elevation: RELEASE_SNAPSHOTS → Polished Complete

**Spec:** roadmap row. DoD focus: 4, 6, 7.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/release_snapshots/__init__.py` — `generate_snapshot_filename()`, `generate_snapshot_markdown()`, `save_snapshot()`, `list_snapshots()`, `get_latest_snapshot()`, `verify_snapshot_immutability()`
- `python/tests/release_snapshots/test_release_snapshots_r_proc2.py` — 16 existing tests

**Build:** Add `SnapshotError`. Ensure `save_snapshot()` explicit error on immutability violation. Add `arc release snapshot` subcommands (`create`, `list`, `verify`) in `cli/release_cmd.py`. Wrap in `ok()`/`err()` envelopes. Extend tests to ≥ 19.

**Deps:** stdlib only. No new deps.

---

### Phase 357 — CLI parity audit: missing `list`/`clear` commands

**Type:** Cross-cutting hardening.

**Prior art (read first):**
- `python/src/agent_runtime_cockpit/cli/context_cmd.py` — check if `list` and `clear` are registered
- `python/src/agent_runtime_cockpit/cli/memory_cmd.py` — check if `list` and `clear` are registered
- `python/src/agent_runtime_cockpit/cli/_subapps.py` — routing verification

**Build:** Ensure `list` and `clear` (with `--yes`) are registered Typer commands in both modules. Add CLI tests. If already done in Phases 347/348, skip and note in phases.md.

---

### Phase 358 — `--json` envelope audit across all new modules

**Type:** Cross-cutting hardening.

**Prior art (read first):**
- All `cli/*.py` modules added in Phases 316–356
- `cli/_helpers.py` — `_out()` pattern

**Build:** Audit every CLI command for stable `--json` envelope output. Fix any that output raw text in JSON mode. Add `--json` envelope schema tests per module.

---

### Phase 359 — Security surface audit: confirmation gates

**Type:** Security hardening audit.

**Prior art (read first):**
- All `cli/*.py` modules — grep for mutating commands without `--yes` gate

**Build:** Audit every mutating CLI command for `--yes` confirmation gate. Fix gaps. Add confirmation-gate tests.

---

### Phase 360 — Performance audit: bound in-memory buffers

**Type:** Performance hardening.

**Prior art (read first):**
- `time_travel/__init__.py` — `StateSnapshot` list
- `notebook/__init__.py` — cell list
- `debug/__init__.py` — `Variable` list
- `release_intelligence/__init__.py` — commit list

**Build:** Add caps: `MAX_SNAPSHOTS=1000`, `MAX_CELLS=500`, `MAX_VARIABLES=500`, `MAX_COMMITS=500`. Emit warning on cap (not silent drop). Add cap behaviour tests.

---

### Phase 361 — Reliability audit: timeouts + cancellation

**Type:** Reliability hardening.

**Prior art (read first):**
- `voice/__init__.py` — `listen()` loop
- `debug/__init__.py` — `connect()`
- `tasks/scheduler.py` — `run_once()`

**Build:** Add explicit timeouts: `listen()` 60s, `connect()` 10s, `run_once()` per-task timeout. Add timeout behaviour tests.

---

### Phase 362 — Ruff + type annotations sweep

**Type:** Code quality.

**Prior art (read first):**
- All new `src/agent_runtime_cockpit/*/` modules (hub, tasks, vision, advisor, voice, composer, debug, notebook, time_travel, migrate, wasm_parser, release_intelligence, release_snapshots)

**Build:** Run `mypy --strict` on each module. Fix all errors. Add missing type annotations to public APIs.

---

### Phase 363 — docs/roadmap.md + docs/phases.md sweep

**Type:** Docs.

**Build:** Update both locked docs with status changes from Phases 336–362. Update `AGENTS.md` active track.

---

### Phase 364 — Final sweep: full verification

**Type:** Release gate.

```bash
cd python && uv run ruff check src tests && uv run pytest tests/ -q && cd ..
pnpm typecheck && pnpm build
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md
```

Record evidence in `docs/phases.md`.

---

### Phase 365 — Release snapshot

**Type:** Process.

```bash
bash scripts/generate-release-snapshot.sh
```

Record HEAD, test counts, version marker in `docs/phases.md` and `docs/roadmap.md`.

---

## 7. Hard prohibitions (charter — no exceptions)

- No removal/rename of existing events, CLI commands, or public APIs.
- No LLM-based security decisions.
- No mutation of the frozen `EnforcementContext`.
- No new roadmap/phase/status markdown files — only the two canonical docs, edited in place.
- No skipped UX states.
- No unmeasured performance claims.
- No banned wording (§0.9).
- No claiming a command ran without its output.
- Single-user, loopback-only alpha posture throughout.
- **No inventing class names, CLI verbs, or mechanisms that don't exist in the repo.** If the v1 plan names something that doesn't exist, the repo wins.

---

## 8. Continuation prompt (if the session is interrupted)

```
Resume ARC Studio phase execution on github.com/Hansuqwer/ARC-STUDIO (branch main),
following docs/prompts/execute-phases-336-365-v2.md exactly.

Re-anchor first: git status --porcelain; git log --oneline -5; tail -n 60 docs/phases.md.
The ledger, not your memory, determines the last completed phase. If the tree is dirty,
diff it against the last ledger entry: finish that phase's Steps 4–6 if close to green,
otherwise git reset --hard && git clean -fd and redo the phase from Step 0.

Then continue the per-phase loop (re-anchor → context kit → research → implement →
ruff + full pytest [+ typecheck/build if TS] → same-commit roadmap/phases update →
commit → verify) through Phase 365. All anti-hallucination rules in §0 remain binding.
```

---

*Generated: 2026-06-10 | Repo: https://github.com/Hansuqwer/ARC-STUDIO*
