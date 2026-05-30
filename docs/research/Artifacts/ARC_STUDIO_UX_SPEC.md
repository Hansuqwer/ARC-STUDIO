# ARC Studio — Visual and UX Specification

**Version:** 0.1.0-draft  
**Date:** 2026-05-16  
**Status:** Review draft; feature-roadmap review findings integrated
**Production Grade:** Expanded interaction, component, fallback, and accessibility detail

## Executive Summary

This specification optimises for three things: chat-first default, graph as a primary surface, and honest per-adapter scope. `arc-studio` opens an interactive chat in the current workspace, the SwarmGraph topology is visible during planning and live execution, and every default runtime is labelled by what it can do today instead of what it may support later.

## 0.5 v0.1 Scope — In, Out, Reserved

### In Scope For v0.1

| Area | Ships in v0.1 |
|---|---|
| CLI | Chat-first `arc-studio`, global install, categorised slash commands, Plan/Build/Auto mode, `@file`/`@folder` mentions, queued input, `/undo`/`/redo`. |
| IDE | Chat, Graph, Runs, Review/Apply, Config, and Status bar in Theia-native layout. Tasks Step cards appear inline in Chat; Phase/Loop views reserved. |
| Runtime | SwarmGraph default and bundled. LangGraph, CrewAI, OpenAI Agents, AG2 shown with gating. |
| Providers | Keyring storage, env-var override, in-app key entry, no secret logging. |
| Graph | Live graph during a run. No replay scrubber. |
| Trust | Workspace trust gate before writes, shell, or paid providers. |
| Cost | Status line, `/status`, Runs table, and paid-call confirmation. |
| Sessions | Shared CLI/IDE session lifecycle, resume, compact, `/sessions`, crash recovery, queued messages. |
| Daemon | Explicit daemon lifecycle state machine and recovery actions. |
| Cockpit primitives | Minimal Run Contract, Run Receipt, Failure Autopsy, EvidenceRefs, stable cross-surface IDs, and TrustDiff schema. |

### Out Of Scope For v0.1

| Area | Deferred |
|---|---|
| Default adapters | LlamaIndex and LM Arena hidden from default UI; advanced commands remain. |
| Trace UI | No `/trace`, no Timeline component, no ReplayScrubber, no event JSON viewer. |
| Replay | No graph scrubber or time-travel UI. Advanced replay command may remain. |
| Planner | Multi-phase plans with runtime annotations deferred to v0.2. |
| Router | Suggestion-based runtime switching deferred to v0.2. |
| HotLoop | Runtime, Device panel, Frames panel, loop trace, frame diffs deferred to v0.2. |
| Parallel phases | Deferred to v0.3+. |
| Inline editor diffs | Cursor-style inline edits deferred to v0.2; v0.1 uses Review panel + Theia diff editor. |
| `@symbol`, `@url`, image input | Protocol fields reserved; implementation deferred. |

### Reserved In v0.1 Protocol

| Reservation | Purpose |
|---|---|
| `handoff` event kind | Carries `goal_for_next_phase`, `state`, `constraints`, `references`, `prior_audit_links`; no v0.1 runtime emits it. |
| Device panel slot | v0.2 HotLoop screenshot/device surface. |
| Frames panel slot | v0.2 HotLoop visual diff timeline surface. |
| Runtime manifest format | One manifest per runtime; SwarmGraph manifest ships first. |
| Tasks phase/loop views | Tasks ships Step view in v0.1; Phase and Loop trace views reserved. |
| Attachments | Image attachment shape is reserved on input and transcript cards; no v0.1 implementation. |
| Mentions | `@symbol` and `@url` syntax reserved; `@file` and `@folder` ship. |
| `run_contract` | Pre/post run contract schema; v0.1 renders minimal pre-run contract. |
| `run_receipt` | Signed per-run artifact schema for support, PRs, evals, and audit verification. |
| `evidence_refs` | Optional evidence references on messages, runs, failures, receipts, and graph nodes. |
| `failure_autopsy` | Structured failed-run diagnosis replacing raw trace-first UX. |
| Stable IDs | `message_id`, `decision_id`, `approval_id`, `policy_decision_id`, and stable `node_id` links across Chat, Graph, Runs, Ledger, and receipts. |
| `trust_diff` | Structured diff for trust, policy, provider, and runtime capability changes. |
| `frame_receipt` | HotLoop visual evidence receipt type reserved for v0.2. |
| Graph node menu | Read-only graph commands reserved: explain edge, show evidence, open receipt; mutating rerun/pause waits for checkpoint support. |

### Roadmap

v0.2: HotLoop, router, planner, Device, Frames. Router and planner can land independently, but become useful when more than one runtime is viable. v0.3: trace UI redesign, audit explorer, plan templates, parallel phase execution.

## Table Of Contents

| Section | Scope |
|---|---|
| §1 | Brand foundation |
| §2 | Colour system |
| §3 | Typography |
| §4 | Iconography |
| §5 | Layout and spacing |
| §6 | Motion |
| §7 | CLI full screen layouts |
| §8 | IDE full screen layouts |
| §9 | Component library |
| §10 | Content and microcopy |
| §11 | Graph visualiser |
| §12 | Backgrounds and surfaces |
| §13 | Sound and haptics |
| §14 | Accessibility |
| §15 | States and edge cases |
| §16 | Assets and deliverables |
| §17 | Open questions |

---

## 1. Brand Foundation

### 1.1 Product Name And Wordmark

Product name: **ARC Studio**.

| Concept | Specification |
|---|---|
| A: Directed graph A-R-C | A vector mark built from seven circular nodes and directed edges. The left stroke forms `A`, the middle curve forms `R`, and the right open curve forms `C`. The queen node sits at the `A` apex and workers sit on the lower graph layer. Negative space must keep the `A`, `R`, and `C` readable at 64px. Monochrome uses `text.primary` for nodes and `border.strong` for edges. Minimum legible size: 32px app icon, 64px docs hero. Deliverables: `.svg`, `.png` at 16/32/64/128/256/512, `.ico`, `.icns`. Prompt: `vector logo, directed graph nodes and arrows forming letters A R C, queen node apex, worker nodes lower layer, geometric, monochrome-ready, no gradients`. |
| B: Geometric arc mark | A single bold arc segment wraps around a small agent dot. The arc forms a partial cockpit silhouette and reads at favicon scale. Negative space must preserve a clear inner circle at 16px. Monochrome uses a filled shape only; no internal stroke under 24px. Minimum legible size: 16px favicon. Deliverables: `.svg`, `.png` at 16/32/64/128/256/512, `.ico`, `.icns`. Prompt: `minimal geometric logo, bold arc segment around agent dot, cockpit silhouette, works at 16px favicon, flat vector, no text`. |
| C: Monospace wordmark | `ARC Studio` set in JetBrains Mono with one accent glyph: `ARC·Studio` or `ARC›Studio`. The accent glyph doubles as the CLI prompt marker. Negative space must keep the glyph visible at status-bar height. Monochrome uses `text.primary`; accent glyph uses `accent.primary` only when colour is available. Minimum legible size: 11px text. Deliverables: `.svg`, `.png` at 128/256/512, text lockup tokens. Prompt: `monospace wordmark ARC Studio with one blue accent glyph, terminal status bar style, precise spacing, flat vector`. |

### 1.2 Tagline And Voice

Tagline: **Run agents. See everything.**

| Rule | Use | Avoid |
|---|---|---|
| Name the state | `Daemon unreachable at 127.0.0.1:7777.` | `Something went wrong.` |
| Name the fix | `Run arc-studio doctor or start the daemon.` | `Try again later.` |
| Name paid/network actions before running | `This may call Anthropic. Estimated ceiling: $0.08.` | `Running provider task...` |

| Before | After |
|---|---|
| `Error: failed` | `Runtime missing: LangGraph needs ARC_LANGGRAPH_EXPORT. Set it in /config > Runtime.` |
| `No API key` | `Provider key missing: ANTHROPIC_API_KEY is not set. Add it with /providers.` |
| `Run failed` | `Run failed after 12.4s at node reviewer. Open Runs for summary or use arc-studio advanced runs trace <id>.` |

### 1.3 Brand Attributes

| Attribute | UI consequence |
|---|---|
| Honest | Runtime buttons are disabled when a runtime has no run path. |
| Observable | Every run exposes live graph state, run status, failure reason, and advanced trace access. |
| Local-first | Workspace path, daemon URL, and provider mode are visible in `/status`. |
| Reversible | Diff, apply, undo, and rollback actions appear together. |
| Bounded | Paid calls, shell actions, and trust changes require explicit confirmation. |
| Auditable | Every run produces a receipt linked to signed audit entries. |
| Evidenced | Factual claims can cite files, tool outputs, graph nodes, run summaries, ledger entries, or receipts. |
| Negotiated | Runtime actions are gated by declared capabilities and degradation behavior. |

---

## 2. Colour System

### 2.1 Core Palette

Contrast ratios are against the expected text/background pairing. Defaults meet WCAG AA: normal text `>=4.5:1`, UI components `>=3:1`.

| Token | Dark | Light | Contrast | Use rule |
|---|---:|---:|---:|---|
| `bg.canvas` | `#1a1b26` | `#f8f9fc` | 12.7 / 12.2 | App background. |
| `bg.surface` | `#24283b` | `#ffffff` | 10.8 / 14.4 | Panels and cards. |
| `bg.surface.raised` | `#292e42` | `#f0f2f7` | 9.8 / 11.6 | Hover/focused surfaces. |
| `bg.sunken` | `#16161e` | `#e8ecf0` | 13.4 / 10.3 | Code blocks, run details, inline logs. |
| `border.subtle` | `#3b4261` | `#d8deea` | 3.2 / 3.1 | Low-emphasis separators. |
| `border.default` | `#565f89` | `#b8c0d4` | 4.8 / 4.2 | Inputs and panels. |
| `border.strong` | `#7aa2f7` | `#2e59d9` | 6.7 / 5.7 | Focus and active edges. |
| `text.primary` | `#c0caf5` | `#1f2335` | 10.8 / 14.4 | Main text. |
| `text.secondary` | `#a9b1d6` | `#3b4261` | 8.5 / 9.6 | Secondary labels. |
| `text.muted` | `#787c99` | `#5c637a` | 4.8 / 6.2 | Placeholder/help text. |
| `text.inverse` | `#1a1b26` | `#ffffff` | 8.2 / 7.4 | Text on accent fills. |
| `accent.primary` | `#7aa2f7` | `#2e59d9` | 6.7 / 5.7 | Run, Send, primary buttons. |
| `accent.primary.hover` | `#9abdf5` | `#2448b8` | 8.3 / 6.8 | Primary hover. |
| `accent.primary.active` | `#5f87e8` | `#1d3f9f` | 5.1 / 7.4 | Primary pressed. |
| `accent.secondary` | `#bb9af7` | `#6a42c2` | 7.0 / 5.6 | Runtime/model/config links. |
| `state.success` | `#9ece6a` | `#2e7d32` | 8.1 / 5.1 | Completed, key set. |
| `state.success.bg` | `#1f3320` | `#e8f5e9` | 5.8 / 5.0 | Success cards. |
| `state.warning` | `#e0af68` | `#b8860b` | 7.4 / 4.8 | Paid call, missing req. |
| `state.warning.bg` | `#3b2f1e` | `#fff8e1` | 5.0 / 4.6 | Warning cards. |
| `state.danger` | `#f7768e` | `#c62828` | 6.2 / 5.6 | Failed/destructive. |
| `state.danger.bg` | `#3b1f2a` | `#ffebee` | 5.4 / 5.4 | Error cards. |
| `state.info` | `#7dcfff` | `#0277bd` | 8.2 / 5.1 | HITL/notice. |
| `state.unknown` | `#c0caf5` | `#5c637a` | 10.8 / 6.2 | Unknown cost, unknown confidence, unverified capability. |
| `state.info.bg` | `#1d3342` | `#e1f5fe` | 5.7 / 5.2 | Info cards. |
| `state.running` | `#7aa2f7` | `#2e59d9` | 6.7 / 5.7 | Animated execution state. |
| `graph.node.queen` | `#bb9af7` | `#7c4dff` | 7.0 / 4.8 | SwarmGraph queen nodes. |
| `graph.node.worker` | `#7aa2f7` | `#2e59d9` | 6.7 / 5.7 | Worker/agent nodes. |
| `graph.node.tool` | `#ff9e64` | `#e65100` | 7.0 / 5.2 | Tool nodes. |
| `graph.node.decision` | `#e0af68` | `#f57f17` | 7.4 / 4.5 | Router/decision nodes. |
| `graph.node.hitl` | `#f7768e` | `#c62828` | 6.2 / 5.6 | Approval nodes. |
| `graph.node.terminal` | `#9ece6a` | `#2e7d32` | 8.1 / 5.1 | Start/end nodes. |
| `graph.node.state.idle` | `#565f89` | `#8a94ad` | 4.8 / 3.2 | Idle overlay. |
| `graph.node.state.running` | `#7aa2f7` | `#2e59d9` | 6.7 / 5.7 | Running overlay. |
| `graph.node.state.waiting` | `#e0af68` | `#b8860b` | 7.4 / 4.8 | Awaiting HITL. |
| `graph.node.state.done` | `#9ece6a` | `#2e7d32` | 8.1 / 5.1 | Done overlay. |
| `graph.node.state.failed` | `#f7768e` | `#c62828` | 6.2 / 5.6 | Failed overlay. |
| `graph.edge.default` | `#565f89` | `#8a94ad` | 3.5 / 3.2 | Inactive edges. |
| `graph.edge.active` | `#7aa2f7` | `#2e59d9` | 6.7 / 5.7 | Active edge. |
| `graph.edge.replay` | `#bb9af7` | `#6a42c2` | 7.0 / 5.6 | Reserved for v0.3 replay/audit explorer. |
| `diff.add` | `#1f3320` | `#e8f5e9` | 5.8 / 5.0 | Added line bg. |
| `diff.add.gutter` | `#9ece6a` | `#2e7d32` | 8.1 / 5.1 | Added gutter. |
| `diff.remove` | `#3b1f2a` | `#ffebee` | 5.4 / 5.4 | Removed line bg. |
| `diff.remove.gutter` | `#f7768e` | `#c62828` | 6.2 / 5.6 | Removed gutter. |
| `diff.context` | `#24283b` | `#ffffff` | 10.8 / 14.4 | Context line bg. |
| `syntax.keyword` | `#bb9af7` | `#6a42c2` | 7.0 / 5.6 | Keywords. |
| `syntax.string` | `#9ece6a` | `#2e7d32` | 8.1 / 5.1 | Strings. |
| `syntax.number` | `#ff9e64` | `#e65100` | 7.0 / 5.2 | Numbers. |
| `syntax.comment` | `#787c99` | `#5c637a` | 4.8 / 6.2 | Comments. |
| `syntax.function` | `#7dcfff` | `#0277bd` | 8.2 / 5.1 | Functions. |
| `syntax.type` | `#e0af68` | `#b8860b` | 7.4 / 4.8 | Types/classes. |
| `syntax.variable` | `#c0caf5` | `#1f2335` | 10.8 / 14.4 | Variables. |

