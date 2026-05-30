# IDE Layout / Panels Review

## Current ARC Spec

ARC Studio specifies a **six-panel model** plus a status bar, rendered inside a Theia-based IDE. The spec (§8, §5, §9) defines the following layout:

### Six Panels (§8.1-8.13, §9 Tabs)

| Panel | Purpose | v0.1 Status |
|---|---|---|
| **Chat** | Primary default surface — transcript, tool cards, HITL cards, input with slash hints | Specified (§8.1), not implemented |
| **Tasks** | Step view (v0.1), Phase/Loop views (v0.2 reserved) — runtime step list, blockers, current node | Specified (§8.2), not implemented |
| **Graph** | Cytoscape.js canvas with live overlay, node inspector, minimap for >20 nodes | Specified (§8.3, §11), partially implemented (arc-workflow-graph-widget) |
| **Runs** | Run list + summary table only — no event timeline or JSON viewer in v0.1 | Specified (§8.5), partially implemented (arc-run-timeline-widget, but shows more than spec allows) |
| **Review/Apply** | Monaco diff editor, file/hunk list, Approve/Reject/Edit First actions | Specified (§8.4), not implemented |
| **Config** | Full-panel tabs: Runtime, Model, Providers, Workspace Trust, Profiles, Graph, Advanced | Specified (§8.6), not implemented |
| **Status bar** | Trust, runtime, mode, daemon, cost, contextual commands | Specified (§7.14, §9 StatusBar), not implemented |

### Default Workspace Layout (§8.1)

```
┌ Activity 48 ┬──────────────── Chat 60% ────────────────┬─ Tasks collapsed┐
│ ARC         │ transcript                                │ ▸ Plan          │
│ Graph       │ messages, HITL cards, tool calls          │                 │
│ Runs        │                                           │                 │
│ Config      │ input + slash hints + send button         │                 │
├─────────────┴───────────────────────────────────────────┴─────────────────┤
│ Status: trust ✓ | SG ✓ | Build | daemon ● | cost $0.00                    │
└────────────────────────────────────────────────────────────────────────────┘
```

Three-column: activity bar (48px), Chat (60%), Tasks collapsed sidebar. Activity bar icons for ARC/Graph/Runs/Config.

### Current Implementation Reality

The codebase currently registers **5 separate widgets**, each independently opened:

1. `ArcWidget` — main widget with 3 collapsible sections (WorkflowExecution, TraceViewer, WorkflowDetection)
2. `ArcAdaptersWidget` — runtime adapter status
3. `ArcWorkflowGraphWidget` — workflow graph visualization
4. `ArcRunTimelineWidget` — run timeline
5. `ArcEventStreamWidget` — event stream

There is **no unified panel model**, **no tabbed interface**, **no chat panel**, **no activity bar**, and **no status bar**. Widgets open in the main area with no coordinated layout.

### Layout Behaviors Specified

| Behavior | Spec Section | Status |
|---|---|---|
| Drag-to-tab sidebar collapse (§8.8) | All panels can drag into right sidebar tabs, default 420px, min 320px, max 55vw | Not implemented |
| Single-sidebar collapse (§8.8) | Icon-only tabs + tooltip when collapsed, sticky chat input | Not implemented |
| Mobile/narrow (§8.9) | <720px: one panel at a time, bottom tab bar; <480px: selectors collapse into Status sheet | Not implemented |
| Keyboard shortcuts (§8.13) | `Ctrl/Cmd+;` focus chat, `Ctrl/Cmd+Shift+H` graph, `Ctrl/Cmd+Shift+U` runs, `Ctrl/Cmd+,` config | Partially implemented (arc-keybinding-contribution.ts exists) |
| Graph-active workspace (§8.3) | Chat 40%, Graph 60%, Tasks overlay top-right — auto-expands on run | Not implemented |
| Review flow (§8.4) | Review/Apply opens over canvas at 70% width, Chat shrinks to 30% | Not implemented |
| Panel slot preferences (Appendix A) | Runtime manifest `slot_preferences.open_by_default` / `closed_by_default` | Not implemented |
| Focus management (§9 Tabs) | Roving tabindex, arrow keys, Enter activates | Not implemented |
| Default layout on first launch (§8.1, §8.7) | Chat default, empty state with CTAs | Not implemented |

### Keyboard Shortcut Audit (§8.13)

