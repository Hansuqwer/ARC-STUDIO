# ADR-015: IDE Compliance Mode and Audit-Grade Receipt Schema

Status: Accepted
Date: 2026-05-19
Accepted: 2026-05-19
Deciders: ARC Studio core team
Parent ADR: ADR-011 (Full Parity Framing)
Related: ADR-013 (SwarmGraph Architecture Lock)
         ADR-014 (Security Architecture)

## Context

Regulatory logging and transparency expectations make ARC Studio's AssuranceTab a compliance evidence surface as well as a developer debugging surface.

## Decision

ARC Studio's IDE AssuranceTab implements a two-mode design with a Both option, backed by one audit data model. Run receipts are extended to a compliance-grade schema, and a regulator export bundle is standardized.

### AssuranceTab Two-Mode Design

Developer mode includes timeline replay, trace tree, span detail, filtering, live tail, replay stepper, and JSON/JSONL export.

Compliance mode includes run summary, policy attribution, evidence panel, audit chain integrity, HITL decisions, injection events, trust downgrades, and compliance bundle export.

Both mode shows Developer and Compliance views side by side.

### Compliance-Grade Receipt Schema

Receipt version 2 includes run id, timestamps, user identifier, workspace path and commit, workspace trust, runtime, runtime mode, profile, isolation, model calls, memory snapshot, prompt versions, policies applied, authorization decisions, HITL decisions, injection events, trust changes, outcome, audit chain root, optional signature, and retention metadata.

### Regulator Export Bundle

`arc receipt export --format compliance --run <id>` produces a PDF summary, JSON receipt, audit-chain JSONL, evidence directory, and optional signature bundled as `run-<id>-compliance-bundle.zip`.

### Receipt Verification

`arc receipt verify <run-id>` verifies audit chain root, optional signature, prompt SHAs, and memory snapshot SHAs where available.

### Audit Chain Integrity Model

Each event includes `prev_event_sha256`; genesis uses `run_id`. The model is tamper-evident, not tamper-proof. Stronger guarantees require external timestamping or hardware attestation and are out of Phase 4 scope.

### Retention Policy

Default retention is 6 months for run receipts and audit events, 10 years for technical documentation, and configurable per workspace. `arc storage vacuum` respects retention policy once implemented.

## Consequences

AssuranceTab serves developer and compliance audiences from one data model. The schema is a superset and existing receipts remain readable through versioned readers. Compliance mode increases UI and storage surface area.

## Banned Claims Specific to This ADR

- "ARC is EU AI Act compliant" is unsafe; ARC produces evidence that supports compliance.
- "AssuranceTab replaces a compliance officer" is unsafe.
- "Audit chain is tamper-proof" is unsafe; it is tamper-evident.
- "Compliance bundle satisfies any regulator" is unsafe.
- "Receipts are signed by default" is unsafe unless signatures are default-enabled.
- "Retention is automatically enforced" is unsafe until storage vacuum retention tests pass.

## Acceptance Criteria (Phase 5 IDE Parity ship)

- AssuranceTab implements Developer, Compliance, and Both modes.
- Compliance mode renders policy attribution, evidence panel, audit chain, HITL decisions, injection events, trust changes.
- `arc receipt export --format compliance` produces complete bundle.
- `arc receipt verify` validates audit chain root and available signatures/SHAs.
- Storage vacuum respects retention policy.
- Banned-claims script passes.
- At least one end-to-end compliance bundle is generated and verified in CI smoke.
