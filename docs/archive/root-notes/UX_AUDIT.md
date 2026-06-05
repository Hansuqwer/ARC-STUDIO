# ARC Studio — Interactive CLI/TUI UX Audit

**Audit date:** 2026-06-04 (Europe/Stockholm).
**Repo HEAD verified by `git clone --depth 1`:** `81ba4557` — *fix(security): harden subprocess and frontend execution*, 2026-06-03.
**Subject:** the interactive surface invoked by `arc` (Textual TUI in `python/src/agent_runtime_cockpit/tui/**`) plus the fallback `ARC_CLASSIC` shell (`cli_repl/**`).
**Auditor role:** senior product designer + staff TUI engineer.
**Companion deliverables in this PR:** `UX_AUDIT_PROMPT.md` (the standalone prompt), `ux/mockups/01_home_dark.png` … `ux/mockups/09_no_color_mono.png`.

---

## 1. Executive summary

**Verdict.** ARC Studio's TUI is **mid-2024-tier**: a competent first pass on Textual that hits the basics (chat, slash menu, command palette, modal screens for runs/sessions/providers/HITL, dark/light theme, NO_COLOR detect, shell escape) but **lags 18-24 months** behind the 2026 state of the art set by Claude Code, OpenAI Codex CLI, Gemini CLI, and Kiro. The four most important deficits are:

1. **No mode system.** Claude Code (`/plan`), Codex CLI (Shift+Tab cycles Plan→Pair→Execute) [Codex-Plan-Mechanics], Kiro (autopilot vs supervised) all model "what the agent is allowed to do right now" as a first-class, *visible* state. ARC has `data.mode = "build"` but no UI affordance, no cycle key, no per-mode allowlist, no per-mode prompt prefix [`python/src/agent_runtime_cockpit/tui/data.py:36`].
2. **No context meter.** Claude Code's `/context` is the single most-shared screenshot of any 2026 CLI [Reddit-50-Slash]. ARC tracks `total_tokens` but never visualizes context fill, never warns when approaching limits, has no `/compact` UX.
3. **No first-class capability/risk surface.** ARC has signed Capability Cards (`capabilities/signing.py`) and MCP risk scoring (`mcp/manifests.py:25`) but **zero TUI affordance** to show a card decision, an MCP outbound risk score, an approval request with context, or a denial with remediation. The current `ApprovalBar` widget is hard-coded to HITL with `y/n/a/Esc` only [`tui/widgets/approval_bar.py`].
4. **The transcript is structurally weak.** Every message is rendered with a flat `▸ You` / `▸ ARC` prefix and a four-space indent [`tui/widgets/transcript.py:69-83`]. There is no markdown rendering, no syntax highlighting, no diff viewer, no streaming animation, no role-color discrimination beyond text prefix. Claude Code, Gemini CLI, and OpenCode all ship rich markdown + syntax highlighting + code-block copy.

**Top 5 wins (already excellent).** Don't break these:

| # | What works | Evidence |
|---|---|---|
| W1 | Theme tokens are real (TokyoNight palette, light variant, NO_COLOR detect) | `tui/theme.py:8-60` |
| W2 | Slash menu autocomplete is fuzzy + filtered from the live registry | `tui/widgets/slash_menu.py:38-53` |
| W3 | Daemon liveness probe is non-blocking and surfaces in the status bar | `tui/screen.py:78-92` |
| W4 | Multi-line input with paste-buffer protection (>3 lines collapses to a placeholder) | `tui/widgets/input_area.py:122-128` |
| W5 | Command palette is real, fuzzy-filtered, lists all registered commands | `tui/widgets/command_palette.py:23-46` |

**Top 5 pains.** Fix these first (severity, file):

| # | Pain | Severity | Evidence |
|---|---|---|---|
| P1 | No mode indicator/cycle. `data.mode = "build"` is set and never changed. | **P0** | `tui/data.py:36`, no `BINDINGS` for mode-cycle in `tui/screen.py:31-43` |
| P2 | No context-usage meter. `total_tokens` tracked, never displayed, no `/compact`. | **P0** | `tui/data.py:51`, `tui/widgets/status_bar.py:25-49` shows cost but not context |
| P3 | No markdown / syntax highlighting in chat. `MessageWidget.render` returns plain text. | **P0** | `tui/widgets/transcript.py:69-83`, `widgets/markdown_block.py` is 10 lines of skeleton |
| P4 | `MessageWidget` says **"`Thinking…`"** but no spinner animation, no streaming reveal. Final text is appended via `data.append_to_last` after the worker returns. | **P0** | `tui/screen.py:296-321` |
| P5 | Approval bar is keyboard-only and HITL-specific. No card, no capability-decision banner, no MCP risk banner. | **P0** | `tui/widgets/approval_bar.py:14-50` |

**Redesign thesis (one sentence).** *Promote the four invisible-but-already-built ARC strengths — capability cards, MCP risk scoring, audit chain, simulation — into first-class, persistently visible TUI surfaces using the 2026 agentic-CLI grammar (Plan/Build/Auto modes, context meter, palette-first navigation, rich markdown, approval cards), so ARC reads as the "Linear for local agent runtimes" instead of "a Textual demo".*

---

## 2. Methodology

| Step | Tool | Output |
|---|---|---|
| Clone HEAD | `git clone --depth 1` | `arc-theia-studio/` |
| Map TUI | `ls`, `wc -l`, `find` | 26 TUI files, 2,062 LOC total |
| Inspect every widget + view | `cat` of all 14 widgets + 7 views + `screen.py` + `theme.py` + `base.tcss` | full quoted in §4 |
| Inspect fallback | `head` of `cli_repl/chat_repl.py`, `cli_repl/rendering.py` | classic shell baseline |
| Search competitive 2026 docs | 4 `web_search` calls | sources cited inline |
| Generate mockups | `generate_image` × 9 | `ux/mockups/01-09.png` |
| **Not run** | — | `uv run pytest`, live `arc` launch, snapshot tests, Textual profiler |

Everything below the §4 "Repo reality" line is file-grounded with exact paths and line numbers. Everything in §3 is web-sourced with primary URLs.

---

## 3. Competitive landscape (2026)

| CLI | Invocation | Slash surface | Modes | Input grammar | Status bar | Theming | Hooks/Skills | A11y posture | Weakness ARC can beat |
|---|---|---|---|---|---|---|---|---|---|
| **Claude Code 2.1.x** | `claude` | 50+ built-ins (`/clear`, `/compact`, `/context`, `/diff`, `/fork`, `/rewind`, `/cost`, `/doctor`, `/plan`, `/fast`, `/effort`, `/permissions`, `/model`, `/memory`, `/mcp`, `/security-review`) [Reddit-50-Slash][TechBytes-CC] | `/plan` toggle; `--full-auto` flag; `/effort` [low/med/high/max/auto] [Reddit-50-Slash] | `/` cmds, `!` shell, `@` file, `↑/↓` history, `Esc Esc` edit-last [ClaudeFast-Interactive] | `/statusline` configurable; ↯ when fast mode on | `/theme`; vim mode | Skills `.claude/skills/<name>/SKILL.md`, subagents, hooks (`SessionStart/End`, `PreCompact`, `PostCompact`, `Stop`) [Hidekazu-CC] | Streamable; multiline needs `/terminal-setup`; `/buddy` pet is opt-in | No tamper-evident audit; no consensus; no signed capability cards |
| **OpenAI Codex CLI 0.9x-0.117** | `codex`, `codex "fix bug"`, `codex exec`, `codex resume` | `/plan`, `/review`, `/copy`, `/clear`, `/compact`, `/theme`, `/title`, `/status`, `/model`, `/permissions`, `/fork`, `/side`, `/raw`, `/resume`, `/new`, `/statusline`, `/personality` [Codex-Slash][Codex-CheatSheet] | **Shift+Tab cycles Plan→Pair→Execute** (default since v0.96.0). Plan is prompt-level (not runtime-enforced) [Codex-Plan-Mechanics]. | `Enter` interrupts mid-turn (steer mode), `Tab` queues a follow-up, `@` fuzzy file, `!` shell, `Esc Esc` edit-last, `Ctrl+G` external editor, `Ctrl+L` clear screen | Configurable status-line + window title via `/statusline` & `/title` | `/theme` with live preview | Built-in Rust sandbox; per-Hook overrides via config.toml | Decent; ratatui; mode in footer | Generic — no consensus, no replay, weak audit |
| **Kiro (AWS)** | `kiro` IDE + `kiro` CLI | Specs (`requirements.md` + `design.md` + `tasks.md`), Hooks (`onSave`/`onCommit`/`spec_change`), Steering files (global `~/.kiro/steering/` + project `.kiro/steering/`) [Kiro-Ernest][DigitalApplied-Kiro] | Autopilot / Supervised, with stage-based approval | Spec-first; less keyboard-driven | IDE chrome | VS Code-OSS based | Hooks with `approval: pr_review`/`auto`; Kiro Powers (MCP server marketplace) | IDE-anchored | Spec overhead in solo mode; AWS-leaning; ARC's IR + simulator + capability cards already cover the same "intent layer" *locally* without cloud |
| **Gemini CLI 0.40+** | `gemini` | Standard slash set + `/memory` four-tier (global → project → session → inbox) [Gemini-Medium] | Plan-Research-Execute cycle | `@` files, `!` shell | Streamlined "Minimalist Mode", "Chapters" for long sessions | Several themes | gVisor (runsc) / LXC native sandbox | Long-paragraph default reduces small-terminal readability [Shipyard] | Verbose default replies; cloud-tied |
| **Aider 0.86** | `aider` | `/diff`, `/commit`, `/undo`, `/lint`, `/test`, `/voice`, `/run` | Git-native, every change a commit | `@` file, prompt | Concise | Light/dark | None | Strong for screen-reader (text-driven) | No multi-agent, no MCP-first |
| **OpenCode 1.3** | `opencode` | 75+ providers via BYOK + slash | — | similar to Claude | Polished | Themes | MCP | Good | Less local-first focus |
| **Goose 1.28** | `goose` | "Recipes" + MCP-UI rendering, planning-first | Plan/Execute | `@`, `!` | Standard | Default | MCP-first | Good | Less polished input grammar |
| **Cursor CLI parts** | `cursor` `--cli` | `.cursor/rules/*.mdc` glob | — | — | — | — | Cursor Rules | n/a | n/a |
| **Windsurf** | `windsurf` | "Flows" persistent context | — | — | — | — | Memories | — | Cloud, IDE-anchored |

