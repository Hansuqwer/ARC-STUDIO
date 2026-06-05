# ARC Studio — R-UX2 Review & Continuation Handover

> **For:** a fresh Arena.ai preview agent with a clean workspace.
> **Date:** 2026-06-05.
> **Your mode:** review → research → improve. NOT greenfield design.
> **Read time:** ~15 minutes. Read it ALL before your first response.

---

## 0. The one rule that matters most

**Do not invent architecture. ARC Studio runs on locked policies + versioned
specs + an executed UX audit.** Your job is to review the in-flight R-UX2
work against `UX_AUDIT.md`, research any uncertain API against the real
codebase (not from memory), and improve/finish what's partial. When the
audit, a spec, or a policy answers a question — cite the path, don't
re-litigate.

Two prior sessions repeatedly drifted into re-designing things that were
already decided. The user caught it every time. Don't be the third.

---

## 1. Clone + orient (do this first, before responding)

```bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio

# Python env
cd python && uv sync --all-extras --dev && cd ..

# Confirm baseline (expect ~5140 Python, ~155 TS)
cd python && uv run pytest -q --ignore=tests/e2e --ignore=tests/integration 2>&1 | tail -3
cd ../packages/arc-protocol-ts && pnpm install && pnpm build && pnpm test 2>&1 | tail -3
cd ..

# The active branch with in-flight R-UX2 work:
git fetch origin
git checkout spec/v0.8-r-ux2
git log --oneline main..spec/v0.8-r-ux2
```

You **cannot** push to the user's machine or run their shell — they run
commands, you interpret output. Standard Arena operating model.

---

## 2. Required reading (in this order — do not skip)

### Tier 1 — Locked policies (read in full, never re-litigate)
1. `docs/policy/cosai-llm-in-path.md` — no LLM in spend/eviction/routing/sandbox decisions
2. `docs/policy/local-first.md` — opt-in only; no surprise exfiltration; defaults OFF
3. `docs/policy/protocol-additive-only.md` — new typed events = 3 Python + 1 TS site; `extra="ignore"`
4. `docs/policy/honesty-over-polish.md` — "Built" = tested + green + verified by command output

### Tier 2 — The authoritative design for this work
5. `UX_AUDIT.md` (repo root, 940 lines) — the executed audit. R-001…R-020 recommendations, 25-heuristic scoring (TUI was 39/100), 4-phase plan (§19), highest-leverage recommendation (§23).
6. `UX_AUDIT_PROMPT.md` — the standalone audit prompt (constraints: NO_COLOR, ≥80×24, ≤16ms keystroke, keyboard-first).

### Tier 3 — The locked plan (where R-UX2 sits)
7. `docs/roadmap.md` — search `R-UX1` … `R-UX4` and `R-TS8`…`R-TS10`. Shows what shipped + what's planned.
8. `docs/phases.md` — read the "Reprioritization 2026-06-05" section near the top. Explains why UX work is ahead of the microVM mandate.

### Tier 4 — Recent postmortems (pattern reference)
9. `docs/research/v0.7-opt-in-cloud-postmortem.md` — example of how findings get recorded.

---

## 3. State of the world

### Tags shipped (all on `main`)
```
v0.3.0 → v0.3.1 → v0.4.0 → v0.4.1 → v0.5.0 → v0.5.1 → v0.5.2 → v0.6 → v0.7
```
9 alpha tags. Token-saving series (R-TS1–R-TS10) + cloud features all complete and documented in roadmap.

### Active branch: `spec/v0.8-r-ux2` (3 commits ahead of main)
```
12c5afb  feat(tui): route !shell escape through sandbox.decide() (R-UX2, audit P0)
29a9cf0  feat(tui): PlanView read-only plan panel (R-UX2 / R-012)
4f01ec9  docs(roadmap): R-UX2 Partial — sandbox shell + PlanView done; ApprovalCard wiring remains
```

