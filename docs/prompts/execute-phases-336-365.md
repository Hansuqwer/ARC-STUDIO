# Execution Plan — Phases 336–365 (Next 30 Phases)

**Repo:** https://github.com/Hansuqwer/ARC-STUDIO  
**Base HEAD:** `62c794d3` on `main`  
**Date authored:** 2026-06-10  
**Python baseline:** 6438 passed | **TS baseline:** 990 passed  
**Next free phase:** 336

---

## Governing Rules (from AGENTS.md)

1. Finish 1 → 100% before broadening. One phase at a time.
2. Every phase ends with: ruff clean + pytest green + typecheck clean + banned-claims clean.
3. Status follows evidence — never the reverse.
4. No commits unless all checks pass; commit message matches repo style.
5. DoD elevation requires all 8 gates cited with evidence.
6. Single-user, loopback-only alpha posture unchanged throughout.

---

## Verification commands (run after every phase)

```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm typecheck && pnpm build
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md
```

---

## Track assignment

| Phases | Track | Goal |
|---|---|---|
| 336–344 | DoD elevation: R94–R102 | Elevate all 9 Baseline Complete feature modules to Polished Complete |
| 345–349 | DoD elevation: R83/R84/R85/R90 | Elevate 4 Baseline Complete research/context features |
| 350–353 | DoD elevation: R-SEC2/3, R-PERF6/7 | Elevate 4 Baseline Complete security/perf items |
| 354–356 | DoD elevation: R-PERF8/9, R-PROC1 | Elevate 3 remaining Baseline Complete items |
| 357 | DoD elevation: R-PROC2 | Elevate release-snapshots module |
| 358–362 | Cross-cutting hardening | CLI parity audit, `--json` envelope gaps, missing `list`/`clear` commands |
| 363–365 | Release gate + docs | Phase-range docs sweep, final sweep, release snapshot |

---

## Phase-by-Phase Specification

---

### Phase 336 — R94 DoD elevation: ARC Advisor → Polished Complete

**Roadmap ID:** R94  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R94): ARC Advisor DoD elevation — Phase 336`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/advisor/__init__.py` | Add explicit `AdvisorError` exception; ensure `analyze()` returns empty `AdvisorReport` (not raises) on empty traces; add `__all__` |
| `python/src/agent_runtime_cockpit/cli/advisor.py` | Wrap all commands in structured `ok()`/`err()` envelopes; add `--yes` confirmation gate to any destructive path (none currently — document this in docstring); ensure `--json` output is stable |
| `python/tests/advisor/test_advisor_r94.py` | Extend to cover: empty-trace empty-state, error-state envelope, `--json` output schema, pricing table completeness, simulate edge cases |
| `docs/phases.md` | Add Phase 336 entry with all 8 DoD gate citations |
| `docs/roadmap.md` | R94 status: Baseline Complete → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** empty-trace → empty `AdvisorReport` (no raise); error path returns `err()` envelope; success returns structured data.
2. **A11y:** CLI-only; keyboard-accessible.
3. **Parity:** `analyze`, `simulate`, `pricing` all use consistent `ok()`/`err()` JSON envelope.
4. **Tests:** ≥ 22 tests covering all 3 commands + error + empty states.
5. **Performance:** `load_usage_from_traces()` streams files, no full-memory load for large trace dirs.
6. **Security:** No paid provider calls; all analysis is local trace parsing.
7. **Reliability:** `AdvisorError` structured exception; all CLI paths exit cleanly on error.
8. **Docs:** `--help` comprehensive; docs updated; banned-claims clean.

---

### Phase 337 — R95 DoD elevation: ARC Dashboard → Polished Complete

