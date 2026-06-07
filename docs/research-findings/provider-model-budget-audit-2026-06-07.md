# Provider / Model / Budget Audit — 2026-06-07

> **Scope:** Provider config, key storage, diagnostics, model catalog, routing, paid-call gates, budget/wallet, cost events, IDE config, CLI parity, secret redaction  
> **Agent count:** 12 parallel sub-agents

---

## 1. Provider Architecture Map

```
THREE DISCONNECTED PROVIDER LISTS

1. CLI catalog (provider_action.py PROVIDERS)
   54 ProviderDefinition entries — static Python list
   Fields: id, display_name, category, auth_kind, env_key_names,
           supports_*, default_models, status, warnings
   ✗ No is_free_tier. ✗ No cost_rates. ✗ No sync with runtime.

2. Runtime registry (providers/registry.py _FACTORIES)
   10 hard-coded + ~99 auto-loaded from models_dev snapshot
   Returns new ProviderClient instance per get() call
   ✗ Only anthropic tested. ✗ No cross-validation with CLI list.

3. Models.dev snapshot (models_dev.py 1.4MB static dict)
   109 providers / 3,588 models with cost, limits, modalities
   Live refresh: ARC_MODELS_DEV_LIVE=1 — BROKEN IN ASYNC CONTEXT
   (silent pass when loop.is_running())
```

### Supported providers by category

| Category | Count | Examples |
|---|---|---|
| Major paid | ~30 | OpenAI, Anthropic, Google, DeepSeek, xAI, Groq, Fireworks, Mistral, Perplexity |
| Chinese-ecosystem | 27 | Alibaba/DashScope, ZhipuAI/GLM, Moonshot/Kimi, SiliconFlow, DeepSeek, Stepfun, Baidu, ModelScope, Xiaomi, Tencent, Drun, iFlow, Qiniu |
| Routing/aggregator | 9 | OpenRouter, CrofAI, LLMGateway, Helicone, 9router |
| Specialty/infra | 25+ | Cloudflare, DigitalOcean, Vultr, Scaleway, Nebius, Baseten, Friendli |
| Local | 5 | Ollama, LM Studio, vLLM, llama.cpp, LocalAI |
| Free/no-billing | 6 | GitHub Models, OpenRouter `:free`, NVIDIA free tier, HF Inference, LM Studio, Ollama Cloud |

### Key storage architecture

```
API keys → env vars only → provider SDK (key never persisted to disk)
~/.arc/providers.json → stores env var NAME only ("key_env_var": "ANTHROPIC_API_KEY")
Direct key storage → blocked: RuntimeError("use --api-key-env")
```

### Routing (broken by design)

- `ProviderRouter` — **dead code**, not wired to TurnManager
- `FallbackProviderClient` — correct failover state machine, **not default**
- Default: positional only — `list[0]` always tried first, no cost/latency/capability routing
- `AgentRouterProxy` — orthogonal local proxy to `agentrouter.org`

### Profiles (4 built-in, frozen)

| ID | Backend | allow_paid | allow_network | allow_shell |
|---|---|---|---|---|
| `stub` | STUB | ❌ | ❌ | ❌ |
| `local-safe` | STUB | ❌ | ❌ | ❌ |
| `local-paid` | LOCAL | ✅ | ✅ | ❌ |
| `gateway` | GATEWAY | ✅ | ✅ | ✅ |

---

## 2. Model / Routing / Budget Data Flow

```
User turn → BudgetEnforcer.preflight()       (NEW schema, USD-only, SQLite)
              ├── first_launch gate ($1.00 if first_launch_confirmed=False)
              ├── RUN cap ($5 default)
              ├── WORKFLOW cap ($25 default)
              ├── SESSION cap ($10 default)
              └── PROVIDER_DAY cap ($100 default)
                    │ pass
                    ▼
            EnforcementContext.allow_paid?   ← TUI defaults True ⚠️
                    │ pass
                    ▼
            Token estimation (TiktokenApproximate, local)
            Cost estimation (input×rate + output×rate, from CostRates)
                    │
                    ▼
            Provider client → SDK → LLM API
            Response: input_tokens, output_tokens, cache tokens
                    │
                    ▼
            extract_cost(response)
              source = "measured" (from response body) or "estimated"
              8dp ROUND_HALF_EVEN
                    │
                    ▼
            BudgetEnforcer.record(cost_usd) → SQLiteWAL
              → QuotaWarning event if scope ≥ 80%

Cost events:
  QUOTA_WARNING → TUI status bar (subscribed)
  BUDGET_BROKER_SYNC → (if remote broker enabled, default OFF)
  SWARMGRAPH_COST → only when measured=True in runtime_config ⚠️
    (source="measured" flag is caller-supplied, not verified)

Pricing feed (default OFF, ARC_PRICING_FEED_ENABLED=1):
  → OpenRouter API (weekly) → hash-pinned
  → accept_new_hash() is a stub ⚠️
  → feed → CostRates injection path: MISSING ⚠️
```

