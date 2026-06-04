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

**Status: queued, NOT YET WRITTEN.** Following the same `edit_file → git diff` workflow, plan:

| # | Will implement | Files |
|---|---|---|
| 010 | UX R-007 ApprovalCard (universal across Capability/Paid/MCP/HITL gates) | `tui/widgets/approval_card.py` (new), `tui/screen.py` |
| 011 | UX R-006 CapabilityCardBanner inline | `tui/widgets/capability_banner.py` (new); subscribe to `CAPABILITY_CARD_DECISION` events |
| 012 | UX R-008 ActivityTray (Ctrl+X) | `tui/widgets/activity_tray.py` (new) |
| 013 | UX R-008 McpDecisionBanner inside ActivityTray | `tui/widgets/mcp_banner.py` (new); subscribe to `MCP_CALL_DECISION` |
| 014 | UX R-012 PlanView split (spec + simulator) | `tui/views/plan_view.py` (new) |
| 015 | Streaming via Textual `RichLog` + `Live` | `tui/screen.py`, `tui/widgets/transcript.py` |
| 016 | Already partially shipped via `patches/post-merge/003`. Promote to a real sandbox.decide() call. | `tui/screen.py` |
| 017 | Event-bus subscriptions for new typed events | `tui/screen.py`, `tui/widgets/*` |

The wiring contract uses already-merged `CAPABILITY_CARD_DECISION` and `MCP_CALL_DECISION` events.

---

## `ux/p2-components-ia/` — ToolCard rebuild, DiffViewer, palette categories, frontmatter, Toaster

**Status: queued.** Plan:

| # | Implements | Files |
|---|---|---|
| 020 | R-005 ToolCard rebuild (expand/copy/rerun keys, risk badge in header) | `tui/widgets/tool_card.py` |
| 021 | R-009 DiffViewer (hunk navigation, side-by-side toggle `s`, word-level toggle `w`) | `tui/widgets/diff_viewer.py` (new), retire `diff_block.py` |
| 022 | R-010 SlashMenu category chips + 2-line items | `tui/widgets/slash_menu.py` |
| 023 | R-011 CommandPalette rebuild (search name+description+aliases, category chips) | `tui/widgets/command_palette.py` |
| 024 | R-014 Toaster | `tui/widgets/toaster.py` (new) |
| 025 | R-015 KeycapHint inline element | `tui/widgets/keycap_hint.py` (new) |
| 026 | R-016 RiskBadge | `tui/widgets/risk_badge.py` (new) |
| 027 | R-017 RunsView polish (filters, sort, `d` diff) | `tui/views/runs_view.py` |
| 028 | R-019 SessionsView fork/rewind keys | `tui/views/sessions_view.py` |
| 029 | Slash-command frontmatter (description/aliases/argument-hint/mode-restriction/risk) | `cli_repl/commands/**` |
| 030 | Retire static `HelpScreen`; render from registry | `tui/widgets/help_screen.py` |

---

## `ux/p3-themes-a11y/` — 5 themes, NO_COLOR glyph fallback, reduced motion, full snapshot matrix

**Status: queued.** Plan:

| # | Implements | Files |
|---|---|---|
| 040 | Catppuccin Mocha theme | `tui/tcss/themes/catppuccin-mocha.tcss`, `tui/theme.py` |
| 041 | Catppuccin Latte theme | `tui/tcss/themes/catppuccin-latte.tcss` |
| 042 | High-Contrast theme | `tui/tcss/themes/high-contrast.tcss` |
| 043 | Monochrome theme | `tui/tcss/themes/monochrome.tcss` |
| 044 | NO_COLOR text fallback for every `●○✓✗⊘` glyph | `tui/widgets/*.py` |
| 045 | `ARC_REDUCED_MOTION=1` disables spinners/transitions | `tui/screen.py`, widgets |
| 046 | `pytest-textual-snapshot` matrix 80×24/120×40/200×60/240×72 + NO_COLOR | `tests/tui/snapshots/`, `pyproject.toml` deps |
| 047 | `/title` `/statusline` configurability | `cli_repl/commands/` |
| 048 | Performance instrumentation (Textual `--log` profile) | `Makefile`, `scripts/perf-tui.sh` |

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
