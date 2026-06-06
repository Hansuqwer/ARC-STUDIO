# Prompt — Audit an External Research Folder Against the Live Repo

> **Purpose:** Reconcile an out-of-tree research/analysis folder (e.g.
> `WorkSpace/ARC/adapters/`) against the canonical `arc-theia-studio` repo, so
> that aspirational/stale claims are separated from verified, actionable facts
> before anything is acted on.
>
> **Reusable:** Point `AUDIT_TARGET` at any sibling research folder. The same
> verify-don't-trust method applies.

---

## Inputs

- `AUDIT_TARGET` — absolute path to the external folder to audit
  (default: `/Users/<user>/WorkSpace/ARC/adapters`).
- `LIVE_REPO` — the canonical repo to verify claims against
  (default: the current `arc-theia-studio` working tree).

## Hard rules

1. **Verify, do not trust.** Every quantitative or structural claim in the
   research docs (line counts, "N copies of X", "adapter is a stub", "feature
   missing") MUST be checked against `LIVE_REPO` with `grep`/`ls`/AST search
   before being repeated. Mark each claim **VERIFIED**, **STALE**, or
   **OVERSTATED/UNDERSTATED** with the command that proved it.
2. **Never edit the external folder.** It is read-only input. All deliverables
   land in `LIVE_REPO/docs/`.
3. **Duplicate checkouts are stale by default.** If `AUDIT_TARGET` contains its
   own copy of the repo, treat its `docs/roadmap.md` / `docs/phases.md` as
   historical, not authoritative. The canonical single-source-of-truth is
   `LIVE_REPO/docs/{roadmap,phases}.md`.
4. **Banned-claims discipline.** The findings doc must pass
   `scripts/check-banned-claims.sh`. No "production-ready", "multi-user",
   "tenant-isolated", etc. Keep gated/default-off/mock labelling intact.
5. **Separate research threads.** A folder may mix unrelated research (e.g.
   adapter-system vs mobile-framework). Classify each doc by which roadmap item
   it actually informs; do not conflate.

## Method

1. **Inventory** the folder: list every file, classify as
   `duplicate-checkout | research-doc | tool-cache | other`, note sizes.
2. **Read** the substantive research docs (skip caches/`.db`).
3. **Reconcile** each load-bearing claim against `LIVE_REPO`:
   - Adapter inventory → `adapters/registry.py` `build_default()` + `ls adapters/`.
   - "Placeholder/stub" → open the named file/line; confirm or refute.
   - "Duplication: N copies of helper" → `grep -rc` the actual symbol names.
   - "Missing module X" → `ls`/`find` for it.
   - API-spec claims (SDK method signatures) → keep as **external-sourced**;
     mark as "unverified against installed SDK" unless the SDK is present.
4. **Produce** `docs/research/<target>-audit.md` with:
   - A verified-claims table (claim → status → evidence command).
   - A "still actionable" list (real findings worth a roadmap item).
   - A "discard/overstated" list (claims that did not survive verification).
   - A note on the duplicate checkout, if any.
5. **Register** one roadmap item + one phase entry in the canonical docs
   pointing at the findings doc. Do **not** create a competing roadmap.

## Acceptance

- `docs/research/<target>-audit.md` exists with every load-bearing claim
  marked VERIFIED / STALE / OVER-or-UNDERSTATED + the proving command.
- A roadmap R-item + phase reference the findings; banned-claims gate passes.
- The external folder is untouched (`git status` shows no changes there).
- No fabricated numbers: if a claim could not be checked (e.g. needs an
  installed SDK), it is labelled "unverified", not asserted.
