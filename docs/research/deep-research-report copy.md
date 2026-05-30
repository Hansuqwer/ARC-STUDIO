# ARC Studio Theia Architecture Research

ARC Studio should be treated as a **Theia-native product**, not as “VS Code with custom panels”. The strongest upstream pattern is to put product-defining behaviour into **Theia extensions** with full access to DI, contribution points, widget management, workspace services and backend lifecycle hooks, while using the VS Code extension model only where compatibility or third-party ecosystem reuse is the real goal. That is especially important because Theia explicitly distinguishes VS Code extensions, Theia extensions and Theia plugins, and it recommends VS Code extensions or Theia extensions over Theia plugins because plugin support remains under discussion. citeturn13view0turn15view18turn15view19

The architectural direction of Theia in 2025–2026 also lines up with ARC’s current pain points. The platform continues to ship on a **monthly release cycle** with **quarterly community releases**, and recent releases have pushed hard on AI integration, workspace trust, terminal UX, testing support and multi-root readiness. In practice, that means ARC should move toward a **modular frontend/backend split**, **typed JSON-RPC contracts**, **multi-root-first workspace handling**, **stateful widgets managed by Theia’s shell**, **preference-driven configuration**, and **trust-aware approval flows** rather than ad hoc UI or service glue. citeturn18view2turn18view0turn20view0turn21view3

One important limitation: I did **not** have access to ARC Studio’s repository or internal design documents in this session. The ARC-specific gap analysis below is therefore an informed mapping from the module names and problem areas you supplied to current Theia patterns. Anywhere I name a specific ARC file or service boundary, treat it as a precise recommendation to validate against the actual codebase, not as a claim that the current code definitely behaves that way.

## Theia architecture baseline

Theia’s core runtime model is still the right starting point for ARC: a **frontend** and a **backend** process communicating primarily via **JSON-RPC** over WebSockets, with REST over HTTP where appropriate. That architecture is designed to support both browser-hosted and Electron-hosted products from one codebase. At code-organisation level, Theia also expects clean separation between `common`, `browser`, `node`, `electron-browser`, `electron-node` and `electron-main` concerns. ARC’s own service split should mirror that layout instead of letting browser widgets or React components become transport or orchestration layers. citeturn14view0turn23view0

Theia extensions are packaged as npm modules that contribute one or more DI modules via `theiaExtensions` in `package.json`. At runtime, Theia builds a **single global DI container per frontend and per backend**, collects contributions through multi-injection, and then wires product behaviour from those contribution points. That is the core reason ARC should prefer native Theia extensions for internal product features: they can bind commands, menus, widgets, backend services, application lifecycle hooks and custom protocols directly into the platform. citeturn30view1turn38view0turn35search5

Dependency injection is not incidental in Theia; it is central. The platform documentation explicitly says DI is integral to Theia, and its extension examples use `ContainerModule`, `@injectable`, constructor injection, field injection and `@postConstruct`. Inversify’s current documentation also confirms that bindings are **transient by default**, singleton scope must be chosen explicitly, and container modules exist to register and later unload bindings with activation and deactivation handlers. For ARC, that means service lifetimes and cleanup should be intentional: singleton for long-lived backend coordinators, transient only where state really must be per-resolution, and activation/deactivation used where transport or listener resources need deterministic setup/teardown. citeturn14view1turn30view4turn29view0turn29view1turn29view2turn29view3

Theia’s JSON-RPC pattern is also clear. A `ConnectionHandler` exposes a path and an `onConnection` callback, while `RpcConnectionHandler` and `RpcProxyFactory` establish typed frontend/backend proxies. In other words, ARC’s “session bridge” should not be an informal fetch/SSE/websocket tangle attached to widgets. It should be a proper **common protocol** in `common/*`, a backend implementation bound as a connection handler, and a frontend proxy created once and reused. citeturn24view4turn15view0turn15view2