| Shortcut | ARC Action | Theia/VS Code Conflict | Spec Resolution |
|---|---|---|---|
| `Ctrl/Cmd+L` | Focus chat input | VS Code clear terminal | Remap to `Ctrl/Cmd+;` |
| `Ctrl/Cmd+Enter` | Send message | Safe | Keep |
| `Ctrl/Cmd+Shift+G` | Open Graph | Source control | Remap to `Ctrl/Cmd+Shift+H` |
| `Ctrl/Cmd+Shift+R` | Open Runs | Rename symbol | Remap to `Ctrl/Cmd+Shift+U` |
| `Ctrl/Cmd+Shift+T` | Open Tasks | Reopen closed tab | Use command palette only |
| `Ctrl/Cmd+,` | Open Config | Settings | Acceptable when ARC panel focused |
| `Esc` | Close transient UI | Safe | Keep |

ARC overrides apply **only when an ARC panel has focus**; otherwise Theia defaults win.

### Density and Breakpoints (§5.1, §5.2)

- Base unit: 4px grid
- Breakpoints: narrow <720px, medium 720-1199px, wide >=1200px
- Density modes: compact (28px rows), comfortable (36px), spacious (44px)
- Chat max-width: 880px

### HotLoop Panel Reservations (§8.12)

v0.2 reserves **Device** and **Frames** panel slots. When HotLoop is active, Graph defaults closed and Device + Frames default open. No v0.1 mockups required.

---

## Comparable Products / Research

### Layout Comparison

| Product | Layout Model | Panel Count | Primary Panel | Secondary | Activity Bar | Status Bar | Tabbed Panels | Drag Rearrange |
|---|---|---|---|---|---|---|---|---|
| **Cursor** | 3-column fixed | 3 | Editor (center) | Explorer (left), Agent panel (right) | No (sidebar icons) | Yes (bottom) | Agent panel has sub-tabs (Chat/Composer) | No |
| **Windsurf** | 3-column fixed | 3 | Editor (center) | Explorer (left), Cascade (right) | No (sidebar icons) | Yes (bottom) | Cascade has mode tabs | No |
| **Kiro** | 3-column fixed | 3 | Editor (center) | Explorer (left), Chat (right) | No (sidebar icons) | Yes (bottom) | Chat panel has tabs | No |
| **VS Code Copilot** | 3-column + sidebar | 3-4 | Editor (center) | Explorer (left), Copilot chat (right sidebar) | Yes (left) | Yes (bottom) | Copilot has Chat/Edits sub-tabs | Yes (sidebar position) |
| **JetBrains AI Assistant** | Tool window | 2+ | Editor | AI Assistant tool window (right/bottom dock) | Yes (left) | Yes (bottom) | Tool window tabs | Yes (dock position) |
| **LangGraph Studio** | Mode switching | 2 | Graph or Chat (mutually exclusive) | Sidebar with config/runs | No | Minimal | Graph/Chat mode toggle | No |
| **ARC Studio (spec)** | 3-column + activity bar | 6 | Chat (60%) | Tasks (collapsed right), Graph/Runs/Config via activity bar | Yes (left, 48px) | Yes (bottom, 24px) | Config uses tabs; panels can tab into sidebar | Yes (drag-to-tab) |

### Key Patterns from Competitors

**Cursor (3-column: explorer/editor/agent):**
- Agent panel is always visible on the right — persistent, not modal
- Sub-tabs within agent panel: Chat vs Composer mode
- Accept/Reject inline in editor, not in agent panel
- Model dropdown above chat input
- Agent panel width ~350px, resizable via drag
- [needs verification] Cursor does not allow the agent panel to be dragged to a separate tab group; it is fixed to the right sidebar slot

**Windsurf (3-column: explorer/editor/Cascade):**
- Cascade panel mirrors Cursor's agent panel pattern
- Code/Chat toggle at top of Cascade panel
- Inline diffs rendered in editor, Cascade shows summary
- [needs verification] Cascade panel is not movable to bottom or left sidebar

**Kiro (3-column: explorer/editor/chat):**
- Amazon's IDE follows the same 3-column pattern
- Chat panel on right with model selector
- Autopilot toggle within chat panel
- [needs verification] Kiro panel layout is fixed, not draggable

**VS Code Copilot (right sidebar chat):**
- Copilot chat opens in right sidebar by default
- Can be moved to bottom panel or left sidebar via drag
- Sub-tabs: Chat, Edits, History
- Integrates with VS Code's existing sidebar/activity bar model
- Command palette (`Ctrl+Shift+P`) is primary navigation for all features
- Status bar shows minimal Copilot status (icon)