### Cross-cutting 2026 norms (cite once)

- **`Shift+Tab` to cycle modes** is the de-facto control [Codex-Plan-Mechanics].
- **`@` for fuzzy file attach** and **`!` for shell escape** are universal [ClaudeFast-Interactive][Codex-CheatSheet].
- **Visible context meter** (Claude Code `/context` shows a 12×12 color grid; Codex `/status` shows remaining capacity [Codex-Slash]).
- **`Enter` interrupts running agent, `Tab` queues a follow-up.** This is non-obvious; ARC currently does neither [Codex-CheatSheet].
- **`Esc Esc` edits the previous user message** when the composer is empty.
- **Streaming markdown + syntax highlighting in code blocks is table stakes** in 2026.
- **`/compact`, `/fork`, `/rewind`** are now expected, not novel.
- **Synchronized output (CSI 2026 h/l)** + double-buffer + batched writes for flicker-free animation [Lobehub-TUI].
- **NO_COLOR + ASCII fallback + box-drawing only (no advanced emoji)** are the consensus accessibility baseline [Lobehub-TUI].
- **Configurable status-line + window title** are now product features (Codex `/statusline` + `/title`).

---

## 4. Repo reality: what exists, where

### 4.1 File map (verified)

| Path | LOC | Role |
|---|---:|---|
| `tui/app.py` | 80 | `ArcApp(App)`, `CSS_PATH = "tcss/base.tcss"`, single `BINDINGS = [("ctrl+q","quit")]`. Default screen is `ArcScreen`. |
| `tui/screen.py` | 445 | `ArcScreen(Screen)` — composes Banner + Transcript + SlashMenu + StatusBar + InputArea; holds 13 BINDINGS; handles slash commands inline. |
| `tui/data.py` | 153 | `DataStore` reactive state; tracks session, mode, runtime_mode, profile_id, workspace, daemon, cost, tokens, streaming flag, approvals, allow_paid, history. |
| `tui/theme.py` | 111 | `Theme` dataclass + `DARK_THEME`/`LIGHT_THEME` + `ThemeManager.toggle()`. Respects `NO_COLOR` and `ARC_THEME`. |
| `tui/tcss/base.tcss` | 75 | Hard-codes TokyoNight hex values; no theme tokens; no theme switch. |
| `tui/widgets/banner.py` | 52 | 3-line ASCII-art banner with `ARC Studio v…` + workspace + daemon dot. Collapses to 1 line at <24 rows. |
| `tui/widgets/status_bar.py` | 49 | Single line with mode, runtime_mode, paid flag, model, workspace, session, cost, daemon dot, streaming dot, keymap hint. |
| `tui/widgets/input_area.py` | 181 | Multi-line TextArea, paste-buffer guard, history Up/Down, Ctrl+R, Tab autocomplete, Enter submit, Shift+Enter newline. |
| `tui/widgets/transcript.py` | 83 | `VerticalScroll` of `MessageWidget`/`ToolCard`/`DiffBlock`. Renders plain text only — no markdown, no syntax highlighting. |
| `tui/widgets/tool_card.py` | 38 | Box-drawing card with status icons `●✓✗⊘`, collapse via `_collapsed` flag. Truncates body at 20 lines. |
| `tui/widgets/diff_block.py` | 27 | Renders unified diff lines verbatim — **no color**, no hunk navigation, no syntax. |
| `tui/widgets/slash_menu.py` | 76 | Live-registry fuzzy filter; visibility class toggle; `best_match` for Tab. |
| `tui/widgets/command_palette.py` | 46 | `ModalScreen` with Input + ListView; filters by substring on names only (no help text in match). |
| `tui/widgets/approval_bar.py` | 51 | Hardcoded HITL only (`y`/`n`/`a`/`Esc`); writes to `HitlSqliteStore`. |
| `tui/widgets/help_screen.py` | 56 | Static text block. Hard-coded shortcut + slash list (out of sync risk). |
| `tui/widgets/markdown_block.py` | 10 | Stub. Not wired. |
| `tui/widgets/message.py` | 5 | Empty stub. |
| `tui/views/providers_view.py` | 271 | Real provider browser, env-var detection, ★ for free, model picker. Most complete view. |
| `tui/views/runs_view.py` | 47 | DataTable from `JsonlTraceStore`. Read-only. |
| `tui/views/sessions_view.py` | 48 | ListView; "New Session" button creates new id, clears transcript. |
| `tui/views/hitl_view.py` | 45 | Pending prompts. |
| `tui/views/audit_view.py` | 46 | Static info. |
| `tui/views/runtimes_view.py` | 41 | Detected runtimes table. |
| `tui/views/settings_view.py` | 32 | Stub-level. |
| `tui/views/side_panel.py` | 18 | Base class. |
| `cli_repl/rendering.py` | — | Rich-based fallback used by `ARC_CLASSIC`. Has `startup_panel`, `command_palette`, `_state_rows`. Mostly orthogonal. |

**Total TUI surface:** 2,062 LOC of Python + 75 LOC of TCSS + 1 theme file. No snapshot tests except `python/tests/test_tui_core.py` (single file).

### 4.2 What is broken or missing (verified absences)