On the UI side, Theia expects custom views and editors to be **widgets** managed centrally by the `WidgetManager`. Widgets are usually implemented with `ReactWidget` or `BaseWidget`, created via `WidgetFactory`, and retrieved with `WidgetManager.getOrCreate` so the shell can manage their lifecycle and restoration. Frontend application startup concerns such as opening views, arranging layout, adding status bar items and persisting application data belong in `FrontendApplicationContribution`, not inside widget constructors. citeturn24view0turn15view13turn24view1

Backend lifecycle is similarly formalised. Long-lived backend services should be created and initialised via `BackendApplicationContribution`, and the current changelog shows that `onStop()` now runs from `gracefulShutdown()` before the root Inversify container is unbound, with parallel asynchronous hooks supported. For ARC, daemon discovery, process cleanup, connection shutdown and stream disposal belong here, not in process-global hacks or widget-driven cleanup. citeturn24view2turn18view5

Theia’s workspace and configuration model is now mature enough that ARC should lean on it instead of inventing parallel mechanisms. Preferences are resolved across **Default**, **User**, **Workspace** and **Folder** scopes, with folder scope explicitly intended for **multi-root workspaces**. Preferences can be accessed through `PreferenceService` or type-safe `PreferenceProxy`. Workspace resolution in `WorkspaceService` already handles “closest containing root” semantics and exposes both `getWorkspaceRootUri()` and `getRootPrefixedPath()`, the latter returning stable root-qualified paths such as `backend/src/index.ts`. Theia’s `WorkspaceStorageService` additionally prefixes persisted data with the current workspace path, giving ARC a natural place to keep per-workspace UI state. citeturn24view3turn15view4turn24view5turn22view0turn33view0

For terminals, tasks and debugging, upstream features are already rich enough that ARC should integrate rather than bypass. `@theia/terminal` contributes integrated terminals, `@theia/terminal-manager` can group multiple terminals in one view, Theia 1.70 added command history via shell integration, and task terminals can be routed into a dedicated tasks page. For automation, Theia exposes `TaskProvider`, `TaskResolver` and `TaskRunner`; for debugging, `DebugService` is the central entry point to configure and start sessions. ARC should attach agent or daemon operations to these existing surfaces where possible rather than building separate bespoke consoles and job runners. citeturn14view15turn12search1turn21view5turn14view5turn14view14

Theia AI is now no longer a side experiment. Its adopter documentation says Theia AI provides **reusable components, prompt management, LLM integration and flexible user interfaces**. Agents are plain injectable Theia services, prompts can use auto-resolved variables and functions, capabilities can be toggled per request, slash commands are first-class, and skills can be discovered from workspace, user-configured and global locations. Recent 1.70 and 1.71 releases added persistent capability settings, an extracted `AgentModeConfirmationService`, tool-confirmation descriptions for shell commands, reasoning controls, token usage indicators and workspace-trust gating for AI features. ARC’s provider configuration UI, approval flows and safety model should therefore align with these primitives instead of inventing a parallel abstraction stack. citeturn16view0turn16view5turn16view7turn16view8turn17view0turn21view4turn21view1turn20view0

## Theia best-practice matrix