High-contrast variant: `bg.canvas=#000000`, `bg.surface=#0b0b0b`, `text.primary=#ffffff`, `border.default=#ffffff`, `accent.primary=#00aaff`, `state.success=#00ff66`, `state.warning=#ffcc00`, `state.danger=#ff4d4d`, `state.info=#66d9ff`. All normal text pairings target `>=7:1`.

### 2.2 Terminal Palette

| ANSI | Colour role | Token |
|---:|---|---|
| 0 | black | `bg.sunken` |
| 1 | red | `state.danger` |
| 2 | green | `state.success` |
| 3 | yellow | `state.warning` |
| 4 | blue | `accent.primary` |
| 5 | magenta | `graph.node.queen` |
| 6 | cyan | `state.info` |
| 7 | white | `text.primary` |
| 8 | bright black | `text.muted` |
| 9 | bright red | `state.danger` |
| 10 | bright green | `state.success` |
| 11 | bright yellow | `state.warning` |
| 12 | bright blue | `accent.primary.hover` |
| 13 | bright magenta | `accent.secondary` |
| 14 | bright cyan | `state.info` |
| 15 | bright white | `text.inverse` |

If the terminal reports `<256` colours, use ANSI slots only. If monochrome, encode state with glyphs: `✓`, `!`, `✗`, `?`, plus labels.

### 2.3 Theme Switching

`theme = "auto" | "dark" | "light" | "high-contrast"`. CLI stores this at `~/.config/arc-studio/config.yaml`; project override is `.arc/config.yaml`. CLI resolves `auto` from `COLORFGBG`, terminal OSC 11 when available, then OS appearance fallback. IDE resolves `auto` from `prefers-color-scheme` and stores user choice in Theia preferences. Custom themes load from `~/.config/arc-studio/themes/*.yaml`.

```yaml
name: graphite-blue
extends: dark
tokens:
  bg.canvas: "#111318"
  bg.surface: "#191d24"
  text.primary: "#e6edf3"
  accent.primary: "#58a6ff"
  state.success: "#56d364"
  state.warning: "#d29922"
  state.danger: "#f85149"
```

---

## 3. Typography

### 3.1 Type Families

| Use | Family | Reason |
|---|---|---|
| UI sans | `Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | Compact labels and good small-size rendering. |
| Display/serif | None | Avoid extra family; product uses graph + mono accent for identity. |
| Monospace | `"JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace` | Ligatures disabled by default, configurable in `/config > Editor`; box drawing reliable; tabular numerals clear. |

CLI recommended terminal font: JetBrains Mono or Berkeley Mono. Required glyphs: `┌ ┐ └ ┘ ─ │ ├ ┤ ┬ ┴ ┼ ▶ ■ ✓ ✗ ↻ → ← ↑ ↓ … • █ ░ ⚿`.

### 3.2 Type Scale

| Token | Family | Weight | Size | Line | Tracking | Colour | Use |
|---|---|---:|---:|---:|---:|---|---|
| `display` | UI sans | 700 | 2rem / 32px | 40px | -0.02em | `text.primary` | Welcome title. |
| `heading.1` | UI sans | 700 | 1.5rem / 24px | 32px | -0.01em | `text.primary` | Panel title. |
| `heading.2` | UI sans | 650 | 1.25rem / 20px | 28px | 0 | `text.primary` | Section title. |
| `heading.3` | UI sans | 600 | 1rem / 16px | 24px | 0 | `text.primary` | Card title. |
| `heading.4` | UI sans | 600 | .875rem / 14px | 20px | 0 | `text.secondary` | Form group. |
| `body` | UI sans | 400 | .875rem / 14px | 22px | 0 | `text.primary` | Main UI text. |
| `body.small` | UI sans | 400 | .8125rem / 13px | 20px | 0 | `text.secondary` | Secondary rows. |
| `caption` | UI sans | 400 | .75rem / 12px | 16px | .01em | `text.muted` | Hints. |
| `code` | Mono | 400 | .8125rem / 13px | 20px | 0 | `text.primary` | Code blocks. |
| `code.small` | Mono | 400 | .75rem / 12px | 18px | 0 | `text.secondary` | Inline JSON, run details, config previews. |
| `mono.status` | Mono | 500 | .75rem / 12px | 16px | 0 | `text.primary` | Status line. |

### 3.3 CLI Type Rules

Prompt prefix: `arc › `. User input uses `text.primary`. Assistant labels are bold. Tool names use mono + `accent.secondary`. Dim text marks timestamps, IDs, and optional hints. Underline only marks OSC 8 links. Box drawing is used for panels, forms, graphs, and diff hunks.

### 3.4 Numerals And Code

Use tabular numerals for token counts, durations, costs, sequence numbers, and timestamps. Code blocks use `bg.sunken`, `border.subtle`, padding `space.3`, optional gutter, and a top-right copy button in IDE. CLI code blocks use Rich syntax highlighting mapped to §2.1 syntax tokens.

---

## 4. Iconography

### 4.1 Icon System

Icon set: Lucide. Stroke width `1.75` in IDE chrome, `2` inside buttons. Default icon size `16px`, large toolbar `20px`, empty states `32px`. Hover changes colour to `accent.primary`; active uses `accent.primary.active`.

| Action | Lucide icon |
|---|---|
| Run | `Play` |
| Stop | `Square` |
| Approve | `CheckCircle` |
| Reject | `XCircle` |
| Apply | `GitPullRequestArrow` |
| Review Diff | `Diff` |
| Configure | `Settings` |
| Switch Runtime | `Workflow` |
| Switch Model | `BrainCircuit` |
| Manage Providers | `KeyRound` |
| Open Graph | `Network` |
| Open Runs | `Activity` |
| Retry | `RotateCcw` |
| Export | `Download` |
| Plan | `ListChecks` |
| Build | `Hammer` |
| Auto | `Sparkles` |

### 4.2 CLI Icon Equivalents

| Action | Unicode | ASCII fallback |
|---|---|---|
| Run | `▶` | `>` |
| Stop | `■` | `x` |
| Approve | `✓` | `OK` |
| Reject | `✗` | `NO` |
| Apply | `→` | `->` |
| Review Diff | `±` | `diff` |
| Configure | `⚙` | `cfg` |
| Runtime | `◆` | `rt` |
| Model | `◉` | `mdl` |
| Providers | `⚿` | `[K]` |
| Graph | `◇` | `graph` |
| Runs | `│` | `runs` |
| Retry | `↻` | `retry` |
| Export | `↓` | `save` |
| Plan | `□` | `plan` |
| Build | `■` | `build` |
| Auto | `●` | `auto` |

### 4.3 Runtime And Provider Badges

Runtime badges are rounded rectangles, height `20px`, radius `space.2`, mono label, fill `bg.surface.raised`, border by capability state.

| Runtime | Glyph | Fill token | UI consequence |
|---|---|---|---|
| SwarmGraph | `SG` | `graph.node.queen` | Default; run enabled. |
| LangGraph | `LG` | `graph.node.worker` | Badge `(coalesced)` on graph. |
| CrewAI | `CR` | `graph.node.tool` | Paid-call warning if run target present. |
| OpenAI Agents | `OA` | `state.info` | Partial badge. |
| AG2 | `A2` | `accent.secondary` | Detection/export only. |
LlamaIndex and LM Arena are not shown in default UI in v0.1. Detection and advanced commands remain available via `arc-studio advanced`.

Provider badges: Anthropic `A`, OpenAI `O`, Google `G`, Azure OpenAI `AZ`, Bedrock `BR`, Vertex `VX`, Ollama `OL`. Key state appears as `keyring`, `env`, `file`, or `unset` chip.

---

## 5. Layout And Spacing

### 5.1 Grid

Base unit: `4px`.

| Token | px | rem |
|---|---:|---:|
| `space.0` | 0 | 0 |
| `space.1` | 4 | .25 |
| `space.2` | 8 | .5 |
| `space.3` | 12 | .75 |
| `space.4` | 16 | 1 |
| `space.5` | 20 | 1.25 |
| `space.6` | 24 | 1.5 |
| `space.7` | 28 | 1.75 |
| `space.8` | 32 | 2 |
| `space.9` | 40 | 2.5 |
| `space.10` | 48 | 3 |
| `space.11` | 64 | 4 |
| `space.12` | 80 | 5 |

Panel gutter: `space.2`. Chat max-width: `880px`. Breakpoints: narrow `<720px`, medium `720-1199px`, wide `>=1200px`. Below `720px`, panels become stacked tabs.

### 5.2 Density Modes

| Mode | Panel padding | Row height | Button height | Font adjustment |
|---|---:|---:|---:|---|
| compact | `space.2` | 28px | 28px | `body.small` |
| comfortable | `space.4` | 36px | 36px | `body` |
| spacious | `space.6` | 44px | 44px | `body` + 1px line gap |

### 5.3 Elevation

| Level | Dark | Light | Use |
|---|---|---|---|
| `elevation.0` | no shadow, `border.subtle` | no shadow, `border.subtle` | Base panels. |
| `elevation.1` | `0 1px 2px #0008` | `0 1px 2px #0002` | Cards. |
| `elevation.2` | `0 8px 24px #000a` | `0 8px 24px #0002` | Modals/sheets. |
| `elevation.3` | `0 16px 48px #000c` | `0 16px 48px #0003` | Command palette, autocomplete. |

---

