# Audit Prompt — Arena.ai Patch Folder Review

You are auditing patch files produced by Arena.ai Agent Preview for ARC Studio.

Target repo under audit:

`/Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO`

Primary workspace for comparison:

`/Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio`

Goal: analyze every patch in the Arena repo folder, verify whether it applies cleanly, inspect what it changes, audit correctness/security/test/docs impact against the current repo, and report findings. Do not apply changes to the primary workspace unless explicitly asked later.

## Patch Inventory

At prompt creation time, these patch files existed under `arena/ARC-STUDIO`:

- `patches/ci-debt/v0.3.1-alpha/001_jest_thresholds_raised.patch`
- `patches/ci-debt/v0.3.1-alpha/002_roadmap_r_ts3_complete.patch`
- `patches/persistence-pricing/v0.4.1-alpha/001_budget_persistence.patch`
- `patches/persistence-pricing/v0.4.1-alpha/002_pricing_refresh.patch`
- `patches/post-merge/001_enforce_card_in_adapters.patch`
- `patches/post-merge/002_mcp_server_call_risk_gate.patch`
- `patches/post-merge/003_shell_escape_sandbox.patch`
- `patches/r01/v0.4.0-alpha/001_token_wallet.patch`
- `patches/r01/v0.4.0-alpha/002_slash_wallet_budget.patch`
- `patches/r01/v0.4.0-alpha/003_quota_warning_consumer.patch`
- `patches/r01/v0.4.0-alpha/004_ts_mirror_quota_warning.patch`
- `patches/tokens/p0/001_byte_stable_message_ordering.patch`
- `patches/tokens/p0/002_anthropic_cache_control_breakpoints.patch`
- `patches/tokens/p0/003_token_counter_utility.patch`
- `patches/tokens/p0/004_status_bar_context_meter.patch`
- `patches/tokens/p0/005_otel_cache_fields.patch`
- `patches/ux/p0-polish/001_widget_mode_badge.patch`
- `patches/ux/p0-polish/002_widget_context_meter.patch`
- `patches/ux/p0-polish/003_widget_header.patch`
- `patches/ux/p0-polish/004_data_context_limit.patch`
- `patches/ux/p0-polish/005_widget_markdown_block.patch`
- `patches/ux/p0-polish/006_transcript_assistant_markdown.patch`
- `patches/ux/p0-polish/007_screen_header_and_mode_cycle.patch`
- `patches/ux/p0-polish/008_tests_mode_cycle.patch`
- `patches/ux/p1-modes-approvals/010_approval_card_capability_banner_activity_tray_mcp_decision.patch`
- `patches/ux/p2-components-ia/020_tool_card_diff_color_toaster.patch`
- `patches/ux/p3-themes-a11y/044_no_color_glyphs_reduced_motion.patch`

Do not rely solely on this list. Re-scan the folder first.

## Required First Steps

Run from the primary workspace unless a command explicitly says otherwise:

```bash
git status --porcelain
```

Then enumerate patches:

```bash
find /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO/patches -name '*.patch' -print | sort
```

If using tools, prefer `Glob` for patch enumeration and `Read` for patch contents.

## Audit Method

For each patch:

1. Read patch header and changed files.
2. Check whether the patch applies cleanly to the Arena repo:

```bash
git -C /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO apply --check <patch-file>
```

3. Check whether the patch applies cleanly to the primary workspace if relevant:

```bash
git -C /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio apply --check <patch-file>
```

4. If `apply --check` fails, record the exact failure and do not force apply.
5. If a patch applies, inspect the affected current files before judging correctness.
6. Look for duplicate/stale changes already present in the repo.
7. Look for conflicts with current architecture, tests, locked docs, AGENTS rules, and banned claims.

Never use destructive commands. No `reset --hard`, no `clean -fd`, no force checkout unless owner explicitly approves.

## Review Priorities

Find and classify:

- patches that do not apply
- patches that are obsolete because code already changed
- patches that reintroduce old behavior
- security regressions
- missing confirmation gates for mutating actions
- provider/paid-call behavior without gates
- secrets or secret-like values
- public API removals/renames
- protocol/event breaking changes
- docs status flips without evidence
- tests that are missing, stale, or too weak
- TypeScript build/type errors likely from changed symbols
- Python ruff/mypy/pytest risks
- UI a11y regressions, especially role/button/focus/keyboard handling
- performance regressions: unbounded buffers, sync FS in hot UI paths, unmeasured claims

## Suggested Grouping

Audit patches by directory:

- `patches/post-merge/` — likely security/runtime-critical. Audit first.
- `patches/tokens/p0/` — token accounting/provider/cache behavior.
- `patches/r01/v0.4.0-alpha/` — token wallet and quota warning features.
- `patches/persistence-pricing/v0.4.1-alpha/` — budget persistence/pricing refresh.
- `patches/ci-debt/v0.3.1-alpha/` — CI thresholds and docs claims.
- `patches/ux/p0-polish/` — UI/TUI polish patches.
- `patches/ux/p1-modes-approvals/` — approval/capability/MCP decision UX.
- `patches/ux/p2-components-ia/` — tool card/diff/toaster UX.
- `patches/ux/p3-themes-a11y/` — NO_COLOR/reduced-motion/a11y.

## Verification Commands

Only run full verification after applying patches in a temporary branch/worktree or after owner approval. For audit-only, prefer `apply --check`, static inspection, and targeted reads.

If you do apply a patch temporarily in the Arena repo, run targeted tests for the affected area, then revert only your own temporary application safely via a disposable worktree/branch. Do not mutate the primary workspace.

Relevant commands when applicable:

```bash
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO/python && uv run ruff check src tests
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO/python && uv run pytest <affected-tests> -q
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO && pnpm typecheck
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO && pnpm build
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/arena/ARC-STUDIO && bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md
```

## Output Format

Produce findings first, ordered by severity:

```markdown
## Findings

### High
- `<patch path>` — issue. Evidence. Impact. Minimal recommendation.

### Medium
- `<patch path>` — issue. Evidence. Impact.

### Low
- `<patch path>` — issue. Evidence.

## Patch Matrix

| Patch | Applies to Arena? | Applies to Primary? | Area | Verdict |
|---|---:|---:|---|---|

## Detailed Audit

### `<patch path>`
- Changed files:
- Intent:
- Apply check:
- Risks:
- Tests/docs impact:
- Recommendation:

## Verification

- Commands run + exact result.

## Safe Apply Plan

- Ordered patch groups recommended for review/application.
- Patches to reject or regenerate.
- Patches needing manual rebase.

## Residual Risks

- Anything not verified.
```

If no serious findings exist, state that explicitly, but still include the patch matrix.

## Constraints

- Do not commit.
- Do not push.
- Do not write secrets.
- Do not modify the primary workspace.
- Use `apply_patch` only if you are explicitly asked to edit the audit prompt or create an audit report file.
- Keep repo claims evidence-based.
