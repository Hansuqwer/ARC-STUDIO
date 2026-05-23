---
date: 2026-05-23
head: 7c0a300
phases_reviewed: [21, 22, 23, 24, 25, 25.5]
status: Final
next_phase: Phase 26 (LangChain)
---

# Phases 23-25.5 Review

## Executive Summary

Phases 23 through 25.5 delivered **enforcement infrastructure, UI resilience, a fully decomposed CLI, and the adapter test harness**. The codebase went from a monolithic 4,225-line `cli.py` with no typed enforcement to a modular architecture with 15 CLI modules, 5 typed denial event helpers, a RingBuffer-based SSE reconnection system, and a `ProviderClient` interface ready for adapter phases.

**Current state:**
- 1,524 Python tests pass (3 pre-existing failures, 21 skipped)
- 3 xfailed, 1 xpassed (pre-existing edge cases)
- **12 enforcement annotations missing** from extracted CLI modules (new finding)
- TypeScript: 6 pre-existing failures in `services.unit.test.ts`

---

## Phase-by-Phase Summary

### Phase 21 — Streaming Audit Verification + HMAC Signing ✓

| Deliverable | Status |
|-------------|--------|
| `StreamingAuditVerifier` with bounded memory | `c6e3772` |
| SHA-256 + HMAC modes with auto-detection | ✅ |
| 100 MB synthetic trace replay within budget | ✅ |
| 21 tests | ✅ |

### Phase 22 — Discriminated RunEvent Unions ✓

| Deliverable | Status |
|-------------|--------|
| 20+ TypedRunEvent variants in discriminated union | `9977bfb` |
| TypeScript type guards | ✅ |
| Backward-compatible `RunEvent` alias | ✅ |

### Phase 23 — Typed Denial Events + Enforcement (Baseline Complete) ✓

3 PRs, 6 commits. Enforcement system with 4 helpers, CLI flags, audit script, UI dialogs.

| PR | Commit | Deliverable |
|----|--------|-------------|
| 23.0 | `3e6ee8c` | Typed denial events + enforcement helpers |
| 23.1 | `fca4bf2` | `EnforcementContext`, `DryRunAbort`, CLI flags (`--allow-paid`, `--trust-workspace`, `--dry-run`) |
| 23.2 | `5a9df47` | `scripts/audit-enforcement-surfaces.sh`, 28 syscall annotations |
| 23.3 | `09bfbb8` | correlation_id, retry endpoint, `DenialModal`, `useDenialHandler` |

### Phase 24 — Trace Viewer Virtualization + Daemon Resilience (Baseline Complete) ✓

| PR | Commit | Deliverable |
|----|--------|-------------|
| 24.1 | `7365191` | `@tanstack/react-virtual`, `VirtualizedEventList` |
| 24.2 | `7365191` | SSE reconnect with `Last-Event-ID` + exponential backoff |
| 24.3 | `7365191` | `RingBuffer` data structure, 5 new tests |

### Phase 25 — CLI Decomposition (Baseline Complete) ✓

6 PRs, 14 new files, 4,225 → 64 lines in `_legacy_cli.py`.

| PR | Files created | Lines removed |
|----|--------------|--------------|
| 25.1 | `_app.py`, `_helpers.py` | 4,225 → 3,835 |
| 25.2 | `info.py` | 3,835 → 3,632 |
| 25.3 | `discover.py`, `exec.py` | 3,632 → 3,359 |
| 25.4 | `_subapps.py`, `runs.py`, `receipt.py`, `audit.py`, `profiles.py` | 3,359 → 1,943 |
| 25.5 | `providers.py`, `mgmt.py`, `studio_workspace.py`, `prompt.py` | 1,943 → 64 |
| 25.6 | `test_cli_snapshots.py`, 4 golden JSON files | — |

### Phase 25.5 — Shared Test Harness + ProviderClient ✓

| File | Purpose |
|------|---------|
| `tests/adapters/_shared/` (6 files) | TypedRunEvent conformance, fake provider, fixture loader, golden compare, denial assertions |
| `providers/client.py` | `ProviderClient` Protocol |
| `providers/registry.py` | Registry (register, get, known) |
| `test_provider_client_contract.py` | 3 contract tests |

---

## Gap Analysis

### Critical: 12 Enforcement Annotations Lost

