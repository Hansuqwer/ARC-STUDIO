# Branch Consolidation — 2026-06-07

Record of the one-time consolidation that unified all parallel work onto a single
trunk (`main`). Written so the fix is auditable and reversible.

## The problem (the "github issues")

Work had fragmented across many branches that were edited concurrently in the **same
clone**, which caused real damage:

- **19 independent mobile PR branches** (`mob/pr1-truth-labeling` … `mob/pr19-approval-engine`),
  each a single commit off the same base (`23a1ef5`), **not stacked** — so no one branch
  held the full mobile SDK.
- **Cross-branch contamination:** rapid `git checkout` switching between `main` and the
  mobile branches wiped/relocated uncommitted work. `mob/pr12` had swept in stray copies
  of the `main`-side CR-028 files (`ConfigTab.tsx`, `useConfigTabState.ts`,
  `config-tab-helpers.ts`, 3 contract tests, `docs/phases.md`, `docs/roadmap.md`).
- **Incomplete commits:** several mobile tests depended on files that lived only in the
  mobile session's *uncommitted* working dir (4 protocol schema JSONs; the Expo
  `package.json` build script) because `runtimes/` is gitignored and they were never
  force-added.
- **Cross-branch API collisions:** `mob/pr4` redefined `mobile trace` as a sub-group
  (`trace verify`) while the base + `mob/pr15`'s test expected `mobile trace <path>` as a
  leaf; and `mob/pr11`'s `mobile-validators.ts` imported types from `./mobile-runtime`
  that `mob/pr17` actually defined in `./mobile-events.ts`.

Root cause: **multiple agents/sessions sharing one working copy and creating per-PR
branches.** The fix below consolidates everything; the go-forward rule is in
`SINGLE-BRANCH-WORKFLOW.md` — one trunk, no per-PR branches.

## What was done

1. **Safety first (reversible):** tagged `backup/main-pre-consolidation-20260607-205818`
   → the pre-consolidation `origin/main` (`4f9f87f`); recorded every branch SHA.
2. **Isolated worktree:** built the consolidation in `git worktree` off `origin/main`, so
   the mobile session's working dir was never touched.
3. **Merged all 19 mobile commits** (`pr1`…`pr19`) via 3-way merge. Additive mobile files
   touched by multiple branches (`mobile/__init__.py`, `cli/mobile.py`, `manifest.py`, …)
   were auto-combined with a scoped `merge=union` driver, then hand-repaired where union
   interleaved import blocks.
4. **Kept `main` canonical** for the CR-028 split files (dropped `pr12`'s strays — verified
   byte-identical) and the docs (`main`'s `phases.md`/`roadmap.md` were the superset).
5. **Completed the incomplete mobile work:** force-added the 4 missing schema files +
   committed the Expo build script (pulled from the mobile working dir). **Excluded** the
   arena/opencode/vendor dirty set per owner instruction.
6. **Resolved the collisions:** `mobile trace <path>` is the leaf (inspect); `verify`
   became the sibling `mobile trace-verify <path>`. Fixed the validators' import to
   `./mobile-events`.
7. **Restored the coverage gate:** added `mobile-validators.test.ts` (24 cases) — pr11 had
   shipped the validators with no tests, dropping `@arc-studio/protocol` coverage 87.6%→68%.

## Verification (all green on the consolidation before push)

- Python: **5776 passed** (49 skipped, 7 xfailed — the 2 Textual snapshot "mismatches" are
  pre-existing xfails).
- `@arc-studio/protocol`: **14 suites / 182 tests**, coverage gate cleared.
- `arc-extension`: **932 passed**; workspace `pnpm typecheck` clean; `ruff` clean.
- CR-028 files byte-identical to `origin/main`.

## Rollback

```bash
git push --force-with-lease origin backup/main-pre-consolidation-20260607-205818:main
```

(Only if the consolidation must be undone; the backup tag is the exact pre-merge `main`.)