---

## 3. Secret Exposure Review

| Surface | Status | Risk |
|---|---|---|
| Key storage on disk | ✅ env var name only | None |
| Key in process memory | ✅ only in SDK object | Low |
| `AnthropicClient._client_instance()` | ❌ passes None to SDK if key missing | Medium — opaque SDK error |
| `_map_error()` — Anthropic + OpenAI-compat | ❌ `str(exc)` unredacted | Medium — SDK may embed key in error |
| `agentrouter_proxy.redacted()` | ✅ only file with active redaction | — |
| FlightRecorder write path | ✅ `redact_payload()` before persistence | Low |
| Storage layer write path | ❌ no redaction at JSONL store level | Medium |
| E2E evidence artifacts | ✅ SHA-256 hashes only | None |
| Groq `gsk-`, DashScope, GLM key formats | ❌ not in named redaction patterns | Medium |
| Multiple redaction module copies (5 files) | ⚠️ drift risk | Low-Medium |
| Audit events | ✅ no key values observed | Low |

---

## 4. Paid-Call Gate Matrix

| Surface | Gate Status | Risk |
|---|---|---|
| CLI (`arc providers action`) | ✅ 4-gate: `--live` + `--allow-paid-calls` + env var + `--confirm` string | Secure |
| CLI all other commands | ✅ dry_run=True by default | Secure |
| `EnforcementContext.allow_paid` default | ✅ `False` | Secure |
| **TUI session `allow_paid` fallback** | ❌ `getattr(self.data, "allow_paid", True)` — **defaults to True** | **HIGH RISK** |
| CapabilityCard gate mode | ⚠️ defaults to `warn`, not `deny` | Medium |
| `ConfirmationRequired` catch sites | ❌ only caught in `cli/obs.py` (not main TUI path) | High |
| `first_launch_confirmed` persistence | ❌ in-memory `BudgetConfig`, not written to SQLite | Medium |
| HTTP API `?allow_paid_calls=true` GET param | ⚠️ accepted from any local process | Low |
| Budget hard cap (SESSION $10, PROVIDER_DAY $100) | ✅ SQLite-persisted, survives restart | Correct backstop |

---

## 5. IDE UX Gaps

| Gap | Severity |
|---|---|
| No active model selection — model list display-only | High |
| No per-provider base_url configuration | High |
| No OAuth/device-flow UI | High |
| Model list capped at 10, no capability/cost badges | High |
| No real cost display — local counters only | High |
| No provider health/ping test — env-var presence only | Medium |
| `/wallet` and `/budget` hidden from `/help` | Medium |
| `arc wallet` CLI command in README not wired | Medium |
| No ProviderAccountInfo rendering | Medium |
| No `unset` provider UI | Low |
| ConfigTab Routing section read-only | Low |
| `ProviderCatalogStatus` research_only/not_recommended not shown | Low |

---

## 6. Tests Needed

| Priority | Test |
|---|---|
| P0 | `test_anthropic_missing_key_raises_auth_error` |
| P0 | `test_map_error_redacts_secret_values` — both `anthropic.py` and `openai_compatible.py` |
| P0 | `test_tui_session_allow_paid_default_is_false` |
| P1 | `test_all_known_providers_have_valid_capabilities` — parametrized over `known()` |
| P1 | `test_chinese_labs_provider_registered` — DashScope, ZhipuAI, Moonshot, SiliconFlow |
| P1 | `test_budget_preflight_integration_with_real_turn` |
| P1 | `test_provider_day_scope_preloaded_on_startup` |
| P1 | `test_first_launch_confirmed_persists_to_storage` |
| P1 | `test_groq_key_pattern_redacted` (`gsk-...`) |
| P1 | `test_live_catalog_refresh_works_in_async_context` |
| P2 | `test_budget_broker_sync_emitted_on_fail_closed_deny` |
| P2 | `test_pricing_feed_injects_cost_rates` |
| P2 | `test_wallet_arc_cli_command_exists` |
| P2 | `test_providers_catalog_json_output_is_pure_json` |

