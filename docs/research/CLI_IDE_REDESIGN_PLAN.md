# ARC Studio CLI + IDE Redesign Plan

**Version:** v0.1.0-draft
**Date:** 2026-05-15
**Status:** Draft for review; feature-roadmap review findings integrated
**Owner:** TBD

---

## 1. Product Research Summary

### 1.1 CLI Comparison

| Feature | Claude Code | OpenCode | Codex CLI | Aider | ARC Studio (current) |
|---------|------------|----------|-----------|-------|---------------------|
| **Install** | Native binary (curl/brew) | npm/brew/binary | npm/brew/binary | pip | pip (`uv sync`) |
| **Launch command** | `claude` | `opencode` | `codex` | `aider` | `arc` (60+ subcommands) |
| **Default behavior** | Chat REPL | Chat TUI | Chat TUI | Chat REPL | `--help` (no default chat) |
| **Config command** | `/config` (interactive TUI) | `/connect` + JSON config | TOML config | YAML config | `arc config show` (read-only) |
| **Model switching** | `/model`, `--model` | `-m`, config | `/model`, `-m` | `/model`, `--model` | No simple switch; nested in `arc run --runtime` |
| **Slash commands** | 40+ | 6+ custom | 30+ | 35+ | 0 |
| **Session resume** | `-c`, `-r`, `--resume` | `-c`, `-s` | `resume`, `fork` | `--restore-chat-history` | No session concept |
| **Non-interactive** | `claude -p "query"` | `opencode run "query"` | `codex exec "query"` | `aider -m "query"` | `arc run <id> --prompt "..."` |
| **Permission modes** | 5 modes + Shift+Tab | JSON permission | Approval + sandbox | `--yes-always` | Workspace trust only |
| **Max nesting depth** | 1 (flat slash commands) | 1 (flat slash commands) | 1 (flat slash commands) | 1 (flat slash commands) | **3** (`arc providers accounts add`) |
| **Total commands** | ~50 (flat) | ~20 (flat) | ~40 (flat) | ~40 (flat) | **60+** (nested) |

### 1.2 IDE Comparison

| Feature | Cursor | Windsurf | Kiro | OpenCode | VS Code Copilot | ARC Studio (current) |
|---------|--------|----------|------|----------|-----------------|---------------------|
| **Layout** | 3-col: explorer/editor/agent | 3-col: explorer/editor/Cascade | 3-col: explorer/editor/chat | TUI + desktop | 3-col: explorer/editor/chat | 2-col: sidebar/main (5 separate widgets) |
| **Chat panel** | Right sidebar, persistent | Right sidebar (Cascade) | Right sidebar | TUI chat | Right sidebar | **No chat panel** |
| **Agent mode** | Agent/Composer toggle | Code/Chat toggle | Autopilot toggle | Plan/Build (Tab) | Chat/Agent/Edit | Execute button only |
| **Model switcher** | Dropdown above input | Dropdown below input | Dropdown above input | Status bar | Dropdown | None |
| **Plan mode** | Yes (numbered steps) | Yes (todo inline) | Yes (specs) | Yes (Tab toggle) | Yes | No |
| **Diff review** | Inline + Accept/Reject | Inline + Accept/Revert | Live diffs + Approve/Step/Apply | `/undo`/`/redo` | Inline + Accept/Discard | No diff review |
| **Trace/timeline** | Activity feed | Checkpoint timeline | Spec timeline | Conversation history | Chat history | 3 separate widgets (timeline, event stream, graph) |
| **Config UI** | Settings + .cursorrules | Settings + Memories | Steering files | `/connect` + JSON | Settings UI | **No config UI** |
| **Progressive disclosure** | Skills behind `/` | Workflows in tabs | Specs opt-in | Plan behind Tab | Agent mode separate | All widgets always visible |
| **Key buttons** | Accept/Reject/Publish | Accept/Continue/Deploy | Approve/Step/Apply | Tab (mode toggle) | Accept/Discard | Execute/Load/Scan/Refresh |

### 1.3 Key UX Patterns Worth Copying

**From CLIs:**
1. **Chat-first default** — Every modern agent CLI launches into a chat REPL by default. No arguments needed.
2. **Slash commands** — Flat, discoverable command namespace. `/config`, `/model`, `/status`, `/run`, `/help`.
3. **Config file + interactive config** — JSON/TOML/YAML config with an interactive `/config` command.
4. **Model/runtime switching via slash command** — `/model sonnet` mid-session, `--model` at launch.
5. **Session continuity** — Resume, continue, fork sessions.
6. **Permission modes** — Plan (read-only), Build (edit), Auto (auto-approve). Cycle with keyboard shortcut.
7. **Non-interactive scripting** — `exec`/`run`/`-p` flag for CI/automation.

**From IDEs:**
1. **Right sidebar chat panel** — Universal pattern. Persistent, always accessible.
2. **Mode toggle** — Plan/Build, Code/Chat, Agent/Composer. One click or keyboard shortcut.
3. **Model dropdown above input** — Visible, one-click switch.
4. **Accept/Reject diff flow** — Inline diffs with per-change and bulk actions.
5. **Activity feed / timeline** — Real-time agent status ("Thought 7s", "Editing files").
6. **Progressive disclosure** — Advanced features behind `/` commands, settings panels, or mode switches.
7. **Status bar** — Model, token usage, git branch, permission mode always visible.

### 1.4 Patterns to Avoid

1. **Deep command nesting** — ARC's `arc providers accounts add` (depth 3) is an anti-pattern. All competitors use flat namespaces.
2. **No default behavior** — Running `arc` with no args shows `--help`. Every competitor launches chat.
3. **Separate widgets with no navigation** — ARC's 5 widgets open in main area with no unified navigation. Competitors use a single agent panel with tabs/sections.
4. **No chat interface** — ARC has workflow execution but no conversational interface.
5. **Config only via CLI** — No IDE config UI. All competitors have settings panels.
6. **No session concept** — No resume, continue, or session history. Every competitor supports this.
7. **No context mentions** — Chat-first tools need `@file` and `@folder` references as table stakes.
8. **No reversible apply contract** — Use git commits plus `/undo` and `/redo`; do not invent snapshots.

