# Product Lock — ARC Studio

**Status**: PENDING — Phase 1.5 extraction
**Owner**: Phase 1.5
**Tracking**: ADR-011 (Accepted 2026-05-19)

> # MOVED-PENDING
>
> This file is a placeholder so that `scripts/check-banned-claims.sh` has a
> stable scan target. The Product Lock content has not yet been extracted into
> a single canonical document.
>
> Until extraction completes, the authoritative locked decisions live in:
>
> - `docs/adr/ADR-011-full-parity-framing.md` — accepted framing
> - `docs/adr/ADR-013-swarmgraph-architecture.md` — SwarmGraph lock
> - `docs/adr/ADR-014-security-architecture.md` — trust + injection lock
> - `docs/adr/ADR-015-ide-compliance-mode.md` — IDE/audit lock
> - `docs/phases.md` — phase-by-phase deliverables and acceptance
> - `docs/roadmap.md` — sequencing and gates
> - `docs/agents.md` — engineering rules
>
> Do not add new locked decisions here. File them as ADRs and reference them
> from this document during the Phase 1.5 extraction pass.

## Extraction Scope (Phase 1.5)

The extraction pass MUST consolidate the following sections from the ADRs and
phase docs into a single product-lock surface:

1. Three runtime modes (`fake|offline`, `gated_local`, `provider_backed`)
2. CLI shape (canonical surface, `arc-studio` alias policy)
3. Config ownership (env-var table, scope precedence, defaults)
4. Transport parity (Python ↔ TS event envelope, schema_version)
5. Provider client contract (capability shape, cost source tagging)
6. Release vs CI gates (which checks block merge vs which block release)
7. Migration policy (session schema, capability schema, receipt schema)
8. External SwarmGraph CLI policy (`ARC_SWARMGRAPH_CLI` legacy alias)
9. Banned-claim list summary (with link to `scripts/banned-claims.txt`)
10. Single-source-of-truth rule (canonical docs only; pointer-stub format)

## Acceptance for Phase 1.5

- [ ] All ten sections above populated with prose drawn from ADRs 011/013/014/015.
- [ ] No new locked decisions introduced (this is extraction, not design).
- [ ] Every claim in this file traceable to an Accepted ADR via inline link.
- [ ] `scripts/check-banned-claims.sh` continues to pass against this file.
- [ ] Replace the `Status: PENDING` header with `Status: Active`.
- [ ] Remove the `# MOVED-PENDING` block.

<!-- banned-claims-scanner: this file is intentionally light on prose during
     the PENDING phase to avoid claims drift. Do not add product claims here
     until Phase 1.5 extraction. -->
