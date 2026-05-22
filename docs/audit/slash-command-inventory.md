# ARC Studio Slash Commands Inventory

**Date:** 2026-05-22  
**Auditor:** Automated slash command audit  
**Scope:** All ARC Studio chat REPL slash commands  
**Status:** ⚠️ PARTIAL - Help text exists but individual `--help` flags not implemented

## Executive Summary

**Result:** All slash commands have help text in the registry, but individual commands don't support `--help` flags.

- **Total commands:** 19
- **Total aliases:** 2 (/quit → /exit, /mode → /runtime)
- **Commands with help text:** 19/19 ✅
- **Commands with `--help` flag:** 0/19 ❌

**Gap identified:** Individual slash commands don't support `--help` flags (e.g., `/run --help` doesn't show help for the run command).

## Slash Commands by Category

### META (3 commands)

| Command | Aliases | Help Text | `--help` Support |
|---------|---------|-----------|------------------|
| `/help` | - | Show this help message | ❌ |
| `/version` | - | Show version info | ❌ |
| `/exit` | `/quit` | Save session and exit | ❌ |

### SESSION (4 commands)

| Command | Aliases | Help Text | `--help` Support |
|---------|---------|-----------|------------------|
| `/clear` | - | Clear session history | ❌ |
| `/summary` | - | Show session summary | ❌ |
| `/sessions` | - | List saved sessions | ❌ |
| `/history` | - | Show recent messages | ❌ |

### RUNTIME (7 commands)

| Command | Aliases | Help Text | `--help` Support |
|---------|---------|-----------|------------------|
| `/run` | - | Execute prompt with SwarmGraph runner | ❌ |
| `/runtime` | `/mode` | Show or set runtime mode: fake, gated_local, provider_backed | ❌ |
| `/tools` | - | Manage session tools: /tools list\|enable\|disable | ❌ |
| `/plan` | - | Switch to Plan mode (read-only) | ❌ |
| `/build` | - | Switch to Build mode (can write) | ❌ |
| `/auto` | - | Switch to policy-driven mode | ❌ |
| `/mode` | (alias) | Alias for /runtime | ❌ |

### WORKSPACE (3 commands)

| Command | Aliases | Help Text | `--help` Support |
|---------|---------|-----------|------------------|
| `/status` | - | Show workspace, runtime, and session status | ❌ |
| `/doctor` | - | Run environment diagnostics | ❌ |
| `/runs` | - | List recent run records | ❌ |

## Command Details

### Meta Commands

#### /help
- **Description:** Show this help message
- **Usage:** `/help`
- **Output:** Lists all available slash commands with their help text
- **Notes:** This is the primary help command that shows all commands

#### /version
- **Description:** Show version info
- **Usage:** `/version`
- **Output:** "ARC Studio - SwarmGraph Native Runtime v0.1.0-alpha"

#### /exit (alias: /quit)
- **Description:** Save session and exit
- **Usage:** `/exit` or `/quit`
- **Output:** Exits the chat REPL

### Session Commands

#### /clear
- **Description:** Clear session history
- **Usage:** `/clear`
- **Output:** "Session history cleared."

#### /summary
- **Description:** Show session summary
- **Usage:** `/summary`
- **Output:** Session ID, message count, creation time

#### /sessions
- **Description:** List saved sessions
- **Usage:** `/sessions`
- **Output:** List of up to 10 most recent saved sessions

#### /history
- **Description:** Show recent messages
- **Usage:** `/history [n]`
- **Arguments:** `n` (optional) - number of messages to show (default: 10)
- **Output:** Recent messages with role and content preview

### Runtime Commands

#### /run
- **Description:** Execute prompt with SwarmGraph runner
- **Usage:** `/run <prompt>`
- **Arguments:** `prompt` (required) - the prompt to execute
- **Gates:** Requires `ARC_ALLOW_RUN=1` or session `allow_run=true`
- **Modes:** Available in `build` and `auto` modes
- **Output:** Run result with status, tasks, cost, and output
- **Notes:** Supports cancellation with Ctrl+C

#### /runtime (alias: /mode)
- **Description:** Show or set runtime mode
- **Usage:** 
  - `/runtime` - show current runtime mode
  - `/runtime <mode>` - set runtime mode
- **Arguments:** `mode` (optional) - one of: `fake`, `gated_local`, `provider_backed`
- **Output:** Current runtime mode, profile, isolation, and cost source

#### /tools
- **Description:** Manage session tools
- **Usage:**
  - `/tools list` - list available tools
  - `/tools enable [tool ...]` - enable tools
  - `/tools disable [tool ...]` - disable tools
- **Output:** Tool status and availability

#### /plan
- **Description:** Switch to Plan mode (read-only)
- **Usage:** `/plan`
- **Output:** "Switched to Plan mode (read-only)."

#### /build
- **Description:** Switch to Build mode (can write)
- **Usage:** `/build`
- **Output:** "Switched to Build mode (can write)."

#### /auto
- **Description:** Switch to policy-driven mode
- **Usage:** `/auto`
- **Output:** "Switched to Auto mode (policy-driven)."

### Workspace Commands

#### /status
- **Description:** Show workspace, runtime, and session status
- **Usage:** `/status`
- **Output:** Workspace path, mode, runtime, session ID, message count, stored runs

#### /doctor
- **Description:** Run environment diagnostics
- **Usage:** `/doctor`
- **Output:** Workspace and ARC directory existence checks