---

## 2. Proposed CLI Redesign

### 2.1 New Global Install Story

**Current:** `cd python && uv sync --all-extras --dev` (local venv, `arc` command only in venv)

**Target:** Global install like Claude Code / OpenCode / Codex CLI

```bash
# Option A: npm global (preferred, matches OpenCode/Codex pattern)
npm install -g arc-studio

# Option B: pipx (Python best practice for CLI tools)
pipx install agent-runtime-cockpit

# Option C: Homebrew (future)
brew install arc-studio

# Option D: curl install script (future)
curl -fsSL https://arc-studio.ai/install | bash
```

**Implementation:**
- Create `arc-studio` npm package that wraps the Python CLI
- The npm package bundles or downloads the Python wheel
- Entry point: `arc-studio` binary (Node.js shim that invokes Python CLI)
- Keep `arc` as an alias for backward compatibility

### 2.2 New Command Shape

**Current:** 60+ commands, 3-level nesting, no default behavior

**Target:** Chat-first default, flat slash commands, hidden advanced commands

Innovation-critical review adjustment: v0.1 is not just chat parity. It must reserve and minimally surface cockpit primitives: `RunContract`, `RunReceipt`, `FailureAutopsy`, `EvidenceRef`, stable cross-surface IDs, runtime capability snapshots, and `TrustDiff`.

```bash
# Default launch — interactive chat
arc-studio
# or
arc

# With initial prompt
arc-studio "Explain this agent workflow"

# Non-interactive (scripting/CI)
arc-studio run "Run the swarmgraph workflow"

# Continue last session
arc-studio -c

# Resume specific session
arc-studio -r <session-id>

# Open config interactively
arc-studio config

# Doctor / health check
arc-studio doctor

# Version
arc-studio --version
```

**Backward compatibility:**
- All existing `arc <subcommand>` commands remain accessible
- They are hidden from default `--help` output
- Available via `arc-studio advanced <subcommand>` or `ARC_EXPERT=1 arc <subcommand>`
- Documented in `docs/advanced-cli.md`

### 2.3 Default Interactive Chat Behavior

When `arc-studio` launches with no arguments:

1. **Startup screen:**
   ```
   ARC Studio v0.1.0-alpha
   Workspace: ~/my-project
   Runtime:   swarmgraph (detected)
   Model:     claude-sonnet-4-5 (default)
   Mode:      build

   Type a message or /help for commands.
   >
   ```

2. **Chat loop:**
   - User types message → agent processes → shows response
   - Agent can: detect workflows, run workflows, show traces, inspect codebase
   - Streaming output with syntax highlighting
   - File/folder context through `@file` and `@folder` mentions
   - File diffs shown in Review panel / Theia diff editor
   - Permission prompts for write operations

3. **Session state:**
   - Conversation history persisted in platform session dir
   - Each session has: ID, workspace, runtime, model, messages, runs
   - Auto-resume on crash

### 2.4 Slash Command List

| Command | Purpose | Implementation |
|---------|---------|---------------|
| `/config` | Open interactive config editor | New: TUI config panel |
| `/runtime` | Switch runtime (swarmgraph/langgraph/crewai/etc.) | Wraps `arc run --runtime` |
| `/model` | Switch model | New: config update + reload |
| `/status` | Show workspace/runtime/session status | Wraps `arc status` + session info |
| `/run` | Run detected workflow | Wraps `arc run` |
| `/doctor` | Run diagnostics | Wraps `arc doctor all` |
| `/workflows` | List detected workflows | Wraps `arc workflows` |
| `/runs` | List run summaries | New: SQLite-backed run list, no default Trace UI |
| `/plan` | Switch to plan mode (read-only) | New: permission mode toggle |
| `/build` | Switch to build mode (edit) | New: permission mode toggle |
| `/auto` | Switch to policy-driven mode | New: permission mode toggle |
| `/clear` | Clear chat history | New: session reset |
| `/compact` | Summarize conversation to free tokens | New: LLM summarization |
| `/sessions` | List recent sessions | New: session dir enumeration |
| `/undo` | Undo last agent changes | New: git revert integration |
| `/redo` | Re-apply last undone agent changes | New: git revert-of-revert integration |
| `/diff` | Show git diff of changes | New: git diff wrapper |
| `/help` | Show command help | New: flat command list |
| `/exit` | Exit session | Existing: quit |
| `/advanced` | Show all advanced commands | New: expert mode toggle |

### 2.5 Config Model

**Interactive config (`/config` or `arc-studio config`):**

```
ARC Studio Configuration
─────────────────────────

  Runtime
    [●] swarmgraph    Detected ✓
    [ ] langgraph     Not installed
    [ ] crewai        Not installed
    [ ] openai-agents Partial

  Model
    [●] claude-sonnet-4-5   (default)
    [ ] gpt-4o
    [ ] claude-opus-4

  Provider Keys
    ANTHROPIC_API_KEY  ✓ Set
    OPENAI_API_KEY     ✗ Not set
    DEEPSEEK_API_KEY   ✗ Not set

  Mode
    [●] Build  (can edit files)
    [ ] Plan   (read-only)

  Workspace Trust
    ~/my-project  Trusted

  [Save]  [Cancel]  [Reset to Defaults]
```

**Config path and fields:**

Use `~/.config/arc-studio/config.yaml` for user config and `.arc/config.yaml` for workspace config. Legacy `~/.arc/` paths may be dual-read with deprecation warning; do not silently migrate.