| Area | Theia best practice | What it means for ARC |
|---|---|---|
| Product-defining functionality | Use **Theia extensions** for core product features; reserve VS Code extensions for compatibility or third-party reuse. Theia extensions have full internal access and compile-time integration, while Theia plugins remain a debated path. citeturn13view0turn15view18 | ARC’s core session model, widgets, approvals, provider config and daemon integration should live in native Theia extensions, not VS Code-style runtime add-ons. |
| Runtime boundaries | Keep `common`, `browser`, `node` and Electron-specific code separate. citeturn23view0 | Move transport DTOs and service interfaces into `common/*`; keep React/UI in `browser/*`; keep daemon/process logic in `node/*`. |
| Dependency injection | Bind services and contributions in `ContainerModule`; use `@injectable`, constructor injection and explicit scopes. Bindings are transient by default in Inversify. citeturn30view1turn30view4turn29view0turn29view2turn29view3 | ARC should replace broad façade classes with explicit singleton services and thin contribution bindings. |
| Contribution points | Use contribution interfaces and `bindContributionProvider` rather than patching core or manually collecting implementations. citeturn30view3turn30view4 | Command, menu, status, notification and event sources should be contributed, not centrally hard-coded. |
| Backend startup/shutdown | Initialise long-lived services via `BackendApplicationContribution`; cleanup via async `onStop`/`gracefulShutdown`. citeturn24view2turn18view5 | Daemon discovery, SSE termination and bridge cleanup should be backend lifecycle-managed. |
| Frontend startup | Use `FrontendApplicationContribution` to open views, register listeners, add status bar items and persist UI state on shutdown. citeturn24view1 | ARC should stop doing shell/layout work inside widgets or random React effects. |
| JSON-RPC transport | Define common protocols and bind `ConnectionHandler` / `RpcConnectionHandler`; create frontend proxies via `RpcProxyFactory`. citeturn24view4turn15view0turn15view2 | ARC’s session bridge should become typed RPC instead of ad hoc transport wrappers. |
| Widgets | Use `ReactWidget`/`BaseWidget`, `WidgetFactory` and `WidgetManager.getOrCreate`. citeturn24view0turn15view13 | Widget lifecycle, singleton semantics and restoration should be platform-managed. |
| Workspace handling | Use `WorkspaceService` root resolution and root-prefixed paths; assume multi-root from day one. citeturn24view5turn22view0turn18view6turn18view7 | ARC should stop assuming a single “primary” root for discovery, context and approvals. |
| Configuration | Use `PreferenceSchema`, `PreferenceService` and `PreferenceProxy`; leverage user/workspace/folder scopes. citeturn24view3turn15view4 | Provider config should be declarative, scope-aware and inspectable in Settings. |
| Persistence | Use workspace-aware storage and stateful widgets instead of custom local-storage keys. `WorkspaceStorageService` prefixes keys by workspace URI. citeturn33view0turn32search0 | Tab state and transient UI preferences should not bleed across projects. |
| Commands and menus | Register commands through `CommandContribution`, attach visibility/enabled state via handlers, and wire menus/keybindings through the matching registries. citeturn27view0turn28view2turn28view4 | ARC actions should become command-first so menus, palette and shortcuts stay consistent. |
| Terminal/tasks/debug | Integrate through Theia terminal, task and debug services rather than custom consoles where possible. citeturn14view15turn12search1turn14view5turn14view14turn21view5 | Agent runs, daemon commands and diagnostics should surface in standard Theia workbench features. |
| AI safety and approvals | Reuse Theia AI capability settings, tool confirmation and agent-mode confirmation patterns; align with workspace trust. citeturn21view4turn20view0turn18view6 | Sandbox approval modals should be trust-aware, configurable and consistent with Theia AI semantics. |
| Performance | Compose only needed extensions, build with Theia CLI production mode, keep Monaco-specific code isolated, prefer shared framework re-exports to duplicate dependencies. citeturn38view0turn38view1turn14view16turn37search9turn18view4turn37search10 | ARC should reduce bundle and startup cost by narrowing feature surfaces and not letting Monaco leak everywhere. |
| Accessibility | Use platform commands/keybindings, accessible labels, focusable controls and avoid colour-only cues; Theia still has open accessibility gaps in keyboard navigation and ARIA coverage. citeturn26search1turn26search0turn26search7 | ARC needs an accessibility layer that is stricter than the current Theia baseline, especially for badges, terminals and modal approvals. |
| Testing | Follow Theia’s split between unit tests, slow/integration tests and `*.ui-spec.ts`; use Theia Playwright page objects for maintainable UI tests. citeturn24view7turn36search1turn36search9 | ARC should test services, protocol contracts, widget restore and multi-root UI behaviour separately. |

## ARC architecture gaps

