# Graph Review

## Current ARC Spec

The ARC Studio UX Spec (§11) defines a Cytoscape.js-based graph visualiser for SwarmGraph topology. Key spec points:

**Canvas (§11.1):** Cytoscape.js with `dagre` default layout; alternatives `cose`, `breadthfirst`. Dotted grid background (1px dots, 24px spacing, 30% opacity). Minimap for graphs with >20 nodes.

**Nodes (§11.2):** Sized by type — queen 140×56, worker/agent 128×48, tool 112×44, decision diamond 96×64, HITL 128×52, terminal 88×40. Labels ellide after 18 chars. Inspector right dock shows ID, runtime, state, event count, last event, copy buttons.

**Edges (§11.3):** Directed arrows always on. Labels only on conditional/router edges. Width scales by message volume (1, 2, 3px). Active edge uses `graph.edge.active`.

**Live Overlay (§11.4):** Batched rendering on 100ms tick. Each tick renders latest state per node. Burst badge for >3 changes in one tick. Animation consistent regardless of event rate.

**Replay (§11.5):** Explicitly excluded from v0.1. No scrubber, time travel, event timeline, or replay keyboard shortcuts. Reserved for v0.3 audit explorer.

**CLI Inline Graph (§7.6, §11.6):** Box-drawing characters (`─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ → ↓`). Tree fallback below 80 columns. Labels truncate to 10 chars.

**Second-Terminal Graph (§7.7, §11.7):** Alt-screen mode via `arc-studio graph --attach <run-id>`. Keys: `i` inspector, `f` fit, `+/-` zoom, `space` pause, `q` close.

**GraphNode Component (§9):** TypeScript interface with `id`, `label`, `type` (queen/worker/agent/tool/decision/hitl/terminal/router/start/end), `runtime`, `state` (idle/running/waiting/done/failed), `badges`, `eventCount`. ARIA: `role=application`, spoken description `{label}, {type}, {runtime}, {state}, {event count} events`.

**Colour Tokens (§2.1):** Full palette for node types (`graph.node.queen`, `graph.node.worker`, `graph.node.tool`, `graph.node.decision`, `graph.node.hitl`, `graph.node.terminal`) and states (`graph.node.state.idle/running/waiting/done/failed`). Edge colours: `graph.edge.default`, `graph.edge.active`, `graph.edge.replay` (reserved).

**IDE Layout (§8.3):** Chat left 40%, Graph right 60%, Tasks overlay top-right. Graph expands automatically when a run emits `graph.node.state` or user selects `/graph`.

### Current Implementation Reality

The current codebase uses **custom SVG rendering**, NOT Cytoscape.js. Both `packages/arc-extension/src/browser/arc-workflow-graph-widget.tsx` and `theia-extensions/arc-workflows/src/browser/arc-workflow-graph-widget.tsx` implement:

- Simple BFS-based layered layout (not dagre)
- Static SVG rendering with hardcoded colours (not spec tokens)
- No live state overlay
- No minimap
- No node inspector
- No pan/zoom (fixed 800×500 SVG)
- No edge animation
- No CLI inline graph
- No second-terminal mode
- No burst badges
- No ARIA graph application role

The spec and implementation are completely misaligned on the rendering engine.

## Comparable Products / Research

### LangGraph Studio

| Feature | LangGraph Studio | ARC Studio v0.1 Spec |
|---|---|---|
| Graph visualization | Full interactive graph with node/edge rendering | Cytoscape.js (spec) / custom SVG (actual) |
| Graph/Chat modes | Two modes: Graph (full detail) and Chat (simplified) | Single graph panel; chat is separate |
| Time travel | Full checkpoint replay via `use-time-travel` | Explicitly excluded from v0.1 |
| Node inspection | Debug agent state at any checkpoint | Node inspector right dock (spec only) |
| Prompt iteration | Built-in prompt engineering integration | Not in v0.1 scope |
| Thread management | Manage threads, assistants, long-term memory | Session lifecycle (spec §7.14.1) |
| Run interaction | Run and interact with agent directly | Execute workflow, view live graph |
| Dataset experiments | Run experiments over datasets | Eval CLI (P4), not graph-integrated |
| Tracing integration | LangSmith tracing integrated into graph view | Advanced trace via CLI only in v0.1 |
| Graph editing | Read-only visualization | Read-only in v0.1 |
| Layout engine | Custom (appears to be ELK/dagre-based) | dagre (spec), BFS (actual) |
| Live execution | Real-time node state during runs | 100ms batched tick (spec) |

