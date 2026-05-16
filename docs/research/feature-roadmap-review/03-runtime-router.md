# Runtime Router Review

## Current ARC Spec

ARC Studio's Runtime Router is a v0.2-reserved feature with only a suggestion card stub in v0.1. The current spec is distributed across four documents:

**From ARC_STUDIO_UX_SPEC.md:**
- §7.5: `/runtime` picker — CLI radio-button runtime selection with readiness badges (bundled/requires X/not installed/partial). Selected runtime applies to the session; `S` saves to `.arc/config.yaml`.
- §7.16: Router suggestion card (reserved v0.2) — Non-modal inline card: "This looks like UI work. HotLoop iterates faster here. Switch? [y/n/always for this project]". Default v0.2 mode: `suggest`. Modes: `manual`, `suggest`, `auto-on-confirm`, `auto`.
- §8.10: Router suggestion overlay (reserved v0.2) — IDE equivalent: non-modal card at top of Chat, dismissible, polite live region.
- Appendix A: Runtime manifest format — Per-runtime YAML with `eligibility_signals`, `prompt_signals`, `cost_signals`, `capabilities`, `panel_slots`, `slot_preferences`.

**From CLI_IDE_REDESIGN_PLAN.md:**
- §2.4: `/runtime` slash command wraps `arc run --runtime`.
- §3.4: Runtime switching UX — Config tab (radio), Chat tab (dropdown above input), Status bar (always visible).
- §4.4: `SessionRuntime` class for per-session override on top of config default.

**From IMPLEMENTATION_PLAN.md:**
- Runtime router exists today in `runtime_router.py` with `AUTO_PRIORITY = ("swarmgraph", "langgraph", "crewai", "lmarena")`.
- `resolve()` supports explicit, auto, and combo (sequential multi-adapter) modes.
- Adoption modes use `<runtime>+swarmgraph` syntax but are explicitly not wired to the router yet.

**From ADR-007:**
- Provider routing is separate from runtime routing. ARC manages metadata/policy; SwarmGraph gateway manages execution. No runtime-level routing logic in ADR-007.

**Current implementation (`runtime_router.py`):**
- Pure backend resolution: explicit runtime ID, auto-priority walk, or combo sequence.
- No prompt analysis, no eligibility scoring, no cost-aware routing, no suggestion logic.
- `AUTO_PRIORITY` is hardcoded, not manifest-driven.
- Adoption runtimes are parsed but always raise `RuntimeNotRunnable`.

**Summary:** The spec reserves router UX for v0.2 but the backend router already exists with hardcoded auto-selection. There is no manifest-driven routing, no prompt-signal analysis, no cost-awareness, and no suggestion engine. The gap between current backend behavior and the v0.2 spec is large.

---

## Comparable Products / Research

| Product | Router Type | How It Works | Manual Override | Auto-Suggest | Cost-Aware | Signal Sources |
|---|---|---|---|---|---|---|
| **Cursor** | Model routing | Dropdown above chat input; per-session selection; settings file for default | Yes, dropdown + settings | No | No (subscription-based) | User choice only |
| **OpenCode** | Model switching | `-m` flag, config file, `/model` slash command | Yes, all surfaces | No | No | User choice only |
| **VS Code Copilot** | Model selection | Dropdown in chat; configurable via settings; supports multiple providers | Yes, dropdown | No | No | User choice only |
| **Claude Code** | Model switching | `/model` command, `--model` flag, `ANTHROPIC_MODEL` env, `settings.json` model key; `availableModels` restriction | Yes, all surfaces | No | No (subscription/API) | User choice, managed policy |
| **LangGraph Studio** | Runtime selection | Graph/chat mode toggle; checkpoint-based replay; no multi-runtime switching | Yes, mode toggle | No | No | User choice |

**Key observations:**

1. **No competitor does auto-routing.** Every product uses manual model/runtime selection. Cursor, OpenCode, Copilot, and Claude Code all require explicit user choice via dropdown, slash command, or config. None analyze prompt intent to suggest a different model.

