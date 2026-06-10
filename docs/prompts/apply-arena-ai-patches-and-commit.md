# Apply Prompt — Arena.ai Patch Series + Commit On Green

You are applying Arena.ai-generated patches to ARC Studio.

Primary repo:

`/Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio`

Arena source repo containing patches:

`/Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO`

Patch root:

`/Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO/patches`

Mission: apply all Arena patch files to the primary repo, resolve only minimal conflicts if safe, run full verification, and commit only if verification is green.

Owner authorization: this prompt explicitly authorizes one or more commits after successful verification. Do not push.

## Hard Rules

- Do not push.
- Do not force-push.
- Do not use destructive git commands (`git reset --hard`, `git clean -fd`, `git checkout -- .`) unless the owner explicitly approves during this run.
- Do not commit if any required verification gate fails.
- Do not commit unrelated dirty work.
- Do not remove or rename public APIs, CLI commands, event names, or protocol surfaces unless a patch already does so and you report it as a blocking issue first.
- Do not write secrets, API keys, tokens, credentials, or private endpoints.
- Do not make paid/provider calls.
- Security allow/deny decisions must remain deterministic.
- Single-user, loopback-only alpha posture remains unchanged.
- Do not create new roadmap/status/handover docs. Only update canonical docs if patches already do or if needed to record applied evidence in `docs/roadmap.md` / `docs/phases.md`.

## Preflight

Run from primary repo:

```bash
git rev-parse --abbrev-ref HEAD
git status --porcelain
```

If the working tree has unrelated dirty files, stop and report them. Do not overwrite them.

Enumerate patch files:

```bash
find /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO/patches -name '*.patch' -print | sort
```

Expected inventory at prompt creation time: 27 patches.

## Patch Order

Apply in this order unless `git apply --check` proves a dependency requires adjustment:

1. `patches/post-merge/001_enforce_card_in_adapters.patch`
2. `patches/post-merge/002_mcp_server_call_risk_gate.patch`
3. `patches/post-merge/003_shell_escape_sandbox.patch`
4. `patches/tokens/p0/001_byte_stable_message_ordering.patch`
5. `patches/tokens/p0/002_anthropic_cache_control_breakpoints.patch`
6. `patches/tokens/p0/003_token_counter_utility.patch`
7. `patches/tokens/p0/004_status_bar_context_meter.patch`
8. `patches/tokens/p0/005_otel_cache_fields.patch`
9. `patches/r01/v0.4.0-alpha/001_token_wallet.patch`
10. `patches/r01/v0.4.0-alpha/002_slash_wallet_budget.patch`
11. `patches/r01/v0.4.0-alpha/003_quota_warning_consumer.patch`
12. `patches/r01/v0.4.0-alpha/004_ts_mirror_quota_warning.patch`
13. `patches/persistence-pricing/v0.4.1-alpha/001_budget_persistence.patch`
14. `patches/persistence-pricing/v0.4.1-alpha/002_pricing_refresh.patch`
15. `patches/ci-debt/v0.3.1-alpha/001_jest_thresholds_raised.patch`
16. `patches/ci-debt/v0.3.1-alpha/002_roadmap_r_ts3_complete.patch`
17. `patches/ux/p0-polish/001_widget_mode_badge.patch`
18. `patches/ux/p0-polish/002_widget_context_meter.patch`
19. `patches/ux/p0-polish/003_widget_header.patch`
20. `patches/ux/p0-polish/004_data_context_limit.patch`
21. `patches/ux/p0-polish/005_widget_markdown_block.patch`
22. `patches/ux/p0-polish/006_transcript_assistant_markdown.patch`
23. `patches/ux/p0-polish/007_screen_header_and_mode_cycle.patch`
24. `patches/ux/p0-polish/008_tests_mode_cycle.patch`
25. `patches/ux/p1-modes-approvals/010_approval_card_capability_banner_activity_tray_mcp_decision.patch`
26. `patches/ux/p2-components-ia/020_tool_card_diff_color_toaster.patch`
27. `patches/ux/p3-themes-a11y/044_no_color_glyphs_reduced_motion.patch`

## Apply Workflow

For each patch:

1. Run `git apply --check <patch>` from the primary repo.
2. If clean, apply with `git apply <patch>`.
3. If it fails:
   - inspect failing hunks and current target files
   - if the change is already present, mark patch as `already applied` and continue
   - if conflict is trivial and safe, manually apply the minimal equivalent change with `apply_patch`
   - if conflict is non-trivial, stop and report exact blocker
4. After each patch/group, run targeted checks when obvious.
5. Do not stage until all patches are applied and inspected.

Record every patch status in a scratch table:

| Patch | Status | Notes |
|---|---|---|

## Required Review Before Commit

After applying all patches:

```bash
git status --porcelain
```

Inspect changed files for:

- secrets or credentials
- public API removals/renames
- unsafe security allow/deny logic
- missing `--yes` gates on mutating CLI actions
- raw JSON-mode output bypassing `_out(ok/err)`
- docs status flips without evidence
- banned claims
- generated artifacts accidentally included

## Verification Gates

Run all gates before commit:

```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
cd python && uv run mypy src/agent_runtime_cockpit/security/ src/agent_runtime_cockpit/protocol/ src/agent_runtime_cockpit/workspace.py src/agent_runtime_cockpit/gating.py src/agent_runtime_cockpit/ag_ui/
pnpm typecheck
pnpm build
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md
```

If any gate fails:

1. Fix only issues introduced by the patch series.
2. Use minimal edits.
3. Rerun the failed gate.
4. If still failing after reasonable fixes, stop and report the failing command, summary, and changed files. Do not commit.

## Commit Protocol

Commit only after all required gates pass.

Before committing:

```bash
git status --porcelain
```

Stage only intended files:

```bash
git add <intended files only>
```

Commit message:

```text
feat(arena): apply audited Arena.ai patch series
```

If the patch series is too large or logically separable, use multiple commits in this order:

```text
fix(security): apply Arena post-merge hardening patches
feat(tokens): apply Arena token accounting patches
feat(ux): apply Arena UX polish patches
docs(roadmap): apply Arena roadmap evidence updates
```

After commit:

```bash
```

Report:

- commit SHA(s)
- patch status table
- verification command results
- files changed summary
- residual risks
- no push performed

## Stop Conditions

Stop and ask owner before:

- applying a patch that deletes large files or rewrites history
- accepting public API or protocol breaking changes
- adding new dependencies
- changing security posture
- touching unrelated dirty files
- committing with failing tests
- pushing

## Final Response Format

```markdown
## Result

- Applied patches: N/N
- Commit(s): `<sha>`
- Push: not performed

## Verification

- `cd python && uv run ruff check src tests`: pass/fail
- `cd python && uv run pytest tests/ -q`: pass/fail
- `cd python && uv run mypy ...`: pass/fail
- `pnpm typecheck`: pass/fail
- `pnpm build`: pass/fail
- `bash scripts/check-banned-claims.sh ...`: pass/fail

## Patch Status

| Patch | Status | Notes |
|---|---|---|

## Files Changed

- summary from `git diff --stat` or commit stat

## Residual Risks

- any skipped checks, warnings, or manual conflict resolutions
```
