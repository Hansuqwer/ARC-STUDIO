# Provider Keys / Cost Review

**Date:** 2026-05-16
**Scope:** v0.1–v0.3 provider key management, cost display, paid-call gating, budget controls
**Owner:** TBD
**Status:** Review draft

---

## Current ARC Spec

### Provider Key Storage (ARC_STUDIO_UX_SPEC.md §7.4, §8.6, §9 KeyBadge, §10.10)

ARC Studio specifies a four-tier key provenance model:

| Source | Priority | Description |
|--------|----------|-------------|
| `env` | 1 (highest) | Environment variable (e.g. `ANTHROPIC_API_KEY`) detected at runtime |
| `keyring` | 2 | OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Locker) via Python `keyring` library |
| `file` | 3 | Config file reference (not the key itself — a pointer to env var name) |
| `unset` | 4 | No key configured for this provider |

**Current implementation status:**

- **Keyring:** Partially implemented. `AuditKeyManager` in `python/src/agent_runtime_cockpit/audit/key_manager.py` uses the `keyring` library for HMAC audit key storage with env fallback. Provider keys themselves are **not yet stored in keyring** — `ProviderAccountStore.add_direct_key_account()` raises `RuntimeError("Direct key storage requires a secure OS keychain backend; use --api-key-env.")` [providers.py:118].
- **Env var override:** Fully implemented. `ProviderAccountStore.add_env_account()` stores env var references (not keys) in `~/.arc/providers.json` [providers.py:95-115].
- **Key provenance display:** Specified in §9 `KeyBadge` component with states `env`, `keyring`, `file`, `unset`. Not yet implemented in frontend.
- **Redaction:** `Redactor` class in `security/redaction.py` strips API keys, bearer tokens, passwords, AWS keys, GitHub tokens, OpenAI/Anthropic keys from all outputs. §10.10 specifies a universal redaction contract across CLI, IDE, SSE, logs.

### Cost Display (ARC_STUDIO_UX_SPEC.md §7.2, §7.9, §7.11, §7.14, §9 CostMeter/CostCeilingBadge)

**Specified cost surfaces:**

1. **Status line** (§7.14): `cost $X.XX` segment with color thresholds: `text.secondary` at ≤$1, `state.warning` at >$5, `state.danger` at >$20, `cost ?` when unknown.
2. **`/status` command** (§7.9): Shows `Session cost total $0.04 | last paid call $0.04 | active ceiling none`.
3. **Runs table** (§7.11, §8.5): `Cost` column in run summaries. `RunSummary.costUsd` can be `number | 'unknown'`.
4. **Paid-call confirmation** (§7.2, §10.3): Card showing provider, model, estimated ceiling, approval buttons. Copy: `This may call {provider}. Session total so far: ${total}. This call adds up to ${ceiling}. Continue?`
5. **CostCeilingBadge** (§9): Shows estimated min/max cost with approval state. Unknown maximum renders `cost ?` with confirmation copy.

**Current implementation status:**

- Cost display: **Not implemented** in frontend. No `CostMeter` or `CostCeilingBadge` components exist.
- Paid-call confirmation: **Specified but not wired**. `RunProfile.allow_paid_calls` exists [profiles.py:13] and gating logic exists, but no UI confirmation flow.
- Session cost tracking: **Not implemented**. No session-level cost accumulator exists.
- Run cost tracking: **Partially specified**. `RunSummary` schema includes `costUsd` field but no backend populates it.
- Quota display: `ProviderQuotaStore` exists [providers.py:176-200] with daily request counters. Not exposed in UI.

### Paid-Call Gating (ARC_STUDIO_UX_SPEC.md §7.13, §10.3)

The spec defines three permission modes with paid-call behavior:

| Mode | Paid calls | Writes | Trust changes |
|------|-----------|--------|---------------|
| Plan | Blocked | Blocked | Blocked |
| Build | Ask | Ask | Ask |
| Auto | Policy (`ask`/`auto`/`deny`) | Policy | Deny (even in Auto) |

Policy lives in `.arc/policy.yaml` (project) and `~/.config/arc-studio/policy.yaml` (user) with project > user > built-in precedence. Project policy cannot weaken user policy for `shell_exec` or `trust_changes`.

**Current implementation:** `RunProfile` dataclass [profiles.py:9-18] with `allow_paid_calls` flag. `enforce_profile()` raises `GatingError` if profile doesn't allow paid calls. No UI confirmation dialog exists.

