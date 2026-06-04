# Pricing Feed Source Comparison

> **Date:** 2026-06-04
> **Decision:** ARC uses **OpenRouter `/api/v1/models`** as the primary
> pricing-feed source. models.dev is the documented fallback.
> **Audience:** Future spec authors; sprint planners. Reference this doc
> instead of re-evaluating the same alternatives.

---

## TL;DR — Why OpenRouter wins

OpenRouter's model API ships **every field** ARC's v0.5.1 spec was about
to invent (`is_free`, `deprecation_date`, tiered pricing, supported_parameters),
covers **3× more models** than models.dev, and requires **no auth**. Better
operational fit than every alternative evaluated.

---

## Comparison matrix

| Source | API endpoint | Coverage | Cache fields | Free? | Auth | Rate limit | Stability |
|---|---|---|---|---|---|---|---|
| **OpenRouter** | `GET https://openrouter.ai/api/v1/models` | **300+ models** including Chinese labs | ✓ `input_cache_read` + `input_cache_write` + tiered | ✓ | ✗ none for reads | Edge-cached | Production grade; years of operation |
| **models.dev** | `GET https://models.dev/api.json` | ~100 models, English-focused | ✓ `cache_read` + `cache_write` | ✓ | ✗ none | None documented | Used in production by opencode; ~6-12 months old |
| **Artificial Analysis** | `GET https://artificialanalysis.ai/api/v2/data/llms/models` | ~100 models | ✗ **no cache pricing** | ✓ with key | ✓ x-api-key header | 1,000 req/day | Well documented; benchmark-focused |
| **simonw/llm-prices** | `GET https://www.llm-prices.com/current-v1.json` | ~30-40 vendors | ✓ `input_cached` only (single field) | ✓ MIT | ✗ static | None | Single maintainer; slower to update niche models |
| **PricePerToken** | MCP server (`https://api.pricepertoken.com/mcp/mcp`) | 300+ models, 561 tracked | ⚠ depends on model | ✓ | ✗ | Unknown | Niche: MCP first, not JSON API first |
| **Helicone llm-cost** | Open-source JSON | 250+ models | ⚠ subset have cache fields | ✓ | ✗ | Unknown | Maintained alongside Helicone product |
| **LiteLLM model_prices.json** | `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` | 250+ models | ✓ comprehensive | ✓ Apache 2.0 | ✗ static | None | Mature; BerriAI product depends on it |

---

## Why OpenRouter wins for ARC specifically

### 1. Schema alignment with what ARC was about to invent

The v0.5.1-v2 spec extended CostRate with 6 new optional fields. OpenRouter
already has equivalents:

| ARC v0.5.1 v2 new field | OpenRouter equivalent | Notes |
|---|---|---|
| `is_free_tier: bool` | `is_free: bool` | Direct equivalent |
| `pricing_valid_until: date` | `deprecation_date: ISO8601` | Direct equivalent |
| `auto_route_to: str` | `canonical_slug: str` | Pattern: legacy `id` + `canonical_slug` points to current |
| `cache_field_names: dict` | (handled by OpenRouter gateway normalization) | OpenRouter normalizes vendor-specific JSON; field naming is consistent |
| `cached_input_usd_per_million: Decimal` | `pricing.input_cache_read: str` | Direct equivalent (string per OR convention to avoid float precision) |
| `cache_storage_usd_per_million_per_hour: Decimal` | ⚠ NOT in OpenRouter schema | Gemini-specific; would still need ARC-side field |

**Five of six fields are free.** Only Gemini cache-storage stays bespoke.

### 2. Tiered pricing support

OpenRouter handles long-context pricing tiers natively:

```json
"pricing": [
  { "prompt": "0.000002", "completion": "0.000012" },
  { "prompt": "0.000004", "completion": "0.000018", "min_context": 200000 }
]
```

ARC's research already documents this pattern (Gemini 3.1 Pro ≤200K vs >200K
pricing). OpenRouter ships it as a first-class schema feature; ARC would
have invented it ad hoc.

### 3. `supported_parameters` array replaces manual capability flags

