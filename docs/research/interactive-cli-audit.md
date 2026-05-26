# ARC Studio Interactive CLI/UX Audit

**Created:** 2026-05-26
**Scope:** All interactive CLI surfaces, REPL, IDE integration, and UX gaps

---

## Current CLI Inventory

### CLI Entry Points

1. **`arc`** - Root CLI (Typer), `cli/_app.py`
   - Global flags: `--allow-paid`, `--trust-workspace`, `--dry-run`
   - TTY auto-launch: bare `arc` with TTY launches `run_chat_repl()`
   - `ARC_NO_TUI=1` disables TUI, shows help instead

2. **`arc-studio`** - Thin shim entry point, `cli_studio.py` (54 lines)
   - Delegates to `arc studio chat`
   - One-shot message support

3. **`arc studio chat`** - Interactive REPL, `cli_repl/chat_repl.py` (116 lines)
   - TTY prompt loop with history
   - Session persistence to `~/.arc/sessions/`
   - SwarmGraph runner integration (fake_offline only)
   - Provider-backed `/run` via `TurnManager` gated by `ARC_ALLOW_RUN`

4. **`arc studio sessions`** - Session management
   - `migrate` command: legacy → canonical format

### CLI Subcommands (Typer sub-apps)

| Sub-app | Commands | Description |
|---------|----------|-------------|
| `arc doctor` | all | Diagnostics |
| `arc sandbox` | doctor, run, audit-verify, audit-list, lima-template, microvm-plan | Sandbox policy & execution |
| `arc policy` | explain, approve, revoke, prune, list, show, validate | Policy management |
| `arc studio` | chat, sessions | REPL & session mgmt |
| `arc runs` | list, get, links | Run records |
| `arc hitl` | pending, respond, show, prune | HITL commands |
| `arc mcp` | serve --stdio | MCP control plane |
| `arc task` | create, status, list, cancel | Async task mgmt |
| `arc replay` | <run-id> | Replay analysis |
| `arc audit` | verify, key-* | Audit chain |
| `arc receipt` | show, export, verify | Run receipts |
| `arc profiles` | list, show, create, delete | Run profiles |
| `arc providers` | status, action, quota-* | Provider mgmt |
| `arc events` | watch, webhook-* | Event notifications |
| `arc battle` | - | SwarmGraph battle mode |
| `arc context` | pack, * | Context retrieval |
| `arc adapter` | * | Adapter mgmt |
| `arc arena` | * | LM Arena |
| `arc config` | * | Workspace config |
| `arc storage` | * | Storage mgmt |
| `arc workspace` | * | Workspace trust |
| `arc isolation` | * | Isolation providers |
| `arc eval` | * | Run evaluation |
| `arc prompt` | * | Prompt optimization |

### REPL Slash Commands

| Command | Category | Description |
|---------|----------|-------------|
| `/help` | meta | Show help |
| `/version` | meta | Show version |
| `/exit` / `/quit` | meta | Save & exit |
| `/clear` | session | Clear history |
| `/summary` | session | Session summary |
| `/sessions` | session | List sessions |
| `/history [n]` | session | Recent messages |
| `/run <prompt>` | runtime | Execute (gated by ARC_ALLOW_RUN) |
| `/runtime [mode]` | runtime | Show/set runtime mode |
| `/tools [list|enable|disable]` | runtime | Manage tools |
| `/mode` | runtime | Alias for /runtime |
| `/plan` | runtime | Switch to Plan mode |
| `/build` | runtime | Switch to Build mode |
| `/auto` | runtime | Switch to Auto mode |
| `/status` | workspace | Workspace/runtime/session status |
| `/doctor` | workspace | Environment diagnostics |
| `/runs` | workspace | Recent run records |

### Total: 40+ CLI commands, 17 slash commands, 23 Typer sub-apps

---

## UX Analysis

### What Works Well

1. **CLI decomposition is excellent** - 4225-line monolith → 15 command modules, all <500 lines
2. **Sandbox system is production-ready** - subprocess provider with env filtering, path guards, bounded output, audit events
3. **Policy system is comprehensive** - classify → decide → approve → execute → audit chain
4. **REPL has rich command registry** - declarative CommandDef with gates, modes, trust levels
5. **MCP control plane works** - stdio-only, 11 tools, 3 resources, trust-gated
6. **Task registry is complete** - SQLite-backed, state machine, retry, MCP tools
7. **Doctor/daemon parity closure** - all orphan routes have explicit fate labels

### UX Gaps & Issues

#### Gap 1: REPL is SwarmGraph-specific, not general-purpose
- `chat_repl.py:93-101` hardcodes `SwarmGraphRunner` for non-slash input
- No way to send arbitrary prompts through provider-backed runtime from REPL
- `/run` command exists but requires `ARC_ALLOW_RUN=1` gate
- User sees "ARC Studio - SwarmGraph Chat" in welcome message
- **Impact:** REPL feels like a toy/demo, not a production tool