### Provider Status Display (ARC_STUDIO_UX_SPEC.md §7.4, §7.9)

The `/providers` form shows a table with columns: Provider, State, Source, Default model, Action. Each provider has a key state chip (`keyring`, `env`, `file`, `unset`). The `/status` command shows `Keys Anthropic ✓ keyring | OpenAI ✓ env | Google ✗ unset`.

**Current implementation:** `ProviderStatus` model [providers.py:36-44] with `api_key_configured` and `api_key_source` fields. CLI commands `arc providers list/status` exist. No IDE provider manager panel exists.

### ADR-007: Provider Routing Unification

ADR-007 establishes a clear separation:

- **ARC layer:** Metadata and policy only. Stores env var references, routing policy, quota display. Never makes inference calls.
- **SwarmGraph Gateway layer:** Execution. Handles actual inference routing, 12+ provider adapters, encrypted vault (Fernet), semantic cache, quota tracking.

ARC passes resolved provider info to gateway via env vars. ARC reads quota from gateway API when available. No duplicate secret storage — ARC references, gateway stores encrypted.

---

## Comparable Products / Research

### Provider Setup

| Product | Key storage method | Setup flow | Multi-provider | Local providers | Key provenance display |
|---------|-------------------|------------|----------------|-----------------|----------------------|
| **Claude Code** | Subscription auth (Claude.ai login) or `ANTHROPIC_API_KEY` env var | Login on first use (OAuth) or set env var | No (Anthropic only, plus Bedrock/Vertex/Foundry via env vars) | No | No — `/status` shows auth method but not granular provenance |
| **Codex CLI** | `OPENAI_API_KEY` env var | Set env var before launch | No (OpenAI only) | No | No |
| **OpenCode** (archived → Crush) | Env vars or JSON config file (`providers.*.apiKey`) | Set env vars or edit `.opencode.json` | Yes (8 providers: OpenAI, Anthropic, Gemini, Bedrock, Groq, Azure, Vertex, OpenRouter) | Yes (`LOCAL_ENDPOINT` for self-hosted) | No — provider list in model dialog, no key status |
| **Cursor** | Built-in subscription or own API key in Settings | Settings > Models > add API key | Yes (OpenAI, Anthropic, Google, plus custom OpenAI-compatible) | Yes (custom endpoint) | Partial — shows configured/not-configured in settings |
| **Aider** | Env vars, `.env` file, or `.aider.conf.yml` | Set env vars or edit config file | Yes (15+ providers) | Yes (Ollama, LM Studio, OpenAI-compatible) | No — no key status display |
| **VS Code Copilot** | GitHub OAuth (built-in) | Sign in to GitHub | No (Microsoft/OpenAI only) | No | N/A — no key management |

**Key observations:**

1. **No competitor uses OS keyring for provider keys.** Claude Code uses OAuth subscription. OpenCode stores keys in JSON config (plaintext). Aider uses env vars / `.env` files. Cursor stores keys in settings (encrypted at rest on disk).
2. **Env vars are the universal baseline.** Every product that supports multiple providers accepts standard env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.).
3. **No competitor shows key provenance.** No product displays whether a key came from env, keyring, or file. ARC's four-tier provenance model is unique.
4. **Local provider support is common.** OpenCode, Cursor, and Aider all support Ollama or custom OpenAI-compatible endpoints. ARC's spec includes Ollama (`OL` badge) but implementation is thin.
5. **Claude Code's `/status`** shows connection status and model but not cost or key provenance granularly.

### Cost Display

| Product | Session cost | Run cost | Per-call estimate | Cost ceiling | Unknown cost handling |
|---------|-------------|----------|-------------------|--------------|----------------------|
| **Claude Code** | No (subscription-based) | No | No | No | N/A |
| **Claude Code (Console/API key)** | No | No | No | No | Usage dashboard on console.anthropic.com |
| **Codex CLI** | No | No | No | No | Usage dashboard on platform.openai.com |
| **OpenCode** | No | No | No | No | No cost tracking |
| **Cursor** | No | No | No | No | Usage in account settings (subscription) |
| **Aider** | Yes (shows token usage per message) | No | No | No | Shows `?` when cost unknown |
| **VS Code Copilot** | N/A (subscription) | N/A | N/A | N/A | N/A |

