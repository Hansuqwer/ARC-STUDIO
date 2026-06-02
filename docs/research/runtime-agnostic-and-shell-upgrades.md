# Research: Runtime-Agnostic Shell + Closing Degraded Gaps

Status: research-first gate for runtime engine selector, /model switching,
live streaming, diff→apply, and full-screen TUI decision.

Each note: source · link/path · learned · consequence · confidence · unresolved.

---

## A. Runtime-agnostic /runtime

### Local code inspection (highest confidence)
- Source: `adapters/registry.py`, `orchestration/runtime_router.py`, `adapters/base.py`
- Learned:
  - `AdapterRegistry.build_default()` registers 14 adapters (swarmgraph, langgraph, crewai,
    openai-agents, ag2, llamaindex, lmarena, dspy, haystack, smolagents, semantic-kernel,
    google-adk, mcp-sdk, langchain).
  - `runtime_router.list_runtimes(workspace) -> list[CapabilityReport]` returns each adapter's
    `runtime_id`, `detected`, `can_run`, `requires_paid_calls`, `availability`, `reason`.
  - `AUTO_PRIORITY = ("swarmgraph", "langgraph", "crewai", "lmarena")`.
  - `RuntimeAdapter.capabilities().can_run` is the runnable gate; all adapters expose this.
  - `_handle_input_rich` hardcodes `from ..swarmgraph import SwarmGraphRunner`.
    `SwarmGraphRunner` (in `swarmgraph/__init__.py`) is the **REPL path**; `SwarmGraphAdapter`
    (in `adapters/swarmgraph/runner.py`) is the Theia-facing adapter. Keep using
    `SwarmGraphRunner` for swarmgraph selection; for other adapters without a sync `.run(prompt)`
    stub, return a degraded/unavailable result.
  - Current `cmd_runtime` changes `session.runtime_mode` (FAKE/GATED_LOCAL/PROVIDER_BACKED) which
    is the execution mode, not the engine. `mode` command is also registered separately.
- Consequence:
  - Repurpose `cmd_runtime` for engine selection (list/use). Execution-mode switching remains via
    `/mode` (already registered). This is a non-breaking repurpose since the contract set already
    has both "runtime" and "mode".
  - Store engine selection in `session.metadata['runtime_adapter']` (str, default 'swarmgraph').
  - In `_handle_input_rich`, route through `_run_with_adapter(prompt, session)` which dispatches
    on `session.metadata.get('runtime_adapter', 'swarmgraph')`. Only swarmgraph has a REPL sync
    path; others return CommandResult(state='degraded', reason='no_repl_path').
- Confidence: High.
- Unresolved: None for this phase.

---

## B. /model switching

### Local code inspection
- Source: `providers/__init__.py`, `providers/models_dev.py`
- Learned:
  - `bundled_openai_compatible_providers()` returns a dict of provider configs from a snapshot.
  - Providers: alibaba, deepseek, github-models, moonshotai, zai, 9router, crofai.
  - `ARC_DEFAULT_PROVIDER` env var selects provider; model can be overridden per-provider env.
  - No `/model list` exists yet; `/model` currently returns `degraded` with "not wired" message.
- Consequence:
  - `/model list`: call `bundled_openai_compatible_providers().keys()` + env-based providers;
    mark each as "configured" (key env set) or "unconfigured".
  - `/model use <provider[:model]>`: set `session.metadata["provider"]` and
    `["provider_model"]`; if key env missing → `CommandResult(state='degraded', reason='no_key')`;
    NEVER set `session.allow_paid_calls`. User must explicitly opt in to paid calls.
  - Session `_configure_provider_default` already sets provider from env; `/model use` overrides
    the in-session selection without changing the safe-default env behavior.
- Confidence: High.