**New config fields needed:**
```yaml
cli:
  default_model: claude-sonnet-4-5
  default_runtime: swarmgraph
  default_mode: build  # plan | build | auto
  session_history: true
  max_session_age_days: 30

providers:
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    default_model: claude-sonnet-4-5
  openai:
    api_key_env: OPENAI_API_KEY
    default_model: gpt-4o
```

### 2.6 Migration Plan

| Phase | Action |
|-------|--------|
| Phase 1 | Create `arc-studio` npm wrapper package and pipx/PyPI install path |
| Phase 2 | Add interactive chat REPL as default entry point |
| Phase 3 | Implement slash command router, aliases, fuzzy autocomplete |
| Phase 4 | Add `@file`/`@folder` mentions, queued input, stable message/session IDs |
| Phase 5 | Add `RunContract` pre-run card and paid-call/cost policy projection |
| Phase 6 | Add `RunReceipt` schema/artifact and `arc-studio receipt show/export/verify` |
| Phase 7 | Add `FailureAutopsy` and `EvidenceRef` rendering for file/tool evidence |
| Phase 8 | Add `/config` interactive TUI, policy loader wiring, TrustDiff reservation |
| Phase 9 | Add `/runtime`, `/model`, capability snapshots, `/providers test`, keyring fallback |
| Phase 10 | Hide advanced commands from default help; keep trace commands advanced-only |
| Phase 11 | Add session persistence, `/sessions`, resume, compact, multi-client status chip |
| Phase 12 | Add git-backed Review/Apply plus `/undo`/`/redo` |
| Phase 13 | Publish to npm (`arc-studio`) and PyPI (`agent-runtime-cockpit`) |

---

## 3. Proposed IDE Redesign

### 3.1 Simplified Navigation Model

**Current:** 5 separate widgets, no unified navigation, commands to open each

**Target:** Theia-native right sidebar with ARC tabs plus Graph in the main editor area. Do not build a custom three-column shell.

```
┌─────────────────────────────────────────┐
│  ARC Studio                      [⚙] [?] │
├─────────────────────────────────────────┤
│  [Chat] [Runs] [Config]                 │  ← Right sidebar tabs
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────────┐  │
│  │                                   │  │
│  │  Active tab content here          │  │
│  │                                   │  │
│  └───────────────────────────────────┘  │
│                                         │
├─────────────────────────────────────────┤
│  Runtime: swarmgraph  Model: sonnet     │  ← Status bar
│  Mode: build                            │
└─────────────────────────────────────────┘
```

### 3.2 Main Panels

#### Panel 1: Chat (default)

```
┌─────────────────────────────────────────┐
│  Chat                    [Plan ● Build]  │
├─────────────────────────────────────────┤
│                                         │
│  🤖 Agent                               │
│  I detected 2 SwarmGraph workflows      │
│  in this workspace:                     │
│                                         │
│  • queen-consensus (3 agents)           │
│  • data-pipeline (2 agents)             │
│                                         │
│  Which would you like to run?           │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ Run queen-consensus               │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ Run data-pipeline                 │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ─────────────────────────────────────  │
│  User                                   │
│  Run the queen-consensus workflow       │
│                                         │
│  🤖 Agent                               │
│  Starting queen-consensus...            │
│  ⏳ Thought 3s                          │
│  ⏳ Executing tool: search_codebase 2s  │
│  ✅ Step 1/4 complete                  │
│                                         │
├─────────────────────────────────────────┤
│  Runtime: swarmgraph ▼  Model: sonnet ▼ │
│  ┌───────────────────────────────────┐  │
│  │ Type a message...            [▶]  │  │
│  └───────────────────────────────────┘  │
│  /runtime  /model  /config  /help       │
└─────────────────────────────────────────┘
```

**Key elements:**
- Chat messages with agent/user distinction
- Inline action buttons (Run workflow, Approve, Reject)
- Real-time status indicators (⏳ timers, ✅ checkmarks)
- Plan/Build mode toggle (Tab key or button)
- Runtime and model dropdowns above input
- Slash command hints below input
- Send button (▶) turns blue when text entered

Feature-roadmap review lock: v0.1 IDE default surfaces are Chat, Graph, Runs, Review/Apply, Config, and Theia status bar. Tasks Phase/Loop panel is reserved for v0.2; v0.1 Task steps render inline in Chat. Workflows remain discoverable through `/workflows` and command palette, not a default tab. Trace/timeline/event JSON UI is not in default v0.1.

#### Panel 2: Runs

```
┌─────────────────────────────────────────┐
│  Runs                      [Refresh]    │
├──────────────┬──────────────────────────┤
│              │                          │
│  Runs List   │  Selected Run Detail     │
│              │                          │
│  ● abc123    │  Run: abc123             │
│    completed │  Status: completed       │
│    2m ago    │  Runtime: swarmgraph     │
│    47 events │  Started: 14:32:01       │
│              │  Duration: 1m 23s        │
│  ○ def456    │                          │
│    failed    │  ┌────────────────────┐  │
│    5m ago    │  │ Failure summary    │  │
│    12 events │  │ node: reviewer     │  │
│              │  │ reason: timeout    │  │
│  ○ ghi789    │  │ last 5 events      │  │
│    running   │  │ redacted           │  │
│    now       │  │ [Advanced trace]   │  │
│    23 events │  └────────────────────┘  │
│              │                          │
│              │  [Replay] [Export] [▶]   │
│              │                          │
└──────────────┴──────────────────────────┘
```

**Key elements:**
- Split view: list on left, detail on right
- Color-coded status (green/red/orange/blue)
- Inline RunSummary and FailureCard expansion
- Export, Delete, Advanced trace actions
- Event count and duration
- Filter by status/runtime/date

#### Panel 3: Workflows

