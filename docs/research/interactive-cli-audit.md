# ARC Studio Interactive CLI/UX Audit

**Created:** 2026-05-26
**Scope:** All interactive CLI surfaces, REPL, IDE integration, and UX gaps

---

## Reality Refresh — 2026-05-26

This audit is intentionally preserved as the original gap analysis, but parts of it are now stale after the Phase 41 implementation slices on `feat/sandbox-lima-execution-docker-hardening-fuzzing`.

Current verified implementation status:
- 41.1 command palette: implemented locally. `/help` renders grouped sections for session, run, sandbox, policy, workspace, providers, tools, audit, tasks, and MCP, with deferred groups labeled honestly.
- 41.2 shared adapters: implemented for the P0 REPL commands and read/search. The REPL uses in-process adapter helpers for `/sandbox doctor`, `/sandbox run`, `/policy explain/list/show`, `/runs list/show/status`, `/doctor`, `/status`, `/read`, and `/search` rather than broad Typer shell-out wrappers.
- 41.3 sandbox approval/policy UX: subprocess sandbox policy path and allowed/denied audit events are implemented for `/sandbox run -- <cmd...>`; richer reusable interactive approval prompts remain incomplete.
- 41.4 progress/error UX: `/run` has a progress sink, progress summary metadata, deterministic progress lines in `arc studio chat`, cancellation metadata, and structured error metadata. Rich/TUI spinner rendering is not implemented.
- 41.5 read/search baseline: `/read` and `/search` are implemented as read-only, workspace-bound, symlink/path-escape guarded, text-only, output-capped REPL commands. `/diff`, `/apply`, and `/test` remain design-only/gated future work.
- 41.6 sessions/IDE bridge: not started.

Current command evidence:
- Code: `python/src/agent_runtime_cockpit/cli_repl/slash_commands.py`, `python/src/agent_runtime_cockpit/cli_repl/adapters.py`, `python/src/agent_runtime_cockpit/cli_repl/chat_repl.py`.
- Tests: `python/tests/test_cli_repl.py`, `python/tests/contract/test_slash_registry_contract.py`.
- Latest local targeted evidence: `cd python && uv run pytest tests/test_cli_repl.py tests/contract/test_slash_registry_contract.py -q` -> `95 passed`; targeted Ruff check on touched CLI files passed.
- Previous broader local evidence for this branch included full Python tests, pnpm lint/typecheck/build/test/test:e2e, and `scripts/check-pr.sh` passing. GitHub Actions did not start because of an external billing/spending-limit blocker, not a code failure.

Claim safety:
- ARC still must not claim OpenCode/Claude Code parity.
- Public microVM execution remains blocked by ADR-024 prerequisites; Lima remains a low-security developer harness and Firecracker remains proof/preflight-only unless real-host proof is later landed.
- Container sandbox remains gated and must not be described as default sandbox execution.

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

### Why Slash Commands Are Not Yet First-Class

The `/` command system exists only inside `arc studio chat`, not inside the full ARC CLI surface. The root CLI is a Typer command tree (`arc sandbox ...`, `arc policy ...`, `arc runs ...`), while the interactive shell uses a separate in-process registry in `cli_repl/slash_commands.py`. There is no adapter layer that maps Typer command groups into REPL slash commands, so most mature CLI features are invisible once the user enters the interactive shell.

Root cause:
- The REPL started as a SwarmGraph chat shim, not as the canonical ARC agent shell.
- Slash commands are manually registered in `_build_registry()`; they are not generated from, or backed by, the Typer command modules.
- Existing CLI command functions often write directly through Typer/Rich output helpers and raise `typer.Exit`, making direct REPL reuse awkward.
- No shared `CommandResult`/renderer contract exists for both Typer and REPL paths.
- Approval UX lives in batch CLI flags (`--ask`, approval tokens, Typer confirm), not a reusable interactive approval service.
- Progress events are emitted by runtime paths but the REPL stores them in `SlashCommandHandler.events` without live rendering.