**Roadmap ID:** R95  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R95): ARC Dashboard DoD elevation — Phase 337`

#### Files to touch

| File | Change |
|---|---|
| `packages/arc-extension/src/browser/arc-dashboard-widget.tsx` | Add explicit loading state (spinner), empty state (no workspaces message), error state (error banner with retry); replace hardcoded summary with real async data fetch via `ArcService`; add `aria-label` to cards |
| `packages/arc-extension/src/browser/__tests__/arc-dashboard-widget.test.tsx` | Extend: loading state renders spinner, empty state renders message, error state renders banner, cards render correct labels |
| `docs/phases.md` | Add Phase 337 entry |
| `docs/roadmap.md` | R95 status → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** Loading spinner, empty-workspace message, error banner with retry, success cards — all explicit.
2. **A11y:** `aria-label` on summary cards; keyboard-reachable; focus visible.
3. **Parity:** Consistent with other IDE widgets (uses `ArcService` async bridge pattern).
4. **Tests:** ≥ 5 tests (loading/empty/error/success/aria).
5. **Performance:** Async data fetch; no blocking main thread.
6. **Security:** No secrets in widget; read-only workspace list.
7. **Reliability:** Error boundary catches fetch failure; retry available.
8. **Docs:** Component JSDoc; docs updated.

---

### Phase 338 — R96 DoD elevation: ARC Voice → Polished Complete

**Roadmap ID:** R96  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R96): ARC Voice DoD elevation — Phase 338`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/voice/__init__.py` | Add `VoiceError` structured exception; ensure `transcribe()` returns a degraded `TranscriptionResult` (not raises) when driver unavailable; add `__all__` |
| `python/src/agent_runtime_cockpit/cli/voice.py` | Wrap all commands in `ok()`/`err()` envelopes; add explicit degraded state when Whisper not installed (currently may raise); `--json` output stable |
| `python/tests/voice/test_voice_r96.py` | Extend: driver-unavailable degraded state, `--json` envelope schema, `status` all states (available/unavailable/error) |
| `docs/phases.md` | Add Phase 338 entry |
| `docs/roadmap.md` | R96 status → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** Driver unavailable → degraded state (not crash); error → `err()` envelope; success → structured result.
2. **A11y:** CLI-only.
3. **Parity:** All 3 commands use consistent envelope.
4. **Tests:** ≥ 27 tests.
5. **Performance:** `listen` loop is non-blocking; uses async where possible.
6. **Security:** No cloud API calls; local Whisper only; audio files not persisted by default.
7. **Reliability:** `VoiceError` on all failure paths; `finally` cleanup in `listen` loop.
8. **Docs:** Updated.

---

### Phase 339 — R97 DoD elevation: ARC Policies → Polished Complete

**Roadmap ID:** R97  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R97): ARC Policies DoD elevation — Phase 339`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/security/policy_templates/__init__.py` | Add `PolicyTemplateError`; ensure `load_template()` returns structured error on unknown ID (not raises bare `KeyError`); add `__all__` |
| `python/src/agent_runtime_cockpit/cli/sandbox.py` | Ensure `template-list`, `template-show`, `template-validate`, `template-apply` all use `ok()`/`err()` envelopes; `template-apply` gets `--yes` confirmation gate (mutating action) |
| `python/tests/security/policy_templates/test_policy_templates_r97.py` | Extend: unknown template → structured error, `template-apply` requires `--yes`, all 5 templates validate clean |
| `docs/phases.md` | Add Phase 339 entry |
| `docs/roadmap.md` | R97 status → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** Unknown template → `err()` envelope; apply without `--yes` → `CONFIRMATION_REQUIRED`; success → applied policy path.
2. **A11y:** CLI-only.
3. **Parity:** Consistent envelopes; `--json` stable.
4. **Tests:** ≥ 28 tests.
5. **Performance:** YAML load is O(1) per template; no full-dir scan on show/validate.
6. **Security:** `template-apply` is confirmation-gated (mutates workspace policy); deterministic validation.
7. **Reliability:** `PolicyTemplateError` on all failure paths.
8. **Docs:** Updated.

---

### Phase 340 — R98 DoD elevation: ARC Composer → Polished Complete

**Roadmap ID:** R98  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R98): ARC Composer DoD elevation — Phase 340`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/composer/__init__.py` | Add `ComposerError`; ensure `generate_swarmgraph_code()` returns `CodeGenResult(ok=False, ...)` on invalid graph (not raises); add `__all__` |
| `python/src/agent_runtime_cockpit/cli/composer.py` | Wrap `generate` and `validate` in `ok()`/`err()` envelopes; `generate` writes output file with `--yes` gate if overwriting existing file |
| `python/tests/composer/test_composer_r98.py` | Extend: invalid graph → `CodeGenResult(ok=False)`, overwrite confirmation gate, `--json` envelope, validate cycle detection |
| `docs/phases.md` | Add Phase 340 entry |
| `docs/roadmap.md` | R98 status → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** Invalid graph → structured error result; overwrite → confirmation gate; success → generated code path.
2. **A11y:** CLI-only.
3. **Parity:** Both commands use consistent envelope.
4. **Tests:** ≥ 22 tests.
5. **Performance:** Code generation is synchronous and fast (pure AST string building).
6. **Security:** Output file overwrite is confirmation-gated.
7. **Reliability:** `ComposerError` on all failure paths; `CodeGenResult.ok` checked before file write.
8. **Docs:** Updated.

---

### Phase 341 — R99 DoD elevation: ARC Debug → Polished Complete

**Roadmap ID:** R99  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R99): ARC Debug DoD elevation — Phase 341`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/debug/__init__.py` | Add `DebugError`; ensure `DebugSession` has explicit `IDLE/RUNNING/STOPPED/ERROR` state enum; `disconnect()` in `finally` block |
| `python/src/agent_runtime_cockpit/cli/debug.py` | All commands use `ok()`/`err()` envelopes; `launch` and `attach` print degraded state when session unreachable; `status` shows all session states explicitly |
| `python/tests/debug/test_debug_r99.py` | Extend: session state transitions, disconnect cleanup, unreachable session → degraded state, `--json` envelope schema |
| `docs/phases.md` | Add Phase 341 entry |
| `docs/roadmap.md` | R99 status → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** All 4 session states explicit; unreachable session → degraded (not crash); error → `err()` envelope.
2. **A11y:** CLI-only.
3. **Parity:** Consistent envelopes across all 3 commands.
4. **Tests:** ≥ 28 tests.
5. **Performance:** Socket timeout configured; non-blocking connect attempt.
6. **Security:** DAP only on loopback (`127.0.0.1`); no remote debug sessions.
7. **Reliability:** `DebugError` on all failure paths; `disconnect()` always called in `finally`.
8. **Docs:** Updated.

---

### Phase 342 — R100 DoD elevation: ARC Notebook → Polished Complete

**Roadmap ID:** R100  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R100): ARC Notebook DoD elevation — Phase 342`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/notebook/__init__.py` | Add `NotebookError`; `export_ipynb()` / `export_markdown()` / `export_python()` return structured error on empty notebook; schema version validated on load |
| `python/src/agent_runtime_cockpit/cli/notebook.py` | All commands use `ok()`/`err()` envelopes; `export` gets `--yes` gate when overwriting existing file; empty notebook → explicit empty state message |
| `python/tests/notebook/test_notebook_r100.py` | Extend: empty notebook → empty state, overwrite confirmation, schema version mismatch → structured error, all 4 export formats round-trip |
| `docs/phases.md` | Add Phase 342 entry |
| `docs/roadmap.md` | R100 status → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** Empty notebook → explicit message; schema mismatch → structured error; overwrite → gate; success → file path.
2. **A11y:** CLI-only.
3. **Parity:** All 4 commands consistent envelopes.
4. **Tests:** ≥ 27 tests.
5. **Performance:** Export is streaming for large notebooks; no full in-memory cell re-read.
6. **Security:** Output overwrite confirmation-gated.
7. **Reliability:** `NotebookError` on all failure paths; schema version forward-compat.
8. **Docs:** Updated.

---

### Phase 343 — R101 DoD elevation: ARC Time Travel → Polished Complete

**Roadmap ID:** R101  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R101): ARC Time Travel DoD elevation — Phase 343`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/time_travel/__init__.py` | Add `TimeTravelError`; `record()` returns degraded `StateSnapshot` on storage failure; `replay()` has explicit end-of-session state; `branch()` confirmation-gated when branching from a non-latest step (destructive intent) |
| `python/src/agent_runtime_cockpit/cli/time_travel.py` | All 5 commands use `ok()`/`err()` envelopes; empty session → explicit empty state; replay at end → explicit done state |
| `python/tests/time_travel/test_time_travel_r101.py` | Extend: storage failure → degraded, empty session → empty state, replay-done state, branch confirmation gate, `--json` envelope |
| `docs/phases.md` | Add Phase 343 entry |
| `docs/roadmap.md` | R101 status → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** Empty session, recording, replaying, done, error — all explicit.
2. **A11y:** CLI-only.
3. **Parity:** All 5 commands consistent envelopes.
4. **Tests:** ≥ 35 tests.
5. **Performance:** Snapshots stored as JSONL (streaming append, not full rewrite); bounded snapshot count per session.
6. **Security:** Branch from non-latest step is confirmation-gated (would fork history).
7. **Reliability:** `TimeTravelError` on all failure paths; storage cleanup on error.
8. **Docs:** Updated.

---

### Phase 344 — R102 DoD elevation: ARC Migrate → Polished Complete

**Roadmap ID:** R102  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R102): ARC Migrate DoD elevation — Phase 344`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/migrate/__init__.py` | Add `MigrationError`; `migrate_workspace()` gets explicit `DRY_RUN` mode (no writes); `validate_migration()` adds `--strict` mode that fails on any unrecognized pattern |
| `python/src/agent_runtime_cockpit/cli/migrate.py` | `run` command gets `--dry-run` flag (shows what would change, writes nothing) and `--yes` gate for actual migration; all commands `ok()`/`err()` envelopes |
| `python/tests/migrate/test_migrate_r102.py` | Extend: dry-run shows diff but no writes, `run` without `--yes` → `CONFIRMATION_REQUIRED`, unknown framework → structured error, AutoGen/LlamaIndex detection |
| `docs/phases.md` | Add Phase 344 entry |
| `docs/roadmap.md` | R102 status → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** Dry-run (shows changes, no writes), confirmed run, validation error, unknown framework — all explicit.
2. **A11y:** CLI-only.
3. **Parity:** All 4 commands consistent envelopes.
4. **Tests:** ≥ 27 tests.
5. **Performance:** AST parsing is per-file; no whole-workspace load into memory.
6. **Security:** `run` is confirmation-gated (writes files to workspace); `--dry-run` is always safe.
7. **Reliability:** `MigrationError` on all failure paths; dry-run always available.
8. **Docs:** Updated; AutoGen/LlamaIndex support documented.

---

### Phase 345 — R83 DoD elevation: ARC Predict → Polished Complete

**Roadmap ID:** R83  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R83): ARC Predict DoD elevation — Phase 345`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/cli/predict_cmd.py` | Wrap in `ok()`/`err()` envelopes; file-not-found → explicit error state; line out-of-range → degraded state with message; `--json` output stable; add `research-grade stub` label to `--help` text |
| `python/tests/test_predict_r83.py` | Extend: file-not-found → `err()`, out-of-range line → degraded, `--json` envelope schema, stub label in `--help` |
| `docs/phases.md` | Add Phase 345 entry |
| `docs/roadmap.md` | R83 status → Polished Complete |

#### DoD gates to satisfy

1. **UX states:** File not found, out-of-range line, empty file, success — all explicit.
2. **A11y:** CLI-only.
3. **Parity:** `--json` envelope consistent with other CLI commands.
4. **Tests:** ≥ 12 tests.
5. **Performance:** Heuristic is O(n lines); bounded.
6. **Security:** Read-only; `ARC_REAL_RUNTIME_SMOKE` gate documented in `--help`.
7. **Reliability:** No unhandled exceptions on bad input.
8. **Docs:** `--help` clearly labels as research-grade stub; docs updated.

---

### Phase 346 — R84 DoD elevation: ARC Index → Polished Complete

**Roadmap ID:** R84  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R84): ARC Index DoD elevation — Phase 346`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/index/__init__.py` | Add `IndexError`; `build()` returns structured result with file count, elapsed time, errors list; empty workspace → explicit empty index state; index size bounded (max files configurable, default 50k) |
| `python/src/agent_runtime_cockpit/cli/index_cmd.py` | All 3 commands use `ok()`/`err()` envelopes; `build` shows progress (file count); `search` on un-built index → explicit degraded state; `stats` on empty index → explicit empty state |
| `python/tests/test_index_r84.py` | Extend: empty workspace, un-built index → degraded search, `stats` empty, `build` result schema, `--json` envelope |
| `docs/phases.md` | Add Phase 346 entry |
| `docs/roadmap.md` | R84 status → Polished Complete |

---

### Phase 347 — R85 DoD elevation: ARC Context → Polished Complete

**Roadmap ID:** R85  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R85): ARC Context DoD elevation — Phase 347`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/cli/context_cmd.py` | All commands (`suggest`, `attach`, `list`, `clear`) use `ok()`/`err()` envelopes; un-built index → degraded state message; empty context → explicit empty state; `clear` gets `--yes` confirmation gate |
| `python/tests/test_context_r85.py` | Extend: no index → degraded, empty context, clear confirmation, `--json` envelope, list/clear commands tested |
| `docs/phases.md` | Add Phase 347 entry |
| `docs/roadmap.md` | R85 status → Polished Complete |

---

### Phase 348 — R90 DoD elevation: ARC Memory → Polished Complete

**Roadmap ID:** R90  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R90): ARC Memory DoD elevation — Phase 348`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/cli/memory_cmd.py` | All commands (`save`, `load`, `search`, `list`) use `ok()`/`err()` envelopes; key-not-found → explicit error; empty memory → explicit empty state; add `clear` command with `--yes` gate; `search` on empty memory → explicit empty state |
| `python/tests/test_memory_r90.py` | Extend: key-not-found, empty memory, `clear` confirmation gate, `--json` envelopes, `list` command |
| `docs/phases.md` | Add Phase 348 entry |
| `docs/roadmap.md` | R90 status → Polished Complete |

---

### Phase 349 — R-PERF7 DoD elevation: Incremental Index → Polished Complete

**Roadmap ID:** R-PERF7  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R-PERF7): incremental index DoD elevation — Phase 349`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/index/__init__.py` | Add explicit `IncrementalUpdateResult` dataclass (files_added, files_updated, files_removed, elapsed_ms, errors); `incremental_update()` returns it; bound max incremental batch (1000 files/call); `get_changed_files()` has timeout |
| `python/tests/index/test_incremental_index_r_perf7.py` | Extend: `IncrementalUpdateResult` schema, batch size limit, timeout behaviour, error on missing file gracefully handled |
| `docs/phases.md` | Add Phase 349 entry |
| `docs/roadmap.md` | R-PERF7 status → Polished Complete |

---

### Phase 350 — R-SEC2 DoD elevation: PromptGuard → Polished Complete

**Roadmap ID:** R-SEC2  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R-SEC2): PromptGuard DoD elevation — Phase 350`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/security/prompt_guard.py` | Add `scan_batch()` for scanning multiple prompts; add `GuardResult.to_dict()` for structured output; add `__all__`; ensure patterns are compiled once at module level (already true — verify) |
| `python/src/agent_runtime_cockpit/cli/` | Add `arc security scan-prompt` CLI command in `cli/security_cmd.py`; `ok()`/`err()` envelopes; `--json` output |
| `python/tests/security/test_prompt_guard.py` | Extend: batch scan, `to_dict()` schema, new `arc security scan-prompt` CLI, all 14 patterns tested individually |
| `docs/phases.md` | Add Phase 350 entry |
| `docs/roadmap.md` | R-SEC2 status → Polished Complete |

---

### Phase 351 — R-SEC3 DoD elevation: SBOM integrity → Polished Complete

**Roadmap ID:** R-SEC3  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R-SEC3): SBOM integrity DoD elevation — Phase 351`