## 6. Motion

### 6.1 Timing Tokens

| Token | Duration | Easing | Use |
|---|---:|---|---|
| `motion.duration.instant` | 0ms | linear | Disabled/reduced motion. |
| `motion.duration.fast` | 120ms | cubic-bezier(.2,0,.2,1) | Button press, chip toggle. |
| `motion.duration.default` | 180ms | cubic-bezier(.2,0,0,1) | Panel open, toast enter. |
| `motion.duration.slow` | 320ms | cubic-bezier(.2,0,0,1) | Graph fit, panel resize. |

### 6.2 Specific Animations

| Animation | Spec |
|---|---|
| Running node pulse | Border `graph.node.state.running`, 1.2s period, opacity .55→1, scale 1→1.035. |
| Edge activation | Colour-fill from source to target over 420ms; no particles. |
| Streaming tokens | Cursor `▌`, blink 530ms; append text without layout animation. |
| Reserved replay scrubber | Not in v0.1; reserved for v0.3 audit explorer. |
| HITL prompt entry | Slides from transcript right edge 12px and fades in over `default`. |
| Mode switch | Chip thumb moves over `fast`; live region announces new mode. |

### 6.3 Reduced Motion

If `prefers-reduced-motion` or CLI `ARC_REDUCED_MOTION=1`, all transitions use `instant`; running state uses static `● running`; live edge updates use colour change only; skeleton shimmer becomes static blocks.

---

## 7. CLI Full Screen Layouts

All CLI screens target 100 columns × 30 rows and remain usable at 80 columns. Below 80 columns, panels become single-column lists, graph switches to tree view, and status line truncates middle segments.

### 7.1 First-Run Welcome

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ARC Studio                                          Run agents. See everything.                   │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Workspace  /Users/me/project                                                                    │
│ Runtime    SG SwarmGraph  ✓ bundled, ready                                                       │
│ Daemon     ○ not running  → will start on first run                                               │
│ Provider   ✗ no key set  → use /providers                                                        │
│ Mode       [Build]  Tab cycles Plan / Build / Auto                                                │
│                                                                                                  │
│ Start with one of these:                                                                         │
│   /providers   add or inspect provider keys                                                       │
│   /config      edit runtime, model, graph, trust                                                  │
│   /workflows   scan this workspace                                                               │
│                                                                                                  │
│ Or ask a question:                                                                               │
│   “What workflows are in this repo?”                                                             │
│                                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ arc ›                                                                                            │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ SG SwarmGraph ✓ | model unset | Build | daemon off | keys unset | /help                          │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Regions: header, readiness table, action hints, input, status line. Keys: `Tab`, `/`, `Enter`, `Ctrl+C`. Tokens: `bg.canvas`, `text.primary`, `state.success`, `state.warning`, `state.danger`. 80-col: hide tagline and collapse hints to one line.

80-column rendering:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ARC Studio                                                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Workspace /Users/me/project                                                  │
│ Runtime   SG SwarmGraph ✓ bundled                                            │
│ Provider  ✗ no key set → /providers                                          │
│ Start: /providers  /config  /workflows                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ arc ›                                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ SG ✓ | model unset | Build | daemon off | /help                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Below 80 columns: remove border, render readiness table as plain list, keep input and status as two lines.

### 7.2 Steady-State Chat

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ARC Studio Chat                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ you                                                                                              │
│   Run the reviewer workflow and check provider cost first.                                       │
│                                                                                                  │
│ agent                                                                                            │
│   I found workflow `reviewer`. I need two tool calls before execution.                            │
│                                                                                                  │
│   ┌ tool: scan_workspace ─────────────────────────────────────────────────────────────────────┐  │
│   │ ✓ found 1 SwarmGraph workflow, 5 nodes, 6 edges                                           │  │
│   └───────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                  │
│   ┌ paid call required ───────────────────────────────────────────────────────────────────────┐  │
│   │ Provider: Anthropic | Model: claude-sonnet | Ceiling: $0.08                               │  │
│   │ Policy requires approval before network calls.                                             │  │
│   │ [Approve]  [Reject]  [Change model]                                                       │  │
│   └───────────────────────────────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ arc › /approve                                                                                   │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ SG ✓ | claude-sonnet | Build | run idle | cost pending $0.08 | /stop /runs /diff                 │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

80-col: tool cards drop right padding; paid call buttons wrap vertically.

Region map: transcript uses rows 3-22, input rows 24-26, status rows 28-29. Tool call cards use `bg.sunken`; paid-call card uses `state.warning.bg`; action labels use `accent.primary`. Keybindings: `Enter` submit, `Ctrl+J` newline, `Ctrl+C` stop stream, `/approve` approve paid call, `/reject` reject paid call.

Chat input supports `@file` and `@folder` mentions in v0.1. Typing `@` opens fuzzy autocomplete for workspace paths. Mention chips show path, type, and approximate token count before send. `@file` injects file content with a 16K token cap; `@folder` injects a tree plus selected contents with a 32K token cap. Exceeding the budget shows a warning and truncates with visible ellipsis. `@symbol`, `@url`, and image attachments are reserved.

Messages typed during an active run are queued FIFO. Status line shows `(N queued)`. Max depth is 5; warn at 3; block at 5. `/stop` executes immediately and asks whether to clear queued messages. Natural messages default to `ask`; explicit run phrases (`run`, `execute`, `start`) or `/run` produce `run` intent. Plan forces `ask`; Build asks before `run`; Auto follows policy.

### 7.3 `/config` Form

```text
┌──────────────────────────────────────── /config ────────────────────────────────────────────────┐
│ Runtime        (●) SwarmGraph bundled   (○) LangGraph   (○) CrewAI   (○) OpenAI Agents          │
│ Model          [ claude-sonnet-4-5                                      ▾ ]                     │
│ Providers      Anthropic: unset   OpenAI: env   Ollama: local                                    │
│ Mode           [ Plan ] [ Build ● ] [ Auto ]                                                     │
│ Workspace      ✓ trusted: /Users/me/project                                                      │
│ Graph          layout: dagre   live overlay: on   minimap: off                                   │
│ Theme          auto   Density: comfortable                                                       │
│                                                                                                  │
│ [Save]  [Cancel]  [Reset project config]                                                         │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Keys: arrows move, Space toggles, Enter saves focused action, Esc cancels. 80-col: provider row becomes vertical list.

Colour tokens: selected radio uses `accent.primary`; trusted workspace uses `state.success`; unset provider uses `state.warning`; destructive reset uses `state.danger` only on hover confirmation. Placeholder strings: model select `Select default model`; runtime help `Runtime applies to the next run unless saved`.

### 7.4 `/providers` Form

```text
┌────────────────────────────────────── /providers ───────────────────────────────────────────────┐
│ Provider        State       Source       Default model             Action                        │
│ Anthropic       ✓ set       keyring      claude-sonnet-4-5        [edit] [remove]                │
│ OpenAI          ✓ set       env          gpt-4o                    [view]                         │
│ Google          ✗ unset     -            gemini-pro                [add]                          │
│ Azure OpenAI    ✗ unset     -            deployment-name           [add]                          │
│ Bedrock         ✗ unset     -            claude-via-bedrock        [add]                          │
│ Ollama          ○ local     localhost    llama3.1                  [test]                         │
│                                                                                                  │
│ Adding Google key                                                                                │
│ Key name: GOOGLE_API_KEY                                                                         │
│ Value:    ************▌                                                                          │
│ Store:    (●) OS keyring  (○) env hint only                                                      │
│                                                                                                  │
│ [Save key] [Cancel]                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

80-column degradation: hide `Default model` column; show selected provider details below table. Keybindings: `A` add key, `R` remove focused key, `T` test provider, `Esc` cancel entry. Secret input never echoes raw characters; pasted value is masked immediately. Raw value is never present in the accessible name; screen readers announce `{N} characters entered`, not the secret.

### 7.5 `/runtime` Picker

```text
┌────────────────────────────────────── /runtime ─────────────────────────────────────────────────┐
│ ● SG SwarmGraph       default, ready, bundled                                                    │
│ ○ LG LangGraph        requires: ARC_LANGGRAPH_EXPORT                                             │
│ ○ CR CrewAI           not installed                                                              │
│ ○ OA OpenAI Agents    partial: SDK/export target required                                        │
│ ○ A2 AG2              detection/export only                                                      │
│                                                                                                  │
│ Enter selects runtime for this session. S saves to .arc/config.yaml.                              │
│ Other runtimes (LlamaIndex, LM Arena) via: arc-studio advanced runtimes list --all                │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Tokens: ready uses `state.success`; missing requirement uses `state.warning`; no run path uses `text.muted`; selected row uses `bg.surface.raised`. 80-column degradation: descriptions wrap on a second indented line.

### 7.6 `/graph` Inline View

```text
┌──────────────────────────────────────── /graph ─────────────────────────────────────────────────┐
│ Workflow: reviewer | Runtime: SG SwarmGraph | Layout: tree                                      │
│                                                                                                  │
│   [start]                                                                                        │
│      │                                                                                            │
│      ▼                                                                                            │
│   ┌──────────┐        ┌────────────┐                                                             │
│   │ queen ●  │ ─────▶ │ search tool│                                                             │
│   └────┬─────┘        └────────────┘                                                             │
│        │                                                                                         │
│        ├────────────▶ [researcher] ─────▶ [writer] ─────▶ [reviewer]                             │
│        │                                      ▲              │                                    │
│        └──────────────────────────────────────┘              ▼                                    │
│                                                            [end]                                  │
│                                                                                                  │
│ Legend: ● running  ✓ done  ! waiting  ✗ failed                                                   │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Colour overlay: queen `graph.node.queen`; worker/agent `graph.node.worker`; tool `graph.node.tool`; terminal `graph.node.terminal`; running state adds `state.running` glyph `●`. 80-column degradation: graph remains but labels truncate to 10 chars. Below 80 columns: tree fallback:

```text
start
└─ queen ●
   ├─ search tool
   └─ researcher → writer → reviewer → end
```

### 7.7 `/graph` Second-Terminal View (reserved v0.2)

Second terminal opens `arc-studio graph --attach <run-id>`. It uses alt-screen mode. Bottom status: `i inspector | f fit | +/- zoom | space pause | q close`. Resize triggers layout recompute; current node remains selected. This is reserved for v0.2; v0.1 ships only inline CLI graph plus IDE graph.

```text
┌───────────────────────────────────── ARC Graph: reviewer ───────────────────────────────────────┐
│                                                                                                  │
│        ┌────────┐                                                                                │
│        │ start  │                                                                                │
│        └───┬────┘                                                                                │
│            ▼                                                                                     │
│        ┌────────┐        ┌────────────┐                                                         │
│        │ queen ●│───────▶│ search     │                                                         │
│        └───┬────┘        └────────────┘                                                         │
│            ▼                                                                                     │
│      ┌──────────┐     ┌────────┐     ┌──────────┐                                                │
│      │researcher│────▶│ writer │────▶│ reviewer │                                                │
│      └──────────┘     └────────┘     └────┬─────┘                                                │
│                                            ▼                                                      │
│                                         ┌─────┐                                                   │
│                                         │ end │                                                   │
│                                         └─────┘                                                   │
│                                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ i inspector | f fit | +/- zoom | space pause | q close | node: queen running                     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.8 `/diff` Review

```text
┌──────────────────────────────────────── /diff ──────────────────────────────────────────────────┐
│ File 1/2: python/src/workflow.py                         Hunk 1 ✓ approved                       │
│   12  def run():                                                                                 │
│ - 13      return old_flow()                                                                       │
│ + 13      return swarm_flow()                                                                     │
│                                                                                                  │
│ File 2/2: README.md                                      Hunk 2 ! pending                        │
│   41  Start ARC Studio:                                                                            │
│ - 42      arc run                                                                                 │
│ + 42      arc-studio                                                                              │
│                                                                                                  │
│ [Approve hunk] [Reject hunk] [Edit first] | [Approve all] [Reject all] | [Apply approved] [Cancel] │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Region map: file list rows 2-4 if `>2` files; hunk body rows 5-23; action bar row 25; git status row 26; status row 28. 80-column fallback: actions wrap to two rows; line numbers shrink from 4 chars to 3 chars; long paths middle-elide.

