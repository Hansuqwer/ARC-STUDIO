# Research: Interactive CLI UX for `arc`

Status: research-first gate for the Rich-based interactive shell.
Scope: inform a Claude Code / opencode / Kiro-*inspired* shell (not parity) that
preserves ARC safety defaults (offline/fake default, provider-backed gated).

Each note: source · link/path · learned · implementation consequence · confidence ·
unresolved.

## 1. External UX references

### opencode CLI / TUI
- Source: opencode docs — CLI & Permissions.
- Link: https://docs.opencode.ai/docs/cli/ , https://opencode.ai/docs/permissions
- Learned: Interactive TUI + non-interactive CLI mode. Granular permission engine
  (per category: bash, read, edit, glob, grep, webfetch, websearch, ...) where each
  action is `allow | prompt | deny`. Slash commands inside the TUI; session list/fork;
  status/model/cost display.
- Consequence: ARC already has an equivalent decision model (`security/sandbox.decide`
  -> read_only/network/install/destructive/privileged). Map an *approval prompt* to the
  existing `confirm_fn` hook on `cmd_sandbox`; render approvable decisions as a prompt,
  hard-deny destructive/privileged. Keep default = deny (offline/safe).
- Confidence: High (matches ARC's existing gates).
- Unresolved: opencode is TS/Go (Bun) — not directly reusable; we only borrow UX shape.

### Codex CLI interactive loop
- Source: opentools.ai Codex CLI guide.
- Link: https://opentools.ai/resources/codex-cli-guide
- Learned: Loop = propose action -> user approves/denies -> execute. Slash commands to
  switch model, compact context, inspect permissions. Approval gate is the safety net.
- Consequence: Our shell renders user block -> result/approval block; `/model` `/status`
  `/session` surface state. Approval must never be silent.
- Confidence: High.

### Claude Code
- Source: anthropics/claude-code issues (permission bypass mid-session).
- Link: https://github.com/anthropics/claude-code/issues/15041
- Learned: Distinct message blocks, persistent permission modes, visible safety state.
- Consequence: Distinct user/assistant/tool/system/warning/error blocks; visible trust
  banner. We do NOT add a bypass mode (safety default stays).
- Confidence: Medium (behavior observed indirectly).

### Kiro agent UX
- Source: local prompt context (AGENTS.md handoff) + ARC roadmap.
- Learned: Plan/build/auto modes, checkpoint/approval interactions, command affordances.
- Consequence: ARC session already has plan/build/auto modes + `/plan /build /auto`;
  prompt shows mode. Surface mode in startup panel + prompt.
- Confidence: High (mirrors existing ARC session model).

### Rich (testable rendering)
- Source: Rich docs — Console API, Panel.
- Link: https://rich.readthedocs.io/en/stable/console.html ,
  https://rich.readthedocs.io/en/stable/reference/panel.html
- Learned: `Console(record=True, width=N)` + `console.export_text()` captures rendered
  output deterministically; `Panel(width=...)` auto-detects width; `box.ASCII` vs unicode
  boxes for fallback.
- Consequence: `Renderer` wraps an injectable `Console`; tests build a recording console
  at fixed width and assert on `export_text()`. ASCII box when `ARC_ASCII=1` or non-utf
  stdout; narrow terminals just wrap (no crash). Avoid markup in prompt string (paths and
  `[mode|...]` would be parsed as Rich markup) — use builtin `input()`.
- Confidence: High.
- Decision: NO Textual. Rich-only meets every acceptance criterion; Textual is a heavy
  full-screen dep not justified here.

## 2. Local ARC code inspection (highest-confidence, most actionable)

- `cli/_app.py` `_arc_default`: bare `arc` + TTY + not `ARC_NO_TUI` -> `run_chat_repl()`.
  Consequence: keep this; branch *inside* `run_chat_repl` on `ARC_PLAIN_REPL`.
- `cli_repl/chat_repl.py`: exports `_format_result/_format_prompt/_format_startup_banner/
  _format_progress_event/_configure_provider_default` — all imported by existing tests.
  Consequence: PRESERVE verbatim; they become the plain/legacy path (`_run_plain_repl`).
- `cli_repl/slash_commands.py`: `SlashCommandHandler.handle -> CommandResult|str|None|
  '__EXIT__'`. `CommandResult(state,output,reason,...)`. States: present/ok/absent/empty/
  blocked/denied/degraded/error/failed. `cmd_sandbox(arg,_session,*,confirm_fn=None)`
  already supports injectable approval; destructive/privileged hard-denied.
  Consequence: rich shell sets `handler.confirm_fn = renderer.confirm_approval`; handler
  passes it to sandbox only. `confirm_fn=None` default keeps every existing test green.
- `security/trust.py` `resolve_trust(ws).level.value`: trust label (untrusted by default).
- `runtime/mode.py` `RuntimeMode` FAKE/GATED_LOCAL/PROVIDER_BACKED; default FAKE.
  Consequence: startup shows `fake/offline`; provider-backed only when explicitly enabled.
- `/clear` already exists (`cmd_clear`). `/model` and `/session` do NOT exist.
  Consequence: add `cmd_model` (honest **degraded** — switching not wired) and
  `cmd_session` (present — current session summary); register with full metadata; add to
  `cmd_help` groups.
- Existing tests (`tests/test_cli_repl.py`) assert `/status` text contains `Workspace`,
  `Trust:`, `BUILD`, `Provider: none`, `Sandbox: subprocess (microvm preflight-only)`,
  `Context: unknown`; `/help` contains group headers + `Recommended entrypoint`.
  Consequence: do not change those command outputs; only wrap them visually in the shell.

## 3. Decision table

| Decision | Chosen | Alternatives | Reason | Files | Confidence |
| --- | --- | --- | --- | --- | --- |
| UI toolkit | Rich only | Textual, prompt_toolkit | Rich is a dep; meets all criteria; no heavy dep | rendering.py, theme.py | High |
| Mode switch | env `ARC_PLAIN_REPL=1` -> plain | new subcommand/flag | matches handoff; zero change to `_app.py` | chat_repl.py | High |
| Legacy preservation | keep `_format_*` as `_run_plain_repl` body | rewrite | existing tests import them | chat_repl.py | High |
| Approval UX | reuse `confirm_fn` hook | new approval engine | no gating change; tests stay green | slash_commands.py, rendering.py | High |
| `/model` | honest `degraded` | fake switch | switching not wired; do-not-fake rule | slash_commands.py | High |
| Prompt input | builtin `input()` | `console.input()` | avoid Rich markup parsing of `[mode|...]`/paths | chat_repl.py | High |
| Determinism | injectable `Console`, `export_text()` | snapshot lib | stdlib-only, stable | rendering.py, tests | High |

## 3b. Grounded references (Context7 + Vercel/GitHub grep + Claude Code source)

- Context7 `/websites/rich_readthedocs_io_en_stable` — confirmed canonical testable-render:
  `Console(record=True)` + `console.export_text(styles=False)`; alternatives `Console(file=StringIO())`
  and `console.capture()`. Consequence: tests use `Console(record=True, width=N).export_text()`.
  Confidence: High.
- Vercel/GitHub grep (`Confirm.ask("Approve`) — PraisonAI: `Panel(panel_content, title="Approval
  Required", border_style="yellow")` + `Confirm.ask("Approve this action?", default=False)` plus a
  follow-up "Remember this choice?". Consequence: validates deny-by-default approval panel; ARC keeps
  single approve `[y/N]` (no persisted "remember" this phase). Confidence: High.
  Note: repeated grep calls returned HTTP 429 "Too Many Requests"; one successful result captured.
- Claude Code source (local UX reference: `/Users/hansvilund/Downloads/claude-code-main`, observed
  patterns only, no code copied):
  - `src/components/permissions/PermissionPrompt.tsx`: `FeedbackType = 'accept' | 'reject'`, default
    question "Do you want to proceed?", reject path "tell Claude what to do differently"; options like
    "Yes, and don't ask again for <cmd> in <dir>". Consequence: ARC's deny-by-default + approve-once
    matches; a persisted "don't ask again" allow-rule is a future enhancement, not implemented now.
  - `src/utils/classifierApprovals.ts`: tracks tool uses auto-approved by a classifier (`bash`/
    `auto-mode`) with `matchedRule`/`reason`. Consequence: directly analogous to ARC `security.sandbox.
    decide()` (classify -> auto-allow read-only, gate the rest). Confidence: High.
  - Distinct `*ToolUseRejectedMessage.tsx`, `StatusLine.tsx`, `ModelPicker.tsx`, `StructuredDiff.tsx`,
    `useExitOnCtrlCD.ts`. Consequence: validates distinct user/assistant/tool/denied blocks, a status/
    model surface, a diff view, and clean Ctrl+C exit+save — all present in the ARC renderer.
  - Claude Code uses Ink/React (full-screen reconciler). Consequence: confirms our NO-Textual call —
    ARC stays line-oriented Rich blocks; a full Ink-style TUI is out of scope. Confidence: High.

## 4. Unresolved / explicitly out of scope (kept honest)
- Live provider token streaming: only via gated provider-backed mode; fake/offline renders
  the deterministic response (no fake streaming).
- Diff/apply: `diff_panel` renderer provided for preview parity; actual apply still routes
  through existing `/edit` `/apply` commands (not rewired this phase).
- Full TUI (split panes / live region): not implemented; line-oriented Rich blocks only.

---

# Plan + UI/UX Mockups (Phase 1)

## Architecture
```
chat_repl.py   orchestration only: session lifecycle, input loop, command routing
               run_chat_repl() -> _run_plain_repl (ARC_PLAIN_REPL/non_interactive)
                                \-> _run_rich_repl (default)  -> calls Renderer
rendering.py   Renderer(console): startup_panel, command_palette, user/assistant/tool
               blocks, progress_line, result_block, command_result, approval_panel,
               confirm_approval, diff_panel
theme.py       state->style map, block->style map, ascii fallback, box selection
slash_commands.py  + cmd_model (degraded), cmd_session (present); handler.confirm_fn hook
```
Default boxes use simple unicode (`box.SQUARE`); `ARC_ASCII=1` or non-utf stdout -> `box.ASCII`.

## Mockups (ASCII fallback shown; unicode boxes by default)

1) Startup screen
```
+ ARC Studio v0.1.0-alpha ------------------------------------------+
| workspace   /Users/.../arc-theia-studio                          |
| trust       untrusted                                            |
| runtime     fake/offline                                         |
| provider    none                                                 |
| model       unknown                                              |
| sandbox     subprocess                                           |
| tools       off                                                  |
| context     unknown                                              |
| session     s-abc123                                             |
+------------------------------------------------------------------+
/help  /status  /model  /session  /tools  /sandbox  /clear  /exit
```
2) Idle prompt
```
arc[build|fake|none|tools:off|ctx:?] >
```
3) User message block
```
+ User -------------------------------------------------------------+
| hello                                                            |
+------------------------------------------------------------------+
```
4) Assistant block (no fake streaming; deterministic fake output)
```
+ Assistant --------------------------------------------------------+
| [SwarmGraph] Run completed - 1/1 tasks, $0.0000                  |
| Fake deterministic response for: hello                          |
+------------------------------------------------------------------+
```
5) Tool call block (from progress events)
```
[tool] read_file args={'path': 'a.txt'}
[tool] read_file ok trust=untrusted
```
6) Sandbox approval prompt (approvable: network/install/unknown)
```
+ Approval Required ------------------------------------------------+
| Sandbox approval required                                        |
| Command: curl https://example.com                               |
| Policy: local-safe   Classification: network                    |
| Reason: network denied by default                               |
| Default: deny. Destructive/privileged remain hard-denied.       |
+------------------------------------------------------------------+
Approve once? [y/N]
```
7) Denied command
```
+ denied -----------------------------------------------------------+
| Sandbox denied: rm -rf .                                         |
| destructive command denied by policy (local-safe)              |
+------------------------------------------------------------------+
```
8) Diff/apply preview (preview only; apply via /edit /apply)
```
+ Proposed Edit (+12 -3) -------------------------------------------+
| file  python/src/.../example.py                                  |
| - old                                                            |
| + new                                                            |
+------------------------------------------------------------------+
Apply via: /edit ...  (apply not auto-wired)
```
9) /help -> grouped palette inside a "Help" panel (existing cmd_help text).
10) /status -> "Status" panel (existing render_status text: Workspace/Trust/Provider/Sandbox/Context).
11) /model -> "Model" panel, **degraded** style: provider/model/runtime + "switching not wired".
12) /session -> "Session" panel: id/mode/runtime/messages/created.
13) Error/degraded state
```
+ error ------------------------------------------------------------+
| command failed: <msg>                                            |
+------------------------------------------------------------------+
```
14) Legacy/plain mode (`ARC_PLAIN_REPL=1 arc`) — unchanged:
```
ARC Studio v0.1.0-alpha
Run agents. See everything.
workspace: /Users/.../arc-theia-studio
state: mode=build runtime=fake provider=none model=unknown trust=untrusted sandbox=subprocess tools=off context=unknown
next: /status  /tools list  /context pack <task>  /agent <task>  /help
arc[build|fake|none|tools:off|ctx:?] >
```
