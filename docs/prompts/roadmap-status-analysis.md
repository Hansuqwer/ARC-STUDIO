# Prompt — Roadmap + Phases Status Analysis

## Goal

Produce an honest, evidence-grounded snapshot of `docs/roadmap.md` + `docs/phases.md`:
1. **100% implemented** (Baseline Complete with verifiable evidence)
2. **Partly implemented** (Partial / slices done / follow-ups open)
3. **Deferred / Research Intake** (not started, or explicitly parked)
4. **Hardening candidates** — for anything implemented that could be made more
   robust, do deep research (context7 / grep / web) on the subject before proposing.

## Constraints from the owner

- **Defer Firecracker/Linux microVM** — do NOT propose activating it.
- For the *other* deferred items, assess whether each is worth making active now
  (small + high-value + verifiable offline = yes; large/needs-live-infra = keep deferred).

## Method

1. Count status markers across both docs: `Baseline Complete`, `Partial`,
   `Research Intake`, `Deferred`/`deferred`.
2. Extract every **Partial** item — what shipped, what's the open follow-up.
3. Extract every **Research Intake / Deferred** item — is it scoped? Implementable offline?
4. For each hardening candidate, verify the current implementation state in `src/`
   before claiming a gap (verify-don't-trust).
5. Rank deferred items: **Activate now** vs **Keep deferred** with a one-line reason each.

## Output

A findings doc `docs/research/roadmap-status-analysis.md`:
- Status summary table (counts).
- Partial items + their open follow-ups.
- Deferred items ranked Activate / Keep-deferred (Firecracker = Keep-deferred, owner directive).
- Top hardening candidate with deep-research backing + a proposed bounded slice.

## Honesty

- Evidence over claims. If a roadmap row says "Baseline Complete" but the code
  doesn't back it, flag the discrepancy.
- No fabricated numbers. No "production-grade" claims.