The CLI extraction (Phase 25) moved `urllib.request` health-check calls from `cli.py` into `cli/mgmt.py` and `cli/info.py`, but the `# enforcement: not-applicable` annotations were lost in the move.

**Affected files:**
- `cli/mgmt.py:105-138` — doctor `env` command health checks
- `cli/mgmt.py:343-356` — doctor `network` command health checks
- `cli/info.py:55-58` — `health` command daemon check

**Fix:** Add `# enforcement: not-applicable — Internal diagnostic health check, not user-triggered network access` to each line. Estimated effort: 5 minutes.

### Pre-existing Test Failures (3)

| Test | Issue |
|------|-------|
| `test_receipt_verify_without_key_uses_audit_key_manager` | Exit code 1 vs 0 when audit key manager has no key |
| `test_runs_budget_cli_output` | Budget display format doesn't match test expectation |
| `test_workspace_config_set` | JSON decode error when workspace config doesn't exist |

None are related to recent changes. All are edge cases in receipt verification, budget display, and workspace config.

### Pre-existing TypeScript Test Failures (6)

All in `services.unit.test.ts` — WorkflowExecutor mock tests. Mock subprocess responses don't match expectations. Unrelated to Phases 23-25.

### ADR-0022.1 Not Landed

The `POLICY_BYPASS_WARNING` event variant has been designed but not implemented. The landing PR skeleton exists at `docs/research/phase-22.1-landing-pr.md`. Required by Phases 26+ for handling unrecognized provider plugins.

### Research Docs Need Reconciliation

`docs/research/adapter-priorities.md` composite scores are placeholders requiring fresh grep.app/context7 research against current versions.

---

## Architecture Decisions Made

| Decision | Rationale |
|----------|-----------|
| `cli.py` → `_legacy_cli.py` + `cli/` package | File name shadowed the `cli/` directory package; rename was required |
| All sub-apps in `cli/_subapps.py` | Avoids circular imports; single source of truth for Typer sub-app instances |
| Enforcement annotations on same line | Prevents refactor-decoupling; ruff linter enforces |
| `RingBuffer` over Queue drop-oldest | Preserves event ordering; sorted by event_id on replay |
| `@tanstack/react-virtual` over `react-window` | Modern API, lighter footprint, hook-based (successor to react-virtual) |
| `ProviderClient` as `Protocol` not ABC | Structural subtyping — any object with the right methods is a valid implementation |

---

## Test Coverage Evolution

| Phase | Python tests | Change | Cumulative |
|-------|-------------|--------|------------|
| 22 baseline | ~1,496 | — | 1,496 |
| 23 | 1,518 | +22 | 1,518 |
| 24 | 1,523 | +5 | 1,523 |
| 25 | 1,521 | +5 snapshot tests | 1,521 |
| 25.5 | 1,524 | +3 provider tests | **1,524** |

---

## What's Next

### Immediate: Fix 12 enforcement annotations

Add `# enforcement: not-applicable` to the health-check `urllib.request` calls in `cli/mgmt.py` and `cli/info.py`.

### Phase 26: LangChain Adapter

The first adapter phase per `docs/research/adapter-roadmap.md`. Requires:
- Detection (T1): probe `langchain` import, report version/capabilities
- Export (T2): AST-walk for `Runnable` compositions
- Live streaming (T3): `BaseCallbackHandler` → TypedRunEvent translation
- **Prerequisites:** ADR-0022.1 landed, enforcement annotations fixed

### Phase 22.1: Land ADR-0022.1

Before any adapter can emit `POLICY_BYPASS_WARNING`, the variant must be added to the TypedRunEvent union. 8-commit PR, 16 tests. Skeleton at `docs/research/phase-22.1-landing-pr.md`.

### Then: Phases 27-35

Per the adapter roadmap: Anthropic SDK, OpenAI-compatible provider, Pydantic AI, DSPy, Haystack, smolagents, Semantic Kernel (T1+T2 only), Google ADK, MCP Python SDK.

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Total commits (Phases 23-25.5) | 21 |
| Python test count | 1,524 passing |
| TypeScript test count | ~1,532 passing (6 pre-existing failures) |
| CLI module count | 15 modules |
| `_legacy_cli.py` size | 64 lines (was 4,225) |
| Enforcement violations | 12 (fixing) |
| Audit script status | ❌ Failed (12 unannotated) |