**What LangGraph Studio does better:**
- Time travel/checkpoint replay is their killer feature — jump to any state, modify, re-run from that point
- Graph + Chat mode toggle gives both detailed and simplified views
- Prompt iteration directly in the IDE
- Thread/assistant management integrated into the graph surface
- LangSmith tracing integration (click a node → see the trace)
- Dataset experiment runner

**What ARC Studio could do better:**
- Multi-runtime graph (not just LangGraph) — SwarmGraph, CrewAI, OpenAI Agents, etc.
- CLI inline graph for terminal-first workflows
- Second-terminal alt-screen graph for dual-monitor setups
- Queen/worker topology visualization (unique to SwarmGraph)
- HITL node states directly on graph
- Cost/token overlay on nodes

### Prefect

| Feature | Prefect | ARC Studio v0.1 |
|---|---|---|
| DAG visualization | Automatic dependency graph from flow execution | Manual graph from workflow detection |
| Real-time monitoring | Live flow run monitoring with state tracking | Live graph via 100ms tick (spec) |
| Timeline/Gantt | Built-in timeline view | Not in v0.1 |
| Logs | Per-task logs in UI | Advanced trace via CLI |
| State tracking | Automatic state management with recovery | Run status via SQLite index |
| Dynamic graphs | Supports dynamic runtime DAG generation | Static topology from detection |

### Dagster

| Feature | Dagster | ARC Studio v0.1 |
|---|---|---|
| Asset lineage | Full data lineage graph | No lineage concept |
| DAG visualization | Automatic asset dependency graph | Manual workflow graph |
| Run visualization | Per-run Gantt chart with step timing | Not in v0.1 |
| Asset health | Health status, freshness policies | Not applicable |
| Graph editing | Read-only | Read-only |

### Temporal

| Feature | Temporal | ARC Studio v0.1 |
|---|---|---|
| Workflow visibility | Event history, search, filtering | Run list with summary |
| Workflow graph | Limited — event timeline, not topology graph | Topology graph (spec) |
| Signal/query/cancel | Full workflow interaction | Cancel run (P1) |
| Reset/replay | Workflow reset to any point | No replay in v0.1 |

### Graph Library Comparison

| Feature | Cytoscape.js | React Flow (xyflow) | X6 (AntV) | Custom SVG |
|---|---|---|---|---|
| License | MIT | MIT | MIT | N/A |
| GitHub Stars | ~9.5K | ~36.5K | ~5.2K | N/A |
| Weekly Installs | ~600K | ~7.4M | ~100K | N/A |
| React-native | No (needs wrapper) | Yes (native React) | No (needs wrapper) | Yes |
| Layout engines | dagre, cose, breadthfirst, klay, elk | dagre, elkjs (plugins) | dagre, force, circular | Manual BFS only |
| Pan/zoom | Built-in | Built-in | Built-in | None (fixed SVG) |
| Minimap | Built-in | Built-in | Built-in | None |
| Custom nodes | Canvas/SVG elements | React components | HTML/SVG | SVG elements |
| Large graph perf | Good (virtualization) | Good (1000+ nodes) | Good | Poor (no virtualization) |
| Edge animation | Built-in | Built-in | Built-in | None |
| Node selection | Built-in | Built-in | Built-in | None |
| Keyboard nav | Built-in | Built-in | Built-in | None |
| Accessibility | Limited | ARIA support | Limited | None |
| Bundle size | ~200KB | ~150KB | ~300KB | ~0KB (inline) |
| Maintenance | Active | Very active | Active | N/A |
| Community | Large | Very large | Medium | N/A |
| TypeScript | Full types | Full types | Full types | Manual |
| Theia compatibility | Needs wrapper | Native React component | Needs wrapper | Already works |

