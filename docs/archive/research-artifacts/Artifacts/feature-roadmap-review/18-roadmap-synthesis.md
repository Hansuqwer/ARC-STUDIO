# ARC Studio Feature Roadmap Review — Synthesis

## 1. Top 20 Recommended Changes

| # | Change | Priority | Feature Area | Rationale |
|---|--------|----------|-------------|-----------|
| 1 | **Add `@file` and `@folder` mention syntax to chat** | P0 — v0.1 must-have | 01 Chat | Every competitor supports context mentions. Without it, ARC chat is strictly less capable than Claude Code, OpenCode, Cursor, and Aider. Table stakes for chat-first tools. |
| 2 | **Implement ModeToggle (Plan/Build/Auto) component** | P0 — v0.1 must-have | 02 Plan/Tasks, 01 Chat | Plan mode is universal across competitors. Without it, ARC cannot restrict writes or paid calls. Currently spec-only, zero implementation. |
| 3 | **Implement git-backed snapshots and `/undo`/`/redo`** | P0 — v0.1 must-have | 07 Review/Apply | Every competitor with undo uses git. Building a custom snapshot system is fragile and duplicates git. Aider and OpenCode both use git revert successfully. |
| 4 | **Implement paid-call confirmation (CLI first)** | P0 — v0.1 must-have | 09 Provider Keys/Cost | Unique ARC differentiator — no competitor asks before paid API calls. Core to high-assurance positioning. Currently spec-only with no UI. |
| 5 | **Implement session cost accumulator (backend)** | P0 — v0.1 must-have | 09 Provider Keys/Cost | All cost display surfaces (status line, `/status`, Runs table) have no backend data source. `RunSummary.costUsd` exists in schema but nothing populates it. |
| 6 | **Add `arc providers test` command** | P0 — v0.1 must-have | 09 Provider Keys/Cost | Users cannot verify keys work without running a workflow. Creates friction and wasted runs. Simple HTTP health check solves this. |
| 7 | **Implement keyring for provider keys with explicit fallback** | P0 — v0.1 must-have | 09 Provider Keys/Cost | Spec promises keyring storage but `add_direct_key_account()` raises RuntimeError. Must ship or spec is dishonest. Graceful degradation for headless/SSH required. |
| 8 | **Implement policy.yaml loader and wire into execution path** | P0 — v0.1 must-have | 08 Config/Policy | Policy is entirely unimplemented — zero Python code for `.arc/policy.yaml` loading, validation, or enforcement. `RunProfile` is a parallel system not connected to policy model. |
| 9 | **Fix user config path mismatch (`~/.arc/` → `~/.config/arc-studio/`)** | P0 — v0.1 must-have | 08 Config/Policy | Spec says `~/.config/arc-studio/`, code uses `~/.arc/`. Must pick one. Recommend XDG-compliant path with dual-read migration. |
| 10 | **Add machine ID + user ID to trust binding** | P0 — v0.1 must-have | 10 Workspace Trust | Spec says trust binds to "canonical path + machine ID + user ID" but `trust.py` only stores path. Trust DB copied to another machine would incorrectly grant trust. |
| 11 | **Add parent folder trust** | P0 — v0.1 must-have | 10 Workspace Trust | VS Code supports this. Per-workspace approval is tedious for users with many repos under a common directory. UX friction point. |
| 12 | **Add protected paths within trusted workspaces (`.arc/`, `.git/`)** | P0 — v0.1 must-have | 10 Workspace Trust | Even trusted workspaces should protect their own trust/config markers from agent writes. Codex CLI does this. |
| 13 | **Add session list command (`/sessions`)** | P1 — v0.1 should-have | 11 Sessions/Daemon | Session resume without a session list is a significant UX gap. Every competitor has this. Straightforward implementation (enumerate session dirs). |
| 14 | **Add command aliases and fuzzy autocomplete** | P1 — v0.1 should-have | 12 CLI Command System | `/q` → `/exit`, `/s` → `/status`. Fuzzy autocomplete (`/conf` → `/config`) is universal across competitors. Low effort, high value. |
| 15 | **Add command queueing during active runs** | P1 — v0.1 should-have | 12 CLI, 01 Chat | Without queueing, user input during active run is lost or blocks. Claude Code and Cursor queue. `/stop` must execute immediately, others queue. |
| 16 | **Switch graph rendering to React Flow (not Cytoscape.js or custom SVG)** | P1 — v0.1 should-have | 05 Graph | Current custom SVG has no pan/zoom, no minimap, no virtualization, no accessibility. Will fail at ~50 nodes. React Flow is dominant (36.5K stars, 7.4M weekly installs), native React, built-in controls. |
| 17 | **Implement live graph state overlay via SSE** | P1 — v0.1 should-have | 05 Graph | Graph without live state is a static diagram — not a differentiator. 100ms batched tick from §11.4 is minimum viable live experience. |
| 18 | **Add status filters and inline expand to Runs panel** | P1 — v0.1 should-have | 06 Runs/Failure Recovery | SQLite index supports filtering. UI needs filter chips for status, runtime, date range. Inline expand provides one level of depth without separate panel. |
| 19 | **Use Theia's right sidebar for ARC panels (not custom 3-column layout)** | P1 — v0.1 should-have | 13 IDE Layout | Every competitor places agent panel in right sidebar. Fighting Theia's layout system to build custom 3-column arrangement is expensive and fragile. |
| 20 | **Add axe-core accessibility audits to E2E tests** | P1 — v0.1 should-have | 17 Testing/Observability | §14 specifies WCAG AA but zero accessibility tests exist. Axe-core catches basic violations in 5 minutes of setup. |

---

## 2. Must-Lock Contracts Before Implementation

These contracts must be stable before implementation begins. Changing them after code is written causes cascading rework.

### Protocol Contracts

| Contract | Status | Must Lock By | Notes |
|----------|--------|-------------|-------|
| **Event schema registry (ADR-004)** | Exists, needs `PHASE_HANDOFF` addition | Before v0.1 code | Add `PHASE_HANDOFF` event type; rename `HANDOFF` → `AGENT_DELEGATION` to resolve naming collision |
| **Session metadata schema** | Not defined | Before v0.1 session code | Define `metadata.yaml` schema with `schema_version`, required fields, workspace binding, daemon port, token file |
| **RunRecord schema (ADR-003)** | Exists, needs `cost_usd` population | Before v0.1 Runs panel | `cost_usd` field exists but nothing populates it. Define population source. |
| **Handoff payload shape (Appendix B)** | Reserved, needs `state_schema` and `handoff_id` | Before v0.2 handoff code | Add `state_schema` field for receiving runtime validation. Add `handoff_id` ULID. Mark immutable fields. |
| **Runtime manifest format (Appendix A)** | Exists, needs validation tests | Before v0.1 `/doctor` | Manifest parsing must be tested. Unknown major version rejection, required field validation. |
| **SSE streaming protocol** | Recommended in redesign plan, not locked | Before v0.1 chat code | Lock SSE as the streaming protocol for both CLI and IDE. Existing event broker infrastructure uses SSE. |
| **Daemon auth token lifecycle** | Mentioned in ADR-008, not defined | Before v0.1 daemon code | Token generation, rotation, storage in session `.token` file (mode 0600), invalidation on restart. |

### UI Component Contracts

| Contract | Status | Must Lock By | Notes |
|----------|--------|-------------|-------|
| **Input component props (mentions, attachments, queueDepth)** | Partially defined | Before v0.1 chat input | Add `mentions`, `attachments` (reserved), `queueDepth` props. Placeholder: "Ask ARC Studio or @mention files..." |
| **Card component variants** | Defined, needs diff preview and MCP metadata | Before v0.1 chat transcript | Add `diffPreview` to HITL card variant. Add MCP metadata to ToolCard. |
| **RunSummary interface** | Defined, needs `advancedTraceAvailable` removal | Before v0.1 Runs panel | Remove dead `advancedTraceAvailable` field. Add `failureContext` for expanded failure detail. |
| **FailureCard props** | Defined, needs expansion | Before v0.1 failure UI | Add `maxEvents`, `failureContext`, `costUsd`. Change `onRetry` label to "Retry with same input". |
| **DaemonStatusBadge states** | Defined, needs `orphaned-run` state | Before v0.1 status bar | Add `orphaned-run` state with `state.warning` tone and recovery action. |
| **HandoffCard component** | Reserved v0.2 | Before v0.2 handoff UI | Add `stateSchema`, `editableFields`, error states, recovery actions (`onRetry`, `onSkipPhase`, `onAbortPlan`). |

### Config/Policy Contracts

| Contract | Status | Must Lock By | Notes |
|----------|--------|-------------|-------|
| **ArcConfig schema (ADR-001)** | Exists, needs env var mapping completion | Before v0.1 config UI | Map all 40+ `ARC_*` env vars to config keys. Only 4 currently mapped. |
| **PolicyConfig schema** | Not implemented | Before v0.1 policy enforcement | Define `PolicyConfig` Pydantic model with `approvals` sub-model. 3-level precedence (project > user > defaults). |
| **"Cannot weaken" enforcement algorithm** | Spec-only | Before v0.1 policy code | Project policy cannot reduce strictness below user policy for `shell_exec`/`trust_changes`. Define strictness ordering: `deny` (3) > `ask` (2) > `auto` (1). |
| **MCP config schema (`.arc/mcp.json`)** | Not defined | Before v0.2 MCP code | Reserve in v0.1. Separate from `.arc/config.yaml`. Match industry convention. |
| **Router mode config** | Not defined | Before v0.2 router code | Add `router.mode` to config: `manual`/`suggest`/`auto-on-confirm`/`auto`. Default `manual` in v0.1, `suggest` in v0.2. |