### Claude Code model command (observed, not copied)
- Source: `/Users/hansvilund/Downloads/claude-code-main/src/commands/model/model.tsx`
- Learned:
  - `handleSelect(model, effort)` updates app state (`setAppState`) — session-scoped.
  - Shows current model in command description; opens interactive picker.
  - No API key is auto-configured on model switch; auth is a separate gate.
- Consequence: ARC analog: `/model use` sets session metadata only; no gate changes.
- Confidence: High (direct source observation).

---

## C. Live streaming (provider-backed only)

### Context7 (Rich Live)
- Source: Context7 `/websites/rich_readthedocs_io_en_stable`
- Link: https://rich.readthedocs.io/en/stable/live.html
- Learned:
  - `with Live(console=console, transient=False) as live: live.update(Panel(text), refresh=True)`
    for in-place token accumulation.
  - `auto_refresh=False` + manual `live.refresh()` gives tighter control per token.
  - `transient=False` leaves the final block in the scrollback (correct for chat history).
  - NOT safe to `console.print()` inside a Live context — use `live.console.print()` or
    `redirect_stdout=True`. For our shell, we need to stop the Live context before printing
    other output.
- Consequence:
  - In `_handle_input_rich`, when `session.runtime_mode == PROVIDER_BACKED` and streaming is
    available, use `with Live(..., transient=False, auto_refresh=False) as live` in the assistant
    block; accumulate delta chunks; call `live.update(renderer.assistant_block(accumulated))`.
  - Provide an injectable `stream_fn` on the Renderer so tests can pass a sync generator instead
    of a real provider; no network call in tests.
  - Fake/offline: no Live context, render deterministic response directly as before.
- Confidence: High.
- Unresolved: `_run_provider_turn` is async; `_handle_input_rich` is sync. Need to check if
  the existing `_run_coro_sync` wrapper handles the streaming generator correctly.

---

## D. Diff → approve → apply

### Local code inspection
- Source: `cli_repl/rendering.py` (diff_panel), `cli/edit.py`, `security/trust.py`,
  `security/sandbox.py`
- Learned:
  - `rendering.py` already has `diff_panel(file, diff_text, added, removed)` — preview only.
  - `security/trust.resolve_trust(workspace).level` — must be 'trusted' for write.
  - Plan mode (`session.mode == 'plan'`) must deny writes.
  - `cli/edit.py` has full edit logic including safety gates.
  - No in-shell apply function yet.
- Consequence:
  - Add `apply_diff(file_path, new_content, workspace, session, confirm_fn)` to
    `rendering.py` (or a new `diff_apply.py`): show diff_panel preview, call confirm_fn, on
    approval write via atomic write under trust + write gate, denied in plan mode + untrusted.
  - `/diff <file>` slash command already exists but chains to CLI; create
    `cmd_apply_diff(arg, session, *, confirm_fn=None)` that handles the in-shell flow.
    This does NOT replace `/edit` or `/apply` — it adds an explicit in-shell diff→apply UX.
- Confidence: High.

---

## E. Full-screen TUI (ARC_TUI=1 decision)

### Context7 Rich Layout
- Learned: `Layout` + `Live(screen=True)` creates a full-screen alternate-screen TUI in Rich.
  Requires the terminal to support alternate-screen ANSI (most modern terminals do).
  No Textual dependency — uses only the existing `rich` dep.
- Consequence: Technically feasible with Rich alone. BUT:
  - `console.print()` within a Live(screen=True) context corrupts the layout.
  - Input requires a separate thread or async read to avoid blocking the Live refresh loop.
  - Testing full-screen mode requires a fake terminal; determinism degrades significantly.
  - `ARC_TUI=1` opt-in with the line-oriented shell as default is the correct gate.
  - **Decision**: Implement `ARC_TUI=1` as a stub/entry-point that logs "full-screen TUI
    requires ARC_TUI=1 (experimental)" but falls back to the line-oriented shell in this phase.
    A full-screen layout is too large for this phase without weakening test determinism.
    Document the blocker: input-blocking + console.print conflict + test coverage degradation.
