# 14 — Testing Strategy

## Summary

Cockpit implementation must stay offline, deterministic, fixture-backed, and contract-first. CI must never call paid providers. Runtime tests use fakes unless explicitly gated by `ARC_REAL_RUNTIME_SMOKE=1`.

## Required Commands

Run before merging any cockpit slice:

```bash
cd python && uv run pytest -q
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
```

Optional targeted loops:

```bash
cd python && uv run pytest -q tests/test_cockpit_contracts.py
cd python && uv run pytest -q tests/cli/test_cockpit_cli.py
pnpm --filter arc-extension test
```

## CI Policy

| Area | Policy |
|------|--------|
| Paid providers | Forbidden in normal CI |
| Network | Mocked or skipped unless explicit smoke gate set |
| Real runtimes | Fake adapters by default |
| Golden data | Stored under fixtures, redacted |
| Secrets | Synthetic only, never real tokens |
| Time | Frozen or injected clock |
| IDs | Deterministic IDs in fixtures |
| Theia UI | Static source-pattern tests unless runtime harness exists |

## Test Layers

| Layer | Purpose | Files |
|-------|---------|-------|
| Python unit tests | Schemas, state transitions, storage, redaction, audit | `python/tests/test_cockpit_*.py` |
| CLI tests | Commands, output contracts, exit codes | `python/tests/cli/test_cockpit_*.py` |
| TypeScript builds | Protocol compatibility, frontend compile | `packages/arc-extension`, `packages/arc-protocol-ts` |
| Theia static tests | Component contracts without browser runtime | `packages/arc-extension/src/test/**/*.test.ts` |
| E2E tests | CLI-to-storage-to-event flow, fake runtime only | `tests/e2e/cockpit/*.spec.ts` or `python/tests/e2e/test_cockpit_*.py` |
| Security tests | Redaction, trust, blocked env, no secret persistence | `python/tests/security/test_cockpit_*.py` |
| Audit tests | HMAC chain, receipts, evidence hashes | `python/tests/audit/test_cockpit_*.py` |

## Fixture Design

Store reusable fixtures under:

```text
python/tests/fixtures/cockpit/
  run_contract.accepted.json
  run_contract.violated.json
  run_receipt.success.json
  run_receipt.failed.json
  failure_autopsy.timeout.json
  evidence_ref.file_diff.json
  capability_snapshot.swarmgraph.fake.json
  trust_diff.new_tool.json
  graph_chat_links.basic.json
  traces/fake_runtime_success.jsonl
  traces/fake_runtime_failure.jsonl
```

Example `run_contract.accepted.json`:

```json
{
  "contract_id": "ctr_test_001",
  "run_id": "run_test_001",
  "session_id": "ses_test_001",
  "objective": "Analyze fixture workflow",
  "runtime": "fake-runtime",
  "mode": "build",
  "allowed_tools": ["read_file", "search_codebase"],
  "write_scope": ["python/tests/fixtures/**"],
  "cost_ceiling_usd": 0,
  "rollback_plan": "none",
  "evidence_expected": ["trace", "receipt"],
  "status": "accepted"
}
```

Example fake trace:

```jsonl
{"event_id":"evt_001","run_id":"run_test_001","type":"RUN_STARTED","ts":"2026-01-01T00:00:00Z"}
{"event_id":"evt_002","run_id":"run_test_001","type":"TOOL_CALL","tool":"read_file","path":"python/tests/fixtures/input.py"}
{"event_id":"evt_003","run_id":"run_test_001","type":"RUN_COMPLETED","status":"success"}
```

## Fake Runtime Tests

Implement one deterministic adapter fixture for all cockpit features:

```python
class FakeCockpitRuntime:
    name = "fake-runtime"

    def run(self, request):
        yield {"type": "RUN_STARTED", "run_id": request.run_id}
        yield {"type": "TOOL_CALL", "tool": "read_file", "path": "python/tests/fixtures/input.py"}
        yield {"type": "RUN_COMPLETED", "status": "success"}
```