#### Files to touch

| File | Change |
|---|---|
| `scripts/check-sbom-integrity.sh` | Add explicit exit codes (0=clean, 1=mismatch, 2=baseline-not-found); add `--strict` flag that fails on first-run (no self-recording); improve output messages (PASS/FAIL/WARN labels) |
| `.github/workflows/python.yml` | Wire `check-sbom-integrity.sh --strict` as a non-blocking warning step (|| true) with clear output label |
| `python/tests/security/test_sbom_integrity.py` | New file: tests for exit-code logic, `--strict` flag, baseline recording, mismatch detection |
| `docs/phases.md` | Add Phase 351 entry |
| `docs/roadmap.md` | R-SEC3 status → Polished Complete |

---

### Phase 352 — R-PERF6 DoD elevation: Memory-mapped traces → Polished Complete

**Roadmap ID:** R-PERF6  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R-PERF6): mmap trace reader DoD elevation — Phase 352`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/orchestration/event_broker.py` | Add `MmapReadResult` dataclass (line_count, elapsed_ms, mmap_used: bool); expose threshold as `MMAP_THRESHOLD_BYTES` constant (currently hardcoded 10MB — make configurable via env `ARC_MMAP_THRESHOLD`); add `__all__` for new exports |
| `python/tests/test_perf_r85_r86_r87.py` | Extend: `MmapReadResult` schema, threshold env override, small file uses non-mmap path, large file uses mmap path |
| `docs/phases.md` | Add Phase 352 entry |
| `docs/roadmap.md` | R-PERF6 status → Polished Complete |

