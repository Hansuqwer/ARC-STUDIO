# Batch 6 — ARC CR Backlog + Mobile Hardening (20 tasks)

Execute on `main` (single trunk, no PRs — see `docs/handover/SINGLE-BRANCH-WORKFLOW.md`). One
commit per task, tests green before each push. Discipline: research-first → verify against
real code → smallest safe additive change → tests → commit → record in `docs/phases.md` +
`docs/roadmap.md` → push. Mobile stays **Simulator Preview** (fixtures only, no real device
access; deterministic security, no LLM allow/deny). Gates: `cd python && uv run ruff check src
tests && uv run pytest tests/ -q` · `pnpm --filter @arc-studio/protocol test` · `pnpm
typecheck` · `bash scripts/check-banned-claims.sh`.

## Track A — Close the critical-review-v2 CR backlog (5)

**A1 (CR-036) MESSAGE event schema mismatch.** Reconcile the event registry's `text` field
with the typed MESSAGE model (additive only). Files: `protocol/` + `tui`. Tests: protocol +
Python↔TS parity. Acceptance: registry shape matches the typed model; parity green.

**A2 (CR-021) `arc wallet` CLI↔README parity.** Verify `arc wallet` exists and matches the
README; fix the doc or add the missing command/alias. Tests: CLI snapshot. Acceptance: README
command runs as documented.

**A3 (CR-034) eval synthetic-labelling completeness.** Ensure every synthetic/simulated eval
metric carries the `synthetic` label through CLI + JSON. Files: `evals/*`. Tests: label
present on all synthetic results. Acceptance: no unlabeled synthetic metric.

**A4 (CR-043) write `McpCallDecisionEvent` v2.** The schema is defined but never emitted — wire
the producer at the MCP per-call decision point. Files: `protocol/mcp_decision_events.py`,
`mcp/*`. Tests: event emitted + typed + parity. Acceptance: decision path writes the event.

**A5 (CR-045) DoD automated CI gate.** Add a CI job running `scripts/check-banned-claims.sh`
(+ assert `docs/roadmap.md`/`docs/phases.md` present) so the DoD wording gate is enforced, not
manual. Files: `.github/workflows/*`. Acceptance: CI fails on a banned claim.

## Track B — Mobile CI hardening (4)

**B1 mobile-rn CI gate.** New `.github/workflows/mobile-rn.yml` running `test_mobile_rn.py`
(recursive forbidden-symbol + TurboModule contract). Acceptance: gate fails on a sensitive symbol.

**B2 mobile-flutter CI gate.** New `.github/workflows/mobile-flutter.yml` running
`test_mobile_flutter.py` (+ `flutter analyze`/`test` when the toolchain is present, best-effort).

**B3 SBOM release gate.** Add `arc mobile sbom` generation + a presence/shape check to
`scripts/release_check.sh`. Acceptance: release check emits + validates the SBOM.

**B4 compliance + native-safety release gate.** Add the recursive forbidden-symbol scan +
`generate compliance-report` to `release_check.sh`. Acceptance: release check fails on any
real device symbol.

## Track C — Surface the new mobile modules through the CLI (6)

**C1 `arc mobile gate evaluate`.** Expose `CapabilityEntryGate` decisions (eligible/missing,
always `route=fixtures`). Tests: denied-by-default + eligible-but-fixtures via CLI.

**C2 `arc mobile flags`.** list / enable / disable / kill-switch over `FeatureFlags`
(default-off). Tests: kill switch overrides; CLI round-trip.

**C3 `arc mobile egress check`.** Surface `EgressGuard` decisions (budget/per-class/critical
block). Tests: over-budget + critical-blocked via CLI.

**C4 `arc mobile queue`.** enqueue / flush / gc / status over `OfflineQueue` (hash-only).
Tests: TTL expiry + hash-only output.

**C5 `arc mobile secure-store`.** put / get / export / delete over `SecureLocalStore` —
**redacted output**, never prints raw secret values. Tests: no-plaintext in CLI output.

**C6 `arc mobile audit-retention`.** Apply TTL/rotation to the decisions audit log via
`audit_retention`. Tests: prune-by-age/count via CLI.

## Track D — Mobile integration + DoD elevation (5)

**D1 Gate the simulate path.** Route `simulate` through `CapabilityEntryGate` so a native
capability records its gate decision; default-off → fixtures (unchanged behavior). Tests:
gated decision recorded; still fixtures.

**D2 Wire `TenantPolicyHook` into `arc mobile` policy explain.** Accept a signed org bundle →
RBAC/ABAC/tenant denials in the decision. Tests: bundle-denied capability via CLI.

**D3 mypy pass on new mobile modules.** Add `mobile/{secure_store,offline_queue,capability_gate,
feature_flags,policy_context,siem_export,sbom,mcp_bridge,audit_retention}.py` to the scoped
mypy gate; fix types. Acceptance: `mypy` clean on the set.

**D4 Mobile docs refresh.** Update `docs/mobile/REAL_VS_MOCK.md` (+ MOBILE_RUNTIME_SDK) with the
new modules — honest matrix, simulator-preview. Acceptance: `check-banned-claims` green; matrix
lists every new module's real-vs-mock status.

**D5 Strengthen security tests.** Property/fuzz tests for `secure_store` (tamper/wrong-key),
`egress_guard` (random byte costs/classes), `capability_gate` (negative space). Acceptance:
fuzz finds no bypass; coverage of the security modules raised.

## Batch acceptance
All 20 committed to `main` with tests; full Python suite + `@arc-studio/protocol` (coverage) +
`pnpm typecheck` + `check-banned-claims` green; each recorded in `docs/phases.md` + `docs/
roadmap.md`. Posture unchanged: Simulator Preview; no real device access; Phase 11 stays an
entry-gate that routes to fixtures.

## Progress log (Batch 6)

- **A1 ✅ (CR-036)** Aligned typed `MessageData` to the MESSAGE event registry + TS shape: body field is `text` (+ source/coalesced/node_id/message_id/tool_call_id/evidence_refs optionals); dropped the diverged, unused `content`/`role`. Regression guard `tests/protocol/test_message_event_registry_parity.py` (4) locks registry==typed==TS. 82 protocol tests pass.
- **A2 ✅ (CR-021)** README documented a non-existent `arc wallet`/`arc wallet budget` CLI; wallet/budget are TUI (`/wallet`,`/budget`) + CLI `arc runs budget <run-id>`. Corrected the Token Budget section + added guard `tests/test_readme_cli_parity.py` (3).
- **A3 ✅ (CR-034)** Eval synthetic-labelling completeness: individual results + the single-run path already carried `synthetic`/`[synthetic/simulated]`, but the 3 batch aggregate payloads + headers omitted it. Added a top-level `synthetic` flag (all-results-synthetic) + `[synthetic]` header prefix to golden-file / golden-dir / --batch summaries via `_batch_synthetic`/`_synthetic_prefix`. Test `test_eval_synthetic_labelling.py` (4).
