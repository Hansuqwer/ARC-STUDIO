# Slash Commands Reference

**Type:** Reference (Diátaxis)  
**Audience:** Chat REPL users, interactive developers  
**Purpose:** Complete reference for all `/` slash commands in ARC Studio chat REPL

---

## Overview

Slash commands are used in the ARC Studio chat REPL for:
- Controlling runtime mode and execution
- Managing chat sessions
- Viewing workspace and run status
- Running diagnostics

**Total commands:** 17 (across 4 categories)  
**Access:** Type `/help` in the chat REPL to see all commands

---

## Command Categories

| Category | Commands | Purpose |
|----------|----------|---------|
| [Meta](#meta-commands) | 3 | Help, version, exit |
| [Runtime](#runtime-commands) | 7 | Execution mode and tools |
| [Session](#session-commands) | 4 | Chat history and sessions |
| [Workspace](#workspace-commands) | 3 | Status and diagnostics |

---

## Meta Commands

### /help

Show available slash commands.

**Syntax:**
```
/help
```

**Output:**
- List of all commands grouped by category
- Brief description of each command
- Usage instructions

**Example:**
```
> /help

Available slash commands:

  [META]
    /exit (/quit)  Save session and exit
    /help  Show this message
    /version  Show version info

  [RUNTIME]
    /auto  Switch to policy-driven mode
    /build  Switch to Build mode (can write)
    ...
```

---

### /version

Show ARC Studio version information.

**Syntax:**
```
/version
```

**Output:**
- ARC Studio version
- Python version
- Runtime versions (if available)

**Example:**
```
> /version
ARC Studio v0.2.0
Python 3.11.15
SwarmGraph 0.1.0
```

---

### /exit

Save session and exit the chat REPL.

**Syntax:**
```
/exit
```

**Aliases:**
- `/quit`

**Behavior:**
- Saves current chat session
- Exits the REPL
- Returns to shell

**Example:**
```
> /exit
Session saved.
Goodbye!
```

---

## Runtime Commands

### /run

Execute prompt with SwarmGraph runner.

**Syntax:**
```
/run <prompt>
```

**Arguments:**
- `<prompt>` — Prompt text to execute

**Requirements:**
- Runtime mode must be `build` or `auto`
- `ARC_ALLOW_RUN=1` environment variable (for safety)

**Example:**
```
> /run Create a simple hello world function

Executing with SwarmGraph...
Run ID: abc123def456
Status: completed
```

**Notes:**
- This is a gated feature (requires explicit opt-in)
- Uses current runtime and profile settings
- Creates a new run in the workspace

---

### /runtime

Show or set runtime mode.

**Syntax:**
```
/runtime [mode]
```

**Arguments:**
- `[mode]` — Optional: fake, gated_local, provider_backed

**Without arguments:**
Shows current runtime mode.

**With mode argument:**
Sets runtime mode.

**Modes:**
- `fake` — Offline, no provider calls, no cost
- `gated_local` — Local execution, gated provider calls
- `provider_backed` — Cloud execution, real provider calls

**Examples:**
```
> /runtime
Current runtime mode: fake

> /runtime gated_local
Runtime mode set to: gated_local
```

**Alias:**
- `/mode`

---

### /tools

Manage session tools.

**Syntax:**
```
/tools [action] [tool_name]
```

**Actions:**
- `list` — List all available tools
- `enable <tool>` — Enable a tool
- `disable <tool>` — Disable a tool

**Examples:**
```
> /tools list
Available tools:
  - read_file (enabled)
  - list_directory (enabled)
  - get_current_time (enabled)

> /tools disable read_file
Tool 'read_file' disabled.

> /tools enable read_file
Tool 'read_file' enabled.
```

---

### /plan

Switch to Plan mode (read-only).

**Syntax:**
```
/plan
```

**Behavior:**
- Sets mode to `plan`
- Disables write operations
- Disables `/run` command
- Allows read-only exploration

**Example:**
```
> /plan
Switched to Plan mode (read-only).
```

**Use case:**
- Exploring ideas without making changes
- Reviewing code without risk
- Planning before building

---

### /build

Switch to Build mode (can write).

**Syntax:**
```
/build
```

**Behavior:**
- Sets mode to `build`
- Enables write operations
- Enables `/run` command (if gated)
- Allows code execution

**Example:**
```
> /build
Switched to Build mode (can write).
```

**Use case:**
- Implementing features
- Making code changes
- Running workflows

---

### /auto

Switch to policy-driven mode.

**Syntax:**
```
/auto
```

**Behavior:**
- Sets mode to `auto`
- Enables automatic decision-making
- Uses policy to decide read/write
- Enables `/run` command (if gated)

**Example:**
```
> /auto
Switched to Auto mode (policy-driven).
```

**Use case:**
- Autonomous agent behavior
- Automatic workflow execution
- Policy-based decisions

---

### /mode

Alias for `/runtime`.

**Syntax:**
```
/mode [mode]
```

See [/runtime](#runtime) for details.

---

## Session Commands

### /clear

Clear session history.

**Syntax:**
```
/clear
```

**Behavior:**
- Clears all messages from current session
- Does not delete saved session
- Resets transcript

**Example:**
```
> /clear
Session history cleared.
```

---

### /history

Show recent messages.

**Syntax:**
```
/history [limit]
```

**Arguments:**
- `[limit]` — Optional: number of messages to show (default: 10)

**Output:**
- Recent messages from current session
- Includes user and system messages
- Shows timestamps

**Example:**
```
> /history 5

Recent messages:
  [05:00:15] user: Hello
  [05:00:16] system: Hi! How can I help?
  [05:01:00] user: Show me the status
  [05:01:01] system: Workspace status: ...
  [05:02:00] user: /history 5
```

---

### /sessions

List saved sessions.

**Syntax:**
```
/sessions
```

**Output:**
- List of saved chat sessions
- Session IDs
- Last modified timestamps
- Message counts

**Example:**
```
> /sessions

Saved sessions:
  1. session_abc123 (10 messages, modified 2026-05-22 05:00:00)
  2. session_def456 (25 messages, modified 2026-05-21 14:30:00)
  3. session_ghi789 (5 messages, modified 2026-05-20 10:15:00)
```

**Note:**
- To resume a session, restart the REPL with `--session-id`
- Sessions are saved automatically on exit

---

### /summary

Show session summary.

**Syntax:**
```
/summary
```

**Output:**
- Current session ID
- Message count
- Session duration
- Runtime mode
- Profile
- Tools enabled/disabled

**Example:**
```
> /summary

Session Summary:
  Session ID: session_abc123
  Messages: 15
  Duration: 10 minutes
  Runtime mode: fake
  Profile: local-safe
  Tools: 3 enabled, 0 disabled
```

---

## Workspace Commands

### /status

Show workspace, runtime, and session status.

**Syntax:**
```
/status
```

**Output:**
- Workspace path
- Detected runtimes
- Available workflows
- Recent runs
- Session info

**Example:**
```
> /status

Workspace: /path/to/workspace
Runtimes: swarmgraph (can_run: true), langgraph (can_run: false)
Workflows: 3 detected
Recent runs: 5 completed, 1 failed
Session: 15 messages, 10 minutes
```

---

### /doctor

Run environment diagnostics.

**Syntax:**
```
/doctor
```

**Output:**
- Environment health checks
- Runtime availability
- Provider configuration
- Storage status
- Network connectivity

**Example:**
```
> /doctor

Environment Diagnostics:
  ✓ Python 3.11.15
  ✓ SwarmGraph installed
  ✗ LangGraph not installed
  ✓ Storage: 2.3 GB used, 50 GB available
  ✓ Network: connected
  ✗ Provider: OpenAI not configured
```

---

### /runs

List recent run records.

**Syntax:**
```
/runs [limit]
```

**Arguments:**
- `[limit]` — Optional: number of runs to show (default: 10)

**Output:**
- Recent runs from workspace
- Run IDs
- Status (completed, failed, cancelled)
- Timestamps

**Example:**
```
> /runs 5

Recent runs:
  1. abc123def456 (completed, 2026-05-22 05:00:00)
  2. ghi789jkl012 (completed, 2026-05-22 04:55:00)
  3. mno345pqr678 (failed, 2026-05-22 04:50:00)
  4. stu901vwx234 (completed, 2026-05-22 04:45:00)
  5. yza567bcd890 (cancelled, 2026-05-22 04:40:00)
```

---

## Command Modes

The chat REPL has three modes that affect which commands are available:

### Plan Mode (Read-Only)

**Enabled commands:**
- All meta commands
- All session commands
- All workspace commands
- `/runtime`, `/tools` (read-only)

**Disabled commands:**
- `/run` (cannot execute)
- `/build`, `/auto` (mode switches)

**Use case:**
- Exploring and planning
- Reviewing code
- No risk of changes

---

### Build Mode (Can Write)

**Enabled commands:**
- All commands
- `/run` (if gated)

**Use case:**
- Implementing features
- Making changes
- Running workflows

---

### Auto Mode (Policy-Driven)

**Enabled commands:**
- All commands
- `/run` (if gated)
- Automatic decision-making

**Use case:**
- Autonomous agents
- Policy-based execution
- Automatic workflows

---

## Usage Tips

### Discovering Commands

```
> /help
```

Shows all available commands with descriptions.

---

### Command History

Use arrow keys (↑/↓) to navigate command history in the REPL.

---

### Tab Completion

Tab completion is not yet supported for slash commands.

---

### Combining with Chat

You can mix slash commands with regular chat messages:

```
> /status
[Shows status]

> What workflows are available?
[AI responds with workflow list]

> /run Create a hello world function
[Executes workflow]
```

---

## Troubleshooting

### "Unknown slash command"

**Problem:** Command not recognized

**Solution:**
- Check spelling: `/help` not `/halp`
- Use `/help` to see available commands
- Commands are case-sensitive

---

### "/run is blocked"

**Problem:** `/run` command fails with "blocked" or "not allowed"

**Solution:**
- Set `ARC_ALLOW_RUN=1` environment variable
- Switch to `build` or `auto` mode: `/build`
- Check that runtime is available: `/status`

---

### "Mode switch failed"

**Problem:** Cannot switch to a different mode

**Solution:**
- Some modes require specific configuration
- Check runtime availability: `/doctor`
- Check profile permissions

---

### "Session not saved"

**Problem:** Session lost after exit

**Solution:**
- Use `/exit` or `/quit` to exit (saves session)
- Don't use Ctrl+C (may not save)
- Check session directory: `~/.arc/sessions/`

---

## Keyboard Shortcuts

In the chat REPL:

- `Ctrl+C` — Cancel current operation (may not save session)
- `Ctrl+D` — Exit (same as `/exit`)
- `↑` / `↓` — Navigate command history
- `Enter` — Submit message or command

---

## Related Documentation

- **[CLI Commands](./cli-commands.md)** — Full CLI reference
- **[How-To: Run a Workflow](../how-to/run-workflow.md)** — Running workflows
- **[Getting Started](../tutorials/getting-started.md)** — First steps tutorial
- **[Chat REPL Guide](../explanation/chat-repl.md)** — How the REPL works (to be created)