**Key insight:** React Flow is the dominant choice for React-based node editors (36.5K stars, 7.4M weekly installs). It has native React components, built-in minimap/pan/zoom/controls, dagre/elkjs layout plugins, and excellent TypeScript support. The spec chose Cytoscape.js, but the implementation uses neither.

## Gaps

1. **Rendering engine mismatch:** Spec says Cytoscape.js; code uses custom SVG with BFS layout. Neither matches the spec.

2. **No live state overlay:** The spec defines a 100ms batched tick for live graph state (§11.4). Current implementation is completely static — no SSE wiring, no state overlay, no burst badges.

3. **No pan/zoom/fit:** Fixed 800×500 SVG canvas. No viewport controls, no fit-to-view, no minimap.

4. **No node inspector:** Spec defines a right-dock inspector showing ID, runtime, state, event count, last event, copy buttons (§11.2). Not implemented.

5. **No CLI inline graph:** Spec defines `/graph` inline view (§7.6) with box-drawing characters and tree fallback. Not implemented.

6. **No second-terminal graph:** Spec defines alt-screen mode (§7.7) with `arc-studio graph --attach <run-id>`. Not implemented.

7. **No edge animation:** Spec defines edge activation colour-fill animation (§6.2). Current edges are static lines.

8. **No ARIA accessibility:** Spec requires `role=application` and spoken descriptions (§9, §14). Current SVG has no ARIA attributes.

9. **No spec colour tokens:** Current code uses hardcoded hex colours (`#1a472a`, `#4fc3f7`, etc.) instead of spec tokens (`graph.node.queen`, `graph.node.state.running`, etc.).

10. **No graph density handling:** No virtualization, no collapse/expand, no subgraph grouping. Will break at ~50 nodes with current SVG approach.

11. **No graph export:** No PNG/SVG/JSON export capability.

12. **No multi-workflow graph switching:** Current implementation has a dropdown but only shows one workflow at a time with no graph comparison.

13. **No runtime-specific graph rendering:** All nodes render identically regardless of runtime. Spec defines different badges for LangGraph `(coalesced)`, different handling per adapter (§11.8).

14. **No graph-toolbar:** Spec implies a toolbar with layout selection, fit, export (§8.3 panel specs). Current implementation only has workflow selector and refresh button.

