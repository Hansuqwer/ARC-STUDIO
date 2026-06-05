# ARC Studio — Arena.ai Handover Prompt

> **Model instruction (paste this at the top of your arena.ai session):**
> Use **claude-opus-4-8** (Anthropic Opus 4.8 Max) for this entire session.
> Do not switch models mid-session. Engage deep analysis mode before planning.

---

## Your first task before anything else

```bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio

# Install Python env
cd python && uv sync --all-extras --dev && cd ..

# Run tests to confirm baseline
cd python && uv run pytest -q --ignore=tests/e2e --ignore=tests/integration 2>&1 | tail -5

# Read these in order:
# 1. docs/roadmap.md        — full release train + R-TS rows
# 2. CHANGELOG.md           — what shipped in each alpha
# 3. MERGE_NOTES.md         — v0.6-alpha current state
# 4. docs/research/         — pricing, compaction, capability tradeoffs
# 5. docs/spec/             — specs for all shipped + queued sprints
```

---

## Session state

**Repository:** https://github.com/Hansuqwer/arc-theia-studio
**Branch:** `spec/v0.6-catalog-picker` (NOT yet merged to main)
**HEAD:** `6c7bea3` (v0.6 CHANGELOG + MERGE_NOTES)
**Last merged tag:** `v0.5.2-alpha` @ `5c05df5` on `main`

### Release train (all tagged and on main)

| Tag | SHA | What |
|-----|-----|------|
| `v0.3.0-alpha` | — | Token-saving P0 (cache_control, token counter, context meter, OTel) |
| `v0.3.1-alpha` | — | CI debt: jest thresholds restored |
| `v0.4.0-alpha` | — | R-01 TokenWallet + /wallet + /budget + QuotaWarning consumer |
| `v0.4.1-alpha` | — | Budget persistence (SQLiteWAL) + pricing refresh (17 model rows) |
| `v0.5.0-alpha` | `0069735` | R-02 compaction + QW-4 handle virtualization (first behavior-changing) |
| `v0.5.1-alpha` | `d667550` | 6 Chinese-lab vendors (91 model rows from OpenRouter) + /wallet display |
| `v0.5.2-alpha` | `5c05df5` | CostRate capability fields backfill (`supported_parameters`, `input_modalities`) |

### Current branch (awaiting green-light to tag v0.6-alpha)

`spec/v0.6-catalog-picker` — 5 commits ahead of main:

| SHA | What |
|-----|------|
| `dd0dcd3` | `/models` + `/model-info` slash commands with capability filters |
| `6155866` | `capability_gates.py` — deterministic per-model capability lookup |
| `e14f1d3` | Status bar model + capability chip `[vision][tools][reasoning]` |
| `2c59216` | `ModelChanged` typed event (3 Python sites + TS mirror) |
| `6c7bea3` | CHANGELOG + MERGE_NOTES |

**Test baseline:** 5089 Python passed, 149 TS passed.

---

## Architecture in 60 seconds

```
arc-theia-studio/
├── python/src/agent_runtime_cockpit/
│   ├── providers/          ← openai_compatible.py (VENDOR_CONFIGS with CostRates)
│   │   ├── base.py         ← CostRates schema (8 fields incl. capability fields)
│   │   ├── anthropic.py    ← separate provider class
│   │   └── openai_compatible.py  ← 15 vendors (openai/groq/deepseek/kimi/glm/etc)
│   ├── budget/             ← BudgetEnforcer (frozen), SQLiteWALStorage, TokenWallet
│   ├── context/            ← handles.py (QW-4), compaction.py (R-02), tool_interceptor.py
│   ├── cli_repl/
│   │   ├── slash_commands.py     ← 48 CommandDef registrations
│   │   └── slash/                ← models.py, model_info.py (v0.6 new)
│   ├── tui/widgets/
│   │   ├── status_bar.py         ← shows model chip [vision][tools]
│   │   └── capability_gates.py   ← get_capabilities() → {feature: bool}
│   ├── protocol/
│   │   ├── typed_events.py       ← all typed events (KnownRunEvent union)
│   │   └── events.py             ← EVENT_TYPES registry
│   └── events/types.py           ← bus-internal ArcEvent subclasses
├── packages/arc-protocol-ts/src/
│   └── run-events.ts             ← TS mirror of all events
└── protocol/fixtures/run-event-registry.json  ← cross-language parity fixture
```