**Key observations:**

1. **No competitor shows real-time cost in status line.** Aider is the closest — it shows token counts per message but not dollar amounts.
2. **No competitor has per-call cost estimates or ceilings.** ARC's `CostCeilingBadge` with min/max estimates is unique in the market.
3. **Subscription products hide cost entirely.** Claude Code, Cursor, Copilot all use subscription pricing — users don't see per-call costs.
4. **API-key products defer to dashboards.** OpenAI Console, Anthropic Console, and cloud providers (Bedrock, Vertex) show costs on web dashboards, not in CLI.
5. **Unknown cost is a real problem.** No product handles "unknown cost" gracefully. ARC's `cost ?` state with explicit confirmation (`Estimated cost: unknown. {provider} does not report estimates. Continue with no ceiling?`) is a competitive differentiator.

### Paid-Call Confirmation

| Product | Pre-call confirmation | Permission modes | Budget ceiling | Auto-approve option |
|---------|----------------------|-----------------|----------------|-------------------|
| **Claude Code** | No (subscription) | 5 permission modes + Shift+Tab | No | Yes (auto mode) |
| **Codex CLI** | No | Approval + sandbox modes | No | Yes |
| **OpenCode** | No | Permission dialog per tool call | No | Yes (allow for session) |
| **Cursor** | No | Agent/Edit modes | No | Yes |
| **Aider** | No | `--yes-always` flag | No | Yes |
| **VS Code Copilot** | No | Chat/Agent/Edit | No | Yes |

**Key observations:**

1. **No competitor asks before paid API calls.** All products either use subscription (no per-call cost) or assume the user accepts costs when they set an API key.
2. **ARC's paid-call confirmation is unique.** The spec's paid-call card (§7.2) with provider, model, ceiling, and approve/reject buttons has no direct competitor equivalent.
3. **Permission modes are universal.** Every competitor has some form of Plan/Build/Auto or read-only/edit modes. ARC's three-mode model (Plan/Build/Auto) aligns with the market.
4. **Budget ceilings don't exist in competitors.** No product has session-level or run-level budget ceilings. This is a gap ARC can own.

---

## Gaps

### Critical Gaps (v0.1 blockers)

1. **Keyring not implemented for provider keys.** `add_direct_key_account()` raises `RuntimeError`. Only env-var references work. The spec promises keyring storage but the implementation is missing. The `keyring` library is used for HMAC audit keys but not for provider API keys.

2. **No cost tracking backend.** No session cost accumulator, no run cost computation, no per-call estimate. `RunSummary.costUsd` exists in schema but nothing populates it. The entire cost display surface (status line, `/status`, Runs table, CostMeter, CostCeilingBadge) has no backend data source.

3. **No paid-call confirmation UI.** `RunProfile.allow_paid_calls` and `GatingError` exist but no confirmation dialog in CLI or IDE. Paid calls are either fully blocked (stub profile) or fully allowed (gateway profile) with no interactive approval.

4. **No provider test command.** The spec shows `[test]` action for Ollama in `/providers` form (§7.4) but no `arc providers test` CLI command exists. Users cannot verify a key works before running a workflow.

5. **Keyring platform behavior unvalidated.** The `keyring` library is imported conditionally with broad `except Exception` [key_manager.py:96-98]. No platform-specific tests exist for macOS Keychain, Linux Secret Service, or Windows Credential Locker. Headless/SSH environments may fail silently.

### High-Priority Gaps (v0.1 should-have)

6. **No local provider (Ollama) detection or test flow.** The spec includes Ollama with `○ local` state and `[test]` action, but no Ollama health check or model listing exists.

7. **No quota display in UI.** `ProviderQuotaStore` exists with daily counters but is not exposed in any UI surface. ADR-007 specifies ARC reads quota from SwarmGraph gateway API, but this is not wired.

8. **No session cost accumulator.** Session-level cost tracking requires accumulating per-run costs. No session-level cost state exists in the session lifecycle (§7.14.1).

9. **Cost estimate source undefined.** The spec references `estimatedCeilingUsd` but doesn't specify where estimates come from. Provider APIs don't return pre-call cost estimates. Token estimation requires local tokenizer or provider-specific heuristics.

10. **Redaction patterns incomplete.** `security/redaction.py` covers common patterns but misses: Azure keys (`AZURE_OPENAI_API_KEY`), Google service account JSON, Bedrock session tokens, OpenRouter keys, generic `sk-` prefixed keys from non-OpenAI providers.