15. **No graph-empty/loading/error states:** Current implementation has basic empty/error text but no spec-compliant empty states with CTAs.

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Switch to React Flow** | 36.5K stars, 7.4M weekly installs, native React, built-in pan/zoom/minimap/controls, dagre plugin, better Theia integration. Cytoscape.js requires a wrapper and has less React ecosystem support. | v0.1 | Low — React Flow is MIT, well-documented, and the migration is a rewrite anyway since current code is custom SVG | §11.1: change "Cytoscape.js" to "React Flow (@xyflow/react)"; §16: change `arc-cytoscape-style.json` to `arc-react-flow-style.json` |
| **Implement live state overlay** | Core product differentiator — seeing SwarmGraph topology animate during execution is the primary value of the graph panel. Without live state, the graph is a static diagram. | v0.1 | Medium — requires SSE event broker (P1a) wiring to frontend; batch tick logic is straightforward | No spec edits needed; §11.4 already defines the behavior |
| **Add node inspector panel** | Users need to inspect node details (state, events, runtime) without leaving the graph. LangGraph Studio has this. Spec already defines it. | v0.1 | Low — side panel with node data display | No spec edits needed; §11.2 already defines inspector |
| **Implement CLI inline graph** | Terminal-first users need graph visibility. Box-drawing graph is a key CLI differentiator vs competitors. | v0.1 | Low — Rich/Textual TUI rendering; tree fallback already spec'd | No spec edits needed; §7.6, §11.6 already define behavior |
| **Defer second-terminal graph** | Alt-screen mode is useful but requires child pty management and is a secondary surface. CLI inline graph covers the primary terminal use case. | v0.2 | N/A | §7.7: mark as "reserved v0.2" |
| **Add graph export (PNG/SVG)** | Users need to share workflow topology. Simple export via React Flow's built-in image export. | v0.1 | Low — React Flow has `toPng`/`toSvg` utilities | §11: add export subsection |
| **Add collapse/expand for subgraphs** | Handles >50 nodes by grouping queen/worker clusters. Essential for real SwarmGraph topologies. | v0.2 | Medium — requires subgraph data model and React Flow group nodes | §11.2: add subgraph/group node type |
| **Implement edge animation** | Visual feedback for active edges during live execution. Spec defines 420ms colour-fill animation. | v0.1 | Low — React Flow supports animated edges natively | No spec edits needed; §6.2 already defines animation |
| **Add graph density modes** | Compact/comfortable/spacious density matching spec §5.2. Affects node sizing and spacing. | v0.2 | Low — React Flow node sizing via props | §11.2: add density mode node sizes |
| **Implement ARIA accessibility** | WCAG AA compliance. Spec defines `role=application` and spoken descriptions. | v0.1 | Low — React Flow has built-in ARIA support; add node labels | No spec edits needed; §9, §14 already define ARIA |
| **Add runtime-specific rendering** | LangGraph nodes show `(coalesced)` badge; SwarmGraph shows full detail. Spec §11.8 defines per-adapter behavior. | v0.1 | Low — conditional rendering based on runtime field | No spec edits needed; §11.8 already defines behavior |
| **Add minimap** | Essential for >20 node graphs. React Flow has built-in MiniMap component. | v0.1 | Low — `<MiniMap />` is a built-in React Flow component | No spec edits needed; §11.1 already requires minimap |
| **Defer graph editing** | Read-only graph is correct for v0.1. Editing would require bidirectional sync with workflow source code, which is complex and error-prone. | v0.3+ | N/A | §11: add explicit "read-only in v0.1" note |
| **Add virtualization for >100 nodes** | React Flow handles 1000+ nodes with virtualization. Custom SVG will fail at ~50 nodes. | v0.1 | Low — React Flow handles this automatically | §11.1: add performance note |
| **Add graph comparison mode** | Side-by-side graph comparison for different runs or workflows. Useful for eval and debugging. | v0.3 | Medium — requires dual canvas and comparison data model | New section in §11 |

## Recommended Decisions

1. **Use React Flow, not Cytoscape.js.** React Flow is the dominant React graph library (36.5K stars vs ~9.5K for Cytoscape), has native React components, built-in minimap/pan/zoom, dagre layout plugin, and better TypeScript support. The current implementation already uses SVG-in-React, so React Flow is a natural evolution. Cytoscape.js would require a wrapper component and has a less active React ecosystem.

2. **Keep graph read-only in v0.1.** Editing workflow graphs requires bidirectional sync with source code (Python files), which is complex and error-prone. LangGraph Studio is also read-only. Focus on visualization quality first.

3. **Live state overlay is v0.1 critical.** The graph without live state is a static diagram — not a differentiator. The 100ms batched tick from §11.4 is the minimum viable live experience. This depends on the P1a event broker being wired to the frontend.

4. **Defer second-terminal graph to v0.2.** The CLI inline graph (§7.6) covers the primary terminal use case. Alt-screen mode adds child pty complexity that is not v0.1-critical.

5. **Handle >100 nodes via React Flow virtualization + subgraph collapse.** React Flow handles 1000+ nodes natively. For dense graphs, add subgraph collapse (queen/worker clusters) in v0.2. This avoids the need for custom virtualization logic.