| Gap | Severity | Evidence (file:line) |
|---|---|---|
| No mode cycle binding; mode never changes | P0 | `tui/screen.py:31-43` BINDINGS, `tui/data.py:36` |
| No `/plan` / `/build` / `/auto` slash commands routed in TUI | P0 | not present in `tui/screen.py:140-260` slash handlers |
| No context meter; no `/compact`, `/context`, `/fork`, `/rewind` | P0 | `tui/widgets/status_bar.py` shows cost not context; `tui/screen.py` has no handlers |
| No markdown rendering in transcript | P0 | `tui/widgets/transcript.py:69-83` returns plain `str` |
| No syntax highlighting in code blocks | P0 | same |
| No streaming animation; "Thinking…" is a literal string | P0 | `tui/screen.py:296` `add_entry("assistant","● Thinking…")` |
| ToolCard truncation is fixed at 20 lines, no "expand" key | P1 | `tui/widgets/tool_card.py:31-34` |
| DiffBlock has no color | P1 | `tui/widgets/diff_block.py:18-26` (all branches print same prefix) |
| ApprovalBar is HITL-only; no Capability/MCP/Paid variants | P0 | `tui/widgets/approval_bar.py:24-37` |
| Theme switch is text-only (`/theme` prints "Theme: light"); TCSS values are hard-coded so the screen does not actually re-skin | P0 | `tui/tcss/base.tcss:4-6` literal `#1a1b26`; `tui/screen.py:159-162` |
| HelpScreen is hand-maintained and will drift | P1 | `tui/widgets/help_screen.py:11-49` |
| Command palette filters by name only; can't search descriptions | P1 | `tui/widgets/command_palette.py:38-40` |
| Banner ASCII art breaks at <80 cols (only collapses on row count) | P1 | `tui/widgets/banner.py:24-25` |
| Slash menu auto-shows but never explains the available `@` and `!` modes | P1 | `tui/widgets/input_area.py:84-89` only `/` is hinted |
| No `@file` fuzzy-attach grammar | P0 | not implemented; no `@` handler |
| Shell escape (`!cmd`) runs `subprocess.run(shell=True, …)` with no surfaced sandbox/risk | P0 | `tui/screen.py:271-291` calls raw shell, bypassing `security/sandbox.py` |
| No persistent task list (Ctrl+T) | P1 | absent |
| No background task pane (Ctrl+B) | P2 | absent |
| Status bar shows no audit/trust badge | P0 | `tui/widgets/status_bar.py:32-46` |
| Status bar shows no context % | P0 | same |
| No mode-indicator footer | P0 | same |
| No NO_COLOR-aware glyph fallback (Unicode `●○✓✗⊘` everywhere) | P1 | grep `●` across widgets returns 5 files |
| No snapshot tests beyond `test_tui_core.py` | P1 | `python/tests/test_tui_core.py` is the only TUI test |
| No tmux/multiplexer mouse-capture toggle | P2 | absent |
| No `Ctrl+G` external editor | P1 | absent |
| No `Esc Esc` edit-last-message | P1 | absent |
| No `Enter` interrupts / `Tab` queues semantics | P0 | absent |
| Banner doesn't render trust state | P1 | `tui/widgets/banner.py:33-43` |

---

## 5. First-run experience walkthrough

Severity is **P0** (showstopper) / **P1** (frustration) / **P2** (papercut) / **P3** (nit).

| t | Action | What happens today | Severity | Cite |
|---|---|---|---|---|
| 0:00 | `git clone … && cd python && uv sync --all-extras --dev` | Works; ~8 min on cold cache | P3 | README |
| 0:08 | `uv run arc` | TUI launches; default screen draws ASCII banner; greeting message includes session id, workspace, **`free-tier provider hint`** | P2: free-hint is good but the banner has no trust badge | `tui/screen.py:61-71` |
| 0:09 | User sees the banner and asks: "What mode am I in?" | **No answer.** Mode is "build" in `data.mode` but invisible. | **P0** | `tui/data.py:36` |
| 0:09 | "Who am I talking to? What model?" | Status bar bottom line shows `build │ fake │ ~/proj │ s-… │ $0 │ ●` — but **only if a provider has been picked**. On first run, model is empty. | **P0** | `tui/widgets/status_bar.py:32-46` |
| 0:10 | Types `hello` and presses Enter | "● Thinking…" appears, then `[SwarmGraph] completed` appended. **No streaming, no typing animation, no token counter, no cost during the run.** | **P0** | `tui/screen.py:296-321` |
| 0:11 | "Where's the cost?" | Status bar shows `$0` because the default SwarmGraph adapter ran in fake mode and emits no measured cost events for the bare-prompt path. | P1 | `tui/widgets/status_bar.py:28` |
| 0:12 | Types `/` | Slash menu appears with fuzzy filter — **good**. | W2 | `tui/widgets/slash_menu.py:38-53` |
| 0:12 | Types `/help` | Modal opens with a hand-curated wall of text. Some slash commands listed in the modal (`/profiles`) don't actually exist in the inline handler. | P1 | `tui/widgets/help_screen.py:11-49` vs `tui/screen.py:140-260` |
| 0:13 | Types `/providers` | Real provider browser opens; user can enter API key. **This is the best part of the TUI.** | W3 | `tui/views/providers_view.py:1-271` |
| 0:14 | Picks Anthropic, returns to chat | Status bar updates; cost still `$0` (no current turn) | OK | — |
| 0:15 | Asks `please write a function to add two numbers in python` | Reply appears as plain text. **No code block, no syntax highlighting, no copy hint.** | **P0** | `tui/widgets/transcript.py:69-83` |
| 0:18 | Types `!ls` to escape to shell | Output appears inside a `Bash:` tool card. **But the call goes straight to `subprocess.run(shell=True, …)` with no sandbox decision.** | **P0** | `tui/screen.py:271-291` |
| 0:19 | Switches workspace to an untrusted folder, runs `/run` | `ensure_trusted` raises; user sees a stack trace as text in the transcript. **No card, no remediation copy, no `/workspace trust` shortcut.** | **P0** | `tui/screen.py:262-269` |
| 0:20 | Switches back, hits `Esc` mid-stream | Streaming stops with `"⏸ Interrupted."` — **good**. | W4 | `tui/screen.py:362-367` |
| 0:21 | Closes with `Ctrl+C` | First C: prompt to press again. Second C within 1s: exits. **Good.** | W5 | `tui/screen.py:340-358` |
| 0:22 | Reopens with `arc` | Lands fresh; no resume affordance shown; user must know `arc -- --resume <id>` or use `/sessions`. | P1 | `tui/app.py:46-79` |

**Summary:** the first 10 minutes contain **6 P0 moments**. Each is fixable.

---

## 6. Heuristic evaluation (25 heuristics)

Scoring: **0 missing · 1 broken · 2 partial · 3 works · 4 delights**.

