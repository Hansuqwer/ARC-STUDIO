# HotLoop Reservations Review

## Current ARC Spec

HotLoop is a v0.2 reserved runtime in ARC Studio for UI iteration with live screenshots and visual diffs. The spec reserves panel slots, component stubs, event names, and a runtime manifest — but ships zero implementation in v0.1.

**What is reserved today (from ARC_STUDIO_UX_SPEC.md):**

| Reservation | Section | Detail |
|---|---|---|
| Device panel slot | §0.5, §8.12 | Live screenshots per target (Flutter/React/Expo). Opens by default when HotLoop is active. |
| Frames panel slot | §0.5, §8.12 | Scrubbable visual diff timeline. Opens beside Device when HotLoop is active. |
| Loop trace view | §8.2 (Tasks panel) | Observation loop ticks, target/device state, frame references. Reserved v0.2 in Tasks panel. |
| Component stubs | §9 (line 1307) | `DeviceThumbnail`, `FrameThumbnail`, `LoopTraceTick`, `RollbackButton` — all deferred. |
| Runtime manifest | Appendix A (line 1663) | Full HotLoop manifest with `id: hotloop`, capabilities, events, panel slots. |
| Event names | Appendix A (line 1686) | `device.frame.captured`, `device.target.changed`, `loop.tick.started`, `loop.tick.completed`, `frame.diff.available` |
| Router suggestion card | §7.16 | "This looks like UI work. HotLoop iterates faster here. Switch?" |
| Handoff transition | §7.17, Appendix B | `swarmgraph → hotloop` handoff with goal, state, constraints, references, audit links. |
| Slot preferences | Appendix A | `open_by_default: ["Chat", "Tasks", "Device", "Frames", "Runs"]`, `closed_by_default: ["Graph", "Review", "Config"]` |
| Capability flags | Appendix A | `inspect: true`, `run: true`, `graph: false`, `device: true`, `frames: true` |
| Cost signal | Appendix A | `paid_provider_required: true` |
| Eligibility signals | Appendix A | `files_match: ["package.json", "pubspec.yaml", "app.json"]`, verbs: `["iterate", "preview", "fix UI", "hot reload"]` |
| Phase view in /tasks | §7.15 | Phase cards showing HotLoop as "reserved v0.2" in plan view. |

**What is NOT reserved or specified:**

- No screenshot capture mechanism (how frames are captured)
- No device/emulator/simulator lifecycle management
- No connection protocol between HotLoop and target app
- No visual diff algorithm specification
- No frame storage or retention policy
- No loop tick semantics (what constitutes a tick, max iterations, stop conditions)
- No target platform list beyond hints (React Native, Flutter, Expo)
- No HotLoop-specific CLI commands
- No HotLoop-specific Python backend modules
- No event payload schemas (only event names)
- No frame metadata schema (resolution, timestamp, target info)
- No rollback semantics (what is rolled back, how checkpoints work)
- No integration path with existing trace/audit infrastructure

**Key design decisions already made:**

1. HotLoop is a runtime, not a tool or mode — it appears in the runtime picker alongside SwarmGraph, LangGraph, etc.
2. HotLoop replaces Graph with Device + Frames as the primary visual surface.
3. HotLoop requires a paid provider (vision model for screenshot analysis).
4. HotLoop is eligible when UI project files are detected (`package.json`, `pubspec.yaml`, `app.json`).
5. The router can suggest switching to HotLoop for UI work.
6. Handoff from SwarmGraph to HotLoop carries state across phase boundaries.

## Comparable Products / Research

