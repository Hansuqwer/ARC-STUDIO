# CLI Command System Review

## Current ARC Spec

ARC Studio specifies a **chat-first CLI** with flat slash commands, three-tier command visibility (Default / Advanced / Hidden), and an advanced passthrough pattern for power users.

### CLI Entry Point (§7.1-7.2, CLI_IDE_REDESIGN_PLAN §2.2)
- `arc-studio` (or `arc` alias) launches interactive chat REPL by default — no arguments needed
- `arc-studio "query"` launches chat with initial prompt
- `arc-studio run "query"` runs non-interactively (scripting/CI)
- `arc-studio -c` continues last session; `arc-studio -r <session-id>` resumes specific session
- `arc-studio config` opens interactive config; `arc-studio doctor` runs diagnostics
- `arc-studio --version` prints version; `arc-studio --help` shows chat-first help (< 20 lines)

### Slash Commands (§10.4, CLI_IDE_REDESIGN_PLAN §2.4)
Flat namespace, categorized into 5 groups:

| Category | Commands |
|---|---|
| Session | `/clear`, `/compact`, `/resume`, `/exit` |
| Configuration | `/config`, `/providers`, `/runtime`, `/model` |
| Workflow | `/run`, `/stop`, `/diff`, `/tasks`, `/runs`, `/workflows` |
| Mode | `/plan`, `/build`, `/auto` |
| Diagnostic | `/status`, `/doctor`, `/graph`, `/version`, `/update --check`, `/help` |

Total: **20 slash commands** specified for default tier.

### Command Tiers (§10.8)
| Tier | Shown where | Criteria |
|---|---|---|
| **Default** | `/help`, slash autocomplete | Chat-first user needs it in normal workflow; stable UX; no raw implementation detail |
| **Advanced** | `arc-studio advanced ...`, advanced docs | Useful for automation, debugging, migration, power users; may expose raw JSON/traces/adapter internals |
| **Hidden/internal** | Not user-facing | IDE/daemon/test integration only |

### Advanced Passthrough (§10.8)
`arc-studio advanced <any-arc-args...>` is equivalent to `arc <any-arc-args...>` with:
- stdout/stderr/exit codes unchanged
- `ARC_STUDIO_ADVANCED=1` set in child process
- Workspace trust and key redaction still apply
- `--unsafe` requires explicit confirmation, never implied by advanced mode
- Default UI may link to advanced commands, but advanced output is never embedded raw unless redacted

### Version and Update (§10.9)
- `/version` shows CLI version, daemon version, protocol version, runtime manifest version
- `/update --check` checks current package channel and prints the package-manager command; **does not modify installed files**
- npm example: `npm install -g arc-studio@latest`
- pipx example: `pipx upgrade arc-studio`

### Help Text (§10.4)
`/help` shows categorized command list with one-line descriptions. No pagination or search specified.

### What ARC CLI Command System Does NOT Currently Specify
- Command aliases (beyond `arc` → `arc-studio`)
- Fuzzy autocomplete for slash commands
- Shell completions (bash/zsh/fish)
- Non-interactive mode beyond `arc-studio run "query"`
- User-extensible slash commands
- Command argument parsing/validation for slash commands
- Command history (up-arrow recall)
- `/runs` command taxonomy (workflow vs diagnostic)
- Exit codes for slash command failures
- Rate limiting / debouncing for rapid command input
- Command middleware (pre/post hooks)

---

## Comparable Products / Research