---

### Phase 353 — R-PERF8 DoD elevation: Provider connection pooling → Polished Complete

**Roadmap ID:** R-PERF8  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R-PERF8): provider connection pooling DoD elevation — Phase 353`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/providers/agentrouter_proxy.py` | Expose `POOL_LIMIT_PER_HOST` as a module constant (currently inline); add `get_pool_stats()` returning active connection count; add `__all__` |
| `python/tests/test_perf_r85_r86_r87.py` | Extend: `POOL_LIMIT_PER_HOST` = 10 verified, `get_pool_stats()` schema, pool reuse across calls |
| `docs/phases.md` | Add Phase 353 entry |
| `docs/roadmap.md` | R-PERF8 status → Polished Complete |

---

### Phase 354 — R-PERF9 DoD elevation: WASM trace parser → Polished Complete (research milestone)

**Roadmap ID:** R-PERF9  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R-PERF9): WASM trace parser research milestone — Phase 354`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/wasm_parser/__init__.py` | Add `WasmParserConfig` dataclass; `benchmark_parser()` returns `BenchmarkResult` with Python baseline time, WASM estimate, speedup_factor; document `wasmtime-py` install path in module docstring; add `__all__` |
| `python/tests/wasm_parser/test_wasm_parser_r_perf9.py` | Extend: `BenchmarkResult` schema, `WasmParserConfig` defaults, research findings documented in test docstrings |
| `docs/phases.md` | Add Phase 354 entry with honest "research milestone" label |
| `docs/roadmap.md` | R-PERF9 status → Polished Complete (research milestone — WASM not yet wired) |