### Medium-Priority Gaps (v0.2)

11. **No budget ceiling enforcement.** The spec mentions `active ceiling` in `/status` and `CostCeilingBadge` but no ceiling configuration or enforcement exists. No `session_max_cost` or `run_max_cost` settings.

12. **No cost history or trends.** Runs table shows per-run cost but no aggregate view, no cost-over-time chart, no per-provider breakdown.

13. **No token count display.** Aider shows token usage per message. ARC doesn't show input/output token counts anywhere in v0.1 spec.

14. **SwarmGraph gateway quota integration not wired.** ADR-007 specifies ARC reads quota from gateway API but the integration path is documented, not implemented.

15. **No provider health check.** No `arc providers test` or `arc providers health` command to verify connectivity, key validity, rate limit status, or available models.

### Low-Priority Gaps (v0.3+)

16. **No cost alerting.** No notification when session cost exceeds threshold.
17. **No multi-key support per provider.** Single key per provider. No key rotation or per-project key isolation.
18. **No cost export.** No `arc runs export --include-cost` or CSV export with cost data.
19. **No cost comparison across providers.** No view comparing cost of same task across different providers/models.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|----------|-----|----------------|------|-----------|
| **P1: Implement keyring for provider keys** | Spec promises keyring storage; currently raises RuntimeError. Use the same `keyring` library pattern from `AuditKeyManager`. | v0.1 | Medium — `keyring` library behavior varies by platform; needs headless/SSH fallback testing | §7.4: Add keyring failure fallback copy. §9 KeyBadge: Add `keyring-unavailable` state. |
| **P2: Add `arc providers test` command** | Users need to verify keys work before running workflows. Every competitor implicitly validates on first use; ARC should validate explicitly. | v0.1 | Low — simple HTTP health check to provider API | §7.4: Add test result states (✓ valid, ✗ invalid, ⚠ rate-limited). §7.10: Add provider test to `/doctor`. |
| **P3: Add session cost accumulator (backend)** | Cost display surfaces need a data source. Start with a simple per-session sum of run costs. | v0.1 | Low — simple accumulator in session metadata | §7.9: Define session cost source. §7.14.1: Add `cost_usd` to session metadata schema. |
| **P4: Implement paid-call confirmation (CLI first)** | Core differentiator. No competitor has pre-call confirmation. CLI is simpler than IDE for v0.1. | v0.1 | Medium — requires blocking prompt in chat REPL flow | §7.2: Refine paid-call card copy. §7.13: Define auto-mode paid-call policy interaction. |
| **P5: Define cost estimate strategy** | `estimatedCeilingUsd` needs a source. Options: (a) hardcoded per-model estimates, (b) provider pricing API, (c) "unknown" with explicit confirmation. Recommend (c) for v0.1, (a) for v0.2. | v0.1 | Low — "unknown" is honest and safe | §9 CostCeilingBadge: Clarify that v0.1 always shows `cost ?` for paid providers. §10.3: Add unknown-cost confirmation copy. |
| **P6: Add Ollama detection and test** | Local providers are important for privacy-sensitive users and cost-free development. Spec includes Ollama badge but no detection. | v0.1 | Low — HTTP GET to `localhost:11434/api/tags` | §7.4: Define Ollama states (local-available, local-unavailable, local-no-models). |
| **P7: Expand redaction patterns** | Current patterns miss Azure, Google, Bedrock, OpenRouter keys. Security risk. | v0.1 | Low — add regex patterns | §10.10: Add complete pattern list to redaction contract. |
| **P8: Add budget ceiling configuration** | Users need to cap spending. No competitor has this — it's a differentiator. | v0.2 | Medium — requires enforcement in run path and clear UX for ceiling exceeded | §7.9: Add ceiling config to `/status`. §9: Add `CostCeilingBadge` exceeded state. §10.3: Add ceiling-exceeded confirmation copy. |
| **P9: Add per-run cost to RunRecord** | Runs table needs cost data. Add `cost_usd` field to `RunRecord` schema and populate from provider response metadata. | v0.1 | Low — schema addition, population depends on provider response parsing | §8.5: Define how run cost is computed. §7.11: Add cost column source. |
| **P10: Wire SwarmGraph gateway quota display** | ADR-007 specifies ARC reads quota from gateway. Need to implement the read path and display in `/providers` and `/status`. | v0.2 | Medium — depends on gateway API stability | §7.4: Add quota column to providers table. §7.9: Add quota to `/status`. |
| **P11: Add token count display in Runs** | Token counts are more useful than cost for debugging and optimization. Aider shows them. | v0.2 | Low — add `input_tokens`/`output_tokens` to RunSummary | §7.11: Add token columns to runs table. §9 RunSummary: Add token fields. |
| **P12: Add cost alerting** | Notify when session cost exceeds user-defined threshold. | v0.3 | Low — threshold check + toast notification | §7.14: Add cost alert segment. §9 Toast: Add cost alert variant. |
| **P13: Keyring platform validation spike** | Test `keyring` library on macOS, Linux (with/without desktop), Windows, headless SSH. Document failure modes. | v0.1 | Medium — may reveal keyring is unreliable on some platforms | §7.4: Add platform-specific keyring guidance. §9 KeyBadge: Add degraded states. |
| **P14: Add `/providers test` to IDE** | Mirror CLI test in IDE provider manager panel. | v0.2 | Low — button + spinner + result display | §8.6: Add test button to Providers tab. |
| **P15: Add cost history view** | Aggregate cost over time, per-provider breakdown, trends. | v0.3 | Medium — requires cost data accumulation and chart component | New section in spec for cost dashboard. |