| Feature | Expo DevTools | Flutter DevTools | React DevTools | React Native Debugger | Chrome DevTools | Storybook | Playwright |
|---|---|---|---|---|---|---|---|
| **Device preview** | Web-based device frame, responsive preview | No device frame; widget tree | No device frame; component tree | No device frame; element inspector | Device mode with frame, DPR, throttling | Canvas with viewport presets | Viewport emulation via `page.setViewportSize()` |
| **Live screenshot** | No | No | No | No | Full-page screenshot, node screenshot | Screenshot via test runner | `page.screenshot()`, full-page, element, mask regions |
| **Visual diff** | No | No | No | No | No | Visual regression via Chromatic/addons | `expect(page).toHaveScreenshot()`, pixel diff, threshold |
| **Element inspector** | Yes (element tree) | Yes (widget inspector, select widget mode) | Yes (component tree, props/state) | Yes (React + RN element tree) | Yes (DOM tree, styles, computed) | Yes (controls/args panel) | Yes (locator-based, `page.locator()`) |
| **Frame timeline** | No | Yes (frame rendering chart, raster/build timeline) | No | No | Yes (Performance panel, FPS, frames) | No | No (trace-based via trace viewer) |
| **Performance overlay** | Metro bundler logs | Yes (performance overlay, jank detection) | No (React Profiler separate) | No | Yes (Performance, Memory, Lighthouse) | No | Yes (trace, CPU throttling) |
| **Hot reload** | Yes (Fast Refresh) | Yes (hot reload, hot restart) | Yes (Fast Refresh via bundler) | Yes (via Metro) | Yes (live reload, HMR) | Yes (hot module replacement) | N/A (test runner) |
| **Network inspection** | Metro logs only | Yes (network tab) | No | Yes (network tab) | Yes (network panel, HAR) | No | Yes (`page.route()`, network events) |
| **State inspection** | Limited | Yes (state, provider, riverpod) | Yes (props, state, hooks, context) | Yes (Redux, props, state) | Yes (DOM state, console, storage) | Yes (args/controls) | Yes (evaluate, `page.evaluate()`) |
| **Console/REPL** | Metro terminal | Yes (logging, debugger) | Yes (console integration) | Yes (Chrome console) | Yes (full console) | No | Yes (`page.evaluate()`) |
| **Replay/time-travel** | No | No | No | Redux DevTools time-travel | No | No | Trace viewer (step-through) |
| **Multi-device** | No | No | No | No | No | Yes (parallel stories) | Yes (parallel browsers/contexts) |
| **Visual regression CI** | No | No | No | No | No | Yes (Chromatic, Storyshots) | Yes (native screenshot comparison) |
| **Agent/LLM integration** | No | No | No | No | No | No | No |

### Key observations from comparable products:

1. **No product combines live screenshots + visual diffs + AI agent iteration.** HotLoop's concept is novel. Expo/Flutter/React DevTools focus on inspection and debugging, not AI-driven UI iteration.

2. **Screenshot capture is well-solved.** Playwright's `page.screenshot()` and Chrome DevTools' capture APIs are mature. For mobile targets, React Native's `react-native-view-shot` or platform-native screenshot APIs exist. The capture mechanism is not the hard part.

3. **Visual diff is well-solved.** Playwright uses pixelmatch with threshold. Storybook uses Chromatic (cloud) or Storyshots (local). The diff algorithm is commodity; the value is in the agent loop that acts on diffs.

4. **Frame timelines exist but are performance-focused.** Flutter DevTools' frame chart shows raster/build time per frame. Chrome DevTools' Performance panel shows FPS. Neither is designed for visual iteration loops. HotLoop's frame timeline is a visual diff timeline, not a performance timeline — different purpose.

5. **Device preview is mostly static.** Chrome DevTools' device mode provides a frame overlay. Expo DevTools renders in a web viewport. None provide live device screenshots from a real device/emulator. HotLoop's Device panel implies real screenshot capture from a running target, which is more complex than static frame overlays.

6. **No product has "loop tick" semantics.** The concept of an observation/action loop where an agent iterates on UI, captures a frame, diffs it, and decides the next action is unique to HotLoop. This is the core differentiator and the part that needs the most careful design.

7. **Rollback is rare.** Redux DevTools has time-travel. Playwright has trace replay. Neither rolls back UI state on a running app. HotLoop's `RollbackButton` implies checkpointing UI state and reverting — this is non-trivial and needs a clear mechanism (git stash? hot reload to prior state? snapshot restore?).

8. **None of these tools are agent-aware.** HotLoop is fundamentally an agent runtime surface, not a developer debugging tool. This distinction should drive all reservation decisions.

## Gaps

### Critical gaps (block v0.2 design)

1. **No event payload schemas.** Event names are reserved (`device.frame.captured`, `loop.tick.started`, etc.) but no payload shape is defined. Without payload contracts, the frontend cannot render Device/Frames panels even as stubs. What fields does `device.frame.captured` carry? `frameUrl`? `base64`? `width`/`height`? `targetId`? `timestamp`?

2. **No screenshot capture mechanism specified.** The spec says "live screenshots" but does not specify how screenshots are captured, from what target, or through what protocol. Is HotLoop capturing from:
   - A local emulator/simulator?
   - A real device over ADB/IDB?
   - A web preview in an iframe?
   - A headless browser (Playwright/Puppeteer)?
   - The target app's own screenshot API?
   This decision fundamentally constrains what HotLoop can do.

3. **No target lifecycle model.** How does HotLoop start/stop/restart the target app? Does it manage the emulator? Does it require the app to already be running? The spec is silent.

