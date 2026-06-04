## 📋 PROMPT — copy from here ⤵

# ARC Studio — Token-Saving P0 Execution Prompt

**Sprint:** v0.3.0-alpha prep — 4 work items, ≤4 dev-days total  
**Research base:** `research/token-saving-plan` @ `cbe34cd`  
**Spec author:** Senior Staff Engineering, 2026-06-04

---

## ROLE

You are a senior staff engineer implementing the ARC Studio Token-Saving P0 sprint.
You may use Python, Pydantic, Typer, and Textual. You may not call paid LLMs from
production code; deterministic logic only for any budget/security decision (CoSAI rule).

---

## NON-NEGOTIABLE CONSTRAINTS

1. **Local-first single-user.** No new network features.
2. **EnforcementContext is `@dataclass(frozen=True)`.** Never mutate. Use ContextVars for new state.
3. **NO LLM in security decisions (CoSAI).** Token-saving heuristics are deterministic.
   LLM summarization (P1, not this sprint) operates only on chat transcript, never on
   TrustState/SandboxPolicy/BudgetVector.
4. **Fail-closed on cost.** Unknown budget → deny, not silent downgrade.
5. **Additive protocol only.** New typed events must appear in three Python sites
   (`KnownRunEvent`, `is_known_event`, `parse_typed_event`) AND TS mirror.
   Never rename or remove existing events.
6. **`extra="ignore"` Pydantic convention.** Preserve on every new model.
7. **Don't edit `theia-extensions/*`** — legacy/archived.
8. **Honesty.** "Built" means a function exists and `uv run pytest` passes for it.
   Never claim test-pass without running the suite.

---

## REPO REALITY (verified 2026-06-04)

### Already built — do not rebuild

| Subsystem | Verified file:line |
|---|---|
| `cache_control` on Anthropic requests | `providers/anthropic.py:237-259` — `_request_kwargs()` sets `kwargs["system"]` (line 251) and `kwargs["tools"]` (line 255); calls `_apply_cache_breakpoints_to_request` at line 258 **only when `request.cache_control` is set by the caller** |
| `cache_creation/read_input_tokens` attributed | `providers/anthropic.py:400-401` — both fields read from API response already |
| `ProviderFeature.PROMPT_CACHING` declared | `providers/anthropic.py:57` |
| `CacheBreakpoint` data model | `providers/base.py` — `CacheBreakpoint(position, index, ttl_seconds)` already defined |
| `AnthropicCountTokensEstimator` | `providers/anthropic_estimator.py:77` — class, method `estimate_tokens(response) -> tuple[int,int]`; delegates to `anthropic.messages.count_tokens`; **currently shelved — no callers outside the module and `providers/__init__.py`** |
| `TiktokenApproximateEstimator` | `providers/anthropic_estimator.py` — `cl100k_base` fallback |
| `optimizer/local.py:count_tokens()` | tiktoken-backed counter for OpenAI; also exported from `optimizer/__init__.py` |
| `BudgetEnforcer` | `budget.py` — `check_and_update(tokens,cost,latency_ms)`, `check_and_warn()`, `exhausted`, `reset()` |
| `DataStore` | `tui/data.py` — `total_tokens:int=0`, `context_limit:int=0`, `entries:list[TranscriptEntry]` |
| Status bar | `tui/widgets/status_bar.py:32-46` — currently shows cost + daemon dot; no token meter |
| Context meter widget | `tui/widgets/context_meter.py` — standalone widget, NOT yet wired into status bar |

### Genuinely absent — build these

| Gap | Verification |
|---|---|
| `request.cache_control` is **never populated** by callers — `_request_kwargs` has the wire but callers always pass `cache_control=None/[]` | `grep -rn "cache_control" python/src/agent_runtime_cockpit/providers/ \| grep -v "anthropic.py\|base.py\|__pycache__"` → 0 hits |
| Message ordering not enforced — system/tools/history order is caller-dependent | No ordering contract in `providers/openai_compatible.py` |
| `estimate_tokens()` public utility — callers must not know which estimator to use | No `context/token_counter.py` exists |
| Token meter in status bar | `status_bar.py` has no token count display |

