# ADR-027: Capability Card Enforcement Gate

**Status:** Accepted
**Date:** 2026-06-04
**Authors:** ARC Studio Team

## Context

Capability Cards describe what a runtime entity *can* do. Until now, they served as documentation and policy-lint inputs only. We need a runtime enforcement gate that evaluates a card before dispatching work (MCP tool call, adapter invocation, SwarmGraph node execution) and deterministically decides allow/deny/warn.

The CoSAI alignment principle mandates: decision rules are deterministic and LLM-free.

## Decision

Implement `capabilities/enforcement.py` with:

1. **Mode resolution** (CLI flag → env var → default `warn`)
2. **Deterministic rule chain** evaluated in strict order; first failing rule wins
3. **Fail-closed semantics** — missing card, invalid signature, or parse error → deny (strict) or warn (warn mode)
4. **No mutation of `EnforcementContext`** — use a separate `_cards_mode` ContextVar for mode state

### Rule evaluation order

| # | Rule | Deny reason |
|---|------|-------------|
| 0 | mode=off → allow | — |
| 1 | card missing | CARD_NOT_FOUND |
| 2 | schema_version mismatch | SCHEMA_VERSION_UNSUPPORTED |
| 3 | opaque=True or requires_review=True | CARD_OPAQUE / REQUIRES_REVIEW |
| 4 | signature invalid/missing (strict requires sig) | SIGNATURE_INVALID / SIGNATURE_MISSING |
| 5 | trust_level=privileged without trust_workspace | TRUST_LEVEL_REQUIRED |
| 6 | paid_call_gate without allow_paid | PAID_CALL_NOT_ALLOWED |
| 7 | audit_level insufficient | AUDIT_LEVEL_INSUFFICIENT |
| 8 | hitl_requirement=blocking without HITL gate | HITL_REQUIRED |

### Event emission

A `CAPABILITY_CARD_DECISION` typed event is emitted for every enforcement decision, matching schema version 2 and the existing event protocol.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| LLM-based decision | Violates CoSAI determinism rule |
| Add fields to EnforcementContext | Frozen dataclass; ContextVar is cleaner |
| Separate gate per rule | Over-engineered; linear rule chain is auditable |

## Consequences

- Every adapter/MCP/SwarmGraph dispatch point must call `enforce_card()` before execution
- Unsigned cards pass in `warn` mode but are denied in `strict` mode
- Audit trail includes full decision data via typed event protocol
