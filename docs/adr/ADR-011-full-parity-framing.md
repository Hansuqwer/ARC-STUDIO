# ADR-011: Full Parity Framing for ARC Studio Scope

Status: Accepted
Date: 2026-05-19
Accepted: 2026-05-19
Deciders: ARC Studio core team
Related: ADR-012 (Rejected — superseded by this ADR)
         ADR-013 (SwarmGraph Architecture Lock — sub-ADR)
         ADR-014 (Security Architecture — sub-ADR)
         ADR-015 (IDE Compliance Mode — sub-ADR)

## Context

ARC Studio scope must be framed as full competitive parity with leading agent CLIs/IDEs while preserving ARC's provenance, gating, and audit differentiators.

## Decision

ARC Studio commits to CLI + IDE parity: a first-class chat/TUI CLI, a Theia IDE, SwarmGraph as owned default runtime, runtime switching, provider gates, audit/provenance, and honest evidence boundaries.

## Acceptance Note

This ADR was accepted on 2026-05-19. Three sub-ADRs (013, 014, 015) refine
specific architectural commitments under this framing:

  ADR-013: SwarmGraph runtime architecture (queen/worker pattern,
           consensus strategies, fan-out gating, failure taxonomy)
  ADR-014: Security architecture (four-tier trust, six-layer defense,
           CaMeL-style separation)
  ADR-015: IDE compliance mode (AssuranceTab two-mode design, EU AI Act
           aligned receipt schema, regulator export bundle)

All three sub-ADRs are read together with this ADR. Phase 1 docs
consolidation encodes the 16-phase plan from this ADR plus the
architectural commitments from the sub-ADRs.
