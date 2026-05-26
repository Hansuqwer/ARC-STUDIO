# Interactive CLI Phase 42 Notes

## Scope

Implemented as P0 foundations for Phase 42.1–42.5 CLI UX. IDE write sharing remains deferred.

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

Pipe contract:
- Pipe transport is quoted argv append, not OS stdin and not shell pipe.
- Allowed pipe targets are read-only/text commands: `/search`, `/read`, `/status`, `/history`.
- Mutating or security-sensitive targets such as `/sandbox`, `/run`, `/alias`, and unknown adapters are blocked.

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
- `/alias --user ...`
- `/alias --workspace ...`

Persistence:
- User: `~/.arc/aliases.json` or `ARC_STUDIO_ALIASES_FILE` override.
- Workspace: `<workspace>/.arc/aliases.json`.
- Workspace aliases take precedence over user aliases.
- Alias writes use same-directory temp files and atomic replace.

Safety:
- Expansion is printed before execution.
- Expanded command is reparsed through normal REPL handling.
- Dangerous expanded sandbox commands still hit the existing policy/sandbox path.
- Recursive expansion is bounded.

## Phase 42.4 Batch Mode

Commands:
- `arc batch plan <file> --policy local-safe [--json]`
- `arc batch run <file> --policy local-safe [--continue-on-error] [--json]`

Behavior:
- Parses each non-empty, non-comment line through `parse_command_chain()`.
- Does not invoke a shell.
- Raw non-slash commands are denied; use `/sandbox run -- <argv>` for command execution.
- Alias expansion is resolved into the plan before execution.
- Sandbox segments are classified and decided before execution.
- Default mode is fail-fast; `--continue-on-error` records failures and proceeds.
- Results preserve command ordering, state, output, reason, and JSON shape.

## Phase 42.5 Session Bundles

Commands:
- `arc studio sessions show <id> [--json]`
- `arc studio sessions export <id> --output <path> [--json]`
- `arc studio sessions import <path> [--new-id] [--overwrite] [--json]`

Bundle schema:
- `schema: arc.session.bundle`
- `schema_version: 1`
- `session_schema_version: 4`
- redacted session payload
- SHA-256 integrity over canonical redacted session payload

Safety:
- Imports validate schema/version/integrity before writing.
- Future session schema versions are rejected.
- Unsafe IDs and secret-looking payloads are rejected.
- Session writes use atomic replace.

## Non-Goals

- No public microVM execution.
- No broader sandbox permissions.
- No IDE daemon, remote sync, shared server, or multi-tenant collaboration.
