# Interactive CLI Phase 42 Notes

## Scope

Implemented as P0 foundations for Phase 42.1–42.3.

## Phase 42.1 Pipelines

Parser: `python/src/agent_runtime_cockpit/cli_repl/pipeline.py`

Behavior:
- Parses unquoted `|`, `&&`, and `||` explicitly.
- Does not invoke a shell.
- Preserves quoted operators as literal text.
- Rejects empty segments and unterminated quotes.
- `A && B`: runs B only if A succeeds.
- `A || B`: runs B only if A fails.
- `A | B`: forwards previous text output by appending it as a quoted argument to the next text command.

Limit:
- Piping into slash commands is blocked for P0 because no stable stdin contract exists for arbitrary slash adapters.

## Phase 42.2 Dashboard

Commands:
- `/dashboard`
- `arc dashboard`

Data sources are local only:
- system/status from REPL status adapter
- runs from `.arc/traces`
- sandbox from provider doctor data
- providers from env/status helpers
- MCP from import/trust probe
- tasks from `.arc/tasks.db`
- audit from `.arc/audit`

Missing producers render `absent` or `degraded`. No live data is fabricated.

## Phase 42.3 Aliases/Snippets

Commands:
- `/alias list`
- `/alias show <name>`
- `/alias set <name> <command>`
- `/alias remove <name>`
- `/alias run <name>`

Persistence:
- User: `~/.arc/aliases.json` or `ARC_STUDIO_ALIASES_FILE` override.
- Workspace: `<workspace>/.arc/aliases.json`.
- Workspace aliases take precedence over user aliases.

Safety:
- Expansion is printed before execution.
- Expanded command is reparsed through normal REPL handling.
- Dangerous expanded sandbox commands still hit the existing policy/sandbox path.
- Recursive expansion is bounded.

## Non-Goals

- No batch mode.
- No session export/import.
- No public microVM execution.
- No broader sandbox permissions.