---

## OUTPUT FORMAT YOU MUST PRODUCE

For each work item:
1. Create/edit the listed files exactly.
2. Add tests at the listed paths.
3. Run the listed verification commands locally and paste output.
4. Commit each item as its own commit (conventional-commits).
5. Update `CHANGELOG.md` `[Unreleased]` → Added.
6. Update `docs/roadmap.md` with a new Status row.
7. Export patch: `git format-patch -1 HEAD --stdout > patches/tokens/p0/00N_<name>.patch`

If any step fails locally, **STOP**, paste the failure, and request guidance.
Do not fix-and-continue silently.

---

## THE PLAN — 4 work items in order

### ITEM 1 — P0-1: Byte-Stable Message Ordering for Provider Auto-Cache (≤0.5 day)

**PR title:** `feat(providers): byte-stable message ordering for prefix caching`  
**Branch:** `feat/token-p0-message-ordering`  
**Why first:** OpenAI auto-caches the longest stable prefix. A single reordering across
requests breaks the cache entirely. This is the zero-cost foundation for all caching benefits.

#### Files to edit

1. **`python/src/agent_runtime_cockpit/providers/openai_compatible.py`**  
   In the method that builds the `messages` list for the API call:
   - Enforce order: system message(s) → tool definitions (if in messages format) → conversation history
   - The order must be **byte-stable**: same content must produce the same bytes across two
     calls in the same session. Do not sort by timestamp or add dynamic fields.

2. **`python/src/agent_runtime_cockpit/providers/anthropic.py`**  
   In `_request_kwargs()` (lines 237–259):
   - `system` block already extracted first — confirm it stays first.
   - `tools` already set separately — confirm no interleaving with messages.
   - Add `# ORDER STABLE: system → tools → messages` comment at line 237 so future
     editors know this ordering is cache-critical.

#### Tests to add

**`python/tests/providers/test_message_ordering.py`** (new file):
- `test_openai_system_first` — system message appears before any role="user" message
- `test_openai_tools_before_conversation` — tool definitions appear before conversation messages
- `test_anthropic_system_block_first` — `kwargs["system"]` set before `kwargs["messages"]`
- `test_byte_stable_across_two_calls_same_session` — calling build-messages twice with same
  input produces identical byte output (no UUID injection, no timestamp drift)
- `test_new_tool_appended_not_inserted` — adding a new tool to the list appends to end,
  never inserts before an existing tool (cache stability)

#### Verification

```bash
cd python
uv run pytest tests/providers/test_message_ordering.py -q
uv run ruff check src/agent_runtime_cockpit/providers
```

#### CHANGELOG

```
### Added
- feat(providers): byte-stable message ordering (system → tools → history) for OpenAI
  auto-prefix-cache and Anthropic breakpoint cache compatibility.
```

**Risk:** Zero. No behavior change beyond ordering. Cache miss falls back to normal pricing.

---

### ITEM 2 — P0-2: Anthropic `cache_control` Breakpoints (≤0.5 day)

**PR title:** `feat(providers): wire cache_control breakpoints into Anthropic requests`  
**Depends on:** Item 1 (stable ordering confirmed)

#### The gap

`providers/anthropic.py:_request_kwargs()` already has `_apply_cache_breakpoints_to_request()`
and `_system_with_cache_control()` wired at lines 251/258. The gap is that **callers never
populate `request.cache_control`** — the list is always empty, so the breakpoint logic
never fires.

#### Files to edit

1. **`python/src/agent_runtime_cockpit/providers/anthropic.py`**  
   In `_request_kwargs()` (lines 237–259), add a **default breakpoint injection**:
   - When `request.cache_control` is empty/None AND `system_texts` exist:
     → auto-inject `CacheBreakpoint(position="system", index=0)` (breakpoint 1 of 4)
   - When `request.cache_control` is empty/None AND `request.tools` exist:
     → auto-inject `CacheBreakpoint(position="tools", index=-1)` (last tool, breakpoint 2 of 4)
   - When `request.cache_control` is **non-empty** (caller set explicit breakpoints):
     → respect caller's breakpoints exactly, no auto-injection
   - This uses only 2 of the 4 Anthropic breakpoints; leaves 2 reserved for P1.

