# 7. CLI Full-Screen Layout Mockups

**Version:** v0.1.0-draft
**Date:** 2026-05-16
**Status:** Draft
**Rendering target:** Monospace terminal, UTF-8, 256-colour or true-colour
**Minimum width:** 80 columns | **Reference width:** 100 columns
**Minimum height:** 24 rows | **Reference height:** 30 rows

---

## Conventions used throughout this section

| Notation | Meaning |
|----------|---------|
| `«region»` | Named layout region in the annotated breakdown |
| `[TOKEN]` | Colour token from the design-token palette |
| `⌨` | Keybinding |
| `░` | Empty/padding area rendered in `bg.canvas` |
| `▏` | Vertical thin separator |
| `━` | Horizontal heavy rule |
| `─` | Horizontal light rule |

**Global degradation rules (80-col):**

1. Truncate right-side padding first.
2. Collapse multi-column layouts into single-column stacked layouts.
3. Abbreviate labels: "Workspace" → "WS", "Runtime" → "RT", "Provider" → "Prov".
4. Elide status-line segments right-to-left (see §7.14).
5. Graph views reduce node box width from 18 to 12 chars.
6. File paths truncate from the left with `…/` prefix.
7. Key badges compress: `✓ Set (env)` → `✓`.

---

## 7.1 First-Run Welcome

**Scenario:** Fresh project, SwarmGraph detected as default runtime, no provider API key set. User launches `arc-studio` for the first time in this workspace.

### (a) 100-column mockup (30 rows)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                    │
│                            █████╗ ██████╗  ██████╗                                                 │
│                           ██╔══██╗██╔══██╗██╔════╝                                                 │
│                           ███████║██████╔╝██║                                                      │
│                           ██╔══██║██╔══██╗██║                                                      │
│                           ██║  ██║██║  ██║╚██████╗                                                 │
│                           ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  Studio v0.1.0-alpha                           │
│                                                                                                    │
│  ──────────────────────────────────────────────────────────────────────────────────────────────     │
│                                                                                                    │
│   Workspace    ~/projects/my-agent-app                                        Detected ✓           │
│   Runtime      SwarmGraph                                                     Ready ✓              │
│   Model        claude-sonnet-4-5 (default)                                                         │
│   Mode         Build                                                                               │
│                                                                                                    │
│  ──────────────────────────────────────────────────────────────────────────────────────────────     │
│                                                                                                    │
│   ⚠  No provider API key found                                                                    │
│                                                                                                    │
│   ARC Studio needs at least one LLM provider key to function.                                      │
│   Set one of the following environment variables:                                                   │
│                                                                                                    │
│     ANTHROPIC_API_KEY    ✗ not set       export ANTHROPIC_API_KEY="sk-…"                           │
│     OPENAI_API_KEY       ✗ not set       export OPENAI_API_KEY="sk-…"                              │
│     GOOGLE_API_KEY       ✗ not set       export GOOGLE_API_KEY="…"                                 │
│                                                                                                    │
│   Or run /config to configure providers interactively.                                             │
│                                                                                                    │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ SwarmGraph ▏ claude-sonnet-4-5 ▏ Build ▏ ~/projects/my-agent-app ▏ ✗ No key ▏ /help for commands  │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### (b) Annotated breakdown

| Region | Rows | Description |
|--------|------|-------------|
| «logo» | 2–7 | ASCII art ARC logo, centred horizontally. Decorative only. |
| «version» | 7 | Version string `Studio v0.1.0-alpha` right of logo on same line. |
| «separator-1» | 9 | Light horizontal rule `─`, full content width. |
| «workspace-info» | 11–14 | Four key=value rows: Workspace, Runtime, Model, Mode. Left-aligned labels at col 4, values at col 17, right-aligned badges at col 73+. |
| «separator-2» | 16 | Light horizontal rule. |
| «warning-block» | 18–27 | Warning icon `⚠` + bold title, explanation paragraph, three key-status rows showing variable name, status badge, and example export command. |
| «hint» | 28 | Text pointing user to `/config`. |
| «status-line» | 30 | Bottom status bar (full spec in §7.14). |

