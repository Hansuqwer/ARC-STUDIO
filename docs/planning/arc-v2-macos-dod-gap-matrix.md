# ARC v2 — macOS DoD Gap Matrix

Date: 2026-06-13 · Baseline: `6578db8`

Legend: **Evidence** = cited; **Partial** = exists, needs more; **Gap** = needed.

## DoD matrix by surface × gate

| Surface | UX states | Accessibility | Parity | Tests | Performance | Security | Reliability | Docs |
|---|---|---|---|---|---|---|---|---|
| Shell chrome | Partial | Evidence | Partial | Evidence | Partial | Evidence | Partial | Evidence |
| Command palette | Partial | Evidence | Partial | Evidence | Evidence | Evidence | Partial | Evidence |
| Editor | Partial | Partial | Partial | Partial | Gap | Evidence | Partial | Partial |
| Workspace tree | Partial | Partial | Partial | Partial | Partial | Evidence | Partial | Partial |
| Search/index | Partial | Partial | Partial | Evidence | Partial | Partial | Evidence | Partial |
| Event Stream | Partial | Partial | Evidence | Evidence | Evidence | Evidence | Partial | Evidence |
| Terminal | Partial | Partial | Partial | Partial | Partial | Partial | Partial | Partial |
| Status rail | Evidence | Evidence | Evidence | Evidence | Evidence | Evidence | Partial | Evidence |

## Closure order

1. M11 closes UX-state and interaction parity gaps.
2. M12 closes accessibility, IME, and theme gaps.
3. M13 closes performance/reliability/security/docs evidence gaps.

Linux deferred until this matrix is closed or residual gaps are explicitly accepted.