---

### Phase 355 — R-PROC1 DoD elevation: Release Intelligence → Polished Complete

**Roadmap ID:** R-PROC1  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R-PROC1): release intelligence DoD elevation — Phase 355`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/release_intelligence/__init__.py` | Add `ReleaseIntelligenceError`; `generate_release_intelligence()` returns degraded report on git-not-found (no raise); add `to_markdown()` output method; add `__all__` |
| `python/src/agent_runtime_cockpit/cli/` | Add `arc release intelligence` CLI command in new `cli/release_cmd.py`; `ok()`/`err()` envelopes; `--json` and `--markdown` output formats |
| `python/tests/release_intelligence/test_release_intelligence_r_proc1.py` | Extend: git-not-found degraded, `to_markdown()` output, CLI `--json`/`--markdown`, `ReleaseIntelligenceError` |
| `docs/phases.md` | Add Phase 355 entry |
| `docs/roadmap.md` | R-PROC1 status → Polished Complete |

---

### Phase 356 — R-PROC2 DoD elevation: RELEASE_SNAPSHOTS → Polished Complete

**Roadmap ID:** R-PROC2  
**Status target:** Baseline Complete → Polished Complete  
**Commit style:** `polish(R-PROC2): release snapshots DoD elevation — Phase 356`

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/release_snapshots/__init__.py` | Add `SnapshotError`; `save_snapshot()` explicit error on immutability violation (never silent overwrite); `list_snapshots()` returns structured list with metadata; add `__all__` |
| `python/src/agent_runtime_cockpit/cli/release_cmd.py` | Add `arc release snapshot` subcommands: `create`, `list`, `verify`; `ok()`/`err()` envelopes |
| `python/tests/release_snapshots/test_release_snapshots_r_proc2.py` | Extend: immutability violation → `SnapshotError`, `list` metadata schema, `verify` detects tampering, CLI envelopes |
| `docs/phases.md` | Add Phase 356 entry |
| `docs/roadmap.md` | R-PROC2 status → Polished Complete |

---

### Phase 357 — CLI parity audit: add missing `list`/`clear` commands

**Type:** Cross-cutting hardening  
**Commit style:** `fix(cli): add missing list/clear commands — Phase 357`

**Gap identified in verification:** `arc context list|clear` and `arc memory list|clear` exist in the Python module but are not wired or tested as CLI commands (Phase 347/348 above may already cover this — skip if already done).

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/cli/context_cmd.py` | Ensure `list` and `clear` (with `--yes`) are registered Typer commands |
| `python/src/agent_runtime_cockpit/cli/memory_cmd.py` | Ensure `list` and `clear` (with `--yes`) are registered Typer commands |
| `python/src/agent_runtime_cockpit/cli/_subapps.py` | Verify routing correct |
| `python/tests/test_context_r85.py` | CLI tests for `list` and `clear` |
| `python/tests/test_memory_r90.py` | CLI tests for `list` and `clear` |
| `docs/phases.md` | Add Phase 357 entry |