Consequence: ARC has many CLI capabilities, but the interactive shell exposes only a thin subset. This is why it does not yet feel like OpenCode or Claude Code.

### What Works Well

1. **CLI decomposition is excellent** - 4225-line monolith → 15 command modules, all <500 lines
2. **Sandbox subprocess foundation is production-ready for bounded local CLI execution** - subprocess provider has env filtering, path guards, bounded output, and audit events; public microVM execution remains blocked and container fallback remains gated
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

## OpenCode / Claude Code Parity Gap

| Area | Current ARC behavior | OpenCode/Claude Code expectation | Missing | Severity | Proposed fix | Files affected |
|------|----------------------|----------------------------------|---------|----------|--------------|----------------|
| Canonical interactive shell | `arc studio chat` exists, but plain `arc` only launches it in TTY and docs do not frame it as canonical | One obvious agent shell that owns chat, tools, approvals, shell, files, diffs, status | Product framing + complete command surface | P0 | Make `arc studio chat` the canonical interactive UX; document `ARC_NO_TUI` fallback | `cli/_app.py`, `cli_repl/chat_repl.py`, docs |
| Slash command coverage | 17 manual slash commands | Slash command palette covers core product actions | Missing `/sandbox`, `/policy`, `/audit`, `/task`, `/providers`, `/mcp`, `/hitl`, `/replay`, `/battle` | P0 | Add slash wrappers over shared service functions | `cli_repl/slash_commands.py`, `cli_repl/commands/__init__.py`, `cli/*.py` |
| Shell/sandbox approval | `arc sandbox run --ask` batch-only | Interactive approval modal/prompt for shell/network/install/write actions | Reusable approval service | P0 | Extract sandbox approval/rendering helpers, wire `/sandbox run` | `security/sandbox.py`, `cli/sandbox.py`, `cli_repl/slash_commands.py` |
| Agent edit loop | No REPL diff/apply/test loop | Read files, propose patch, show diff, approve, apply, run tests | Agent workflow loop | P0/P1 | Design `/read`, `/edit`, `/diff`, `/apply`, `/test` with sandbox gates | new command/service modules |
| Progress rendering | Events are captured but not rendered live | Streaming progress, tool calls, cost, status | Live event renderer | P1 | Render `run.started`, `run.progress.*`, `run.completed`, errors | `cli_repl/slash_commands.py`, `chat_repl.py` |
| Context/file selection | Context commands exist top-level only | Interactive file/context commands in shell | `/context`, `/files`, `/read` | P1 | Add read-only context slash commands first | `cli/context.py`, `tools/`, `cli_repl/` |
| Provider/model switching | `/runtime`; no `/model`; providers top-level only | `/model`, `/provider`, live status, budget warnings | Model/provider command layer | P1 | Wrap provider catalog/status/model commands | `cli/providers.py`, `cli_repl/` |
| Tool/MCP discovery | `/tools` only for local tools; MCP top-level only | `/tools`, `/mcp`, trust-gated local control plane status | MCP/tool status inside shell | P1 | Add `/mcp status`, `/mcp serve` docs/warnings, tool list details | `cli/mcp.py`, `mcp/server.py`, `cli_repl/` |
| Task/todo workflow | `arc task ...` top-level; no `/todo` | Visible task/todo list and progress | `/task`, `/todo` | P1 | Add `/task list/status/cancel`; decide if `/todo` maps to task registry | `cli/task.py`, `tasks/`, `cli_repl/` |
| Error recovery | REPL loop can surface exceptions poorly | Shell survives command failures | Per-command exception boundary | P1 | Wrap `handler.handle()` and render structured errors | `cli_repl/chat_repl.py` |
| Session resume/search | Sessions persist, but limited search/resume UX | Resume named sessions, searchable history | Better session UX | P2 | `/sessions resume`, `/search`, global history | `cli_repl/session.py`, `chat_repl.py` |
| Dashboard/TUI | None | Optional status dashboard | Terminal dashboard | P3 | Defer until command layer stable | new `cli/dashboard.py` if justified |

