# ARC Studio — Local CLI Bootstrap Prompt

**Paste the section below into your local agent (Claude Code, Codex CLI, Aider, OpenCode, Cursor, Goose, etc.) after running `cd arc-theia-studio` in a fresh clone.**

The prompt is self-contained: it points the agent at the existing review + patch artifacts in this repo and tells it exactly what to do, in what order, with which verification commands.

---

## 📋 PROMPT — copy from here ⤵

You are a senior staff engineer working on the ARC Studio repo. I have just cloned `https://github.com/Hansuqwer/arc-theia-studio` and you are running inside it. Treat this prompt as a **work order**; do not improvise outside it.

### Context files to read first (in this order)

1. **`POST_MERGE_REVIEW.md`** — verified audit of the last 8 PRs, lists the three P0 wiring gaps that must be closed.
2. **`patches/INDEX.md`** — full apply order, dependencies, and the queued P1/P2/P3 UX work.
3. **`UX_AUDIT.md`** — 25-section UX redesign with 20 numbered recommendations (R-001…R-020).
4. **`EXECUTION_PROMPT.md`** — the original sprint spec the 8 PRs were meant to satisfy (used to identify drift).
5. **`AGENTS.md`** at repo root — project engineering rules; **obey them**.

Do **not** read `IMPLEMENTATION_SUMMARY.md`, `PHASE_*.md`, or `SWARMGRAPH_FEATURE_LIST.md` for build status — they are stale planning artifacts. `docs/roadmap.md` is authoritative for current status.

### Non-negotiable constraints

- **Local-first single-user.** No public HTTP, no multi-tenant features, no cloud calls in security paths.
- **stdio-first MCP.** Do not add HTTP transports.
- **Trust + paid-call gates always enforce.** Use `EnforcementContext` (frozen dataclass) + `ContextVar`s; never mutate the dataclass.
- **No LLM in security decisions** (CoSAI rule). All risk re-scoring stays regex/heuristic.
- **Fail-closed.** Missing key, invalid signature, parse error → deny.
- **Additive protocol only.** Add typed events in three Python sites (`KnownRunEvent` union, `is_known_event` set, `parse_typed_event` type_map) AND mirror in `packages/arc-protocol-ts/src/run-events.ts` (`KnownRunEvent` + `KNOWN_RUN_EVENT_TYPES`).
- **No new framework adapters** (Mastra, MAF, etc.) — out of scope.
- **Don't edit `theia-extensions/*`** — legacy/archived.
- **Honesty.** "Built" means a function exists *and* `uv run pytest` passes for it. Never claim test-pass without running the suite.

### Mandatory tool versions

```bash
# Pinned in .tool-versions:
# Python 3.11.10 · uv (latest) · Node.js 20.18.0 · pnpm 9.15.9
which uv || curl -LsSf https://astral.sh/uv/install.sh | sh
which pnpm || corepack enable && corepack prepare pnpm@9.15.9 --activate
```

### Step 1 — Establish baseline (DO NOT SKIP)

```bash
git log -1 --format='%H %s %ai'        # expect HEAD around 788dbc9 (2026-06-04) or newer
cd python && uv sync --all-extras --dev
uv run pytest -q 2>&1 | tail -5         # expect ~4782 passed / 2 pre-existing failures
cd ..
```

If the baseline shows more than 2 failures, **stop and tell me**. Do not patch on top of a broken tree.

The 2 known pre-existing failures (ignore them):
- `tests/auth/test_auth_manager.py::test_provider_statuses_fallback_to_stored_creds`
- `tests/tasks/test_task_executor.py::test_concurrent_task_execution`

### Step 2 — Apply the shipped patches

These are already produced and verified. Apply in this exact order:

```bash
bash patches/verify.sh
```

That single script:
1. Applies `patches/post-merge/001…003.patch` (closes the three P0 wiring gaps from POST_MERGE_REVIEW.md).
2. Applies `patches/ux/p0-polish/001…008.patch` (Header, ModeBadge, ContextMeter, MarkdownBlock, Shift+Tab cycle, `/plan` `/build` `/auto` `/review`, 8 new tests).
3. Runs `uv run ruff check`, `uv run pytest tests/test_tui_core.py tests/tui tests/capabilities tests/mcp tests/adapters tests/security -q`.
4. Ends with `=== ALL GREEN ===` and `1107 passed, 1 skipped`.

If any patch fails to apply, **stop and tell me**: paste the failing patch path + the first 20 lines of `git apply --check` output. Don't try to "fix and continue" silently.

### Step 3 — Commit the shipped patches

One commit per logical group, conventional-commits style:

```bash
git add python/src/agent_runtime_cockpit/adapters/base.py \
        python/src/agent_runtime_cockpit/adapters/swarmgraph.py \
        python/src/agent_runtime_cockpit/adapters/langgraph.py
git commit -m "fix(adapters): wire enforce_card into run_workflow (D-01)"

git add python/src/agent_runtime_cockpit/mcp/server.py
git commit -m "fix(mcp): wire outbound risk gate into _tool_result (D-02)"

git add python/src/agent_runtime_cockpit/tui/screen.py
git commit -m "fix(tui): route shell escape through trust + denylist (D-03)"

git add python/src/agent_runtime_cockpit/tui/widgets/header.py \
        python/src/agent_runtime_cockpit/tui/widgets/mode_badge.py \
        python/src/agent_runtime_cockpit/tui/widgets/context_meter.py \
        python/src/agent_runtime_cockpit/tui/widgets/markdown_block.py \
        python/src/agent_runtime_cockpit/tui/widgets/transcript.py \
        python/src/agent_runtime_cockpit/tui/data.py \
        python/src/agent_runtime_cockpit/tui/screen.py \
        python/tests/tui/
git commit -m "feat(tui): UX P0 polish — Header, ModeBadge, ContextMeter, Markdown, Shift+Tab cycle (R-001..R-004)"
```

Do **not** push to origin unless I explicitly say so. Work on a local feature branch:

```bash
git checkout -b feat/post-merge-and-ux-p0
```

### Step 4 — Smoke-test the UI by eye

Run each of these in a real terminal (not piped) and confirm visually:

```bash
cd python
uv run arc                                  # expect modern Header + ModeBadge "■ build" + ctx meter
# Inside the TUI:
#   Press Shift+Tab → mode chip changes to ▶ auto, then ◆ review, then ▲ plan
#   Type /plan        → system message "Mode: plan" + chip updates
#   Type /help        → modal lists commands
#   Type !ls          → tool card; if workspace untrusted, shows deny banner
#   Type some markdown → assistant reply should render bullets + code blocks
#   Ctrl+C twice      → exits

NO_COLOR=1 uv run arc                       # ASCII-only chips: (plan) (build) etc.
COLUMNS=80 LINES=24 uv run arc              # header collapses gracefully
```

If any of those fail visually, tell me what you saw vs what you expected.

### Step 5 — Begin P1 work (Approval card + capability banner + MCP decision stream)

This is the next phase. The patches are **not yet written**; you will write them. Plan from `patches/INDEX.md` § `ux/p1-modes-approvals/`:

| # | Implements | Files to create / touch |
|---|---|---|
| 010 | UX R-007 ApprovalCard (universal across Capability/Paid/MCP/HITL gates) | new `python/src/agent_runtime_cockpit/tui/widgets/approval_card.py`; edit `tui/screen.py` to push as modal |
| 011 | UX R-006 CapabilityCardBanner inline | new `tui/widgets/capability_banner.py`; subscribe to already-merged `CAPABILITY_CARD_DECISION` typed events |
| 012 | UX R-008 ActivityTray (Ctrl+X) | new `tui/widgets/activity_tray.py`; wire existing `action_toggle_activity` |
| 013 | UX R-008 McpDecisionBanner inside ActivityTray | new `tui/widgets/mcp_banner.py`; subscribe to already-merged `MCP_CALL_DECISION` |
| 014 | UX R-012 PlanView split (spec + simulator) | new `tui/views/plan_view.py`; reuse `simulation/simulator.py` |
| 015 | Streaming via Textual `RichLog` + `Live` | edit `tui/screen.py` `_handle_chat_message` + `tui/widgets/transcript.py` |
| 016 | Promote `_handle_shell_escape` from denylist to full `security/sandbox.decide()` | edit `tui/screen.py` |
| 017 | Event-bus subscriptions for new typed events | edit `tui/screen.py` + new widgets |

**Workflow per patch** (this is the exact pattern that produced the shipped P0 work):

1. Read the relevant section of `UX_AUDIT.md` for the recommendation (e.g. R-007).
2. Inspect already-merged event/model types you'll consume:
   - `python/src/agent_runtime_cockpit/protocol/capability_card_events.py`
   - `python/src/agent_runtime_cockpit/protocol/typed_events.py` (search `CAPABILITY_CARD_DECISION`, `MCP_CALL_DECISION`, `EVAL_POLICY_APPLIED`)
   - `python/src/agent_runtime_cockpit/capabilities/enforcement.py` (`enforce_card`, `DenialReason`)
   - `python/src/agent_runtime_cockpit/mcp/sandbox.py` (`decide_call`, `load_decisions`)
   - `python/src/agent_runtime_cockpit/events/` (the in-process bus)
3. Write the new widget/view. Match the style of `tui/widgets/mode_badge.py` (small, focused, `DEFAULT_CSS`, NO_COLOR-aware).
4. Add unit tests under `python/tests/tui/` mirroring `test_mode_cycle.py`.
5. Run `uv run pytest tests/tui tests/test_tui_core.py -q` — must be all-green before committing.
6. Run `uv run ruff check src/agent_runtime_cockpit/tui tests/tui` — must be clean.
7. Capture the change with `git diff > patches/ux/p1-modes-approvals/0NN_descriptive_name.patch`.
8. Verify clean re-apply: stash → unstash → `git apply --check` → ok.
9. Append a row to `patches/INDEX.md` under the P1 section.
10. Commit with `git commit -m "feat(tui): R-007 ApprovalCard"` etc.