4. **No loop semantics.** What is a "tick"? Is it one agent observation → action → screenshot cycle? What stops the loop? Max iterations? Convergence detection? User interrupt? Cost ceiling? Without loop semantics, `LoopTraceTick` cannot be designed.

5. **No frame storage model.** Are frames stored on disk? In the trace store? In a separate frame cache? How long are they retained? Are they referenced by URL or embedded as base64? The Frames panel needs to know this.

6. **No rollback mechanism.** `RollbackButton` is reserved but the spec does not define what rollback means. Git revert? Hot reload to prior bundle? State snapshot restore? This is a critical design decision.

7. **No connection to trace/audit infrastructure.** HotLoop runs produce traces. Do frames attach to trace events? Is there an audit trail for loop decisions? The spec reserves events but does not connect them to ARC's existing trace store or audit chain.

### Significant gaps (weaken reservations)

8. **`device.target.changed` is underspecified.** What triggers this event? User switching targets? Agent changing target? Device disconnect? What payload does it carry?

9. **No frame diff payload schema.** `frame.diff.available` — does it carry the diff image? Pixel diff metrics? A similarity score? Regions of change? The Frames panel needs this to render meaningfully.

10. **No target platform matrix.** The manifest hints at React Native (`package.json`), Flutter (`pubspec.yaml`), and Expo (`app.json`), but there is no platform capability matrix. Can HotLoop work with web apps? Desktop apps? Native iOS/Android? The scope is unclear.

11. **No cost model detail.** `paid_provider_required: true` is set, but there is no cost estimate per tick, no cost ceiling per loop, no cost visibility in the Device/Frames panels. Given that HotLoop uses vision models (expensive), cost transparency is critical.

12. **No panel layout spec beyond "Device + Frames".** How are Device and Frames arranged? Side by side? Stacked? Tabs? What are their relative sizes? How do they interact with Chat and Tasks panels?

13. **No empty/loading/error states for Device/Frames panels.** Every other panel in the spec has state tables (§8.5 Runs, §8.3 Graph). Device and Frames have none.

14. **No keyboard shortcuts for HotLoop-specific actions.** Rollback? Next frame? Previous frame? Pause loop? Resume? The keyboard shortcut audit (§8.13) has no HotLoop entries.

15. **No accessibility considerations for visual panels.** Device and Frames are inherently visual. How do screen readers interact with them? What are the accessible labels for frame thumbnails? What is the alt text for screenshots?

### Minor gaps (nice to have)

16. **No HotLoop-specific CLI commands.** Other runtimes have CLI surface (`arc runs *`, `arc hitl *`). HotLoop has none. Should there be `arc hotloop status`? `arc hotloop frames`? `arc hotloop pause`?

17. **No HotLoop icon/glyph beyond `HL`.** The manifest specifies `glyph: HL` and `badge_tone: info`, but there is no Lucide icon mapping (§4.1) or CLI Unicode equivalent (§4.2).

18. **No HotLoop-specific status bar segments.** When HotLoop is active, what does the status bar show? Loop iteration count? Current target? Frame count? Cost so far?

19. **No HotLoop integration with Runs panel.** Does a HotLoop run appear in the Runs list? What summary fields are shown? `failureFrame` is in the manifest's `summary_fields` — what does that render as?

