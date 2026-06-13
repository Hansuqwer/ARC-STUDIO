# ARC v2 — macOS DoD Gap Matrix

Date: 2026-06-13 · Baseline: `cd0a9b0`

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

## M11–M13 execution status

Arena prepared the parallel execution pack and report templates, but cannot close
M11–M13 in this sandbox because M4 pixel/VoiceOver/IME/perf evidence and Rust
toolchain checks are required.

| Phase | Prepared artifact | Current status |
|---|---|---|
| M11 | `reports/evidence/m11-ux-interaction-polish-2026-06-13.md` | Pending M4 UX/interaction evidence |
| M12 | `reports/evidence/m12-a11y-ime-theme-polish-2026-06-13.md` | Pending M4 VoiceOver/IME/theme evidence |
| M13 | `reports/evidence/m13-macos-certification-2026-06-13.md` | Pending local CLI certification run |

## Closure order

1. M11 closes UX-state and interaction parity gaps.
2. M12 closes accessibility, IME, and theme gaps.
3. M13 closes performance/reliability/security/docs evidence gaps.

Linux deferred until this matrix is closed or residual gaps are explicitly accepted.