### R-UX series status
| Sprint | Status | Detail |
|--------|--------|--------|
| R-UX1 | ✅ Baseline Complete | Header + ContextMeter + ModeBadge + Markdown (commit 0b03f41 on main) |
| **R-UX2** | ⚠ **Partial — your focus** | widgets exist; 2 gaps filled this sprint; 1 gap remains |
| R-UX3 | Planning Only | Components + IA (ToolCard, DiffViewer, SlashMenu, Palette, frontmatter registry) |
| R-UX4 | Planning Only | Themes + A11y (5 themes, NO_COLOR glyphs, reduced motion, snapshot harness) |

### Test baseline: 5140 Python passed, 155 TS passed, 30 skipped, 5 xfailed (all pre-existing).

---

## 4. R-UX2 detailed status — what's done, what's not

R-UX2 = "Modes + Approvals" per `UX_AUDIT.md` §19 P1. Six pieces:

| # | Piece | Audit ref | File | Status |
|---|-------|-----------|------|--------|
| 1 | ApprovalCard (unify 4 gates) | R-007 | `tui/widgets/approval_card.py` (140 LOC) | ⚠ **widget EXISTS, not event-wired into live transcript** |
| 2 | CapabilityCardBanner | R-006 | `tui/widgets/capability_banner.py` (91 LOC) | ✅ exists, consumes `CAPABILITY_CARD_DECISION` |
| 3 | ActivityTray + McpDecisionBanner | R-008 | `tui/widgets/activity_tray.py` (137), `mcp_banner.py` (60) | ✅ exists, consumes `MCP_CALL_DECISION`, has `push_mcp_decision()` |
| 4 | PlanView | R-012 | `tui/views/plan_view.py` (84 LOC) | ✅ **DONE this sprint** (29a9cf0), 5 tests |
| 5 | Streaming | — | `tui/screen.py` | ✅ uses `is_streaming` flag (not the old static "Thinking…" string) |
| 6 | Sandbox-aware shell | audit §5 P0 | `tui/screen.py:_handle_shell_escape` | ✅ **DONE this sprint** (12c5afb), 4 tests |

### The ONE remaining gap (your primary task)

**ApprovalCard is built but not subscribed to the event bus.** When a
capability gate / paid-call gate / MCP outbound gate / HITL gate fires, the
`ApprovalCard` modal should mount in the live transcript with the decision
context + 4 buttons (`y` allow once / `a` always / `n` deny / `d` dry-run) +
the audit `correlation_id` footer (per `UX_AUDIT.md` R-007 + §12).