**JetBrains AI Assistant (tool window):**
- AI Assistant opens as a tool window — dockable to right, bottom, or floating
- Uses JetBrains' existing tool window infrastructure (same as Terminal, Run, Debug)
- Tab-based within the tool window stripe
- Can be pinned/unpinned, auto-hide
- Does not redefine the IDE layout — integrates into existing paradigm

**LangGraph Studio (graph/chat mode switching):**
- Mutually exclusive modes: either Graph view or Chat view is visible, not both simultaneously
- Sidebar for configuration and run history
- Time-travel/replay in graph mode
- This is the closest conceptual match to ARC's Graph-active workspace (§8.3)
- However, LangGraph Studio is a standalone app, not an IDE extension

### What Competitors Do Better

1. **Simplicity**: Cursor/Windsurf/Kiro all use 3 columns — explorer, editor, agent. Users understand this immediately. ARC's 6-panel model is 2x the cognitive load.
2. **Persistent agent panel**: The right-sidebar chat pattern is universal. Users expect the agent to always be "over there on the right."
3. **Editor integration**: Diffs, inline edits, and code actions happen in the editor, not in a separate panel. ARC's Review/Apply panel (§8.4) fights this pattern.
4. **Command palette as escape hatch**: VS Code and JetBrains rely on command palette for advanced features. ARC specifies this partially (§9 CommandPalette) but does not lean on it enough.
5. **Dockable, not prescribed**: JetBrains and VS Code let users move panels. ARC specifies drag-to-tab (§8.8) but the default layout is rigid.
6. **Mode switching over panel proliferation**: LangGraph Studio toggles between graph and chat. ARC tries to show both simultaneously (§8.3 at 40/60 split), which requires wider screens.

### What ARC Does Differently (And Should Keep)

1. **Graph as first-class surface**: No competitor shows a live agent topology graph during execution. This is ARC's differentiator.
2. **Runs panel**: Cursor/Windsurf have no run history panel. ARC's run management is more sophisticated.
3. **Tasks panel**: Step/Phase/Loop views are unique to ARC's multi-runtime model.
4. **Honest runtime gating**: Disabled runtimes with reasons — no competitor does this.
5. **Status bar with cost**: Real-time cost visibility in the status bar is unique.
6. **Activity bar for ARC-specific panels**: Separating ARC panels from Theia's explorer/terminal is the right call.

---

## Gaps

### Critical Gaps

1. **No chat panel implemented**: The spec's primary default surface (§8.1) does not exist. The current `ArcWidget` has a prompt input for workflow execution but no conversational transcript rendering.
2. **5 independent widgets, not 6 coordinated panels**: The current architecture registers 5 separate widgets with no layout coordination. The spec requires 6 panels with coordinated visibility, sizing, and tab behavior.
3. **No activity bar**: The spec shows a 48px left activity bar with ARC/Graph/Runs/Config icons (§8.1). This does not exist.
4. **No status bar**: The spec defines a 24px status bar with segments for trust, runtime, mode, daemon, cost (§7.14, §9 StatusBar). Not implemented.
5. **No unified navigation**: Users currently open widgets via separate commands/menu items. There is no single "ARC Studio" entry point with tabbed or activity-based navigation.
6. **Review/Apply panel not specified for Theia's editor**: The spec (§8.4) describes a Monaco diff editor at 70% width, but Theia already has a built-in diff editor. The spec does not clarify whether ARC should use Theia's diff infrastructure or build its own.

### Design Gaps

7. **Theia's editor area is ignored**: The spec assumes Chat + Graph + Tasks fill the entire window. But Theia has an editor area (for code files). The spec does not address how ARC panels coexist with open code editors. This is a fundamental oversight.
8. **Panel coexistence with Theia's built-in panels**: Theia has Explorer, Search, SCM, Debug, Extensions, Outline, and more. The spec does not address whether ARC panels share the sidebar with these, replace them, or occupy a separate slot.
9. **40/60 Chat/Graph split requires wide screens**: §8.3 specifies Chat at 40%, Graph at 60% during active runs. At 1200px, Chat gets 480px — barely enough for readable chat messages (spec says max-width 880px, but minimum comfortable is ~350px). At 1024px, Chat gets 410px. This layout is only comfortable at >=1400px.
10. **Tasks panel collapsed state unclear**: §8.1 shows Tasks as "collapsed" with `▸ Plan` visible. The spec does not define the collapsed width, whether it's icon-only or shows labels, or how it expands (click, hover, keyboard).
11. **No panel persistence**: The spec does not specify whether panel layout (sizes, open/closed state, tab order) persists across sessions.
12. **Config panel as full-panel vs sidebar**: §8.6 describes Config as a "full-panel" with tabs, but §8.1 shows Config as an activity bar icon. These conflict — is Config a sidebar panel or a full main-area panel?
13. **No specification for what happens in the main/editor area**: When Chat is at 60% and Tasks is collapsed on the right, what occupies the remaining space? Theia's editor? An empty canvas? The spec is silent.