## Typer Command To Slash Command Mapping

| Typer command group | Current REPL slash status | Recommended slash status | Notes |
|---------------------|---------------------------|---------------------------|-------|
| `arc sandbox doctor` | Missing | `/sandbox doctor` | P0; read-only diagnostic |
| `arc sandbox run` | Missing | `/sandbox run -- <cmd>` | P0; requires approval UX |
| `arc sandbox audit-list` | Missing | `/sandbox audit-list` or `/audit sandbox` | P1 |
| `arc policy explain` | Missing | `/policy explain -- <cmd>` | P0; safe read-only |
| `arc policy list/show` | Missing | `/policy list`, `/policy show <name>` | P1 |
| `arc audit verify` | Missing | `/audit verify <run-id>` | P1 |
| `arc runs` | Partial: `/runs` only lists trace files | `/runs list`, `/runs show <id>`, `/runs trace <id>` | P0/P1; use real run store |
| `arc task` | Missing | `/task list`, `/task status <id>`, `/task cancel <id>` | P1 |
| `arc providers` | Missing | `/providers status`, `/provider`, `/model` | P1 |
| `arc doctor` | Partial: local checks only | `/doctor`, `/doctor all`, `/doctor sandbox` | P0 |
| `arc mcp` | Missing | `/mcp status`, `/mcp serve --stdio` docs/gate | P2; server start may remain top-level |
| `arc hitl` | Missing | `/hitl pending`, `/hitl respond` | P1; approval workflow |
| `arc replay` | Missing | `/replay <run-id>` | P2 |
| `arc battle` | Missing | `/battle list`, `/battle show <id>` | P2; run stays gated |
| `arc events watch` | Missing | `/events watch` | P2; needs async stream handling |
| `arc workspace` | Missing | `/workspace trust/status` | P1; trust-sensitive |
| `arc config` | Missing | `/config show`, `/config validate` | P2 |
| `arc context` | Missing | `/context pack`, `/read` | P1; key for agent UX |
| `arc mcp serve`, daemon `serve` | Missing | Mostly top-level only | Long-running server commands should not block REPL unless task-backed |

## Recommended Slash Command Inventory

P0 interactive shell commands:
- `/help`
- `/status`
- `/doctor [all|sandbox|providers]`
- `/run <prompt>`
- `/sandbox doctor`
- `/sandbox run -- <cmd...>`
- `/policy explain -- <cmd...>`
- `/runs list`
- `/runs show <id>`

P1 command expansion:
- `/audit verify <run-id>`
- `/audit list`
- `/task list`
- `/task status <id>`
- `/providers status`
- `/provider [id]`
- `/model [id]`
- `/tools list|enable|disable`
- `/mcp status`
- `/hitl pending`
- `/hitl respond <id>`
- `/context pack`

P2 agent workflow commands:
- `/read <path>`
- `/search <pattern>`
- `/diff`
- `/apply`
- `/test [cmd]`
- `/replay <run-id>`
- `/battle list|show`
- `/events watch`

P3 power-user commands:
- `/alias`
- `/dashboard`
- `/batch`
- `/pipeline`

## Direct Answer: Why Aren't The `/` Commands Inside The CLI?

They are inside one CLI mode only: `arc studio chat`. They are not inside the root Typer CLI because ARC currently has two parallel command systems. The top-level Typer commands are mature and broad; the REPL slash registry is manual and narrow. There is no shared command adapter contract, so adding a Typer command does not automatically make it available as a slash command. To reach OpenCode/Claude Code style UX, ARC needs to promote the REPL into the canonical agent shell and expose high-value Typer capabilities through slash command adapters with shared rendering, approval, progress, and error handling.

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

---

## Current Plan Audit Prompt

Use this prompt to audit implementation against the current CLI/UX plan after new Phase 41 or Phase 42 work lands:

