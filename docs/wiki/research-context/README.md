# Research Context Index

This wiki folder keeps non-authoritative research context for future agents.

Authoritative planning lives only in:
- `docs/roadmap.md`
- `docs/phases.md`

Use this folder for supporting notes, Context7 summaries, external research, and archived-plan pointers. Do not treat wiki notes as implementation status.

## Context7 Notes

### 2026-05-17 — pnpm workspace archive cleanup

Context7 library: `/websites/pnpm_io`

Relevant docs summary:
- `pnpm-workspace.yaml` uses a `packages` list to include workspace package dirs.
- Wildcards are supported, e.g. `packages/*`.
- Negation patterns are supported, e.g. `!**/test/**`, to exclude matched packages.
- Root package is always part of the workspace.

Applied project decision:
- Legacy `theia-extensions/*` and `packages/arc-browser-app` are no longer active workspace packages.
- Their sources are archived under `docs/archive/` for rollback/history.
- Active workspace packages are canonical app/package paths only.

## Archived Planning Context

Stale/historical roadmap and phase docs are archived under:
- `docs/archive/stale-roadmaps/`

They may contain useful reasoning, but current status must be checked against the locked docs above.