2. **`python/src/agent_runtime_cockpit/providers/anthropic.py`**  
   In `complete()` usage-tracking (lines 400–401), ensure `cache_creation_input_tokens` is
   passed to `BudgetEnforcer.check_and_update()` at the correct premium rate (25% surcharge).
   The tokens are already extracted; wire them through.

#### Tests to add

**`python/tests/providers/test_anthropic_cache_control.py`** (new file):
- `test_system_block_gets_cache_control_by_default` — when request has system text and
  no explicit cache_control, the built kwargs have `cache_control` on the system block
- `test_last_tool_def_gets_cache_control_by_default` — when request has tools and no
  explicit cache_control, last tool in the list has `cache_control: {"type": "ephemeral"}`
- `test_explicit_cache_control_not_overridden` — when caller sets cache_control, auto-injection
  is skipped
- `test_no_cache_control_when_no_system_or_tools` — no auto-injection when request has neither
- `test_cache_read_tokens_attributed` — `cache_read_input_tokens` flows through to budget tracking
- `test_cache_creation_tokens_attributed` — `cache_creation_input_tokens` flows through
- `test_idempotent_two_calls_same_input` — same request twice produces same breakpoint positions

#### Verification

```bash
cd python
uv run pytest tests/providers/test_anthropic_cache_control.py -q
# Smoke proof:
grep -n "cache_control" python/src/agent_runtime_cockpit/providers/anthropic.py | head -10
```

#### CHANGELOG

```
### Added
- feat(providers): auto-inject cache_control breakpoints on Anthropic system + tools
  blocks (2 of 4 breakpoints; 50% read-cost savings on stable prefix after turn 1).
### Security
- cache_creation_input_tokens attributed at 25% premium in BudgetEnforcer;
  wallet will not under-count first-turn cost.
```

**Risk:** Zero. Cache miss falls back to normal pricing; no behavior change for callers.

---

### ITEM 3 — P0-3: Provider-Aware Token Counter Utility (≤0.5 day)

**PR title:** `feat(context): provider-aware token counter`

#### Files to create

1. **`python/src/agent_runtime_cockpit/context/__init__.py`**
   ```python
   from .token_counter import estimate_tokens
   __all__ = ["estimate_tokens"]
   ```
   Note: `context/agents_md.py` and `context/skill_md.py` already exist in this package
   (added in v0.2.0 sprint). This `__init__` may already exist — check first, extend if so.

2. **`python/src/agent_runtime_cockpit/context/token_counter.py`** — new module.  
   Public API:
   ```python
   def estimate_tokens(
       content: str | list,   # str or list[TranscriptEntry]
       *,
       provider: str | None = None,
   ) -> int
   ```
   Implementation rules (in priority order):
   - `provider == "anthropic"` → delegate to `AnthropicCountTokensEstimator` from
     `providers/anthropic_estimator.py` **if a client is available**; otherwise fall back
     to heuristic. **Never call the count_tokens API per-keystroke** — cache results
     keyed on `(hash(content), provider)` with an LRU cache of size 256.
   - `provider == "openai"` → use `optimizer/local.py:count_tokens()` (tiktoken-backed)
     if tiktoken is installed; else heuristic.
   - All other / unknown → heuristic: `max(1, int(len(text) / 4 * 1.33))`
   - `context_limit == 0` means unknown — callers must never compute a percentage from it.

#### Files to edit

3. **`python/src/agent_runtime_cockpit/tui/data.py`**  
   In `add_entry()` (after appending the entry):
   - Call `estimate_tokens(entry.content, provider=self.current_provider)`
   - Add result to `self.total_tokens`
   - Note: this is an **increment**, not a recount. It's an approximation;
     exact counts come from provider responses.

#### Tests to add

