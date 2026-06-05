---
title: Phase 22.1 — Landing PR for ADR-0022.1 (POLICY_BYPASS_WARNING)
parent: docs/adr/ADR-0022.1.md
date: 2026-05-22
status: DRAFT — apply when ADR-0022.1 is accepted
required_by: [Phase 26, Phase 30, Phase 31, Phase 32, Phase 34]
test_count: 16
---

# Phase 22.1

Additive variant `POLICY_BYPASS_WARNING` in TypedRunEvent union; helper `emit_policy_bypass_warning`; UI banner; audit-query filter.

## Why standalone

Required-by Phases 26, 30, 31, 32, and 34. Bundling into Phase 26 would couple two reviews. Standalone PR makes blast radius visible: protocol surface only.

## Commit series

### Commit 22.1.1 — Python Pydantic model and enum

**Files:**
- `python/src/agent_runtime_cockpit/protocol/events.py` — extend union
- `python/src/agent_runtime_cockpit/protocol/_bypass.py` — new module

**Add:** `PolicyBypassReason(StrEnum)` with 5 values: `UNKNOWN_PROVIDER_PLUGIN`, `CUSTOM_HTTP_CLIENT`, `CUSTOM_SUBPROCESS_RUNNER`, `UNINSTRUMENTED_TOOL`, `UPSTREAM_BYPASSED_BOUNDARY`.

**Add:** `PolicyBypassWarning(TypedRunEventBase)` with `kind: Literal["POLICY_BYPASS_WARNING"]`, `run_id`, `parent_run_id`, `timestamp`, `policy_id`, `bypass_reason`, `surface`, `surface_identifier`, `suggested_remediation`.

**Tests:** 5 — construction, validation rejects unknown reason, JSON round-trip, enum coverage, payload completeness.

### Commit 22.1.2 — TypeScript mirror

**Files:** `packages/arc-protocol-ts/src/events.ts`, `package.json` (bump minor).

**Tests:** 3 — type guard narrows, JSON serialization, unknown reason fails type guard.

### Commit 22.1.3 — Enforcement helper and rate-limit

**Files:** `python/src/agent_runtime_cockpit/security/enforcement.py` (add `emit_policy_bypass_warning`), `security/_bypass_rate_limit.py`.

Helper mirrors four Phase 23 helpers. Rate-limit: one per `(run_id, surface_identifier)` per run, dedup state lives in same `contextvar` as EnforcementContext.

**Tests:** 1 — 100 calls same (run_id, surface_identifier) → 1 event; 100 calls distinct identifiers → 100 events.

### Commit 22.1.4 — Audit verifier compatibility

**Files:** `python/tests/audit/test_verifier_with_bypass_warnings.py`.

**Tests:** 1 — 100 MB synthetic trace with 10,000 bypass warnings replays within Phase 21 budget; HMAC validates.

### Commit 22.1.5 — UI banner

**Files:** `packages/arc-extension/src/ui/PolicyBypassBanner.tsx`, `EventChannelSubscriber.ts`, `AuditView.tsx`.

Non-blocking banner when ≥1 bypass warning fires. Dismiss per-run, not per-session.

**Tests:** 3 — banner appears with ≥1 warning, stays dismissed within same run, re-appears on fresh run.

### Commit 22.1.6 — arc audit query filter

**Files:** `python/src/agent_runtime_cockpit/audit/cli.py`.

`arc audit query --kind POLICY_BYPASS_WARNING --run <id>` returns matching events. Composes with existing filters.

**Tests:** 2 — filter isolation, filter composition with --surface.

### Commit 22.1.7 — Documentation

**Files:** `docs/protocol/events.md` (new section), `docs/security/enforcement-surfaces.md` (decision-tree diagram), `docs/adr/ADR-0022.1.md` (status → Accepted), `docs/phases.md` (Phase 22 note), `CHANGELOG.md`.

### Commit 22.1.8 — E2E smoke

**Files:** `python/tests/e2e/test_bypass_warning_e2e.py`.

**Tests:** 1 — emit, replay, query; end-to-end round-trip.

## Verification

```bash
pytest python/tests/protocol/test_policy_bypass_warning_model.py -v
pytest python/tests/security/test_emit_policy_bypass_warning.py -v
pytest python/tests/audit/ -v
pytest python/tests/ -q
pnpm --filter @arc/arc-protocol-ts test
pnpm --filter @arc/arc-extension test
bash scripts/audit-enforcement-surfaces.sh
bash scripts/check-banned-claims.sh
```

## Exit gate

All 8 commits merged. 16 tests green. Protocol-ts minor version bumped. ADR-0022.1 accepted. Architecture review **not required** — additive protocol amendment without new gated surfaces.