OpenRouter's response includes `supported_parameters: ["tools", "json_mode",
"structured_outputs", "web_search", "reasoning"]`. Future ARC features that
gate on capability (e.g., "only show models with `tools` in the routing
picker") can read this instead of hand-maintained per-model flags.

### 4. Coverage

300+ models vs models.dev's ~100. For ARC's open-weight adoption story
(DeepSeek, Qwen, Kimi, GLM, MiMo, MiniMax), more coverage means fewer
hand-typed rows.

### 5. Operationally simplest

| Aspect | OpenRouter | models.dev | Artificial Analysis |
|---|---|---|---|
| Auth | None | None | Required (1k/day) |
| Caching | Edge-cached | Static JSON | Server-side |
| Polling cost | One GET, no headers | Same | Same + auth header |
| Production maturity | Years of operation | New | Stable |
| Backed by | OpenRouter business | Community + opencode | Independent benchmark co |

---

## Why NOT OpenRouter — honest counterpoints

### CP1. OpenRouter is a commercial company

Their data quality is tied to their business model. If they shut down or
pivot, ARC's feed dies. Mitigated by: ARC always keeps a local snapshot;
models.dev documented as fallback.

### CP2. OpenRouter prices include their 5.5% credit-purchase fee structure indirectly

Strictly: their `pricing` field shows what they bill (which is provider
rate; the 5.5% is on credit purchase). When ARC uses OpenRouter as a
*pricing reference* but calls vendors *directly*, the numbers should still
match. Verify per-vendor on first integration to catch any drift.

### CP3. OpenRouter only lists models OpenRouter serves

If a vendor exists that OpenRouter hasn't integrated, the feed won't cover
it. Edge case for ARC today (OpenRouter has nearly everything), could
matter for niche or self-hosted models later.

### CP4. The `canonical_slug` pattern is similar but not identical to ARC's `auto_route_to`

`auto_route_to` was designed as "if I see this legacy ID, route to this
current ID." `canonical_slug` is "the canonical name for this model
variant." Functionally similar; minor parser logic needed to map one to
the other.

---

## Why NOT models.dev

It's a fine source. OpenRouter is just **strictly better** for ARC's use
case. models.dev advantages would be:

- If ARC ever supported models NOT served by OpenRouter (rare)
- If models.dev's TOML source repository is easier to PR fixes against
  than OpenRouter's data (untested)
- If OpenRouter became unreliable and models.dev stayed up

For these reasons models.dev is documented as the **secondary** source.
`scripts/sync_from_pricing_feed.py` accepts `--source models-dev` to switch.

---

## Why NOT Artificial Analysis

**Missing cache pricing fields.** Their schema reports `price_1m_input_tokens`
and `price_1m_output_tokens` and a `blended_3_to_1` figure — no cache
read/write fields anywhere in the public API.

Cache pricing is the **headline feature** of ARC's token-saving story (R-04
populator, R-03 visibility, R-02 compaction work all depend on cache
accounting being accurate). A pricing source that can't tell you "cache
read is $0.30 vs input $3.00" is the wrong source.

Artificial Analysis remains useful for **other features ARC could add**:
- `/wallet` could display benchmark intelligence_index alongside cost
- Model picker could filter by speed (`median_output_tokens_per_second`)
- A future "model recommendation" feature could rank by quality-per-dollar

That's a future sprint, not this one.

---

## Why NOT simonw/llm-prices

Excellent quality for the models it covers, but coverage is too narrow:
~30-40 vendors with English-speaking focus. Critical gap: weak Chinese-lab
coverage (DeepSeek partial, Qwen/Kimi/GLM/MiMo/MiniMax mostly absent at
time of writing). ARC's open-weight expansion needs comprehensive coverage.

Stays in the comparison table as an example of a **high-quality narrow
source**. If ARC ever wants pricing for a model OpenRouter and models.dev
both miss, llm-prices might have it.

---

## Why NOT PricePerToken

Their developer surface is **MCP** (Model Context Protocol) — designed for
Claude Code / Cursor / Windsurf to consume via an MCP server. ARC could
host its own MCP client, but for a pricing-table sync use case, JSON-over-
HTTP is simpler. MCP advantage only manifests if ARC adds an "ask the
pricing data" agent feature (out of scope).

---

## Decision

**Primary:** `https://openrouter.ai/api/v1/models`
**Fallback:** `https://models.dev/api.json`
**Out of scope:** Artificial Analysis (no cache fields), llm-prices (narrow
coverage), PricePerToken (MCP-first), LiteLLM JSON (good but adds nothing
OpenRouter doesn't already provide).

The `scripts/sync_from_pricing_feed.py` script accepts `--source` to switch
between primary and fallback. v0.5.1-alpha-v3 spec uses OpenRouter by
default. v0.7-alpha-v3 (the opt-in runtime feed) lets users configure
either via `ARC_PRICING_FEED_URL`.

---

## What happens if this decision goes stale

This decision is good as of 2026-06-04. Re-evaluate if:

| Trigger | Action |
|---|---|
| OpenRouter shuts down or pivots away from open API | Activate models.dev fallback; re-write sync_from_pricing_feed.py default |
| Artificial Analysis adds cache pricing fields | Reconsider AA as primary (their benchmark data is valuable bonus) |
| A new source emerges with materially better coverage | Document in this file, run comparison, decide |
| LiteLLM's model_prices.json becomes more comprehensive than OpenRouter | Reconsider; LiteLLM is mature and Apache 2.0 |

This document gets re-reviewed quarterly per the `docs/research/pricing-snapshot-*.md` cadence.

---

## Sources

- OpenRouter Models API: [openrouter.ai/docs/api/api-reference/models/get-models](https://openrouter.ai/docs/api/api-reference/models/get-models) (accessed 2026-06-04)
- OpenRouter Provider Integration (schema spec): [openrouter.ai/docs/guides/guides/for-providers](https://openrouter.ai/docs/guides/guides/for-providers) (accessed 2026-06-04)
- models.dev: [github.com/anomalyco/models.dev](https://github.com/anomalyco/models.dev) (accessed 2026-06-04)
- Artificial Analysis API: [artificialanalysis.ai/api-reference](https://artificialanalysis.ai/api-reference) (accessed 2026-06-04)
- simonw/llm-prices: [github.com/simonw/llm-prices](https://github.com/simonw/llm-prices) (accessed 2026-06-04)
- PricePerToken MCP: [pricepertoken.com/mcp](https://pricepertoken.com/mcp) (accessed 2026-06-04)
- LiteLLM model registration: [docs.litellm.ai/docs/provider_registration/add_model](https://docs.litellm.ai/docs/provider_registration/add_model) (referenced)
