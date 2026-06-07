# ARC Mobile Runtime — No-Overclaim Policy

ARC Mobile Runtime must describe implemented behavior precisely.

## Required wording for current release

Use:

- simulator preview
- mock-only capability catalog
- no production native access
- no real mobile OS bridge
- static/mock simulation
- advisory compliance artifact, when generated

Avoid unsupported wording:

- production mobile SDK
- enterprise-ready mobile SDK
- real camera access
- real microphone access
- real contacts/calendar/photos/files/location access
- production MCP gateway
- autonomous background agent
- app-store-ready native runtime

## Claim rules

A claim is allowed only when implementation and tests support it.

| Claim | Minimum evidence required |
|---|---|
| Production SDK | Built package, example app, CI, signed plan gate, scoped approvals, traces, compliance artifacts |
| Enterprise-ready | Tenant/org policy, RBAC/ABAC, audit export, retention, device posture/MDM hooks, package provenance |
| Native bridge | Native iOS/Android source, build tests, documented API, no sensitive OS access bypass |
| Real capability | OS permission mapping, user approval UX, trace evidence, compliance artifacts, rollback flag |
| Tamper-evident trace | Previous-hash chain, verification CLI, mutation/reorder/delete tests |
| App-store-ready | Generated and reviewed iOS/Android artifacts plus review notes |

## Safe fallback

When in doubt, say:

> ARC Mobile Runtime currently provides simulator-preview tooling. It does not provide production native mobile access yet.