2. **Cursor's agent mode is not routing.** Cursor toggles between Agent and Composer modes, but this is a permission/capability toggle, not a routing decision. The model stays the same.

3. **Claude Code's `/model` is the closest analogue.** It supports per-session switching via `/model`, CLI flag, env var, and settings — all manual. The `availableModels` setting lets admins restrict choices but doesn't auto-select.

4. **LangGraph Studio has no multi-runtime concept.** It operates exclusively on LangGraph graphs. The "mode" toggle is graph vs chat view, not runtime selection.

5. **No product has prompt-signal routing.** No competitor analyzes the user's prompt to recommend a different model or runtime. This is a greenfield opportunity for ARC Studio — but also a risk of overengineering.

6. **Cost awareness is absent everywhere.** Cursor and Copilot hide cost behind subscriptions. Claude Code shows API usage but doesn't route based on it. No product says "this prompt would be cheaper on model X."

**Source URLs:**
- Claude Code settings: https://docs.anthropic.com/en/docs/claude-code/settings
- Claude Code overview: https://docs.anthropic.com/en/docs/claude-code/overview
- Cursor docs: https://docs.cursor.com/

---

## Gaps

1. **No manifest-driven routing.** `AUTO_PRIORITY` is hardcoded in `runtime_router.py:21`. The runtime manifest format (Appendix A) defines `eligibility_signals`, `prompt_signals`, and `cost_signals` but the router ignores them entirely.

2. **No prompt analysis.** The spec describes `prompt_signals` (verbs, patterns) per runtime manifest, but no code parses user prompts against these signals. The router has zero awareness of what the user is asking.

3. **No eligibility scoring.** `eligibility_signals` in manifests (e.g., `files_match: ["**/*swarm*.py"]`) are defined but never evaluated by the router. Detection happens in adapters' `detect()` method, not in a unified eligibility layer.

4. **No cost-aware routing.** `cost_signals` (`paid_provider_required`, `shell_required`) exist in manifests but the router only checks `requires_paid_calls` as a binary gate, not as a ranking factor.

5. **No suggestion engine.** The v0.2 spec describes a suggestion card ("This looks like UI work. HotLoop iterates faster here.") but no backend code generates suggestions. The entire suggestion pipeline is missing.

6. **No router mode implementation.** The spec defines four modes (`manual`, `suggest`, `auto-on-confirm`, `auto`) but only `manual` (explicit) and a crude `auto` (hardcoded priority) exist. `suggest` and `auto-on-confirm` are not implemented.

7. **No "always for this project" persistence.** The suggestion card spec includes `[y/n/always for this project]` but there's no storage for per-project routing preferences.

8. **No panel slot preferences enforcement.** Manifests define `slot_preferences` (which panels open by default per runtime) but the IDE doesn't read or apply these.

9. **Combo mode is not adoption.** `ComboRuntimeAdapter` runs adapters sequentially and labels it "combo." The spec correctly separates combo from adoption, but the UX doesn't make this distinction visible.