#### Gap 2: No interactive mode for `arc sandbox run`
- `arc sandbox run` is batch-only (CLI args + JSON output)
- No TTY mode with interactive approval prompts
- The `--ask` flag exists but only works for non-JSON output
- No progress display during execution
- No structured output for terminal (just JSON)
- **Impact:** Users can't interactively sandbox-run commands from terminal

#### Gap 3: No REPL integration with sandbox/policy
- REPL has `/run` but doesn't know about sandbox policies
- No way to do `arc sandbox run --policy local-safe -- <cmd>` from REPL
- No `/sandbox` slash commands
- No `/policy explain` from REPL
- **Impact:** Sandbox/policy features are invisible to REPL users

#### Gap 4: No progress/feedback in REPL
- SwarmGraph runner runs synchronously with no progress updates
- No spinner, no step-by-step output, no live task tracking
- Provider-backed `/run` via `TurnManager` has event emission but no consumer
- **Impact:** User sits at a blank prompt during execution

#### Gap 5: IDE and CLI REPL are disconnected
- IDE uses `arc-extension` backend service → Python CLI
- REPL is standalone Python process
- No shared session state between IDE and CLI
- No way to export REPL session to IDE or vice versa
- **Impact:** Users doing CLI work can't bring it into IDE

#### Gap 6: No colored/structured output in REPL
- REPL uses plain `print()` for all output
- No rich formatting (tables, trees, progress bars)
- `/doctor` output is plain text with Unicode checkmarks
- `/status` output is plain text
- **Impact:** CLI REPL looks dated compared to modern CLI tools

#### Gap 7: No command history search
- History file stores raw input lines
- No `Ctrl+R` reverse search
- No history filtering by command type
- History is per-session, not global
- **Impact:** Users can't quickly find past commands

#### Gap 8: No error recovery in REPL
- Exceptions during run crash the REPL loop
- No `try/except` around user input processing
- Session state may be corrupted after crash
- **Impact:** Poor user experience on errors

#### Gap 9: No multi-command or pipeline support
- REPL processes one input at a time
- No `|` pipe between commands
- No `&&` / `||` chaining
- No batch mode (`arc run -f commands.txt`)
- **Impact:** Power users can't script workflows

#### Gap 10: No `arc` default TTY behavior documentation
- `bare arc` with TTY launches REPL automatically
- `ARC_NO_TUI=1` required for `arc --help`
- This is surprising to new users expecting `--help` by default
- **Impact:** User confusion, especially from other CLI tools

#### Gap 11: Sandbox audit is CLI-only, not REPL-integrated
- `arc sandbox audit-list` exists but no REPL command
- No `/audit` slash command
- No audit trail visible during REPL sessions
- **Impact:** Audit features are invisible to REPL users

#### Gap 12: No `arc studio status` or interactive dashboard
- `/status` shows basic info but not daemon health, trust state, or isolation status
- No `arc status` top-level command
- No `arc dashboard` for terminal-based monitoring
- **Impact:** Users need to remember specific commands to check system state

---

## Feature Completeness Matrix

| Feature | CLI | REPL | IDE | Status |
|---------|-----|------|-----|--------|
| Sandbox run | Yes (batch) | No | Partial | Batch only |
| Policy explain | Yes | No | No | REPL gap |
| Audit verify | Yes | No | Partial | REPL gap |
| HITL pending | Yes | No | Yes | REPL gap |
| Provider status | Yes | No | Yes | REPL gap |
| Run streaming | Yes | No | Yes | REPL gap |
| SwarmGraph insight | No | No | Yes | - |
| Doctor/diagnostics | Yes | Yes (/doctor) | Yes | Good |
| Session management | No | Yes | Partial | IDE gap |
| Task management | Yes | No | Partial | REPL gap |
| MCP serve | Yes | No | No | REPL gap |
| Event watch | Yes | No | Partial | REPL gap |
| Cost tracking | No | No | Yes | CLI/REPL gap |
| Replay analysis | Yes | No | Yes | REPL gap |
| Consensus escrow | No | No | Yes | CLI/REPL gap |
| Adaptive consensus | No | No | No | Not implemented |
| Budget tracking | No | No | Partial | CLI/REPL gap |

---

## Prioritized Recommendations

### P0: Fix REPL to be production-useful
1. Make `/run` use provider-backed runtime by default (not SwarmGraph fake_offline)
2. Add interactive approval flow for sandbox commands
3. Add progress updates during execution
4. Add error handling to prevent REPL crashes

### P1: Connect REPL to existing CLI features
5. Add `/sandbox`, `/policy`, `/audit`, `/tasks` slash commands
6. Add `/doctor` enhancement showing daemon health, trust, isolation
7. Add colored/structured output to all REPL commands
8. Add history search (`Ctrl+R`)

### P2: IDE-CLI unification
9. Shared session state between IDE and CLI
10. Export/import session between IDE and CLI
11. CLI can connect to running IDE daemon

### P3: Advanced features
12. Multi-command pipelines
13. Interactive dashboard (`arc dashboard`)
14. Command aliases and snippets