6. **Use dagre layout via `dagre` + `@xyflow/react` plugin.** Dagre is the spec default and works well for DAG-like SwarmGraph topologies. React Flow has a well-maintained dagre layout example. Keep `elkjs` as an alternative for complex graphs.

7. **No replay in v0.** Confirmed by spec §11.5. Replay is reserved for v0.3 audit explorer. This keeps v0.1 scope tight.

## Specific Spec Edits

- **§11.1 Canvas:** Change "IDE uses Cytoscape.js" to "IDE uses React Flow (@xyflow/react). Default layout via `dagre` plugin; alternatives `elkjs`, `breadthfirst`." Change "Background uses dotted grid" to "Background uses dotted grid (React Flow `<Background variant='dots' />`)." Change "Minimap: yes for graphs with >20 nodes" to "Minimap via React Flow `<MiniMap />` component; enabled for graphs with >20 nodes."

- **§11.2 Nodes:** Add "Subgraph/group nodes: queen/worker clusters can be collapsed into group nodes in v0.2." Add "Node sizing adjusts per density mode (§5.2): compact reduces by 15%, spacious increases by 15%."

- **§11.3 Edges:** Add "Edge animation: active edges use React Flow animated edge type with 420ms colour-fill from source to target (§6.2)."

- **§11.5 Replay:** Add explicit statement: "Graph replay, time travel, checkpoint scrubber, and event timeline are reserved for v0.3 audit explorer. No replay UI ships in v0.1 or v0.2."

- **§7.7 Second-Terminal Graph:** Change header to "§7.7 `/graph` Second-Terminal View (reserved v0.2)." Add "Alt-screen mode deferred to v0.2. CLI inline graph (§7.6) covers the primary terminal use case in v0.1."

- **§8.3 Graph-Active Workspace:** Add "Components: `GraphCanvas` (React Flow), `GraphToolbar`, `NodeInspector`, `TasksOverlay`, `MiniMap`."

- **§9 GraphNode:** Add `subgraphId?: string` field to `GraphNodeData` for future collapse/expand support. Add `group?: boolean` field for group nodes.

- **§16 Assets:** Change `arc-cytoscape-style.json` to `arc-react-flow-style.json` with description "React Flow node/edge style overrides and theme tokens."

- **§11.8 Honest Scope Per Adapter:** Add "AG2 and LlamaIndex: no graph in default UI (detection/export only). LM Arena: not shown."

- **Add §11.10 Graph Export:** "Graph can be exported as PNG or SVG via React Flow's built-in image export. Export action available in graph toolbar. Exported image includes current viewport, node states, and legend."

- **Add §11.11 Performance:** "React Flow handles graphs up to 1000+ nodes via virtualization. For graphs >100 nodes, subgraph collapse (v0.2) reduces visual complexity. Layout computation uses dagre with O(n log n) performance. Minimap is disabled below 360px panel width."

## Acceptance Criteria

### v0.1 Graph Visualizer

- [ ] React Flow (@xyflow/react) installed and rendering workflow graph
- [ ] Dagre layout produces correct layered topology from workflow nodes/edges
- [ ] Node types render with spec colours: queen (purple), worker (blue), tool (orange), decision (yellow), HITL (red), terminal (green)
- [ ] Node labels ellide after 18 characters
- [ ] Directed arrows on all edges; dashed arrows on conditional edges
- [ ] Pan, zoom, and fit-to-view work via React Flow controls
- [ ] Minimap appears for graphs with >20 nodes
- [ ] Node inspector panel opens on node click, showing ID, runtime, state, event count, last event
- [ ] Graph toolbar with layout selector, fit button, export button
- [ ] Empty state shows "No graph yet. Scan workspace or run a graph-shaped workflow." with CTAs
- [ ] Loading state shows "Extracting workflow graph..." skeleton
- [ ] Error state shows "Graph render failed" with retry button
- [ ] ARIA: graph canvas has `role=application`; nodes announce `{label}, {type}, {runtime}, {state}`
- [ ] Graph export (PNG/SVG) works from toolbar
- [ ] Multi-workflow dropdown switches between detected workflows
- [ ] Runtime-specific rendering: LangGraph nodes show `(coalesced)` badge
- [ ] Colour tokens from §2.1 used consistently (not hardcoded hex)
- [ ] Reduced motion: all transitions use instant; running state uses static indicator