---

## Recommended Decisions

### Decision 1: Keyring is v0.1 required, but with explicit fallback

**Lock:** Provider keyring storage ships in v0.1. If `keyring` library fails (headless SSH, missing daemon, platform incompatibility), fall back to env-var-only mode with visible degraded status. Never fall back to plaintext file storage.

**Rationale:** The spec promises keyring. Not shipping it makes the spec dishonest. But keyring failures are common in CI/headless environments, so graceful degradation is required.

**Action:**
- Implement `ProviderKeyringStore` mirroring `AuditKeyManager` pattern
- Add `keyring_status` to `/doctor` output: `✓ keyring available`, `⚠ keyring unavailable (env vars only)`, `✗ keyring error`
- KeyBadge shows `keyring` or `env` source; if keyring unavailable, `env` is the only option shown

### Decision 2: Cost estimates are "unknown" in v0.1

**Lock:** v0.1 does not attempt to estimate costs. All paid calls show `cost ?` with explicit confirmation. Hardcoded per-model estimates are deferred to v0.2.

**Rationale:** Provider pricing is complex (input vs output tokens, caching, reasoning tokens, tool use multipliers). Hardcoded estimates go stale quickly and create false confidence. "Unknown" is honest and forces explicit user consent.

**Action:**
- `CostCeilingBadge` always shows `cost ?` for paid providers in v0.1
- Confirmation copy: `This may call {provider}. Estimated cost: unknown. {provider} does not report estimates before the call. Session total so far: ${total}. Continue?`
- Ollama and other local providers show `cost $0.00` (no paid call confirmation needed)

### Decision 3: Session cost accumulator is v0.1 required

**Lock:** A simple per-session cost total is required for v0.1. It accumulates `cost_usd` from completed runs. Displayed in status line and `/status`.

**Rationale:** Even with "unknown" per-call estimates, the session total provides useful feedback. After a run completes, the provider response includes actual token usage and cost (for providers that return it). Accumulating these gives users a session-level view.

**Action:**
- Add `cost_usd_total` to session metadata (`metadata.yaml` per §7.14.1)
- Status line shows `cost $X.XX` when total > 0, `cost $0.00` when no paid runs, `cost ?` when any run had unknown cost
- Reset on `/clear` or new session

### Decision 4: Paid-call confirmation is CLI-first in v0.1

**Lock:** v0.1 implements paid-call confirmation in CLI only. IDE confirmation is v0.2.

**Rationale:** CLI confirmation is simpler (blocking prompt in REPL). IDE requires async modal/dialog with proper focus management. The CLI path proves the backend gating before investing in IDE UX.

**Action:**
- CLI paid-call prompt: `Paid call required: {provider} / {model}. Session total: ${total}. Approve? [y/n/change model]`
- IDE shows a non-blocking banner in v0.1: `Paid call required. Use CLI to approve or switch to Plan mode.`
- Full IDE paid-call card (§7.2) ships in v0.2