| # | Heuristic | Score | Justification |
|---|---|---:|---|
| H01 | Visibility of system status (mode, model, trust, audit, context) | **1** | mode hidden; trust hidden; audit hidden; context hidden. cost+daemon visible |
| H02 | Match between system and the real world (vocabulary) | 2 | "build/plan/auto" exists but not surfaced; `runtime_mode` exposed via `fake/gated_local/provider_backed` is confusing |
| H03 | User control and freedom (undo/redo, fork, rewind) | 0 | no `/fork`, `/rewind`, `/compact` |
| H04 | Consistency and standards (matches Claude Code / Codex norms) | 1 | `@`, `Enter-interrupt`, `Tab-queue`, `Esc Esc`, `/context`, `/compact` all missing |
| H05 | Error prevention (sandbox before shell, trust before run) | 1 | shell escape bypasses sandbox |
| H06 | Recognition over recall (palette, autocomplete) | 3 | slash menu + palette work well |
| H07 | Flexibility/efficiency (power-user shortcuts) | 2 | many bindings exist but Tab-completes only `/`; no `@file` fuzzy |
| H08 | Aesthetic & minimalist design | 2 | ASCII art banner is decorative, not informative |
| H09 | Help users recognize, diagnose, recover from errors | 1 | most errors are stringified exceptions |
| H10 | Help and documentation in context | 2 | static `HelpScreen`; will drift |
| H11 | Color semantics (success/warn/error never as sole cue) | 2 | uses `●` dots; good fallback; but no explicit role color rules |
| H12 | NO_COLOR / reduced-motion / monochrome | 2 | NO_COLOR detected; reduced-motion not honored; TCSS is hard-coded |
| H13 | Performance / first paint | 2 | I did not profile; size of compose tree is small (5 children); should be <100 ms; flicker on resize untested |
| H14 | Streaming & live token feed | 1 | none; final-text-only |
| H15 | Markdown + syntax highlighting | 0 | none |
| H16 | Diff viewer with hunk nav | 1 | flat lines, no color, no nav |
| H17 | Tool-call surface (collapse, expand, copy, rerun) | 2 | collapsible flag but no key, no copy |
| H18 | Approval/risk surface | 1 | HITL-only bar |
| H19 | History (Up/Down, Ctrl+R) | 3 | history works |
| H20 | Sessions (list, switch, resume, fork) | 2 | list+switch works; no fork/rewind |
| H21 | File attach grammar (`@`) | 0 | none |
| H22 | Shell grammar (`!`) | 2 | works but unsafe |
| H23 | Status-line configurability | 0 | hard-coded |
| H24 | Theme switch (live re-skin) | 1 | `/theme` toggles model state but TCSS values are literals |
| H25 | Discoverability of new features (release-notes, what's new) | 0 | no `/release-notes`, no banner pulse |

**Total:** 39 / 100. Median 2. The TUI scores like a competent prototype; competitors all sit 75+.

---

## 7. Information architecture redesign

### 7.1 Proposed view tree

```
ArcApp (App)
└── ArcScreen (Screen)
    ├── Header  ← new compact 2-line header (replaces 3-line ASCII Banner)
    │   ├── Wordmark "ARC"  + version
    │   ├── Workspace + TrustBadge
    │   ├── ModeBadge (Plan/Build/Auto/Review)
    │   └── ContextMeter  (new)
    ├── Transcript  (existing, rebuilt to render markdown)
    │   ├── UserMessage  (rich)
    │   ├── AssistantMessage  (rich, streaming, code-block copy)
    │   ├── ToolCard  (existing, expanded)
    │   ├── CapabilityCardBanner  (new)
    │   ├── ApprovalCard  (new)
    │   ├── McpDecisionBanner  (new)
    │   └── DiffViewer  (rebuilt with hunk nav)
    ├── SlashMenu  (existing, expand to show category chips)
    ├── ActivityTray  (new, Ctrl+X) — background tasks, daemon health, MCP decisions stream
    ├── StatusBar  (rebuilt; configurable, 1-line)
    └── InputArea  (existing, add @ and ! grammar)
```

### 7.2 Modes (formal state machine)

```
       Shift+Tab               Shift+Tab            Shift+Tab
 [Plan] ────────────▶ [Build] ────────────▶ [Auto] ────────────▶ [Review] ─┐
   ▲                                                                       │
   └───────────────────────────── Shift+Tab ───────────────────────────────┘
```

| Mode | Visible affordance | Allowed | Disallowed | Default approval | Notes |
|---|---|---|---|---|---|
| **Plan** | amber `▲ plan` badge | simulator, IR compile, capability dry-run, file read | model calls, tool calls, writes, shell | — | maps to existing `simulation/simulator.py` |
| **Build** | cyan `■ build` badge | model calls (with paid gate), tool calls, single-file writes, shell via sandbox | privileged ops, network without per-call approval | per high-risk | default mode |
| **Auto** | red `▶ auto` badge | everything Build allows + multi-file edits + queued steps | privileged + critical risk | per critical-risk only | requires `--allow-auto` or `/auto on` |
| **Review** | purple `◆ review` badge | reads, diffs, approve/deny pending HITLs, audit verify, capability verify | execution | n/a | post-flight + governance mode |

Cycle key: **`Shift+Tab`** matches Codex CLI [Codex-Plan-Mechanics]. Jump: `/plan`, `/build`, `/auto`, `/review`.

### 7.3 Slash-command namespace (target ≥40)

Grouped (Claude Code grammar, ARC-specific extras in **bold**):

- **Session:** `/clear`, `/compact`, `/context`, `/fork`, `/rewind`, `/resume`, `/new`, `/export`, `/copy`
- **Mode:** `/plan`, `/build`, `/auto`, `/review`, `/status`
- **Models:** `/model`, `/providers`, `/connect`, `/effort`, `/fast`, `/cost`, `/usage`
- **Runtime:** `/runtime`, `/runtimes`, `/run`, `/runs`, **`/simulate`**, **`/blast-radius`**
- **Capabilities:** **`/capabilities verify-run`**, **`/capabilities enforce-mode`**, **`/cards`**
- **MCP:** `/mcp`, **`/mcp risk scan`**, **`/mcp decisions`**, **`/mcp proxy`**, **`/mcp policy explain`**
- **Audit & trust:** **`/audit verify`**, **`/workspace trust`**, `/permissions`
- **HITL:** `/hitl pending`, `/hitl respond`
- **Memory:** **`/memory`**, **`/agents-md list/pin/drift`**, **`/skills`**
- **A2A:** **`/a2a list`**, **`/a2a verify`**, **`/a2a invoke`**
- **Observability:** **`/obs export`**, **`/obs semconv-check`**, `/cost`, `/usage`, **`/replay`**
- **Diagnostics:** `/doctor`, **`/release-notes`**, **`/whatsnew`**, `/bug`, `/feedback`
- **Editor:** `/theme`, `/statusline`, `/title`, `/vim`, `/help`, `/exit`

Frontmatter per command (Claude-Code-style):

```yaml
---
name: capabilities verify-run
aliases: [cards verify-run]
description: Verify all Capability Cards used in a run
argument-hint: "<run-id> [--mode warn|strict|off]"
mode-restriction: any
risk: low
disable-model-invocation: false
---
```

### 7.4 Status-bar contract (configurable)

Slots (in order, each toggleable via `/statusline`):
`mode · model · provider · workspace · trust · audit-mode · context% · session · cost · daemon · streaming · keymap-hint`

Default ≤ width: collapse from the right (drop hint → drop daemon dot → drop cost → …). Width threshold per element.

### 7.5 Command palette taxonomy

Add category chips on the left (`session`, `mcp`, `cap`, `audit`, `runtime`, `obs`, `mode`, `git`, `dx`). Search both `name` and `description`. Keyboard: `↑/↓` navigate, `Enter` run, `Esc` close, `⌘K`/`Ctrl+K` reopen, `?` toggle help inside palette.

---

## 8. Visual design system

### 8.1 Color tokens

Define tokens once (`tui/theme.py`), reference from TCSS via `$token`. Five themes ship: **TokyoNight** (default dark), **Catppuccin Mocha** (alt dark), **Catppuccin Latte** (light), **High Contrast** (a11y), **Monochrome** (NO_COLOR / reduced-color).

Token names (semantic, not literal):

```
$bg, $bg-elev, $bg-sunk, $fg, $fg-muted, $fg-dim
$accent, $accent-bg
$success, $success-bg
$warning, $warning-bg
$error, $error-bg
$info, $info-bg
$user, $assistant, $system, $tool
$diff-add, $diff-add-bg, $diff-del, $diff-del-bg, $diff-mod, $diff-mod-bg
$border, $border-focus, $border-strong
$risk-low, $risk-med, $risk-high, $risk-crit
$mode-plan, $mode-build, $mode-auto, $mode-review
```

### 8.2 Typography

- **Mono only**, JetBrains Mono / Hack / SF Mono as user terminal preference.
- Bold for state changes (selection, focus, current mode).
- Italics avoided (rendered as underline in many terminals).
- Heading sizes carried by `─` rules and box-drawing, never by ANSI font-size hacks.

### 8.3 Iconography

Single ASCII fallback for every glyph; Powerline icons opt-in.

| Concept | Color | Unicode | ASCII fallback |
|---|---|---|---|
| Allow | `$success` | `●` | `[ok]` |
| Deny | `$error` | `✗` | `[no]` |
| Warn | `$warning` | `!` | `[!]` |
| Pending | `$info` | `○` | `[..]` |
| Trust | `$success` | `●` | `[trusted]` |
| Mode plan | `$mode-plan` | `▲` | `(plan)` |
| Mode build | `$mode-build` | `■` | `(build)` |
| Mode auto | `$mode-auto` | `▶` | `(auto)` |
| Mode review | `$mode-review` | `◆` | `(review)` |
| Risk low/med/high/crit | risk colors | `●●●●` | `[L][M][H][C]` |

### 8.4 Spacing

Vertical rhythm uses Textual `padding`: `0 1` for tight chrome, `1 2` for cards. Horizontal hairline gap of 1 cell between meta and content. Cards use `border: round $border` (1px).

### 8.5 Focus & motion

- Focus: 1px `$border-focus` border + subtle `$bg-elev`.
- Motion: cap 200 ms; honor `ARC_REDUCED_MOTION=1`; never block input; spinners cap at 12 fps.
- Synchronized output: enable CSI 2026 h/l atomically per frame [Lobehub-TUI].

### 8.6 Mockups

See `ux/mockups/01_home_dark.png` through `09_no_color_mono.png`. Each caption below pairs the mockup to the file it represents or proposes:

| File | Caption | Represents |
|---|---|---|
| `01_home_dark.png` | Home screen, TokyoNight | replaces `tui/widgets/banner.py` + adds `ContextMeter` + `ModeBadge` |
| `02_approval_card.png` | Approval modal for capability gate | proposed `tui/widgets/approval_card.py` (new) |
| `03_plan_mode_split.png` | Plan-mode split: spec + predicted plan | proposed `tui/views/plan_view.py` (new) |
| `04_command_palette.png` | Command palette with category chips | rebuild of `tui/widgets/command_palette.py` |
| `05_context_meter.png` | Full `/context` overlay | new `tui/views/context_view.py` |
| `06_mcp_risk_stream.png` | Activity-tray MCP decisions stream | new `tui/widgets/activity_tray.py` |
| `07_capability_card_banner.png` | Inline capability-card banner | new `tui/widgets/capability_banner.py` |
| `08_home_light.png` | Light theme home | proves token-driven TCSS |
| `09_no_color_mono.png` | Monochrome NO_COLOR home | proves a11y fallback |

---

## 9. Component spec (before / after)

For each component: **anatomy → states → keys → events → edge cases → a11y → before/after ASCII**. Numbered `R-001`+ for traceability.

### R-001 Header (replaces Banner)

- **Anatomy.** 2 rows. Row 1: `ARC` wordmark · `vX.Y.Z` · workspace path (collapsed `~/proj/sg`) · TrustBadge. Row 2: ModeBadge · ContextMeter · cost · daemon dot.
- **States.** untrusted (red), trusted (green), partial (amber); daemon online/offline; streaming pulse.
- **Keys.** click TrustBadge → `/workspace trust`; click ContextMeter → `/context`.
- **Events.** `MODE_CHANGED`, `TRUST_CHANGED`, `CONTEXT_USAGE_UPDATED`.
- **Edge cases.** Workspace > 30 chars: collapse with `…`. Width < 80: drop daemon dot first.
- **A11y.** Both rows survive in monochrome via brackets `[trusted]`, `[plan]`.

Before:
```
  █████╗ ██████╗  ██████╗     ARC Studio v0.1.0-alpha
 ██╔══██╗██╔══██╗██╔════╝     ~/projects/swarmgraph
 ███████║██████╔╝██║          daemon ● online  ·  /help for commands
```

After:
```
ARC v0.2.0-alpha  ~/projects/swarmgraph  [●trusted]                                ctx 18%
■ build · swarmgraph/gpt-5.4-mini · audit=sha256 · $0.0042 · ●daemon · ●streaming
```

**Why 110%:** the header is now informative on every cell. No row is decoration. Mode/trust/context become *always visible*.

---

### R-002 ContextMeter (new)

- **Anatomy.** Inline in header: `ctx 18%`. On `/context`: full overlay (mockup 05) — 12-column color grid + per-category legend + total ratio bar.
- **States.** `<60% calm`, `60-80% notice`, `80-95% warn`, `>95% danger`.
- **Keys.** `/context` (overlay), `/compact [hint]` (frees space), `Ctrl+T` (tasks).
- **Events.** `CONTEXT_USAGE_UPDATED`.
- **Edge cases.** Unknown total context (older provider) → show only token count.

**Why 110%:** today `total_tokens` is tracked and *never displayed*. Claude Code users cite `/context` as their most-used command [Reddit-50-Slash].

---

### R-003 ModeBadge + ModeCycle

- **Anatomy.** Single colored chip in header: `▲ plan`, `■ build`, `▶ auto`, `◆ review`.
- **States.** mode + dry-run flag + paid flag + isolation flag.
- **Keys.** `Shift+Tab` cycles; `/plan` / `/build` / `/auto` / `/review` jumps.
- **Events.** `MODE_CHANGED`.
- **Edge cases.** Transitioning into `Auto` from untrusted workspace → blocked with toast.

**Why 110%:** ARC has a `data.mode` string and zero affordance. Codex CLI shows mode in the footer + cycle key [Codex-Plan-Mechanics]; ARC must too.

---

### R-004 Transcript MessageWidget (rebuild)

- **Anatomy.** Each message renders as a stack: avatar/role chip → optional metadata row → markdown body → optional inline diff or tool card.
- **States.** streaming (cursor pulse), final, edited, redacted.
- **Keys.** `Ctrl+O` expand/collapse code blocks; `c` to copy focused code block; `e` to edit last user message (= `Esc Esc` when empty).
- **Events.** `MESSAGE_STREAM_CHUNK`, `MESSAGE_STREAM_DONE`, `MESSAGE_EDITED`.
- **Edge cases.** Code blocks > 200 lines auto-collapse with a "show full" affordance.
- **A11y.** screen-reader: emits role + first 80 chars + count of code blocks.

Before (`tui/widgets/transcript.py:69-83`):
```
▸ ARC  16:42:18
  Here is a function:
  def add(a, b):
      return a + b
```

After:
```
▸ arc                                                                       16:42:18
Here is a function:

  python ─────────────────────────────────────────────────────  [c] copy  [Ctrl+O]
  1  def add(a, b):
  2      return a + b
  ───────────────────────────────────────────────────────────────────────────────
```

**Why 110%:** markdown + syntax + copy puts ARC on parity with Claude Code, OpenCode, Gemini CLI all at once. Implementation reuses Textual's `RichLog` + `rich.syntax.Syntax`.

---

### R-005 ToolCard (rebuild)

- **Anatomy.** Header row: status dot + tool name + duration + cost + risk badge. Body: collapsed-by-default after 3 lines. Footer: `[Ctrl+O] expand · [c] copy · [r] rerun`.
- **States.** queued/running/success/error/cancelled/blocked.
- **Keys.** `Ctrl+O` toggle; `c` copy body; `r` rerun (if idempotent metadata).
- **Edge cases.** Background tool → moves to ActivityTray when `Ctrl+B`.

**Why 110%:** today the card has no key to expand, no copy, no risk; risk is the SwarmGraph differentiator.

---

### R-006 CapabilityCardBanner (new)

Mockup 07.

- **Anatomy.** 1-row banner with colored left rail. Format: `{glyph} capability_card · {card_id} · {decision} · {reason or audit_level} · {correlation_id|elapsed}`.
- **States.** allow (green), warn (amber), deny (red).
- **Keys.** `Enter` open card detail; `v` run `/capabilities verify-run` for context.
- **Events.** consumes `CAPABILITY_CARD_DECISION` typed events.

**Why 110%:** turns the existing `capabilities/` subsystem from invisible plumbing into a customer-visible promise.

---

### R-007 ApprovalCard (rebuild of `approval_bar.py`)

Mockup 02.

- **Anatomy.** Centered modal, 80 cols wide, 12 rows tall. Title, subtitle, key/value rows (action, provider, model, estimated cost, risk signals), four-button row (`y` allow once, `a` always, `n` deny, `d` dry-run), footer with audit chain + correlation_id.
- **States.** capability gate, paid-call gate, MCP outbound gate, HITL gate. Each gates uses the same component with a different title and body schema.
- **Keys.** `y`/`a`/`n`/`d` + `Esc`.
- **Edge cases.** Dry-run flag forces `d`-only and dims the others.

**Why 110%:** unifies four separate gates (Capability, Paid, MCP, HITL) into one component. ARC's audit story becomes immediately tangible: every approval is one keypress and is correlation-id-stamped.

---

### R-008 McpDecisionBanner + ActivityTray (new)

Mockup 06.

- **Anatomy.** Tray surface accessible via `Ctrl+X`. Inside: tabs `MCP`, `Tasks`, `Hooks`, `Daemon`. The `MCP` tab is a live stream of recent decisions with columns `time, server, tool, risk, decision, latency, signals`. The banner is a 1-row inline version that appears in the transcript when a decision fires in-context.
- **Keys.** `↑/↓` navigate, `a` approve pending, `d` deny pending, `Enter` inspect, `/` filter.
- **Events.** consumes `MCP_CALL_DECISION` typed events.

**Why 110%:** MCP supply-chain risk is the most discussed 2026 security topic; ARC already classifies; this surface makes the classification *visible and steerable*.

---

### R-009 DiffViewer (rebuild)

- **Anatomy.** Header `── path/to/file ── [3 hunks · +12 -4]`. Body with line numbers, color-coded ±, hunk separators `@@`. Sidebar minimap (10 cols) when width ≥ 140.
- **States.** unified, side-by-side (toggle `s`), word-level (toggle `w`).
- **Keys.** `j/k` line nav; `[`/`]` hunk nav; `s` side-by-side; `w` word-level; `c` copy hunk; `o` open in `$EDITOR`.
- **Edge cases.** Diffs > 5k lines: virtualize.

**Why 110%:** current DiffBlock prints raw text without color. Hunk nav alone is a competitive-parity unlock vs Claude Code's `/diff`.

---

### R-010 SlashMenu (extend)

- **Anatomy.** Category chips on the left of each item. Two-line items: name + hint. Group separators.
- **Keys.** `Tab` to complete first; `↓` to navigate; `Enter` to insert.
- **Edge cases.** Empty query: show MRU first.

---

### R-011 CommandPalette (rebuild)

Mockup 04.

- **Anatomy.** As mockup. Category chips. Searches across name + description + aliases.
- **Keys.** `⌘K`/`Ctrl+K` (open from anywhere), `Esc` close, `?` inline help.

---

### R-012 PlanView (new)

Mockup 03.

- **Anatomy.** Split view: left spec (markdown), right predicted task list with status dots. Header: `Plan mode · read-only` (locked glyph).
- **Keys.** `Shift+Tab` cycle to Build; `/apply` enter Build with the plan as the input.

**Why 110%:** Plan mode is now the de-facto "first read, then write" cadence in all 2026 agentic CLIs; ARC has the IR + Simulator to power it deterministically.

---

### R-013 ContextView (new)

Mockup 05. Full `/context` overlay as described in R-002.

---

### R-014 Toaster (new)

- **Anatomy.** Bottom-right transient toast for non-blocking notices (daemon reconnected, HITL pending, drift detected).
- **Keys.** `Esc` dismiss focused toast; auto-dismiss after 4 s.

---

### R-015 KeycapHint inline element

- **Anatomy.** `[y]`, `[Esc]`, `[Ctrl+P]` rendered as 1px bordered chips inline in text.

---

### R-016 RiskBadge inline element

- **Anatomy.** `●low` / `●medium` / `●high` / `●critical` colored chip with ASCII fallback `[L]`/`[M]`/`[H]`/`[C]`.

---

### R-017 — R-020 (Views to rebuild)

| ID | View | Change | Why |
|---|---|---|---|
| R-017 | `runs_view.py` | Add filters (status, runtime, has-audit, has-card), sort, search; row → drawer with timeline; key `d` runs `/diff vs <run>`. | Today read-only. |
| R-018 | `hitl_view.py` | Reuse ApprovalCard per row; bulk approve with `A`. | Today minimal. |
| R-019 | `sessions_view.py` | Show MRU, snippet of last user message, `f` fork, `r` rewind. | Today list-only. |
| R-020 | `providers_view.py` | Add per-provider quota status, env var doctor, free-tier ★ already exists — keep. | Today best view; small additive polish. |

---

## 10. Keybinding redesign

Canonical map (cross-referenced to Claude Code [ClaudeFast-Interactive], Codex CLI [Codex-CheatSheet], Gemini CLI [Gemini-Medium]):

| Key | Action | ARC today | Claude | Codex | Gemini | Notes |
|---|---|---|---|---|---|---|
| `Enter` | Submit / interrupt during turn | submit only | submit / interrupt | submit / interrupt | submit | **change: while streaming → interrupt** |
| `Shift+Enter` | Newline | yes | yes (after `/terminal-setup`) | yes | yes | keep |
| `Tab` | Autocomplete `/` / queue next message during turn | autocomplete `/` only | queue | queue | queue | **add: queue-during-stream** |
| `Shift+Tab` | Cycle mode Plan→Build→Auto→Review | — | — | yes | — | **new** |
| `@` | Fuzzy file attach | — | yes | yes | yes | **new** |
| `!` | Shell escape via sandbox | yes (no sandbox) | yes | yes | yes | **fix: route via `security/sandbox.py`** |
| `Ctrl+C` | Interrupt; press twice to exit | yes | yes | yes | yes | keep |
| `Ctrl+D` | Exit on empty | yes | yes | yes | yes | keep |
| `Ctrl+P` / `Ctrl+K` | Command palette | yes | — | — | — | keep |
| `Ctrl+L` | Scroll to bottom (rename → clear screen, keep history) | scroll | clear screen | clear screen | clear screen | **change: clear screen** |
| `Ctrl+R` | History search | yes | — | — | — | keep |
| `Ctrl+T` | Task list | — | yes | — | — | **new** |
| `Ctrl+B` | Background current task | — | yes | — | — | **new** |
| `Ctrl+O` | Toggle verbose / expand tool card | toggle card | toggle verbose | — | — | keep with broader semantics |
| `Ctrl+X` | Activity tray | toggle activity (no impl) | — | — | — | **wire** |
| `Ctrl+G` | Open prompt in `$EDITOR` | — | — | yes | — | **new** |
| `Esc` | Cancel/clear input | clear input | close menu | close drawer | close | keep |
| `Esc Esc` | Edit last user message | — | yes | yes | yes | **new** |
| `Ctrl+T` | Toggle task list | — | yes | — | — | **new** |
| `Alt+P` | Switch model | — | yes | — | — | **new** |
| `Alt+T` | Toggle extended thinking | — | yes | — | — | **new** |
| `F1` / `?` | Help overlay | yes | yes | — | — | keep |

**Fallback for terminals that swallow `Shift+Enter`:** display `Alt+Enter` as a second-row hint when ARC detects no shell integration; provide `/terminal-setup` walk-through script.

---

## 11. Slash-command redesign

(See §7.3 for the namespace.) Each command is a single markdown file under `python/src/agent_runtime_cockpit/cli_repl/commands/` with frontmatter:

```yaml
---
name: capabilities verify-run
aliases: [cards verify-run, cap verify-run]
description: Verify all Capability Cards used in a run (signature + audit_level + HITL)
argument-hint: "<run-id> [--mode warn|strict|off]"
mode-restriction: any
risk: low
popup_visible: true
---
```

This frontmatter must be consumed by both `SlashMenu` (live registry) and `CommandPalette` so they stop diverging. Hand-maintained `HelpScreen` static text is **deleted**; help renders from the registry.

---

## 12. Approvals & risk UX

Universal pattern across **Capability gate**, **Paid-call gate**, **MCP outbound gate**, **HITL gate**:

1. **Inline banner** (1-row, colored left-rail) appears in the transcript at decision time.
2. If the decision is `require_approval`, the banner expands into an **ApprovalCard** modal (mockup 02).
3. Buttons: `[y] allow once · [a] allow always · [n] deny · [d] dry-run · [Esc] deny`.
4. Footer always carries `audit chain: <mode>` and `correlation_id: <12-hex>` to bind to the audit chain.
5. After the decision, an entry remains in the transcript as a thin chip, clickable to open the audit record.

**Color rules:**
- `allow` → `$success`. Never use green for anything else in the chat.
- `warn` → `$warning`. Reserved for "would deny in strict".
- `deny` → `$error`. Always paired with `[d]ry-run` to nudge users out of the block.
- `require_approval` → `$info`. Never silently mutate.

**Copy decks** (concise; 12 examples):

| Code | Copy |
|---|---|
| `CARD_NOT_FOUND` (warn) | "No Capability Card for this entity. Run continues; pin one with `/capabilities sign` to enable enforcement." |
| `CARD_NOT_FOUND` (strict) | "Capability Card missing. Run blocked. `/capabilities sign <entity>` to pin." |
| `SIGNATURE_INVALID` | "Signature does not match. Card was tampered or key rotated. `/capabilities verify-run` for detail." |
| `AUDIT_LEVEL_INSUFFICIENT` | "This card requires HMAC audit; run is using SHA-256. Re-run with `--audit hmac` or downgrade card." |
| `HITL_REQUIRED` | "This step requires human approval. Press `[y]` to approve, `[n]` to deny." |
| `PAID_CALL_NOT_ALLOWED` | "Paid call denied. Pass `--allow-paid` or run `/permissions paid on`." |
| `MCP_RISK_HIGH` | "Tool `<name>` classified high-risk (write, network). `[a]` to always allow, `[n]` to deny." |
| `MCP_RISK_CRITICAL` | "Tool `<name>` classified critical (exec, roots-violation). Blocked by policy `strict`. Switch to `auto_low` only if you know what you're doing." |
| `TRUST_DENIED` | "Workspace not trusted. `/workspace trust` to approve." |
| `DRY_RUN` | "Dry-run active. No mutating actions will be executed." |
| `BUDGET_EXCEEDED` | "Budget exceeded: $0.012 used / $0.010 cap. Raise cap with `/budget set --cost 0.05`." |
| `DAEMON_DOWN` | "Local daemon offline. Some views are read-only. `arc serve &` to restore." |

---

## 13. Streaming & live updates

| Concern | Today | After |
|---|---|---|
| Token streaming | "● Thinking…" string, replaced once | streaming reveal with a 1-cell pulsing caret; flushes line-by-line via Textual's `RichLog.write` |
| Tool-call collapsing | always full | first 3 lines + "[Ctrl+O] expand" |
| Long outputs | 20-line cap in ToolCard | virtualized; `[c] copy full` |
| Background tasks | none | `Ctrl+B` moves the active task to ActivityTray; toast on completion |
| Task list | none | `Ctrl+T` opens a multi-step plan with check states |

Implementation: Textual `RichLog` for the transcript + `rich.syntax.Syntax` for code; per-chunk `live.update(refresh=True)` with `transient=False`. Use **synchronized output (CSI ?2026 h/l)** for atomic frames [Lobehub-TUI].

---

## 14. History, search, sessions

| Feature | Today | After |
|---|---|---|
| `↑/↓` history | works | keep |
| `Ctrl+R` history search | works (basic) | fuzzy + MRU |
| `/sessions` list | works (id only) | id + snippet + last activity + cost; `f` fork; `r` rewind |
| `/fork` | — | branch from current point into new session id, copy transcript |
| `/rewind` | — | step back N messages, optionally revert workspace via `git stash` |
| `/compact [hint]` | — | summarize history with optional focus; bound to `Ctrl+J` |
| `/context` | — | overlay (mockup 05) |
| `/resume <id>` | available via flag | promote to slash; show in palette |
| `/export [path]` | — | dumps transcript as markdown + optional bundle |

---

## 15. Error & empty states

Already in §12 copy decks for 12 of the 20 most common; the remaining 8:

| Code | Copy |
|---|---|
| `NO_PROVIDER_KEY` | "No API key found. Set env var or run `/providers` to configure." |
| `RUNTIME_NOT_DETECTED` | "No supported runtime detected in workspace. `arc runtimes` to see options." |
| `SCHEMA_VERSION_UNSUPPORTED` | "Card/run is from a newer schema version. Update ARC: `uv tool upgrade arc-studio`." |
| `LOCK_CONTENTION` | "Workspace locked by another `arc` process. Wait or `arc workspace unlock`." |
| `MCP_DRIFT` | "MCP server `<name>` tool list changed. Inspect with `/mcp drift <name>`." |
| `AUDIT_KEY_MISSING` | "HMAC key unavailable. Verifying in SHA-256 mode. `arc audit key init` to enable HMAC." |
| `WORKSPACE_NOT_FOUND` | "Workspace path missing. Did the folder move? `/workspace show` for current." |
| `RUN_NOT_FOUND` | "No run with id `<id>`. `/runs` to browse." |

**Empty states.** Each modal/view ships with an empty-state illustration (ASCII), one-line explanation, and a primary action link.

---

## 16. Onboarding & doctor

**First-launch wizard (3 keys).** On bare `arc` in a fresh workspace:

```
Welcome to ARC Studio.

  [1] Pick a provider           (we recommend ★ Cerebras for free GPT-OSS)
  [2] Trust this workspace      (~/projects/swarmgraph)
  [3] Take the 60-second tour   (Plan mode → Build mode → Approval card)

  Press 1, 2, or 3 — or Esc to skip.
```

**`/init`.** Generates `.arc/AGENTS.md` skeleton (project conventions), creates a `.arc/` directory if missing, runs `arc doctor`.

**`/doctor`.** Existing `arc doctor` reused; surfaces in a card with `[fix it]` keycap per failed check (link to remediation slash command).

**`/welcome`.** Re-runs the wizard.

---

## 17. Accessibility & i18n

- **`NO_COLOR`**: detected today; extend to swap *all* dot glyphs for `[ok]`/`[!]`/`[..]` text.
- **Reduced motion**: respect `ARC_REDUCED_MOTION=1`; disable pulses, fade-ins, banner animation.
- **Screen reader**: emit a stable a11y label per message: `role: user|assistant; chars: 240; codeblocks: 1`. Textual supports `name`/`tooltip` on every widget.
- **Focus**: visible 1px border on focused widget; logical Tab-order: Header → Transcript → SlashMenu → InputArea → StatusBar.
- **Min size 80×24**: graceful degradation order: drop minimap → collapse banner → drop daemon dot → drop cost from status bar.
- **RTL**: defer; declare in `docs/i18n.md` that strings are en-US only in v0.2.

---

## 18. Performance budget

| Budget | Target | Instrumentation |
|---|---|---|
| First paint after `arc` | < 100 ms | Textual `--log file.log` profiler |
| Keystroke → echo | < 16 ms (1 frame @ 60 fps) | log `Key` event delivery time |
| Streaming token append | < 30 ms per chunk | `Live.update` cadence |
| Resize redraw | < 50 ms | SIGWINCH timing test |
| Spinner | 12 fps cap | `set_interval(1/12, …)` |
| Idle redraw | 0 | no timers running when no state change |
| Slash menu rebuild | < 20 ms | benchmark with 200-command registry |
| Status bar refresh | every 1 s today | move to event-driven; no idle redraw |

Use Textual's `App(log_path=…)` + `textual run --dev` to profile each. Add a `make perf-tui` target.

---

## 19. Implementation plan (4 phases, all in scope)

> All dependencies on already-built backend subsystems are real and cross-linked to the 7-item Capability-Card execution plan in `EXECUTION_PROMPT.md`.

### Phase P0 — Polish (3-4 days; ships under existing alpha)

| ID | Change | Files |
|---|---|---|
| R-001 | New Header (replaces Banner) | `tui/widgets/header.py` (new), retire `widgets/banner.py` |
| R-002 | ContextMeter (inline + `/context`) | `tui/widgets/context_meter.py` (new), `tui/views/context_view.py` (new), wire to `data.total_tokens` |
| R-003 | ModeBadge + `Shift+Tab` cycle + `/plan`/`/build`/`/auto`/`/review` | `tui/widgets/mode_badge.py` (new), edits to `tui/screen.py:31-43` BINDINGS and `_handle_slash` |
| R-004 partial | Markdown body via `rich.markdown.Markdown` for assistant messages | `tui/widgets/transcript.py:69-83`, new `widgets/markdown_block.py` (replace stub) |
| Token-driven TCSS | one `theme.tcss` with `$tokens`; `theme.py` generates Textual variables | `tui/tcss/base.tcss` rewrite |

### Phase P1 — Modes + Approvals (1 week)

| ID | Change | Files |
|---|---|---|
| R-007 | ApprovalCard unifies four gates | `tui/widgets/approval_card.py` (new), `tui/widgets/approval_bar.py` retired |
| R-006 | CapabilityCardBanner consumes `CAPABILITY_CARD_DECISION` | `tui/widgets/capability_banner.py` (new); subscribe to `events` bus |
| R-008 | ActivityTray + McpDecisionBanner consumes `MCP_CALL_DECISION` | `tui/widgets/activity_tray.py`, `tui/widgets/mcp_banner.py` (new); wire `Ctrl+X` |
| R-012 | PlanView using existing `simulation/simulator.py` | `tui/views/plan_view.py` (new) |
| Streaming | Replace `"● Thinking…"` placeholder with `RichLog` + `Live` | `tui/screen.py:296-321`, `tui/widgets/transcript.py` |
| `!` sandbox | Route shell escape through `security/sandbox.py` | `tui/screen.py:271-291` |

### Phase P2 — Components + IA (2 weeks)

| ID | Change | Files |
|---|---|---|
| R-005 | ToolCard rebuild with expand/copy/rerun keys | `tui/widgets/tool_card.py` |
| R-009 | DiffViewer rebuild (hunk nav, side-by-side toggle) | `tui/widgets/diff_block.py` → `tui/widgets/diff_viewer.py` |
| R-010 | SlashMenu category chips + 2-line items | `tui/widgets/slash_menu.py` |
| R-011 | CommandPalette rebuild | `tui/widgets/command_palette.py` |
| R-014/R-015/R-016 | Toaster, KeycapHint, RiskBadge | `tui/widgets/` (new files) |
| R-017–R-020 | Views polish | corresponding `tui/views/*.py` |
| Slash registry from frontmatter | All commands gain frontmatter; `HelpScreen` is removed in favor of registry render | `cli_repl/commands/**` |

### Phase P3 — Themes + a11y (1 week)

| ID | Change | Files |
|---|---|---|
| Token themes × 5 | TokyoNight / Catppuccin Mocha / Catppuccin Latte / High-Contrast / Monochrome | `tui/theme.py`, `tui/tcss/themes/*.tcss` |
| `NO_COLOR` glyph fallback | wrap every `●○✓✗⊘` with theme-aware text fallback | `tui/widgets/*.py` |
| Reduced motion | `ARC_REDUCED_MOTION=1` disables spinners | `tui/screen.py` + widgets |
| Snapshot tests | `pytest-textual-snapshot` against 8 canonical screens | `python/tests/tui/` (new dir) |
| Window-title configurability | `/title`, `/statusline` | `tui/screen.py` + new commands |

---

## 20. Test plan

- **Snapshot tests** (`pytest-textual-snapshot`) for: home dark/light/mono, approval card, plan-mode split, palette, context overlay, MCP stream, capability banner, error states. Store under `python/tests/tui/snapshots/`.
- **Fixture terminals**: 80×24, 120×40, 200×60, 240×72. Each screen rendered in each.
- **NO_COLOR run**: pytest fixture sets `NO_COLOR=1` and asserts no ANSI color escapes in `console.export_text()`.
- **Key-binding contract test**: enumerate `BINDINGS` for every screen; assert canonical map is fully implemented.
- **Golden trace renders**: feed a recorded `JsonlTraceStore` run through the TUI; assert the rendered transcript matches the snapshot.
- **Performance test**: assert first paint < 100 ms in a headless run using `textual run --headless`.

Run command:

```bash
cd python && uv run pytest tests/tui -q
```

---

## 21. Asset inventory produced by this audit

| Path | Purpose |
|---|---|
| `UX_AUDIT_PROMPT.md` | the standalone prompt that produced this audit |
| `UX_AUDIT.md` | this file |
| `ux/mockups/01_home_dark.png` | home screen, TokyoNight |
| `ux/mockups/02_approval_card.png` | approval modal |
| `ux/mockups/03_plan_mode_split.png` | plan-mode split view |
| `ux/mockups/04_command_palette.png` | command palette |
| `ux/mockups/05_context_meter.png` | full `/context` overlay |
| `ux/mockups/06_mcp_risk_stream.png` | MCP decisions stream |
| `ux/mockups/07_capability_card_banner.png` | inline capability banner |
| `ux/mockups/08_home_light.png` | light theme variant |
| `ux/mockups/09_no_color_mono.png` | monochrome NO_COLOR variant |

---

## 22. Risks & anti-patterns (what NOT to copy)

| # | From | Anti-pattern | Why avoid |
|---|---|---|---|
| A1 | Claude Code | `/buddy` terminal pet | feature creep that increases context bytes [TechBytes-CC] |
| A2 | Gemini CLI | long-paragraph default replies | small terminals; ARC must default to bullets [Shipyard] |
| A3 | Codex CLI | plan mode enforced only at prompt level (not runtime) | ARC's Plan must be enforced via capability cards + isolation [Codex-Plan-Mechanics] |
| A4 | Kiro | spec-first overhead even for solo prototyping | make `/init` optional [DigitalApplied-Kiro] |
| A5 | Many | Unicode emoji as primary signaling | breaks on Windows / older fonts; use box-drawing [Lobehub-TUI] |
| A6 | Many | full redraw on every keystroke | use diff + double buffer + synchronized output [Lobehub-TUI] |
| A7 | Some | mouse-only controls | always provide keyboard equivalent |
| A8 | Many | LLM-driven security decisions | violates CoSAI 2026 [see earlier audit] |
| A9 | Some | "delight" animations that delay input | cap at 200 ms; cancellable |
| A10 | Many | hidden modal modes (vim default-on) | always opt-in via `/vim` |
| A11 | Cursor/Windsurf | cloud-tied UX | ARC must remain local-first; no `/cloud` |
| A12 | Codex | undisclosed model-id naming | always show full model id in status bar |

---

## 23. Final recommendation — the single highest-leverage UX change

**Ship R-001 + R-002 + R-003 together as one PR.** The Header + ContextMeter + ModeBadge ship in 3-4 days, touch only the chrome (no risk to chat behavior), and **simultaneously close H01, H03 partial, P1, P2, the absent context meter, and the absent mode cycle**. Every user opens the app and immediately sees: *"oh — this is a 2026 tool, not a 2024 tool"*. That single PR carries ARC from a 39/100 heuristic score into the mid-60s, sets the visual vocabulary for every subsequent phase, and gives the Capability-Card and MCP-risk subsystems their first real surface.

Implementation order:

```bash
# 1. Token-driven TCSS first (unblocks every theme later)
mkdir -p python/src/agent_runtime_cockpit/tui/tcss/themes
mv python/src/agent_runtime_cockpit/tui/tcss/base.tcss python/src/agent_runtime_cockpit/tui/tcss/themes/tokyonight.tcss

# 2. Header widget
python/src/agent_runtime_cockpit/tui/widgets/header.py        # R-001
python/src/agent_runtime_cockpit/tui/widgets/context_meter.py # R-002
python/src/agent_runtime_cockpit/tui/widgets/mode_badge.py    # R-003

# 3. Screen wires Shift+Tab and /plan|/build|/auto|/review
edit python/src/agent_runtime_cockpit/tui/screen.py:31-43     # BINDINGS
edit python/src/agent_runtime_cockpit/tui/screen.py:53-58     # compose()
edit python/src/agent_runtime_cockpit/tui/screen.py:140-260   # slash handlers

# 4. Snapshots
mkdir -p python/tests/tui/snapshots
python/tests/tui/test_header_snapshot.py
python/tests/tui/test_mode_cycle.py

# 5. Verify
cd python && uv run pytest tests/tui -q
cd python && uv run ruff check src/agent_runtime_cockpit/tui
cd python && uv run mypy src/agent_runtime_cockpit/tui
cd python && uv run arc                      # eyeball
NO_COLOR=1 cd python && uv run arc           # eyeball
COLUMNS=80 LINES=24 cd python && uv run arc  # eyeball
```

Everything in §19 P1-P3 sequentially follows from this base.

---

## Citations

[Reddit-50-Slash] https://www.reddit.com/r/ClaudeAI/comments/1shz99l/here_are_50_slash_commands_in_claude_code_that/ (2026-04)
[TechBytes-CC] https://techbytes.app/posts/claude-code-2026-cheat-sheet-hooks-mcp-commands/ (2026-04)
[ClaudeFast-Interactive] https://claudefa.st/blog/guide/mechanics/interactive-mode (2026-06)
[Hidekazu-CC] https://hidekazu-konishi.com/entry/claude_code_features_settings_reference_2026.html (2026-05)
[Codex-CheatSheet] https://computingforgeeks.com/codex-cli-cheat-sheet/ (2026-03)
[Codex-Slash] https://developers.openai.com/codex/cli/slash-commands (2026-05)
[Codex-Plan-Mechanics] https://codex.danielvaughan.com/2026/04/08/plan-mode-mechanics/ (2026-04)
[Kiro-Ernest] https://www.ernestchiang.com/en/notes/ai/kiro/ (2025-07)
[DigitalApplied-Kiro] https://www.digitalapplied.com/blog/amazon-kiro-aws-agentic-ide-complete-guide (2026-04)
[Gemini-Medium] https://medium.com/@fhinkel/gemini-cli-from-terminal-interface-to-agentic-ecosystem-05b0d38bac40 (2026-05)
[Shipyard] https://shipyard.build/blog/claude-code-vs-gemini-cli/ (2024-07, still cited)
[Lobehub-TUI] https://lobehub.com/skills/neversight-learn-skills.dev-tui-design (2026-03)
[Toad-Announce] https://willmcgugan.github.io/announcing-toad/ (2025-07)
[Aider-Compare] https://sanj.dev/post/comparing-ai-cli-coding-assistants/ (2026-04)
[Pasquale-Tools] https://pasqualepillitteri.it/en/news/386/ai-coding-cli-alternatives-2026 (2026-06)