---

### Phase 358 — `--json` envelope audit across all new modules

**Type:** Cross-cutting hardening  
**Commit style:** `fix(cli): --json envelope parity audit — Phase 358`

Verify every new CLI command added in Phases 316–356 has a stable `--json` envelope. Fix any that output raw text in JSON mode.

#### Files to touch (audit-driven — fix only what fails)

| Likely candidates | Change |
|---|---|
| Any `arc <module> <cmd>` that does `typer.echo(str(result))` in `--json` mode | Replace with `typer.echo(json.dumps(ok(result.to_dict())))` |
| `python/tests/*/test_*.py` for each affected module | Add `--json` envelope schema test |
| `docs/phases.md` | Add Phase 358 entry |

---

### Phase 359 — Security surface audit: confirm all destructive commands gated

**Type:** Security hardening audit  
**Commit style:** `fix(security): confirm all destructive commands confirmation-gated — Phase 359`

Audit every new CLI command (Phases 316–358) for any mutating/destructive action without `--yes` gate. Fix gaps.

#### Likely files to touch

| File | Likely gap |
|---|---|
| `python/src/agent_runtime_cockpit/cli/hub.py` | `remove` already gated ✅ — verify `add` has no silent overwrite |
| `python/src/agent_runtime_cockpit/cli/time_travel.py` | Branch from non-latest may need gate |
| `python/src/agent_runtime_cockpit/cli/migrate.py` | `run` already gated ✅ — verify |
| `python/src/agent_runtime_cockpit/cli/composer.py` | File overwrite on `generate` |
| `python/tests/*/test_*.py` | Add confirmation-gate tests for any new gates |
| `docs/phases.md` | Add Phase 359 entry |

---

### Phase 360 — Performance audit: bound all in-memory buffers

**Type:** Performance hardening  
**Commit style:** `fix(perf): bound in-memory buffers across new modules — Phase 360`

