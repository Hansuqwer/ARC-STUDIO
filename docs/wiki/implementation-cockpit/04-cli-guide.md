# 04 — CLI Guide

## Current State

**Entry point:** `python/src/agent_runtime_cockpit/cli.py` — 79 commands, 3-level nesting, `no_args_is_help=True`
**Install:** `pip install agent-runtime-cockpit` → `arc` command (requires Python venv)
**No chat REPL, no session concept, no slash commands**

## Target State

- `arc-studio` launches interactive chat REPL
- `arc-studio "query"` launches with initial prompt
- `arc-studio -c` resumes last session
- `arc-studio config` opens interactive config TUI
- `arc-studio doctor` runs diagnostics
- `arc-studio advanced <cmd>` accesses all old 79 commands

## Implementation Slice 1: Chat REPL

**Create file:** `python/src/agent_runtime_cockpit/cli/chat_repl.py`

```python
class ChatREPL:
    """
    Interactive chat-first CLI for ARC Studio.
    Uses rich for formatting. No Textual dependency.
    """
    def __init__(self, workspace: Path, config: ArcConfig):
        self.workspace = workspace
        self.config = config
        self.session_mgr = SessionManager(workspace)
        self.slash_router = SlashCommandRouter()

    def run(self, initial_prompt: str | None = None):
        """Main chat loop."""
        ...
```

**Acceptance criteria:**
- `arc-studio` (no args) → startup banner with workspace/runtime/model/mode
- User types message → agent processes → streaming response
- `Ctrl+C` saves session and exits
- Session saved to `~/.arc/sessions/<session_id>/transcript.jsonl`

## Implementation Slice 2: Slash Commands

**Create file:** `python/src/agent_runtime_cockpit/cli/slash_commands.py`

```python
class SlashCommandRouter:
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
        '/receipt': ReceiptHandler,
        '/contract': ContractHandler,
    }
```

**Acceptance criteria:**
- All 22 commands work
- `/config` opens interactive config editor (rich Table + Panel)
- `/runtime <id>` switches runtime for session
- `/model <id>` switches model
- `/runs` lists runs from SQLite index
- `/receipt show <run-id>` prints receipt
- `/contract show` prints current run contract
- Command aliases work: `/q → /exit`, `/s → /status`, `/h → /help`

## Implementation Slice 3: Session Manager

**Create file:** `python/src/agent_runtime_cockpit/cli/session.py`

```python
class SessionManager:
    """Manages CLI session lifecycle."""
    def __init__(self, workspace: Path): ...
    def create(self) -> Session: ...
    def resume(self, session_id: str) -> Session: ...
    def list(self) -> list[SessionSummary]: ...
    def save(self, session: Session): ...
    def compact(self, session_id: str) -> Session: ...
```

**Session storage:** `~/.arc/sessions/<session_id>/` with `metadata.yaml`, `transcript.jsonl`, `runs.jsonl`
**Latest session symlink:** `~/.arc/sessions/latest → <session_id>/`
**Session ID format:** ULID (26 chars, lexicographically sortable, time-ordered)

**Acceptance criteria:**
- Sessions survive process exit
- `arc-studio -c` resumes latest session
- `arc-studio -r <session-id>` resumes specific session
- `/sessions` lists recent sessions
- `/compact` summarizes transcript to free tokens
- Session lock prevents concurrent write corruption

## Implementation Slice 4: npm Wrapper

**Create directory:** `packages/arc-studio-cli/`

```
packages/arc-studio-cli/
├── package.json          # name: arc-studio, bin: arc-studio
├── bin/arc-studio        # Node.js shim → Python bridge
├── src/cli.ts            # CLI argument parser
├── src/python-bridge.ts  # child_process bridge to arc CLI
└── scripts/install-python.mjs  # Download/bundle Python wheel
```

**Shim behavior:**
1. No args → `arc chat-repl` (new subcommand)
2. `run "..."` → `arc run --prompt "..."`
3. `config` → `arc-studio config` → launches TUI editor
4. `doctor` → `arc doctor all`
5. `advanced <cmd>` → `arc <cmd>` with `ARC_STUDIO_ADVANCED=1`
6. `--version` → prints version
7. `--help` → shows chat-first help (< 20 lines)

**Acceptance criteria:**
- `npm install -g arc-studio` succeeds
- `arc-studio` launches chat REPL
- `arc-studio --version` prints version
- `arc-studio --help` shows chat-first help
- `arc-studio advanced runs list` still works
- `arc` alias works (symlink to `arc-studio`)

## Do Not Implement Yet

- `@file`/`@folder` mentions — Phase 4 of redesign plan
- Queued input for active runs — Phase 4
- Fuzzy slash autocomplete — Phase 4
- Config migration from old format — Phase 4
- Textual/TUI advanced screens — Phase 5
- Second-terminal graph — v0.2 [RESERVED]