Based on the problem areas you listed, the most likely structural mismatch is that `arc-backend-service.ts` has become a **facade that is too broad**. In Theia terms, that usually means one class is now mixing backend lifecycle, transport, provider config, session orchestration, workspace interpretation and UI-oriented state. That pattern is the opposite of Theia’s DI and contribution model, which expects smaller injectable services exposed through explicit contribution points or protocols. citeturn14view1turn30view4turn24view2

The next likely gap is **single-root thinking** in a platform that is now firmly multi-root aware. Theia already resolves “closest containing root”, exposes root-prefixed paths, stores folder-scoped preferences, supports workspace files and is even moving upstream away from “primary” versus “secondary” root assumptions in newer changelog work. If ARC still treats one workspace root as default for agent context, daemon discovery, sandbox approval scope or file resolution, it is misaligned with the platform. citeturn24view3turn24view5turn22view0turn18view6turn18view7

On the frontend, the risk areas you named strongly suggest that widget lifecycle and tab persistence are at least partly **manual** today. In Theia, widgets are supposed to be created through `WidgetFactory`, deduplicated by `WidgetManager`, laid out by the shell, and their surrounding startup/shutdown behaviour controlled by `FrontendApplicationContribution`. If ARC is opening widgets directly, storing tab state in bespoke browser storage, or letting components create/dispose transport connections independently, that will keep producing restoration bugs, duplicate subscriptions and inconsistent layout behaviour. citeturn15view13turn24view1turn33view0

The “session bridge”, “daemon discovery” and “SSE reconnect” items also point to a likely **transport inversion**: the frontend probably knows too much about backend connection details. Theia’s normal pattern is the reverse. The backend owns long-lived connections and exposes a typed API over JSON-RPC; the frontend consumes a stable proxy. If ARC instead lets views own reconnect logic, stream parsing, or daemon process discovery, then widget lifecycles will keep breaking communication and reconnection will remain brittle. citeturn24view2turn24view4turn15view2

“Event virtualization” is a particularly strong signal. Theia’s event model is based on `Emitter`, and there have been upstream memory-leak warnings when too many listeners accumulate. Theia has also recently improved contribution-provider memory cleanup. That strongly suggests ARC should treat event fan-out as a dedicated infrastructure concern, with explicit batching and disposal, not as something every tab or widget does independently. citeturn31search0turn31search1turn7search17

Finally, the UI contribution items you listed — command/menu contributions, status bar items, notification badges, provider config UI, sandbox approval modals — suggest ARC may currently be building too much with custom DOM and too little with Theia’s own contribution and preference systems. Theia already has native patterns for commands, menus, keybindings, toolbars, messages, status bar items, tree decorators and scope-aware preferences. The more ARC aligns with those primitives, the less bespoke UI plumbing it will need to carry. citeturn27view0turn28view2turn15view16turn15view17turn11search3turn24view3

## Recommended service decomposition

### Target service split

I would refactor `arc-backend-service.ts` into a **thin orchestration edge** and move most real behaviour into a small set of injectable singleton services:

**In `common/*`**
- `arc-protocol.ts` for JSON-RPC interfaces, DTOs and event payloads.
- `arc-workspace-types.ts` for root-qualified path and workspace context types.
- `arc-provider-types.ts` for provider configuration and approval schemas.

**In `node/*`**
- `ArcDaemonDiscoveryService`: process/daemon discovery, health checks, cache and invalidation.
- `ArcSessionRegistry`: create, track, resume and end sessions.
- `ArcStreamService`: own the real SSE/stream lifecycle, including reconnect and backoff.
- `ArcApprovalService`: sandbox approvals, tool confirmations and policy checks.
- `ArcProviderConfigService`: resolve config from preferences, environment and secrets.
- `ArcWorkspaceContextService`: translate Theia workspace roots into Arc-specific execution context.
- `ArcBackendContribution`: `BackendApplicationContribution` that initialises discovery/stream processes and cleans them up safely. citeturn24view2turn18view5turn24view4

