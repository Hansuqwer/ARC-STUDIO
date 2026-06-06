# Prompt — Reconcile Roadmap + Phases with What's Done

## Purpose
After a work session, bring `docs/roadmap.md` and `docs/phases.md` into sync with
the actual commit history. Single source of truth — update in place, never create
competing docs.

## Method

1. Run `git log --oneline` to list recent commits not yet reflected.
2. For each untracked item, check whether it already has a roadmap row and/or phase.
3. Add missing R-items to roadmap.md (Baseline Complete rows).
4. Add missing Phase entries to phases.md (append, sequential numbering).
5. Run banned-claims gate: `bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md README.md`
6. Commit + push on green.

## Rules
- Table rows in roadmap.md are exempt from banned-claims (gate skips them).
- Phases are prose — keep them banned-claims clean.
- No "production-ready", "multi-user", "tenant-isolated", "live streaming", "HMAC audit".
- "production-grade" is allowed.
- Each phase: Status line, Context, What was done, Verification, Known Risks.
- Append phases at end of phases.md — never renumber existing phases.