### Step 6 — Continue to P2 and P3

Same workflow for `patches/ux/p2-components-ia/` (11 patches) and `patches/ux/p3-themes-a11y/` (9 patches). See `patches/INDEX.md` for the full list. **All four phases ship; nothing is deferred.**

### Step 7 — Final whole-suite verification

After every phase:

```bash
cd python
uv run pytest -q 2>&1 | tail -3
uv run ruff check src tests
uv run mypy src
cd ..
pnpm install --frozen-lockfile
pnpm build && pnpm typecheck && pnpm check:pr
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/roadmap.md
```

Required end state per phase:
- Python: ≥ 4790 passed (4782 baseline + new tests), 2 known failures or fewer, 0 errors.
- TS: build green, typecheck green, `pnpm check:pr` green.
- Banned claims check: clean.

### Common landmines to avoid

These are real things that bit during the P0 work:

1. **`EnforcementContext` is `@dataclass(frozen=True)`.** Do not add fields. Use a separate `ContextVar` (`security/context.py` already does this for `_enforcement_context`).
2. **The `swarmgraph` package name has a MetaPathFinder bridge.** Never put new code under `agent_runtime_cockpit.swarmgraph.*`; use `capabilities/`, `swarmgraph_ir/`, `simulation/`, `tui/`, or new top-level dirs.
3. **MCP tool decorators** (`@mcp.tool()`) are nested inside `create_mcp_server`. New tools must follow the existing `_trusted()` + `_tool_result(name, callback, args)` pattern.
4. **Typed events live in three sites + one TS site.** Missing any one breaks parity tests.
5. **`Banner` import must stay** in `tui/screen.py` (use `# noqa: F401`) — at least one test asserts `query_one("#banner")`.
6. **`uv run` is mandatory.** Bare `pytest` will not pick up the right Python env.
7. **`pnpm-workspace.yaml` excludes legacy `theia-extensions/*`.** Don't edit those dirs even if grep shows hits.
8. **`extra="ignore"` on Pydantic models** is the repo's forward-compat convention — preserve it on every new model.
9. **`subprocess.run` in TUI shell escape**: `patches/post-merge/003` adds a denylist; P1 patch 016 must promote to `security.sandbox.decide()`.

### Failure protocol

If any step above fails:

- **Patch won't apply** → stop. Paste the failing patch and `git apply --check` output to me. Do NOT manually edit the source and pretend the patch applied.
- **Test fails** → stop. Don't `@pytest.mark.skip` or `xfail` to make it green. Either fix the root cause or report the failure to me with the first 50 lines of pytest output.
- **`uv sync` fails on system deps** → tell me the exact missing lib (libpq, libcrypto, etc.) and the OS package needed.
- **TypeScript build fails on Theia API drift** → don't downgrade Theia; tell me and we'll open a separate fix PR.

### What to deliver back to me

After Step 4 (P0 shipped + smoked):

```
✅ Baseline: <SHA>, <N> passed locally
✅ Applied: 3 post-merge + 8 P0-UX patches → 1107 passed
✅ Smoked: dark/NO_COLOR/80x24 all render correctly
✅ Committed on branch feat/post-merge-and-ux-p0
✅ Ready to start P1 work
```

Then we'll iterate phase-by-phase. Begin.

## 📋 END PROMPT ⤴

---

## Tips for piping into specific local CLIs

**Claude Code:**
```bash
claude < LOCAL_CLI_PROMPT.md
# or, with explicit context loading:
claude "$(cat LOCAL_CLI_PROMPT.md)"
```

**Codex CLI:**
```bash
codex "$(cat LOCAL_CLI_PROMPT.md)"
```

**Aider:**
```bash
aider --message-file LOCAL_CLI_PROMPT.md \
      POST_MERGE_REVIEW.md patches/INDEX.md UX_AUDIT.md EXECUTION_PROMPT.md AGENTS.md
```

**OpenCode:**
```bash
opencode -m "$(cat LOCAL_CLI_PROMPT.md)"
```

**Cursor / VS Code Chat:**
- Open `LOCAL_CLI_PROMPT.md` and `POST_MERGE_REVIEW.md` as `@`-mentions.
- Paste the prompt body into chat.

**Goose:**
```bash
goose session start --instructions LOCAL_CLI_PROMPT.md
```

## Quick sanity check before you run the agent

```bash
# Confirm artifacts are present:
test -f POST_MERGE_REVIEW.md  || echo "MISSING: POST_MERGE_REVIEW.md"
test -f patches/INDEX.md      || echo "MISSING: patches/INDEX.md"
test -f patches/verify.sh     || echo "MISSING: patches/verify.sh"
test -x patches/verify.sh     || chmod +x patches/verify.sh
test -d patches/post-merge    || echo "MISSING: patches/post-merge/"
test -d patches/ux/p0-polish  || echo "MISSING: patches/ux/p0-polish/"
ls patches/post-merge/*.patch | wc -l    # expect 3
ls patches/ux/p0-polish/*.patch | wc -l  # expect 8
```

If all checks pass, the prompt is ready to feed to your local agent.