10. **Adoption modes are dead code paths.** `AdoptionRegistry.parse_runtime_id()` parses `<runtime>+swarmgraph` but `resolve()` always raises `RuntimeNotRunnable` for adoption modes. The router cannot route to adoption runtimes.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **R1: Manifest-driven auto-priority** — Replace hardcoded `AUTO_PRIORITY` with manifest `eligibility_signals` scoring. Score each runtime by workspace file matches, detection confidence, and capability readiness. Sort by score. | Hardcoded priority cannot adapt to workspace context. Manifest signals exist but are unused. | v0.2 | Low. Scoring is deterministic; fallback to current behavior if manifest missing. | §7.5: Add "Auto-selection scores runtimes by manifest eligibility signals. See Appendix A." |
| **R2: Static prompt-signal matching** — Match user prompt against manifest `prompt_signals` (verbs, patterns) using simple keyword/regex matching. If a non-active runtime scores higher, emit suggestion card in `suggest` mode. | The spec reserves prompt_signals but no code uses them. Static matching is cheap and deterministic. | v0.2 | Low. Keyword matching is simple; false positives are harmless in `suggest` mode (user can decline). | §7.16: Add "Suggestions are generated by matching prompt against runtime manifest prompt_signals. LLM-based analysis is reserved for v0.3." |
| **R3: Router mode config** — Add `router.mode` to `.arc/config.yaml` with values `manual`/`suggest`/`auto-on-confirm`/`auto`. Default: `manual` in v0.1, `suggest` in v0.2. | The spec defines four modes but only two exist (manual + crude auto). Mode must be configurable. | v0.2 | Low. Mode is a config flag; behavior changes are additive. | §8.6 Config: Add "Router tab with mode selector (manual/suggest/auto-on-confirm/auto)." §7.13: Add router mode to policy.yaml. |
| **R4: Cost-aware ranking** — When multiple runtimes are eligible, factor `cost_signals` into ranking. Prefer runtimes with `paid_provider_required: false` when cost sensitivity is high (session cost > threshold). | The spec defines cost_signals but router ignores cost. Users care about cost. | v0.2 | Medium. Cost estimates are approximate; ranking by cost could override better-fit runtime. | Appendix A: Add `cost_sensitivity` field to manifest. §7.16: Add "Cost is a tiebreaker, not primary signal." |
| **R5: "Always for this project" persistence** — Store per-project routing preferences in `.arc/router-prefs.yaml`. Keys: `preferred_runtime`, `declined_suggestions[]`, `auto_switch_rules[]`. | The suggestion card spec includes "always for this project" but no storage exists. | v0.2 | Low. Simple YAML file; no security implications. | §7.16: Add "Always-for-project writes to .arc/router-prefs.yaml." |
| **R6: Panel slot enforcement** — Read manifest `slot_preferences` and auto-open/close panels when runtime switches. E.g., HotLoop opens Device+Frames, closes Graph. | Manifests define slot_preferences but IDE ignores them. Runtime switching should adapt the UI. | v0.2 | Low. Panel open/close is non-destructive; user can override. | §8.10: Add "Runtime switch applies manifest slot_preferences to panel layout." |
| **R7: Adoption routing** — Wire `AdoptionRegistry` into `resolve()` so `<runtime>+swarmgraph` modes are routable when adoption runners are ready. | Adoption modes are parsed but always raise. Router must support adoption once P2 integrations land. | v0.2 | Medium. Adoption routing depends on P2 integration readiness; router changes must not break standalone modes. | §7.5: Add "Adoption modes (e.g., langgraph+swarmgraph) appear in /runtime picker when ready." |
| **R8: LLM-based prompt analysis (reserved)** — Send prompt to LLM for task-type classification and runtime recommendation. Only used when static matching is ambiguous. | Static keyword matching has limits. LLM can understand nuance (e.g., "fix the UI" vs "orchestrate agents"). | v0.3 | High. Adds latency, cost, and complexity. Must not block the run flow. | §7.16: Add "LLM-based analysis is v0.3. v0.2 uses static matching only." |
| **R9: Router health indicator** — Status bar segment showing router mode and confidence. E.g., `Router: suggest (confident)` or `Router: manual`. | User should know what router mode is active and whether suggestions are being generated. | v0.2 | Low. Status segment is read-only. | §7.14: Add "Router mode segment in status line." |
| **R10: Eligibility signal debugging** — `/doctor runtime` shows per-runtime eligibility scores, prompt signal matches, and why each runtime was selected or skipped. | Router decisions are opaque. Users need to understand why a runtime was chosen. | v0.2 | Low. Diagnostic output only. | §7.10: Add "Router eligibility scores in /doctor output." |

---

## Recommended Decisions

### 1. Router is static/rule-based in v0.2. LLM delegation is v0.3.