### v0.1 Live Graph State

- [ ] Live graph updates during workflow execution via SSE event broker
- [ ] Node state changes render (idle → running → done/failed) with spec colours
- [ ] Running node shows pulse animation (1.2s period, opacity .55→1, scale 1→1.035)
- [ ] Active edges show colour-fill animation (420ms)
- [ ] State updates batched at 100ms tick
- [ ] Burst badge shows count when node has >3 changes in one tick
- [ ] Graph auto-fits on first render during live run

### v0.1 CLI Inline Graph

- [ ] `/graph` command shows inline graph with box-drawing characters
- [ ] Tree fallback renders below 80 columns
- [ ] Labels truncate to 10 characters at 80 columns
- [ ] Colour overlay uses ANSI palette mapping to spec tokens
- [ ] Legend shows running/done/waiting/failed glyphs

### v0.1 Deferred Items

- [ ] No replay scrubber in graph UI
- [ ] No time travel or checkpoint navigation
- [ ] No event timeline in graph panel
- [ ] No graph editing (read-only)
- [ ] No second-terminal alt-screen graph
- [ ] No subgraph collapse (v0.2)

## Reject / Do Not Build

| Idea | Reason |
|---|---|
| **Cytoscape.js** | React Flow is better suited: native React, larger community (36.5K vs 9.5K stars), built-in minimap/pan/zoom, dagre plugin, better TypeScript. Switching to Cytoscape would require a wrapper and lose React component ergonomics. |
| **Editable graph in v0.1** | Bidirectional sync with Python source code is complex and error-prone. LangGraph Studio is read-only. Focus on visualization quality first. Editing can be v0.3+ after the runtime/protocol is stable. |
| **Second-terminal graph in v0.1** | Alt-screen mode requires child pty management and is a secondary surface. CLI inline graph covers the primary terminal use case. Defer to v0.2. |
| **X6 (AntV)** | Smaller community (~5.2K stars), less React-native, larger bundle. No advantage over React Flow for this use case. |
| **Custom SVG (current approach)** | No pan/zoom, no minimap, no virtualization, no accessibility, no edge animation, hardcoded colours, fixed canvas size. Will fail at ~50 nodes. Must be replaced. |
| **Graph replay in v0.1** | Explicitly excluded by spec §11.5. Reserved for v0.3 audit explorer. Adding replay now would expand v0.1 scope significantly and conflict with the trace UI removal decision. |
| **3D graph visualization** | Gimmicky, poor accessibility, no practical benefit for SwarmGraph topology. All competitors use 2D. |
| **Force-directed layout as default** | Dagre produces cleaner layered layouts for DAG-like SwarmGraph topologies. Force-directed is unpredictable and harder to read for workflow graphs. Keep as alternative only. |
| **Graph comparison mode in v0.1** | Requires dual canvas and comparison data model. Useful for eval but not v0.1-critical. Defer to v0.3. |
| **No-code workflow builder** | Explicitly deferred in IMPLEMENTATION_PLAN.md §Do Not Build Yet. Would distract from high-assurance cockpit work. |
| **Graph-as-code sync** | Bidirectional graph↔Python sync is complex and error-prone. The graph is a visualization of the workflow, not the source of truth. Keep it read-only. |
| **Graph density auto-detection** | Over-engineering. Let users choose density mode (§5.2) or use subgraph collapse (v0.2). |
| **WebGL/Canvas rendering** | Overkill for <1000 node graphs. React Flow's SVG rendering is sufficient. WebGL adds complexity and reduces accessibility. |