### Storage Contracts

| Contract | Status | Must Lock By | Notes |
|----------|--------|-------------|-------|
| **Session directory structure** | Partially defined | Before v0.1 session code | Define per-session files: `metadata.yaml`, `transcript.jsonl`, `runs.jsonl`, `queue.jsonl`, `.lock`, `.token`. Platform-specific root paths. |
| **Frame storage (HotLoop)** | Not defined | Before v0.2 HotLoop code | Reserve: frames stored in workspace-local cache (not JSONL). Traces reference frames by ID. |
| **Handoff persistence** | Not defined | Before v0.2 handoff code | Handoff documents stored in session directory as JSON files. Edited handoffs create new files with `original_handoff_id`. |
| **Trust DB format** | Exists, needs machine/user ID | Before v0.1 trust enforcement | Add `machine_id`, `user_id`, `trusted_at` to `~/.arc/trusted-workspaces.json` entries. |

---

## 3. v0.1 Implementation Scope

**Bounded. No expansion.** v0.1 ships a chat-first CLI with SwarmGraph default, basic IDE panels, and core security infrastructure.

### Ships in v0.1

#### Chat Core
- `arc-studio` launches into chat REPL with no arguments
- Streaming output via SSE with cursor animation
- Tool call cards, HITL cards, paid-call cards in transcript
- Plan/Build/Auto mode toggle (Tab in CLI, button in IDE)
- Session lifecycle: ULID IDs, JSONL journaling, auto-resume on crash
- `@file` and `@folder` mention syntax with autocomplete (max 16K/32K tokens)
- Message queueing during active runs (max depth 5, `/stop` executes immediately)
- Intent routing: "ask" (LLM response) vs "run" (workflow execution) — keyword-based in v0.1
- `/compact` manual context compaction with skill carry-forward
- Command aliases (`/q`, `/s`, `/h`, `/d`, `/w`, `/c`)
- Fuzzy autocomplete for slash commands
- Command history (up-arrow recall)
- 20+ slash commands across 5 categories
- `arc-studio advanced <cmd>` passthrough to Python CLI
- Chat uses configured provider model (no separate chat model)

#### CLI Surface
- `arc-studio "query"` launches with initial prompt
- `arc-studio run "query"` non-interactive mode with exit codes
- `arc-studio -c` continue last session, `-r <id>` resume specific
- `arc-studio --version` shows CLI, daemon, protocol, manifest, bundled SwarmGraph versions
- `arc-studio --help` shows < 20 lines
- `/sessions` lists recent sessions
- `/undo` and `/redo` (git revert of ARC commits)
- `arc providers test <provider>` validates key
- `arc-studio doctor install` install-specific diagnostics
- Shell completions for bash/zsh/fish
- Exit codes: 0 (success), 1 (error), 2 (diagnostic fail), 3 (run fail), 4 (denied), 130 (interrupted)

#### Provider Keys & Cost
- Keyring storage for provider keys with explicit fallback to env-only mode
- Key provenance display: `env`, `keyring`, `file`, `unset`
- Session cost accumulator (sum of completed run costs)
- Cost display in status line: `cost $X.XX`, `cost $0.00`, or `cost ?`
- Paid-call confirmation in CLI (blocking prompt)
- `CostCeilingBadge` shows `cost ?` for paid providers in v0.1 (no estimation)
- Local providers (Ollama) show `cost $0.00`, skip confirmation
- Ollama detection and test
- Expanded redaction patterns (Azure, Google, Bedrock, OpenRouter, generic `sk-` prefix)

#### Workspace Trust & Security
- Default UNTRUSTED for all new workspaces
- Trust stored outside workspace at `~/.arc/trusted-workspaces.json`
- Trust binds to canonical path + machine ID + user ID
- Parent folder trust ("Trust Parent" cascades to subfolders)
- Protected paths: `.arc/`, `.git/` read-only even in trusted workspaces
- Untrusted mode: read-only chat/context; blocks writes, shell, paid calls, runtime
- `/workspace trust`, `/workspace untrust`, `/workspace trust-status` commands
- Multi-root workspace: adding untrusted folder switches entire workspace to untrusted
- Empty window (no folder): trusted by default
- `allow_if_no_db` parameter removed from `ensure_trusted()`

#### Config & Policy
- 5-level config precedence: CLI > env > workspace > user > defaults
- User config path: `~/.config/arc-studio/config.yaml` (with dual-read migration from `~/.arc/`)
- `PolicyConfig` Pydantic model with `approvals` sub-model
- 3-level policy precedence: project > user > defaults
- "Cannot weaken" enforcement for `shell_exec` and `trust_changes`
- Policy wired into `JobSupervisor.start_run()` and HITL flow
- Policy is file-only in v0.1 (edit `.arc/policy.yaml` directly)
- `phase_advance` reserved in model, always resolves to `ask`
- IDE Config tab (sidebar) with Runtime, Model, Providers, Workspace Trust, Profiles, Graph, Advanced sub-tabs
- CLI `/config` interactive TUI form

#### Graph Visualization
- React Flow (@xyflow/react) for graph rendering
- Dagre layout (default), elkjs alternative
- Pan, zoom, fit-to-view, minimap (>20 nodes)
- Node types with spec colors: queen, worker, tool, decision, HITL, terminal
- Live state overlay via SSE (100ms batched tick)
- Running node pulse animation, active edge color-fill animation
- Node inspector panel (ID, runtime, state, event count, last event)
- Graph export (PNG/SVG)
- ARIA: `role=application`, spoken descriptions
- Runtime-specific rendering (LangGraph `(coalesced)` badge)
- CLI inline graph with box-drawing characters (§7.6)
- Graph opens in main editor area during active runs (not sidebar)

#### Runs Panel
- Run list table: Run ID, Runtime, Status, Cost, Duration, Failure node, Summary
- Status filter chips: All, Running, Completed, Failed, Cancelled
- Runtime filter, date range filter (Today, 7d, 30d, All)
- Inline row expand showing full RunSummary and failure context
- FailureCard with cost display, configurable last-N events (default 5, range 3-20)
- Delete with confirmation modal
- Export as JSON (full RunRecord + audit refs)
- "Open advanced trace" → `arc-studio advanced runs trace <id>`
- 50 runs per page, load-more button
- No event timeline, no JSON viewer, no replay scrubber in v0.1

#### Review/Apply/Rollback
- Per-hunk approve/reject/edit-first workflow
- "Apply Approved" creates git commit: `[ARC Studio] Applied changes from run {run_id}`
- "Approve All" and "Reject All" bulk actions
- `/undo` reverts last ARC commit via `git revert`
- `/redo` reverts the last undo
- Git repo detection; non-git workspaces show warning
- Conflict detection before apply (dry-run patch)
- Concurrent edit warning (file mtime changed after diff generation)
- Edit First opens file in editor with proposed change
- Review session persistence (hunk decisions survive panel close/reopen)
- Partial apply failure handling (show succeeded/failed, offer retry/skip/rollback)
- Binary file detection
- Uses Theia's built-in diff editor (not custom Monaco viewer)
- Companion Review panel in sidebar for file/hunk list and approval actions

#### Sessions & Daemon
- ULID session IDs, per-platform session directories
- `metadata.yaml` with defined schema (schema_version, workspace, runtime, model, mode, timestamps)
- `transcript.jsonl` journaling (every turn journaled before rendering)
- File-based session lock with stale detection (PID + timestamp, 30s timeout)
- CLI and IDE share same workspace session by default
- `{N} clients attached` indicator
- Daemon auto-start from `stopped` state only
- 8-state daemon state machine (not-installed, stopped, starting, running, stale, port-conflict, unreachable, version-mismatch)
- Daemon port configurable via `daemon.port` (default 7777, fallback scan 7777-7787)
- Auth token per session in `.token` file (mode 0600)
- Daemon crash mid-run marks run as `orphaned`; recovery prompt on restart
- Cross-workspace resume warning
- Session retention: auto-prune after 30 days, max 50 sessions

#### IDE Layout
- ARC panels in Theia's right sidebar as tabbed views: Chat, Runs, Config
- Graph widget opens in main editor area during active runs
- Theia's status bar extended with ARC segments: trust, runtime, mode, daemon, cost
- First-launch default: Chat tab open, all others closed
- Command palette primary navigation (`Ctrl/Cmd+Shift+P` > "ARC: Open ...")
- Keyboard shortcuts: `Ctrl/Cmd+;` focus chat, `Ctrl/Cmd+Enter` send, `Ctrl/Cmd+Shift+H` toggle Graph, `Ctrl/Cmd+Shift+U` toggle Runs
- Panel layout persistence via Theia storage
- Sidebar resizable (default 420px, min 320px, max 55vw)