**Decision:** All v0.2 routing logic uses deterministic rule-based matching:
- Eligibility: workspace file patterns, detection confidence, capability readiness
- Prompt signals: keyword/regex matching against manifest `verbs` and `patterns`
- Cost: binary gate (`paid_provider_required`) + tiebreaker ranking
- Mode: config-driven (`manual`/`suggest`/`auto-on-confirm`/`auto`)

**Why:** No competitor does LLM-based routing. Static matching is cheap, fast, auditable, and sufficient for v0.2 where only 2-3 runtimes are realistically viable (SwarmGraph + maybe LangGraph). LLM classification adds latency (1-3s), cost ($0.001-0.01 per call), and opacity to a decision the user should understand.

**What to delegate to LLM later (v0.3):**
- Ambiguous prompt classification when static signals tie
- Cross-runtime task decomposition ("this has both backend and UI parts")
- Learning from user overrides (if user always declines HotLoop suggestions, adjust weights)

### 2. Router never auto-switches without confirmation in v0.2.

**Decision:** `auto` mode is defined but **disabled by default** in v0.2. Default is `suggest`. `auto-on-confirm` requires explicit per-phase approval. `auto` (fully automatic) requires explicit opt-in and a warning.

**Why:** Runtime switching changes execution semantics, cost profile, and audit guarantees. Silent auto-switching would violate the "honest" and "bounded" brand attributes (§1.3). Users must understand and approve runtime changes, especially when:
- Switching from bundled (free) to paid-provider runtime
- Switching from standalone to adoption mode (changes audit semantics)
- Switching mid-session (changes active run behavior)

### 3. SwarmGraph remains the default and bundled runtime. Router does not override this.

**Decision:** `AUTO_PRIORITY` always starts with SwarmGraph. Even if eligibility scoring favors another runtime, SwarmGraph is the default when no explicit user choice exists. Suggestions can recommend alternatives, but the default never changes without user action.

**Why:** SwarmGraph is the only bundled runtime with zero external dependencies. It's the safe baseline. Changing the default would break user expectations and could introduce unexpected costs.

### 4. Router suggestions are non-modal and dismissible. Never focus-stealing.

**Decision:** Suggestion cards use `role=status` with polite live region (as spec says). They never steal focus, never block input, and never auto-apply. User can dismiss with no consequence.

**Why:** Focus-stealing suggestions would be worse than no suggestions. The user is mid-conversation; interrupting them breaks flow. This matches the spec (§8.10) but needs to be explicit in implementation.

### 5. Cost is a tiebreaker, not a primary routing signal.

**Decision:** Router ranks by eligibility/prompt-fit first, then uses cost as a tiebreaker when scores are within 10%. Cost never overrides a clearly better-fit runtime.

**Why:** Overweighting cost would route users to cheaper but wrong runtimes. A $0.01 SwarmGraph run that produces wrong results is worse than a $0.08 LangGraph run that's correct. Cost matters but is secondary to fit.

### 6. "Always for this project" is workspace-scoped, not global.

**Decision:** Per-project routing preferences live in `.arc/router-prefs.yaml` (workspace-scoped). They do not affect other workspaces. User can clear them from `/config > Router`.

**Why:** Routing preferences are workspace-specific. A UI project should prefer HotLoop; a backend project should prefer SwarmGraph. Global preferences would be wrong across diverse workspaces.

---

## Specific Spec Edits

### ARC_STUDIO_UX_SPEC.md

- **§0.5 (Out Of Scope):** Change "Router: Suggestion-based runtime switching deferred to v0.2" to "Router: Suggestion-based runtime switching deferred to v0.2. Static eligibility scoring is v0.2 foundation."

- **§7.5 (/runtime Picker):** Add paragraph after existing content:
  > "Auto-selection scores runtimes by manifest `eligibility_signals` (workspace file patterns, detection confidence, capability readiness). The highest-scoring runnable runtime is selected when no explicit choice exists. Run `/doctor runtime` to see eligibility scores."