Expected assertions:

| Assertion | Expected |
|-----------|----------|
| Determinism | Same input emits same event IDs when seeded |
| No provider calls | OpenAI/Anthropic env vars ignored or blocked |
| No network | Socket/network mocks unused |
| Trace complete | Started and completed events persisted |
| Receipt generated | Receipt hash matches trace fixture |

## Feature Matrix

| Feature | Python unit tests | CLI tests | TS/static tests | E2E tests |
|---------|-------------------|-----------|-----------------|-----------|
| RunContract | Schema, lifecycle, violation checks | `/contract show`, accept/reject | `RunContractCard` props/copy | Proposed → accepted → fulfilled |
| RunReceipt | Hashing, receipt verification | `arc runs receipt`, `arc runs verify` | receipt rendering contract | Run complete emits receipt |
| FailureAutopsy | known/guess classification | `arc runs autopsy` | autopsy panel sections | failed fake run produces autopsy |
| EvidenceRef | URI validation, hash verification | evidence list/show | link rendering | trace event links to file/chat/graph |
| CapabilitySnapshot | capability schema, diff | `arc capabilities snapshot/diff` | capabilities badge | runtime snapshot blocks unsupported action |
| TrustDiff | policy diff, approval gate | `arc trust diff/approve` | trust diff card | untrusted workspace blocked |
| Graph/chat cross-links | stable link IDs | inspect linked event | source patterns for link handlers | graph click highlights chat evidence |

## RunContract Tests

Exact test names:

```text
test_run_contract_schema_accepts_minimal_valid_payload
test_run_contract_defaults_to_proposed_status
test_run_contract_accept_transition_sets_accepted
test_run_contract_fulfilled_when_tools_and_writes_within_scope
test_run_contract_violated_when_tool_not_allowed
test_run_contract_violated_when_write_outside_scope
test_run_contract_violated_when_cost_exceeds_ceiling
test_run_contract_blocks_run_until_acceptance_when_policy_requires_it
test_cli_contract_show_prints_objective_runtime_scope
test_cli_contract_accept_persists_status
test_run_contract_card_static_props_match_protocol
test_e2e_fake_run_contract_lifecycle_success
```

Fixture example:

```json
{
  "allowed_tools": ["read_file"],
  "write_scope": ["src/**/*.py"],
  "observed_tools": ["read_file"],
  "observed_writes": ["src/app.py"],
  "observed_cost_usd": 0
}
```

Expected assertions:

| Test | Assert |
|------|--------|
| valid payload | Pydantic model loads, `status == "proposed"` |
| accept | stored status becomes `accepted` |
| allowed completion | status becomes `fulfilled` |
| unknown tool | status becomes `violated`, violation reason includes tool |
| outside write | status becomes `violated`, path included |
| CLI show | exit `0`, output includes `contract_id`, `runtime`, `write_scope` |
| static card | source exports `RunContractCardProps`, renders objective |

## RunReceipt Tests

Exact test names:

```text
test_run_receipt_schema_accepts_success_payload
test_run_receipt_includes_trace_hash_and_audit_hash
test_run_receipt_hash_is_deterministic_for_same_trace
test_run_receipt_verify_accepts_untampered_receipt
test_run_receipt_verify_rejects_tampered_trace_hash
test_cli_runs_receipt_prints_receipt_id_and_status
test_cli_runs_verify_exits_nonzero_for_tampered_receipt
test_run_receipt_panel_static_renders_hash_status_evidence_count
test_e2e_fake_run_writes_verifiable_receipt
```

Fixture example:

```json
{
  "receipt_id": "rcp_test_001",
  "run_id": "run_test_001",
  "status": "success",
  "trace_sha256": "sha256:fixture_trace_hash",
  "audit_sha256": "sha256:fixture_audit_hash",
  "evidence_refs": ["ev_test_001"],
  "verified": true
}
```