- Confidence: High (decision: defer with opt-in stub + documented blocker).

---

## Decision table

| Decision | Chosen | Alternatives | Reason |
| --- | --- | --- | --- |
| /runtime semantics | Engine selector (swarmgraph/langgraph/…) | Keep as mode switcher | ARC is runtime-agnostic; mode already covered by /mode |
| Engine slot | session.metadata['runtime_adapter'] | New session field | Backward compat; no schema change |
| Offline engine default | swarmgraph (backward compat) | lmarena | Preserves all existing tests |
| /model use gate | Sets metadata only; no paid_calls change | Auto-enable paid | Safety default must not be weakened silently |
| Streaming gate | Provider-backed only; injectable stream_fn | Rich Live always | Fake streaming is prohibited; gate already exists |
| Diff apply gate | trust + write gate + plan-mode deny | Open write | Matches sandbox/trust policy |
| Full-screen TUI | ARC_TUI=1 stub; line shell default | Full Textual port | Input conflict + test determinism; no new dep |
| Rich dep | Rich-only (existing dep) | Textual | No new dep needed for all features |

---

## Phase 1 — Mockups

### /runtime list
```
+ Runtime ---------------------------------------------------------------+
| active     swarmgraph                                                   |
|                                                                         |
| ID              detected  can_run  paid  availability                   |
| swarmgraph      yes       no       no    detected_not_runnable          |
| langgraph       yes       no       no    detected_not_runnable          |
| lmarena         yes       yes      no    runnable                       |
| crewai          yes       no       yes   detected_not_runnable          |
| openai-agents   no        no       yes   not_detected                   |
+-------------------------------------------------------------------------+
Use: /runtime use <id>
```

### /runtime use swarmgraph (success or degraded)
```
+ Runtime ---------------------------------------------------------------+
| Active engine set to: swarmgraph                                        |
| can_run: no  (install missing; set ARC_SWARMGRAPH_CLI)                  |
| Execution mode unchanged: fake/offline                                  |
| Paid calls: unchanged (off)                                             |
+-------------------------------------------------------------------------+
```

### /model list
```
+ Model -----------------------------------------------------------------+
| active     none / unknown                                               |
|                                                                         |
| Provider       Configured  Default model                                |
| 9router        yes         ag/gemini-3.5-flash-extra-low               |
| deepseek       no          deepseek-chat                                |
| github-models  no          ai21-jamba-1.5-large                        |
| lmarena        yes         (offline/fake)                               |
+-------------------------------------------------------------------------+
Use: /model use <provider[:model]>
```

### /model use 9router (with key set)
```
+ Model -----------------------------------------------------------------+
| Provider: 9router                                                       |
| Model: ag/gemini-3.5-flash-extra-low                                   |
| Paid calls: unchanged (off) — enable via ARC_ALLOW_PAID=1              |
+-------------------------------------------------------------------------+
```

### Streaming assistant block (provider-backed gated)
```
+ Assistant (streaming) -------------------------------------------------+
| Thinking...                                                             |
| The answer is                                                           |
| The answer is 42.                                                       |  <- live updates
+-------------------------------------------------------------------------+
```

### Diff → approve → apply
```
+ Proposed Edit (+3 -1) -------------------------------------------------+
| file   python/src/.../example.py                                        |
| - old line                                                              |
| + new line                                                              |
| + another new line                                                      |
| + third new line                                                        |
+-------------------------------------------------------------------------+
Apply to python/src/.../example.py? [y/N]
```

### Full-screen TUI (ARC_TUI=1 — stub message this phase)
```
+ System ----------------------------------------------------------------+
| Full-screen TUI (ARC_TUI=1) is experimental and not yet implemented.   |
| Falling back to line-oriented Rich shell.                               |
| Blocker: input blocking conflicts with Live(screen=True) refresh loop. |
+-------------------------------------------------------------------------+
```