#### Install & Distribution
- `npm install -g arc-studio` (thin shim triggers pip/pipx install)
- `pipx install agent-runtime-cockpit` (canonical Python path)
- Python >=3.11 prerequisite
- SwarmGraph bundled and vendored (version visible in `/version`)
- `/update --check` prints upgrade command without self-modifying
- Version mismatch detection on startup (warn + continue, don't block)
- Shell completions for bash/zsh/fish
- Uninstall documented for npm and pipx paths

#### Testing & Docs
- axe-core accessibility audits in Playwright E2E
- Manifest validation tests (valid v1, unknown major, missing fields)
- Redaction E2E test (inject fake secrets, verify redaction marker in all surfaces)
- Daemon state machine tests (start, healthy, crash, restart, orphan recovery)
- Automated screenshot generation via Playwright
- `docs/onboarding.md` (5-step getting started guide)
- `docs/cli-migration.md` (old→new command mapping)
- Docs link checker in CI
- All existing tests pass: 550 Python, 239 TypeScript, 12 E2E

### Explicitly Out of v0.1 Scope

| Feature | Why Out | Reserved In Protocol? |
|---------|---------|----------------------|
| **Trace UI (event timeline, JSON viewer, replay scrubber)** | Product positioning is chat-first with graph overlay, not observability-first. Advanced fallback exists. | Yes — v0.3 audit explorer |
| **Planner (multi-phase plan generation)** | Requires dedicated planning LLM call, cost estimation, handoff docs. Significant feature. | Yes — v0.2 |
| **Phase view and Loop trace view in Tasks** | Require planner and HotLoop respectively. | Yes — v0.2 |
| **HotLoop runtime, Device panel, Frames panel** | Requires vision model, target lifecycle, novel loop architecture. | Yes — v0.2 (schemas reserved) |
| **Runtime router suggestions** | Requires manifest-driven eligibility scoring, prompt-signal matching. | Yes — v0.2 |
| **Handoff protocol (inter-runtime phase transfer)** | Requires planner, router, and at least 2 viable runtimes. | Yes — v0.2 (payload shape reserved) |
| **MCP server configuration and tool consumption** | Requires stable chat/tool-card foundation first. | Yes — v0.2 (schema reserved) |
| **ACP server mode** | Distribution play, not core product. | Yes — v0.3 (types reserved) |
| **`@symbol` mentions** | Requires LSP integration or AST parsing. | Yes — v0.2 |
| **Image/multimodal input** | Requires image handling, base64 encoding, provider multimodal support. | Yes — v0.2 (protocol shape reserved) |
| **Chat history browsing** | Session resume is sufficient for v0.1. | Yes — v0.2 (`/sessions` ships in v0.1) |
| **`/share` conversation** | Requires hosted viewer or export format. | Yes — v0.2 |
| **Multi-session (parallel)** | Significant session lifecycle complexity. | Yes — v0.2 |
| **Skills/custom slash commands** | Requires directory watching, frontmatter parsing, dynamic context injection. | Yes — v0.2 |
| **Inline diffs in editor (Cursor pattern)** | Requires deep Theia/Monaco integration. | Yes — v0.2 |
| **Retry-with-edit for failed runs** | Requires protocol changes and UI for editing run parameters. | Yes — v0.2 |
| **Budget ceiling enforcement** | Requires ceiling config, real-time checking, ceiling-exceeded UX. | Yes — v0.2 |
| **Token estimation (local tokenizer)** | Requires shipping tokenizer libraries (~8MB bundle). | Yes — v0.2 |
| **Graph editing** | Requires bidirectional sync with Python source code. | Yes — v0.3+ |
| **Graph replay/time travel** | Explicitly excluded by spec §11.5. | Yes — v0.3 audit explorer |
| **Second-terminal alt-screen graph** | Requires child pty management. | Yes — v0.2 |
| **Mobile/narrow window handling** | Theia browser app is not responsive. | Yes — v0.2 |
| **Drag-to-tab panel rearrange** | Theia tab bar DnD API limited. | Yes — v0.2 |
| **Custom activity bar** | Duplicates Theia's left sidebar. | Yes — v0.2 polish |
| **Electron desktop app** | ADR-008 explicitly post-v0.1. | Yes — v0.2 spike, v0.3 app |
| **Homebrew formula** | npm + pipx cover primary audience. | Yes — v0.2 |
| **curl install script** | Security review needed for piped-to-bash. | Yes — v0.2 |
| **Auto-update** | Self-modifying installs are risky for alpha. | Yes — v0.2 |
| **Release channels (latest/stable)** | Requires release infrastructure. | Yes — v0.2 |
| **LlamaIndex runtime** | Hidden from default UI. Detection/export only. | No — not in default v0.1 |
| **LM Arena runtime** | Hidden from default UI. Not shown. | No — not in default v0.1 |
| **AG2 runtime** | Hidden from default UI. Detection/export only. | No — not in default v0.1 |

---

## 4. v0.2 Reserved Scope

v0.2 builds on stable v0.1 foundation. These items are reserved but not committed — scope will be refined after v0.1 user feedback.

### Planner & Tasks
- Multi-phase plan generation (planning LLM call)
- Phase view in Tasks panel (PhaseCard with cost ceilings, acceptance criteria, handoff refs)
- Plan approval flow with audit trail linkage
- Plan outputs persisted as JSON in session directory
- Acceptance criteria per phase (optional, verifiable by runtime)
- Plan editing deferred to v0.3

### Handoff Protocol
- `PHASE_HANDOFF` event emission at phase boundaries
- Handoff payload validation with `state_schema`
- Handoff persistence in session directory
- HandoffCard UI with edit/confirm/cancel/retry/skip/abort actions
- Failed handoff recovery: pause for user intervention
- Redaction of `state` values and `references` URLs in handoff display
- Immutability of structural fields (`prior_audit_links`, `from_runtime`, `to_runtime`, `handoff_version`, `handoff_id`)

### Runtime Router
- Manifest-driven eligibility scoring (replaces hardcoded `AUTO_PRIORITY`)
- Static prompt-signal matching (keyword/regex against manifest verbs/patterns)
- Router mode config: `manual`/`suggest`/`auto-on-confirm`/`auto`
- Non-modal suggestion card: "This looks like UI work. HotLoop iterates faster here. Switch?"
- "Always for this project" persistence in `.arc/router-prefs.yaml`
- Panel slot enforcement (runtime switch applies manifest `slot_preferences`)
- Cost as tiebreaker (not primary signal)
- `/doctor runtime` shows eligibility scores
- LLM-based prompt analysis reserved for v0.3

### HotLoop
- Screenshot capture mechanism (at least React Native/Expo)
- Device panel: live screenshots from connected target
- Frames panel: scrubbable visual diff timeline
- Loop tick lifecycle: observe → diff → decide → act → repeat
- Loop stop conditions: max iterations, cost ceiling, user interrupt, convergence
- Frame cache (workspace-local, separate from JSONL)
- Rollback mechanism (hot reload or git-based)
- All 5 reserved events with payload schemas
- Cost visibility: per-tick cost, cumulative cost, cost ceiling
- Keyboard shortcuts: focus Device, focus Frames, rollback, pause/resume
- Target platform: React Native (Expo) full support; bare RN and Flutter partial

### MCP Integration
- `.arc/mcp.json` config format (workspace and user scope)
- `arc mcp add/list/remove/get/status/debug` CLI commands
- MCP server lifecycle: start, stop, reconnect, health check
- MCP tool discovery (`tools/list`) and injection into LLM tool set
- MCP tool call routing (`tools/call`)
- MCP tool results in existing ToolCard with MCP metadata
- MCP output size warnings (10K token threshold)
- MCP permissions mapped to Plan/Build/Auto modes
- MCP server trust confirmation on first start
- MCP sandboxing via isolation providers
- MCP resources as `@` context mentions
- MCP prompts as slash commands
- MCP elicitation dialogs in chat
- OAuth 2.0 for remote MCP servers (DCR)

### Chat Enhancements
- `@symbol` mentions (LSP-based symbol resolution)
- Image/multimodal input (paste/drag-drop)
- Chat history browsing (`/sessions` with search/filter)
- `/share` conversation (export or hosted link)
- Skills/custom commands (`.arc/commands/<name>.md`)
- Auto-compaction (triggered at 90% context)
- Session fork (`/fork` creates branch from checkpoint)
- Inline diffs in editor (Cursor/Windsurf pattern)
- Checkpoint timeline UI (Windsurf-style)

### Provider & Cost
- Budget ceiling configuration (`session_max_cost_usd`, `run_max_cost_usd`)
- Budget ceiling enforcement (blocks runs when exceeded)
- IDE paid-call confirmation dialog (async modal)
- SwarmGraph gateway quota display in `/providers` and `/status`
- Hardcoded per-model cost estimates (with staleness warning)
- Token count display in Runs table
- Cost history / aggregate view

### Review/Apply
- Inline diffs in Theia editor (not separate panel)
- Branch-based isolation (agent works on feature branch)
- Checkpoint timeline for applied changes

### Config & Policy
- Schema version migration (v1 → v2)
- `$schema` YAML schema for editor autocomplete
- Local config file (`.arc/config.local.yaml`, gitignored)
- Hot-reload for UI config fields
- IDE Policy tab with validation
- Granular policy rules (pattern matching like OpenCode)
- Config backup on save (5 timestamped copies)
- Managed/org config (MDM/registry support)

### Sessions & Daemon
- Session export/import (portable archive)
- Session fork
- Trust expiry (90-day re-confirmation)
- Symlink escape detection
- PARTIAL trust level implementation
- Filesystem deny-read profiles
- Trust change audit log
- Mounted drive warnings

### IDE Layout
- Tasks as separate panel (with Phase and Loop views)
- Custom activity bar icons
- Drag-to-tab panel rearrange
- Mobile/narrow window handling (>=480px)

### Install & Distribution
- Homebrew tap (not cask)
- curl install script (after security review)
- Release channels (latest/stable)
- Electron packaging spike (ADR-008 P1-P2)

### Testing
- Visual regression tests (Playwright screenshot comparison)
- Chaos/resilience tests (daemon crash, SSE reconnect, network timeout)
- HITL E2E flow test
- Eval batch E2E flow test
- Session persistence E2E test
- CLI REPL pexpect tests

---

## 5. v0.3+ Deferred Scope

These items are explicitly deferred. Do not implement in v0.1 or v0.2.

### Audit Explorer & Trace UI
- Full trace UI with nested span tree
- Replay scrubber with time-travel
- Event JSON viewer in default UI
- Span-level replay from failure point
- Graph replay/checkpoint navigation
- Full-text search across run events
- OTel audit trail for trust/security events

### Advanced Routing
- LLM-based prompt classification for router
- Cross-runtime task decomposition suggestions
- Learning from user overrides (weight adjustment)

### Advanced Handoff
- Handoff rollback (undo completed handoff, return to previous phase)
- Handoff templates for common transitions
- Handoff diff view (original vs edited)
- Cryptographic signing of handoff documents
- Parallel phase handoff (fan-out/fan-in)
- Cross-machine handoff

### Advanced Planner
- Plan editing (phase revision, re-approval, plan diff)
- Cloud planning (Ultraplan equivalent)
- Plan comparison (side-by-side plan revisions)

### ACP Server Mode
- `arc acp serve` — ARC as ACP-compatible agent server
- JSON-RPC over stdio for external editors (Zed, JetBrains, Neovim)
- ACP session management, tool mapping, streaming, cancellation
- Tested against Zed, JetBrains IDEs, Avante.nvim

### MCP Advanced
- MCP-to-SwarmGraph tool adapter (MCP tools as SwarmGraph workers)
- MCP server marketplace / curated gallery
- Per-agent MCP tool scoping
- Auto-import from Claude Desktop / VS Code configs

### Graph Advanced
- Graph editing (bidirectional sync with Python source)
- Subgraph collapse/expand (queen/worker clusters)
- Graph comparison mode (side-by-side runs)
- Graph density modes (compact/comfortable/spacious)
- Second-terminal alt-screen graph

### Chat Advanced
- Web/URL context (`@url` mention)
- Multi-session (parallel agents)
- Message editing
- Chat search (full-text across sessions)
- Skills with subagent execution and dynamic context injection
- Auto-review for approval requests (LLM-based reviewer)

### Security Advanced
- Remote workspace trust (SSH, Dev Containers)
- Session encryption at rest
- Binary integrity verification (GPG/Sigstore)
- Cross-machine trust sync

### Distribution
- Electron desktop app (bundled Python, auto-start daemon)
- Homebrew cask
- apt/dnf/apk repositories
- Auto-update with release channels
- curl install script with signed manifests

### Testing Advanced
- Cross-platform E2E matrix (Ubuntu, macOS, Windows)
- Performance benchmarks (graph render, run list, SSE throughput)
- Mutation testing on core modules
- Fuzz testing for manifest parsing
- Load testing for event broker

### Observability
- Cost alerting (threshold notifications)
- Run aggregate stats (p50/p95 duration, success rate)
- Run comparison view (side-by-side diff)
- Cost export to CSV/JSON
- Cost dashboard (local)

---

## 6. Rejected Ideas

| Idea | Why Rejected | Reconsider When |
|------|-------------|-----------------|
| **Cytoscape.js for graph rendering** | React Flow is better suited: native React, larger community (36.5K vs 9.5K stars), built-in minimap/pan/zoom, dagre plugin, better TypeScript. Current SVG approach also rejected — no pan/zoom, no virtualization, will fail at ~50 nodes. | Never — React Flow is the decision. |
| **Custom snapshot system (not git) for undo** | Git already does this perfectly. Every competitor with undo uses git. Custom system would be fragile, lack conflict detection, lack universal tooling. | Never — git is the decision. |
| **Plaintext key storage in config files** | Security risk. Config files are often committed to git or backed up to cloud. | Never — keyring + env vars only. |
| **Pre-call token estimation in v0.1** | Requires shipping tokenizer libraries (~8MB). Estimates are often wrong. Creates false confidence. | v0.2 if user demand justifies bundle size. |
| **Real-time cost streaming** | Provider APIs don't stream cost. Cost only known after call completes. | Never — post-run cost is sufficient. |
| **Multi-key support per provider** | Adds complexity to key management, routing, audit. Most users have one key per provider. | Post-v0.1 when multi-tenant architecture exists. |
| **Automatic provider failover based on cost** | Requires real-time cost comparison (needs estimates, which are rejected). Changes model behavior silently — violates "honest" brand. | Never — manual switching only. |
| **LLM-based routing in v0.2** | Adds latency (1-3s), cost ($0.001-0.01/call), opacity. Static matching is sufficient for v0.2 where 2-3 runtimes are viable. | v0.3 for ambiguous prompt classification. |
| **Fully automatic routing as default** | Violates "honest" and "bounded" brand attributes. Runtime switching changes execution semantics, cost, audit guarantees. | Never — default is `suggest` mode, user must approve. |
| **Cost-primary routing** | Would route to cheaper but wrong runtimes. A cheap wrong result is worse than a correct expensive one. | Never — cost is tiebreaker only. |
| **Auto-switching mid-run** | Would corrupt execution state and break audit continuity. | Never — only between runs or at phase boundaries. |
| **Unified "handoff" event for intra and inter-runtime** | Fundamentally different payload shapes, consumers, lifecycle semantics. Separate types are cleaner. | Never — `AGENT_DELEGATION` (intra) and `PHASE_HANDOFF` (inter) are separate. |
| **Automatic handoff state inference** | Fragile and opaque. When it fails, users cannot debug why. Explicit `state_schema` is visible and debuggable. | Never — explicit schema is the decision. |
| **Handoff as first-class run (separate run_id)** | Handoffs are transitions within a session, not independent runs. Separate run_ids fragment session timeline. | Never — handoffs are events within session transcript. |
| **Cryptographic signing of handoff documents (v0.2)** | SwarmGraph HMAC audit chain already provides integrity. Separate signing doubles key management. | v0.3 if multi-machine handoff becomes a requirement. |
| **Handoff rollback (v0.2)** | Requires previous runtime to support checkpoint resume. Runtime-specific, not universal. | v0.3 for runtimes that support checkpoint. |
| **Editable graph in v0.1** | Bidirectional sync with Python source is complex and error-prone. LangGraph Studio is also read-only. | v0.3+ after runtime/protocol is stable. |
| **3D graph visualization** | Gimmicky, poor accessibility, no practical benefit. All competitors use 2D. | Never. |
| **No-code workflow builder** | Explicitly deferred in IMPLEMENTATION_PLAN. Distracts from high-assurance cockpit work. | Post-v0.1 if product direction changes. |
| **Graph-as-code sync** | Bidirectional graph↔Python sync is complex. Graph is visualization, not source of truth. | Never — keep it read-only. |
| **Custom 3-column layout replacing Theia editor** | Users need editor for code, diffs, Graph. Fighting Theia's layout system is expensive. | Never — use Theia's right sidebar. |
| **Separate ARC status bar** | Theia already has a status bar. Second bar wastes 24px and creates ambiguity. | Never — contribute to Theia's status bar. |
| **Custom activity bar** | Theia already has left sidebar with view icons. Duplicates chrome. | v0.2 polish only if needed. |
| **Six panels for v0.1** | Too much surface. Tasks Step view is thin content. Review/Apply duplicates Theia diff editor. | Never — 4 panels for v0.1: Chat, Graph, Runs, Config. |
| **40/60 Chat/Graph split in sidebar** | At sidebar width, Chat gets ~168px, Graph ~252px. Unusable for both. | Never — Graph opens in main area. |
| **Custom Monaco diff viewer** | Theia already includes Monaco and full diff editor. Building parallel viewer is expensive duplication. | Never — use Theia's diff editor. |
| **Mobile/narrow handling in v0.1** | Theia browser app is not responsive. Requires system-wide responsive work. | v0.2. |
| **Drag-to-tab rearrange in v0.1** | Theia tab bar DnD API limited. Fixed tabs match Cursor/Windsurf. | v0.2 polish. |
| **Per-hunk undo after apply** | Complex partial revert logic, confusing git history. Per-hunk control available before apply. | Never — unit of undo is the commit (batch). |
| **Auto-apply without review in Build mode** | Violates high-assurance principle. Explicit review before write is core design. | Never — Auto mode has policy-driven auto-approve. |
| **Three-way merge UI for conflicts** | Complex, out of scope. Standard conflict markers in editor are sufficient. | Never — users are developers who understand git. |
| **Non-git fallback snapshots** | Significant complexity for edge case. Non-git workspaces are rare in target audience. | Never — warning + `git init` suggestion is sufficient. |
| **Branch-based isolation (v0.1)** | Significant git management complexity. | v0.2. |
| **Cloud-synced sessions** | Requires auth, storage infrastructure, privacy review. ARC is local-first. | Post-v0.1 as optional feature. |
| **Real-time collaborative sessions** | CRDTs, conflict resolution, presence indicators. Different product. | Never — multi-client attach (CLI+IDE for same user) is sufficient. |
| **Session encryption at rest (v0.1)** | Key management, recovery, platform keychain integration. | v0.3. |
| **Session share links (v0.1)** | Hosted service (privacy implications) or local export (less useful). | v0.2 export/import first, share links on top. |
| **Daemon as system service** | Installation complexity, security model change (always-on loopback server). | Never — auto-start on demand is correct. |
| **Session branching with merge** | Git-style session branching. Merge semantics for conversations undefined. | Never — fork is sufficient. |
| **Multiple daemons per machine** | Complicates port management, session discovery, resource allocation. | Never — one daemon per workspace. |
| **Session replay as live re-execution** | Requires deterministic LLM outputs, tool idempotency, environment snapshots. | v0.3+ at best. |
| **Session-level undo/redo** | Ambiguous — undo tool calls? File edits? LLM responses? | Never — git-level undo is correct. |
| **WebSocket instead of SSE** | SSE is simpler, works with Theia HTTP, supports replay. WebSocket adds complexity. | Never — SSE is the decision. |
| **Subcommand nesting for slash commands** | All competitors use flat namespaces. Nesting adds cognitive overhead. | Never — flat is the decision. |
| **Interactive subshell for advanced mode** | Confuses chat-first default, requires separate state management. | Never — one-shot passthrough is correct. |
| **`/update` that self-modifies (v0.1)** | Risky across npm/pipx/brew. | v0.2 when distribution is stable. |
| **Command marketplace / plugin registry** | Premature. No plugin loading mechanism exists. | Post-v0.1 when file-based commands are stable. |
| **Natural language command parsing** | Chat loop handles natural language. Slash commands are for explicit control. | Never — mixing creates ambiguity. |
| **Man pages for CLI** | Chat-first tools don't need man pages. | Never. |
| **MCP as SwarmGraph workers (v0.2)** | MCP tools are LLM-facing, not runtime workers. Wrapping adds latency without clear benefit. | v0.3 if consensus over MCP outputs is needed. |
| **ACP client mode in ARC IDE** | ARC IS the cockpit. Delegating to external agents dilutes positioning. | Never. |
| **MCP server marketplace (v0.2)** | Requires curation, security review, publisher verification. | v0.3+ after MCP consumption is stable. |
| **MCP auto-import from other tools** | Import logic adds maintenance burden as formats evolve. | v0.3 if demand exists. |
| **MCP as replacement for built-in tools** | Built-in tools are tightly integrated with permissions, trust, cost, audit. | Never — MCP is supplementary. |
| **ACP as primary chat protocol** | ARC has working JSON-RPC/SSE architecture. ACP is for external editor integration. | Never — internal protocol stays. |
| **MCP server hosting platform** | ARC is a cockpit, not an MCP hosting provider. | Never. |
| **HotLoop as visual regression CI tool** | Playwright and Chromatic solve this. HotLoop's value is agent iteration loop. | Never. |
| **Multi-device / device farm management** | Separate product (BrowserStack, Firebase Test Lab). | Never. |
| **Performance profiling overlays in HotLoop** | Flutter/Chrome DevTools already do this. HotLoop's frame timeline is for visual iteration. | Never. |
| **HotLoop without vision model** | Loop requires visual understanding. Without vision model, degrades to blind automation. | Never — disable if no vision model. |
| **Embedding screenshots in JSONL traces** | Binary data bloats traces, breaks append-only model. | Never — frames in separate cache, traces reference by ID. |
| **HotLoop for non-UI workloads** | Category error. Non-visual workloads belong in SwarmGraph. | Never. |
| **HotLoop as Storybook replacement** | Different purpose. Storybook is component dev; HotLoop iterates on running UI. | Never. |
| **Automatic UI code generation from screenshots** | Separate product. HotLoop's "action" is targeted modification, not full code gen. | v0.3+ at earliest. |
| **HotLoop-specific trace store** | Fragments storage architecture, duplicates ADR-003. | Never — use existing trace store. |
| **HotLoop in v0.1** | v0.1 scope is already large. HotLoop requires vision model, target lifecycle, novel loop. | Never — v0.2 is correct. |
| **Bundling Python in npm package** | Complex platform-specific builds, large tarball (50-100MB), no competitor does this for Python backends. | Never — thin shim + pip install is the decision. |
| **Auto-update in v0.1** | Auto-updating Python packages through npm is fragile. v0.1 is alpha. | v0.2 when release channels exist. |
| **Homebrew cask in v0.1** | Homebrew expects stable releases. Alpha is poor fit. | v0.3 when stable releases exist. |
| **curl install script in v0.1** | Piping curl to bash is security concern. Needs review. | v0.2 after security review. |
| **Electron desktop app in v0.1** | Explicitly out of scope. Daemon bundling spike not run. | v0.2 spike, v0.3 app. |
| **Release channels in v0.1** | Requires release infrastructure. Alpha doesn't need latest/stable distinction. | v0.2. |
| **Binary integrity verification in v0.1** | GPG signing infrastructure, key management, CI changes. | v0.3 when enterprise adoption is a goal. |
| **apt/dnf/apk repos in v0.1** | Signing keys, repo hosting, maintenance. Python tools rarely use apt/dnf. | v0.3 if Linux enterprise adoption requires. |
| **`arc-studio install` command** | Uncommon pattern. npm/pipx handle installation. | Never. |
| **Cypress E2E framework** | Playwright already configured. Second framework is duplication. | Never. |
| **Coverage enforcement gate** | 61.84% coverage, target 70%. Gating blocks PRs without quality improvement. | After 70% coverage reached. |
| **React component snapshot tests** | Source-pattern contracts sufficient. Snapshots brittle and Theia-version-dependent. | Never. |
| **Pixel-perfect terminal UI tests** | Terminal rendering depends on emulator, font, width. Test content, not pixels. | Never. |
| **Mutation testing** | High CI cost, low ROI at current coverage. | After 70% coverage. |
| **Full jsdom-based Theia testing** | Theia runtime cannot be adequately mocked. Source-pattern + Playwright is correct. | Never. |
| **Real provider call E2E tests in CI** | Paid calls in CI are unacceptable cost/risk. | Never — keep opt-in and nightly. |
| **E2E tests for every adapter** | Combinatorial explosion. Test SwarmGraph + one adoption adapter. | Never — unit/conformance for others. |
| **Trust based on git remote URL** | Remotes can be changed, forked, spoofed. Path-based trust is more reliable. | Never. |
| **Trust based on file hash/signature** | Impractical for workspaces that change constantly. | Never. |
| **Per-file trust granularity** | Too complex. Workspace-level is correct for agent cockpit. | Never. |
| **Trust expiry shorter than 90 days** | Too much UX friction. "Trust fatigue." | Never — 90 days is the minimum. |
| **Automatic trust for version-controlled folders** | Git repo can be cloned from any source. Version control is not evidence of trustworthiness. | Never — keep explicit approval. |
| **Trust inheritance from GitHub org** | Requires network calls and external identity. | Never — local-first tool. |
| **Biometric/2FA for trust approval** | Overkill for local dev tool. Machine ID + user ID + explicit approval is sufficient. | Never. |
| **Trust scoring based on content analysis** | Speculative. Requires ML-based analysis. | Never — not a priority. |
| **Separate trust levels per runtime** | Overly complex. Trust is workspace-level property. | Never. |
| **`--unsafe` bypass for trust** | Trust is not optional. `--unsafe` requires explicit confirmation. | Never. |
| **Trust based on workspace age** | Time is not evidence of trust. Malicious workspace can sit for 30 days. | Never. |
| **Switch config format to JSON or TOML** | YAML already implemented, supports comments, matches Python ecosystem. ADR-001 decided this. | Never — YAML is the decision. |
| **8-level precedence like OpenCode** | Overly complex. 5-level model covers all practical cases. | Never. |
| **Policy UI in v0.1** | Security-relevant. File-only editing forces deliberate review. | v0.2. |
| **Config hot-reload in v0.1** | File watching, state invalidation, race conditions. | v0.2 for cosmetic config. |
| **Auto-migrate `~/.arc/` to `~/.config/arc-studio/`** | Silent file moves break scripts. Dual-read with deprecation warning is safer. | Never — dual-read is the decision. |
| **Merge policy into config.yaml** | Security-relevant, should be reviewable independently. Separate files enable separate git review. | Never — separate is correct. |
| **Inline secrets in config** | Violates security model. Env vars and keyring are correct. | Never. |
| **Per-agent policy in v0.1** | Premature. No multi-agent UI in v0.1. | v0.2+. |
| **Managed/org config in v0.1** | Platform-specific code (macOS plist, Windows registry). | v0.2. |
| **Variable substitution (`{env:VAR}`)** | Adds parsing complexity. Env var override system covers primary use case. | v0.2. |
| **Config diff/preview UI** | File-based config with git diff covers this. | v0.2+. |
| **Config export/import/sharing** | Requires org/managed config infrastructure first. | v0.2+. |
| **Default Trace UI in v0.1** | Explicitly out of scope. Product positioning is chat-first with graph overlay. | v0.3 audit explorer. |
| **Event timeline / Gantt chart in Runs (v0.1)** | Requires event-level timestamp indexing, significant rendering work. Prefect/Dagster have this because they're pipeline tools; ARC v0.1 is chat-first cockpit. | v0.3 if user demand validates. |
| **Event JSON viewer in default UI (v0.1)** | Power-user territory. Advanced CLI provides it. | v0.3 or never. |
| **Span-level replay from failure point (v0.1)** | Requires runtime support (SwarmGraph checkpoint semantics). | v0.3+. |
| **Run comparison view (v0.1)** | Requires selection UI, diff rendering. Most v0.1 users have few runs. | v0.2. |
| **Soft-delete with trash/recycle bin** | Storage complexity (trash table, retention, purge). Confirmation modal is sufficient. | v0.2+ if multi-user workspace requires. |
| **Run tagging/labeling (v0.1)** | Tag storage, tag UI, tag-based filtering. Session grouping and date filters are sufficient. | v0.2. |
| **Run bookmarking/favorites (v0.1)** | Premature. v0.1 users have few enough runs. | v0.2+. |
| **Run annotations/comments** | Annotation storage, user identity, comment UI. Collaboration feature; v0.1 is single-user local. | Post-v0.1. |
| **Automated failure classification (ML-based)** | ML infrastructure, training data, classification model. Overkill. | v0.3+ if failure volume justifies. |
| **Run dependency graph (DAG of runs)** | Pipeline workflows; ARC v0.1 targets single-workflow execution. | v0.3+ if pipeline orchestration becomes direction. |
| **Full-text search across event content (v0.1)** | SQLite FTS5 requires indexing event content. ADR-003 defers this. | v0.2+. |
| **Run SLA/alerting** | Alert rules, notification channels, SLA definitions. Monitoring feature, not cockpit. | Post-v0.1. |
| **Multi-tenant run views** | Auth, storage isolation, tenant model redesign. v0.1 is single-user local. | Never. |
| **Cloud-hosted run dashboard** | Auth, multi-tenancy, security redesign. ARC is local-first. | Never. |
| **Run marketplace (share runs publicly)** | Workspace-specific data, prompts, potentially secrets. Security risk. | Never. |
| **Automated retry with ML-tuned parameters** | Violates high-assurance principle. Users should control retry. Paid calls are cost risk. | Never. |
| **Run replay with real provider calls** | Incurs real costs. Replay must be sandboxed or gated. | Never — deterministic replay behind runtime support. |
| **Cloud planning (Ultraplan equivalent)** | Cloud infrastructure, web sessions, Remote Control, dedicated review surface. Fundamentally different product direction. | Never — local-first is the positioning. |
| **Kiro-style spec timelines in v0.1** | Product philosophy, not a feature. ARC's equivalent is multi-phase planner with handoffs (v0.2). | v0.2+. |
| **Auto-open Tasks panel when entering Plan mode** | Mode and panel are orthogonal. Forcing Tasks open is focus theft. | Never. |
| **Persist checklists across sessions (v0.1)** | Storage schema decision. Checklists are lightweight scratchpad. | v0.2 if user demand exists. |
| **Voice input** | Out of scope for agent cockpit. | Never. |
| **Emoji reactions on messages** | Cosmetic. Not aligned with honest/observable brand. | Never. |
| **Chat themes per session** | Global theme is sufficient. | Never. |
| **Separate chat model** | Configuration complexity with marginal benefit. Users can switch via `/model`. | Reconsider if users want cheap chat + expensive runs. |
| **Message editing** | Transcript mutation complexity. Users can re-prompt. | v0.3 if requested. |

---

## 7. Risk Register

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Theia layout integration is harder than expected** | High | High | Use Theia's right sidebar infrastructure (not custom layout). Graph opens in main area. Defer drag-to-tab and mobile to v0.2. Reduce to 4 panels. |
| **React Flow bundle size impacts browser app startup** | Medium | Medium | React Flow is ~150KB (vs Monaco at 15.9 MiB). Acceptable. Use webpack split chunks (already configured). |
| **Keyring library fails on headless/SSH environments** | High | Medium | Explicit fallback to env-only mode. Visible degraded status. Never fall back to plaintext. Document platform behavior. |
| **SSE event broker cannot handle high event rate from SwarmGraph** | Medium | High | 100ms batched tick limits render frequency. Bounded queue with overflow discard (oldest first). Load test in v0.2. |
| **Git-based undo fails on non-git workspaces** | Medium | Medium | Detect git repo before apply. Warn user. Offer `git init`. Allow continue without undo with explicit confirmation. |
| **Session lock race conditions with concurrent CLI+IDE** | Medium | High | File-based lock with stale detection (PID + 30s timeout). Daemon owns all writes. CLI/IDE use RPC. Retry with backoff. |
| **Daemon port conflicts on multi-workspace machines** | Medium | Medium | Configurable port with fallback scanning (7777-7787). Port file for client discovery. One daemon per workspace. |
| **SwarmGraph vendored dependency breaks on Python version change** | Low | High | Vendored SwarmGraph tested against Python 3.11-3.13. CI runs conformance tests. `arc doctor` checks bundled runtime. |
| **Redaction misses a secret pattern in production** | Medium | High | E2E redaction test with injected fake secrets. Expand pattern list (Azure, Google, Bedrock, OpenRouter, generic `sk-`). Redact any value matching configured provider key env var name. |
| **npm shim + pip install fails on systems without pip** | Medium | Medium | Detect pip/pipx availability. Clear error message with install instructions. Python >=3.11 prerequisite checked. |
| **Policy "cannot weaken" enforcement has edge cases** | Low | High | Simple strictness comparison algorithm. Unit tests for all combinations. Project policy can only strengthen, never weaken, for `shell_exec` and `trust_changes`. |
| **`@file` mention token budget management is complex** | Medium | Medium | Hard limits: 16K per file, 32K per folder. Truncate with warning. User can remove mentions. Simple truncation, not smart selection. |
| **Intent routing misclassifies messages** | Medium | Medium | Keyword-based in v0.1 (simple, auditable). Plan mode forces "ask". Build mode asks for confirmation on "run". User can override with `/run`. LLM-based in v0.2. |
| **Graph rendering fails on large SwarmGraph topologies (>100 nodes)** | Medium | Medium | React Flow virtualization handles 1000+ nodes. Subgraph collapse in v0.2. Minimap for >20 nodes. Layout computation is O(n log n). |
| **Context compaction loses critical context** | Medium | Medium | Manual `/compact` only in v0.1 (user-initiated). Skills carried forward (first 5K tokens each, max 25K total). Original transcript preserved. Auto-compaction deferred to v0.2. |

### Product Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **v0.1 scope is too large for timeline** | High | High | Bounded scope in Section 3. Explicit out-of-scope list. 4 panels not 6. Defer Tasks panel to v0.2 (inline in chat). Use Theia diff editor. No Trace UI. |
| **Chat-first CLI confuses existing `arc` users** | Medium | Medium | `arc-studio advanced <cmd>` passthrough. CLI migration guide (`docs/cli-migration.md`). `arc` alias preserved. Onboarding guide walks through new flow. |
| **Paid-call confirmation annoys users** | Medium | Medium | Plan mode blocks all paid calls (no prompts). Auto mode can auto-approve via policy. Build mode asks. Local providers (Ollama) skip confirmation. |
| **Default UNTRUSTED creates onboarding friction** | Medium | Medium | Trust dialog is clear and actionable. "Trust Parent" reduces friction for multi-repo users. Onboarding guide explains trust model. |
| **No Trace UI disappoints observability-focused users** | Medium | Medium | Advanced fallback: `arc-studio advanced runs trace <id>`. Clear messaging: "Trace UI returns in v0.3 audit explorer." Runs panel provides summary-level observability. |
| **SwarmGraph-only default limits appeal** | Low | Medium | SwarmGraph is bundled and works out of the box. Other runtimes (LangGraph, CrewAI, OpenAI Agents) are available via `/runtime`. Adoption runners exist (P2). Router suggests alternatives in v0.2. |
| **Cost display with `cost ?` is unhelpful** | Medium | Low | Honest: providers don't give pre-call estimates. Session total provides post-run feedback. Per-model estimates in v0.2. Better than wrong estimates. |
| **Graph visualization doesn't differentiate from LangGraph Studio** | Medium | Medium | Live state overlay during execution is unique. Multi-runtime graph (not just LangGraph). CLI inline graph. Queen/worker topology. HITL nodes on graph. Cost overlay on nodes (v0.2). |

### Timeline Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Python backend and TypeScript frontend have different velocities** | Medium | High | Protocol contracts locked before implementation (Section 2). SSE interface is the primary integration point. E2E tests verify integration. |
| **Theia version skew blocks extension builds** | Medium | High | PR 3 (Theia version-skew audit) already completed. Lock Theia version across all packages. CI builds browser app on every push. |
| **CI is currently red (python/node/roadmap gate)** | High | High | R-1: Quote glob in arc-ag-ui test. R-2: Native deps in CI workflows. R-3: Stale event-loop fixture removed. Fix these 3 items before v0.1 branch. |
| **10 unmerged remote branches create merge conflicts** | Medium | Medium | R-4: 3 may have salvageable work, 7 intentionally parked. Park all 10 before v0.1 branch. Salvage in v0.2 if needed. |
| **`.env` history scrub blocks release** | Low | High | R-5: Plan documented in `docs/ENV_HISTORY_SCRUB_PLAN.md`. Execute only after release date approval. Does not block v0.1 development. |
| **Accessibility audit fails and blocks release** | Medium | Medium | Add axe-core to E2E now (not at end). Fix violations incrementally. Keyboard-only flow tested early. Screen reader labels added during component implementation. |
| **npm package name `arc-studio` is taken** | Low | High | Check npm registry immediately. If taken, use `@arc-studio/cli`. Update all references. |

---

## 8. Dependency Map

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           v0.1 Dependency Graph                               │
│                                                                              │
│  ┌─────────────────┐                                                         │
│  │  Protocol Types  │ ◄── Foundation: event schemas, RunRecord, session      │
│  │  (ADR-004)       │     metadata, daemon auth                              │
│  └───────┬─────────┘                                                         │
│          │                                                                    │
│          ▼                                                                    │
│  ┌─────────────────┐     ┌──────────────────┐                                │
│  │  Config/Policy   │────►│  Workspace Trust  │ ◄── Trust depends on config  │
│  │  (ADR-001)       │     │  (trust.py)       │     paths and policy         │
│  └───────┬─────────┘     └────────┬─────────┘                                │
│          │                        │                                          │
│          ▼                        ▼                                          │
│  ┌─────────────────┐     ┌──────────────────┐                                │
│  │  Provider Keys  │────►│  Session/Daemon   │ ◄── Sessions need provider   │
│  │  & Cost         │     │  (lifecycle)      │     keys, trust, config      │
│  └───────┬─────────┘     └────────┬─────────┘                                │
│          │                        │                                          │
│          ▼                        ▼                                          │
│  ┌──────────────────────────────────────┐                                    │
│  │         Chat Core (CLI + IDE)        │ ◄── Depends on ALL above           │
│  │  (sessions, modes, mentions, queue)  │     Chat is the integration point  │
│  └───────┬──────────┬───────────┬───────┘                                    │
│          │          │           │                                            │
│          ▼          ▼           ▼                                            │
│  ┌───────────┐ ┌────────┐ ┌──────────────┐                                  │
│  │  Graph    │ │  Runs  │ │  Review/Apply │ ◄── All depend on chat session  │
│  │  (React   │ │  (list │ │  (git-backed  │     and daemon                  │
│  │   Flow)   │ │  +sum) │ │   undo)       │                                  │
│  └───────────┘ └────────┘ └──────────────┘                                  │
│                                                                              │
│  ┌──────────────────────────────────────┐                                    │
│  │         IDE Layout (Theia sidebar)   │ ◄── Wraps Chat, Runs, Config      │
│  │         Status bar contribution      │     Graph in main area             │
│  └──────────────────────────────────────┘                                    │
│                                                                              │
│  ┌──────────────────────────────────────┐                                    │
│  │         Install/Distribution         │ ◄── Independent: npm shim, pipx,  │
│  │         (npm, pipx, completions)     │     completions, doctor            │
│  └──────────────────────────────────────┘                                    │
│                                                                              │
│  ┌──────────────────────────────────────┐                                    │
│  │         Testing/Observability        │ ◄── Cross-cutting: axe-core,       │
│  │         (E2E, a11y, docs)            │     manifest tests, redaction E2E  │
│  └──────────────────────────────────────┘                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                     v0.2 Dependency Graph (Reserved)                          │
│                                                                              │
│  Planner ──► Phase view ──► Handoff protocol ──► Router suggestions          │
│     │             │               │                    │                     │
│     │             │               │                    │                     │
│     ▼             ▼               ▼                    ▼                     │
│  Plan approval  PhaseCard    PHASE_HANDOFF      HotLoop runtime              │
│  audit linkage  acceptance   event emission     Device panel                 │
│                 criteria                          Frames panel               │
│                                                                              │
│  MCP config ──► MCP server lifecycle ──► MCP tool consumption                │
│     │                  │                       │                             │
│     ▼                  ▼                       ▼                             │
│  .arc/mcp.json    start/stop/reconnect    ToolCard with MCP metadata         │
│  sandbox config   health checks           MCP permissions → Plan/Build/Auto  │
│                                                                              │
│  Chat enhancements: @symbol, image input, history, /share, skills            │
│  Cost: budget ceilings, gateway quota, per-model estimates                   │
│  Review: inline diffs, checkpoint timeline                                   │
│  Config: schema migration, $schema, local config, hot-reload                 │
│  Trust: expiry, symlink detection, deny-read profiles                        │
│  IDE: Tasks panel, activity bar, drag rearrange, mobile                      │
│  Distribution: Homebrew tap, curl script, release channels, Electron spike   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Key dependency rules:
1. Protocol types MUST be locked before any feature implementation.
2. Config/Policy MUST be implemented before any enforcement-dependent features (trust, paid-call gating, MCP).
3. Session/Daemon MUST be stable before Chat, Graph, Runs, or Review can work correctly.
4. Chat is the integration point — it depends on everything below it.
5. Graph, Runs, and Review are parallel — they depend on Chat/Session but not on each other.
6. v0.2 features depend on stable v0.1 foundation. Do not start v0.2 work until v0.1 is shipped.
7. Planner → Handoff → Router → HotLoop is a strict dependency chain in v0.2.
8. MCP consumption depends on stable chat agent architecture (tool routing, card rendering).
```

---

## 9. Suggested Implementation Order

### Phase 1: Foundation (Weeks 1-3)
**Goal:** Lock contracts, build infrastructure that everything else depends on.

1. Lock protocol contracts (Section 2): event schemas, session metadata, daemon auth token lifecycle, SSE streaming protocol
2. Add `PHASE_HANDOFF` event type, rename `HANDOFF` → `AGENT_DELEGATION`
3. Define session metadata schema (`metadata.yaml` with `schema_version`)
4. Define daemon auth token lifecycle (generation, rotation, storage, invalidation)
5. Lock SSE as streaming protocol for CLI and IDE
6. Fix user config path (`~/.config/arc-studio/` with dual-read migration)
7. Implement `PolicyConfig` Pydantic model and `load_policy()` loader
8. Implement "cannot weaken" enforcement algorithm
9. Wire policy into `JobSupervisor.start_run()` and HITL flow
10. Add machine ID + user ID to trust binding
11. Add parent folder trust and protected paths
12. Remove `allow_if_no_db` from `ensure_trusted()`
13. Implement keyring for provider keys with explicit fallback
14. Add `arc providers test` command
15. Expand redaction patterns (Azure, Google, Bedrock, OpenRouter, generic `sk-`)

**Deliverable:** Config, policy, trust, and provider infrastructure working. Protocol contracts locked.

### Phase 2: Session & Daemon Core (Weeks 3-5)
**Goal:** Session lifecycle and daemon state machine working end-to-end.

16. Implement session metadata schema with workspace binding
17. Implement file-based session lock with stale detection
18. Implement daemon auth token lifecycle
19. Implement daemon state machine (8 states + orphaned-run)
20. Implement daemon auto-start from `stopped` state
21. Implement daemon port config with fallback scanning
22. Implement daemon crash recovery (orphan run detection)
23. Implement cross-workspace resume warning
24. Implement session retention (30-day prune, max 50)
25. Implement session cost accumulator
26. Implement `/sessions` command
27. Implement CLI command aliases and fuzzy autocomplete
28. Implement command queueing during active runs
29. Implement command history (up-arrow recall)
30. Implement shell completions

**Deliverable:** Sessions persist, daemon starts/stops/recoveres correctly, CLI commands work.

### Phase 3: Chat Core (Weeks 5-8)
**Goal:** Chat-first CLI and IDE chat panel working with all v0.1 features.

31. Implement chat REPL with streaming via SSE
32. Implement `@file` and `@folder` mention syntax with autocomplete
33. Implement message queueing UI (status line indicator)
34. Implement intent routing (keyword-based: ask vs run)
35. Implement ModeToggle component (Plan/Build/Auto)
36. Implement tool call cards, HITL cards, paid-call cards in transcript
37. Implement paid-call confirmation (CLI blocking prompt)
38. Implement `/compact` with skill carry-forward
39. Implement all 20+ slash commands
40. Implement `arc-studio advanced <cmd>` passthrough
41. Implement IDE chat panel in Theia right sidebar
42. Implement status bar contribution (trust, runtime, mode, daemon, cost)
43. Implement keyboard shortcuts (`Ctrl/Cmd+;`, `Ctrl/Cmd+Enter`, etc.)
44. Implement first-launch default (Chat tab open, others closed)

**Deliverable:** Chat works in CLI and IDE with all v0.1 features.

### Phase 4: Graph & Runs (Weeks 8-10)
**Goal:** Graph visualization and run management working.

45. Install React Flow (@xyflow/react)
46. Implement graph rendering with dagre layout
47. Implement pan, zoom, fit-to-view, minimap
48. Implement node types with spec colors
49. Implement live state overlay via SSE (100ms batched tick)
50. Implement node inspector panel
51. Implement graph export (PNG/SVG)
52. Implement ARIA accessibility for graph
53. Implement CLI inline graph (§7.6)
54. Implement Runs panel with list table and filters
55. Implement inline row expand for run detail
56. Implement FailureCard with cost display and configurable event count
57. Implement run export (JSON) and delete (with confirmation)
58. Implement pagination (50 per page, load-more)
59. Implement "Open advanced trace" → `arc-studio advanced runs trace <id>`

**Deliverable:** Graph animates during runs, Runs panel shows run history with filtering.

### Phase 5: Review/Apply & Config UI (Weeks 10-12)
**Goal:** Diff review and configuration surfaces working.

60. Implement git-backed apply (creates commit on "Apply Approved")
61. Implement `/undo` and `/redo` (git revert)
62. Implement per-hunk approve/reject/edit-first
63. Implement "Approve All" and "Reject All" bulk actions
64. Implement conflict detection (dry-run patch)
65. Implement concurrent edit warning (mtime check)
66. Implement Edit First workflow (opens Theia editor)
67. Implement review session persistence
68. Implement partial apply failure handling
69. Use Theia's built-in diff editor (not custom Monaco)
70. Implement IDE Config tab (sidebar) with sub-tabs
71. Implement CLI `/config` interactive TUI form
72. Implement `arc-studio doctor install`

**Deliverable:** Users can review, approve, and apply changes with git-backed undo. Config is editable in IDE and CLI.

### Phase 6: Install, Testing & Docs (Weeks 12-14)
**Goal:** Distribution, quality, and documentation ready for release.

73. Create `arc-studio` npm package (thin shim + pip install)
74. Verify `pipx install agent-runtime-cockpit` works
75. Implement `/update --check` and `arc-studio update`
76. Implement version mismatch detection on startup
77. Add axe-core to Playwright E2E tests
78. Add manifest validation tests
79. Add redaction E2E contract test
80. Add daemon state machine tests
81. Add automated screenshot generation via Playwright
82. Write `docs/onboarding.md` (5-step guide)
83. Write `docs/cli-migration.md` (old→new mapping)
84. Add docs link checker to CI
85. Fix CI issues (R-1: quote glob, R-2: native deps, R-3: stale fixture)
86. Run full test suite: 550 Python + 239 TypeScript + 12 E2E
87. Run release checklist dry-run
88. Generate docs screenshots
89. Verify install/uninstall on macOS and Linux
90. Final banned-claims check

**Deliverable:** v0.1 installable, tested, documented, and ready for release.

### Critical Path
```
Phase 1 (Foundation) → Phase 2 (Session/Daemon) → Phase 3 (Chat) → Phase 4 (Graph/Runs) → Phase 5 (Review/Config) → Phase 6 (Install/Test/Docs)
```

Phases 4 and 5 can overlap (Graph/Runs and Review/Config are independent). Phase 6 can start in parallel with Phase 5 (testing and docs don't block on Review/Apply completion).

---

## 10. Final Lock / No-Lock Recommendation

### Lock Now (v0.1 spec is stable enough to implement)

| Area | Recommendation | Confidence |
|------|---------------|------------|
| **Chat-first CLI default** | LOCK. Core product differentiator. Every competitor does this. Spec is thorough. | High |
| **SwarmGraph default and bundled** | LOCK. Non-negotiable. Only bundled runtime with zero external dependencies. | High |
| **Plan/Build/Auto modes** | LOCK. Matches market pattern. Well-specified. ModeToggle is straightforward. | High |
| **Session lifecycle (ULID, JSONL, auto-resume)** | LOCK. Solid design. JSONL journal with crash recovery is robust. | High |
| **Daemon state machine (8 states)** | LOCK. Thorough spec. No competitor has this level of daemon lifecycle management. | High |
| **Workspace trust model** | LOCK. Default UNTRUSTED, external storage, machine/user ID binding, parent trust, protected paths. Security-critical and well-designed. | High |
| **Git-backed undo** | LOCK. Every competitor with undo uses git. Custom snapshot system is rejected. | High |
| **SSE streaming protocol** | LOCK. Already recommended in redesign plan. Existing event broker uses SSE. Simple, HTTP-based. | High |
| **Redaction contract** | LOCK. Universal redaction across all surfaces. Pattern list expanded. E2E test added. Security-critical. | High |
| **Config 5-level precedence** | LOCK. CLI > env > workspace > user > defaults. Covers all practical cases. ADR-001 validated. | High |
| **Policy model (ask/auto/deny)** | LOCK. 3-level precedence, "cannot weaken" enforcement, file-only in v0.1. Security-critical. | High |
| **No default Trace UI in v0.1** | LOCK. Product positioning is chat-first. Advanced fallback exists. Trace UI returns in v0.3. | High |
| **HotLoop reserved for v0.2** | LOCK. Requires vision model, target lifecycle, novel loop architecture. Not v0.1 material. Event payload schemas reserved. | High |
| **React Flow for graph rendering** | LOCK. Dominant library, native React, built-in controls. Cytoscape.js and custom SVG both rejected. | High |
| **4 panels for v0.1 (Chat, Graph, Runs, Config)** | LOCK. 6 panels is too much surface. Tasks merges into chat as inline cards. Review uses Theia diff. | High |
| **Theia right sidebar for ARC panels** | LOCK. Fighting Theia's layout is expensive. Every competitor uses right sidebar for agent panel. | High |
| **npm thin shim + pip install** | LOCK. Bundling Python in npm is rejected. pipx is canonical Python path. | High |
| **`/update --check` prints commands, never self-modifies** | LOCK. Self-modifying installs are risky for alpha. Transparent approach. | High |
| **MCP reserved for v0.2** | LOCK. Depends on stable chat foundation. Schema reserved in v0.1 protocol. | High |
| **ACP reserved for v0.3** | LOCK. Distribution play, not core product. Types reserved. | High |

### Need More Iteration (not ready to lock)

| Area | What Needs Iteration | Recommendation |
|------|---------------------|----------------|
| **Cost estimation strategy** | v0.1 uses `cost ?` (no estimates). v0.2 needs a decision: hardcoded per-model table vs provider pricing API vs local tokenizer. Each has tradeoffs. | Lock v0.1 as `cost ?`. Defer v0.2 decision until user feedback on `cost ?` UX. |
| **Intent routing classifier** | v0.1 uses keyword matching. v0.2 proposes LLM-based classification. The boundary between "ask" and "run" is fuzzy and needs real-world data. | Lock v0.1 as keyword-based. Collect misclassification data. Decide v0.2 approach after v0.1 usage. |
| **Router suggestion threshold** | v0.2 router needs a score threshold for when to show suggestions. Too low = noise. Too high = missed opportunities. Needs tuning data. | Lock v0.2 as `suggest` mode with configurable threshold. Default threshold TBD after v0.1 usage data. |
| **Context compaction algorithm** | v0.1 uses manual `/compact`. Auto-compaction (v0.2) needs trigger threshold, summarization model, skill preservation strategy. | Lock v0.1 as manual. Defer auto-compaction design until v0.1 `/compact` usage patterns are observed. |
| **Handoff `state_schema` format** | v0.2 handoff needs a schema format for state validation. String identifier vs inline JSON Schema has different complexity tradeoffs. | Lock v0.1 reservation. Decide format during v0.2 handoff implementation based on actual runtime state shapes. |
| **MCP permission granularity** | v0.2 MCP needs per-server or per-tool permission rules. OpenCode's pattern matching is powerful but complex. Simple per-server allow/deny may be sufficient initially. | Lock v0.2 as per-server trust + Plan/Build/Auto mapping. Defer per-tool granularity until MCP usage data exists. |
| **Session retention defaults** | 30-day retention and 50-session max are reasonable defaults but may need adjustment based on actual usage patterns. | Lock v0.1 defaults as configurable. Adjust after v0.1 usage data. |
| **Graph density modes** | Compact/comfortable/spacious density affects node sizing and spacing. Needs user feedback on preferred defaults. | Lock v0.1 as single density (comfortable). Add density modes in v0.2 based on feedback. |
| **Keyboard shortcut conflicts** | Some shortcuts conflict with Theia/VS Code defaults. The "only when ARC focused" rule needs context-key implementation verification. | Lock v0.1 shortcuts as specified. Verify context-key behavior during implementation. Adjust if conflicts persist. |
| **npm package name availability** | `arc-studio` on npm is [needs verification]. If taken, need fallback name. | Check npm registry immediately. Lock name or fallback before Phase 6. |

### Explicitly Do Not Lock (defer decision)

| Area | Why Not Lock | When to Decide |
|------|-------------|----------------|
| **Electron packaging approach** | ADR-008 P1 packaging spike not run. PyInstaller vs embedded Python vs uv-based bootstrap needs measurement. | v0.2 spike, decide after measurement. |
| **Planner architecture** | Multi-phase plan generation is a significant feature. Needs dedicated design cycle. v0.2 scope. | v0.2 design phase, after v0.1 ships. |
| **HotLoop screenshot capture mechanism** | Depends on target platform (emulator vs real device vs web). Needs platform-specific design. | v0.2 HotLoop design phase. |
| **Loop tick semantics (HotLoop)** | Observation/action loop is novel. Stop conditions, convergence detection, max iterations need real-world testing. | v0.2 HotLoop implementation. |
| **Rollback mechanism (HotLoop)** | Depends on target platform's hot-reload capabilities. Git revert vs hot reload vs snapshot restore. | v0.2 HotLoop implementation. |
| **Managed/org config** | Enterprise feature. Requires platform-specific code (MDM, registry). Not needed for alpha. | v0.2+ when enterprise adoption is a goal. |
| **Release channel strategy** | latest/stable channels require release infrastructure and enough release history to matter. | v0.2 when there's enough release history. |
| **Binary integrity verification** | GPG signing or Sigstore attestations. Requires signing infrastructure and key management. | v0.3 when enterprise adoption is a goal. |
| **Cross-platform E2E matrix** | CI cost/complexity. Ubuntu CI is sufficient for alpha. | v0.3 when v0.1 is stable on primary platform. |
| **Visual regression testing** | UI colors/layout not yet implemented. Baseline screenshots don't exist. | v0.2 after UI stabilizes post-redesign. |

### Summary

**Lock now:** 20 items covering chat, sessions, daemon, trust, config, policy, graph rendering, IDE layout, install, and protocol reservations. These are stable, well-researched, and have clear implementation paths.

**Need iteration:** 10 items where v0.1 decisions are locked but v0.2 decisions need real-world data. Lock v0.1 behavior, defer v0.2 decisions.

**Do not lock:** 10 items that are explicitly v0.2+ or v0.3+ concerns. Premature locking would constrain design options without benefit.

**Net assessment:** The v0.1 spec is lockable. The critical path (Protocol → Config/Policy/Trust → Session/Daemon → Chat → Graph/Runs → Review/Config → Install/Test/Docs) has well-defined contracts and clear implementation order. v0.2 reservations are sufficient to prevent breaking changes. The main risk is scope creep — the bounded v0.1 scope in Section 3 must be enforced.
