# Slash Command Help Audit (Phase 1, B.2)

**Date:** 2026-05-22  
**Auditor:** Automated audit via `cli_repl/slash_commands.py` inspection  
**Scope:** All slash commands in ARC Studio CLI REPL

---

## Summary

**Total commands:** 17  
**Commands with help text:** 17/17 (100%)  
**Global `/help` command:** ✅ Implemented and working  
**Per-command `--help` support:** ❌ Not implemented

---

## Command Inventory

### Meta Commands (3)
| Command | Aliases | Help Text | Category |
|---------|---------|-----------|----------|
| `/exit` | `/quit` | Save session and exit | meta |
| `/help` | — | Show this help message | meta |
| `/version` | — | Show version info | meta |

### Runtime Commands (7)
| Command | Aliases | Help Text | Category |
|---------|---------|-----------|----------|
| `/auto` | — | Switch to policy-driven mode | runtime |
| `/build` | — | Switch to Build mode (can write) | runtime |
| `/mode` | — | Alias for /runtime | runtime |
| `/plan` | — | Switch to Plan mode (read-only) | runtime |
| `/run` | — | Execute prompt with SwarmGraph runner | runtime |
| `/runtime` | — | Show or set runtime mode: fake, gated_local, provider_backed | runtime |
| `/tools` | — | Manage session tools: /tools list\|enable\|disable | runtime |

### Session Commands (4)
| Command | Aliases | Help Text | Category |
|---------|---------|-----------|----------|
| `/clear` | — | Clear session history | session |
| `/history` | — | Show recent messages | session |
| `/sessions` | — | List saved sessions | session |
| `/summary` | — | Show session summary | session |

### Workspace Commands (3)
| Command | Aliases | Help Text | Category |
|---------|---------|-----------|----------|
| `/doctor` | — | Run environment diagnostics | workspace |
| `/runs` | — | List recent run records | workspace |
| `/status` | — | Show workspace, runtime, and session status | workspace |

---

## Help System Coverage

### ✅ Implemented
1. **Global help command:** `/help` displays all commands grouped by category with one-line summaries
2. **Command registration:** All 17 commands registered in `CommandRegistry` with `help_text` field
3. **Help text quality:** All help texts are concise, descriptive, and follow consistent format
4. **Category grouping:** Commands organized into 4 logical categories (meta, runtime, session, workspace)
5. **Alias documentation:** Aliases shown in help output (e.g., `/exit (/quit)`)

### ❌ Gaps Identified

#### Gap 1: No per-command detailed help
**Severity:** Medium  
**Description:** Individual commands do not support a `--help` argument for detailed help.

**Current behavior:**
```bash
/run --help
# Treats "--help" as the prompt argument, not as a help request
```

**Expected behavior (per B.2 acceptance criteria):**
```bash
/run --help
# Should display detailed help for /run command:
# - Full description
# - Argument syntax
# - Examples
# - Related commands
```

**Impact:**
- Users cannot get detailed help for individual commands
- No way to see command-specific examples or argument syntax
- Inconsistent with CLI commands (which all support `--help`)

**Recommendation:**
- Implement `--help` argument handling in command handlers
- Add detailed help text to `CommandDef` (e.g., `detailed_help` field)
- Update command handlers to check for `--help` argument and return detailed help

#### Gap 2: No command usage examples
**Severity:** Low  
**Description:** Help text shows one-line summaries but no usage examples.

**Example:**
```
/tools - Manage session tools: /tools list|enable|disable
```

This shows the subcommands but not actual usage examples like:
```
/tools list              # List all available tools
/tools enable read_file  # Enable the read_file tool
/tools disable *         # Disable all tools
```

**Recommendation:**
- Add `examples` field to `CommandDef`
- Display examples in detailed help (when `--help` is implemented)

#### Gap 3: No searchable help
**Severity:** Low  
**Description:** No way to search help text or filter commands by keyword.

**Recommendation:**
- Add `/help <keyword>` to search/filter commands
- Example: `/help session` shows only session-related commands

---

## Verification

### Test 1: Global help command
```python
from agent_runtime_cockpit.cli_repl.slash_commands import _build_registry, cmd_help
from agent_runtime_cockpit.cli_repl.session import ChatSession

registry = _build_registry()
session = ChatSession()
help_output = cmd_help('', session)

assert len(registry.list_commands()) == 17
assert all(f"/{cmd.name}" in help_output for cmd in registry.list_commands())
```
**Result:** ✅ Pass

### Test 2: All commands have help text
```python
registry = _build_registry()
commands_without_help = [cmd.name for cmd in registry.list_commands() if not cmd.help_text]

assert len(commands_without_help) == 0
```
**Result:** ✅ Pass (all 17 commands have help text)

### Test 3: Per-command --help support
```python
# Check if any command handler checks for --help argument
import inspect
from agent_runtime_cockpit.cli_repl import slash_commands

handlers = [
    slash_commands.cmd_run,
    slash_commands.cmd_status,
    slash_commands.cmd_tools,
    # ... etc
]

for handler in handlers:
    source = inspect.getsource(handler)
    has_help_check = '--help' in source or 'help' in source.lower()
    # Result: No handlers check for --help argument
```
**Result:** ❌ Fail (no `--help` support in any command handler)

---

## Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Every slash command has help text | ✅ Pass | 17/17 commands have `help_text` field |
| `/help` command works | ✅ Pass | Displays all commands with summaries |
| `/command --help` equivalent exists | ❌ Fail | No per-command detailed help |
| Gaps logged | ✅ Pass | This document + GitHub issues (pending) |

**Overall:** Partial pass. Global help works, but per-command detailed help not implemented.

---

## Next Steps

1. **Create GitHub issues for gaps:**
   - Issue: "Implement per-command --help support for slash commands"
   - Issue: "Add usage examples to slash command help"
   - Issue: "Add searchable/filterable help for slash commands"

2. **Implementation priority:**
   - High: Per-command `--help` support (Gap 1)
   - Medium: Usage examples (Gap 2)
   - Low: Searchable help (Gap 3)

3. **Estimated effort:**
   - Gap 1: 3-4 hours (add detailed help infrastructure + update all handlers)
   - Gap 2: 2 hours (add examples to all commands)
   - Gap 3: 1 hour (add search/filter to `/help` command)

---

## Related Tasks

- **B.1:** CLI help text audit (completed) - all CLI commands support `--help`
- **B.6:** Reference docs for slash commands (pending) - should include detailed help for each command
- **B.8:** CLI help text fill (pending) - should include slash command help gaps

---

## Audit Script

For future audits, use:

```python
#!/usr/bin/env python3
"""Slash command help audit script."""
from agent_runtime_cockpit.cli_repl.slash_commands import _build_registry

registry = _build_registry()
commands = registry.list_commands()

print(f"Total commands: {len(commands)}")
print(f"Commands with help text: {sum(1 for c in commands if c.help_text)}/{len(commands)}")
print(f"Commands with aliases: {sum(1 for c in commands if c.aliases)}")
print(f"Categories: {', '.join(registry.categories())}")

# Check for --help support (would need to test each handler)
print("\nNote: Per-command --help support requires manual testing of each handler.")
```

---

**Audit complete.** See gaps section for follow-up work.
