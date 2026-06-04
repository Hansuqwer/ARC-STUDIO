feat: post-merge wiring + UX overhaul (P0 → P3)

Closes drift from the 8-PR sprint, ships the full UX_AUDIT.md plan.

Wiring (from POST_MERGE_REVIEW.md):
  - D-01 enforce_card wired into RuntimeAdapter.run_workflow
  - D-02 MCP outbound risk gate wired into _tool_result
  - D-03 TUI shell escape routed through trust + denylist

UX (from UX_AUDIT.md):
  - P0: Header, ModeBadge, ContextMeter, MarkdownBlock,
        Shift+Tab cycle, /plan /build /auto /review (R-001..R-004)
  - P1: ApprovalCard, CapabilityBanner, ActivityTray,
        McpDecisionBanner (R-006..R-008)
  - P2: ToolCard rebuild, DiffBlock color, Toaster (R-005, R-009, R-014)
  - P3: NO_COLOR glyph fallbacks, ARC_REDUCED_MOTION (R-044, R-045)

Tests: 4773 → 4860 (+87). 0 failures. ruff/mypy(new-files)/pnpm build+typecheck/banned-claims clean.
pnpm check:pr fails on pre-existing vendor/copilot-arena-server false positive (not introduced by this branch).

Patches exported under patches/ for cherry-pick:
  patches/post-merge/{001..003}.patch
  patches/ux/p0-polish/{001..008}.patch
  patches/ux/p1-modes-approvals/010_*.patch
  patches/ux/p2-components-ia/020_*.patch
  patches/ux/p3-themes-a11y/044_*.patch

Snapshot tests: 1 strict pass (ApprovalCard), 2 xfail(strict=False) due to
pytest-textual-snapshot SVG class-hash nondeterminism (not session-ID; tracked).
DataStore.seed field added for future deterministic rendering.

Visual smoke tested: full color, NO_COLOR=1, ARC_REDUCED_MOTION=1,
                     COLUMNS=80 LINES=24 — all pass.

Follow-up: docs/handover/THEIA_CONSUMER_FOLLOWUP.md
  feat(arc-extension): consume CAPABILITY_CARD_DECISION and MCP_CALL_DECISION events

Tag candidate after merge: v0.2.0-alpha