Today the gate decisions emit typed events (`CAPABILITY_CARD_DECISION`,
`MCP_CALL_DECISION`) but only `CapabilityCardBanner` + `ActivityTray` consume
them as inline banners. The full modal `ApprovalCard` flow (the §12 "universal
approval pattern") is not yet wired in `screen.py`.

---

## 5. Your review framework

Run these checks and report findings in the §7 format.

### Check 1 — Verify the 2 shipped R-UX2 pieces actually work
```bash
# Sandbox-aware shell
grep -n "decide\|SandboxPolicy\|shlex" python/src/agent_runtime_cockpit/tui/screen.py | head -8
cd python && uv run pytest tests/tui/test_sandbox_shell_escape.py -q
# expect 4 passed: read-only allowed, destructive blocked, untrusted blocked, network gated

# PlanView
cd python && uv run pytest tests/tui/test_plan_view.py -q
# expect 5 passed
```
If either fails → that's a regression in the in-flight work; surface it.

### Check 2 — Confirm the ApprovalCard gap is real (not already done)
```bash
grep -rn "ApprovalCard\|approval_card" python/src/agent_runtime_cockpit/tui/screen.py
# If EMPTY → gap confirmed: ApprovalCard not wired into screen
# If matches → re-scope; maybe partially wired

# What does ApprovalCard expose?
grep -n "def \|class \|BINDINGS\|def on_" python/src/agent_runtime_cockpit/tui/widgets/approval_card.py
```

### Check 3 — Confirm sandbox decision is CoSAI-clean
```bash
# The shell gate must be deterministic — no LLM call in the path
grep -n "openai\|anthropic\|llm\|complete(" python/src/agent_runtime_cockpit/tui/screen.py
# expect: no LLM imports in _handle_shell_escape
```
Per `docs/policy/cosai-llm-in-path.md`, the sandbox decision is a deterministic
classifier. Verify.

### Check 4 — Heuristic re-score
`UX_AUDIT.md` §6 scored the TUI at 39/100. After R-UX1 (Header + ContextMeter +
ModeBadge) and R-UX2 partial (sandbox shell, PlanView), several heuristics
should improve: H01 (system status), H05 (error prevention — sandbox), H18
(approval surface — partial). Re-score H01, H05, H14, H15, H18 and report the
delta. Be honest: only credit what's wired and tested, not what merely exists
as an unwired widget.

### Check 5 — No regressions
```bash
cd python && uv run pytest -q --ignore=tests/e2e --ignore=tests/integration 2>&1 | tail -3
# expect 5140 passed; pre-existing acceptable failures only:
#   test_concurrent_accumulation (SQLite env flake)
#   test_provider_statuses_fallback_to_stored_creds (env flake)
#   5 xfailed (2 CLI doctor, 1 CLI runs, 2 TUI snapshot SVG-hash)
```

---

## 6. The improvement task (after review)

Finish R-UX2 → Baseline Complete by wiring `ApprovalCard` into the live flow.

### Research first (mandatory — don't code from memory)
- **Codebase:** read `tui/widgets/approval_card.py` fully (its constructor,
  states, button handlers). Read `tui/widgets/approval_bar.py` (the HITL-only
  predecessor it's meant to replace — see how the old one writes to
  `HitlSqliteStore`). Read how `ActivityTray` subscribes to the event bus
  (`events/bus.py` `get_bus().subscribe(...)`).
- **Typed events:** read `protocol/typed_events.py` for `CapabilityCardDecisionEvent`
  + `McpCallDecisionEvent` payload shapes. Read `events/types.py` for the
  bus-internal `ArcEvent` subclasses.
- **Context7:** `/textualize/textual` — `push_screen`/`ModalScreen` for the
  modal approval flow; `Button` + `on_button_pressed` patterns.
- **Vercel grep:** search real `ModalScreen` approval/confireastern patterns
  with `def on_button_pressed` + `dismiss(` in Textual apps.

### Then implement (per `UX_AUDIT.md` R-007 + §12)
The universal approval pattern:
1. Gate decision fires → if `require_approval`, mount `ApprovalCard` modal.
2. Buttons: `[y]` allow once · `[a]` allow always · `[n]` deny · `[d]` dry-run · `[Esc]` deny.
3. Footer carries `audit=<mode>` and `correlation_id: <12-hex>`.
4. After decision, leave a thin chip in the transcript linking to the audit record.
5. Color rules (§12): allow=$success, warn=$warning, deny=$error, require_approval=$info.

### Constraints (non-negotiable)
- No LLM in the approval decision (CoSAI). The card *displays* a decision the
  deterministic engine already made; it does not *make* the decision.
- Additive only; don't break the existing `approval_bar.py` HITL path until the
  card fully replaces it (ship side-by-side, migrate, then retire).
- Every commit ships its own tests + green `uv run pytest -q`.
- Do NOT tag without explicit user go-ahead.

### Verification gates before reporting done
```bash
cd python
uv run ruff check src/agent_runtime_cockpit/tui tests/tui
uv run pytest tests/tui -q
uv run pytest -q --ignore=tests/e2e --ignore=tests/integration 2>&1 | tail -3
```

---

## 7. Report-back format

```
R-UX2 review:

✓ Verified working (with evidence):
  - <piece> — <test name> passed / <grep line cited>

⚠ Flagged:
  - <one-line-clarity items>

✗ Gap confirmed:
  - ApprovalCard not wired in screen.py (grep returned empty) — <plan>

Heuristic re-score (vs audit §6 baseline 39/100):
  - H01 system status: 1 → N (because <evidence>)
  - H05 error prevention: 1 → N (sandbox shell now routes through decide())
  - H18 approval surface: 1 → N (only if ApprovalCard wired+tested)
  - New estimated total: NN/100

Recommendation:
  - <finish ApprovalCard wiring | or surface a blocker>
```

Then, if you proceed to implement: one commit per logical change, each with
tests, on branch `spec/v0.8-r-ux2`. Report each commit SHA + test delta.

---

## 8. Pitfalls (from prior sessions — avoid)

1. **Designing instead of reading.** The spec (`UX_AUDIT.md`) is authoritative.
   Read `approval_card.py` before proposing how approvals should work — it's
   already built.
2. **Crediting unwired widgets as "done."** A widget that exists but isn't
   subscribed to the event bus is NOT shipped. Per honesty-over-polish, only
   credit wired + tested.
3. **Claiming test-pass without output.** Paste `uv run pytest` output.
4. **Re-evaluating locked decisions.** Hash-pinning (not Ed25519), OpenRouter
   primary, catalog-drives-UI-not-wire — all locked. Cite, don't re-open.
5. **Tagging without go-ahead.** Never.
6. **Slash commands meant for the user's CLI agent** (`/compact`, `/clear`) —
   if the user types one, ask before acting; it may not be for you.

---

## 9. What lands after R-UX2

- **R-UX3** (Planning Only): Components + IA — ToolCard rebuild, DiffViewer with
  hunk nav, SlashMenu category chips, CommandPalette rebuild, frontmatter-driven
  slash registry (eliminates HelpScreen drift). 2 weeks per audit §19 P2.
- **R-UX4** (Planning Only): Themes + A11y — 5 themes, NO_COLOR glyph fallback,
  reduced motion, pytest-textual-snapshot harness. 1 week per audit §19 P3.
- **R-OPEN-DEFERRED-RUNBOOKS**: half-day each, validate v0.4.1 persistence +
  R-01 wallet display semantics.
- **Phase 104+105** (deferred): microVM macOS hardening + Linux Firecracker
  host proof — the "original mandate," resumed after R-UX series or when
  Linux/KVM host access materializes.

Do not start any of these unless the user asks. Finish R-UX2 first.

---

## 10. Your first message (calibrated to the user's preferences)

```
Orientation complete. Cloned at <SHA>; on branch spec/v0.8-r-ux2.

Read:
  Policies: cosai-llm-in-path, local-first, protocol-additive-only, honesty-over-polish
  Design: UX_AUDIT.md (R-007 ApprovalCard, §12 universal approval pattern, §19 P1)
  Plan: roadmap.md R-UX2 row (Partial), phases.md reprioritization section

R-UX2 state I see:
  ✅ sandbox-aware shell (12c5afb) — !cmd routes through sandbox.decide()
  ✅ PlanView R-012 (29a9cf0) — read-only SimulationReport panel
  ✅ CapabilityBanner + ActivityTray widgets exist + consume their typed events
  ⚠ ApprovalCard (140 LOC) built but NOT wired into screen.py event flow

Please confirm state:
  git log --oneline main..spec/v0.8-r-ux2
  cd python && uv run pytest tests/tui/test_sandbox_shell_escape.py tests/tui/test_plan_view.py -q

Once confirmed, my plan: review the 3 in-flight commits, re-score the audit
heuristics that R-UX1+R-UX2 touched, then finish the ApprovalCard event wiring
(R-007 / §12) to take R-UX2 to Baseline Complete. I will NOT redesign the
approval flow — approval_card.py already defines it; I'll wire it.
```