---

## 7. Next-Slice Implementation Prompt

**Target:** Paid-call gate hardening + secret redaction + `arc wallet` CLI

### 1. Fix TUI paid-call gate default

File: `python/src/agent_runtime_cockpit/tui/screen.py`

```python
# BEFORE (dangerous):
self._session.allow_paid_calls = bool(getattr(self.data, "allow_paid", True))

# AFTER:
self._session.allow_paid_calls = bool(getattr(self.data, "allow_paid", False))
```

### 2. Add `_map_error()` redaction to both provider clients

Promote `redacted()` from `agentrouter_proxy.py` into a shared utility:

```python
def redact_provider_error(text: str, api_key: str | None) -> str:
    if api_key and api_key in text:
        text = text.replace(api_key, "[REDACTED]")
    return Redactor().redact(text)
```

Apply in `openai_compatible.py` and `anthropic.py` `_map_error()`.

### 3. Fix `AnthropicClient` fail-open

```python
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise AuthError("ANTHROPIC_API_KEY environment variable not set")
self._client = Anthropic(api_key=api_key, ...)
```

### 4. Add Groq/DashScope key patterns to redaction

```python
r"gsk-[A-Za-z0-9]{40,}",   # Groq
r"sk-[A-Za-z0-9\-_]{20,}", # DashScope and generic sk- variants
```

### 5. Wire `/wallet` and `/budget` into `/help`

Add `"budget"` to the `cmd_help` groups dict.

### 6. Add `arc wallet` CLI command stub

```python
wallet_app = typer.Typer(name="wallet", help="View token budget and usage")

@wallet_app.command("budget")
def wallet_budget(...):
    """Show budget limits and current usage."""
```

### Do NOT do

- `ProviderRouter` wiring to TurnManager
- Fix `ARC_MODELS_DEV_LIVE` async context
- Pricing feed → CostRates injection
- `accept_new_hash()` persistence
- Chinese-labs provider registry tests

---

## Key Findings Summary

**Four biggest problems:**

1. **TUI paid-call gate defaults to True** — `getattr(self.data, "allow_paid", True)` makes paid calls the default in TUI sessions unless explicitly blocked. The CLI correctly defaults to `False`.

2. **`_map_error()` has no redaction** in either primary provider client — `str(exc)` from SDK exceptions propagates raw, potentially including key material if the SDK ever embeds it in a 401 response body.

3. **`ProviderRouter` is dead code** — not wired to TurnManager; routing always uses position-0 with no cost/latency awareness.

4. **Two `BudgetEnforcer` classes with the same name** — legacy `BudgetVectorEnforcer` (in-memory tokens) and new schema-based `BudgetEnforcer` (SQLite USD) coexist; tests exercise the legacy class while the live path uses the new one.

### Answers to key research questions

| Question | Answer |
|---|---|
| Which providers supported? | 109 (models.dev), 54 in CLI catalog. 27 Chinese-ecosystem providers. |
| How are keys stored? | Env-var only. Config stores env var name reference, never raw key. |
| Are raw keys ever exposed? | Not intentionally. Risk path: `_map_error()` unredacted `str(exc)`. |
| Which commands make paid calls? | `arc providers action` (4-gate). TUI if `allow_paid` unset (defaults True). |
| How is paid-call opt-in enforced? | `EnforcementContext.allow_paid=False` + RunProfile + BudgetEnforcer preflight. |
| What model catalog exists? | Static 1.4MB Python dict, 3,588 models with cost rates, limits, modalities. |
| How does routing choose? | Positional only. ProviderRouter is dead code. |
| What budget/wallet persistence? | SQLiteWAL for SESSION and PROVIDER_DAY. `arc wallet` CLI not wired. |
| Cost events: measured or estimated? | Anthropic: measured from response body. SWARMGRAPH_COST: caller-supplied flag. |
| Are quotas local-only? | Yes — `scope: "local_quota_counters_only"`. Budget broker is optional (default OFF). |
| Is quota reset remote? | No — local counters only. README accurately says "(local only, not provider)". |