- **§7.16 (Router Suggestion Card):** Add after existing content:
  > "Suggestions are generated by matching the user's prompt against runtime manifest `prompt_signals` using static keyword/regex matching. LLM-based prompt analysis is reserved for v0.3. Cost signals are used as tiebreakers only, not primary routing factors. 'Always for this project' writes to `.arc/router-prefs.yaml`."

- **§7.16 (Router modes):** Add mode definitions:
  > - `manual`: No suggestions. User switches via `/runtime` only. Default for v0.1.
  > - `suggest`: Non-modal suggestion card when a non-active runtime scores higher. User must accept. Default for v0.2.
  > - `auto-on-confirm`: Auto-switch at phase boundaries with explicit confirmation. Requires planner integration.
  > - `auto`: Fully automatic switching. Requires explicit opt-in and warning. Not recommended.

- **§8.6 (Config):** Add "Router" tab:
  > "Router tab: mode selector (manual/suggest/auto-on-confirm/auto), per-project preferences, eligibility signal viewer. Save writes `.arc/config.yaml` for mode and `.arc/router-prefs.yaml` for project preferences."

- **§8.10 (Router Suggestion Overlay):** Add:
  > "Runtime switch applies manifest `slot_preferences` to panel layout. E.g., HotLoop opens Device+Frames panels and closes Graph."

- **§10.7 (Planner, Router, Handoff Copy):** Add:
  > | Router mode manual | `Routing is manual. Use /runtime to switch.` |
  > | Router mode suggest | `Router will suggest runtimes. Accept or decline suggestions.` |
  > | Router mode auto-on-confirm | `Router auto-switches at phase boundaries with confirmation.` |
  > | Router mode auto | `Router auto-switches without confirmation. Use /config to change.` |

- **Appendix A (Runtime Manifest):** Add `router_config` section:
  ```yaml
  router_config:
    eligibility_weight: 1.0        # Weight for eligibility scoring (0-1)
    prompt_signal_weight: 0.8      # Weight for prompt signal matching (0-1)
    cost_weight: 0.3               # Weight for cost ranking (0-1, tiebreaker only)
    min_suggestion_threshold: 0.6  # Minimum score delta to trigger suggestion
  ```

### CLI_IDE_REDESIGN_PLAN.md

- **§2.4 (Slash Commands):** Add `/router` command:
  > | `/router` | Show router mode and eligibility scores | New: router status display |
  > | `/router mode <mode>` | Set router mode | New: router mode switch |

- **§3.4 (Runtime Switching UX):** Add:
  > "Router mode is visible in status bar. Clicking router segment opens Config > Router tab."

- **§4.4 (Runtime-Selection Abstraction):** Add `RouterMode` to `SessionRuntime`:
  ```python
  class SessionRuntime:
      def __init__(self, config: ArcConfig):
          self.config = config
          self.override: str | None = None
          self.router_mode: Literal["manual", "suggest", "auto-on-confirm", "auto"] = "suggest"
  ```

### IMPLEMENTATION_PLAN.md

- **P3 (Theia UX Productization):** Add router item:
  > | Router mode UI | User can see and change router mode | `packages/arc-extension` components | P2 router backend | Add router mode selector in Config tab, status bar segment, suggestion card component | UI contract tests | Suggestion timing and focus management |

- **P2 (Runtime + SwarmGraph Integrations):** Add router backend item:
  > | Router backend | Manifest-driven eligibility scoring and prompt-signal matching | `runtime_router.py`, new `router_suggestion.py` | Runtime manifests, adoption registry | Add `score_eligibility()`, `match_prompt_signals()`, `generate_suggestion()`; mode-driven behavior | Unit tests for scoring, matching, suggestion generation | Scoring weights may need tuning |

---

## Acceptance Criteria