20. **No HotLoop-specific motion/animation spec.** §6 defines animations for running nodes, edge activation, streaming tokens. What animates during a HotLoop tick? Frame capture flash? Diff highlight? Loop progress?

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Define event payload schemas for all 5 reserved events** | Frontend cannot render panels without knowing what data events carry. Event names alone are insufficient. | v0.1 (reserve schemas), v0.2 (implement) | Low — schemas are additive and versioned per ADR-004 | Appendix A: add YAML payload examples for each event; §8.12: reference payload schemas |
| **Specify screenshot capture mechanism** | "Live screenshots" is a product claim, not a technical spec. The capture mechanism determines platform support, latency, and feasibility. | v0.1 (document approach), v0.2 (implement) | Medium — wrong mechanism choice could require rework | New §8.12.1: capture mechanism (target types, protocols, requirements); Appendix A: add `capture_modes` to manifest |
| **Define loop tick semantics** | Without loop semantics, `LoopTraceTick` and `loop.tick.*` events are meaningless. The loop is HotLoop's core differentiator. | v0.1 (reserve semantics), v0.2 (implement) | Medium — loop design affects cost, UX, and agent architecture | New §8.12.2: loop lifecycle (start, tick, converge, stop, pause); Appendix A: add `loop_config` to manifest |
| **Define frame storage and retention** | Frames must be stored somewhere. The trace store (JSONL) is not designed for binary data. A frame cache needs a lifecycle. | v0.1 (document approach), v0.2 (implement) | Low — storage design is internal to backend | New section in Appendix A: `frame_storage` spec; reference ADR-003 for storage strategy |
| **Define rollback mechanism** | `RollbackButton` is reserved but meaningless without a rollback model. This is a user-facing action that needs clear semantics. | v0.1 (document approach), v0.2 (implement) | Medium — rollback mechanism affects target app architecture | §9: expand `RollbackButton` stub with rollback model; Appendix A: add `rollback_modes` to capabilities |
| **Add Device/Frames panel layout spec** | Panel arrangement affects the entire IDE layout. "Opens beside Device" is not a layout spec. | v0.1 | Low — layout decisions are cheap now, expensive later | §8.12: add layout diagram (like §8.3 Graph-Active Workspace); §8.8: add HotLoop sidebar collapse behavior |
| **Add empty/loading/error/offline states for Device/Frames** | Every panel needs state tables. Device and Frames are the only panels without them. | v0.1 | Low | §8.12: add state tables matching §8.3/§8.5 pattern |
| **Add HotLoop to keyboard shortcut audit** | HotLoop actions (rollback, frame navigation, pause/resume) need keyboard bindings. | v0.1 | Low | §8.13: add HotLoop-specific shortcuts |
| **Add cost visibility to HotLoop surface** | `paid_provider_required: true` means every tick costs money. Users need per-tick cost, cumulative cost, and cost ceiling visibility. | v0.1 (reserve), v0.2 (implement) | Low | §8.12: add cost display requirements; Appendix A: add `cost_per_tick_estimate` to manifest |
| **Connect HotLoop events to trace/audit infrastructure** | HotLoop runs should appear in Runs panel and be traceable. Events should reference trace records. | v0.1 (reserve refs), v0.2 (implement) | Medium — requires event schema alignment | Appendix A: add `trace_ref` and `audit_ref` to event payloads; §8.5: add HotLoop run summary rendering |
| **Define target platform capability matrix** | The manifest hints at platforms but does not define what HotLoop actually supports. Scope clarity prevents overclaim. | v0.1 | Low | Appendix A: add `supported_targets` matrix with support levels (full/partial/stub) |
| **Add HotLoop CLI command reservations** | Other runtimes have CLI surface. HotLoop should reserve command names even if not implemented. | v0.1 | Low | New §7.18: HotLoop CLI reservations (`arc hotloop status/frames/pause/resume/rollback`) |
| **Add HotLoop icon/glyph mapping** | Consistency with other runtimes requires icon mapping in §4.1 and §4.2. | v0.1 | Low | §4.1: add HotLoop Lucide icon; §4.2: add HotLoop Unicode/ASCII equivalents |
| **Add HotLoop status bar segments** | Status bar should show HotLoop-specific state when active. | v0.1 (reserve), v0.2 (implement) | Low | §7.14: add HotLoop status bar segments (target, iteration, frames, cost) |
| **Add accessibility requirements for Device/Frames** | Visual panels must have accessible alternatives. | v0.1 | Low | §14: add HotLoop accessibility requirements (alt text, ARIA labels, screen reader announcements) |
| **Add HotLoop motion/animation spec** | Loop ticks and frame captures need visual feedback. | v0.1 (reserve), v0.2 (implement) | Low | §6.2: add HotLoop-specific animations (frame capture flash, diff highlight, loop progress) |

## Recommended Decisions

### Lock for v0.1 (reservations only)

1. **Keep current panel reservations (Device, Frames) as-is.** They are minimal and correct. No expansion needed.

2. **Reserve event payload schemas (not just names).** Add minimal payload shapes to Appendix A for all 5 events. Mark them `reserved_v0_2: true` and `schema_version: 1`. This gives the frontend a contract to code against without requiring implementation.

3. **Reserve loop tick semantics.** Document the loop lifecycle in §8.12: `start → observe → act → capture → diff → decide → (repeat or stop)`. Define stop conditions: max iterations, cost ceiling, user interrupt, convergence detection. Keep it to one paragraph — enough to guide v0.2 design, not enough to constrain implementation.

4. **Reserve frame storage approach.** Document that frames are stored in a workspace-local frame cache (not in JSONL traces), referenced by frame ID in events. JSONL traces store frame references, not binary data. This aligns with ADR-003 (JSONL stays lean).

5. **Reserve rollback model.** Document that rollback uses the target app's native hot-reload or git-based revert mechanism. HotLoop does not implement its own state snapshot system. This keeps HotLoop thin and avoids reinventing checkpoint management.