Apply/rollback is git-backed. `Apply approved` creates one commit: `[ARC Studio] Applied changes from run {run_id}`. `/undo` reverts the most recent ARC Studio commit with `git revert --no-edit`; `/redo` reverts that revert. Non-git workspaces show `Workspace is not a git repository. Undo will not be available.` with actions `[git init] [Continue without undo] [Cancel]`. One apply batch is the undo unit.

Hunk states: `pending`, `approved`, `rejected`, `applied`, `conflict`, `edited`. Before apply, ARC performs a dry-run patch. Failed hunks show `⚠ conflict - file modified` with actions `[Open for manual merge] [Skip] [Apply remaining]`. File mtimes are recorded when diff is generated; changed files show a non-blocking concurrent edit warning. Review decisions persist across panel close/reopen for 24 hours.

### 7.9 `/status`

```text
Project        /Users/me/project
Runtime        SG SwarmGraph ✓ bundled, default
Model          claude-sonnet-4-5 via Anthropic
Daemon         ● 127.0.0.1:7777 responding
Keys           Anthropic ✓ keyring | OpenAI ✓ env | Google ✗ unset
Last run       run_01H... completed in 48.2s
Session cost   total $0.04 | last paid call $0.04 | active ceiling none
Mode           [Build]
Trust          ✓ workspace trusted
```

80-column fallback: one key per line. Tokens: daemon up `state.success`, unset key `state.warning`, mode chip uses `accent.primary`, trusted workspace `state.success`.

### 7.10 `/doctor`

```text
✓ Python package import
✓ Daemon reachable at 127.0.0.1:7777
✓ SwarmGraph bundled runtime
! LangGraph export target missing
  Fix: set ARC_LANGGRAPH_EXPORT or disable LangGraph in /config.
! Anthropic key unset
  Fix: run /providers and add Anthropic key.
✗ Docker isolation unavailable
  Fix: install Docker/OrbStack or use subprocess isolation.
```

Successful run exit code `0` if warnings are non-blocking. Exit code `2` when a required runtime or daemon dependency is unavailable. `--json` returns `checks[]` with `id`, `status`, `message`, `fix`.

### 7.11 `/runs` Summary

```text
┌──────────────────────────────────────── /runs ──────────────────────────────────────────────────┐
│ Run ID        Runtime       Status       Cost      Duration     Summary                         │
│ run_01H...    SwarmGraph    ✓ complete   $0.04     48.2s        reviewer completed              │
│ run_01G...    SwarmGraph    ✗ failed     $0.00     12.4s        failed at node reviewer          │
│                                                                                                  │
│ [Open summary] [Open advanced trace in editor] [Delete]                                          │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

No event timeline, event JSON detail, replay scrubber, or `/trace` command ships in default v0.1. Advanced fallback: `arc-studio advanced runs trace <run-id>`.

### 7.12 Error States

| Error | Exact text | Recovery |
|---|---|---|
| Daemon unreachable | `Daemon unreachable at 127.0.0.1:7777.` | `Run arc-studio doctor or restart with arc-studio serve.` |
| Model unauthorised | `Model unauthorised: provider rejected claude-sonnet-4-5.` | `Open /providers and choose a model your account can use.` |
| Paid call denied | `Paid call blocked by approvals policy.` | `Switch to Plan mode, approve this call, or change policy in /config.` |
| Runtime missing req | `LangGraph cannot run: ARC_LANGGRAPH_EXPORT is not set.` | `Set it in /config > Runtime or switch to SwarmGraph.` |

Each CLI error screen uses the same structure: title row, cause, fix, next action, command suggestion. IDE equivalents use a toast plus an inline panel banner. Danger copy never offers `--force` unless the command is explicitly safe.

### 7.13 Plan / Build / Auto Chip

Status line shows `[Plan]`, `[Build]`, or `[Auto]`. `Tab` cycles `Plan → Build → Auto → Plan`. Plan disables writes and paid calls; Build asks for destructive approvals; Auto uses policy rules.

#### 7.13.1 `/auto` Policy

`/auto` does not approve everything. It follows this policy without repeatedly asking:

```yaml
approvals:
  paid_calls: ask
  destructive_writes: ask
  trust_changes: deny
  shell_exec: deny
  phase_advance: ask
```

Allowed values: `ask`, `auto`, `deny`. v0.1 default keeps `trust_changes` and `shell_exec` denied even in Auto. `phase_advance` is reserved for v0.2 planner integration.

Approval policy lives outside cosmetic config.

| Scope | Path |
|---|---|
| Project | `.arc/policy.yaml` |
| User | `~/.config/arc-studio/policy.yaml` |

Policy precedence: project policy > user policy > built-in safe defaults. Project policy cannot weaken user policy for `shell_exec` or `trust_changes`; user policy can impose stricter limits.

### 7.14 Status Line

Segments: workspace, session id, runtime, model, mode, daemon, run state, key state, cost, help. Separator: ` | `. Cost segment format: `cost $X.XX`; `text.secondary` at `<= $1`, `state.warning` at `> $5`, `state.danger` at `> $20`, `cost ?` when unknown. Truncation order: workspace path middle-elides first, model second, key state third, session id fourth. OSC 8 clickable segments: workspace path, run ID, `/status` cost detail, docs URL.

### 7.14.1 Session Lifecycle Contract

`session_id` uses ULID: 26 characters, lexicographically sortable, time-ordered, separate from `run_id`. CLI and IDE read/write the same session layout.

| Platform | Session root |
|---|---|
| Linux | `~/.local/share/arc-studio/sessions/<session_id>/` |
| macOS | `~/Library/Application Support/arc-studio/sessions/<session_id>/` |
| Windows | `%LOCALAPPDATA%\arc-studio\sessions\<session_id>\` |

Per-session files: `metadata.yaml`, `transcript.jsonl`, `runs.jsonl`, future `audit.log`. Every assistant turn is journaled to `transcript.jsonl` before rendering. If a journal has incomplete/unrendered turns, next launch offers automatic `/resume`. CLI and IDE attach to the same workspace session by default. If two clients attach, both surfaces show `{N} clients attached`. Concurrent writes are serialized by daemon session lock. `/new` creates a new explicit session.

### 7.14.2 Daemon Lifecycle Contract

| State | CLI startup | IDE startup | `/status` | `/doctor` | Recovery |
|---|---|---|---|---|---|
| `not-installed` | error before chat | setup banner | unavailable | fail | install package / run bootstrap |
| `stopped` | auto-start allowed | auto-start allowed | stopped | warning | start daemon |
| `starting` | progress row | loading badge | starting | pending | wait/retry |
| `running` | normal | normal | running + version | pass | none |
| `stale` | prompt before replace | prompt before replace | stale pid | warning | confirm replace |
| `port-conflict` | do not kill process | do not kill process | conflict | fail | choose port or stop other process |
| `unreachable` | chat read-only | disconnected banner | unreachable | fail | restart daemon |
| `version-mismatch` | show client/daemon versions | show banner | mismatch | fail | upgrade matching package |

`arc-studio` may auto-start daemon only from `stopped`. It must not kill another process on `port-conflict`. It must prompt before replacing stale daemon. Version mismatch reports exact client and daemon versions.

### 7.15 `/tasks` Phased Plan View (reserved v0.2)

```text
┌──────────────────────────────────────── /tasks ─────────────────────────────────────────────────┐
│ Plan ready: 3 phases, estimated $0.02-$0.18                                                     │
│                                                                                                  │
│ ▶ Phase 1  SG SwarmGraph   Build backend workflow       ceiling $0.02   planned                 │
│   Phase 2  HL HotLoop      Iterate React UI             ceiling $0.12   reserved v0.2            │
│   Phase 3  SG SwarmGraph   Validate agent handoff       ceiling $0.04   planned                 │
│                                                                                                  │
│ Handoff after phase 1: goal_for_next_phase, state, constraints, references, prior_audit_links     │
│                                                                                                  │
│ [Approve plan] [Edit phase] [Re-plan] [Cancel]                                                   │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Keys: arrows navigate phases, Enter expands, `e` edits phase, `a` approves plan, `r` replans. 80-column version removes handoff field list and shows `handoff doc available`.

### 7.16 Router Suggestion Card (reserved v0.2)

```text
┌ router suggestion ──────────────────────────────────────────────────────────────────────────────┐
│ This looks like UI work. HotLoop iterates faster here. Switch? [y/n/always for this project]     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

After accept:

```text
✓ Runtime switched for next phase: HotLoop
handoff emitted: swarmgraph → hotloop | state keys: files, constraints, prior_audit_links
```

Router modes: `manual`, `suggest`, `auto-on-confirm`, `auto`. Default v0.2 mode: `suggest`. v0.1 reserves copy and event shape only.

### 7.17 Handoff Transition (reserved v0.2)

```text
┌ phase boundary ─────────────────────────────────────────────────────────────────────────────────┐
│ Phase 1 done: SwarmGraph built backend workflow.                                                │
│ Next: Phase 2 on HotLoop, goal: iterate React UI against live screenshots.                       │
│ Carrying: changed files, constraints, references, prior audit links.                             │
│                                                                                                  │
│ [Continue] [Edit handoff] [Cancel]                                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Default behaviour pauses at phase boundary. `planner.auto_advance=true` makes this non-modal but still visible.

### 7.18 First-Untrusted-Workspace Flow