**`python/tests/context/test_token_counter.py`**:
- `test_heuristic_short_text` — known short string, result within 15% of expected
- `test_heuristic_empty_string` — returns 0 or 1, never negative
- `test_heuristic_unicode` — non-ASCII content handled without error
- `test_anthropic_falls_back_to_heuristic_without_client` — when no Anthropic client
  available, heuristic is used
- `test_openai_uses_tiktoken_when_installed` — mock tiktoken import, assert it's called
- `test_unknown_provider_uses_heuristic` — provider="groq" → heuristic
- `test_list_input_sums_per_entry` — list of TranscriptEntry sums token counts
- `test_lru_cache_hit` — calling twice with same content does not double-count side effects

#### Verification

```bash
cd python
uv run pytest tests/context/test_token_counter.py -q
uv run ruff check src/agent_runtime_cockpit/context tests/context
uv run mypy src/agent_runtime_cockpit/context
```

#### CHANGELOG

```
### Added
- feat(context): provider-aware token counter (delegates to AnthropicCountTokensEstimator
  for Anthropic; tiktoken for OpenAI; len/4*1.33 heuristic fallback). LRU-cached.
- DataStore.add_entry() increments total_tokens via estimate_tokens().
```

**Risk:** Low. Additive module. Heuristic is an approximation; exact counts still come
from provider responses. Existing `total_tokens` field already tracks this semantically.

---

### ITEM 4 — P0-4: Context-Usage Meter in Status Bar (≤0.5 day)

**PR title:** `feat(tui): context-usage meter in status bar`

#### Files to edit

1. **`python/src/agent_runtime_cockpit/tui/widgets/status_bar.py`** (lines 32–46)  
   Add a token-usage segment after the existing cost segment:
   - Format when `context_limit > 0`: `tok N/M (P%)` where P = int(N/M*100)
   - Format when `context_limit == 0`: `tok N` (never show percentage)
   - Color tier (Textual markup, not CSS colors): 
     - `< 60%` → `[green]`
     - `60–85%` → `[yellow]`
     - `> 85%` → `[red]`
   - NO_COLOR path (when `self.theme.current.no_color`):
     - `[low]`, `[warn]`, `[hot]` text prefixes instead of color markup
   - Do **not** remove the existing `ContextMeter` widget — it lives in the header.
     This adds a compact inline reading to the status bar.

2. **`python/src/agent_runtime_cockpit/tui/data.py`**  
   Ensure `context_limit` is set when a provider responds with model metadata.
   Check if `current_model` already exposes `context_window` or similar — if so, wire it.

#### Tests to add

**`python/tests/tui/test_status_bar_context_meter.py`**:
- `test_renders_tokens_and_limit` — when `total_tokens=5000, context_limit=10000`, output
  contains "5000/10000" and "(50%)"
- `test_no_limit_shows_only_count` — when `context_limit=0`, output contains "5000" but
  not "/" and not "%"
- `test_color_tier_green` — 3000/10000 (30%) → green markup
- `test_color_tier_yellow` — 7000/10000 (70%) → yellow markup
- `test_color_tier_red` — 9000/10000 (90%) → red markup
- `test_no_color_low` — 30%, NO_COLOR → "[low]" in output
- `test_no_color_warn` — 70%, NO_COLOR → "[warn]" in output
- `test_no_color_hot` — 90%, NO_COLOR → "[hot]" in output

#### Verification

```bash
cd python
uv run pytest tests/tui/test_status_bar_context_meter.py tests/tui -q
uv run ruff check src/agent_runtime_cockpit/tui tests/tui
# Visual proof (manual smoke):
uv run arc   # status bar should show "tok 0" on launch
```

#### CHANGELOG

```
### Added
- feat(tui): inline context-usage meter in status bar ("tok N/M (P%)");
  green/yellow/red color tiers at 60%/85%; NO_COLOR text tags [low]/[warn]/[hot].
```

**Risk:** Trivial. Read-only display. `context_limit=0` → raw count only, no division.

---

## CROSS-CUTTING REQUIREMENTS

### Tests

