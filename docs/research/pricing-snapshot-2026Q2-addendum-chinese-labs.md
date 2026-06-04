# Pricing Snapshot — 2026 Q2 Addendum: Chinese Labs & Open-Weight Vendors

> **Snapshot date:** 2026-06-04
> **Status:** Addendum to `docs/research/pricing-snapshot-2026Q2.md`.
> **Scope:** DeepSeek, Qwen (Alibaba), Kimi (Moonshot), GLM (Zhipu Z.AI),
> MiMo (Xiaomi). Plus a sixth opportunistic add: MiniMax M2.5 series
> (appears alongside the others in routing configs).
> **For consumer:** Planning input for ARC adoption via existing
> `providers/openai_compatible.py` (no new provider modules needed).

---

## TL;DR

| Finding | Severity |
|---|---|
| **All five are OpenAI-compatible.** No new provider module required; ARC's `providers/openai_compatible.py` covers all with `base_url` swaps. | ✓ low-risk |
| **Cache discounts vary wildly (80–98%).** DeepSeek V4-Flash hits 98% off ($0.14 → $0.0028/M). Wallet must handle per-model cache multipliers, not a single per-vendor constant. | ⚠ requires data-model change |
| **Some have completely free tiers** (GLM-4.7-Flash, GLM-4.5-Flash, GLM-4.6V-Flash). Wallet should detect `$0/M` rows and skip cost tracking for them. | ⚠ edge case to handle |
| **Promotional pricing is widespread and expiring**: DeepSeek V4-Pro 75% off ended 2026-05-31; Xiaomi MiMo V2-Pro auto-routes to V2.5 on 2026-06-01. Pricing table needs *valid_from* / *valid_until* fields. | ⚠ pricing freshness |
| **Vision models charge differently** for audio/video/image vs text. New unit-of-account problem ARC hasn't faced before. | ⚠ defer until needed |
| **Chinese phone-number gates** block direct-API signup for some vendors (Moonshot historically). Gateway providers (OpenRouter, AIMLAPI, TokenMix, Ofox) bypass this with markup. | informational |

**Recommendation:** This work is **NOT v0.4.1-alpha scope.** Adopt these vendors in a future v0.5+ release. v0.4.1's pricing refresh should land Anthropic/OpenAI/Google fixes only; this addendum is the *planning document* for whichever sprint picks up Chinese-lab routing.

---

## §1 — DeepSeek

**API:** `https://api.deepseek.com/v1` (OpenAI-compatible)
**Free tier:** 5M tokens on signup, valid 30 days
**Cache mechanism:** Automatic prefix-based; no opt-in flag required
**Critical caveat:** R1 (deepseek-reasoner) and V3-era IDs (deepseek-chat) **retire after 2026-07-24 15:59 UTC**. Use explicit V4 names in new code.