**In `browser/*`**
- `ArcSessionBridge`: a single frontend proxy façade over typed JSON-RPC, with no direct SSE knowledge.
- `ArcWorkspaceContext`: current root, root mapping and root-prefixed path helpers for the UI.
- `ArcStatusService`: derived status for the status bar, notifications and badges.
- `ArcBadgeService`: view/tree decorator state and notification counts.
- `ArcTabStateService`: state serialisation/restoration for open Arc widgets.
- `ArcFrontendContribution`: restore layout, open default views, register status items and persist state on shutdown. citeturn24view1turn15view13turn33view0

That split follows Theia’s actual architecture rather than layering incidental browser code on top of a backend lump. It also gives each service one transport boundary, one lifecycle boundary and one testing surface. citeturn23view0turn30view1turn30view4

### Service ownership model

The key ownership rule should be:

- **Backend services own reality**: processes, streams, sessions, reconnect, trust policy and provider resolution.
- **Frontend services own presentation**: widgets, focus, derived view state, menus, badges and temporary tab state.
- **Common interfaces own contracts**: no frontend code importing backend implementations, and no widgets reaching into daemon/process code. citeturn14view0turn24view4turn23view0

If you keep a façade called `arc-backend-service.ts`, it should become an **integration façade only**: effectively a composition layer that delegates to the services above, useful for migration but not a permanent home for business logic.

### Multi-root workspace strategy

ARC should adopt an explicit **root-qualified context model**.

Theia’s `WorkspaceService.getWorkspaceRootUri()` already returns the containing root and chooses the closest match when a file belongs to more than one root. It also provides `getRootPrefixedPath()`, which produces a stable root-qualified relative path even in single-root workspaces. Preferences can be stored at **folder scope**, not just user or workspace scope, and workspace files can hold preferences for multi-folder workspaces. That gives ARC a ready-made model for provider selection, daemon routing, approval scope and session context. citeturn24view5turn22view0turn24view3

Concretely, I recommend that ARC:

- never store or transmit a bare relative path when a root-qualified path can be used;
- resolve effective provider config in the order **folder → workspace → user → default**, mirroring Theia preference resolution;
- attach each session to a concrete root mapping rather than an implicit “current workspace”;
- make root selection visible in the UI whenever an operation spans multiple roots;
- treat “no root” as a first-class case for empty windows or detached resources. citeturn24view3turn22view0turn18view6turn18view7

This matters even more because current upstream changelog work is explicitly removing “secondary root” semantics in some AI/workspace logic and standardising on all roots being equal. ARC should design for that future now, not fight it later. citeturn18view6turn18view7

## Performance and bundle plan

ARC’s performance work should focus on three layers: **composition**, **runtime event pressure**, and **Monaco containment**.

At composition time, Theia applications are assembled by choosing dependencies in the browser app or Electron app, then bundling with Theia CLI. That means bundle size can be reduced most effectively by limiting included extensions and avoiding accidental cross-package dependencies. The CLI supports production builds with `theia build` and efficient dev rebuilds with `theia build --watch --mode development`. The extension authoring docs also show the standard `bundle`, `rebuild`, `start` and `watch` scripts that ARC should keep close to upstream. citeturn38view0turn38view1

For Monaco specifically, the upstream `@theia/monaco` package exists as the boundary between `@theia/monaco-editor-core` and the rest of the application, and Theia’s Monaco guidance has long been to **keep Monaco integration encapsulated** and let the rest of the product use higher-level editor abstractions where possible. That is exactly the right rule for ARC. Monaco should be a dependency of editor-facing modules, not of provider config, session management, notifications or approval flows. If a view does not need Monaco, it should not import Monaco-derived services at all. citeturn14view16turn37search10

Where ARC does need custom bundling work, it should also note the upstream rename from `@theia/native-webpack-plugin` to `@theia/bundle-plugin`. That is a small but useful indicator that ARC should keep build customisations aligned with current Theia build tooling instead of carrying an old custom webpack story forever. citeturn18view4