### Decision 5: `arc providers test` is v0.1 required

**Lock:** A simple provider health check command ships in v0.1.

**Rationale:** Users cannot verify keys work without running a workflow. This creates friction and wasted runs. A simple health check (model list or token balance) solves this.

**Action:**
- `arc providers test <provider-id>` — sends minimal request to provider API
- Results: `✓ key valid, models available`, `✗ key invalid`, `⚠ rate limited`, `⚠ network error`
- For Ollama: `arc providers test ollama` checks `localhost:11434/api/tags`
- Add to `/doctor` checks

### Decision 6: Budget ceilings are v0.2

**Lock:** Session-level and run-level budget ceilings are deferred to v0.2.

**Rationale:** v0.1 cost tracking is already ambitious (accumulator + confirmation + display). Adding ceiling enforcement requires: ceiling configuration, real-time cost checking, ceiling-exceeded handling, and clear UX for blocked runs. This is too much for v0.1.

**Action:**
- Reserve `session_max_cost_usd` and `run_max_cost_usd` fields in config schema
- Document in §7.9 as "reserved v0.2"
- v0.1 shows `active ceiling none` in `/status` (as spec already says)

### Decision 7: No token estimation in v0.1

**Lock:** ARC does not estimate tokens locally in v0.1.

**Rationale:** Local token estimation requires shipping tokenizer libraries (tiktoken for OpenAI, anthropic-tokenizer for Anthropic). This adds significant bundle size and maintenance burden. Providers return actual token counts in responses, which is sufficient for post-run cost tracking.

**Action:**
- Document that pre-call estimates are unavailable in v0.1
- Post-run, use provider response metadata (`usage.input_tokens`, `usage.output_tokens`) for cost computation
- Add local token estimation as v0.2 proposal

---

## Specific Spec Edits

### ARC_STUDIO_UX_SPEC.md

**§7.4 `/providers` Form:**
- Add `[test]` action for all providers (not just Ollama)
- Add test result states after test action: `✓ valid`, `✗ invalid`, `⚠ rate-limited`, `⚠ network error`
- Add keyring failure fallback: if keyring unavailable, show `(keyring unavailable, env vars only)` in header
- Change Ollama state from `○ local` to `○ local` with sub-states: `available`, `unavailable`, `no-models`

**§7.9 `/status`:**
- Add `Quota` line when gateway quota available: `Quota Anthropic: 42/100 today | OpenAI: unlimited`
- Clarify session cost source: `Session cost total $0.04 (from 2 completed runs) | last paid call $0.04 | active ceiling none (v0.1: estimates unavailable)`
- Add keyring status: `Keys keyring ✓ | Anthropic ✓ keyring | OpenAI ✓ env | Google ✗ unset`