6. **Add empty/loading/error state tables for Device/Frames.** Match the pattern from §8.3 and §8.5. This costs nothing and prevents ambiguity.

7. **Add HotLoop to keyboard shortcut audit.** Reserve 3-4 shortcuts: `Ctrl/Cmd+Shift+D` (focus Device), `Ctrl/Cmd+Shift+F` (focus Frames), `Ctrl/Cmd+Shift+R` (rollback), `Space` (pause/resume loop when focused).

8. **Add target platform matrix to manifest.** Be honest about scope:
   - React Native (Expo): planned full support
   - React Native (bare): planned partial support
   - Flutter: planned partial support
   - Web (Next.js/Vite): deferred
   - Desktop: deferred

9. **Reserve HotLoop CLI command names.** Add `arc hotloop status`, `arc hotloop frames`, `arc hotloop pause`, `arc hotloop resume`, `arc hotloop rollback` to §7 as reserved commands. No implementation, just name reservations.

10. **Do NOT expand v0.1 scope.** No implementation, no backend modules, no frontend components beyond stubs. Reservations only.

### Defer to v0.2

11. **Screenshot capture mechanism implementation.** The v0.1 spec should document the intended approach but not commit to a specific mechanism. The capture mechanism depends on target platform and should be designed during v0.2 implementation.

12. **Visual diff algorithm.** Playwright's pixelmatch approach is a good default, but the diff implementation should be chosen during v0.2 based on actual target platforms and screenshot formats.

13. **Loop agent architecture.** How the agent observes, decides, and acts is a v0.2 design problem. v0.1 should reserve the event flow but not specify the agent model.

14. **Cost estimation per tick.** Cost depends on the vision model used and screenshot size. Reserve the cost display UI but do not commit to specific cost estimates until v0.2 testing.

15. **Rollback implementation.** The rollback mechanism depends on the target platform's hot-reload capabilities. Reserve the concept but defer implementation.

### Explicitly reject

16. **Do NOT make HotLoop a general-purpose visual regression tool.** HotLoop is an agent runtime surface, not a replacement for Playwright/Chromatic. Visual regression CI is out of scope.

17. **Do NOT make HotLoop a device farm manager.** HotLoop works with a single local target (emulator/simulator/device). Multi-device management is out of scope.

18. **Do NOT make HotLoop a performance profiler.** Frame timelines are for visual iteration, not performance analysis. Flutter/Chrome DevTools already do performance profiling well.

19. **Do NOT make HotLoop work without a vision model.** The loop requires visual understanding. If no vision model is available, HotLoop should be disabled, not degraded to a non-visual mode.

20. **Do NOT embed screenshots in JSONL traces.** Binary data in JSONL would bloat trace files and break the storage model. Frames go in a separate cache; traces reference them.

## Specific Spec Edits

### §0.5 "Out Of Scope For v0.1" (line 37)
**Current:** `HotLoop | Runtime, Device panel, Frames panel, loop trace, frame diffs deferred to v0.2.`
**Edit:** `HotLoop | Runtime, Device panel, Frames panel, loop trace, frame diffs, screenshot capture, target lifecycle, loop agent deferred to v0.2. Event payload schemas and loop semantics reserved in v0.1 protocol.`

### §0.5 "Reserved In v0.1 Protocol" (lines 45-48)
**Current:**
```
| Device panel slot | v0.2 HotLoop screenshot/device surface. |
| Frames panel slot | v0.2 HotLoop visual diff timeline surface. |
```
**Edit:** Add three rows:
```
| Device panel slot | v0.2 HotLoop screenshot/device surface. |
| Frames panel slot | v0.2 HotLoop visual diff timeline surface. |
| HotLoop event payloads | v0.2 event payload schemas (device.frame.captured, loop.tick.*, frame.diff.available, device.target.changed); no v0.1 runtime emits them. |
| HotLoop loop semantics | v0.2 observation/action loop lifecycle (start, tick, converge, stop); reserved in §8.12. |
| HotLoop frame storage | v0.2 frame cache beside JSONL traces; traces reference frames by ID. |
```

### §8.12 "Panel Reservations For HotLoop (v0.2)" (line 893)
**Current:** 3 lines of panel table + 1 line of behavior note.
**Edit:** Expand to include layout, state tables, and loop semantics:

```markdown
### 8.12 Panel Reservations For HotLoop (v0.2)

| Panel | Reservation |
|---|---|
| Device | Live screenshots per target (Flutter/React/Expo). Opens by default when HotLoop runtime is active. |
| Frames | Scrubbable visual diff timeline. Opens beside Device when HotLoop runtime is active. |

**Layout:** When HotLoop is active, Chat remains left (40%), Device + Frames stack right (60%, Device above Frames, 60/40 split). Graph defaults closed. Tasks overlay shows Loop trace view.

**Device panel states:**
| State | Display |
|---|---|
| Empty | `No target connected. Start a HotLoop run or connect a device.` |
| Loading | `Capturing screenshot...` with skeleton placeholder. |
| Populated | Current screenshot, target name, resolution, capture timestamp. |
| Error | `Screenshot capture failed` with retry action. |
| Offline | `Target disconnected.` |

**Frames panel states:**
| State | Display |
|---|---|
| Empty | `No frames captured yet. Frames appear as HotLoop iterates.` |
| Loading | `Processing diff...` |
| Populated | Scrubbable timeline of frame thumbnails with diff highlights. |
| Error | `Frame processing failed` with retry. |

**Loop semantics (reserved):** HotLoop runs an observation/action loop. Each tick: observe (capture screenshot) → diff (compare to prior frame) → decide (agent evaluates change) → act (apply UI modification) → repeat. Loop stops on: max iterations reached, cost ceiling hit, user interrupt, or convergence (no meaningful visual change for N ticks). Loop state is visible in Tasks panel (Loop trace view) and status bar.

When HotLoop is active, Graph defaults closed and Device + Frames default open. No v0.1 mockups are required; final specification lands in the HotLoop v0.2 design.
```

### §8.13 "Keyboard Shortcut Audit" (line 902)
**Edit:** Add HotLoop rows:
```
| `Ctrl/Cmd+Shift+D` | Focus Device panel | Safe | Reserved v0.2 |
| `Ctrl/Cmd+Shift+F` | Focus Frames panel | Safe | Reserved v0.2 |
| `Ctrl/Cmd+Shift+B` | Rollback to prior frame | Safe (conflicts with VS Code build, but only when ARC focused) | Reserved v0.2 |
| `Space` (when Device/Frames focused) | Pause/resume HotLoop loop | Safe (contextual) | Reserved v0.2 |
```

### §9 "HotLoop Reserved Component Stubs" (line 1307)
**Edit:** Expand stubs with minimal interface hints:
```markdown
### HotLoop Reserved Component Stubs (v0.2)

| Component | Purpose | Reserved props |
|---|---|---|
| `DeviceThumbnail` | Shows target device screenshot. | `src: string` (frame URL or data URI), `targetName: string`, `width: number`, `height: number`, `capturedAt: string` (ISO 8601) |
| `FrameThumbnail` | Shows one visual-diff frame. | `frameId: string`, `src: string`, `diffScore?: number`, `diffRegions?: Rect[]`, `tickNumber: number` |
| `LoopTraceTick` | Shows one observation/action loop tick. | `tickNumber: number`, `action: string`, `frameRef: string`, `durationMs: number`, `costUsd?: number`, `status: 'running' | 'done' | 'failed'` |
| `RollbackButton` | Rolls HotLoop target back to prior frame/checkpoint. | `targetFrameId: string`, `onRollback: () => void`, `disabled: boolean` |

All stubs are deferred to HotLoop v0.2 design. No v0.1 implementation.
```

### §4.1 "Icon System" (line 260)
**Edit:** Add HotLoop icon:
```
| HotLoop | `MonitorSmartphone` | Reserved v0.2 |
```

### §4.2 "CLI Icon Equivalents" (line 286)
**Edit:** Add HotLoop row:
```
| HotLoop | `◫` | `HL` |
```

### §4.3 "Runtime And Provider Badges" (line 308)
**Edit:** Add HotLoop row:
```
| HotLoop | `HL` | `state.info` | Reserved v0.2; badge `(observational)` on graph-less runs. |
```

### §7.14 "Status Line" (line 704)
**Edit:** Add HotLoop segment note:
```
When HotLoop is active, status line adds: target name, loop iteration (e.g., `tick 3/20`), frame count, cumulative cost. Format: `HL | <target> | tick N/M | <N> frames | cost $X.XX`. Truncation: target name elides first, frame count second.
```