The runtime optimisation plan should then be:

- terminate SSE or daemon streams **once in the backend**, not once per widget;
- normalise them into **typed JSON-RPC notifications** or request/response calls;
- keep one frontend `ArcSessionBridge` singleton per browser window;
- fan out into view models with throttled or coalesced events;
- update status bar items and badges from derived aggregate state, not raw stream chatter. citeturn24view2turn24view4turn31search0turn31search1

That design directly addresses “session bridge”, “SSE reconnect” and “event virtualization”. It also reduces the chance of Emitter-based listener leaks, an area where Theia itself has had to tighten behaviour. citeturn31search1turn7search17

For workbench responsiveness, I would also avoid opening heavy ARC panels eagerly unless they are part of the default product posture. Theia 1.70 did make AI Chat and Terminal first-class defaults in the Theia IDE, but that was a deliberate product choice, not a blanket rule for every adopter. ARC should only auto-open views that genuinely define the product. Everything else should be command-openable and lazily instantiated through `WidgetManager`. citeturn21view3turn15view13

## Accessibility plan

Theia gives ARC strong primitives, but not a complete accessibility guarantee. There are still open upstream issues around keyboard navigation, screen-reader support, terminal accessibility and ARIA coverage, including historical gaps for status bar items and tree items. That means ARC should aim to be **better than the baseline** rather than assuming the framework solves everything automatically. citeturn26search1turn26search0turn26search7

The first rule is to make every ARC action **command-first**. If an action exists only as a button in a custom widget, it is already on the wrong path. In Theia, commands can be surfaced through the command palette, menus, keybindings and toolbars, with `isEnabled` and `isVisible` determining context. That gives both accessibility and product consistency. The sandbox approval flow, provider config actions, session restart commands and daemon operations should all be representable as commands. citeturn27view0turn28view2turn28view4

The second rule is to avoid purely visual indicators. Your “notification badges” and “status bar items” should always have a textual meaning, a tooltip and a command target. Theia’s plugin API and internal status bar support both text-based status items, but the accessibility issues around status bar/tree ARIA mean ARC should explicitly provide readable labels and avoid conveying critical state only via colour or iconography. For view-local badges, prefer native decorator patterns and add a matching accessible summary in the status bar or widget header. citeturn28view0turn28view1turn11search3turn26search0

The third rule is strict focus management. Sandbox approval modals, provider config dialogs and custom widgets should respect predictable keyboard focus, default actions, escape handling and focus restoration to the originating widget. This is especially important because Theia has known rough edges around cross-workbench keyboard navigation. ARC should therefore be conservative with custom modal mechanics and lean on Theia’s message, quick pick and command patterns whenever a fully custom dialog is unnecessary. citeturn15view16turn26search1turn26search7

Terminal-related accessibility also deserves special handling. Theia has improved terminal command history and terminal grouping, but upstream accessibility discussions still mention terminal contrast and screen-reader-related gaps. ARC should therefore ensure that any terminal-linked workflow has a non-terminal fallback for critical information, and that approvals or errors are not only visible inside a terminal stream. citeturn21view5turn12search1turn26search1

## Testing strategy

ARC should adopt a **layered Theia-native test strategy**.

At the service layer, follow Theia’s documented convention of `*.spec.ts` for unit tests, `*.slow-spec.ts` for slower integration tests and dedicated test helpers under `src/node/test`. That is the right place to test daemon discovery, provider config resolution, SSE backoff, approval policy, workspace-root mapping and JSON-RPC contract correctness. citeturn24view7turn25view0

At the browser layer, follow Theia’s `*.ui-spec.ts` convention for widget and browser interaction tests. Widget restoration, tab reopening, focus behaviour, multi-root root switching, status bar updates and notification badge rendering should all be tested here. Because `WorkspaceStorageService` scopes persisted data by workspace URI, tab state tests should explicitly cover switching between workspaces and saved workspace files. citeturn24view7turn33view0