**§7.14 Status Line:**
- Clarify cost segment behavior: `cost $X.XX` when session has paid runs with known costs, `cost $0.00` when no paid runs, `cost ?` when any run had unknown cost or no runs yet
- Add truncation rule: cost segment is never truncated (it's safety-critical)

**§9 KeyBadge:**
- Add `keyring-unavailable` state: when keyring library fails, badge shows `env-only` with warning tone
- Add tooltip: `Key stored in {source}. {warning if degraded}`
- Clarify: `file` source means config file contains env var reference, not the key itself

**§9 CostMeter:**
- Change `estimatedCeilingUsd` default to `'unknown'` for all paid providers in v0.1
- Add `actualCostUsd` field for post-run cost display
- Add `isLocal` prop — local providers (Ollama) show `cost $0.00` and skip confirmation

**§9 CostCeilingBadge:**
- Change v0.1 behavior: always shows `cost ?` for paid providers
- Add disabled state: `cost unavailable` when provider doesn't support cost reporting
- Add local provider variant: `cost $0.00` with `state.success` tone for Ollama

**§10.3 Confirmations:**
- Update paid-call copy for unknown cost: `This may call {provider}. Estimated cost: unknown — {provider} does not provide pre-call estimates. Session total so far: ${total}. Continue?`
- Add key removal confirmation: `Remove {provider} key from keyring? This cannot be undone. Env vars are not affected.`
- Add keyring-unavailable warning: `Keyring is unavailable on this system. Keys will only work from environment variables.`

**§10.10 Redaction Contract:**
- Add missing patterns: Azure OpenAI keys, Google service account JSON, AWS Bedrock session tokens, OpenRouter keys, generic `sk-` prefix keys (16+ chars), `ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_` GitHub tokens (already present), `xoxb-` Slack tokens, `Bearer ` tokens
- Add rule: redact any value matching the env var name of a configured provider key

**§8.6 Config:**
- Add Providers tab detail: list providers with key status, test button, add/edit/remove actions
- Add keyring status indicator at top of Providers tab
- Add reserved v0.2 section: Budget Ceilings (session max, run max)

### CLI_IDE_REDESIGN_PLAN.md

**§2.4 Slash Command List:**
- Add `/providers test <provider>` to the command list

**§2.5 Config Model:**
- Add `providers` section with keyring status and per-provider test results

### ADR-007

- Add implementation timeline: Phase 1 (keyring for provider keys) is v0.1, Phase 2 (gateway quota read) is v0.2
- Clarify that ARC's `ProviderQuotaStore` is the fallback when gateway is offline, not the primary source

---

## Acceptance Criteria

### v0.1 Provider Keys

- [ ] `arc providers test <provider>` validates key and reports status (valid/invalid/rate-limited/network-error)
- [ ] Provider keys can be stored in OS keyring via `arc providers accounts add --keyring`
- [ ] Keyring failure is detected and reported: `/doctor` shows keyring status
- [ ] Env var keys continue to work and take precedence over keyring
- [ ] `KeyBadge` component renders with correct source labels (`env`, `keyring`, `file`, `unset`)
- [ ] Key values are never displayed in CLI output, IDE UI, logs, or SSE events
- [ ] Redaction covers all major provider key patterns (OpenAI, Anthropic, Azure, Google, AWS, OpenRouter, GitHub, Slack)
- [ ] `add_direct_key_account()` no longer raises RuntimeError — it uses keyring or fails gracefully
- [ ] `/providers` form shows test action for all providers
- [ ] Ollama detection works: shows available/unavailable/no-models states

### v0.1 Cost Display

- [ ] Session cost accumulator exists and tracks completed run costs
- [ ] Status line shows `cost $X.XX` or `cost $0.00` or `cost ?`
- [ ] `/status` shows session cost detail with run count
- [ ] Runs table shows per-run cost (or `?` if unknown)
- [ ] `CostMeter` component renders with provider, model, approval state
- [ ] `CostCeilingBadge` component renders with `cost ?` for paid providers, `cost $0.00` for local
- [ ] Paid-call confirmation works in CLI (blocking prompt)
- [ ] Paid-call gating blocks calls in Plan mode
- [ ] Paid-call gating asks in Build mode
- [ ] Local providers (Ollama) skip paid-call confirmation
- [ ] Session cost resets on `/clear` or new session

### v0.1 Security

- [ ] No provider key is ever written to a config file in plaintext
- [ ] No provider key appears in CLI output, IDE UI, logs, SSE events, or trace files
- [ ] Key provenance (env/keyring/file/unset) is displayed but key values are not
- [ ] Redaction is applied universally: CLI, IDE, SSE, logs, traces, advanced commands

### v0.2 (Reserved)

- [ ] Budget ceiling configuration (`session_max_cost_usd`, `run_max_cost_usd`)
- [ ] Budget ceiling enforcement (blocks runs when ceiling exceeded)
- [ ] IDE paid-call confirmation dialog (async modal)
- [ ] SwarmGraph gateway quota display in `/providers` and `/status`
- [ ] Hardcoded per-model cost estimates
- [ ] Token count display in Runs table
- [ ] Cost history / aggregate view

---

## Reject / Do Not Build

### Rejected: Plaintext key storage in config files

**Why rejected:** Security risk. Config files are often committed to git, backed up to cloud storage, or readable by other processes. Even with `.gitignore`, accidental commits happen. Every competitor that stores keys in config files (OpenCode, Aider) has this vulnerability.

**Alternative:** OS keyring + env var references only. If keyring is unavailable, env vars are the only option. Never write keys to disk.

### Rejected: Pre-call token estimation in v0.1

**Why rejected:** Requires shipping tokenizer libraries (tiktoken ~5MB, anthropic-tokenizer ~3MB). Adds maintenance burden (tokenizer updates, model-specific tokenizers). Estimates are often wrong (reasoning tokens, tool use, caching). Creates false confidence.

**Alternative:** Show `cost ?` with explicit confirmation. Post-run, use actual provider response metadata for cost tracking. Add local estimation in v0.2 if user demand justifies the bundle size.

### Rejected: Real-time cost streaming

**Why rejected:** Provider APIs don't stream cost information. Cost is only known after the call completes. Attempting to estimate mid-stream is unreliable and misleading.

**Alternative:** Show cost after run completion. Accumulate in session total.

### Rejected: Multi-key support per provider

**Why rejected:** Adds complexity to key management UI, routing logic, and audit trail. Most users have one key per provider. Multi-key is an enterprise feature that requires tenant isolation first.

**Alternative:** Single key per provider in v0.1. Multi-key deferred until multi-tenant architecture exists (post-v0.1).

### Rejected: Automatic provider failover based on cost

**Why rejected:** Requires real-time cost comparison across providers, which requires pre-call estimates (rejected above). Also changes model behavior silently, which violates the "honest" brand attribute.

**Alternative:** Manual provider switching via `/providers` or `/model`. Router suggestions in v0.2 can include cost considerations but must be explicit.

### Rejected: Cost export to CSV/JSON

**Why rejected:** Low priority for v0.1. Cost data is visible in Runs table and `/status`. Export is a nice-to-have that can be added when cost tracking is mature.

**Alternative:** Add `arc runs export --include-cost` in v0.2 or v0.3.

### Rejected: Cloud-based cost dashboard

**Why rejected:** ARC Studio is local-first. A cloud dashboard requires multi-tenant infrastructure, authentication, and data export — all post-v0.1 scope.

**Alternative:** Local cost history view in IDE (v0.3). Cloud dashboard is not planned.

### Rejected: Per-model hardcoded cost table

**Why rejected for v0.1:** Provider pricing changes frequently. A hardcoded table goes stale within weeks. Requires maintenance and release cadence just for pricing updates.

**Alternative for v0.2:** Fetch pricing from provider APIs or a maintained pricing endpoint at startup, with local cache and staleness warning. Or accept that estimates are approximate and label them clearly.

---

## Appendix: Research Sources

### Product Documentation

- **Claude Code:** https://docs.anthropic.com/en/docs/claude-code/overview — subscription-based auth, env var support for API keys, Bedrock/Vertex/Foundry integration via env vars, `/config` settings interface, `/status` for connection info
- **Claude Code env vars:** https://docs.anthropic.com/en/docs/claude-code/env-vars — comprehensive env var reference including `ANTHROPIC_API_KEY`, provider-specific base URLs, model configuration
- **Claude Code settings:** https://docs.anthropic.com/en/docs/claude-code/settings — scope system (managed/user/project/local), JSON config, no keyring for provider keys
- **Claude Code third-party:** https://docs.anthropic.com/en/docs/claude-code/third-party-integrations — Bedrock/Vertex/Foundry setup, LLM gateway configuration, cost tracking via cloud dashboards
- **OpenCode:** https://github.com/opencode-ai/opencode (archived, now https://github.com/charmbracelet/crush) — env vars or JSON config for API keys, 8 providers, `LOCAL_ENDPOINT` for self-hosted, no keyring, no cost display
- **Aider config:** https://aider.chat/docs/config.html — env vars, `.env` file, YAML config for API keys, 15+ providers, no keyring
- **Aider API keys:** https://aider.chat/docs/config/api-keys.html — `--api-key provider=key` syntax, env var mapping, YAML config `api-key` entries
- **Cursor:** https://docs.cursor.com — built-in subscription or own API key in Settings, model dropdown, no key provenance display, no cost tracking

### ARC Studio Source Files

- `python/src/agent_runtime_cockpit/providers.py` — Provider registry, account store (env refs only), routing policy, quota store
- `python/src/agent_runtime_cockpit/security/profiles.py` — RunProfile with `allow_paid_calls`, profile enforcement
- `python/src/agent_runtime_cockpit/security/redaction.py` — Redactor class with secret patterns
- `python/src/agent_runtime_cockpit/audit/key_manager.py` — AuditKeyManager with keyring storage pattern (reusable for provider keys)
- `docs/adr/007-provider-routing-unification.md` — ARC metadata layer vs SwarmGraph gateway execution layer
- `docs/research/ARC_STUDIO_UX_SPEC.md` — Full UX spec including §7.4 providers, §7.14 cost segment, §9 components, §10.3 confirmations, §10.10 redaction