**Key invariants you must never violate:**
1. `EnforcementContext` is `@dataclass(frozen=True)` — never mutate, use `ContextVar`
2. Gemini block in `openai_compatible.py` has `if self._vendor == "gemini"` caching guard — DO NOT remove (HTTP/2 bug, documented in commit `8cdc378`)
3. No LLM in cost/budget/capability decisions (CoSAI rule)
4. `protocol-additive-only.md`: new typed events need 3 Python sites + 1 TS site
5. `BudgetEnforcer` lives at `budget/schema.py:166` — additive changes only

---

## What the next agent should do

### Immediate: Merge + tag v0.6-alpha

The branch `spec/v0.6-catalog-picker` is ready. User gave green-light but session ended before merge. Run:

```bash
git checkout main && git pull --ff-only
git merge --no-ff spec/v0.6-catalog-picker \
  -m "feat: v0.6-alpha — catalog-driven model picker

/models + /model-info slash commands with per-model capability filters.
capability_gates.py: fail-closed per-model capability lookup.
Status bar chip: model + [vision][tools][reasoning] tags.
ModelChanged typed event (3 Python + 1 TS site).
5030→5089 tests (+59). No new deps. Catalog drives UI, NOT wire."

git tag -a v0.6-alpha -m "Catalog-driven model picker.
/models --has vision|tools|reasoning|--free|--max-input|--search|--vendor
capability_gates.py: get_capabilities(model_id) → dict[str,bool], fail-closed
ModelChanged typed event with diff semantics.
+59 tests (5030→5089)."

git push origin main v0.6-alpha
```

Then write `docs/research/v0.6-catalog-picker-postmortem.md` (same pattern as v0.5.1 postmortem).

### After v0.6 tags: queued work

**v0.7-alpha** — per `docs/spec/v0.7-alpha-opt-in-cloud-features-v3.md`:
- Runtime catalog feed (opt-in, OFF by default)
- Shared observability broker
- Auto-refresh of vendor pricing (signed feed)

**Backfill** (not yet sprint-scoped):
- Anthropic cost rows in `VENDOR_CONFIGS` so `/models --vendor anthropic` returns results
- Non-Chinese-lab capability fields (OpenAI, Groq, etc.) — currently empty defaults
- Per-vendor `--max-context` filter using context window size

---

## Critical files to read before writing code

```bash
# Policy (read once, never violate)
cat docs/policy/cosai-llm-in-path.md
cat docs/policy/local-first.md
cat docs/policy/protocol-additive-only.md
cat docs/policy/honesty-over-polish.md

# Current capability data shape
grep -n "supported_parameters\|input_modalities\|is_free_tier" \
  python/src/agent_runtime_cockpit/providers/base.py

# Vendor blocks (what /models reads)
grep -n '"deepseek"\|"kimi"\|"glm"\|"crofai"' \
  python/src/agent_runtime_cockpit/providers/openai_compatible.py | head -10

# Gemini guard (DO NOT TOUCH)
grep -n "gemini.*caching\|if self._vendor.*gemini" \
  python/src/agent_runtime_cockpit/providers/openai_compatible.py
```

---

## Environment

```
Python: 3.11.10
uv: latest
Node.js: 20.18.0
pnpm: 9.15.9
```

`.env` (gitignored, at repo root):
```
GEMINI_API_KEY=<valid key>
CROFAI=<valid key — covers all Chinese-lab models for smoke testing>
```

CrofAI (`https://crof.ai/v1`, OpenAI-compat) is the test proxy for all Chinese-lab vendors.
Available models for testing: `deepseek-v4-pro`, `glm-5.1`, `minimax-m2.5`, `mimo-v2.5-pro`, `kimi-k2.5`, `kimi-k2.6`.

---

## How to run gates before any PR

```bash
cd python
uv run ruff check src/ tests/
uv run pytest -q --ignore=tests/e2e --ignore=tests/integration
cd ..
cd packages/arc-protocol-ts && pnpm build && pnpm test
cd ../..
bash scripts/release_check.sh  # needs bash 4+; on macOS run each gate manually
```

Expected: 5089+ Python passed, 149+ TS passed, 0 ruff errors.

Pre-existing acceptable failures (do not regress these):
- `tests/budget/test_persistence.py::test_concurrent_accumulation` — SQLite lock, env-specific
- `tests/auth/test_auth_manager.py::test_provider_statuses_fallback_to_stored_creds` — env flake
- `tests/tasks/test_task_executor.py::test_concurrent_task_execution` — env flake
- 5 xfailed: 2 CLI doctor, 1 CLI runs, 2 TUI snapshot SVG-hash