### v0.1 (Reservations Only)
- [ ] Router suggestion card component exists as stub/disabled in IDE
- [ ] Router mode config key exists in `.arc/config.yaml` schema (default: `manual`)
- [ ] Runtime manifest format includes `eligibility_signals`, `prompt_signals`, `cost_signals` (already exists in Appendix A)
- [ ] No suggestion logic executes; router is manual-only
- [ ] `/runtime` picker shows all runtimes with readiness badges
- [ ] Status bar shows active runtime (already exists)

### v0.2 (Router Foundation)
- [ ] `AUTO_PRIORITY` replaced with manifest-driven eligibility scoring
- [ ] `score_eligibility(workspace, manifest)` returns float score per runtime
- [ ] `match_prompt_signals(prompt, manifest)` returns float score per runtime
- [ ] `generate_suggestion(prompt, workspace, active_runtime, all_runtimes)` returns suggestion or None
- [ ] Router mode config works: `manual`/`suggest`/`auto-on-confirm`/`auto`
- [ ] `suggest` mode: non-modal suggestion card appears when non-active runtime scores > threshold higher
- [ ] Suggestion card actions work: Accept (switches runtime), Decline (dismisses), Always for project (writes `.arc/router-prefs.yaml`)
- [ ] `auto-on-confirm` mode: auto-switches at phase boundaries with confirmation (requires planner)
- [ ] `auto` mode: fully automatic switching with explicit opt-in warning
- [ ] Panel slot preferences applied on runtime switch
- [ ] `/doctor runtime` shows per-runtime eligibility scores
- [ ] Status bar shows router mode segment
- [ ] Cost is tiebreaker only (documented and tested)
- [ ] All suggestion text matches §10.7 spec exactly
- [ ] Unit tests for: eligibility scoring, prompt matching, suggestion generation, mode behavior, cost tiebreaking
- [ ] Contract tests for: suggestion card, router mode selector, status segment

### v0.3 (LLM-Enhanced Routing)
- [ ] LLM-based prompt classification available as opt-in
- [ ] Ambiguous prompts (static score tie) trigger LLM classification
- [ ] User overrides feed into suggestion weight adjustment
- [ ] Cross-runtime task decomposition suggestions

---

## Reject / Do Not Build

| Idea | Why Rejected |
|---|---|
| **LLM-based routing in v0.2** | Adds latency (1-3s), cost ($0.001-0.01/call), and opacity to a decision users should understand. Static matching is sufficient for v0.2 where 2-3 runtimes are viable. Defer to v0.3. |
| **Fully automatic routing as default** | Violates "honest" and "bounded" brand attributes. Runtime switching changes execution semantics, cost, and audit guarantees. Users must approve. |
| **Cost-primary routing** | Would route users to cheaper but wrong runtimes. Cost is a tiebreaker, not primary signal. A cheap wrong result is worse than a correct expensive one. |
| **Global "always" preferences** | Routing preferences are workspace-specific. A UI project prefers HotLoop; a backend project prefers SwarmGraph. Global preferences would be wrong across diverse workspaces. |
| **Focus-stealing suggestion modal** | Interrupts user mid-conversation. Suggestion cards must be non-modal and dismissible without focus theft. |
| **Auto-switching mid-run** | Runtime switching should only happen between runs or at phase boundaries. Switching mid-run would corrupt execution state and break audit continuity. |
| **Router-based provider selection** | Provider routing is separate from runtime routing (ADR-007). Router selects runtime; provider gateway selects inference provider. Do not conflate. |
| **Router for LlamaIndex/LM Arena in v0.1** | Both are hidden from default UI in v0.1. Router should not suggest hidden runtimes. |
| **Real-time prompt streaming to router** | Router analyzes the complete prompt after submission, not streaming tokens. Streaming analysis adds complexity with no benefit for suggestion accuracy. |
| **Router A/B testing framework** | Premature. Router is v0.2; A/B testing requires production traffic and metrics infrastructure that doesn't exist yet. |
| **Router learning from failures** | If a runtime fails, the router should not automatically deprioritize it without understanding why. Failures may be transient (network, quota) not intrinsic to the runtime. |