### Appendix A "HotLoop Manifest" (line 1663)
**Edit:** Add payload schemas and additional fields:
```yaml
# Add to capabilities section:
capabilities:
  inspect: true
  run: true
  graph: false
  device: true
  frames: true
  capture_modes: ["emulator", "simulator", "real_device"]  # reserved
  rollback_modes: ["hot_reload", "git_revert"]  # reserved
  loop_config:  # reserved
    max_ticks: 20
    convergence_threshold: 3  # stop after N ticks with no meaningful change
    cost_ceiling_usd: 0.50  # default per-run cost ceiling

# Add event payload schemas (reserved v0.2):
event_schemas:
  device.frame.captured:
    schema_version: 1
    fields:
      - frameId: string (ULID)
      - targetId: string
      - targetName: string
      - width: number
      - height: number
      - capturedAt: string (ISO 8601)
      - frameUrl: string (workspace-local path)
      - tickNumber: number

  device.target.changed:
    schema_version: 1
    fields:
      - targetId: string
      - targetName: string
      - targetType: string (emulator|simulator|real_device|web)
      - platform: string (ios|android|web|flutter)
      - status: string (connected|disconnected|error)

  loop.tick.started:
    schema_version: 1
    fields:
      - tickNumber: number
      - runId: string
      - startedAt: string (ISO 8601)

  loop.tick.completed:
    schema_version: 1
    fields:
      - tickNumber: number
      - runId: string
      - completedAt: string (ISO 8601)
      - durationMs: number
      - action: string (description of what the agent did this tick)
      - frameRef: string (frameId of the resulting screenshot)
      - diffScore: number (0-1, how much changed from prior frame)
      - costUsd: number (cost of this tick's vision model call)
      - converged: boolean (true if loop should stop)

  frame.diff.available:
    schema_version: 1
    fields:
      - diffId: string (ULID)
      - frameA: string (frameId of prior frame)
      - frameB: string (frameId of current frame)
      - diffUrl: string (workspace-local path to diff image)
      - pixelDiffPercent: number (percentage of pixels that changed)
      - similarityScore: number (0-1, 1 = identical)
      - changedRegions: array of {x, y, width, height}

# Add frame storage spec:
frame_storage:
  location: "<workspace>/.arc/frames/<run-id>/"
  format: png
  retention: "until run deleted or arc runs delete <run-id>"
  max_frames_per_run: 200
  reference_model: "traces store frameId; frames stored separately"

# Add supported targets matrix:
supported_targets:
  - platform: react-native-expo
    support_level: planned_full
    capture: "expo-dev-client or react-native-view-shot"
  - platform: react-native-bare
    support_level: planned_partial
    capture: "react-native-view-shot or ADB/IDB screencap"
  - platform: flutter
    support_level: planned_partial
    capture: "flutter screenshot or ADB/IDB screencap"
  - platform: web-nextjs
    support_level: deferred
    capture: "Playwright page.screenshot()"
  - platform: web-vite
    support_level: deferred
    capture: "Playwright page.screenshot()"
```

### §15 "States and Edge Cases" (line 1541)
**Edit:** The existing table at line 1541 already has a "v0.2 HotLoop" column. Verify that Device and Frames rows have HotLoop state entries. If not, add them:
```
| Device | no target | capturing | screenshot | capture failed | target disconnected | N/A | N/A |
| Frames | no frames | processing diff | timeline | diff failed | N/A | N/A | rollback applied |
```

### New §7.18 "HotLoop CLI Reservations (v0.2)"
**Add after §7.17:**
```markdown
### 7.18 HotLoop CLI Reservations (v0.2)

No HotLoop CLI commands ship in v0.1. These names are reserved:

| Command | Purpose |
|---|---|
| `arc hotloop status` | Show current HotLoop target, loop state, frame count. |
| `arc hotloop frames` | List captured frames for current or specified run. |
| `arc hotloop pause` | Pause the active HotLoop loop. |
| `arc hotloop resume` | Resume a paused HotLoop loop. |
| `arc hotloop rollback` | Roll back to a prior frame/checkpoint. |
| `arc hotloop target list` | List available targets (devices/emulators/simulators). |
| `arc hotloop target set <id>` | Switch the active HotLoop target. |

All reserved commands return `HotLoop is not available in v0.1. This command is reserved for v0.2.` when invoked in v0.1.
```

## Acceptance Criteria

### v0.1 readiness (reservations only)