For end-to-end workbench testing, use **Theia Playwright page objects**. Theia’s Playwright examples specifically position page objects as an abstraction over Theia UI details so tests stay concise, maintainable and stable, and they also support extensibility for custom views and editors. That is exactly the right fit for ARC because many of your risk areas are workbench-level behaviours, not isolated functions. citeturn36search1turn36search9

I would prioritise the following end-to-end fixtures:

- a **single-root workspace** fixture for baseline behaviour;
- a **multi-root workspace** fixture with duplicated file names across roots;
- a **saved workspace file** fixture with folder-scoped settings;
- a **daemon restart** fixture that forces stream reconnect;
- a **restricted/untrusted workspace** fixture for approval and command gating;
- a **state restore** fixture covering tab persistence and session reattachment. citeturn24view3turn24view5turn20view0

The 1.71 improvements to VS Code test extension support are also a useful signal: the upstream project is still actively refining test/workbench fidelity. ARC benefits from staying close to native Theia workbench patterns, because the more custom shell behaviour it invents, the less it benefits from those upstream fixes. citeturn20view0

## Top Theia-specific improvements

The table below uses your ARC naming where possible. Where a file or module name does not exist yet, I have named the **recommended ownership location**.

| Improvement | Theia pattern/source | ARC file/module | Benefit | Complexity | Priority |
|---|---|---|---|---|---|
| Split the backend façade into domain services | `BackendApplicationContribution` for lifecycle, DI-bound singleton services, explicit `common/browser/node` split. citeturn24view2turn23view0turn29view2 | `arc-backend-service.ts` → `arc-daemon-discovery-service.ts`, `arc-session-registry.ts`, `arc-stream-service.ts`, `arc-provider-config-service.ts`, `arc-approval-service.ts` | Removes god-object coupling; clearer ownership and easier testing | High | **P0** |
| Replace ad hoc bridge code with typed JSON-RPC | `ConnectionHandler`, `RpcConnectionHandler`, `RpcProxyFactory`. citeturn24view4turn15view0turn15view2 | `common/arc-protocol.ts`, `browser/arc-session-bridge.ts`, `node/arc-rpc-contribution.ts` | Stable cross-process contracts and easier reconnect logic | High | **P0** |
| Make workspace resolution multi-root-native | `WorkspaceService.getWorkspaceRootUri()` and `getRootPrefixedPath()`; folder-scoped settings for multi-root. citeturn24view5turn22view0turn24view3 | `workspace-root detection`, `browser/arc-workspace-context.ts` | Correct file/session/provider behaviour across multi-root workspaces | Medium | **P0** |
| Move widget creation under `WidgetManager` | `WidgetFactory`, `WidgetManager.getOrCreate`, `ReactWidget`. citeturn15view13turn24view0 | `frontend widget lifecycle`, `browser/widgets/*`, `arc-view-contribution.ts` | Fixes duplicate widgets, restore bugs and layout drift | Medium | **P0** |
| Persist tab and view state with workspace scope | `WorkspaceStorageService` prefixes keys by workspace URI; frontend contributions can persist app data on shutdown. citeturn33view0turn24view1 | `tab state persistence`, `arc-tab-state-service.ts` | Prevents state bleeding across projects; improves restart fidelity | Medium | **P0** |
| Make the session bridge a singleton frontend service | Frontend services should consume one backend proxy instead of per-widget transports. Supported by Theia’s DI and RPC patterns. citeturn30view4turn24view4 | `session bridge` | Stops per-tab connection duplication and inconsistent reconnect state | Medium | **P0** |
| Terminate SSE in one backend stream service | Theia’s normal cross-process path is backend-owned transport plus frontend RPC proxy; long-lived init belongs in backend contributions. citeturn24view2turn14view0turn24view4 | `SSE reconnect`, `node/arc-stream-service.ts` | Reliable reconnect, smaller browser memory footprint, simpler widgets | High | **P0** |
| Add event virtualisation and batching | Theia eventing uses `Emitter`; upstream has seen listener leak warnings and improved cleanup. citeturn31search0turn31search1turn7search17 | `event virtualization`, `common/arc-events.ts`, `browser/arc-event-bus.ts` | Lower render churn and fewer listener leaks | Medium | **P1** |
| Refactor actions into command/menu/keybinding contributions | `CommandContribution`, `MenuContribution`, `KeybindingContribution`, context-aware handlers. citeturn27view0turn28view2turn28view4 | `command/menu contributions`, `arc-command-contribution.ts`, `arc-menu-contribution.ts` | Better keyboard access, cleaner menus, less widget code | Medium | **P1** |
| Centralise status bar ownership | Startup/status items fit `FrontendApplicationContribution`; status bars are a native workbench surface. citeturn24view1turn28view0 | `status bar items`, `arc-status-bar-contribution.ts`, `arc-status-service.ts` | Consistent surface for connection, trust and approval state | Low | **P1** |
| Implement badges with decorators, not bespoke DOM | Maintainer guidance for tree badges uses `TreeDecorator` / `tailDecorations`; VS Code-extension badge parity is not universal. citeturn11search3turn11search10 | `notification badges`, `browser/decorators/*`, `arc-badge-service.ts` | Native look-and-feel and fewer compatibility corners | Medium | **P1** |
| Move provider config into the preference system | `PreferenceSchema`, `PreferenceService`, `PreferenceProxy`, user/workspace/folder scopes. citeturn24view3turn15view4turn17view3 | `provider config UI`, `common/arc-preferences.ts`, `provider-config-widget.tsx` | Declarative config, scope-aware overrides, Settings integration | Medium | **P1** |
| Align sandbox approvals with Theia AI trust/confirmation patterns | `AgentModeConfirmationService`, tool confirmation descriptions, workspace trust gating. citeturn21view4turn20view0turn18view6 | `sandbox approval modals`, `arc-approval-service.ts`, `sandbox-approval-dialog.tsx` | Safer UX, less custom policy code, clearer user intent | Medium | **P1** |
| Use native terminal/tasks/debug surfaces | `@theia/terminal`, `@theia/terminal-manager`, `TaskProvider/Resolver/Runner`, `DebugService`. citeturn14view15turn12search1turn14view5turn14view14turn21view5 | `terminal integration`, `task/debug APIs`, `terminal/arc-terminal-contribution.ts` | Reuses core workbench UX instead of parallel consoles | Medium | **P2** |
| Contain Monaco and modernise bundling | Keep Monaco integration isolated; use Theia CLI builds; prefer shared re-exports; align with `@theia/bundle-plugin`. citeturn14view16turn38view1turn37search9turn18view4turn37search10 | `Monaco bundle optimisation`, browser-app build config, editor modules | Smaller bundle, cleaner editor boundary, better upgradeability | Medium | **P2** |

### Recommended service decomposition summary

If you want the shortest possible target shape, it is this:

- **Backend**: discovery, session registry, stream/reconnect, approvals, provider config, workspace context.
- **Common**: typed protocols, DTOs, root-qualified path model.
- **Frontend**: one session bridge, one workspace context service, one status/badge service, stateful widgets managed through Theia shell patterns.
- **Contributions**: one backend application contribution, one frontend application contribution, command/menu/keybinding contributions, widget factories and view contributions. citeturn24view1turn24view2turn24view4turn15view13turn27view0

### Open questions and limitations

Because I did not have ARC Studio source access in this session, a few implementation-level questions remain open:

- whether `arc-backend-service.ts` is currently only a façade or also a transport object;
- whether ARC already implements `StatefulWidget`-style persistence or uses custom storage;
- whether session transport is currently SSE-only, SSE plus websocket, or already partially JSON-RPC;
- whether provider configuration is already backed by Theia preferences or lives in separate persisted state.

Those questions do **not** change the direction of the recommendations above. They only affect migration order and the exact file boundaries.