### (c) Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Focus input prompt (appears after key is set or user dismisses warning) |
| `/` | Begin slash command entry |
| `Tab` | Cycle mode: Build → Plan → Auto → Build |
| `Ctrl+C` | Exit |
| `?` or `F1` | Show `/help` |
| `Ctrl+L` | Clear and repaint |

### (d) Colour tokens

| Region | Token |
|--------|-------|
| «logo» | `accent.primary` |
| «version» | `text.secondary` |
| «separator» lines | `text.muted` |
| «workspace-info» labels | `text.secondary` |
| «workspace-info» values | `text.primary` |
| «workspace-info» badges "Detected ✓", "Ready ✓" | `state.success` |
| «warning-block» icon `⚠` | `state.warning` |
| «warning-block» title | `state.warning` bold |
| «warning-block» body text | `text.primary` |
| «warning-block» `✗ not set` | `state.danger` |
| «warning-block» export examples | `text.muted` |
| «hint» `/config` | `accent.primary` underline |
| «status-line» background | `bg.canvas` inverted |
| «status-line» `✗ No key` | `state.danger` |

### (e) Exact placeholder text

```
Studio v0.1.0-alpha
Workspace    ~/projects/my-agent-app                           Detected ✓
Runtime      SwarmGraph                                        Ready ✓
Model        claude-sonnet-4-5 (default)
Mode         Build

⚠  No provider API key found

ARC Studio needs at least one LLM provider key to function.
Set one of the following environment variables:

  ANTHROPIC_API_KEY    ✗ not set       export ANTHROPIC_API_KEY="sk-…"
  OPENAI_API_KEY       ✗ not set       export OPENAI_API_KEY="sk-…"
  GOOGLE_API_KEY       ✗ not set       export GOOGLE_API_KEY="…"

Or run /config to configure providers interactively.
```

### (f) 80-column degraded version

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                      ARC Studio v0.1.0-alpha                                 │
│                                                                              │
│  ──────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   WS   ~/projects/my-agent-app                     Detected ✓               │
│   RT   SwarmGraph                                  Ready ✓                   │
│   Mod  claude-sonnet-4-5 (default)                                           │
│   Mode Build                                                                 │
│                                                                              │
│  ──────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   ⚠  No provider API key found                                              │
│                                                                              │
│   Set one of the following environment variables:                            │
│                                                                              │
│     ANTHROPIC_API_KEY  ✗  export ANTHROPIC_API_KEY="sk-…"                    │
│     OPENAI_API_KEY     ✗  export OPENAI_API_KEY="sk-…"                       │
│     GOOGLE_API_KEY     ✗  export GOOGLE_API_KEY="…"                          │
│                                                                              │
│   Or run /config to set up providers.                                        │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ SwarmGraph ▏ sonnet-4-5 ▏ Build ▏ ✗ No key ▏ /help                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Degradations applied:** ASCII logo → single text line. Labels abbreviated. Export examples kept but tighter. Status line: model truncated to `sonnet-4-5`, workspace path dropped, `/help for commands` → `/help`.

---

## 7.2 Steady-State Chat

**Scenario:** One user turn asking about code. Assistant responds with two tool calls: a free `read_file` (completed) and a paid `llm_analyze` sub-call requiring confirmation. Streaming is in progress.

### (a) 100-column mockup (30 rows)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ARC Studio                                                                  session: a3f8c2e     │
├━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┤
│                                                                                                    │
│  ┌─ You ────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Explain the consensus voting logic in swarmMain/main.py and suggest improvements.           │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                    │
│  ┌─ Assistant ──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ I'll examine the consensus voting implementation.                                           │  │
│  │                                                                                             │  │
│  │ ┌─ tool: read_file ─────────────────────────────────────────────────────── 1.2s ✓ ────┐    │  │
│  │ │ swarmMain/main.py (lines 42–87)                                                     │    │  │
│  │ └─────────────────────────────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                                             │  │
│  │ ┌─ tool: llm_analyze ─────────────────────────────────── paid call ── ⠹ pending ────┐    │  │
│  │ │ Provider: anthropic/claude-sonnet-4-5                                               │    │  │
│  │ │ Estimated cost: ~$0.003 (1.2k input tokens)                                        │    │  │
│  │ │                                                                                     │    │  │
│  │ │                      [ ✓ Approve ]    [ ✗ Deny ]    [ Always allow ]                │    │  │
│  │ └─────────────────────────────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                                             │  │
│  │ The consensus voting logic at line 48 uses a simple majority threshold. Each worker         │  │
│  │ agent casts a vote, and the queen aggregates results using                                  │  │
│  │ ⠹ streaming…                                                                               │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                    │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  > _                                                                                               │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ SwarmGraph ▏ claude-sonnet-4-5 ▏ Build ▏ ~/projects/my-agent-app ▏ ✓ anthropic ▏ ⠹ running       │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### (b) Annotated breakdown