| Feature | Claude Code | OpenCode (archived→Crush) | Codex CLI | Aider | GitHub CLI | kubectl | ARC Studio (spec) |
|---|---|---|---|---|---|---|---|
| **Total commands** | ~50 built-in + unlimited skills | ~20 (flat) | ~35 built-in | ~35 in-chat | ~50+ subcommands | ~50+ top-level | 20 slash + 60+ advanced |
| **Max nesting depth** | 1 (flat slash commands) | 1 (flat) | 1 (flat) | 1 (flat) | 3 (`gh api graphql -f query=...`) | 3+ (`kubectl get pods -n ns`) | 1 (slash) / 3 (advanced) |
| **Default behavior** | Chat REPL | Chat TUI | Chat TUI | Chat REPL | `--help` | `--help` | Chat REPL ✅ |
| **Slash commands** | 50+ built-in, user-extensible via skills | 6+ custom via `.md` files | 35+ built-in | 35+ in-chat | N/A (subcommands) | N/A (subcommands) | 20 specified |
| **User-extensible commands** | ✅ Skills (SKILL.md, frontmatter, args, subagents) | ✅ Custom commands via `.md` files in `.opencode/commands/` | ✅ Skills (SKILL.md, config) | ❌ | ❌ | ❌ (plugins only) | ❌ Not specified |
| **Command aliases** | ✅ `/bg`→`/background`, `/new`→`/clear`, `/quit`→`/exit`, `/cost`→`/usage` | ❌ | ✅ `/quit`→`/exit`, `/approvals`→`/permissions`, `/clean`→`/stop` | ❌ | ✅ `gh pr list` aliases | ✅ `kubectl get po` | ❌ Not specified |
| **Fuzzy autocomplete** | ✅ Type `/` + letters to filter | ✅ Command dialog with fuzzy search | ✅ Slash popup with filtering | ✅ Tab completion | ❌ | ❌ (but kubectl has plugins) | ✅ Specified (combobox role) |
| **Shell completions** | ❌ (chat-first, not needed) | ❌ | ❌ | ❌ | ✅ `gh completion -s zsh` | ✅ `kubectl completion zsh` | ❌ Not specified |
| **Non-interactive mode** | ✅ `claude -p "query"` | ✅ `opencode -p "query"` | ✅ `codex` with config | ✅ `aider -m "query"` | ✅ All commands non-interactive | ✅ All commands | ✅ `arc-studio run "query"` |
| **Command arguments** | ✅ `$ARGUMENTS`, `$0`, `$name` substitution in skills | ✅ Named args via `$NAME` placeholders | ✅ Inline args for most commands | ✅ Args for most commands | ✅ Flags and positional args | ✅ Flags and positional args | ❌ Not specified for slash commands |
| **Command categories** | Implicit (grouped in docs by workflow) | ❌ | Implicit (grouped in docs) | Implicit | Explicit (subcommand groups) | Explicit (resource types) | ✅ Explicit (5 categories) |
| **Hidden commands** | ✅ `user-invocable: false` skills | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Hidden/internal tier |
| **Advanced passthrough** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ `arc-studio advanced <cmd>` |
| **Command permissions** | ✅ `allowed-tools` per skill, `Skill(name)` deny rules | ✅ Permission dialog per tool | ✅ Approval presets (Auto, Read Only) | ✅ `--yes-always` | ❌ | ❌ (RBAC server-side) | ✅ Mode system (Plan/Build/Auto) |
| **Help system** | `/help` shows all, `/doctor` for config | `Ctrl+?` help dialog | `/help` shows all, slash popup | `/help` shows all | `gh help <cmd>` | `kubectl help <cmd>`, man pages | `/help` shows categorized list |
| **Version command** | `/release-notes` for changelog | ❌ | ❌ (uses `--version` flag) | `/version` | `gh --version` | `kubectl version` | `/version` + `/update --check` |

### Key Patterns from Competitors

**Claude Code's skills system** is the most sophisticated user-extensible command mechanism:
- Skills are directories with `SKILL.md` (YAML frontmatter + markdown)
- Support named arguments, dynamic context injection (`` !`command` ``), subagent execution
- Can control model, effort level, allowed tools, invocation (user-only, model-only, both)
- Distributed at personal, project, plugin, enterprise, and managed scopes
- Live change detection — adding/editing skills takes effect mid-session
- This is a **major differentiator** that ARC does not currently match

**Codex CLI's slash commands** are tightly integrated with the TUI:
- Commands queue when a task is running (parsed after current turn finishes)
- `/statusline` and `/title` let users configure TUI chrome interactively
- `/keymap` for remapping shortcuts
- `/personality` for communication style
- Many commands have interactive pickers (model, permissions, plugins)

**OpenCode's custom commands** are simpler but effective:
- `.md` files in `.opencode/commands/` become commands
- Named arguments via `$NAME` placeholders
- Project-scoped and user-scoped commands
- Organized in subdirectories for namespacing (`user:git:commit`)