```text
┌ workspace trust ────────────────────────────────────────────────────────────────────────────────┐
│ This workspace is untrusted. ARC Studio can read files but cannot write, run, or call paid       │
│ providers.                                                                                       │
│                                                                                                  │
│ [Trust this workspace] [Stay untrusted] [Learn more]                                             │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Chat input is disabled until the user chooses an option. Trust requires explicit Enter/click on the focused button; no shortcut bypass.

Trust binds to canonical path + machine ID + user ID. Symlinked paths resolve before trust check. Moving or cloning a workspace requires a new trust decision. Trust can be revoked from `/config > Workspace Trust`. Untrusted mode allows read-only chat/context but blocks writes, shell execution, paid calls, and runtime execution.

---

## 8. IDE Full Screen Layouts

### 8.1 Default Workspace

```text
┌ Activity 48 ┬──────────────── Chat 60% ────────────────┬─ Tasks collapsed┐
│ ARC         │ transcript                                │ ▸ Plan          │
│ Graph       │ messages, HITL cards, tool calls          │                 │
│ Runs        │                                           │                 │
│ Config      │ input + slash hints + send button         │                 │
├─────────────┴───────────────────────────────────────────┴─────────────────┤
│ Status: trust ✓ | SG ✓ | Build | daemon ● | cost $0.00                    │
└────────────────────────────────────────────────────────────────────────────┘
```

States: empty shows “Ask a question, scan workspace, or open sample”; loading shows labelled skeletons; populated shows transcript; error shows retry banner.

Keyboard shortcuts: `Ctrl/Cmd+;` focus chat input, `Ctrl/Cmd+Enter` send, `Ctrl/Cmd+Shift+H` open Graph, `Ctrl/Cmd+Shift+U` open Runs, `Ctrl/Cmd+,` open Config, `Esc` close transient UI. Components: `ChatPanel`, `TasksPanel`, `StatusBar`, `ModeToggle`, `RuntimeSelector`, `ModelSelector`, `ToastContainer`.

### 8.2 Tasks Panel Views

The Tasks panel replaces the previous planning sidebar. `/plan` remains the read-only mode command; `/tasks` opens this panel.

| View | v0.1 status | Default when | Content |
|---|---|---|---|
| Step view | Ships | SwarmGraph active phase | Runtime step list, blockers, current node, in-phase subtasks. |
| Phase view | Reserved v0.2 | Planner emits multi-phase plan | Phase cards, runtime badges, cost ceilings, handoff document links. |
| Loop trace view | Reserved v0.2 | HotLoop active phase | Observation loop ticks, target/device state, frame references. |

User can toggle view when more than one view exists. Runtime chooses default view. Phase and Loop trace views render reservation empty states in v0.1.

### 8.3 Graph-Active Workspace

Graph opens in the main editor area during active runs or when the user selects `/graph`. ARC panels remain in Theia's right sidebar; avoid replacing Theia's editor with a custom three-column layout.

State table: empty graph shows `No graph for this runtime`; loading shows `Extracting workflow graph...`; populated shows React Flow canvas; error shows `Graph render failed` with retry. Components: `GraphCanvas` (`@xyflow/react`), `GraphToolbar`, `NodeInspector`, `MiniMap`.

### 8.4 Review Flow

Review/Apply opens as a sidebar panel plus Theia diff editor in the main area. Left/sidebar column lists files/hunks; main area uses Theia's Monaco diff editor. Footer actions: Apply Approved, Approve All, Reject All, Edit First, Close.

Keyboard: `J/K` next/previous hunk, `A` approve, `R` reject, `E` edit-first, `Ctrl/Cmd+Enter` apply approved, `Esc` close if no pending destructive confirmation. Error state preserves hunk decisions and shows retry. Inline Cursor/Windsurf-style editor diffs are reserved for v0.2.

### 8.5 Runs

Runs panel shows run list and per-run summary only. It does not show event timeline, event JSON, trace replay, or replay scrubber in v0.1. Columns: Run ID, Runtime, Status, Cost, Duration, Failure node, Summary. Filters: status chips (`All`, `Running`, `Completed`, `Failed`, `Cancelled`), runtime, and date range (`Today`, `7d`, `30d`, `All`). Rows can expand inline to show `RunSummary`, `FailureCard`, and redacted failure context. Failure rows include `Open advanced trace in editor`, which runs or displays `arc-studio advanced runs trace <run-id>`.

State table: empty `No stored runs`; loading `Loading runs...`; populated run table; error `Runs could not be loaded`; offline `Local daemon unavailable; showing cached summaries if available`. Components: `RunList`, `RunSummaryCard`, `CostCeilingBadge`.

### 8.6 Config

Full-panel Config tabs: Runtime, Model, Providers, Workspace Trust, Profiles, Graph, Advanced. Save writes `.arc/config.yaml`; user-wide changes write `~/.config/arc-studio/config.yaml`.

Dirty state: Save button enabled and status bar segment shows `config unsaved`. Validation errors appear inline and block save. Provider key fields route to keyring and never write raw keys to YAML.

Config precedence:

| Priority | Source |
|---:|---|
| 1 | CLI flags |
| 2 | Environment variables |
| 3 | Project `.arc/config.yaml` |
| 4 | User `~/.config/arc-studio/config.yaml` |
| 5 | Built-in defaults |

Policy precedence is separate: project `.arc/policy.yaml` > user `~/.config/arc-studio/policy.yaml` > built-in safe defaults. Policy is separate because it is security-relevant and should be reviewable independently of cosmetic config.

### 8.7 Empty Workspace

Message: `No workflows detected yet.` CTAs: `Ask a question`, `Scan workspace`, `Open sample SwarmGraph project`.

No detected workflow is not an error. Chat stays enabled. Scan action runs `detectWorkflows()` and updates Workflows/Graph panels.

### 8.8 Single-Sidebar Collapse

ARC uses Theia's right sidebar tabs: Chat, Runs, Config, plus Review when changes exist. Graph opens in the main editor area. Tasks Step cards appear inline in Chat for v0.1; dedicated Tasks Phase/Loop panel is reserved for v0.2. Default sidebar width 420px, min 320px, max 55vw.

When collapsed, panel headers show icon-only tabs plus tooltip. Chat input remains sticky. Graph canvas disables minimap below 360px width.

### 8.9 Mobile / Narrow Window

Below 720px: one panel visible at a time, bottom tab bar, graph switches to vertical tree layout, diff opens full screen.

Below 480px: model/runtime selectors collapse into `Status` sheet. Minimum touch target 44px. Hover states map to active/focus states.

### 8.10 Router Suggestion Overlay (reserved v0.2)

Non-modal inline card at the top of Chat. Copy: `This looks like UI work. HotLoop iterates faster here. Switch?` Actions: `Yes`, `No`, `Always for this project`. It is dismissible without focus theft and announced via polite live region.

### 8.11 Phase Transition Flow (reserved v0.2)

Modal sheet by default at phase boundary. Fields: previous runtime result, next runtime, goal, state keys carried over, constraints, references, prior audit links. Actions: Continue, Edit handoff, Cancel. If `planner.auto_advance=true`, render as non-modal Chat card instead.

### 8.12 Panel Reservations For HotLoop (v0.2)

| Panel | Reservation |
|---|---|
| Device | Live screenshots per target (Flutter/React/Expo). Opens by default when HotLoop runtime is active. |
| Frames | Scrubbable visual diff timeline. Opens beside Device when HotLoop runtime is active. |

When HotLoop is active, Graph defaults closed and Device + Frames default open. No v0.1 mockups are required; final specification lands in the HotLoop v0.2 design.

### 8.13 Keyboard Shortcut Audit

| Shortcut | Action | Theia/VS Code conflict | v0.1 default |
|---|---|---|---|
| `Ctrl/Cmd+L` | Focus chat input | VS Code clear terminal | Remap to `Ctrl/Cmd+;` |
| `Ctrl/Cmd+Enter` | Send message | Safe | Keep |
| `Ctrl/Cmd+Shift+G` | Open Graph | Source control | Remap to `Ctrl/Cmd+Shift+H` |
| `Ctrl/Cmd+Shift+R` | Open Runs | Rename symbol | Remap to `Ctrl/Cmd+Shift+U` |
| `Ctrl/Cmd+Shift+T` | Open Tasks | Reopen closed tab | Use command palette by default |
| `Ctrl/Cmd+,` | Open Config | Settings | Acceptable when ARC panel focused |
| `Esc` | Close transient UI | Safe | Keep |

Settings → Keyboard exposes all ARC shortcuts. ARC overrides apply only when an ARC panel has focus; otherwise Theia defaults win.

### Panel Specs

| Panel | Header | Body | Footer | Events consumed |
|---|---|---|---|---|
| Chat | title, mode toggle, runtime/model selectors | transcript, tool cards, HITL cards, inline Task step cards, router suggestions | multiline input, slash hints, mention chips, queue indicator | `MESSAGE`, `TOOL_CALL_*`, `HITL_PROMPT`, `RUN_*`, `handoff` |
| Tasks | reserved v0.2 | Phase/Loop views reserved; Step cards live in Chat in v0.1 | reserved | `plan.update`, `STEP_*`, reserved `handoff` |
| Graph | title, layout select, fit/export | React Flow canvas, minimap, inspector | fit/zoom/inspector controls | `NODE_*`, `HANDOFF`, `STATE_SNAPSHOT` |
| Runs | filters, refresh | run list, summary, cost, failure node | export/delete/open advanced trace | `RUN_*` |
| Review/Apply | changed files, counts | diff hunks, Monaco diff | apply/reject/edit | diff proposal events |
| Config | tabs, reset | forms | save/cancel | config service |

Interactive states: default uses `bg.surface`; hover `bg.surface.raised`; focus-visible `border.strong`; active `accent.primary.active`; disabled `text.muted` with no pointer events.

---

## 9. Component Library

All components use tokens from §2, spacing from §5, type from §3, icons from §4, and motion from §6. Every interactive component implements the following state contract unless overridden:

| State | Required treatment |
|---|---|
| default | Base token background, visible border if clickable area is not otherwise obvious. |
| hover | `bg.surface.raised`; icon/text moves to `accent.primary` only for action affordances. |
| focus-visible | 2px outline using `border.strong`, offset 2px, never removed. |
| active | Background uses `accent.primary.active` for primary actions or `bg.sunken` for neutral controls. |
| disabled | `text.muted`, opacity .55, no pointer events, still readable. |

Keyboard order follows DOM order. Modal and sheet components trap focus. Roving tabindex is required for tabs, segmented toggles, listboxes, command palette rows, graph node keyboard navigation, and diff hunk lists.

### Button

Variants: primary, secondary, ghost, danger, icon-only. Sizes: sm 28px, md 36px, lg 44px. States: default `bg.surface`, hover `bg.surface.raised`, focus `border.strong`, active `accent.primary.active`, disabled `text.muted`.

```ts
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost' | 'danger' | 'icon';
  size: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  icon?: LucideIcon;
  iconPosition?: 'start' | 'end';
  children?: React.ReactNode;
  ariaLabel?: string;
  onPress?: () => void;
}
```

ARIA: native `button`; icon-only requires `aria-label`; loading sets `aria-busy=true` and preserves width.

### Chip

Variants: status, mode, badge, removable. Height 20px, radius `space.2`, padding `space.1 space.2`. ARIA label includes status.

```ts
interface ChipProps {
  variant: 'status' | 'mode' | 'badge' | 'removable';
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'running';
  label: string;
  icon?: LucideIcon;
  selected?: boolean;
  onRemove?: () => void;
}
```

ARIA: decorative chips are `span`; status chips use `role=status`; removable chips expose a nested button labelled `Remove {label}`.

### Input

Single-line height 36px; multiline min 40px max 200px. Autocomplete popup uses `elevation.3`. Role `combobox` when slash suggestions open.

```ts
interface InputProps {
  value: string;
  placeholder?: string;
  multiline?: boolean;
  autocomplete?: CommandSuggestion[];
  mentions?: Mention[];
  attachments?: Attachment[];
  queueDepth?: number;
  disabled?: boolean;
  error?: string;
  prefixIcon?: LucideIcon;
  suffix?: React.ReactNode;
  onChange: (value: string) => void;
  onSubmit?: () => void;
}

interface Mention {
  type: 'file' | 'folder';
  path: string;
  tokenCount?: number;
}

interface Attachment {
  type: 'image';
  name: string;
  dataRef: string;
}
```

Placeholders: Chat input uses `Ask ARC Studio or @mention files...`; command input uses `Type / for commands`; provider key input uses `Paste key; it will not be logged`. `attachments` is reserved for v0.2 image input.

### Select / Combobox

Used for runtime, model, provider. Supports keyboard arrows, typeahead, `aria-expanded`, `aria-activedescendant`.

```ts
interface ComboboxProps<T> {
  value: T | null;
  options: T[];
  getLabel: (option: T) => string;
  getDescription?: (option: T) => string;
  getDisabled?: (option: T) => boolean;
  onChange: (option: T) => void;
  placeholder?: string;
}
```

Disabled runtime options must include the missing requirement text. Example: `LangGraph - requires ARC_LANGGRAPH_EXPORT`.

### Toggle

Plan/Build/Auto cycler. One active segment. `Tab` in CLI, button in IDE. Live region announces mode.

```ts
interface ModeToggleProps {
  value: 'plan' | 'build' | 'auto';
  onChange: (value: 'plan' | 'build' | 'auto') => void;
  disabledModes?: Array<'plan' | 'build' | 'auto'>;
}
```

Mode copy: Plan `Read-only. No writes or paid calls.` Build `Can propose changes. Asks before applying.` Auto `Follows approval policy.`

### Tabs

Panel tabs and Config tabs. Roving tabindex. Arrow keys switch focus; Enter activates.

```ts
interface TabsProps {
  tabs: Array<{ id: string; label: string; icon?: LucideIcon; disabled?: boolean; badge?: string }>;
  activeId: string;
  onChange: (id: string) => void;
  orientation?: 'horizontal' | 'vertical';
}
```

### Card

Workflow, run, HITL, paid-call. Padding `space.4`, border `border.default`, radius `space.2`, elevation `elevation.1`.

```ts
interface CardProps {
  variant: 'workflow' | 'run' | 'hitl' | 'paid-call' | 'message' | 'empty' | 'image';
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info';
  title?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  diffPreview?: {
    files: Array<{ path: string; addedLines: number; removedLines: number }>;
    sampleLines?: string[];
    onReviewFull: () => void;
  };
}
```

Paid-call cards always display provider, model, estimated ceiling, and approval buttons.

### RunContractCard

Pre-run and post-run contract surface. v0.1 ships minimal pre-run card; post-run fulfillment is reserved but schema-stable.

```ts
interface RunContract {
  contractId: string;
  runId?: string;
  sessionId: string;
  objective: string;
  runtime: string;
  mode: 'plan' | 'build' | 'auto';
  allowedTools: string[];
  writeScope: string[];
  costCeilingUsd: number | 'unknown';
  approvalPolicy: string;
  rollbackPlan: 'git-revert' | 'manual' | 'none';
  evidenceExpected: Array<'file_diff' | 'test_output' | 'tool_output' | 'graph_node' | 'receipt'>;
  status: 'proposed' | 'accepted' | 'fulfilled' | 'violated';
}