### Implementation Gaps

14. **Theia sidebar vs custom layout**: The spec describes a custom 3-column layout but does not specify how to achieve this within Theia's layout system. Theia supports left sidebar, right sidebar, bottom panel, and main editor area. The spec's layout (activity bar + chat + tasks sidebar) may require custom layout managers.
15. **Drag-to-tab requires Theia layout API**: §8.8's drag-to-tab behavior requires Theia's tab bar drag-and-drop API, which has limited support. [needs verification]
16. **Mobile/narrow handling not scoped**: §8.9 specifies behavior below 720px and 480px, but Theia's browser app is not designed for mobile. This may be v0.2 or later scope.
17. **Keyboard shortcut conflicts not fully resolved**: §8.13 remaps some shortcuts but `Ctrl/Cmd+,` for Config still conflicts with Theia Settings when ARC panel is not focused. The "only when ARC panel focused" rule requires context-key implementation.

### Scope Gaps

18. **Six panels may be too many for v0.1**: Chat, Tasks, Graph, Runs, Review/Apply, Config — implementing all six panels with coordinated layout is a large surface for v0.1.
19. **Review/Apply panel duplicates Theia's diff editor**: Theia already has a Monaco-based diff editor. Building a separate Review/Apply panel with Monaco diff is redundant and expensive.
20. **Tasks panel has minimal v0.1 content**: Step view ships in v0.1, but Phase and Loop views are v0.2 reserved. A panel with only one view may not justify its own slot.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **P1: Reduce to 4 panels for v0.1** — Chat, Graph, Runs, Config. Merge Tasks into Chat (as inline cards) and defer Review/Apply to Theia's diff editor. | Six panels is too much surface for v0.1. Tasks Step view is thin content. Review/Apply duplicates Theia. | v0.1 | Medium — requires spec restructure but reduces implementation load | §8.1: Remove Tasks and Review/Apply from default layout; §8.2: Tasks Step view becomes inline chat cards; §8.4: Defer to Theia diff |
| **P2: Use Theia's sidebar infrastructure, not custom layout** — Place ARC panels in Theia's right sidebar with tabs. Activity bar icons map to sidebar tabs. | Theia already has sidebar, tab bars, drag rearrange, and persistence. Fighting Theia's layout system is expensive and fragile. | v0.1 | Low — aligns with Theia conventions | §8.1: Replace custom 3-column with Theia right sidebar; §8.8: Use Theia tab drag |
| **P3: Editor area stays for code** — ARC panels occupy the right sidebar only. The main editor area remains for code files, diffs, and Theia's built-in views. | Users need to see code while chatting. Every competitor keeps the editor visible. ARC's spec implicitly replaces the editor with panels. | v0.1 | Low — matches user expectations | §8.1: Clarify editor area is preserved; §8.3: Graph opens in main area (not sidebar) when active |
| **P4: Graph opens in main area during runs** — When a run starts, Graph opens as a main-area tab (beside any open editors). Chat remains in right sidebar. | Graph needs more space than a sidebar can provide. 40/60 split in sidebar is cramped. Main area gives Graph room. | v0.1 | Low — Theia supports main-area widgets | §8.3: Change Graph to main-area widget; remove 40/60 split spec |
| **P5: Status bar integrates with Theia's status bar** — ARC adds segments to Theia's existing bottom status bar instead of creating a separate bar. | Theia already has a status bar. Adding a second bar wastes 24px and confuses users. | v0.1 | Low — Theia supports status bar contributions | §7.14, §9 StatusBar: Change to Theia status bar contribution |
| **P6: Command palette as primary navigation** — All ARC panels accessible via `Ctrl/Cmd+Shift+P` > "ARC: Open Chat/Graph/Runs/Config". Activity bar icons are secondary. | Matches Theia/VS Code conventions. Reduces need for custom activity bar. Users already know command palette. | v0.1 | Low | §8.1: Demote activity bar to secondary; §8.13: Add command palette entries |
| **P7: Persist panel layout in Theia preferences** — Panel open/closed state, sidebar width, and tab order persist via Theia's layout storage. | Users expect layout to survive reload. Theia already stores layout state. | v0.1 | Low | §8: Add persistence note |
| **P8: Defer mobile/narrow to v0.2** — Remove §8.9 from v0.1 scope. Theia browser app is not mobile-ready. | Mobile handling requires responsive layout work across the entire Theia app, not just ARC panels. Out of scope for v0.1. | v0.2 | None | §8.9: Mark as v0.2 reserved |
| **P9: Defer drag-to-tab rearrange to v0.2** — Panels open in fixed sidebar tabs for v0.1. Drag rearrange is nice-to-have. | Theia's drag-and-drop API for tab bars is limited. Fixed tabs are simpler and match Cursor/Windsurf. | v0.2 | None | §8.8: Mark drag rearrange as v0.2 |
| **P10: Config as sidebar tab, not full-panel** — Config opens as a sidebar tab (like Chat/Runs), not a full main-area panel. | Config is a setup surface, not a primary workflow. Sidebar width (~420px) is sufficient for forms. | v0.1 | Low | §8.6: Change to sidebar tab |
| **P11: Use Theia's diff editor for Review/Apply** — When a run proposes changes, open Theia's built-in diff editor in the main area. Add Approve/Reject buttons via Theia's editor toolbar or a companion sidebar panel. | Building a Monaco diff viewer from scratch is expensive and duplicates Theia. Theia's diff editor already supports side-by-side, inline, navigation, and editing. | v0.1 (if Review ships) or v0.2 | Medium — requires integration with Theia's editor API | §8.4: Rewrite to use Theia diff editor + companion panel |
| **P12: Default layout on first launch** — Chat tab open in right sidebar. All other panels closed. Empty state in Chat shows CTAs. No activity bar icons until user opens a second panel. | Reduces cognitive load. Matches Cursor's default (agent panel open, nothing else). Users discover additional panels via command palette or slash commands. | v0.1 | Low | §8.1, §8.7: Define explicit first-launch state |
| **P13: Runtime manifest `slot_preferences` drives default panel visibility** — When a runtime is selected, its manifest's `open_by_default` / `closed_by_default` arrays control which panels open. | Already specified in Appendix A. Makes layout adaptive per runtime. SwarmGraph opens Chat+Graph+Runs; HotLoop (v0.2) opens Chat+Device+Frames. | v0.1 | Low — manifest format already defined | §8.1: Reference manifest-driven defaults |

