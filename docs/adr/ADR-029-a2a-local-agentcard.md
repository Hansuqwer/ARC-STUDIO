# ADR-029: A2A Local AgentCard Generator + Loopback Client

**Status:** Accepted
**Date:** 2026-06-04
**Decision Makers:** ARC Studio maintainers

## Context

ARC Studio needs agent-to-agent (A2A) interoperability following the A2A v1.2 spec. However, ARC is a single-user local workstation tool — no inbound HTTP server should be exposed for A2A discovery.

## Decision

1. **Disk-only AgentCard**: Generate and store AgentCards at `.arc/a2a/agent-card.json`. No HTTP server.
2. **Loopback-only outbound client**: The A2A client only connects to `127.0.0.1` URLs (regex: `^http://127\.0\.0\.1:\d+(/|$)`).
3. **Mandatory signature verification**: Unsigned cards are refused for outbound invocations.
4. **Per-card approval**: Cards must be approved (`.arc/a2a/approved.json`) before invocation.
5. **Reuse existing signing**: HMAC-SHA256 signing from `capabilities/signing.py` patterns.
6. **Deterministic output**: Given fixed inputs, `generate_agent_card()` always produces the same JSON.

## Alternatives Considered

| Alternative | Reason Rejected |
|---|---|
| Expose inbound HTTP for A2A discovery | Security risk; ARC is single-user local tool |
| Allow any URL in outbound client | Opens network exfiltration vector |
| Skip signature requirement | Allows spoofed cards to invoke actions |
| Global auto-approve | Violates least-privilege principle |

## Consequences

- Agents on the same machine can interoperate via loopback.
- Remote A2A requires explicit future design (tunneling, gateway).
- All invocations are auditable via the card approval chain.

## Files Affected

- `python/src/agent_runtime_cockpit/a2a/` — new package
- `python/src/agent_runtime_cockpit/cli/a2a.py` — CLI commands
- `python/src/agent_runtime_cockpit/capabilities/models.py` — `EntityType.A2A_AGENT`