```
┌─────────────────────────────────────────┐
│  Workflows                  [Scan]      │
├─────────────────────────────────────────┤
│                                         │
│  Detected Workflows                     │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ 🐝 queen-consensus                │  │
│  │    Runtime: SwarmGraph            │  │
│  │    Agents: 3 (queen + 2 workers)  │  │
│  │    File: swarmMain/main.py        │  │
│  │    [Run] [Inspect] [Graph]        │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ 📊 data-pipeline                  │  │
│  │    Runtime: LangGraph             │  │
│  │    Nodes: 5                       │  │
│  │    File: pipeline/graph.py        │  │
│  │    [Run] [Inspect] [Graph]        │  │
│  └───────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

**Key elements:**
- Card per workflow with runtime badge
- Agent/node count
- File location
- Run, Inspect, Graph actions
- Scan button to re-detect

#### Panel 4: Config

```
┌─────────────────────────────────────────┐
│  Config                     [Reset]     │
├─────────────────────────────────────────┤
│                                         │
│  Runtime                                │
│  ┌───────────────────────────────────┐  │
│  │ ● SwarmGraph (detected)          │  │
│  │ ○ LangGraph                      │  │
│  │ ○ CrewAI                         │  │
│  │ ○ OpenAI Agents                  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Model                                  │
│  ┌───────────────────────────────────┐  │
│  │ claude-sonnet-4-5          [▼]   │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Provider Keys                          │
│  ANTHROPIC_API_KEY  ✓ Set              │
│  OPENAI_API_KEY     ✗ Not set          │
│  [Add Key]                              │
│                                         │
│  Mode                                   │
│  [●] Build  [ ] Plan  [ ] Auto         │
│                                         │
│  Workspace Trust                        │
│  ~/my-project  ✓ Trusted               │
│                                         │
│  [Save Changes]                         │
│                                         │
└─────────────────────────────────────────┘
```

**Key elements:**
- Runtime radio selection
- Model dropdown
- Provider key status with add/edit
- Mode toggle (Plan/Build/Auto)
- Workspace trust status
- Save button persists to `.arc/config.yaml`

### 3.3 Button/Action Model

| Button | Location | Action |
|--------|----------|--------|
| **Run** | Workflows card, Chat action | Execute workflow |
| **Stop** | Chat (during execution) | Cancel running workflow |
| **Approve** | Chat (HITL prompt) | Approve agent action |
| **Reject** | Chat (HITL prompt) | Reject agent action |
| **Apply** | Diff view | Apply proposed changes |
| **Review Diff** | Chat action | Open diff viewer |
| **Configure** | Status bar, Config tab | Open config panel |
| **Switch Runtime** | Config tab, status bar dropdown | Change active runtime |
| **Open Trace** | Runs list | View trace detail |
| **Retry** | Error banner, failed run | Re-run failed workflow |
| **Export** | Runs detail | Export trace JSON |
| **Replay** | Runs detail | Replay trace events |
| **Scan** | Workflows tab | Re-detect workflows |
| **Refresh** | Runs tab | Reload runs list |
| **Plan/Build** | Chat tab header | Toggle permission mode |

### 3.4 Runtime Switching UX

**In Config tab:**
- Radio button selection per runtime
- Shows detection status (✓ detected, ✗ not installed, ⚠ partial)
- Shows required env vars per runtime
- Save persists to `.arc/config.yaml`

**In Chat tab:**
- Dropdown above input: `Runtime: swarmgraph ▼`
- Click to switch mid-session
- Shows detection badge: `swarmgraph ✓`

**In Status bar:**
- Always visible: `Runtime: swarmgraph`
- Click to open config tab

### 3.5 Trace/Run UX

**Unified approach:**
- Runs tab replaces 3 separate widgets (timeline, event stream, graph)
- Timeline view is the default detail view
- Event stream available as sub-tab within run detail
- Graph view available via "Graph" button on workflow card

**Progressive disclosure:**
- Simple list → click → detail → click event → full JSON
- Most users only need list + timeline
- Advanced users can drill into event JSON

### 3.6 HITL/Approval UX

**In Chat panel:**
```
🤖 Agent
I want to modify swarmMain/main.py:
- Add consensus voting to queen agent
- Update worker response format

┌───────────────────────────────────┐
│  - import json                    │
│  + import json, hashlib           │
│                                   │
│    def vote(self, proposals):     │
│  +     scores = self.rank(...)    │
│  +     return max(scores)         │
└───────────────────────────────────┘

[Approve] [Reject] [Edit First]
```

**Key elements:**
- Inline diff preview
- Three action buttons
- Edit First opens editor
- Approve applies changes
- Reject discards and tells agent

---

## 4. Architecture Changes Needed

### 4.1 Package/Global Binary Changes

**New npm package: `arc-studio`**
```
packages/arc-studio-cli/
├── package.json          # npm package, bin: arc-studio
├── bin/
│   └── arc-studio        # Node.js shim
├── src/
│   ├── cli.ts            # Chat REPL entry point
│   ├── slash-commands.ts # Slash command router
│   ├── session.ts        # Session management
│   ├── config-tui.ts     # Interactive config TUI
│   └── python-bridge.ts  # Bridge to Python CLI
└── scripts/
    └── install-python.mjs # Downloads/bundles Python wheel
```

**Shim behavior:**
1. `arc-studio` (no args) → launches Node.js chat REPL
2. `arc-studio run "..."` → bridges to Python `arc run`
3. `arc-studio config` → launches interactive config TUI
4. `arc-studio doctor` → bridges to Python `arc doctor`
5. `arc-studio advanced <cmd>` → passes through to Python CLI
6. `arc` (alias) → same as `arc-studio`

**Python wheel bundling:**
- npm package includes pre-built Python wheel
- Or downloads from PyPI on first run
- Uses embedded Python or system Python (detect)
- Alternative: `pipx install agent-runtime-cockpit` for Python-native path

### 4.2 CLI Entrypoint Changes

**New file: `python/src/agent_runtime_cockpit/chat_repl.py`**
```python
class ChatREPL:
    """Interactive chat-first CLI for ARC Studio."""

    def __init__(self, workspace: Path, config: ArcConfig):
        self.workspace = workspace
        self.config = config
        self.session = SessionManager(workspace)
        self.slash_router = SlashCommandRouter()

    def run(self, initial_prompt: str | None = None):
        """Main chat loop."""
        self.print_startup_banner()
        if initial_prompt:
            self.process_message(initial_prompt)
        while True:
            try:
                message = self.prompt_input()
                if message.startswith('/'):
                    self.slash_router.dispatch(message, self)
                else:
                    self.process_message(message)
            except KeyboardInterrupt:
                self.session.save()
                break
            except EOFError:
                self.session.save()
                break

    def process_message(self, message: str):
        """Route message to appropriate handler."""
        # Detect intent: run workflow, ask question, inspect trace, etc.
        # Use LLM for complex queries, direct handlers for commands
        pass