Expected assertions:

| Test | Assert |
|------|--------|
| hash deterministic | two runs over same JSONL produce same hash |
| tampered trace | verification fails, reason includes `trace_sha256` |
| CLI receipt | no raw secrets in output |
| E2E | receipt points to persisted trace path and audit path |

## FailureAutopsy Tests

Exact test names:

```text
test_failure_autopsy_schema_separates_knowns_and_guesses
test_failure_autopsy_requires_failure_run_id
test_failure_autopsy_redacts_secret_values_from_error_text
test_failure_autopsy_extracts_timeout_from_fake_runtime_failure
test_cli_runs_autopsy_prints_knowns_before_guesses
test_cli_runs_autopsy_exits_nonzero_when_run_not_failed
test_failure_autopsy_panel_static_renders_knowns_guesses_next_steps
test_e2e_failed_fake_run_generates_autopsy
```

Fixture example:

```json
{
  "autopsy_id": "aut_test_001",
  "run_id": "run_test_failed_001",
  "knowns": ["runtime exited with code 124", "last event was TOOL_CALL"],
  "guesses": ["tool timeout exceeded"],
  "next_steps": ["rerun with shorter input", "inspect evt_002"]
}
```

Expected assertions:

| Test | Assert |
|------|--------|
| knowns/guesses | deterministic ordering, no guess in knowns |
| redaction | `sk-...`, bearer tokens, passwords replaced with `[REDACTED]` |
| CLI | headings ordered: `Known`, `Guesses`, `Next steps` |

## EvidenceRef Tests

Exact test names:

```text
test_evidence_ref_schema_accepts_trace_file_chat_graph_kinds
test_evidence_ref_rejects_untrusted_absolute_path
test_evidence_ref_hash_matches_fixture_file
test_evidence_ref_hash_mismatch_marks_unverified
test_evidence_ref_links_event_id_to_trace_line
test_cli_evidence_list_prints_kind_uri_verified
test_cli_evidence_show_resolves_fixture_path
test_evidence_link_static_component_uses_stable_evidence_id
test_e2e_trace_event_creates_evidence_ref
```

Fixture example:

```json
{
  "evidence_id": "ev_test_001",
  "run_id": "run_test_001",
  "kind": "trace",
  "uri": "arc://runs/run_test_001/events/evt_002",
  "sha256": "sha256:fixture_event_hash",
  "verified": true
}
```

Expected assertions:

| Test | Assert |
|------|--------|
| URI | `arc://` accepted, unsafe absolute path rejected |
| hash | mismatch does not crash; marks unverified |
| static link | component passes `evidenceId`, not array index |

## CapabilitySnapshot Tests

Exact test names:

```text
test_capability_snapshot_schema_accepts_fake_runtime
test_capability_snapshot_records_tools_modes_limits
test_capability_snapshot_diff_detects_removed_tool
test_capability_snapshot_diff_detects_new_paid_capability
test_capability_snapshot_blocks_run_requiring_missing_tool
test_cli_capabilities_snapshot_outputs_json
test_cli_capabilities_diff_marks_breaking_change
test_capability_badge_static_renders_offline_paid_and_isolation_flags
test_e2e_runtime_capability_snapshot_used_before_run
```

Fixture example:

```json
{
  "runtime": "fake-runtime",
  "version": "0.0.0-test",
  "tools": ["read_file", "search_codebase"],
  "modes": ["plan", "build"],
  "supports_paid_calls": false,
  "supports_isolation": true
}
```

Expected assertions:

| Test | Assert |
|------|--------|
| removed tool | diff severity `breaking` |
| paid capability | CI policy marks unsupported unless gated |
| CLI JSON | parseable JSON, stable keys |

## TrustDiff Tests

Exact test names:

