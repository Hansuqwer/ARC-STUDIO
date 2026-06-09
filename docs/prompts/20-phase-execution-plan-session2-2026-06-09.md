# 20-Phase Execution Plan — 2026-06-09 (Session 2)

**Starting state:** Phase 294 complete · 6135 Python tests · 288 TS test files · ruff clean · origin/main @ 9df0dcf2

**Known gap:** R-SEC4 implemented (commit 11ef03f2) but roadmap still shows `Not Started` — fix in Phase 295.

**Priority order:**
1. Fix roadmap gap (R-SEC4) — Phase 295
2. Elevate R86/R87/R88/R89/R-SEC1/R-PERF2-5/R-PROC3-6 to Polished Complete via DoD gates — Phases 296–305
3. New features: R84 (ARC Index), R85 (ARC Context), R83 (ARC Predict), R90 (ARC Memory) — Phases 306–313
4. Security/process residuals: R-SEC2, R-SEC3, R-PERF1 — Phases 314
5. Sweep + release snapshot — Phase 315

## Phase 295 — Fix: R-SEC4 roadmap status + R-SEC4/R88/R89/R86/R87 DoD evidence record
## Phase 296 — Polished Complete: R87 ARC Stream (producer-truth, parity, accessibility DoD gates)
## Phase 297 — Polished Complete: R86 ARC Continuum (`arc continuum` --help snapshot, parity, TUI degraded state)
## Phase 298 — Polished Complete: R88 ARC Git (parity CLI↔TUI, error states, `--help` snapshot)
## Phase 299 — Polished Complete: R89 ARC Diff (hunk accessibility, parity, error states)
## Phase 300 — Polished Complete: R-SEC1 + R-SEC4 (security gate evidence, confirm deterministic decisions)
## Phase 301 — Polished Complete: R-PERF2/3/4/5 (measured timings, buffer bounds, evidence)
## Phase 302 — Polished Complete: R-PROC3/4/5/6 (CI runs clean, snapshot output, date check works)
## Phase 303 — R84a: `arc index build` — local SQLite/FAISS semantic codebase index skeleton
## Phase 304 — R84b: `arc index search <query>` — top-k symbol + file results
## Phase 305 — R85a: `arc context suggest` — automatic context file retrieval for a prompt
## Phase 306 — R85b: `arc context attach` — inject retrieved context into next agent run
## Phase 307 — R90a: `arc memory save/load` — Fernet-encrypted persistent project knowledge store
## Phase 308 — R90b: `arc memory search <query>` — keyword/embedding search over saved notes
## Phase 309 — R83a: `arc predict next-edit` — next-edit autocomplete stub with local LM fallback
## Phase 310 — R-SEC2: `prompt_guard.py` — deterministic regex injection-pattern detection
## Phase 311 — R-SEC3: Python SBOM via `pip-audit --json` + `pnpm-lock.yaml` integrity check
## Phase 312 — R-PERF1: Streaming workspace inventory — async generator, < 5s for 100K files
## Phase 313 — R-PERF8: Provider connection pooling — aiohttp `TCPConnector(limit_per_host=10)`
## Phase 314 — R-PERF6: Memory-mapped trace reading — `mmap` for large JSONL traces
## Phase 315 — Sweep: ruff/mypy/TS typecheck + banned-claims + roadmap/phases + release snapshot v0.9

---

## Workflow per phase

```
For each phase:
1. Read relevant source files / context7 / grep GitHub if needed
2. Implement (minimal, correct)
3. Test (uv run pytest / npx jest)
4. Verify ruff clean + banned-claims clean on changed docs
5. Commit + push
6. Update docs/phases.md + docs/roadmap.md in the final sweep phase
```

**Rules (per AGENTS.md):**
- Finish 1→100% before broadening: complete each phase end-to-end before starting the next.
- Additive only — no existing CLI/API surface removal.
- Evidence over claims — state what was actually run.
- No commits unless tests pass + ruff clean.