- [ ] §0.5 explicitly lists HotLoop event payloads, loop semantics, and frame storage as v0.1 protocol reservations
- [ ] §8.12 includes panel layout diagram, state tables for Device and Frames, and reserved loop semantics paragraph
- [ ] §8.13 includes HotLoop keyboard shortcut reservations
- [ ] §9 includes reserved props for `DeviceThumbnail`, `FrameThumbnail`, `LoopTraceTick`, `RollbackButton`
- [ ] §4.1, §4.2, §4.3 include HotLoop icon/glyph/badge entries
- [ ] §7.14 includes HotLoop status bar segment specification
- [ ] §7.18 exists with reserved HotLoop CLI commands
- [ ] Appendix A includes event payload schemas for all 5 events (marked `reserved_v0_2: true`)
- [ ] Appendix A includes `frame_storage` specification
- [ ] Appendix A includes `supported_targets` matrix with honest support levels
- [ ] Appendix A includes `loop_config` with max ticks, convergence threshold, cost ceiling
- [ ] Appendix A includes `capture_modes` and `rollback_modes` in capabilities
- [ ] §15 state table includes Device and Frames rows with HotLoop state entries
- [ ] No HotLoop implementation code exists in v0.1 (verified by grep for `hotloop` in `python/src/` and `packages/arc-extension/src/`)
- [ ] All HotLoop references in v0.1 code are limited to protocol type definitions and reservation stubs

### v0.2 readiness (implementation)

- [ ] Screenshot capture mechanism implemented for at least one target platform
- [ ] Device panel renders live screenshots from connected target
- [ ] Frames panel renders scrubbable timeline with visual diffs
- [ ] Loop tick lifecycle implemented: observe → diff → decide → act → repeat
- [ ] Loop stop conditions implemented: max iterations, cost ceiling, user interrupt, convergence
- [ ] Frame cache implemented (workspace-local, separate from JSONL traces)
- [ ] Rollback mechanism implemented for at least one target platform
- [ ] All 5 reserved events emitted with correct payload schemas
- [ ] HotLoop runs appear in Runs panel with appropriate summary fields
- [ ] Cost visibility: per-tick cost, cumulative cost, cost ceiling displayed
- [ ] Keyboard shortcuts work: focus Device, focus Frames, rollback, pause/resume
- [ ] Empty/loading/error/offline states implemented for Device and Frames panels
- [ ] Accessibility: ARIA labels, screen reader announcements for frame changes
- [ ] CLI commands work: `arc hotloop status`, `arc hotloop frames`, `arc hotloop pause/resume`
- [ ] Target platform support: at least React Native (Expo) with full capture loop
- [ ] Integration tests: full HotLoop tick cycle with fake target and mocked vision model

## Reject / Do Not Build

| Idea | Why rejected |
|---|---|
| **HotLoop as a general visual regression CI tool** | HotLoop is an agent runtime surface, not a CI tool. Playwright and Chromatic already solve visual regression testing. HotLoop's value is the agent iteration loop, not the diff itself. Building CI features would dilute focus and compete with mature tools. |
| **Multi-device / device farm management** | HotLoop targets a single local device/emulator/simulator. Device farm management is a separate product (BrowserStack, Firebase Test Lab, AWS Device Farm). HotLoop should not manage device pools. |
| **Performance profiling overlays** | Flutter DevTools and Chrome DevTools already provide excellent performance profiling. HotLoop's frame timeline is for visual iteration, not FPS/jank analysis. Adding performance metrics would confuse the product's purpose. |
| **HotLoop without vision model** | The loop requires visual understanding to decide if UI changes are correct. Without a vision model, HotLoop degrades to a blind automation loop, which is not the product. If no vision model is available, HotLoop should be disabled with a clear message, not degraded. |
| **Embedding screenshots in JSONL traces** | Binary data in JSONL would bloat trace files, break the append-only model, and make trace scanning slow. Frames belong in a separate cache. Traces reference frames by ID. This aligns with ADR-003's principle that JSONL stays lean. |
| **HotLoop for non-UI workloads** | HotLoop is specifically for UI iteration. Using it for API testing, data pipeline iteration, or non-visual agent work is a category error. Those workloads belong in SwarmGraph or other runtimes. |
| **HotLoop as a Storybook replacement** | Storybook is a component development environment. HotLoop iterates on running UI. They serve different purposes. HotLoop should not try to replicate Storybook's controls, args, or story management. |
| **Automatic UI code generation from screenshots** | While a vision model could theoretically generate UI code from screenshots, this is a separate product (v0.3+ at earliest). HotLoop's loop is observation → action, where "action" is a targeted modification, not full code generation. |
| **HotLoop-specific trace store** | HotLoop should use the existing trace store (JSONL + SQLite index). Adding a separate trace store for HotLoop would fragment the storage architecture and duplicate ADR-003 work. Frames are the only HotLoop-specific storage need. |
| **HotLoop in v0.1** | The v0.1 scope is already large (chat, graph, runs, config, trust, providers, SwarmGraph). HotLoop requires vision model integration, target lifecycle management, and a novel loop architecture. Rushing it into v0.1 would compromise quality and delay release. |
