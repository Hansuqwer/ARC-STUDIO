# Patch Index

**Generated:** 2026-06-04 against HEAD `788dbc9` of `Hansuqwer/arc-theia-studio`.
**Baseline test result before patches:** 4782 pass, 2 pre-existing failures, 42 skipped, 3 xfailed (227 s).
**After applying `post-merge/` + `ux/p0-polish/`:** 1107 pass / 1 skipped in the focused suite (`tests/test_tui_core.py tests/tui tests/capabilities tests/mcp tests/adapters tests/security`); no regression.

Apply order is **strict**: `post-merge/` first, then `ux/p0-polish/` … `ux/p3-themes-a11y/`. Each phase depends on its predecessor's wiring.

Use:

```bash
bash patches/verify.sh
```

or apply manually:

```bash
for p in patches/post-merge/*.patch patches/ux/p0-polish/*.patch; do
    git apply --whitespace=nowarn "$p"
done
```

---

## `post-merge/` — close the three critical wiring gaps from POST_MERGE_REVIEW.md

| # | Patch | Severity | Files | Verify |
|---|---|---|---|---|
| 001 | `001_enforce_card_in_adapters.patch` | **P0** | `adapters/base.py`, `adapters/swarmgraph.py`, `adapters/langgraph.py` | `cd python && uv run pytest tests/capabilities tests/adapters -q` |
| 002 | `002_mcp_server_call_risk_gate.patch` | **P0** | `mcp/server.py` | `cd python && uv run pytest tests/mcp -q` |
| 003 | `003_shell_escape_sandbox.patch` | **P0** | `tui/screen.py` | `cd python && uv run pytest tests/test_tui_core.py -q` |

Each patch turns a built-but-decorative subsystem into a live runtime gate. After these three, the 7-PR sprint is functionally complete per `EXECUTION_PROMPT.md`.

---

## `ux/p0-polish/` — modern header, mode badge, context meter, markdown (3-4 days of work, shipped here)

Implements UX_AUDIT.md recommendations **R-001, R-002, R-003, R-004 (assistant subset)** and the `Shift+Tab` mode cycle.

| # | Patch | Implements | Files | Verify |
|---|---|---|---|---|
| 001 | `001_widget_mode_badge.patch` | R-003 ModeBadge | `tui/widgets/mode_badge.py` (new) | `cd python && uv run pytest tests/tui/test_mode_cycle.py -q` |
| 002 | `002_widget_context_meter.patch` | R-002 ContextMeter | `tui/widgets/context_meter.py` (new) | `cd python && uv run python -c 'from agent_runtime_cockpit.tui.widgets.context_meter import ContextMeter; print("ok")'` |
| 003 | `003_widget_header.patch` | R-001 Header (Wordmark + Workspace + TrustBadge + DaemonDot + ModeBadge + ContextMeter) | `tui/widgets/header.py` (new) | `cd python && uv run python -c 'from agent_runtime_cockpit.tui.widgets.header import Header; print("ok")'` |
| 004 | `004_data_context_limit.patch` | R-002 context_limit field on DataStore | `tui/data.py` | `cd python && uv run pytest tests/test_tui_core.py -q` |
| 005 | `005_widget_markdown_block.patch` | R-004 real markdown render | `tui/widgets/markdown_block.py` | (covered by 006) |
| 006 | `006_transcript_assistant_markdown.patch` | R-004 wire assistant role to MarkdownBlock + MessageHeader | `tui/widgets/transcript.py` | `cd python && uv run pytest tests/test_tui_core.py -q` |
| 007 | `007_screen_header_and_mode_cycle.patch` | R-001 swap Banner→Header (keeps `#banner` id for backward compat); R-003 `Shift+Tab` binding + `/plan` `/build` `/auto` `/review` slash commands + `action_cycle_mode` | `tui/screen.py` | `cd python && uv run pytest tests/test_tui_core.py tests/tui -q` |
| 008 | `008_tests_mode_cycle.patch` | UX R-003 contract tests | `tests/tui/__init__.py`, `tests/tui/test_mode_cycle.py` (new) | `cd python && uv run pytest tests/tui/test_mode_cycle.py -q` |