**GitHub CLI and kubectl** represent the traditional subcommand model:
- Both use nested subcommands (not flat)
- Both have shell completion generation
- kubectl has extensive alias support (`po` → `pods`, `svc` → `services`)
- GitHub CLI has 50+ commands across 15+ groups
- Neither is chat-first; both are command-first

---

## Gaps

1. **No user-extensible slash commands.** Claude Code has 50+ built-in plus unlimited user skills. Codex has skills. OpenCode has custom `.md` commands. ARC has 20 fixed commands with no extension mechanism. This is the largest gap.

2. **No command aliases.** Claude Code has `/bg`→`/background`, `/new`→`/clear`, `/quit`→`/exit`. Codex has `/quit`→`/exit`, `/clean`→`/stop`. ARC has none specified beyond `arc`→`arc-studio`.

3. **No shell completions.** GitHub CLI and kubectl both generate completions for bash/zsh/fish. For the non-chat CLI surface (`arc-studio config`, `arc-studio doctor`, `arc-studio run`), completions would improve the scripting experience.

4. **No command argument parsing for slash commands.** Claude Code skills support `$ARGUMENTS`, `$0`, `$name` substitution. Codex commands accept inline arguments. ARC's slash commands are specified without argument syntax (e.g., `/runtime swarmgraph` vs `/runtime` with interactive picker).

5. **No command queueing during active runs.** Codex queues slash commands when a task is running. Claude Code supports `/background` to detach. ARC does not specify what happens when a user types `/config` during an active run.

6. **No command history.** No up-arrow recall, no `/history`, no session command log. All competitors support some form of command recall or session history browsing.

7. **No `/runs` taxonomy decision.** The spec lists `/runs` under "Workflow" category but it reads like a diagnostic command (list run summaries). Should it be workflow (actionable) or diagnostic (informational)?

8. **No exit code specification for slash commands.** `/doctor` specifies exit codes (0 for pass, 2 for fail), but no other slash command has defined exit codes. Critical for non-interactive scripting.

9. **No fuzzy autocomplete specification.** The spec mentions `combobox` role for input autocomplete but does not define fuzzy matching behavior, ranking, or keyboard navigation for slash command suggestions.