```

**Slash command router:**
```python
class SlashCommandRouter:
    """Routes /commands to handlers."""

    COMMANDS = {
        '/config': ConfigHandler,
        '/runtime': RuntimeSwitchHandler,
        '/model': ModelSwitchHandler,
        '/status': StatusHandler,
        '/run': RunWorkflowHandler,
        '/doctor': DoctorHandler,
        '/workflows': WorkflowListHandler,
        '/runs': RunListHandler,
        '/plan': PlanModeHandler,
        '/build': BuildModeHandler,
        '/auto': AutoModeHandler,
        '/clear': ClearSessionHandler,
        '/compact': CompactSessionHandler,
        '/sessions': SessionListHandler,
        '/undo': UndoHandler,
        '/redo': RedoHandler,
        '/diff': DiffHandler,
        '/help': HelpHandler,
        '/exit': ExitHandler,
        '/advanced': AdvancedModeHandler,
    }
```

### 4.3 Config Loader Updates

**Current:** `config/loader.py` loads YAML with 4-level precedence

**New additions:**
- Interactive config editor (TUI with rich/Textual)
- Config validation with user-friendly errors
- Config migration from old format
- Provider key management (add/edit/remove via TUI)

**New file: `python/src/agent_runtime_cockpit/config/editor.py`**
```python
class ConfigEditor:
    """Interactive TUI config editor."""

    def run(self):
        """Launch interactive config editor."""
        # Uses rich/Textual for TUI
        # Shows runtime selection, model selection, provider keys
        # Saves to workspace or user config
        pass
```

### 4.4 Runtime-Selection Abstraction

**Current:** `RuntimeRouter` with auto-priority and explicit runtime ID

**New:** Add session-scoped runtime preference

```python
class SessionRuntime:
    """Per-session runtime preference."""

    def __init__(self, config: ArcConfig):
        self.config = config
        self.override: str | None = None  # Set by /runtime command

    def resolve(self) -> str:
        """Get active runtime for this session."""
        if self.override:
            return self.override
        return self.config.runtime.default or 'auto'

    def switch(self, runtime_id: str):
        """Switch runtime for current session."""
        self.override = runtime_id
        # Validate runtime is available
```

### 4.5 Daemon/Session Lifecycle

**New session management:**
```
~/.arc/sessions/
├── abc123.json    # Session state
├── def456.json
└── latest -> abc123.json  # Symlink to most recent
```

**Session state:**
```json
{
  "id": "abc123",
  "workspace": "/Users/hans/my-project",
  "runtime": "swarmgraph",
  "model": "claude-sonnet-4-5",
  "mode": "build",
  "messages": [
    {"role": "user", "content": "Run the workflow"},
    {"role": "assistant", "content": "Starting swarmgraph..."}
  ],
  "runs": ["run-001", "run-002"],
  "created": "2026-05-15T14:30:00Z",
  "updated": "2026-05-15T14:35:00Z"
}
```

### 4.6 Theia Frontend Layout Changes

**Current:** 5 separate widgets, each registered independently

**New:** Single `ArcStudioWidget` with tabbed interface

**File changes:**
```
packages/arc-extension/src/browser/
├── arc-studio-widget.tsx          # NEW: Main widget with tabs
├── tabs/
│   ├── ChatTab.tsx                # NEW: Chat panel
│   ├── RunsTab.tsx                # REFACTOR: Merges timeline + event stream
│   ├── WorkflowsTab.tsx           # REFACTOR: Merges detection + graph
│   └── ConfigTab.tsx              # NEW: Config panel
├── components/
│   ├── ChatMessage.tsx            # NEW: Chat message bubble
│   ├── ChatInput.tsx              # NEW: Chat input with slash commands
│   ├── RuntimeSelector.tsx        # NEW: Runtime dropdown
│   ├── ModelSelector.tsx          # NEW: Model dropdown
│   ├── ModeToggle.tsx             # NEW: Plan/Build toggle
│   ├── DiffViewer.tsx             # NEW: Inline diff view
│   ├── ApprovalButtons.tsx        # NEW: Approve/Reject/Edit
│   ├── RunCard.tsx                # NEW: Run list card
│   ├── RunTimeline.tsx            # MOVE: From arc-run-timeline-widget
│   ├── WorkflowCard.tsx           # NEW: Workflow card
│   └── StatusBar.tsx              # NEW: Bottom status bar
├── arc-widget.tsx                 # DEPRECATE: Replace with arc-studio-widget
├── arc-adapters-widget.tsx        # KEEP: For advanced users
├── arc-workflow-graph-widget.tsx  # MERGE: Into WorkflowsTab
├── arc-run-timeline-widget.tsx    # MERGE: Into RunsTab
└── arc-event-stream-widget.tsx    # MERGE: Into RunsTab
```

**Widget registration:**
```typescript
// Replace 5 widget registrations with 1
bindViewContribution(bindings, ArcStudioContribution);
bind(ArcStudioWidget).toSelf();
bind(WidgetFactory).toDynamicValue(ctx => ({
  id: 'arc-studio',
  createWidget: () => ctx.container.get(ArcStudioWidget),
}));
```

### 4.7 Protocol/API Changes

**New protocol methods needed:**

```typescript
interface ArcService {
  // Existing (keep)
  executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult>;
  cancelWorkflow(runId: string): Promise<CancelResult>;
  getTraces(): Promise<TraceFile[]>;
  readTrace(traceId: string): Promise<TraceData>;
  detectWorkflows(): Promise<WorkflowInfo[]>;
  listRuntimeCapabilities(): Promise<RuntimeCapabilitiesResponse>;