interface RunContractCardProps {
  contract: RunContract;
  onAccept?: () => void;
  onEdit?: () => void;
  onCancel?: () => void;
}
```

Copy: `Run contract: {objective}. Runtime {runtime}; rollback {rollbackPlan}; cost ceiling {costCeilingUsd}.`

### EvidenceChip

Small citation surface attached to chat messages, failures, graph nodes, receipts, and ledger rows.

```ts
interface EvidenceRef {
  evidenceId: string;
  kind: 'file' | 'tool_output' | 'run' | 'node' | 'ledger' | 'receipt' | 'frame_receipt';
  target: string;
  range?: [number, number];
  redacted?: boolean;
}

interface EvidenceChipProps {
  ref: EvidenceRef;
  onOpen: (ref: EvidenceRef) => void;
}
```

Invalid evidence refs are stripped server-side before rendering. v0.1 renders `file` and `tool_output`; unsupported-claim downgrading is reserved for v0.2.

### RunReceipt

Signed local artifact generated for completed and failed runs. This is not Trace UI; it is the human/export surface.

```ts
interface RunReceipt {
  receiptVersion: 1;
  receiptId: string;
  sessionId: string;
  runId: string;
  contractId?: string;
  status: 'completed' | 'failed' | 'cancelled';
  summary: string;
  costUsd?: number | 'unknown';
  filesChanged: Array<{ path: string; added?: number; removed?: number }>;
  approvals: string[];
  evidenceRefs: EvidenceRef[];
  rollbackCommand?: string;
  trustBoundariesCrossed: string[];
  unresolvedRisks: string[];
  auditChainRef: string;
  signature: string;
}
```

CLI verbs: `arc-studio receipt show <run>`, `arc-studio receipt export <run>`, `arc-studio receipt verify <file>`. Default UI links to receipts before advanced trace.

### TrustDiffSheet

Structured capability diff shown before trust/policy/provider changes that weaken safety or enable new paid/runtime capabilities.

```ts
interface TrustDiff {
  diffId: string;
  before: string[];
  after: string[];
  addedCapabilities: string[];
  removedRestrictions: string[];
  affectedRuntimes: string[];
  requiresConfirmation: boolean;
}
```

v0.1 renders TrustDiff for first workspace trust. Broader key/policy/runtime diffs are v0.2.

### DiffHunk

Props: file, hunkId, status, lines, onApprove, onReject, onEditFirst. Added/removed lines use diff tokens.

```ts
interface DiffHunkProps {
  filePath: string;
  hunkId: string;
  status: 'pending' | 'approved' | 'rejected' | 'applied' | 'conflict' | 'edited';
  lines: Array<{ type: 'add' | 'remove' | 'context'; oldLine?: number; newLine?: number; text: string }>;
  isBinary?: boolean;
  staleBase?: boolean;
  commitSha?: string;
  onApprove: (hunkId: string) => void;
  onReject: (hunkId: string) => void;
  onEditFirst: (hunkId: string) => void;
  onSkip?: (hunkId: string) => void;
  onOpenMerge?: (hunkId: string) => void;
}
```

Keyboard: `A` approve, `R` reject, `E` edit-first, `J/K` next/previous hunk when Review panel focused.

### GraphNode

Props: id, label, type, runtime, state, badges. React Flow node styles map fills to graph node tokens.

```ts
interface GraphNodeData {
  id: string;
  label: string;
  type: 'queen' | 'worker' | 'agent' | 'tool' | 'decision' | 'hitl' | 'terminal' | 'router' | 'start' | 'end';
  runtime: 'swarmgraph' | 'langgraph' | 'crewai' | 'openai-agents' | 'ag2' | 'llamaindex' | 'lmarena';
  state: 'idle' | 'running' | 'waiting' | 'done' | 'failed';
  badges?: string[];
  eventCount?: number;
  subgraphId?: string;
  group?: boolean;
}
```

ARIA: graph canvas exposes `role=application`; selected node announces `{label}, {type}, {runtime}, {state}, {eventCount} events`.

### RunList

Run summary table for v0.1. It does not expose event timeline or event JSON.

```ts
interface RunSummary {
  runId: string;
  sessionId: string;
  runtime: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt: string;
  durationMs?: number;
  costUsd?: number | 'unknown';
  failureNode?: string;
  failureReason?: string;
  failureContext?: Array<{ type: string; timestamp: string; summary: string }>;
  contractId?: string;
  receiptId?: string;
  evidenceRefs?: EvidenceRef[];
  failureAutopsy?: FailureAutopsy;
}
```

```ts
interface RunListProps {
  runs: RunSummary[];
  selectedRunId?: string;
  filters?: { status?: string; runtime?: string; dateRange?: 'today' | '7d' | '30d' | 'all' };
  onSelect: (runId: string) => void;
  onOpenAdvancedTrace: (runId: string) => void;
  onOpenReceipt?: (runId: string) => void;
}
```

ARIA: `role=table`; failure rows announce failure node and advanced trace fallback.

Runs panel renders only `RunSummary`, contract fulfillment, receipts, and Failure Autopsy. No default event timeline or event JSON viewer exists.

### Toast

Variants success/info/warning/danger. Position top-right IDE; bottom above status CLI. Auto-dismiss 5s unless dangerous.

```ts
interface ToastProps {
  tone: 'success' | 'info' | 'warning' | 'danger';
  title: string;
  message: string;
  action?: { label: string; onPress: () => void };
  dismissible?: boolean;
}
```

ARIA: `role=status` for success/info, `role=alert` for warning/danger.

### Modal / Sheet

Focus trap, Esc closes unless destructive confirmation in progress. `role=dialog`, labelled title.

```ts
interface ModalProps {
  title: string;
  description?: string;
  open: boolean;
  closeOnEscape?: boolean;
  closeOnBackdrop?: boolean;
  onClose: () => void;
  children: React.ReactNode;
}
```

### KeyBadge

States: env, keyring, file, unset. Never renders secret value.

```ts
interface KeyBadgeProps {
  provider: string;
  source: 'env' | 'keyring' | 'file' | 'unset';
  valid?: boolean;
}
```

Text: `env`, `keyring`, `file`, `unset`. Tooltip names the variable, not the value.

### CostMeter

Displays estimated ceiling, provider, model, approval state. Warning token when paid call pending.

```ts
interface CostMeterProps {
  provider: string;
  model: string;
  estimatedCeilingUsd: number | 'unknown';
  approvalState: 'not-required' | 'pending' | 'approved' | 'denied';
}
```

### CostCeilingBadge

Shows estimated min/max cost and approval state on phase cards, status details, Runs rows, and paid-call confirmations.

```ts
interface CostCeilingBadgeProps {
  estimatedMinimumUsd: number;
  estimatedMaximumUsd: number | 'unknown';
  currency: 'USD';
  approvalState: 'not-required' | 'pending' | 'approved' | 'denied';
}
```

States: default `text.secondary`, hover reveals provider/model tooltip, focus opens cost detail, active pins tooltip, disabled renders `cost unavailable`. Unknown maximum renders `cost ?` and requires confirmation copy: `Estimated cost: unknown. {provider} does not report estimates. Continue with no ceiling?`

### DaemonStatusBadge

Shows daemon state, version, port, and recovery action.

```ts
interface DaemonStatusBadgeProps {
  state: 'not-installed' | 'stopped' | 'starting' | 'running' | 'stale' | 'port-conflict' | 'unreachable' | 'version-mismatch' | 'orphaned-run';
  version?: string;
  port?: number;
  recoveryAction?: string;
}
```

States: running uses `state.success`; starting uses `state.running`; stale/port-conflict/version-mismatch/orphaned-run use `state.warning`; unreachable/not-installed use `state.danger`.

### FailureCard

Inline chat card rendered when a run fails. This is bounded failure context, not Trace UI.

```ts
interface FailureCardProps {
  runSummary: RunSummary;
  autopsy?: FailureAutopsy;
  lastEvents: Array<{ type: string; timestamp: string; summary: string }>;
  maxEvents?: number;
  costUsd?: number | 'unknown';
  onRetry: () => void;
  onOpenDoctor: () => void;
  onOpenAdvancedTrace: () => void;
}

interface FailureAutopsy {
  runId: string;
  probableCause: string | 'unknown';
  confidence: 'high' | 'medium' | 'low' | 'unknown';
  failedNode?: string;
  lastSafeState?: string;
  retryOptions: Array<{ label: string; command?: string; risk: 'low' | 'medium' | 'high' }>;
  relatedIssues: string[];
  knows: string[];
  guesses: string[];
  evidenceRefs: EvidenceRef[];
}
```

Copy: `Run failed at {failureNode}: {failureReason}. Retry, run diagnostics, open receipt, or open the advanced trace.` Actions: Retry with same input, Open Diagnostic, Open Receipt, Show Advanced Trace. Expandable section `Show me what happened` shows only the last `maxEvents` redacted events before failure; default 5, configurable 3-20. Autopsy must distinguish `knows` from `guesses`; low-confidence causes render as `unknown` plus evidence links.

### PhaseCard (reserved v0.2)

Represents one planner phase in Tasks Phase view.

```ts
interface PhaseCardProps {
  phaseNumber: number;
  title: string;
  runtime: string;
  estimatedCostCeilingUsd: number;
  status: 'planned' | 'running' | 'done' | 'skipped' | 'failed';
  substeps: string[];
  handoffDocumentRef?: string;
}
```

### RuntimeSuggestionCard (reserved v0.2)

Router inline suggestion shown in Chat.

```ts
interface RuntimeSuggestionCardProps {
  detectedTaskType: string;
  recommendedRuntime: string;
  currentRuntime: string;
  reason: string;
  onAccept: () => void;
  onDecline: () => void;
  onAlwaysForProject: () => void;
}
```

ARIA: `role=status`, polite live region, no focus theft.

### HandoffCard (reserved v0.2)

Phase-boundary summary and approval surface.

```ts
interface HandoffCardProps {
  fromRuntime: string;
  toRuntime: string;
  goal: string;
  stateKeysCarriedOver: string[];
  constraints: string[];
  references: string[];
  priorAuditLinks: string[];
  onConfirm: () => void;
  onEdit: () => void;
  onCancel: () => void;
}
```

Keyboard: Enter confirms, Esc cancels, `E` edits when focused.

### WorkspaceTrustBanner

First-run gate for untrusted workspaces.

```ts
interface WorkspaceTrustBannerProps {
  workspacePath: string;
  onTrust: () => void;
  onStayUntrusted: () => void;
  onLearnMore: () => void;
}
```

Copy: `This workspace is untrusted. ARC Studio can read files but cannot write, run, or call paid providers.`

### HotLoop Reserved Component Stubs (v0.2)

| Component | Purpose |
|---|---|
| `DeviceThumbnail` | Shows target device screenshot; spec deferred to HotLoop v0.2 design. |
| `FrameThumbnail` | Shows one visual-diff frame; spec deferred to HotLoop v0.2 design. |
| `LoopTraceTick` | Shows one observation/action loop tick; spec deferred to HotLoop v0.2 design. |
| `RollbackButton` | Rolls HotLoop target back to prior frame/checkpoint; spec deferred to HotLoop v0.2 design. |

### StatusBar / StatusSegment

24px height, mono status font, segments clickable where relevant.

```ts
interface StatusSegmentProps {
  id: string;
  label: string;
  value: string;
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'running';
  href?: string;
  onPress?: () => void;
}
```

### CommandPalette Row

Icon, command label, shortcut, description. Active row uses `bg.surface.raised`.

```ts
interface CommandPaletteRowProps {
  command: string;
  title: string;
  description: string;
  shortcut?: string;
  icon?: LucideIcon;
  disabled?: boolean;
}
```

### EmptyState

Icon 32px, title, body, up to three CTAs.

```ts
interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  body: string;
  actions?: Array<{ label: string; variant: 'primary' | 'secondary' | 'ghost'; onPress: () => void }>;
}
```

### Skeleton

Static under reduced motion; shimmer otherwise using `bg.surface.raised`.

```ts
interface SkeletonProps {
  shape: 'text' | 'rect' | 'circle';
  width: number | string;
  height: number | string;
  lines?: number;
}
```

---

## 10. Content And Microcopy

### 10.1 Errors

| State | CLI text | IDE toast |
|---|---|---|
| Daemon unreachable | `Daemon unreachable at 127.0.0.1:7777. Run arc-studio doctor or start arc-studio serve.` | `Daemon unreachable. Start it or run Doctor.` |
| Model unauthorised | `Provider rejected this model. Pick another in /model or /providers.` | `Model unauthorised. Open Providers.` |
| Paid call denied | `Paid call blocked by policy. Approve, switch mode, or change /config.` | `Paid call blocked by policy.` |
| Runtime missing | `Runtime missing requirement: {requirement}. Fix it in /runtime.` | `Runtime requirement missing.` |

### 10.2 Empty States

Chat: `Ask about this repo or run /workflows.` Graph: `No graph yet. Scan workspace or run a graph-shaped workflow.` Runs: `No runs stored yet. Run a workflow first.` Review: `No changes to review.` Config: `No project config exists. Save to create .arc/config.yaml.`

### 10.3 Confirmations

Paid call: `This may call {provider}. Session total so far: ${total}. This call adds up to ${ceiling}. Continue?` Destructive apply: `Apply approved changes to the workspace?` Rollback: `Rollback last applied change? This edits files back to the previous snapshot.` Key removal: `Remove {provider} key from keyring? Env vars are not changed.` Runtime switch mid-run: `A run is active. Switch runtime for the next run only?`

Git-backed apply confirmations: Rollback copy is `Revert last ARC Studio commit ({sha_short}, {N} files)? This creates a git revert commit.` Approve all: `Approve all {N} pending hunks?` Reject all: `Reject all {N} pending hunks?` Apply without git: `Workspace is not a git repository. Undo will not be available. Continue?` Partial apply: `Applied {M}/{N} hunks. {R} hunks had conflicts. Commit applied hunks?`

### 10.4 Help Text

```text
Session
  /clear      start fresh; previous transcript saved
  /compact    summarise context to free tokens
  /sessions   list recent sessions
  /resume     resume a previous session
  /exit       save and quit