| Model ID | Input | Cached input | Output | Context | Notes |
|---|---|---|---|---|---|
| `deepseek-v4-flash` | $0.14 | $0.0028 (98% off) | $0.28 | 1M | Default low-cost |
| `deepseek-v4-pro` (promo, expired) | $0.435 | $0.003625 | $0.87 | 1M | 75% off ended 2026-05-31 — but [verdent.ai](https://www.verdent.ai/guides/deepseek-v4-pricing-api-migration-2026) reports DeepSeek made the discount **permanent at 1/4 of original** post-May 31 |
| `deepseek-v4-pro` (regular ref) | $1.74 | $0.0145 | $3.48 | 1M | Listed as crossed-out reference |
| `deepseek-chat` (legacy) | maps to V4-Flash non-thinking | same | same | 1M | **Retires 2026-07-24** |
| `deepseek-reasoner` (legacy) | maps to V4-Flash thinking | same | same | 1M | **Retires 2026-07-24** |

**Cache field name in API response:** `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens`. Different from Anthropic's `cache_read_input_tokens` — wallet aggregation needs per-provider field-name mapping.

---

## §2 — Qwen (Alibaba)

**API:** `https://dashscope.aliyuncs.com/compatible-mode/v1` (OpenAI-compatible) or `https://coding-intl.dashscope.aliyuncs.com/v1` for coding endpoint
**Free tier:** Discontinued 2026-04-15 (was 1000 req/day on OAuth). Groq still hosts Qwen3-32B free with rate limits.
**Cache mechanism:** Automatic, similar to OpenAI auto-cache

| Model ID | Input | Cached input | Output | Context | Notes |
|---|---|---|---|---|---|
| `qwen3.7-max` | $2.50 | $0.25 (90% off) | $7.50 | 1M | New 2026-05-20 flagship; **97M output tokens in benchmark = 4× median verbosity** — ARC wallet should warn about high output multiplier |
| `qwen3.7-plus` | $0.40 | $0.08 (80% off) | $1.60 | 1M | Multimodal (text+image+video); 6× cheaper than Max |
| `qwen3-max` (closed) | $0.78 | — | $3.90 | 262K | Open-weight tier |
| `qwen3.6-plus` | $0.325 | — | $1.95 | 1M | Open-weight |
| `qwen3-coder-plus` | $0.50–$0.65 | — | $1.50–$3.25 | 131K–1M | Coding specialist |
| `qwen3.6-35B-A3B` (open-weight API) | $0.15 | $0.05 | $0.65 | 131K | Cheapest hosted tier |
| `qwen2.5-72b-instruct` | $0.35 | — | $0.65 | 131K | Legacy but still supported |

**Tokenizer note:** Qwen's tokenizer differs significantly from cl100k_base. Heuristic `len/4` estimator will be off. Use `tiktoken` is wrong; need Qwen's own tokenizer or API token-count endpoint.

---

## §3 — Kimi (Moonshot AI)

**API:** `https://api.moonshot.ai/v1` (OpenAI-compatible)
**Free tier:** $1 minimum recharge; cumulative $5 grants $5 voucher bonus
**Phone-number gate:** Direct signup typically requires Chinese mainland phone number. Gateway access (TokenMix, OpenRouter) bypasses.
**Cache mechanism:** Automatic context caching

| Model ID | Input (cache miss) | Cached input | Output | Context | Notes |
|---|---|---|---|---|---|
| `kimi-k2.6` | $0.95 | $0.16 (83% off) | $4.00 | 256K | New 2026-04-20 flagship; multimodal (text+image+video) |
| `kimi-k2.5` | $0.60 | $0.10 (83% off) | $3.00 | 256K | Cheaper multimodal; Agent Swarm support |
| `kimi-k2-0905-preview` (legacy) | $0.60 | $0.15 | $2.50 | 256K | **EOL 2026-05-25** |
| `kimi-k2-0711-preview` (legacy) | $0.55 | $0.15 | $2.20 | 131K | **EOL 2026-05-25** |
| `kimi-k2-turbo-preview` (legacy) | $1.15 | $0.15 | $8.00 | 256K | **EOL 2026-05-25** |
| `kimi-k2-thinking-turbo` (legacy) | $1.15 | $0.15 | $8.00 | 256K | **EOL 2026-05-25** |

**Web search add-on:** $0.005/call.
**Migration deadline:** All legacy K2 SKUs deprecated by 2026-05-25. New code should target K2.5 or K2.6 only.

---

## §4 — GLM (Zhipu AI / Z.AI)

**API:** `https://open.bigmodel.cn/api/paas/v4/` or `https://api.z.ai/api/paas/v4/` (OpenAI-compatible)
**Free tier:** **Several genuinely free models** — GLM-4.7-Flash, GLM-4.5-Flash, GLM-4.6V-Flash. No rate-limit-per-day cap on these (per [vibecoding.app](https://vibecoding.app/blog/zhipu-ai-glm-pricing-2026)). Use as loss leaders.
**Coding Plan subscription** also exists ($30–$240/quarter) — separate from per-token API.

| Model ID | Input | Cached input | Output | Context | Notes |
|---|---|---|---|---|---|
| `glm-5-turbo` | $1.20 | $0.24 (80% off) | $4.00 | 203K | Top tier |
| `glm-5.1` | $0.98 | $0.182 | $3.08 | 203K | Newer than 5; per [pricepertoken.com](https://pricepertoken.com/pricing-page/provider/z-ai) |
| `glm-5` | $0.60 | $0.12 | $1.92 | 203K | Standard 5 |
| `glm-4.7` | $0.40 | $0.08 | $1.54 | 203K | Best value mid-tier |
| `glm-4.7-thinking` | $0.40 | $0.08 | $1.54 | 203K | Same price, thinking mode |
| `glm-4.6` | $0.43 | $0.08 | $1.74 | 205K | Prior gen |
| `glm-4.5` | $0.60 | $0.11 | $2.20 | 131K | Established workhorse |
| `glm-4.5-air` | $0.125 | $0.025 | $0.85 | 131K | Cheap |
| `glm-4.7-flash` | **FREE** | **FREE** | **FREE** | 203K | Zero-cost ⚠ wallet must skip |
| `glm-4.5-flash` | **FREE** | **FREE** | **FREE** | — | Zero-cost ⚠ wallet must skip |
| `glm-4.6v` (vision) | $0.30 | $0.05 | $0.90 | 131K | Multimodal |
| `glm-4.5v` (vision) | $0.60 | $0.11 | $1.80 | 66K | Multimodal |

**Wallet impact:** Free-tier rows must not crash cost calculations and not display "$0.00 remaining" as if exhausted. Add `is_free_tier: bool` flag to cost record schema.

---

## §5 — MiMo (Xiaomi)

**API:** `https://api.xiaomimimo.com/v1` (OpenAI-compatible per official platform docs)
**Free tier:** Limited credit at signup; no perpetual free.
**Critical migration:** **MiMo-V2-Pro / Omni auto-route to V2.5 on 2026-06-01 (already happened); full deprecation 2026-06-30**. ARC should not target legacy V2-Pro names.
**Price drop event:** 2026-05-27, Xiaomi made V2.5 Pro permanent at $1.00/$3.00 (was $0.435/$0.87 promo). Flat-rate, no long-context multiplier.

| Model ID | Input | Cached input | Output | Context | Notes |
|---|---|---|---|---|---|
| `mimo-v2.5-pro` | $1.00 | $0.20 (80% off) | $3.00 | 1M | Flagship; 1T params / 42B active; MIT license |
| `mimo-v2.5` | $0.40 | $0.08 (80% off) | $2.00 | 1M | Multimodal (text+image+video+audio) |
| `mimo-v2-flash` | $0.10 | $0.02 | $0.40 | 256K | High-speed inference |
| `mimo-v2-pro` (legacy) | — | — | — | — | **Auto-routes to v2.5 as of 2026-06-01; deprecated 2026-06-30** |
| `mimo-v2-omni` (legacy) | $0.40 | — | $2.00 | 262K | Same — migrating to V2.5 |

**Important:** MiMo V2.5 is **MIT-licensed open weights** (1T params, 42B active). Self-hosting is viable if ARC ever wants to support a local-LLM backend (out of scope for now).

---

## §6 — MiniMax (bonus — appears in same routing configs)

Included because it shows up in the same Bailian gateway routing configs as Qwen/GLM/Kimi (per [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1rgufpk/openclaw_alibaba_cloud_coding_plan_8_frontier/)).

| Model ID | Input | Output | Context | Notes |
|---|---|---|---|---|
| `MiniMax-M2.5` | $0.30 | $1.20 | 1M | Standard |
| `MiniMax-M2.5-Lightning` | $0.30 | $2.40 | 200K | 2× faster, 2× output cost |
| `MiniMax-M2.7` | $0.39 | $1.56 | 200K | Newer mid-tier |
| `MiniMax-M2.7-Highspeed` | $0.78 | $3.12 | 200K | Faster variant |
| `MiniMax-M2.1` | $0.78 | $3.12 | 200K | Older speed tier |
| `MiniMax-M2-her` | $0.39 | $1.56 | 65K | Smaller context |

Per [screenapp.io](https://screenapp.io/blog/glm4-minimax-m25-pricing): SWE-Bench Verified 80.2% (vs Opus 4.6 ~79%), at roughly 1/20th Opus cost. Worth tracking.

---

## §7 — OpenRouter / gateway pass-through

ARC can adopt any of the above via OpenRouter without per-vendor account setup. Per [costgoat.com](https://costgoat.com/deals/openrouter.ai) and [promptcost.org](https://promptcost.org/en/blog/openrouter-pricing-guide-2026/):

| Aspect | OpenRouter | Direct vendor |
|---|---|---|
| Per-token markup on inference | **0%** (pass-through) | (base) |
| Credit purchase fee | 5.5% on non-crypto, $0.80 min | n/a |
| Cache discount pass-through | ✓ "around 90% off cached Anthropic input tokens, 50% off OpenAI" | per vendor (98% on DeepSeek, 80–90% elsewhere) |
| BYOK (Bring Your Own Key) | ✓ small platform fee instead of full markup | n/a |
| Chinese-phone gate | Bypassed | Often required |
| Single API key for 300+ models | ✓ | ✗ |
| Sample free tier | 25+ open-weight models, 50 req/day (1000 with $10 paid) | varies |

**For ARC v0.5+ planning:** OpenRouter is the path of least resistance. One `base_url=https://openrouter.ai/api/v1` config, one API key, all five vendors accessible. Pay the 5.5% credit-purchase fee or 0% on inference and accept it as the convenience tax.

Note: AIMLAPI, TokenMix, Ofox, Portkey are similar gateways with different fee structures. Ofox in particular advertises 0% credit-purchase fee.

---

## §8 — Changes to ARC required to support these vendors

### Minimal (v0.5-alpha-class, ~150 LOC)

1. **`providers/openai_compatible_cost.py`** — extend cost-record schema with:
   - `cached_input_usd_per_million: Decimal | None` (separate from `input_usd_per_million`)
   - `cache_field_names: dict[str, str]` — e.g., `{"hit": "prompt_cache_hit_tokens", "miss": "prompt_cache_miss_tokens"}` (DeepSeek) vs `{"read": "cache_read_input_tokens", "creation": "cache_creation_input_tokens"}` (Anthropic-style)
   - `is_free_tier: bool` (default False; True for GLM Flash, MiMo limited tiers)
   - `pricing_valid_until: date | None` for promo expirations
   - `auto_route_to: str | None` for legacy aliases (DeepSeek `deepseek-chat`, MiMo `mimo-v2-pro`)

2. **New seed rows for ~40 models** across the 5 vendors (rough count: DeepSeek 5, Qwen 7, Kimi 6, GLM 13, MiMo 5, MiniMax 6, +/- some legacy)

3. **Wallet display logic** — when `is_free_tier=True`, show `"FREE TIER"` instead of `"$X.XX / $cap"` for that model.

4. **Tokenizer fallback** — `len/4 × 1.33` heuristic will be increasingly wrong on CJK-trained tokenizers (Qwen, Kimi, GLM, MiMo, MiniMax). Flag in `/wallet` output as `≈ (heuristic, accuracy unverified for {model})`.

### Stretch (v0.6-alpha+, ~400 LOC)

5. **Per-model tokenizer support** — bundle Qwen/Kimi/GLM tokenizers (or use API token-count endpoints if cheap).
6. **`pricing_valid_until` enforcement** — warn on first use of a model whose pricing has expired; require user re-confirm.
7. **Multimodal token accounting** — separate `image_tokens`, `audio_tokens`, `video_tokens` buckets for the multimodal models (Qwen 3.7 Plus, Kimi K2.6, MiMo V2.5, GLM 4.6V). Different rates per modality, sometimes huge (e.g., Gemini's Native Audio model: $3.00/M audio input vs $0.50/M text).

### Out of scope for ARC

- **Subscription-plan parsing** (Zhipu Coding Plan $10–$80/quarter, separate from per-token API). Users on subscription plans should manually configure "free" cost rows.
- **Off-peak discount scheduling** (DeepSeek had 50–75% off at 16:30–00:30 UTC for V3). V4 off-peak not officially confirmed. Skip.

---

## §9 — Sources (all accessed 2026-06-04)

### DeepSeek
- [techjacksolutions.com/ai-tools/deepseek/deepseek-pricing](https://techjacksolutions.com/ai-tools/deepseek/deepseek-pricing/) (dated 2026-05-19)
- [tokenmix.ai/blog/deepseek-api-pricing](https://tokenmix.ai/blog/deepseek-api-pricing) (dated 2026-05-14)
- [verdent.ai/guides/deepseek-v4-pricing-api-migration-2026](https://www.verdent.ai/guides/deepseek-v4-pricing-api-migration-2026) (dated 2026-04-29)
- [devtk.ai/en/blog/deepseek-api-pricing-guide-2026](https://devtk.ai/en/blog/deepseek-api-pricing-guide-2026/) (dated 2026-05-24)

### Qwen
- [costbench.com/software/llm-api-providers/qwen-api](https://costbench.com/software/llm-api-providers/qwen-api/) (dated 2026-05-22)
- [codersera.com/blog/qwen-3-5-complete-guide-2026](https://codersera.com/blog/qwen-3-5-complete-guide-2026/) (dated 2026-05-27)
- [digitalapplied.com/blog/qwen-3-7-max-alibaba-flagship-ai-model-2026](https://www.digitalapplied.com/blog/qwen-3-7-max-alibaba-flagship-ai-model-2026) (dated 2026-05-25)
- [apidog.com/blog/qwen-3-7-plus](https://apidog.com/blog/qwen-3-7-plus/) (dated 2026-06-03)
- [techjacksolutions.com/ai-tools/qwen/qwen-pricing](https://techjacksolutions.com/ai-tools/qwen/qwen-pricing/) (dated 2026-05-29)

### Kimi
- [tokenmix.ai/blog/kimi-k2-api-pricing](https://tokenmix.ai/blog/kimi-k2-api-pricing) (dated 2026-05-15)
- [costgoat.com/pricing/kimi-api](https://costgoat.com/pricing/kimi-api) (dated 2026-05-21)
- [deepinfra.com/blog/kimi-k2-6-pricing-guide-deployment-tradeoffs](https://deepinfra.com/blog/kimi-k2-6-pricing-guide-deployment-tradeoffs) (dated 2026-04-30)
- [openrouter.ai/moonshotai/kimi-k2-thinking](https://openrouter.ai/moonshotai/kimi-k2-thinking) (older but currently accurate)

### GLM (Zhipu Z.AI)
- [vibecoding.app/blog/zhipu-ai-glm-pricing-2026](https://vibecoding.app/blog/zhipu-ai-glm-pricing-2026) (dated 2026-04-10)
- [pricepertoken.com/pricing-page/provider/z-ai](https://pricepertoken.com/pricing-page/provider/z-ai) (dated 2026-05-22) — *most comprehensive Z.AI table*
- [screenapp.io/blog/glm4-minimax-m25-pricing](https://screenapp.io/blog/glm4-minimax-m25-pricing) (dated 2026-02-14)
- [docs.z.ai/guides/llm/glm-4.5](https://docs.z.ai/guides/llm/glm-4.5) (official, older)

### MiMo (Xiaomi)
- [pricepertoken.com/pricing-page/model/xiaomi-mimo-v2.5-pro](https://pricepertoken.com/pricing-page/model/xiaomi-mimo-v2.5-pro) (dated 2026-04-29)
- [apidog.com/blog/xiaomi-mimo-v2-5-api-cost](https://apidog.com/blog/xiaomi-mimo-v2-5-api-cost/) (dated 2026-05-27)
- [platform.xiaomimimo.com/docs/en-US/updates/model](https://platform.xiaomimimo.com/docs/en-US/updates/model) (official deprecation timeline)
- [artificialanalysis.ai/models/mimo-v2-5-pro](https://artificialanalysis.ai/models/mimo-v2-5-pro) (dated 2026-04-22)

### MiniMax (bonus)
- [screenapp.io/blog/glm4-minimax-m25-pricing](https://screenapp.io/blog/glm4-minimax-m25-pricing)
- [aimlapi.com/ai-ml-api-pricing](https://aimlapi.com/ai-ml-api-pricing) (catalog reference)

### OpenRouter / gateways
- [costgoat.com/deals/openrouter.ai](https://costgoat.com/deals/openrouter.ai) (dated 2026-06-01)
- [promptcost.org/en/blog/openrouter-pricing-guide-2026](https://promptcost.org/en/blog/openrouter-pricing-guide-2026/) (dated 2026-04-19)
- [ofox.ai/blog/openrouter-alternatives-2026](https://ofox.ai/blog/openrouter-alternatives-2026/) (dated 2026-05-06)

---

## §10 — Open questions & deferred items

| Q | Resolution path |
|---|---|
| Does ARC's existing `openai_compatible.py` actually round-trip cache fields, or does it drop them? | Run grep on the local clone before v0.5 scoping |
| Should ARC support Anthropic-compatible mode for Qwen 3.7 Max (advertised drop-in)? | Probably yes; verify Anthropic SDK code path doesn't reject custom base_url |
| For multimodal models, can ARC reuse current token accounting or does it need a separate counter per modality? | Defer to v0.6+; first observe production-routing patterns |
| Do free-tier GLM models survive rate-limit pressure (i.e., are they actually free in practice or rate-limited to uselessness)? | Test by routing a sample workload through them before encoding `is_free_tier=True` |
| Off-peak discount support (DeepSeek 50–75% off at 16:30–00:30 UTC) | Probably out of scope — too vendor-specific |
| Tokenizer accuracy on CJK-heavy content (Qwen/Kimi/GLM) — is `len/4` wildly wrong? | Re-run `docs/research/token-estimator-accuracy.md` script with these vendors once routed |

---

## §11 — Cross-references

- Main pricing snapshot: `docs/research/pricing-snapshot-2026Q2.md` (Anthropic/OpenAI/Google)
- ARC's existing OpenAI-compatible adapter: `python/src/agent_runtime_cockpit/providers/openai_compatible.py`
- Wallet display: `python/src/agent_runtime_cockpit/budget/wallet.py`
- Token estimator brief: `docs/research/token-estimator-accuracy.md` (rerun needed for CJK-heavy tokenizers)
- Quarterly refresh procedure: `docs/research/pricing-snapshot-2026Q2.md` §4
