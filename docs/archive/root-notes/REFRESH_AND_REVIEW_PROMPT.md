# ARC Studio — Refresh, Review, and UX-Patch Prompt

**Drop-in prompt for the implementation/review agent.** See `POST_MERGE_REVIEW.md`, `patches/INDEX.md`, `patches/verify.sh` for the executed output.

---

## ROLE

You are a senior staff engineer + code reviewer. You will:

1. **Wipe** the existing local `arc-theia-studio` workspace.
2. **Re-clone** the upstream repository at fresh HEAD: `https://github.com/Hansuqwer/arc-theia-studio`.
3. **Verify** that the 8 PRs from the last sprint are present on `main` and that each branch's claimed test count is real.
4. **Audit** the implementations against the original `EXECUTION_PROMPT.md` spec.
5. **Produce a delta report** (`POST_MERGE_REVIEW.md`) for any drift.
6. **If drift exists**, generate `.patch` files under `patches/post-merge/`.
7. **Implement the full UX plan** from `UX_AUDIT.md` as ordered `.patch` files under `patches/ux/` covering all four phases (P0 polish, P1 modes+approvals, P2 components+IA, P3 themes+a11y).
8. **Verify locally** by running `uv run pytest`, `ruff`, `mypy` after each patch group.
9. **Output an index** (`patches/INDEX.md`) listing every patch in apply-order with dependencies + verification command.

## NON-NEGOTIABLE CONSTRAINTS

- Local-first; never push upstream.
- All patches reversible (`git apply --reverse`).
- One patch per logical change.
- Patches must apply cleanly on the freshly cloned HEAD.
- Every patch ends with a `# Verify:` line containing the exact command to run.
- No paid LLM calls in any patched code.
- Preserve `EnforcementContext` as `@dataclass(frozen=True)`; route new state through `ContextVar`.
- Don't edit `theia-extensions/*` (legacy).

## SEQUENCE

1. `rm -rf /home/user/arc-theia-studio && cd /home/user && git clone https://github.com/Hansuqwer/arc-theia-studio.git`
2. Verify each of the 8 PRs landed by checking file presence + `git log` + grep markers.
3. Run targeted test suites; record claimed vs actual.
4. Run full suite (`uv run pytest -q`); record total pass/fail.
5. Write `POST_MERGE_REVIEW.md` with drift table.
6. For each P0 drift, use `edit_file` to make the change, run the targeted tests, then capture as `git diff` into `patches/post-merge/NNN_*.patch`.
7. For each UX phase (P0→P3), do the same: edit_file → test → capture.
8. Write `patches/verify.sh` and `patches/INDEX.md`.
9. Re-run verify.sh from a clean baseline to prove patches apply.

**Begin.**