#### /runs
- **Description:** List recent run records
- **Usage:** `/runs`
- **Output:** List of up to 10 most recent run files with size and timestamp

## Findings

### ✅ Strengths

1. **Complete help text** - All 19 commands have help text in the registry
2. **Centralized registry** - Commands are defined in a single, declarative registry
3. **Rich metadata** - Each command has category, gates, modes, trust requirements
4. **Aliases supported** - `/quit` → `/exit`, `/mode` → `/runtime`
5. **Consistent structure** - All commands follow the same CommandDef pattern
6. **Global help** - `/help` command shows all commands with descriptions

### ❌ Gaps Identified

1. **No individual `--help` flags** - Commands don't support `/command --help` syntax
   - Example: `/run --help` doesn't show help for the run command
   - Instead, it would try to execute with "--help" as the prompt
   - **Impact:** Users can't get help for individual commands without using `/help`

2. **No usage examples** - Help text is one-line descriptions without examples
   - Example: `/tools` help doesn't show the subcommands (list/enable/disable)
   - **Impact:** Users need to guess command syntax

3. **No argument documentation** - Commands with arguments don't document them
   - Example: `/history` accepts a number but this isn't documented
   - Example: `/runtime` accepts mode values but doesn't list them in help
   - **Impact:** Users need to try commands to discover arguments

### 💡 Recommendations

1. **Implement `--help` flag support** - Add logic to check for `--help` in command handlers
   ```python
   def cmd_run(arg: str, session: ChatSession) -> str:
       if arg.strip() in ("--help", "-h"):
           return "Usage: /run <prompt>\n\nExecute a prompt with the SwarmGraph runner..."
       # ... rest of implementation
   ```

2. **Add usage examples to help text** - Extend CommandDef with an `examples` field
   ```python
   examples=[
       "/run What is the capital of France?",
       "/run --help"
   ]
   ```

3. **Document arguments** - Add an `arguments` field to CommandDef
   ```python
   arguments=[
       ("prompt", "required", "The prompt to execute"),
       ("--help", "optional", "Show this help message")
   ]
   ```

4. **Enhanced help command** - Add `/help <command>` to show detailed help for one command
   ```python
   def cmd_help(arg: str, session: ChatSession) -> str:
       if arg:
           # Show detailed help for specific command
           cmd = registry.get(arg)
           if cmd:
               return f"/{cmd.name}: {cmd.help_text}\n\nUsage: ..."
       # Show all commands
       return registry.help_text()
   ```

## Acceptance Criteria

✅ **Inventory of all slash commands** - Complete (19 commands documented)  
❌ **Every slash command has `/command --help` equivalent** - Not implemented  
📝 **Logged gaps** - Gap documented in this report

## Gap Summary

**Gap:** Individual slash commands don't support `--help` flags.

**Current behavior:**
```bash
/run --help
# Tries to execute with "--help" as the prompt
```

**Expected behavior:**
```bash
/run --help
# Shows: Usage: /run <prompt>
#        Execute a prompt with the SwarmGraph runner.
#        Examples:
#          /run What is the capital of France?
```

**Workaround:** Use `/help` to see all commands, but this doesn't show detailed usage for individual commands.

**Recommendation:** Implement `--help` flag support in Phase 1 Task B.2 completion.

## Implementation Plan for `--help` Support

### Option 1: Add to each handler (simple)
```python
def cmd_run(arg: str, session: ChatSession) -> str:
    if arg.strip() in ("--help", "-h"):
        return """Usage: /run <prompt>

Execute a prompt with the SwarmGraph runner.

Arguments:
  prompt    The prompt to execute (required)

Examples:
  /run What is the capital of France?
  /run Explain quantum computing

Gates:
  Requires ARC_ALLOW_RUN=1 or session allow_run=true

Modes:
  Available in: build, auto
"""
    # ... rest of implementation
```

### Option 2: Add to CommandDef (declarative)
```python
@dataclass
class CommandDef:
    name: str
    help_text: str
    category: str
    handler: Callable[..., str | None]
    # New fields:
    usage: str = ""  # e.g., "/run <prompt>"
    arguments: list[tuple[str, str, str]] = field(default_factory=list)  # (name, required/optional, description)
    examples: list[str] = field(default_factory=list)
    # ... existing fields
```

### Option 3: Wrapper function (automatic)
```python
def with_help_support(handler: Callable) -> Callable:
    """Decorator that adds --help support to command handlers."""
    def wrapper(arg: str, session: ChatSession) -> str:
        if arg.strip() in ("--help", "-h"):
            cmd = registry.get(handler.__name__.replace("cmd_", ""))
            return cmd.detailed_help() if cmd else "No help available."
        return handler(arg, session)
    return wrapper

@with_help_support
def cmd_run(arg: str, session: ChatSession) -> str:
    # ... implementation
```

**Recommended:** Option 2 (declarative) - extends the existing CommandDef structure and keeps help text centralized.

## Next Steps

1. ✅ Slash command inventory complete
2. ❌ Implement `--help` flag support (deferred to v0.2)
3. 📝 Document gap as GitHub issue
4. 📝 Move to next Phase 1 task

## Verification Commands

```bash
# Launch chat REPL
cd python && uv run arc studio chat

# Test commands
/help
/version
/status
/run --help  # Currently doesn't work as expected
```

---

**Audit completed:** 2026-05-22  
**Phase 1 Task B.2:** ⚠️ PARTIAL - Help text exists but `--help` flags not implemented
