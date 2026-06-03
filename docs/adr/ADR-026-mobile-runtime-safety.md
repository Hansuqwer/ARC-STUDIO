# ADR-026: ARC Mobile Runtime Safety Posture

## Status

Accepted for simulator-first foundation.

## Decision

ARC Mobile Runtime is the Edgebody runtime beside SwarmGraph. The MVP is mock-only and simulator-first. Real native bridges, background execution, production MCP gateways, and sensitive data access are out of scope until explicit capability, permission, policy, test, and app-store review gates are implemented.

## Consequences

- `arc mobile` commands must not require a device.
- Runtime fixtures must be deterministic and replayable.
- Sensitive capabilities default to deny or approval-required.
- MCP exposure is denied by default.
- App-store compliance files are generated from manifests in later phases, not hand-written claims.