---

## Recommended Decisions

### Decision 1: Four panels for v0.1, not six

**Lock:** Chat, Graph, Runs, Config. Defer Tasks (merge into Chat as inline step cards) and Review/Apply (use Theia's diff editor).

Rationale: Six panels is too much surface. Tasks Step view is a thin list that renders well as inline chat cards (matching Cursor's "Agent steps" feed). Review/Apply requires Monaco diff integration that Theia already provides. Reducing to 4 panels cuts implementation scope by 33% without losing functionality.

### Decision 2: Right sidebar with tabs, not custom 3-column layout

**Lock:** ARC panels live in Theia's right sidebar as tabbed views. The main editor area remains for code files and Graph visualization.

Rationale: Every competitor (Cursor, Windsurf, Kiro, VS Code Copilot) places the agent panel in the right sidebar. Users expect this. Fighting Theia's layout system to build a custom 3-column arrangement is expensive and fragile. Theia's sidebar already supports tabs, resize via drag, and collapse.

### Decision 3: Graph opens in main area during active runs

**Lock:** Graph visualization opens as a main-area tab (alongside code editors), not in the sidebar. Chat remains in the right sidebar.

Rationale: Graph needs canvas space. At sidebar width (~420px), a graph with >10 nodes is cramped. The spec's 40/60 Chat/Graph split (§8.3) requires both panels in the sidebar, which is only comfortable at >=1400px window width. Opening Graph in the main area gives it room while keeping Chat accessible. This matches LangGraph Studio's approach (graph as primary surface) while respecting the IDE's editor area.

### Decision 4: Status bar contribution, not separate bar

**Lock:** ARC adds status segments to Theia's existing bottom status bar via Theia's status bar contribution API.

Rationale: Theia already has a 22-24px status bar. Adding a second bar wastes vertical space and creates confusion about which bar is authoritative. Theia's status bar supports left/center/right segments and clickable items — sufficient for ARC's trust, runtime, mode, daemon, and cost indicators.

### Decision 5: Command palette primary, activity bar secondary

**Lock:** All ARC panels are accessible via Theia's command palette (`Ctrl/Cmd+Shift+P`). Activity bar icons (or sidebar view container icons) are added as secondary shortcuts.

Rationale: Theia users already use the command palette. Adding a custom 48px activity bar duplicates Theia's left sidebar icon strip. VS Code Copilot and JetBrains AI Assistant both integrate into existing navigation rather than creating parallel chrome. Activity bar icons can be added later as a polish item.

### Decision 6: First-launch default — Chat only

**Lock:** On first launch, only the Chat tab is open in the right sidebar. All other panels are closed. Chat shows empty state with CTAs: "Ask a question", "Scan workspace", "Open sample".

Rationale: Minimizes cognitive load. Matches Cursor's default (agent panel visible, nothing else). Users discover Graph, Runs, and Config through slash commands (`/graph`, `/runs`, `/config`), command palette, or by clicking sidebar icons after they learn the tool.

### Decision 7: Panel layout persistence via Theia storage

**Lock:** Panel open/closed state, sidebar width, and tab order persist across sessions using Theia's layout storage service.

Rationale: Standard IDE behavior. No spec change needed — Theia handles this automatically for registered widgets.

### Decision 8: Defer mobile/narrow and drag rearrange to v0.2

**Lock:** §8.9 (mobile/narrow) and §8.8 (drag-to-tab rearrange) are v0.2 reserved. v0.1 targets desktop browser at >=720px width with fixed sidebar tabs.

Rationale: Theia's browser app is not responsive. Mobile handling requires system-wide responsive layout work. Drag rearrange requires Theia's tab bar DnD API, which is limited. Both are polish items, not core functionality.

---

## Specific Spec Edits

### §8.1 Default Workspace

**Replace** the current 3-column ASCII layout with:

```
┌ Theia Left Sidebar ┬── Editor Area (code files, Graph during runs) ──┬─ ARC Right Sidebar ┐
│ Explorer           │                                                  │ [Chat] [Runs] [Cfg]│
│ Search             │  (open code editors, or Graph widget during run) │                    │
│ SCM                │                                                  │  Chat transcript   │
│ ...                │                                                  │  + input           │
├────────────────────┴──────────────────────────────────────────────────┴────────────────────┤
│ Theia Status Bar:  trust ✓ | SG ✓ | Build | daemon ● | cost $0.00                          │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Add:** "ARC panels occupy Theia's right sidebar as tabbed views. The editor area remains available for code files and Graph visualization. Theia's existing status bar is extended with ARC segments."

**Add:** "First-launch default: Chat tab open, all other tabs closed. Empty state shows CTAs."

**Remove:** The 48px activity bar from the v0.1 layout. Move to v0.2 polish.

### §8.2 Tasks Panel Views

**Change:** "Tasks panel" → "Tasks section within Chat transcript"

**Replace:** "The Tasks panel replaces the previous planning sidebar" → "Task steps render as inline cards within the Chat transcript during active runs. A dedicated Tasks panel is deferred to v0.2 when Phase and Loop views ship."

**Add to §9 Card component:** `TaskStepCard` variant for inline step rendering in chat.

### §8.3 Graph-Active Workspace

**Replace** the 40/60 Chat/Graph split with:

"During an active run, the Graph widget opens in Theia's main editor area as a tab. Chat remains in the right sidebar at full sidebar width. When the run completes, the Graph tab remains open but does not auto-close. Users can close it manually or it closes on the next run's graph open."

**Remove:** "Chat left 40%, Graph right 60%, Tasks overlay top-right."

### §8.4 Review Flow

**Replace with:**

"Review/Apply uses Theia's built-in diff editor in the main area. A companion 'Review' panel opens in the right sidebar (beside Chat) showing the file/hunk list and Approve/Reject/Edit First actions. Selecting a hunk navigates the diff editor to the corresponding change. Edit First opens the file in Theia's standard editor."

**Remove:** "Review/Apply opens over canvas at 70% width. Chat shrinks to 30%."

### §8.5 Runs

**No change needed.** Runs as a sidebar tab is correct. Confirm that the current `arc-run-timeline-widget` is simplified to match the spec's run-summary-only v0.1 scope (no event timeline or JSON viewer).

### §8.6 Config

**Change:** "Full-panel Config tabs" → "Config opens as a sidebar tab with internal sub-tabs"

**Add:** "Config tab width matches sidebar width (default 420px, min 320px). Forms stack vertically. Save writes `.arc/config.yaml`."

### §8.8 Single-Sidebar Collapse

**Simplify to:** "All ARC panels are tabs in Theia's right sidebar. The sidebar can be collapsed to icon-only mode (Theia's built-in sidebar toggle). When collapsed, panel tabs show icons with tooltips. Sidebar width defaults to 420px, minimum 320px, maximum 55vw. Drag-to-tab rearrange is deferred to v0.2."

### §8.9 Mobile / Narrow Window

**Mark as v0.2 reserved:** "Mobile and narrow-window handling is deferred to v0.2. v0.1 targets desktop browser at >=720px width."

### §8.12 Panel Reservations For HotLoop

**No change needed.** Device and Frames reservations are correctly scoped to v0.2.

### §8.13 Keyboard Shortcut Audit

**Update:** Remove `Ctrl/Cmd+Shift+T` (Open Tasks) since Tasks is merged into Chat. Add command palette entries as the primary keyboard navigation:

| Shortcut | Action | Notes |
|---|---|---|
| `Ctrl/Cmd+;` | Focus chat input | Primary shortcut |
| `Ctrl/Cmd+Enter` | Send message | |
| `Ctrl/Cmd+Shift+H` | Toggle Graph in main area | Opens/closes Graph tab |
| `Ctrl/Cmd+Shift+U` | Toggle Runs sidebar tab | |
| `Ctrl/Cmd+,` | Open Config sidebar tab | Only when ARC sidebar focused |
| `Esc` | Close transient UI | |
| Command palette | `ARC: Open Chat/Graph/Runs/Config` | Primary navigation |

### §7.14 Status Line

**Add for IDE:** "In the IDE, ARC status segments are contributed to Theia's existing bottom status bar via `StatusBar` contribution API. Segments: trust state, runtime badge, mode chip, daemon badge, cost meter. Segments are clickable and navigate to the relevant panel (e.g., clicking runtime opens Config tab)."

### §9 Tabs Component

**Add:** "Panel tabs in the right sidebar use Theia's tab bar infrastructure. The `Tabs` component (§9) is used for Config's internal sub-tabs (Runtime, Model, Providers, etc.), not for panel-level navigation."

### Appendix A: Runtime Manifest

**Update `slot_preferences` example:**

```yaml
slot_preferences:
  open_by_default: ["Chat"]          # Only Chat opens on first run with this runtime
  suggest_open: ["Graph", "Runs"]     # Shown as suggestions in empty state
  closed_by_default: ["Config"]
  main_area_widgets: ["Graph"]        # Graph opens in main area, not sidebar
```

---

## Acceptance Criteria

### v0.1 Layout

- [ ] ARC panels (Chat, Graph, Runs, Config) are registered as tabbed views in Theia's right sidebar
- [ ] Chat tab is open by default on first launch; all other tabs are closed
- [ ] Chat tab renders a transcript with user/agent messages, tool cards, HITL cards, and input with slash hints
- [ ] Graph widget opens in Theia's main editor area during active runs (not in sidebar)
- [ ] Runs tab shows run summary table only (no event timeline or JSON viewer)
- [ ] Config tab shows sub-tabs: Runtime, Model, Providers, Workspace Trust, Graph, Advanced
- [ ] Theia's status bar includes ARC segments: trust, runtime, mode, daemon, cost
- [ ] All ARC panels accessible via command palette (`Ctrl/Cmd+Shift+P` > "ARC: Open ...")
- [ ] Keyboard shortcuts work: `Ctrl/Cmd+;` focus chat, `Ctrl/Cmd+Shift+H` toggle Graph, `Ctrl/Cmd+Shift+U` toggle Runs
- [ ] ARC keyboard shortcuts only override Theia defaults when ARC sidebar has focus
- [ ] Panel layout (open/closed, sidebar width) persists across browser reload
- [ ] Empty state in Chat shows CTAs: "Ask a question", "Scan workspace", "Open sample"
- [ ] Graph widget closes or remains open after run completes (user-controlled, not auto-close)
- [ ] Sidebar is resizable via drag (Theia built-in), default 420px, min 320px, max 55vw
- [ ] Sidebar can be collapsed to icon-only mode (Theia built-in toggle)

### v0.1 Review/Apply (if shipped)

- [ ] Changes open in Theia's built-in diff editor (main area)
- [ ] Companion Review panel in sidebar shows file/hunk list and Approve/Reject/Edit First actions
- [ ] Selecting a hunk navigates the diff editor to the corresponding change
- [ ] Edit First opens the file in Theia's standard editor

### v0.1 Deferred (explicitly not in scope)

- [ ] Tasks as a separate panel (deferred to v0.2 with Phase/Loop views)
- [ ] Custom activity bar (deferred to v0.2 polish)
- [ ] Mobile/narrow window handling (deferred to v0.2)
- [ ] Drag-to-tab panel rearrange (deferred to v0.2)
- [ ] Custom Monaco diff viewer (use Theia's diff editor instead)
- [ ] Device and Frames panels (v0.2 HotLoop reserved)

### Integration Tests

- [ ] Browser app starts with Chat tab open in right sidebar
- [ ] Sending a message renders agent response in Chat transcript
- [ ] Starting a run opens Graph widget in main editor area
- [ ] Completing a run adds a row to Runs tab
- [ ] Opening Config tab shows all sub-tabs with correct forms
- [ ] Status bar shows correct ARC segments with correct states
- [ ] Command palette entries for all ARC panels work
- [ ] Keyboard shortcuts work and do not conflict with Theia when ARC is not focused
- [ ] Reloading the browser preserves panel layout
- [ ] Sidebar resize via drag works correctly
- [ ] Sidebar collapse/expand works correctly

---

## Reject / Do Not Build

### Rejected: Custom 3-column layout replacing Theia's editor area

**Why rejected:** The spec's §8.1 layout (activity bar + chat 60% + tasks sidebar) implicitly replaces Theia's editor area with ARC panels. This is wrong — users need the editor for code, diffs, and Graph visualization. Every competitor keeps the editor visible. Building a custom layout manager on top of Theia is expensive and fights the platform.

**Alternative:** Use Theia's right sidebar for ARC panels. Keep the editor area for code and Graph.

### Rejected: Separate ARC status bar

**Why rejected:** Theia already has a bottom status bar. Adding a second bar wastes 24px of vertical space and creates ambiguity. Theia's status bar API supports custom segments and clickable items.

**Alternative:** Contribute ARC segments to Theia's status bar.

### Rejected: Custom activity bar

**Why rejected:** Theia already has a left sidebar with view icons (Explorer, Search, SCM, etc.). Adding a separate 48px activity bar for ARC duplicates this chrome. VS Code Copilot integrates into the existing sidebar icon strip. JetBrains AI Assistant uses the tool window stripe.

**Alternative:** Register ARC panels as views in Theia's right sidebar. Add command palette entries as primary navigation. Activity bar icons can be added as v0.2 polish if needed.

### Rejected: Six panels for v0.1

**Why rejected:** Implementing Chat, Tasks, Graph, Runs, Review/Apply, and Config with coordinated layout is too much surface for v0.1. Tasks Step view is thin content (a list of steps). Review/Apply requires building a Monaco diff viewer that Theia already provides.

**Alternative:** Ship 4 panels: Chat, Graph, Runs, Config. Render task steps as inline chat cards. Use Theia's diff editor for review. Add Tasks as a separate panel in v0.2 when Phase and Loop views ship.

### Rejected: 40/60 Chat/Graph split in sidebar

**Why rejected:** At sidebar widths, a 40/60 split gives Chat ~168px and Graph ~252px (at 420px sidebar). This is unusable for both panels. Even at the maximum 55vw on a 1440px screen (792px sidebar), Chat gets 317px — barely readable.

**Alternative:** Graph opens in the main editor area. Chat stays at full sidebar width.

### Rejected: Custom Monaco diff viewer for Review/Apply

**Why rejected:** Theia already includes Monaco and a full diff editor with side-by-side, inline mode, hunk navigation, and editing support. Building a parallel diff viewer is expensive, duplicates platform functionality, and creates maintenance burden.

**Alternative:** Open Theia's diff editor for review. Add a companion sidebar panel for the file/hunk list and approval actions.

### Rejected: Mobile/narrow window handling in v0.1

**Why rejected:** Theia's browser application is not designed for mobile or narrow windows. Making ARC panels responsive requires making the entire Theia app responsive, which is out of scope for v0.1.

**Alternative:** Defer to v0.2. v0.1 targets desktop browser at >=720px.

### Rejected: Drag-to-tab panel rearrange in v0.1

**Why rejected:** Theia's tab bar drag-and-drop API has limited support for cross-container drag (sidebar to main area). Fixed tab positions match Cursor/Windsurf's approach and are sufficient for v0.1.

**Alternative:** Fixed sidebar tabs for v0.1. Drag rearrange as v0.2 polish.

### Deferred: Tasks as separate panel

**Why deferred:** Tasks Step view (v0.1) is a simple list of runtime steps, blockers, and current node. This renders well as inline cards in the Chat transcript (matching Cursor's agent steps feed). Phase and Loop views (v0.2) are richer and may justify a separate panel.

**When to revisit:** v0.2, when Phase view and Loop trace view are implemented.

### Deferred: HotLoop Device and Frames panels

**Why deferred:** Correctly scoped as v0.2 in the spec (§8.12). No action needed.