- New code requires unit tests as listed above.
- Coverage must not drop on touched modules.
- Full suite gate: `uv run pytest -q --ignore=tests/e2e --ignore=tests/integration`

### Hygiene (run after every item)

```bash
cd python
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src 2>&1 | tail -3   # 272 errors acceptable (pre-existing baseline)
cd ..
pnpm build && pnpm typecheck && pnpm check:pr
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/roadmap.md
```

### Docs

- Update `CHANGELOG.md` `[Unreleased]` → Added after every commit.
- Update `docs/roadmap.md` with one new Status row per item.
- No new ADR needed. ADR-031 will accompany P1 `/compact`.

### Patches

After each item's commit:
```bash
mkdir -p patches/tokens/p0
git format-patch -1 HEAD --stdout > patches/tokens/p0/00N_<descriptive_name>.patch
```

### Commits (one per item)

```
feat(providers): byte-stable message ordering for prefix caching (P0-1)
feat(providers): wire cache_control breakpoints into Anthropic requests (P0-2)
feat(context): provider-aware token counter (P0-3)
feat(tui): context-usage meter in status bar (P0-4)
```

---

## COMMON LANDMINES (token-saving specific)

1. **Reordering tools mid-session destroys cache.** New tools must be APPENDED to the
   tool list, never inserted before an existing tool.
2. **`AnthropicCountTokensEstimator` and `len/4*1.33` give different counts.**
   Status bar, BudgetEnforcer, and cache-hit metrics MUST all use the same source
   per provider session. Use `estimate_tokens()` from Item 3 as the single call site.
3. **`estimate_tokens()` must NOT call the provider `count_tokens` API on every keystroke.**
   LRU-cache results keyed on `(hash(content), provider)`.
4. **`context_limit=0` means unknown.** Never compute a percentage from it.
   Show raw count only.
5. **`cache_control` breakpoints count against Anthropic's per-request limit (4).**
   P0-2 uses 2 of 4. Leave 2 reserved for P1. Document this in the code.
6. **`cache_creation_input_tokens` is billed at 25% premium.** Attribute correctly
   to BudgetEnforcer; otherwise wallet under-counts first-turn cost.
7. **`context/__init__.py` may already exist** (added in v0.2 sprint with `agents_md`).
   Check before creating; extend if present.

---

## WHAT IS EXPLICITLY NOT IN THIS SPEC

- Microcompact / tool-result trimming (P1-1) — separate spec
- `/compact`, `/fork`, `/rewind` (P1-2, P1-3) — separate spec
- Streaming interrupt at budget threshold (P1-4) — separate spec
- Auto-compact at context threshold (P1-5) — separate spec
- `context_limit` wired from provider model metadata — P1
- tiktoken as a hard dependency — P2 optional install only

---

## DELIVERY CHECKLIST

```
[ ] P0-1 committed, tests pass, patch exported
[ ] P0-2 committed, tests pass, patch exported
[ ] P0-3 committed, tests pass, patch exported
[ ] P0-4 committed, tests pass, patch exported
[ ] uv run pytest -q (full suite) — tail -5 pasted
[ ] uv run ruff check src tests — clean
[ ] uv run mypy src — 272 or fewer errors
[ ] pnpm build && pnpm typecheck — clean
[ ] pnpm check:pr — clean
[ ] CHANGELOG.md [Unreleased] updated (4 entries)
[ ] docs/roadmap.md 4 new Status rows
[ ] grep proof: cache_control sent on Anthropic calls
[ ] grep proof: status bar contains "tok"
[ ] No EnforcementContext mutation
[ ] No LLM in any decision path
[ ] patches/tokens/p0/ contains 4 patch files
```

## 📋 END PROMPT ⤴

---

## How to use this prompt

```bash
# Feed only the prompt body:
sed -n '/^## 📋 PROMPT — copy from here ⤵$/,/^## 📋 END PROMPT ⤴$/p' \
    TOKEN_SAVING_EXECUTION_PROMPT.md | claude

# Or via next-sprint.sh:
./next-sprint.sh token-p0
```