Configuration
  /config     project and user settings
  /providers  manage provider keys
  /runtime    choose runtime
  /model      choose model

Workflow
  /run        run selected workflow
  /stop       cancel active run
  /diff       review proposed changes
  /undo       revert last ARC Studio applied change
  /redo       re-apply last undone ARC Studio change
  /contract   show current run contract
  /receipt    show/export/verify run receipts
  /tasks      open the Tasks panel (steps now; phases reserved)
  /runs       list run summaries
  /workflows  list detected workflows

Mode
  /plan       read-only mode
  /build      apply-capable mode
  /auto       policy-driven mode

Diagnostic
  /status     workspace, runtime, daemon, keys, cost
  /doctor     environment check
  /graph      open graph
  /version    CLI, daemon, protocol, manifest versions
  /update --check  print package-manager upgrade command
  /help       this list
```

Aliases: `/q` -> `/exit`, `/s` -> `/status`, `/h` -> `/help`, `/d` -> `/diff`, `/w` -> `/workflows`, `/c` -> `/config`. Slash autocomplete is fuzzy; `/conf` can match `/config`.

Default slash commands should stay below 20 and avoid command-count competition. State-specific actions such as `open receipt`, `retry failed node`, `show why paid call was blocked`, and `open config field causing this failure` are ranked in the Cockpit Command Palette instead of becoming more slash commands.

### 10.4.1 Cockpit Command Palette

CLI and IDE share a state-aware command index. CLI opens it with `Ctrl+K`; IDE uses Theia command palette entries when ARC has focus. The palette ranks commands from live state: failed run -> `Open Failure Autopsy`, missing key -> `Add provider key`, selected graph node -> `Explain edge` / `Show evidence`, active contract -> `Show run contract`. Slash commands are stable shortcuts; the palette is the adaptive surface.

### 10.11 Context Mentions

| Mention | Resolves to | Token budget | v0.1 status |
|---|---|---:|---|
| `@file.ext` | File content | 16K tokens | Ships |
| `@folder/` | Directory tree plus selected file contents | 32K tokens | Ships |
| `@symbol` | Symbol definition through LSP/AST | 8K tokens | Reserved v0.2 |
| `@url` | Web page content | 16K tokens | Reserved v0.3 |

Mention autocomplete triggers on `@`, fuzzy matches workspace paths, and inserts removable chips before send. Mentioned content is resolved before model call, redacted, and included in the prompt context. Missing or ignored files produce an inline warning, not a fatal error.

### 10.12 Context Compaction

`/compact` triggers LLM summarisation of the current transcript. Original transcript remains in `transcript.jsonl`. Summary replaces context for future turns. Invoked skill/context blocks carry forward up to 5K tokens each and 25K total. Success copy: `Context compacted. {N} tokens -> {M} tokens. {K} context blocks preserved.` Auto-compaction is reserved for v0.2.

### 10.8 Command Tiers

| Tier | Shown where | Criteria |
|---|---|---|
| Default | `/help`, slash autocomplete | Chat-first user needs it in normal workflow; stable UX; no raw implementation detail. |
| Advanced | `arc-studio advanced ...`, advanced docs | Useful for automation, debugging, migration, power users; may expose raw JSON/traces/adapter internals. |
| Hidden/internal | Not user-facing | IDE/daemon/test integration only. |

`arc-studio advanced <any-arc-args...>` is equivalent to `arc <any-arc-args...>` with these differences: stdout/stderr/exit codes are unchanged; `ARC_STUDIO_ADVANCED=1` is set in the child process; workspace trust and key redaction still apply; `--unsafe` requires explicit confirmation and is never implied by advanced mode; default UI may link to an advanced command, but advanced output is never embedded raw unless redacted.

### 10.9 Version And Update Check

`/version` shows CLI version, daemon version, protocol version, and runtime manifest version. `/update --check` checks the current package channel and prints the package-manager command; it does not modify installed files. npm example: `npm install -g arc-studio@latest`. pipx example: `pipx upgrade arc-studio`.

### 10.10 Redaction Contract

All surfaces use the same redactor: CLI output, IDE chat, SSE events, Runs summaries, graph inspector, error cards, failure cards, logs, and advanced command output invoked through `arc-studio advanced`. The redactor removes API keys, bearer tokens, passwords, provider secrets, common cloud credentials, and `.env` values. `/status` always shows key provenance (`env`, `keyring`, `file`, `unset`) and never partial key values. Tooltips may show env var names but never values.

### 10.5 Loading Strings

Daemon: `Starting loopback daemon...` Runtime detection: `Detecting runtimes...` First model call: `Contacting provider...` Graph extraction: `Extracting workflow graph...` Runs loading: `Loading run summaries...`

### 10.6 Accessibility Text

Live regions announce: `Assistant response started`, `Tool call {name} started`, `Plan step {n} completed`, `Node {label} running`, `Approval required`, `Run completed`.

### 10.7 Planner, Router, Handoff Copy (reserved v0.2)

| Surface | Exact copy |
|---|---|
| Router suggestion | `This looks like UI work. HotLoop iterates faster here. Switch? [y/n/always for this project]` |
| Planner approval | `Plan ready: {N} phases, estimated {min}-{max}. Approve to start with phase 1: {title}.` |
| Phase boundary | `Phase {n} done. Next: {title} on {runtime}. Carrying: {summary}. Continue?` |
| Phase re-entry | `Phase {n} reopened. Changes to {file_or_decision} will affect downstream phases {list}.` |
| Auto-advance disabled | `Auto-advance is off. Confirm each phase boundary.` |
| Router off | `Routing is manual. Use /runtime to switch.` |

---

## 11. Graph Visualiser (SwarmGraph)

### 11.1 Canvas

IDE uses React Flow (`@xyflow/react`). Default layout uses `dagre`; alternatives `elkjs` and `breadthfirst`. Background uses dotted grid through React Flow `<Background variant="dots" />`: 1px dots, 24px spacing, 30% opacity. Minimap uses React Flow `<MiniMap />` for graphs with `>20` nodes.

### 11.2 Nodes

Queen 140×56, worker/agent 128×48, tool 112×44, decision diamond 96×64, HITL 128×52, terminal 88×40. Labels ellide after 18 chars. Inspector right dock shows ID, runtime, state, event count, last event, copy buttons. Density modes adjust node size by -15% compact and +15% spacious. Subgraph/group node fields are reserved for v0.2 collapse/expand.

### 11.3 Edges

Directed arrows always on. Label only conditional/router edges. Width increases by message volume bucket: 1, 2, 3px. Active edge uses `graph.edge.active` and React Flow animated edge style with 420ms colour-fill from source to target.

### 11.4 Live Overlay

Always batch. `graph.node.state` events are rendered on a 100ms tick. Each tick renders the latest state per node. Animation is the same regardless of event rate. If multiple state changes occur for one node within a tick, only the final state animates. A burst badge shows the number of skipped intermediate states when a node has more than three changes in one tick.

### 11.5 Replay

Replay UI is not in v0.1. No scrubber, time travel, event timeline, or replay keyboard shortcuts are exposed in default UI. Advanced command replay may remain under `arc-studio advanced`.

### 11.6 CLI Inline Graph

Uses `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼` and arrows `→ ↓`. Narrow fallback is tree list with indentation.

### 11.7 Second-Terminal Graph

Alt-screen child pty. Keys: `i` inspector, `f` fit, `q` close. Resize recalculates layout and preserves selected node. Reserved for v0.2.

### 11.8 Honest Scope Per Adapter

| Runtime | Default UI graph consequence |
|---|---|
| SwarmGraph | Full graph, full live overlay. |
| LangGraph | Nodes render with `(coalesced)` badge. |
| CrewAI | Run gated when export target or provider policy missing. |
| OpenAI Agents | Run gated when SDK/export target missing. |
| AG2 | Detection/export only; no Run button in default UI. |

LlamaIndex and LM Arena are not shown in default UI in v0.1. Detection and advanced commands remain available via `arc-studio advanced`.

### 11.9 Other Runtime Surfaces

Other runtimes may not expose a graph. HotLoop (v0.2) uses Device and Frames panels instead; see §8.12. The graph panel closes by default when the active runtime manifest prefers Device/Frames over Graph.

### 11.9.1 Graph As Cockpit Linkage

Graph events must carry stable `node_id` and should include `message_id`, `tool_call_id`, `decision_id`, `approval_id`, and `evidence_refs` when available. Selecting a graph node highlights related chat messages, tool cards, approvals, run summary rows, and receipts. Selecting a cited chat message focuses the originating graph node.

v0.1 graph commands are read-only: `Explain edge`, `Show evidence`, `Open receipt`, `Copy node id`. Mutating commands (`Rerun node`, `Pause before node`, `Force handoff`) are reserved until checkpoint/replay semantics exist and runtime capability negotiation can prove support.

### 11.10 Graph Export

Graph can export PNG or SVG from the graph toolbar. Export includes current viewport, node states, and legend. Export is UI-only; it does not modify run records.

### 11.11 Graph Performance

React Flow is the v0.1 graph engine decision. Custom SVG and Cytoscape are rejected for v0.1. React Flow handles pan, zoom, fit-to-view, minimap, custom React nodes, and large graphs with lower implementation risk. For graphs over 100 nodes, v0.1 keeps viewport performance acceptable; v0.2 adds subgraph collapse to reduce visual complexity. Minimap is disabled below 360px panel width.

---

## 12. Backgrounds, Textures, Surface Treatment

IDE backgrounds are flat colours from §2.1. Decorative background only appears on first-run empty workspace: dotted graph pattern using `border.subtle` at 16px spacing, 12% opacity. Marketing surfaces use the graph-logo motif with `bg.canvas`, `accent.primary`, and `graph.node.queen`. Skeletons use static blocks under reduced motion, shimmer otherwise.

---

## 13. Sound And Haptics

No sound by default. Optional sounds: HITL prompt and run completion, stored as short `.ogg`, `<800ms`, peak `-18 LUFS`. Config: `ui.sound = false`. Terminal bell off by default; `cli.bell = "off" | "errors" | "hitl" | "complete" | "all"`. Visual bell flashes status segment with `state.info.bg`.

---

## 14. Accessibility Specification

Target: WCAG AA minimum, AAA for core text where feasible. Keyboard-only CLI flow: launch `arc-studio`, type prompt, `Tab` to mode, `/runtime`, arrows select runtime, `/graph`, `/diff`, approve hunk with Enter, `/exit`. IDE flow: `Ctrl+Shift+P`, open ARC Studio, Tab to Chat, send, `Ctrl/Cmd+Shift+H`, arrow graph nodes, `Ctrl/Cmd+Shift+U`, review diff, apply, exit panel. Screen readers use live regions in §10.6. Graph nodes expose spoken description: `{label}, {type}, {runtime}, {state}, {event count} events`. Colour-blind support: every state has icon + text, not colour alone. Strings externalised via `arc.nls.json`; durations use locale formatting.

### 14.6 Planner, Router, Handoff Accessibility (reserved v0.2)

Phase transitions announce via polite live region with `role=status`: `Phase {n} complete. Next phase requires confirmation.` Router suggestion cards are announceable but do not steal focus; dismiss uses a labelled button. Handoff cards are required focus stops; Esc cancels transition, Enter confirms, and Edit Handoff is reachable before Confirm.

---

## 15. States And Edge Cases

| Surface | Empty | Loading | Populated | Error | Offline | Awaiting approval | Applied/Rolled back | v0.2 HotLoop |
|---|---|---|---|---|---|---|---|---|
| CLI Chat | welcome | labelled progress | transcript | error card | daemon hint | HITL card | diff summary | Reserved |
| IDE Chat | empty CTAs | skeleton | transcript | banner | toast + retry | HITL card | toast + link | Reserved |
| Graph | no graph | extracting | live canvas | overlay | no live updates | HITL node | final state | Device/Frames replace graph |
| Runs | no runs | loading runs | run summaries | run load error | cached summaries | run waiting | new summary row | Reserved |
| Review | no changes | preparing diff | hunks | apply error / conflict | disabled apply | pending hunk | applied badge + commit sha | Reserved |
| Config | defaults | reading config | form | validation | local-only | confirm modal | saved toast | HotLoop settings reserved |
| Plan/Tasks | not-yet-planned | planning | executing-phase-N | failed-at-phase-N | blocked | awaiting-approval | completed | Phase/Loop views reserved |
| Router | idle | suggesting | suggestion-accepted | suggestion-overridden | manual-mode | suggestion pending | suggestion-declined | Reserved |
| Handoff | pending | preparing | confirmed | failed | unavailable | awaiting confirm | completed | Reserved |

CLI and IDE behaviour is identical for missing runtime, missing key, paid call blocked, and daemon unreachable. They diverge in graph rendering: CLI uses tree fallback; IDE uses React Flow canvas. Runs has inline summary expansion but no Trace UI; use `arc-studio advanced runs trace <id>` for event detail.

Review-specific states: `no-git-warning` shows undo unavailable and offers `git init`; `concurrent-edit` warns when file mtime changed after diff generation; `conflict` shows manual merge/skip/apply remaining actions; `partial-apply` shows applied/failed hunk counts; `edited` marks hunks changed through Edit First.

---

## 16. Asset And Deliverables List

| Asset | Format | Sizes / notes | Name |
|---|---|---|---|
| Logo concepts | SVG | vector | `arc-logo-{a,b,c}.svg` |
| PNG icons | PNG sRGB | 16/32/64/128/256/512 | `arc-icon-{size}.png` |
| Windows icon | ICO | multi-size | `arc-studio.ico` |
| macOS icon | ICNS | multi-size | `arc-studio.icns` |
| Theia theme | JSON | VS Code/Theia colour theme | `arc-studio-dark.json` |
| High contrast theme | JSON | Theia | `arc-studio-high-contrast.json` |
| ANSI palette | YAML | 16 colours | `arc-terminal-palette.yaml` |
| React Flow style | JSON | node/edge selectors and token map | `arc-react-flow-style.json` |
| Fonts | WOFF2 | Inter, JetBrains Mono subsets | `fonts/*.woff2` |
| Social card | PNG | 1200×630 | `arc-social-card.png` |
| Docs screenshots | PNG | dark/light/CLI | `docs/screenshots/*.png` |
| Design spec | Markdown | production spec | `arc-studio-design-spec.md` |
| Slash command docs | Markdown | user docs | `docs/slash-commands.md` |

---

## 17. Open Questions

| Question | Options | Recommendation |
|---|---|---|
| Is `arc-studio` npm name available? | use `arc-studio`, `@arc-studio/cli`, `arc-studio-ai` | Check; prefer `arc-studio`. |
| Chat model source? | provider LLM, local model, runtime-specific | Provider LLM via configured model. |
| Ship CLI before IDE redesign? | CLI first, IDE first, together | CLI first; IDE tabs next. |
| Embed Python in npm package? | download wheel, require Python, bundle standalone | Start with Python requirement + clear doctor. |
| Min terminal width? | 80, 100, dynamic | 80 supported; 100 preferred. |
| When does trace UI return? | v0.2 with HotLoop frame timeline, v0.3 audit explorer, never | v0.3 audit explorer. |

Resolved by feature-roadmap review: chat uses configured provider model; CLI ships before IDE polish; npm shim requires Python and uses pipx/pip install path; React Flow is graph engine; git is snapshot/undo system; Theia right sidebar is default IDE layout; `/sessions` ships in v0.1.

---

## What Would Make This Spec Wrong

- SwarmGraph is not bundled by default.
- The product keeps `arc` as a command-tree-first CLI instead of chat-first.
- Provider keys cannot use OS keyring.
- Theia is replaced before v0.1 implementation.
- Runtime adapters gain or lose capabilities and the honesty matrix is not updated.
- The team decides graph is secondary rather than primary.
- The global distribution target changes away from npm/pipx.
- The planner and router ship with v0.1 instead of v0.2.
- HotLoop's Device/Frames reservations turn out to be the wrong shape.
- Removing trace UI causes more user friction than expected; monitor `/doctor` and advanced trace usage.

---

## Appendix A: Runtime Manifest Format

One YAML file per runtime, named `runtime.manifest.yaml`, vendored alongside the adapter.

Required fields: `manifest_version`, `id`, `display_name`, `glyph`, `badge_tone`, `category`, `eligibility_signals`, `prompt_signals`, `cost_signals`, `capabilities`, `events_produced`, `summary_fields`, `panel_slots`, `protocol_features`, `slot_preferences`. Capability negotiation reservations also require `capability_snapshot`, `degradations`, `evidence_model`, `cost_model`, `recovery_model`, `handoff_model`, and `conformance_probe_ids` keys, even when values are `unknown` or empty.

Rules: unsupported major `manifest_version` is rejected; unsupported minor version warns but may load when required fields exist. Manifest validation runs in `/doctor`.

```yaml
manifest_version: 1
id: swarmgraph
display_name: SwarmGraph
glyph: SG
badge_tone: queen
category: deliberative
eligibility_signals:
  workspace:
    - files_match: ["**/*swarm*.py", "**/swarmMain/**/*.py"]