  // New (chat/session)
  sendChatMessage(sessionId: string, message: string): Promise<ChatResponse>;
  createSession(workspace: string): Promise<Session>;
  resumeSession(sessionId: string): Promise<Session>;
  listSessions(workspace: string): Promise<Session[]>;
  getSession(sessionId: string): Promise<Session>;

  // New (config)
  getConfig(workspace: string): Promise<ArcConfig>;
  updateConfig(workspace: string, config: Partial<ArcConfig>): Promise<void>;
  switchRuntime(workspace: string, runtimeId: string): Promise<void>;
  switchModel(workspace: string, modelId: string): Promise<void>;

  // New (HITL/diff)
  requestApproval(runId: string, diff: DiffProposal): Promise<ApprovalResponse>;
  applyDiff(runId: string, diffId: string): Promise<void>;
  rejectDiff(runId: string, diffId: string): Promise<void>;
}
```

---

## 5. Implementation Phases

### Phase 1: Research + Product Spec (1 week)
**Goal:** Finalize this plan, get review approval

- [x] Research competitor CLIs and IDEs
- [x] Document current ARC Studio state
- [x] Draft this plan
- [ ] Review with team
- [ ] Finalize scope for Phase 2

**Deliverable:** Approved plan document (this file)

### Phase 2: Global CLI Wrapper (1-2 weeks)
**Goal:** `arc-studio` installs globally and launches

- [ ] Create `packages/arc-studio-cli/` npm package
- [ ] Implement Node.js shim (`bin/arc-studio`)
- [ ] Bundle/download Python wheel
- [ ] Implement Python bridge (child_process to `arc`)
- [ ] Create `arc` alias
- [ ] Test: `npm install -g arc-studio` → `arc-studio --version` works
- [ ] Test: `pipx install agent-runtime-cockpit` → `arc --version` works
- [ ] Publish to npm (alpha tag)

**Deliverable:** `npm install -g arc-studio` works

### Phase 3: Chat-First CLI Shell (2-3 weeks)
**Goal:** `arc-studio` launches interactive chat

- [ ] Implement `ChatREPL` in Python
- [ ] Implement startup banner with workspace/runtime/model info
- [ ] Implement message processing loop
- [ ] Add streaming output with rich formatting
- [ ] Add permission prompts for write operations
- [ ] Implement session persistence (`~/.arc/sessions/`)
- [ ] Implement `arc-studio -c` (continue) and `arc-studio -r` (resume)
- [ ] Test: `arc-studio` → chat REPL launches
- [ ] Test: Send message → agent responds
- [ ] Test: `arc-studio -c` → resumes last session

**Deliverable:** `arc-studio` launches chat, processes messages

### Phase 4: Slash Commands + Config (2 weeks)
**Goal:** `/config`, `/runtime`, `/model` work

- [ ] Implement `SlashCommandRouter`
- [ ] Implement all 20 slash commands
- [ ] Implement interactive config TUI (`ConfigEditor`)
- [ ] Implement runtime switching via `/runtime`
- [ ] Implement model switching via `/model`
- [ ] Add plan/build mode toggle (`/plan`, `/build`)
- [ ] Test: `/config` → interactive editor opens
- [ ] Test: `/runtime langgraph` → switches runtime
- [ ] Test: `/model gpt-4o` → switches model

**Deliverable:** Full slash command set works

### Phase 5: IDE Navigation Simplification (2-3 weeks)
**Goal:** Single ARC Studio widget with tabs

- [ ] Create `ArcStudioWidget` with tab bar
- [ ] Implement `ChatTab` (chat panel with input)
- [ ] Implement `RunsTab` (merged timeline + event stream)
- [ ] Implement `WorkflowsTab` (merged detection + graph)
- [ ] Implement `ConfigTab` (config panel)
- [ ] Implement `StatusBar` component
- [ ] Implement `RuntimeSelector` and `ModelSelector` dropdowns
- [ ] Implement `ModeToggle` (Plan/Build)
- [ ] Deprecate old 5 widgets (keep for backward compat)
- [ ] Test: Open ARC Studio → single widget with tabs
- [ ] Test: Switch tabs → content loads correctly

**Deliverable:** Single widget with 4 tabs replaces 5 widgets

### Phase 6: Chat + HITL + Diff Polish (2-3 weeks)
**Goal:** Chat panel with agent interaction, approvals, diffs

- [ ] Implement `ChatMessage` component (bubbles)
- [ ] Implement `ChatInput` with slash command autocomplete
- [ ] Implement `DiffViewer` component
- [ ] Implement `ApprovalButtons` (Approve/Reject/Edit)
- [ ] Wire chat to backend agent execution
- [ ] Implement HITL flow in chat (agent requests approval)
- [ ] Implement inline diff display
- [ ] Add real-time status indicators (timers, checkmarks)
- [ ] Add streaming response rendering
- [ ] Test: Chat → run workflow → see results
- [ ] Test: Agent proposes change → approve → applied

**Deliverable:** Chat panel with full agent interaction

### Phase 7: Docs, Tests, Release Prep (1-2 weeks)
**Goal:** Production-ready CLI + IDE

- [ ] Update README with new install/run instructions
- [ ] Write CLI usage docs
- [ ] Write IDE usage docs
- [ ] Write migration guide for existing `arc` users
- [ ] Write advanced commands doc (`docs/advanced-cli.md`)
- [ ] Add CLI integration tests
- [ ] Add Theia UI contract tests
- [ ] Add E2E browser tests for chat flow
- [ ] Run full test suite: Python + TypeScript
- [ ] Run banned claims check on all docs
- [ ] Update RELEASE_CHECKLIST.md
- [ ] Set release date
- [ ] Execute `.env` history scrub
- [ ] Tag v0.1.0-alpha

**Deliverable:** v0.1.0-alpha release

---

## 6. Testing Plan

### 6.1 CLI Install Tests

| Test | Description |
|------|-------------|
| `npm install -g arc-studio` | Global install succeeds |
| `arc-studio --version` | Prints version, exits 0 |
| `arc-studio --help` | Shows chat-first help (not 60+ commands) |
| `arc-studio` | Launches chat REPL |
| `arc-studio "hello"` | Launches chat with initial prompt |
| `arc-studio -c` | Continues last session |
| `arc-studio config` | Opens interactive config |
| `arc-studio doctor` | Runs diagnostics |
| `pipx install agent-runtime-cockpit` | Python install succeeds |
| `arc --version` | Prints version (backward compat) |
| `arc advanced runs list` | Advanced commands accessible |

### 6.2 CLI Interactive Smoke Tests

| Test | Description |
|------|-------------|
| Chat launch | REPL starts with banner |
| Message processing | User message → agent response |
| Slash command routing | `/help` → shows command list |
| `/config` | Opens interactive editor |
| `/runtime swarmgraph` | Switches runtime |
| `/model claude-sonnet-4-5` | Switches model |
| `/status` | Shows workspace/runtime/session info |
| `/run` | Runs detected workflow |
| `/runs` | Shows run summaries, filters, and failure cards |
| `RunContract` | Pre-run contract generated with objective/runtime/mode/cost/rollback |
| `RunReceipt` | Completed/failed run emits signed receipt artifact |
| Failure Autopsy | Failed run shows knows/guesses/confidence/evidence split |
| Evidence refs | Chat/run/failure objects can carry file/tool evidence refs |
| `/doctor` | Runs diagnostics inline |
| `/plan` | Switches to plan mode |
| `/build` | Switches to build mode |
| `/exit` | Saves session, exits |
| Session persistence | Exit → `-c` → restores state |
| Non-interactive | `arc-studio run "..."` → runs and exits |

### 6.3 Config Tests

| Test | Description |
|------|-------------|
| Config init | `arc-studio config` → creates `.arc/config.yaml` |
| Config load | Loads workspace + user config with precedence |
| Runtime selection | Select runtime → persists to config |
| Model selection | Select model → persists to config |
| Provider key add | Add key → persists securely |
| Invalid config | Shows user-friendly error |
| Config migration | Old format → new format auto-migration |

### 6.4 Runtime-Switching Tests

| Test | Description |
|------|-------------|
| `/runtime swarmgraph` | Switches to SwarmGraph |
| `/runtime langgraph` | Switches to LangGraph |
| Invalid runtime | Shows available runtimes |
| Runtime detection | Shows ✓/✗/⚠ per runtime |
| Session-scoped | Switch persists within session |
| Config-scoped | `/config` → save → persists across sessions |

### 6.5 Theia UI Contract Tests

| Test | Description |
|------|-------------|
| Widget registration | Single `arc-studio` widget registered |
| Tab rendering | 4 tabs render correctly |
| Chat tab | Chat input + messages render |
| Runs tab | Run list + detail split view |
| Workflows tab | Workflow cards with actions |
| Config tab | Config form with save |
| Status bar | Runtime/model/mode visible |
| Runtime dropdown | Opens, selects, closes |
| Model dropdown | Opens, selects, closes |
| Mode toggle | Plan/Build toggles correctly |
| Tab switching | Content updates on tab change |

### 6.6 E2E Browser Tests

| Test | Description |
|------|-------------|
| App starts | `pnpm start:browser` → localhost:3000 reachable |
| ARC widget loads | `arc-studio` widget renders |
| Chat tab default | Chat tab is default active tab |
| Send message | Type message → click send → response appears |
| Run workflow | Click "Run" on workflow card → execution starts |
| View trace | Click run in list → timeline renders |
| Switch config | Click Config tab → form loads |
| Change runtime | Select runtime → save → persists |
| HITL flow | Agent proposes → approve → change applied |

### 6.7 Backward Compatibility Tests

| Test | Description |
|------|-------------|
| `arc runs list` | Still works (via `arc advanced runs list` or `ARC_EXPERT=1`) |
| `arc runtimes --capabilities --json` | Still works |
| `arc doctor all` | Still works |
| `arc config show` | Still works |
| `arc isolation status` | Still works |
| `arc audit verify` | Still works |
| Python tests | All 550 existing tests pass |
| Extension tests | All 270 existing tests pass |

---

## 7. Risks and Open Questions

### 7.1 Distribution

| Question | Options | Recommendation |
|----------|---------|---------------|
| npm vs pip for global install? | npm (arc-studio), pipx (agent-runtime-cockpit), both | **Both** — npm for Node-first users, pipx for Python-first |
| How to bundle Python wheel in npm package? | Include in npm tarball, download on first run, use system Python | **Download on first run** — keeps npm package small |
| What Python to use? | System Python, embedded Python, user's venv | **Detect system Python first**, fall back to download prompt |
| Should `arc` remain as alias? | Yes (backward compat), No (clean break) | **Yes** — `arc` → `arc-studio` symlink |

### 7.2 CLI Architecture

| Question | Options | Recommendation |
|----------|---------|---------------|
| Should chat REPL be in Python or Node? | Python (rich/Textual), Node (Ink/Blessed) | **Python** — existing codebase, rich library available |
| Should Node shim bridge to Python or reimplement? | Bridge (child_process), Reimplement (native Node) | **Bridge** — less duplication, Python is canonical |
| How to handle existing `arc` command? | Alias to `arc-studio`, Keep separate, Deprecate | **Alias** — `arc` → `arc-studio` with chat-first default |
| Should low-level commands remain public? | Yes (hidden), No (remove), Yes (expert mode) | **Expert mode** — `arc advanced <cmd>` or `ARC_EXPERT=1` |

### 7.3 Runtime Switching

| Question | Options | Recommendation |
|----------|---------|---------------|
| Session-scoped or global? | Session only, Global config, Both | **Both** — session override + config default |
| What happens when runtime not available? | Error, Fallback to auto, Show available | **Show available** — list detected runtimes |
| Can user switch mid-conversation? | Yes, No (restart required) | **Yes** — `/runtime` switches for next message |
| How does combo runtime work in chat? | `/runtime langgraph+swarmgraph`, Config only | **Both** — slash command + config |

### 7.4 Config

| Question | Options | Recommendation |
|----------|---------|---------------|
| Project-local or user-global config precedence? | Project > User (current), User > Project | **Keep current** — CLI > env > workspace > user > defaults |
| How to store provider keys? | Env vars only, Keychain, Encrypted config | **Env vars + keychain** — don't store keys in config files |
| Should config be editable in IDE? | Yes (Config tab), No (CLI only) | **Yes** — Config tab in IDE |
| Config format? | YAML (current), JSON, TOML | **Keep YAML** — existing ADR-001 model |

### 7.5 Theia UI

| Question | Options | Recommendation |
|----------|---------|---------------|
| How much to redesign before v0.1? | Full redesign, Incremental, Tabs only | **Tabs only** — merge existing widgets into tabbed interface |
| Should old widgets remain? | Yes (backward compat), No (remove) | **Yes** — keep as hidden/advanced widgets |
| Chat in Theia or CLI only for v0.1? | Both, CLI only, Theia only | **Both** — chat REPL + Theia chat tab |
| How to handle agent responses in Theia? | Stream via SSE, Poll, WebSocket | **SSE** — existing event broker infrastructure |

### 7.6 Scope and Timeline

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Phase 2 (npm wrapper) takes longer than expected | Delays all phases | Start with pipx path first, npm second |
| Chat REPL quality not competitive | Poor user experience | Use rich/Textual for polished TUI |
| Theia tab redesign breaks existing widgets | Regression | Keep old widgets, add new tabbed widget |
| Session persistence complex | Delays Phase 3 | Start with simple JSON file, add SQLite later |
| HITL/diff UX in Theia is hard | Delays Phase 6 | Start with simple approve/reject, add diff later |
| Total timeline exceeds expectations | Release delayed | Phase 2-4 can ship independently as CLI-only alpha |

### 7.7 Key Decisions Needed

1. **Release date:** Deferred until this UX direction works. When do we want to target?
2. **npm package name:** `arc-studio` available on npm? Need to check.
3. **Chat model:** What LLM powers the chat agent? Currently ARC doesn't have a built-in chat model.
4. **Agent architecture:** Does the chat agent use the same runtimes, or is it a separate LLM call?
5. **Theia version:** Stay on 1.71.0 or upgrade?
6. **Backward compat:** How long do we support old `arc` command shape?

---

## 8. Acceptance Criteria

### CLI (Phases 2-4)

- [ ] `npm install -g arc-studio` succeeds
- [ ] `arc-studio` launches interactive chat REPL
- [ ] `arc-studio "query"` launches chat with initial prompt
- [ ] `arc-studio run "query"` runs non-interactively
- [ ] `arc-studio -c` resumes last session
- [ ] `arc-studio config` opens interactive config editor
- [ ] `arc-studio doctor` runs diagnostics
- [ ] `arc-studio --version` prints version
- [ ] `arc-studio --help` shows chat-first help (< 20 lines)
- [ ] `/config` opens interactive config
- [ ] `/runtime <id>` switches runtime
- [ ] `/model <id>` switches model
- [ ] `/status` shows workspace/runtime/session info
- [ ] `/run` runs detected workflow
- [ ] `/help` shows slash command list
- [ ] All 20 slash commands work
- [ ] Session persists across launches
- [ ] `arc advanced <cmd>` accesses old commands
- [ ] All 550 Python tests pass
- [ ] All 270 extension tests pass

### IDE (Phases 5-6)

- [ ] Single `arc-studio` widget replaces 5 widgets
- [ ] 4 tabs: Chat, Runs, Workflows, Config
- [ ] Chat tab has input + messages + send button
- [ ] Runs tab has list + detail split view
- [ ] Workflows tab has cards with Run/Inspect/Graph
- [ ] Config tab has runtime/model/provider/mode settings
- [ ] Status bar shows runtime/model/mode
- [ ] Runtime dropdown switches runtime
- [ ] Model dropdown switches model
- [ ] Plan/Build toggle works
- [ ] Chat sends messages and receives responses
- [ ] HITL approval flow works (Approve/Reject)
- [ ] Diff viewer shows proposed changes
- [ ] All existing tests pass
- [ ] New UI contract tests pass

### Release (Phase 7)

- [ ] README updated with new install instructions
- [ ] CLI usage docs written
- [ ] IDE usage docs written
- [ ] Migration guide written
- [ ] Advanced commands doc written
- [ ] Banned claims check passes
- [ ] RELEASE_CHECKLIST.md all items green
- [ ] `.env` history scrubbed
- [ ] CI green for 3 consecutive days
- [ ] v0.1.0-alpha tagged and published

---

## Appendix A: Current CLI Command Inventory

See Section 1 of the codebase inventory (from exploration agent). 60+ commands across 15 subcommand groups, max nesting depth 3.

## Appendix B: Current IDE Widget Inventory

See Section 2 of the codebase inventory. 5 widgets, no unified navigation, no chat panel.

## Appendix C: Competitor Slash Command Reference

Full slash command tables for Claude Code (40+), Codex CLI (30+), Aider (35+), OpenCode (6+ custom) documented in Section 1.1 research.