```text
You are a senior ARC Studio CLI/UX auditor. Audit the current branch against the locked plan in docs/roadmap.md, docs/phases.md, docs/research/interactive-cli-audit.md, and docs/research/parallel-cli-sessions-plan.md.

Rules:
- Do not edit files.
- Do not infer completion from docs alone; verify code and tests.
- Do not claim OpenCode/Claude Code parity unless all listed UX capabilities are implemented and tested.
- Do not claim public microVM execution unless ADR-024 P1-P7 prerequisites are proven and tests show real microVM command execution.
- Treat GitHub Actions billing/spending-limit failures as external CI blockers, not code validation.
- Preserve unrelated dirty worktree changes in your report.

Audit scope:
1. Read current git branch, HEAD, status, recent commits, and untracked files.
2. Compare Phase 41 implementation against docs/phases.md chunks 41.1 through 41.6:
   - 41.1 Slash Command Palette
   - 41.2 Shared Command Adapters
   - 41.3 Approval UX
   - 41.4 Progress, Cancellation, Error UX
   - 41.5 Read/Search/Diff/Apply/Test Design
   - 41.6 History, Sessions, IDE Bridge
3. Compare Phase 42 implementation against docs/phases.md deliverables:
   - pipelines
   - dashboard
   - aliases/snippets
   - batch mode
   - session export/import
   - IDE daemon connection
4. Inspect these files at minimum:
   - python/src/agent_runtime_cockpit/cli_repl/slash_commands.py
   - python/src/agent_runtime_cockpit/cli_repl/adapters.py
   - python/src/agent_runtime_cockpit/cli_repl/chat_repl.py
   - python/src/agent_runtime_cockpit/cli_repl/session.py
   - python/src/agent_runtime_cockpit/security/sandbox.py
   - python/src/agent_runtime_cockpit/isolation/microvm.py
   - python/tests/test_cli_repl.py
   - python/tests/contract/test_slash_registry_contract.py
   - python/tests/test_cli_sandbox.py
5. Verify whether these commands exist and are tested:
   - /help grouped command palette
   - /sandbox doctor
   - /sandbox run -- <cmd...>
   - /policy explain -- <cmd...>
   - /runs list
   - /runs show <id>
   - /doctor
   - /status
   - /read <path>
   - /search <pattern>
6. Verify whether these remain deferred/design-only and are documented honestly:
   - /diff
   - /apply
   - /test
   - public microVM execution
   - container sandbox unless ARC_ENABLE_CONTAINER_SANDBOX=1
7. Run or report the latest available evidence for:
   - cd python && uv run ruff check src tests
   - cd python && uv run pytest tests/test_cli_repl.py tests/contract/test_slash_registry_contract.py -q
   - cd python && uv run pytest tests/test_cli_sandbox.py -q
   - cd python && uv run pytest -q
   - pnpm lint
   - pnpm typecheck
   - pnpm build
   - pnpm test
   - pnpm test:e2e
   - bash scripts/check-pr.sh
   If a command is not run, state why.

Return a concise audit report with:

Summary
- Branch:
- HEAD:
- Overall status:
- Highest-priority incomplete item:

Phase 41 Matrix
- 41.1: status, evidence, gaps
- 41.2: status, evidence, gaps
- 41.3: status, evidence, gaps
- 41.4: status, evidence, gaps
- 41.5: status, evidence, gaps
- 41.6: status, evidence, gaps

Phase 42 Matrix
- 42.1 pipelines: status, evidence, gaps
- 42.2 dashboard: status, evidence, gaps
- 42.3 aliases/snippets: status, evidence, gaps
- 42.4 batch mode: status, evidence, gaps
- 42.5 session export/import + IDE connection: status, evidence, gaps

Validation Evidence
- lint:
- typecheck:
- tests:
- E2E:
- build:
- CI:

Truth/Claim Safety
- What is real:
- What is design-only:
- What is blocked:
- Any overclaims in docs:

Recommended Next Work
- Next phase/chunk:
- Files likely touched:
- Tests required:
- Risks:
```
