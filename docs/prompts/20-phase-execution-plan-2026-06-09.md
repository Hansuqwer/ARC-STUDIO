# 20-Phase Execution Plan — 2026-06-09

**Starting state:** Phase 274 complete · 6065 Python tests · ruff clean · stubs at
`stream/websocket.py` + `continuum/store.py` · ADR-030 locked.

**Order:** R87 first (ADR-030 foundational prerequisite), then R-PROC3/5/6, then R-SEC1, then
R-PERF residuals, then R88/R89. Each phase: research/verify → implement → test → commit → push.

## Phase 275 — R87a: GlobalEventBroker + `/api/events/stream` SSE endpoint
## Phase 276 — R87b: Wire EventBroker terminal events → GlobalEventBroker
## Phase 277 — R87c: TuiEventSource SSE client + replace NotificationBadge poll
## Phase 278 — R86a: SessionStore `_init_db` + `_encrypt`/`_decrypt` + transcript
## Phase 279 — R86b: `ui_state` + `run_context` + `arc continuum list/resume` CLI
## Phase 280 — R-PROC6: `check-patches-freshness.sh` + CI gate
## Phase 281 — R-PROC3: `generate-release-snapshot.sh` + release workflow
## Phase 282 — R-PROC5: Date-fabrication detection in `check-banned-claims.sh`
## Phase 283 — R-SEC1: `TOOL_RISK_LEVELS` + `arc_run_start` subprocess isolation
## Phase 284 — R-PERF4 residual: `startRun()` async + `EditPlanBridge` non-blocking
## Phase 285 — R-PERF2 residual: Virtualize `TraceViewerSection`/`AssuranceTab` lists
## Phase 286 — R-PERF3: Lazy provider loading (< 2s startup)
## Phase 287 — R-PERF5: SQLite WAL auto-checkpoint tuning
## Phase 288 — R-SEC4 residual: `run_id` allowlist + `relative_to()` confinement
## Phase 289 — R88a: `arc git-native init` + auto-branch per session
## Phase 290 — R88b: Auto-commit on every agent file edit + auto-revert on failure
## Phase 291 — R89a: `InlineDiff` TUI widget + `arc diff apply --interactive`
## Phase 292 — R89b: IDE `DiffHunk` accept/reject component
## Phase 293 — R-PROC4: Normalize `arc-theia-studio` alias → `ARC-STUDIO` in docs
## Phase 294 — Sweep: ruff/mypy/TS typecheck clean + banned-claims + release snapshot