| Region | Rows | Description |
|--------|------|-------------|
| «title-bar» | 1 | App name left-aligned, session ID `a3f8c2e` right-aligned |
| «separator» | 2 | Heavy rule `━` |
| «chat-area» | 3–26 | Scrollable message area |
| «user-bubble» | 4–6 | User message. Label "You" in header. Full text on one line. |
| «assistant-bubble» | 8–25 | Assistant response. Contains two inline tool-call blocks and streaming text. |
| «tool-block-1» | 11–13 | Completed `read_file`. Shows path, line range, duration `1.2s`, checkmark `✓`. Single collapsed line (expandable with `Enter`). |
| «tool-block-2» | 15–20 | Pending paid `llm_analyze`. Border highlighted in warning colour. Shows provider, cost estimate, three action buttons. Spinner `⠹` animates in header. |
| «streaming-text» | 22–24 | Partially rendered response text. Last line shows spinner `⠹ streaming…` |
| «input-area» | 28 | Prompt `> ` with blinking cursor `_`. Grows to max 5 lines. |
| «status-line» | 30 | Status bar with animated spinner segment `⠹ running` |

### (c) Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Send message (input focused) / Expand tool block (tool focused) |
| `Shift+Enter` | Newline in multiline input |
| `y` or `Enter` | Approve paid call (when confirmation is focused) |
| `n` | Deny paid call |
| `a` | Always allow this provider for session |
| `Escape` | Dismiss confirmation without action |
| `Tab` | Cycle mode chip |
| `Ctrl+C` | Cancel streaming / interrupt agent |
| `↑` / `↓` | Scroll chat history |
| `Ctrl+L` | Clear screen, keep history |
| `/` (empty input) | Open slash command autocomplete |
| `PgUp` / `PgDn` | Page scroll in chat area |

### (d) Colour tokens

| Region | Token |
|--------|-------|
| «title-bar» text | `text.primary` |
| «title-bar» session ID | `text.muted` |
| «user-bubble» label "You" | `accent.primary` bold |
| «user-bubble» border + text | `text.muted` border, `text.primary` text |
| «assistant-bubble» label "Assistant" | `state.info` bold |
| «assistant-bubble» border | `text.muted` |
| «tool-block-1» border | `text.muted` |
| «tool-block-1» label | `text.secondary` |
| «tool-block-1» duration | `text.muted` |
| «tool-block-1» `✓` | `state.success` |
| «tool-block-2» border | `state.warning` |
| «tool-block-2» label | `text.secondary` |
| «tool-block-2» `paid call` badge | `state.warning` bg, `bg.canvas` fg |
| «tool-block-2» spinner `⠹ pending` | `state.running` animated |
| «tool-block-2» `[✓ Approve]` | `state.success` inverse |
| «tool-block-2» `[✗ Deny]` | `state.danger` inverse |
| «tool-block-2» `[Always allow]` | `text.secondary` inverse |
| «streaming-text» body | `text.primary` |
| «streaming-text» `⠹ streaming…` | `state.running` animated |
| «input-area» `>` | `accent.primary` |
| «input-area» cursor | `text.primary` blink |
| «status-line» `⠹ running` | `state.running` animated |

### (e) Exact placeholder text

```
You: Explain the consensus voting logic in swarmMain/main.py and suggest improvements.