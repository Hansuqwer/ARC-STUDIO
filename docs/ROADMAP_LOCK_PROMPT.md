# ARC Studio — Roadmap Lock & Single-Source Consolidation Prompt

Status: LOCKED governance prompt. Execute in full, in order. Do not broaden scope.

Branch: `spec/v0.8-r-ux2`

## Purpose

ARC Studio has accumulated multiple competing roadmaps, phase lists, and planning
documents. This prompt establishes and enforces a single source of truth:

- **ONE roadmap:** `docs/roadmap.md`
- **ONE phase list:** `docs/phases.md`
- **ONE agent charter:** `AGENTS.md` (root)

Both `docs/roadmap.md` and `docs/phases.md` are already CI-protected
(`scripts/release_check.sh:185-186`), confirming they are canonical. Everything
else that duplicates or competes with them is archived, not kept in parallel.

## Invariants (the lock)

1. There is exactly one roadmap (`docs/roadmap.md`) and one phase list
   (`docs/phases.md`). No other file may present itself as a roadmap or phase plan.
2. Both canonical docs carry a `LOCKED` header with the commit they were locked at.
3. **Finish 1 → 100% before broadening.** The current locked phase is completed
   end to end before any new phase, feature, or roadmap item is started. No new
   top-level scope is added while the active phase is incomplete.
4. Any duplicate or competing roadmap/phase/plan/status document is **archived**
   (moved under `docs/archive/`), never left active.
5. All non-related stray documents are moved out of the repo root and out of active
   `docs/` into the archive bucket, leaving only the structured documentation trees
   (`docs/adr/`, `docs/architecture/`, `docs/security/`, `docs/how-to/`,
   `docs/reference/`, `docs/reports/`, `docs/schemas/`, `docs/guides/`,
   `docs/tutorials/`, `docs/explanation/`, `docs/policy/`) plus the two canonical docs.
6. Additive-only protocol/claim discipline still applies. Do not delete code or
   public surfaces as part of this consolidation — only documents.

## Archive bucket decision

The repo's CI hygiene scripts already exclude `docs/archive/` from banned-claim,
PR-hygiene, and artifact checks (`scripts/check-pr.sh:103`,
`scripts/check-artifacts.sh:17`, `scripts/check-banned-claims.sh:98-100`). Therefore
the archive bucket is **`docs/archive/`** (existing, CI-recognized). A new
`docs/artifacts/` would not be excluded and would cause stale-doc CI failures unless
the same three scripts are updated to exclude it as well.

## Execution steps

1. **Keep canonical, add LOCKED headers.** Prepend a `> LOCKED at <commit> — single
   source of truth. Finish 1→100% before broadening.` banner to `docs/roadmap.md`
   and `docs/phases.md`.
2. **Reconcile phase status.** Update `docs/phases.md` so the active phase reflects
   real state on `spec/v0.8-r-ux2` (verified by tests, not claims).
3. **Archive duplicates.** `git mv` every competing roadmap/phase/plan/status doc
   into `docs/archive/<category>/` (see manifest). This includes the root-level
   `roadmap.md`, `docs/LOCKED_*`, `.phase2_complete_manifest.txt`, duplicate research
   review dirs, and stray root planning/handover/prompt notes.
4. **Update `AGENTS.md`.** Rewrite the root charter to: (a) name the single
   roadmap/phase list, (b) state the 1→100% lock discipline, (c) point to the active
   phase, (d) keep the existing sandbox/microVM truth constraints.
5. **Verify nothing breaks.** Run `scripts/check-banned-claims.sh`,
   `scripts/check-artifacts.sh`, `bash scripts/check-pr.sh` (or `pnpm check:pr`),
   `cd python && uv run ruff check src tests`, and confirm no references to moved
   docs remain in code/CI/scripts.
6. **Commit** as a single docs-only change: `docs: lock single roadmap + phase list,
   archive duplicates, refresh AGENTS.md`.

## Acceptance criteria

- `git ls-files 'docs/**/*roadmap*' 'roadmap.md'` returns only `docs/roadmap.md`
  (plus clearly-archived files under `docs/archive/`).
- Exactly one active phase list: `docs/phases.md`.
- `AGENTS.md` names both canonical docs and the lock discipline.
- All hygiene scripts and `ruff` still pass; no broken references to moved files.
- No code or public API/CLI surface removed.

## Out of scope

- No feature work. No code changes. No roadmap content rewrite beyond status
  reconciliation and the LOCKED header.
- After this lands, proceed to the P0 hardening sprint starting with the SQLite
  `database is locked` fix.