**Apply 001-008 in order.** They are independent of `post-merge/` but co-tested.

After P0:
- New header renders TokyoNight palette by default; respects `NO_COLOR`.
- `Shift+Tab` cycles Plan → Build → Auto → Review.
- `/plan`, `/build`, `/auto`, `/review` jump directly.
- Assistant messages render markdown + syntax-highlighted code blocks (via `rich.markdown.Markdown`).
- Inline context meter shows `ctx N% · used/limit tok`.
- Trust badge in header surfaces the workspace trust state.
- All 8 new tests pass; the original 58 TUI tests still pass (66/66 in this subtree).

---

## `ux/p1-modes-approvals/` — universal ApprovalCard, CapabilityCardBanner, ActivityTray, PlanView, streaming RichLog, sandbox-routed shell

**Status: ✅ SHIPPED** — commit `dd54780`. Patch: `patches/ux/p1-modes-approvals/010_…patch` (676 lines). 24 tests.

| # | Patch | Implements | Files |
|---|---|---|---|
| 010 | `010_approval_card_capability_banner_activity_tray_mcp_decision.patch` | R-006 CapabilityCardBanner, R-007 ApprovalCard (all gate kinds), R-008 ActivityTray + McpDecisionBanner | `widgets/approval_card.py`, `widgets/capability_banner.py`, `widgets/activity_tray.py`, `widgets/mcp_banner.py`, `screen.py` |

Remaining queued (not yet written): 011–017.

---

## `ux/p2-components-ia/` — ToolCard rebuild, DiffViewer, palette categories, frontmatter, Toaster

**Status: ✅ SHIPPED (partial)** — commit `acde33d`. Patch: `patches/ux/p2-components-ia/020_…patch` (480 lines). 18 tests.

| # | Patch | Implements | Files |
|---|---|---|---|
| 020 | `020_tool_card_diff_color_toaster.patch` | R-005 ToolCard rebuild (expand key, risk badge, 5-line preview), R-009 DiffBlock colored (+/-/@@ lines, n/p hunk nav), R-014 Toaster (dock:bottom, auto-dismiss) | `widgets/tool_card.py`, `widgets/diff_block.py`, `widgets/toaster.py` |

Remaining queued (not yet written): 021–030.

---

## `ux/p3-themes-a11y/` — 5 themes, NO_COLOR glyph fallback, reduced motion, full snapshot matrix

**Status: ✅ SHIPPED (partial)** — commit `c0cd62e`. Patch: `patches/ux/p3-themes-a11y/044_…patch` (210 lines). 44 tests.

| # | Patch | Implements | Files |
|---|---|---|---|
| 044 | `044_no_color_glyphs_reduced_motion.patch` | R-044 NO_COLOR glyph fallback map (`glyph()`) + R-045 `ARC_REDUCED_MOTION=1` (`is_reduced_motion()`, `thinking_indicator()`) | `tui/theme_extras.py` (new), `tui/screen.py` |

Remaining queued (not yet written): 040–043, 046–048.

---

## What is shipped right now

✅ **3 post-merge wiring patches** — verified clean-apply + 1107 tests pass.
✅ **8 P0 UX polish patches** — verified clean-apply + 66 TUI tests pass.

**Total LOC delivered:** 535 lines of patch + 423 lines of new code (3 widgets + 1 test module) + helper hooks across 4 production modules.

## What still needs writing (28 patches across P1/P2/P3)

The remaining phases are listed above with file paths and intent. Each patch in P1+ will follow the same workflow: edit with `edit_file`, run `pytest`, capture with `git diff`, verify clean-apply.

For the highest-leverage next move, start with **P1 010 ApprovalCard** — it consumes the already-merged `CAPABILITY_CARD_DECISION` and `MCP_CALL_DECISION` typed events and replaces the HITL-only `tui/widgets/approval_bar.py`. It is the single most visible UX improvement after the Header.

---

## Run everything

```bash
bash patches/verify.sh
```

Expected output: every patch applies, `uv run pytest tests/test_tui_core.py tests/tui tests/capabilities tests/mcp tests/adapters tests/security -q` ends with `1107 passed, 1 skipped`.
