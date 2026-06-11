# HITL Decision API — daemon-side additive proposal (F3 / owner question Q9)

Status: **AUTHORIZED & IMPLEMENTED** (2026-06-11). Owner directive "execute all
phases you're able to" recorded as authorization per checkpoint-#1 precedent.
Delete-only rollback: remove the two routes from `web/routes.py` and this doc.

Implementation notes:
- Discovery: `HitlSqliteStore` already existed with complete HITL machinery
  (single-use tokens, `HitlDecided` bus event, audit-signable `HitlResponse`).
  The endpoint is a thin additive HTTP face over existing persistence.
- Decision vocabulary follows the daemon's enum: `approve | reject | modify | skip`.
  The sketch's invented `always_require` is dropped (producer-truth applies to
  vocabularies too); the shell's `AlwaysRequireApproval` maps to `reject` + notes
  (documented in `rust/arc-dock/src/hitl.rs`).
- Routes: `GET /api/hitl` (pending queue) + `POST /api/hitl/{hitl_id}/decision`.
- Evidence: 10 route tests (230 total web+protocol suite), live e2e verified,
  Rust client `hitl_list()` / `hitl_decide()` in `arc-daemon-client::hitl`.

Finding F3 (Sprint-1, repo-verified): `hitl_required` existed only as an SSE
push notification; there was no decision endpoint. The native HITL modal
(`rust/arc-dock/src/hitl.rs`, view-model complete and tested) emits a
`HitlDecision` and needed somewhere to POST it. Sprint 8 was blocked on this.
**Now unblocked.**

Constraints honored: additive only (new route, new schema, no renames);
deterministic security (the daemon validates and decides; no LLM anywhere);
audit append-on-allow via the daemon's existing audit subsystem; producer of
truth stays the daemon (the shell relays a user verdict, nothing more).

## Proposed route

```
POST /api/hitl/{hitl_id}/decision
```

(Pattern matches existing per-resource routes like
`/api/runs/{run_id}/events`; bearer-token middleware and workspace-trust
enforcement apply exactly as for other mutating POSTs — both already fire
on mutating methods per `web/server.py` middleware.)

## Request body (new Pydantic model `HitlDecisionRequest`)

```json
{
  "decision": "approve" | "reject" | "always_require",
  "operator_id": "user@example.com",
  "client": "arc-shell/2.0.0-alpha",
  "idempotency_key": "01HV…-h1-1"
}
```

- `decision` vocabulary aligns with the existing `HITL_RESPONSE` event's
  `decision` field (fixture-verified: `decision`/`operator_id`/`responded_at`).
- `idempotency_key`: daemon stores per `hitl_id`; replay of the same key
  returns the original result (the shell's double-submit guard is UI-level;
  this is the API-level guarantee).

## Response envelope (standard ArcEnvelope)

- 200 `{ok: true, data: {hitl_id, decision, responded_at}}` — daemon has:
  1. validated the hitl_id exists, is pending, and is not timed out;
  2. emitted `HITL_RESPONSE` onto the run's event stream (existing event,
     existing schema — no protocol change);
  3. appended the audit row (allow AND deny are both audited);
  4. unblocked/cancelled the waiting step accordingly.
- `ok:false` error codes (all existing codes, no new vocabulary needed):
  - `INVALID_INPUT` — unknown decision value / malformed body
  - `PERMISSION_DENIED` — untrusted workspace (existing trust gate)
  - `RUN_FAILED`-family — hitl already resolved or timed out (daemon picks
    the precise existing code during implementation; the shell renders
    whatever arrives — it already maps codes via `state_from_error`)

## Timeout interaction

`HITL_TIMEOUT` (existing event) remains daemon-owned. A decision arriving
after timeout returns the already-resolved error; the shell's modal then
advances on the error ack the same way it advances on success ack
(`decision_acked` is id-keyed, not outcome-keyed — already implemented).

## What the shell already guarantees (tested, `rust/arc-dock/src/hitl.rs`)

- No approval authority shell-side; single egress = this POST.
- Escape ≠ deny: dismiss keeps the prompt queued; nothing auto-submits.
- Initial focus Deny; focus trap; double-submit blocked until ack.
- Prompts ride the AuditSecurity stream class: never dropped (overflow =
  hard error surface), never coalesced.

## Test plan (daemon-side, lands with the endpoint)

1. approve / reject / always_require happy paths -> HITL_RESPONSE emitted,
   audit row present (allow AND deny), step unblocked/cancelled.
2. Unknown hitl_id -> error envelope; nothing emitted.
3. Double POST same idempotency_key -> identical response, single audit row.
4. Decision after HITL_TIMEOUT -> resolved-error; no state change.
5. Untrusted workspace -> PERMISSION_DENIED (existing gate fires).
6. Fixture: add `protocol/fixtures/` instances for the request/response pair
   (additive; generator-script pattern with validate-before-write).

## Owner decision requested

- [ ] Authorize as proposed (daemon implementation may be scheduled)
- [ ] Authorize with changes: ____________________
- [ ] Defer (Sprint 8 remains blocked; native HITL ships read-only queue view)