Audit new modules for unbounded in-memory growth. Fix: `TimeTravelSession` snapshot list, `Notebook` cell list, `DebugSession` variable list, `ReleaseIntelligence` commit list.

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/time_travel/__init__.py` | Cap `StateSnapshot` list at `MAX_SNAPSHOTS = 1000` (configurable); emit warning on cap |
| `python/src/agent_runtime_cockpit/notebook/__init__.py` | Cap cells at `MAX_CELLS = 500`; return error on `add_cell` beyond cap |
| `python/src/agent_runtime_cockpit/debug/__init__.py` | Cap `Variable` list per scope at `MAX_VARIABLES = 500` |
| `python/src/agent_runtime_cockpit/release_intelligence/__init__.py` | Cap commit list at `MAX_COMMITS = 500` |
| `python/tests/*/test_*.py` | Tests for cap behaviour (warning on cap, not silent drop) |
| `docs/phases.md` | Add Phase 360 entry |

---

### Phase 361 — Reliability audit: timeouts + cancellation on all async ops

**Type:** Reliability hardening  
**Commit style:** `fix(reliability): timeouts + cancellation on all async ops — Phase 361`

Add explicit timeouts to: `VoicePipeline.listen()`, `DebugSession.connect()`, `TaskScheduler.run_once()`, `WasmTraceParser` benchmark.

#### Files to touch

| File | Change |
|---|---|
| `python/src/agent_runtime_cockpit/voice/__init__.py` | `listen()` timeout parameter (default 60s); raises `VoiceError` on timeout |
| `python/src/agent_runtime_cockpit/debug/__init__.py` | `DebugSession.connect()` timeout (default 10s) |
| `python/src/agent_runtime_cockpit/tasks/scheduler.py` | `run_once()` per-task timeout (already has budget cap — add wall-clock timeout) |
| `python/tests/*/test_*.py` | Timeout behaviour tests (mock `asyncio.wait_for`) |
| `docs/phases.md` | Add Phase 361 entry |

---

### Phase 362 — Ruff + type annotations sweep on new modules

**Type:** Code quality  
**Commit style:** `fix(quality): type annotations + ruff sweep on new modules — Phase 362`

Add missing type annotations to public APIs in all new modules (R91–R102, R-SEC2/3, R-PERF6/7/8/9, R-PROC1/2). Run `mypy --strict` on each new module and fix all errors.

#### Files to touch

| Directory | Check |
|---|---|
| `python/src/agent_runtime_cockpit/hub/` | mypy --strict |
| `python/src/agent_runtime_cockpit/tasks/` | mypy --strict |
| `python/src/agent_runtime_cockpit/vision/` | mypy --strict |
| `python/src/agent_runtime_cockpit/advisor/` | mypy --strict |
| `python/src/agent_runtime_cockpit/voice/` | mypy --strict |
| `python/src/agent_runtime_cockpit/composer/` | mypy --strict |
| `python/src/agent_runtime_cockpit/debug/` | mypy --strict |
| `python/src/agent_runtime_cockpit/notebook/` | mypy --strict |
| `python/src/agent_runtime_cockpit/time_travel/` | mypy --strict |
| `python/src/agent_runtime_cockpit/migrate/` | mypy --strict |
| `python/src/agent_runtime_cockpit/wasm_parser/` | mypy --strict |
| `python/src/agent_runtime_cockpit/release_intelligence/` | mypy --strict |
| `python/src/agent_runtime_cockpit/release_snapshots/` | mypy --strict |
| `docs/phases.md` | Add Phase 362 entry |

---

### Phase 363 — docs/roadmap.md + docs/phases.md sweep

**Type:** Docs  
**Commit style:** `docs: Phases 336-362 roadmap + phases sweep — Phase 363`

Update both locked docs with status changes from Phases 336–362.

#### Files to touch

| File | Change |
|---|---|
| `docs/roadmap.md` | All R94–R102, R83–R85, R90, R-SEC2/3, R-PERF6/7/8/9, R-PROC1/2 → Polished Complete |
| `docs/phases.md` | Verify all Phase 336–362 entries present with evidence |
| `AGENTS.md` | Update active track to reflect Phases 336–363 complete |

---

### Phase 364 — Final sweep: full verification

**Type:** Release gate  
**Commit style:** `docs(release): Phase 364 final sweep — Phases 336-363`

Run full suite, confirm all gates pass, record evidence.

```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm typecheck && pnpm build
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md
```

#### Files to touch

| File | Change |
|---|---|
| `docs/phases.md` | Add Phase 364 final sweep entry with test counts |

---

### Phase 365 — Release snapshot

**Type:** Process  
**Commit style:** `docs(release): Phase 365 release snapshot — v0.9-polished`

Generate release snapshot, bump version marker in phases.md.

#### Files to touch

| File | Change |
|---|---|
| `docs/phases.md` | Add Phase 365 entry; record HEAD, test counts |
| `docs/roadmap.md` | Add v0.9-polished release gate entry |

---

## Summary table

| Phase | ID | Type | Key files |
|---|---|---|---|
| 336 | R94 | DoD elevation | `advisor/__init__.py`, `cli/advisor.py`, `tests/advisor/test_advisor_r94.py` |
| 337 | R95 | DoD elevation | `arc-dashboard-widget.tsx`, `arc-dashboard-widget.test.tsx` |
| 338 | R96 | DoD elevation | `voice/__init__.py`, `cli/voice.py`, `tests/voice/test_voice_r96.py` |
| 339 | R97 | DoD elevation | `security/policy_templates/__init__.py`, `cli/sandbox.py`, `tests/.../test_policy_templates_r97.py` |
| 340 | R98 | DoD elevation | `composer/__init__.py`, `cli/composer.py`, `tests/composer/test_composer_r98.py` |
| 341 | R99 | DoD elevation | `debug/__init__.py`, `cli/debug.py`, `tests/debug/test_debug_r99.py` |
| 342 | R100 | DoD elevation | `notebook/__init__.py`, `cli/notebook.py`, `tests/notebook/test_notebook_r100.py` |
| 343 | R101 | DoD elevation | `time_travel/__init__.py`, `cli/time_travel.py`, `tests/time_travel/test_time_travel_r101.py` |
| 344 | R102 | DoD elevation | `migrate/__init__.py`, `cli/migrate.py`, `tests/migrate/test_migrate_r102.py` |
| 345 | R83 | DoD elevation | `cli/predict_cmd.py`, `tests/test_predict_r83.py` |
| 346 | R84 | DoD elevation | `index/__init__.py`, `cli/index_cmd.py`, `tests/test_index_r84.py` |
| 347 | R85 | DoD elevation | `cli/context_cmd.py`, `tests/test_context_r85.py` |
| 348 | R90 | DoD elevation | `cli/memory_cmd.py`, `tests/test_memory_r90.py` |
| 349 | R-PERF7 | DoD elevation | `index/__init__.py`, `tests/index/test_incremental_index_r_perf7.py` |
| 350 | R-SEC2 | DoD elevation | `security/prompt_guard.py`, `cli/security_cmd.py` (new), `tests/security/test_prompt_guard.py` |
| 351 | R-SEC3 | DoD elevation | `scripts/check-sbom-integrity.sh`, `.github/workflows/python.yml`, `tests/security/test_sbom_integrity.py` (new) |
| 352 | R-PERF6 | DoD elevation | `orchestration/event_broker.py`, `tests/test_perf_r85_r86_r87.py` |
| 353 | R-PERF8 | DoD elevation | `providers/agentrouter_proxy.py`, `tests/test_perf_r85_r86_r87.py` |
| 354 | R-PERF9 | DoD elevation | `wasm_parser/__init__.py`, `tests/wasm_parser/test_wasm_parser_r_perf9.py` |
| 355 | R-PROC1 | DoD elevation | `release_intelligence/__init__.py`, `cli/release_cmd.py` (new), `tests/release_intelligence/...` |
| 356 | R-PROC2 | DoD elevation | `release_snapshots/__init__.py`, `cli/release_cmd.py`, `tests/release_snapshots/...` |
| 357 | parity | Hardening | `cli/context_cmd.py`, `cli/memory_cmd.py`, `cli/_subapps.py` |
| 358 | `--json` | Hardening | All new `cli/*.py` modules (audit-driven) |
| 359 | security | Hardening | Confirmation gate audit across `cli/*.py` |
| 360 | perf | Hardening | `time_travel/__init__.py`, `notebook/__init__.py`, `debug/__init__.py`, `release_intelligence/__init__.py` |
| 361 | reliability | Hardening | `voice/__init__.py`, `debug/__init__.py`, `tasks/scheduler.py` |
| 362 | quality | Type/lint | All new `src/agent_runtime_cockpit/*/` modules (mypy --strict) |
| 363 | docs | Sweep | `docs/roadmap.md`, `docs/phases.md`, `AGENTS.md` |
| 364 | gate | Final sweep | `docs/phases.md` |
| 365 | release | Snapshot | `docs/phases.md`, `docs/roadmap.md` |

---

## Continuation prompt (copy-paste to resume)

```
Continue implementing ARC Studio. Read docs/roadmap.md, docs/phases.md, and AGENTS.md first.
The active execution plan is docs/prompts/execute-phases-336-365.md.
Start at the lowest-numbered phase that is NOT yet in docs/phases.md.
For each phase: implement the change, add/update tests, run:
  cd python && uv run ruff check src tests
  cd python && uv run pytest tests/ -q
  pnpm typecheck && pnpm build
  bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md
Fix any failures before committing. Commit with the style shown in the plan.
Update docs/roadmap.md and docs/phases.md in the same commit or an immediate follow-up.
Continue to the next phase without stopping unless tests fail or the action is destructive/irreversible.
Do not overclaim status — Baseline Complete means happy-path works; Polished Complete requires all 8 DoD gates cited with evidence.
```