prompt_signals:
  verbs: ["run", "orchestrate", "coordinate", "consensus"]
  patterns: ["queen", "worker", "multi-agent"]
cost_signals:
  paid_provider_required: false
  shell_required: true
capabilities:
  inspect: true
  run: true
  export_schema: true
  export_workflow: true
  graph: true
  trace_ui: false
capability_snapshot:
  inspect: claimed
  dry_run: unknown
  run: claimed
  cancel: claimed
  redact: daemon
  emit_graph_live: claimed
  report_cost_pre: unknown
  report_cost_post: unknown
  recover: unknown
  accept_handoff_v1: false
  produce_handoff_v1: false
degradations:
  redact: arc.daemon_redactor
  report_cost_pre: cost_unknown
evidence_model:
  refs: [file, tool_output, run, node, receipt]
cost_model:
  preflight: unknown
  postflight: optional
recovery_model:
  rollback: git-revert
  node_rerun: reserved
handoff_model:
  version: 1
  accepts: false
  produces: false
conformance_probe_ids: []
events_produced:
  - RUN_STARTED
  - RUN_COMPLETED
  - RUN_FAILED
  - NODE_STARTED
  - NODE_UPDATE
summary_fields:
  - runId
  - sessionId
  - runtime
  - status
  - startedAt
  - durationMs
  - costUsd
  - failureNode
  - failureReason
  - failureContext
panel_slots:
  primary: Graph
  secondary: Tasks
protocol_features:
  handoff: reserved
slot_preferences:
  open_by_default: ["Chat", "Tasks", "Graph", "Runs"]
  closed_by_default: ["Review", "Config"]
```

HotLoop v0.2 forward-reference:

```yaml
manifest_version: 1
id: hotloop
display_name: HotLoop
glyph: HL
badge_tone: info
category: observational
eligibility_signals:
  workspace:
    - files_match: ["package.json", "pubspec.yaml", "app.json"]
prompt_signals:
  verbs: ["iterate", "preview", "fix UI", "hot reload"]
cost_signals:
  paid_provider_required: true
capabilities:
  inspect: true
  run: true
  graph: false
  device: true
  frames: true
events_produced:
  - device.frame.captured
  - device.target.changed
  - loop.tick.started
  - loop.tick.completed
  - frame.diff.available
summary_fields:
  - runId
  - sessionId
  - runtime
  - status
  - startedAt
  - durationMs
  - costUsd
  - failureFrame
  - failureReason
  - failureContext
panel_slots:
  primary: Device
  secondary: Frames
protocol_features:
  handoff: reserved
slot_preferences:
  open_by_default: ["Chat", "Tasks", "Device", "Frames", "Runs"]
  closed_by_default: ["Graph", "Review", "Config"]
```

## Appendix B: Reserved Handoff Event Payload

No runtime emits this in v0.1. The event name and payload shape are reserved for v0.2.

```yaml
event_type: handoff
handoff_version: 1
from_runtime: swarmgraph
to_runtime: hotloop
goal_for_next_phase: string
state: object
constraints: string[]
references: string[]
prior_audit_links: string[]
created_at: iso8601
session_id: ulid
run_id: ulid | null
```

Unknown `handoff_version` major is rejected. Payload is redacted before logging or SSE display. Handoff events are included in session transcript but marked reserved until v0.2.

---

## Lock Criteria

The spec is lockable when all are true:

| Criterion | Status |
|---|---|
| Session schema exists and uses ULID `session_id`. | Required |
| Daemon state machine exists. | Required |
| Command tiers exist. | Required |
| Runtime manifest versioning exists. | Required |
| Handoff payload versioning exists. | Required |
| `RunSummary` schema exists. | Required |
| `FailureCard` exists. | Required |
| Trace UI remains removed from default v0.1. | Required |
| LlamaIndex and LM Arena remain hidden from default UI. | Required |
| `/runs` and `/workflows` appear in `/help`. | Required |
| `/trace` does not appear in `/help`. | Required |
| Advanced passthrough is defined. | Required |
| Redaction contract exists. | Required |
| Trust binding exists. | Required |
| Unknown cost state exists. | Required |
| `/update --check` does not self-modify installed files. | Required |
| `@file` and `@folder` mention contracts exist; `@symbol`/`@url` reserved. | Required |
| Message queueing semantics exist. | Required |
| React Flow is the graph engine decision. | Required |
| Git-backed apply/undo/redo semantics exist. | Required |
| Policy/config path split and precedence are explicit. | Required |
| Trust binding includes canonical path, machine ID, and user ID. | Required |
| Runs filters and inline failure expansion are specified without default Trace UI. | Required |
| RunContract schema exists and v0.1 pre-run card is specified. | Required |
| RunReceipt schema exists and is signed by the existing audit chain. | Required |
| FailureAutopsy schema exists with `knows`, `guesses`, `confidence`, and evidence refs. | Required |
| EvidenceRef schema exists and can attach to chat messages, run summaries, graph nodes, receipts, and failures. | Required |
| Stable cross-surface IDs exist: `message_id`, `decision_id`, `approval_id`, `policy_decision_id`, stable `node_id`. | Required |
| Runtime manifest capability snapshot, degradation map, evidence/cost/recovery/handoff reservations exist. | Required |
| TrustDiff schema exists. | Required |
| Frame receipt evidence type is reserved for HotLoop. | Required |
| Graph node command menu is read-only in v0.1; mutating commands remain reserved. | Required |
| CLI/IDE approval actions are idempotent through shared approval IDs. | Required |
