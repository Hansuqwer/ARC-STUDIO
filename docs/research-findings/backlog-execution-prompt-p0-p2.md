# ARC Studio — P0→P2 Backlog Execution Prompt (12 items, recommended order)

> Executes CR-002, CR-004, CR-005, CR-008, CR-010, CR-007, CR-012, CR-019, CR-016, CR-017, CR-018, CR-014
> from `critical-review-v2-execution-2026-06-07.md`, in the recommended risk-adjusted order.
> Continuation of the DoD-elevation track (R-POLISH1–3 / Phases 159–161 already landed).

---

## Role & effort

Senior engineer + adversarial reviewer. Run sub-agents at the **highest available effort** (requesting env: Sonnet 4.6, max effort). Orchestrate **up to 5 sub-agents**, but only where it is conflict-safe (see §Orchestration).

## Non-negotiable discipline (this has repeatedly caught wrong findings)

1. **Verify before you claim or edit.** Read the real current code for every item before changing it. This session has disproved multiple prior "facts": 3 false dead-code targets, a `workspace.py` shadowed by a `workspace/` package, a contract test that *asserted* the anti-pattern, and a provider that *already* redacted. Treat every backlog description as a hypothesis to confirm against source.
2. **Research before each item:** Context7 (current library docs) + Vercel Grep / GitHub code search (real-world idioms) + repo grep. Log what each tool returned. If a tool is unavailable, say so; never fake it.
3. **Continue on green.** After an item's tests + lint are green, commit it and move to the next. If red, fix the root cause before proceeding; if an approach fails twice, step back and rethink.
4. **Additive only.** No protocol field / public CLI / widget removals. Deterministic security (no LLM allow/deny). Secrets redacted. Paid calls gated.
5. **Anti-overclaim.** Status follows evidence. No "production-ready/complete/secure" wording; `scripts/check-banned-claims.sh` is authoritative. Record landed work in `docs/phases.md` + `docs/roadmap.md` in place (new phase + R-POLISH/R-id rows), never new status docs.
6. **Leave the pre-existing uncommitted arena work untouched.** Stage only the files you change per item. No commits unless the work is green.
7. **DoD gates** (AGENTS.md): each slice cites evidence for the gates it touches — UX states, a11y, parity, tests, perf, security, reliability, docs.

## Orchestration (≤5 sub-agents, conflict-aware DAG)

- **Research fan-out (parallel, read-only, safe):** up to 5 research agents, one per batch below, each producing: Context7 docs used, Grep idioms, verified current-code findings (file:line), a proposed minimal diff, the exact tests, and risks. Research agents **do not edit files**.
- **Implementation (sequenced by file-conflict, integrator-owned):** the lead integrates each batch's research, makes the edits, writes/extends tests, runs verification, and commits when green. Batches that share files MUST be sequential.
- **File-conflict map (why batches are sequenced, not all-parallel):**
  - `mcp/proxy.py` ← CR-005 **and** CR-018 (same file → same batch)
  - `mcp/server.py` ← CR-004; `cli/mcp.py` ← CR-008 (MCP batch)
  - `tui/screen.py` ← CR-002 (also touched by the already-landed CR-024 → re-read first)
  - Theia `node/services/*.ts` ← CR-007 (notification) + CR-012 (run-lifecycle, config) (TS batch)
  - `security/profiles.py` ← CR-019; `swarmgraph_ir/validation.py` ← CR-017 (py-correctness batch)
  - `arc-extension/.../arc-event-stream-widget.tsx` ← CR-014 (perf)
  - SwarmGraph bridge ← CR-016 (producer-gated, isolated, do last)

## Recommended order → batches

**Batch A — MCP security cluster (CR-004, CR-005, CR-008, CR-018)** · R26 / Phase 78 (+ proxy timeout)
- CR-004: route MCP **resources** through `_tool_result()` risk gate + audit (`mcp/server.py`).
- CR-005: MCP proxy `env=None` must always `_sanitise_env` (`mcp/proxy.py`).
- CR-008: `arc mcp serve` Rich output → stderr on stdio transport (`cli/mcp.py`).
- CR-018: MCP proxy timeout + ≤1 MB structured error envelope (`mcp/proxy.py`).
- Verify: `cd python && uv run ruff check src tests && uv run pytest tests/mcp -q`.

**Batch B — TUI paid-call fail-closed (CR-002)** · R-POLISH1 / new Phase 162
- Flip `allow_paid` default to fail-closed in `tui/screen.py`/`data.py`; audit on allow; confirm-to-enable.
- Verify: `uv run pytest tests/tui -q && uv run ruff check src tests`.

**Batch C — CLI mutation confirmation gates (CR-010)** · R69 / Phase 69
- Confirmation gate on `arc policy rule-add/rule-remove` and `arc sandbox audit-compact` (+ `--yes`/`--force` for scripting); deterministic.
- Verify: `uv run pytest tests/ -q -k "policy or sandbox_audit" && uv run ruff check src tests`.

**Batch D — Theia Node env allowlist + async (CR-007, CR-012)** · R52/63 + R14/new 163
- CR-007: `NotificationBackendService` uses a `buildArcCliEnv` allowlist on the CLI bridge.
- CR-012: convert `startRun`/`getConfigStatus`/`saveConfig` (+ `listRuntimeCapabilities` if sync) from `execFileSync` to `execFileAsync` (non-blocking).
- Verify: `pnpm --filter arc-extension build && pnpm --filter arc-extension test && pnpm typecheck`.

**Batch E — Python correctness (CR-019, CR-017)** · R50/active + R17/17
- CR-019: profile schema version guard + v1→v2 migration in `security/profiles.py`.
- CR-017: DFS `_detect_cycles()` in `swarmgraph_ir/validation.py` (reject cyclic graphs).
- Verify: `uv run pytest tests/ -q -k "profile or swarmgraph_ir or validation" && uv run ruff check src tests`.

**Batch F — IDE perf (CR-014)** · R24 / 24
- Bound `liveEvents` at ~2000 with an eviction banner (`arc-event-stream-widget.tsx`); reuse `VirtualizedEventList`.
- Verify: `pnpm --filter arc-extension build && pnpm --filter arc-extension test && pnpm typecheck`.

**Batch G — SwarmGraph SDK→IDE bridge (CR-016, producer-gated, LAST)** · R15 / 15
- Add `translate_swarmgraph_event` producer; **until fully wired, the IDE tab MUST show a degraded "no SwarmGraph producer connected" state** (producer-truth). Do not render invented data.
- Verify: `uv run pytest tests/ -q -k swarmgraph` + `pnpm --filter arc-extension build`.

## Per-item protocol (every item)

1. **Research:** Context7 (relevant lib: MCP SDK / Theia / Typer / Textual), Vercel Grep / GitHub for idioms, repo grep. Log results.
2. **Verify current code:** read the exact file(s); confirm the issue still exists as described; correct the hypothesis if not.
3. **Implement** the smallest safe change; reuse canonical helpers (e.g., `security.redaction`, existing audit builders) — do not duplicate.
4. **Tests:** add/extend; deterministic, offline. Update any test that encoded the old (wrong) behavior — strengthen, don't weaken.
5. **Verify green:** run the batch's lint + tests (+ build/typecheck for TS).
6. **Record + commit:** add `phases.md`/`roadmap.md` rows; `check-banned-claims.sh`; stage only changed files; commit; continue to next item.

## Final report

Per item: what was verified, what changed, tests run (exact results), roadmap/phase rows added, commit hash, and any hypothesis the code disproved. End with the updated backlog status and `git status --short`.
