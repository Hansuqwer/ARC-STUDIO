# Prompt — Restructure roadmap.md + phases.md for incoming intake

**Goal:** Consolidate every completed item into a single scannable master list at the top
of each canonical doc, and add a clear NEW INTAKE marker at the bottom so large incoming
roadmap/phase documents can be appended without hunting through history.

**Hard constraints (from AGENTS.md):**
- `docs/roadmap.md` and `docs/phases.md` are the ONLY canonical docs. Update IN PLACE.
- Never create a competing roadmap/phase/status markdown (a prompt doc under `docs/prompts/`
  is fine — it is not a status doc).
- Additive protocol: do NOT delete existing detailed entries. Add navigation/consolidation
  sections only.
- Truth constraints: honor the banned-claims list in `scripts/check-banned-claims.sh`
  (no overclaiming about readiness, multi-tenancy, isolation, streaming, or audit signing).
  Run the banned-claims gate before committing.
- Do not fabricate status. Every status in the master list is extracted from the existing
  detailed entry it points to.

**Procedure:**
1. Extract every `## Phase` header + its `**Status:**` line from phases.md (awk).
2. Extract every roadmap R-item + its status cell from roadmap.md (grep).
3. Insert into phases.md (before `## Reprioritization 2026-06-05`): a "Completed Phases —
   Master Index" table (numeric order) + a short "Not-yet-Complete / Blocked / Deferred /
   Superseded" table for the exceptions.
4. Insert into roadmap.md (after `## Status Vocabulary`): a "Completed Roadmap — Master
   Ledger" grouped table.
5. Append a "NEW INTAKE" section to the END of both files with append instructions.
6. Verify: `bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md README.md`.
7. Commit + push (docs-only; no code, so no full pytest needed — banned-claims gate is the
   relevant gate). Poll CI.

**Append rule for incoming docs:** new phase tasks go under the phases.md NEW INTAKE marker
as `## Phase <n> — <title>`; new roadmap entries go under the roadmap.md NEW INTAKE marker
as a table row or `## R<n> — <title>` section. After a new item reaches Baseline Complete,
add its one-line row to the relevant master list above.