```text
test_trust_diff_schema_accepts_new_tool_and_scope_changes
test_trust_diff_detects_new_write_scope
test_trust_diff_detects_new_paid_provider_permission
test_trust_diff_requires_approval_for_high_risk_change
test_trust_diff_approval_updates_external_trust_store
test_cli_trust_diff_prints_risk_summary
test_cli_trust_approve_persists_decision
test_trust_diff_card_static_renders_before_after_risk
test_e2e_untrusted_workspace_blocks_run_before_contract
```

Fixture example:

```json
{
  "diff_id": "td_test_001",
  "workspace": "/tmp/arc-fixture",
  "before": {"tools": ["read_file"], "write_scope": []},
  "after": {"tools": ["read_file", "write_file"], "write_scope": ["src/**"]},
  "risk": "high",
  "requires_approval": true
}
```

Expected assertions:

| Test | Assert |
|------|--------|
| new write scope | risk at least `medium` |
| paid provider | risk `high`, approval required |
| trust store | writes external trust DB, not workspace file |

## Graph/Chat Cross-Link Tests

Exact test names:

```text
test_cross_link_schema_accepts_graph_chat_evidence_targets
test_cross_link_ids_are_stable_for_same_run_event
test_cross_link_rejects_missing_evidence_ref
test_cross_link_resolves_graph_node_to_chat_message
test_cli_links_show_prints_source_target_evidence
test_graph_chat_static_components_use_link_id_not_index
test_e2e_graph_click_highlights_chat_message_and_evidence
```

Fixture example:

```json
{
  "link_id": "lnk_test_001",
  "run_id": "run_test_001",
  "source": {"kind": "graph_node", "id": "node_planner"},
  "target": {"kind": "chat_message", "id": "msg_001"},
  "evidence_id": "ev_test_001"
}
```

Expected assertions:

| Test | Assert |
|------|--------|
| stable IDs | same source/target/evidence → same `link_id` |
| missing evidence | validation fails before storage |
| static UI | no use of list index as React key for links |

## Redaction and Security Tests

Exact test names:

```text
test_redaction_removes_openai_api_key_from_stdout
test_redaction_removes_anthropic_api_key_from_stderr
test_redaction_removes_bearer_token_from_trace_event
test_redaction_removes_password_assignment_from_autopsy
test_receipt_does_not_store_raw_secret_values
test_evidence_ref_rejects_path_traversal_uri
test_contract_write_scope_rejects_parent_directory_escape
test_ci_provider_env_vars_are_not_forwarded_to_fake_runtime
test_no_paid_provider_ci_policy_fails_when_provider_mode_enabled
```

Fixture example:

```json
{
  "stdout": "OPENAI_API_KEY=sk-test-secret",
  "stderr": "Authorization: Bearer test-token",
  "expected": "[REDACTED]"
}
```

Expected assertions:

| Test | Assert |
|------|--------|
| secret patterns | raw token absent from trace, receipt, autopsy, CLI output |
| env forwarding | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AWS_SECRET_ACCESS_KEY` absent |
| path traversal | `../` evidence URI rejected |
| paid provider | normal CI exits nonzero or skips with explicit reason |

## Audit/Receipt Verification Tests

Exact test names:

```text
test_audit_chain_verifies_fixture_receipt
test_audit_chain_rejects_reordered_events
test_audit_chain_rejects_deleted_event
test_audit_chain_rejects_modified_event_payload
test_run_receipt_links_to_audit_path
test_run_receipt_verification_checks_audit_hmac_chain
test_cli_audit_verify_receipt_prints_verified_true
test_cli_audit_verify_receipt_exits_nonzero_on_tamper
```

Fixture example:

```json
{
  "run_id": "run_test_001",
  "audit_path": "python/tests/fixtures/cockpit/audit/run_test_001.audit.jsonl",
  "receipt_id": "rcp_test_001",
  "chain_head": "sha256:fixture_chain_head"
}
```

Expected assertions:

| Test | Assert |
|------|--------|
| valid chain | verification returns `verified: true` |
| reordered | verification fails with chain-order reason |
| deleted event | verification fails with missing-link reason |
| receipt | receipt references audit path and chain head |

## Theia Static Test Patterns

Static tests should verify source contracts without launching Theia:

```text
test_run_contract_card_exports_props_interface
test_run_receipt_panel_renders_receipt_id_status_hash
test_failure_autopsy_panel_renders_knowns_before_guesses
test_evidence_link_uses_evidence_id_as_key
test_capability_badge_renders_paid_offline_isolation_flags
test_trust_diff_card_renders_before_after_sections
test_graph_chat_link_components_share_link_id_prop
```

Expected assertions:

| Component | Assert |
|-----------|--------|
| RunContractCard | props include `contract`, `onAccept`, `onCancel` |
| RunReceiptPanel | renders `traceSha256`, `auditSha256`, `verified` |
| FailureAutopsyPanel | source order: knowns before guesses |
| EvidenceLink | uses `evidenceId`, supports `onSelectEvidence` |
| CapabilityBadge | renders paid/offline/isolation flags |
| TrustDiffCard | renders before/after/risk |
| GraphChatLink | uses stable `linkId` |

## E2E Happy Path

Exact test name:

```text
test_e2e_cockpit_fake_runtime_contract_receipt_evidence_links
```

Flow:

```text
1. Create trusted temp workspace
2. Load fake runtime capability snapshot
3. Propose RunContract
4. Accept RunContract
5. Execute fake runtime
6. Persist JSONL trace + SQLite run metadata
7. Generate EvidenceRef for trace event
8. Generate RunReceipt
9. Verify audit chain and receipt
10. Resolve graph/chat cross-link
```

Expected assertions:

| Step | Assert |
|------|--------|
| contract | status `fulfilled` |
| run | status `success` |
| trace | JSONL contains `RUN_STARTED`, `RUN_COMPLETED` |
| evidence | verified `true`, stable `evidence_id` |
| receipt | verified `true`, hashes present |
| audit | HMAC chain valid |
| links | graph node resolves to chat msg and evidence |
| providers | no paid-provider env or network call |

## E2E Failure Path

Exact test name:

```text
test_e2e_cockpit_fake_runtime_failure_autopsy_receipt
```

Flow:

```text
1. Use fake runtime configured to timeout
2. Accept contract
3. Execute run
4. Persist failed trace
5. Generate FailureAutopsy
6. Generate failed RunReceipt
7. Verify receipt and audit chain
```

Expected assertions:

| Step | Assert |
|------|--------|
| run | status `failed` |
| autopsy | knowns include timeout, guesses are separate |
| receipt | status `failed`, still verifiable |
| redaction | raw secret fixture values absent |
| contract | fulfilled or violated reason explicit |

## No Paid-Provider CI Policy

Required guard tests:

```text
test_ci_rejects_provider_optimizer_mode_without_explicit_gate
test_ci_skips_real_runtime_smoke_without_arc_real_runtime_smoke
test_fake_runtime_does_not_read_openai_or_anthropic_env
test_capability_snapshot_paid_provider_false_in_ci_fixture
```

Allowed smoke gate only:

```bash
ARC_REAL_RUNTIME_SMOKE=1 cd python && uv run pytest -q tests/integration/real_runtime
```

Normal CI expected behavior:

| Condition | Expected |
|-----------|----------|
| provider env present | ignored by fake runtime |
| provider mode requested | skipped or blocked with explicit message |
| `ARC_REAL_RUNTIME_SMOKE` unset | real-runtime tests skipped |
| paid call attempted | test fails |

## Merge Gate

Before merge, require:

```text
Python: cd python && uv run pytest -q
Protocol: pnpm --filter @arc-studio/protocol build
Extension: pnpm --filter arc-extension build
Security: redaction tests cover stdout/stderr/trace/autopsy/receipt
Audit: receipt verification rejects tamper
Fixtures: deterministic, redacted, committed
CI: no paid-provider calls
```