10. **No `/update` without `--check`.** The spec only defines `/update --check` (print command, don't modify). No `/update` that actually performs the upgrade. This is intentional for safety but leaves the upgrade flow incomplete.

11. **No command middleware/hooks.** Claude Code has hooks that fire before/after tool events. Codex has lifecycle hooks. ARC has no mechanism for pre/post command hooks (e.g., auto-format after `/diff` approve).

12. **Help text is static.** `/help` shows a fixed categorized list. No search, no filtering, no context-aware suggestions. Claude Code's `/help` is similarly basic, but Claude's skill descriptions provide richer discoverability.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Add command aliases** | Muscle memory varies; `/q` for `/exit`, `/s` for `/status`, `/r` for `/run` reduce typing | v0.1 | Low — pure mapping table | §10.4: Add alias column to help text |
| **Define slash command argument syntax** | `/runtime swarmgraph` should work without interactive picker; `/model claude-sonnet-4-5` needs arg parsing | v0.1 | Low — extend router to parse args | §10.4: Add `[args]` notation to each command |
| **Add fuzzy autocomplete for slash commands** | Users type `/conf` and expect `/config` to match; essential for discoverability | v0.1 | Low — fuzzy match over command names | §9 Input component: Add fuzzy matching spec |
| **Decide `/runs` category** | Currently in "Workflow" but behaves like diagnostic; should be consistent | v0.1 | None — documentation only | §10.4: Move `/runs` to Diagnostic category |
| **Add shell completions for non-chat CLI** | `arc-studio config`, `arc-studio doctor`, `arc-studio run` benefit from tab completion in shell | v0.2 | Low — standard completion generation | CLI_IDE_REDESIGN_PLAN §2.2: Add completions section |
| **Add user-extensible commands (project-scoped)** | Teams need custom workflows (`/deploy`, `/lint-all`, `/run-tests`); Claude Code skills prove this is high-value | v0.2 | Medium — needs file watching, validation, security review | New §10.11: Custom commands spec |
| **Add command queueing during active runs** | User types `/stop` during a run — it should queue, not error or be ignored | v0.1 | Medium — needs message queue in chat loop | §7.2: Add queueing behavior |
| **Add command history (up-arrow recall)** | Standard REPL expectation; all terminal tools support this | v0.1 | Low — readline/prompt_toolkit built-in | §7.2: Add history behavior |
| **Define exit codes for all slash commands** | Non-interactive mode needs reliable exit codes for CI/scripting | v0.1 | Low — enumeration | §10.4: Add exit code table |
| **Add `/history` command** | Browse past sessions, not just resume latest; Claude Code has `/resume` picker | v0.2 | Low — session list already exists | §10.4: Add `/history` to Session category |
| **Add `/update` (without `--check`)** | Users want one-command upgrade; `/update --check` prints the command but doesn't run it | v0.2 | Medium — self-modifying installs are risky | §10.9: Add `/update` with confirmation flow |
| **Add command hooks (pre/post)** | Auto-format after apply, run tests after `/run`, log commands to audit | v0.3 | Medium — needs hook infrastructure | New §10.12: Command hooks spec |
| **Add `/alias` command** | Let users define personal aliases mid-session: `/alias q /exit` | v0.3 | Low — config-backed alias table | §10.4: Add `/alias` to Configuration category |
| **Add context-aware help** | `/help runs` shows `/runs` detail; `/help` during active run shows `/stop` prominently | v0.2 | Low — conditional rendering | §10.4: Add context-aware help behavior |
| **Add `/commands` to list all (including advanced)** | Single entry point to discover everything; distinct from `/help` which shows default only | v0.1 | Low — just a listing | §10.4: Add `/commands` to Diagnostic category |

---

## Recommended Decisions

### 1. Command taxonomy: Keep flat, categorize by user intent
The current 5-category system (Session, Configuration, Workflow, Mode, Diagnostic) is good. Move `/runs` from Workflow to Diagnostic — it lists run summaries, it doesn't execute workflows. `/run` stays in Workflow.

### 2. `/runs` is diagnostic, not workflow
`/runs` shows a table of past runs with status, cost, duration. It does not start, stop, or modify runs. It belongs in Diagnostic alongside `/status` and `/doctor`. The action commands (`/run`, `/stop`) remain in Workflow.

### 3. Yes, `arc-studio run` should exist for non-interactive mode
The spec already defines `arc-studio run "query"` for scripting/CI. This is correct and matches the pattern from Claude Code (`claude -p`), OpenCode (`opencode -p`), and Codex. Keep it. Add exit code specification.

### 4. Slash commands should be user-extensible (v0.2)
Claude Code's skills system is the gold standard. ARC should adopt a simplified version:
- Project-scoped commands in `.arc/commands/<name>.md`
- User-scoped commands in `~/.config/arc-studio/commands/<name>.md`
- Markdown body becomes the prompt sent to the agent
- Named arguments via `$NAME` placeholders (like OpenCode)
- No dynamic shell execution in v0.2 (defer `` !`command` `` injection)
- No subagent execution in v0.2 (defer `context: fork`)
- Commands appear in `/help` with `project:` or `user:` prefix

### 5. Command aliases: Add minimal set for v0.1
Define these aliases in v0.1:
- `/q` → `/exit`
- `/s` → `/status`
- `/h` → `/help`
- `/d` → `/diff`
- `/w` → `/workflows`
- `/c` → `/config`

### 6. Fuzzy autocomplete: Required for v0.1
All competitors have this. Type `/conf` → match `/config`. Type `/ru` → match `/run`, `/runs`. Use simple prefix + substring matching (not full fuzzy) for v0.1.

### 7. Shell completions: v0.2, not v0.1
Shell completions only apply to the non-chat CLI surface (`arc-studio config`, `arc-studio doctor`, `arc-studio run`). Since v0.1 is chat-first, completions are lower priority. Add in v0.2 when the non-chat surface stabilizes.

### 8. Command history: Required for v0.1
Up-arrow recall is table stakes for any REPL. Use prompt_toolkit or readline built-in history. Persist to `~/.local/share/arc-studio/history` (or platform equivalent).

### 9. Command queueing: Required for v0.1
If a user types `/stop` during an active run, it should queue and execute when the current turn completes. If they type `/config`, show a message: "A run is active. `/config` will open after it finishes. Type `/stop` to cancel."

### 10. No `/update` (without `--check`) in v0.1
Self-modifying installs are risky. `/update --check` prints the upgrade command and lets the user run it manually. This is the safest approach for v0.1. Revisit in v0.2.

### 11. Exit codes: Define for v0.1
| Exit code | Meaning |
|---|---|
| 0 | Success |
| 1 | General error (command not found, invalid args) |
| 2 | Diagnostic failure (`/doctor` found blocking issues) |
| 3 | Run failure (non-interactive `arc-studio run` failed) |
| 4 | Permission denied (trust gate, paid call denied) |
| 130 | Interrupted (Ctrl+C) |

---

## Specific Spec Edits

### §10.4 Help Text
- Add alias column: show `/q` next to `/exit`, `/s` next to `/status`, etc.
- Add `[args]` notation: `/runtime [id]`, `/model [id]`, `/run [workflow]`, `/doctor [check]`
- Move `/runs` from "Workflow" to "Diagnostic" category
- Add `/commands` to Diagnostic: "list all commands including advanced"
- Add `/history` to Session category (v0.2 reservation)
- Add exit code note at bottom: "Exit codes: 0 success, 1 error, 2 diagnostic fail, 3 run fail, 4 denied, 130 interrupted"

### §10.8 Command Tiers
- Add explicit criteria for when a command graduates from Advanced to Default
- Add note: "Custom commands (v0.2) appear in Default tier with `project:` or `user:` prefix"
- Clarify that `arc-studio advanced` does NOT enter a subshell; it's a one-shot passthrough

### §10.9 Version And Update
- Add: "`/update` without `--check` is reserved for v0.2. In v0.1, `/update` shows the same output as `/update --check` with an additional note: 'To upgrade, run the command above.'"
- Add daemon version mismatch behavior: "If daemon version differs from CLI, `/version` shows a warning and suggests `arc-studio serve --restart`."

### §7.2 Steady-State Chat
- Add command queueing: "If a run is active, slash commands that don't affect the run (`/config`, `/providers`, `/runtime`) are queued. Commands that affect the run (`/stop`, `/plan`) execute immediately. Queued commands show a pending indicator in the status line."
- Add command history: "Up-arrow recalls previous inputs. History persists to platform session directory. `/clear` does not clear input history."
- Add fuzzy autocomplete: "Typing `/` opens autocomplete popup. Filtering uses prefix + substring matching. Arrow keys navigate, Enter selects, Esc dismisses."

### §9 Input Component
- Add fuzzy matching spec: "Autocomplete uses prefix match first, then substring match. Results sorted by category order (Session > Configuration > Workflow > Mode > Diagnostic), then alphabetically. Custom commands sorted after built-in."
- Add argument hints: "When a command expects arguments, autocomplete shows a hint: `/runtime [swarmgraph, langgraph, crewai]`"

### CLI_IDE_REDESIGN_PLAN §2.4 Slash Command List
- Add argument column showing expected args for each command
- Add alias column
- Add exit code column
- Add `/commands` to the table
- Reserve `/history` for v0.2

### New §10.11 Custom Commands (v0.2 reservation)
Add a new section reserving the custom command mechanism:
- Location: `.arc/commands/<name>.md` (project) and `~/.config/arc-studio/commands/<name>.md` (user)
- Format: Markdown file, first line becomes description
- Invocation: `/<name>` or `/project:<name>` or `/user:<name>`
- Arguments: `$NAME` placeholders replaced with user input
- Security: Project commands require workspace trust; user commands always available
- Live detection: New commands detected on next `/` press (file watching not required for v0.2)

---

## Acceptance Criteria

### v0.1
- [ ] `arc-studio` launches chat REPL with no arguments
- [ ] `arc-studio "query"` launches chat with initial prompt
- [ ] `arc-studio run "query"` runs non-interactively and exits with correct exit code
- [ ] `arc-studio -c` resumes last session
- [ ] `arc-studio --version` prints CLI, daemon, protocol, manifest versions
- [ ] `arc-studio --help` shows < 20 lines of chat-first help
- [ ] All 20 slash commands work in interactive chat
- [ ] `/help` shows categorized command list with aliases
- [ ] `/version` shows version info inline in chat
- [ ] `/update --check` prints upgrade command without modifying files
- [ ] Slash commands accept arguments (e.g., `/runtime swarmgraph`)
- [ ] Fuzzy autocomplete works for slash commands (type `/conf` → match `/config`)
- [ ] Command aliases work (`/q` → `/exit`, `/s` → `/status`)
- [ ] Up-arrow recalls previous inputs (command history)
- [ ] Commands queue during active runs (`/config` waits, `/stop` executes immediately)
- [ ] `arc-studio advanced <cmd>` passes through to Python CLI with `ARC_STUDIO_ADVANCED=1`
- [ ] Exit codes: 0 (success), 1 (error), 2 (diagnostic fail), 3 (run fail), 4 (denied), 130 (interrupted)
- [ ] `/runs` appears in Diagnostic category in `/help`
- [ ] Redaction applies to all command output (keys, tokens, secrets never shown)

### v0.2
- [ ] Shell completions generated for bash/zsh/fish (`arc-studio completion -s zsh`)
- [ ] User-extensible commands via `.arc/commands/<name>.md`
- [ ] Project-scoped and user-scoped custom commands
- [ ] Custom commands support `$NAME` argument substitution
- [ ] `/history` command browses past sessions
- [ ] Context-aware help (`/help runs` shows detail, `/help` during run highlights `/stop`)
- [ ] `/commands` lists all commands including advanced

### v0.3
- [ ] Command hooks (pre/post middleware for slash commands)
- [ ] `/alias` command for user-defined aliases
- [ ] `/update` performs upgrade with confirmation
- [ ] Advanced command output embeddable in chat (redacted)

---

## Reject / Do Not Build

| Idea | Why rejected |
|---|---|
| **Subcommand nesting for slash commands** (`/run start`, `/run stop`, `/run list`) | All competitors use flat namespaces. Nesting adds cognitive overhead and breaks the muscle-memory pattern users expect from Claude Code, Codex, and Aider. Keep `/run`, `/stop`, `/runs` as separate flat commands. |
| **Interactive subshell for advanced mode** (`arc-studio advanced` enters a sub-prompt) | The spec correctly defines `arc-studio advanced <cmd>` as one-shot passthrough. A subshell would confuse the chat-first default and require separate state management. |
| **`/update` that self-modifies in v0.1** | Self-modifying installs are risky across npm/pipx/brew. `/update --check` printing the command is safer. Revisit when distribution is stable. |
| **Command marketplace / plugin registry** | Premature. No plugin loading mechanism exists (IMPLEMENTATION_PLAN §Do Not Build). Skills/commands should be file-based first, registry later. |
| **Natural language command parsing** ("run the workflow" → auto-detect `/run`) | The chat loop already handles natural language. Slash commands are for explicit control. Mixing them creates ambiguity: does "run the tests" mean `/run` or a shell command? |
| **Slash command permissions per command** | Overkill for v0.1. The mode system (Plan/Build/Auto) already gates writes and paid calls. Per-command permissions add complexity without clear use cases. Claude Code's `allowed-tools` is per-skill, not per-built-in-command. |
| **Man pages for CLI** | Chat-first tools don't need man pages. `--help` and `/help` are sufficient. GitHub CLI and kubectl have man pages because they're command-first; ARC is chat-first. |
| **Command recording/replay** | Interesting for debugging but premature. Session transcript already captures user input. Command replay would need deterministic environment guarantees that don't exist yet. |
| **Multi-command chaining** (`/run && /diff`) | Shell-like chaining in chat is confusing. Users can type natural language: "run the workflow then show me the diff." The agent handles sequencing. |
| **`/trace` command in v0.1 default** | Explicitly out of scope per §0.5. Advanced trace access via `arc-studio advanced runs trace <id>` is sufficient. Trace UI returns in v0.3 audit explorer. |
