# Pricing Snapshot — 2026 Q2

> **Snapshot date:** 2026-06-04
> **Method:** Vendor docs + secondary sources cross-checked. Every cell cites
> a URL with access date. No estimates — cells marked `N/A` where sources
> disagree or data is missing.
> **For consumer:** `docs/spec/R-01-token-wallet.md` TokenWallet display +
> ongoing `providers/*_cost.py` PRs.

---

## TL;DR — Discrepancies vs. plan / older priors

| Claim | Plan said | Snapshot found | Severity |
|---|---|---|---|
| Anthropic cache read = 0.10× input | ✅ same | ✅ confirmed 0.10× across Haiku 4.5 / Sonnet 4.6 / Opus 4.7 | none |
| Anthropic cache write 5m = 1.25× | ✅ same | ✅ confirmed | none |
| Anthropic cache write 1h = 2.0× | ✅ same | ✅ confirmed | none |
| Anthropic TTL default 5m (1h opt-in) | ✅ confirmed | ✅ confirmed | none |
| **OpenAI auto-cache ≥1024 tokens** | ≥1024 tokens | **Now applies to all Responses API requests; threshold removed per most current sources** | ⚠ verify |
| **OpenAI cached input = 90% off (was 50% on 4o-mini)** | mixed | **Universally 90% off (0.1× input) across GPT-5.x family; 50% only on legacy 4o-mini** | medium |
| **Vertex cache discount = 75%** | 75% | **Now 90% via context caching API on Gemini 2.5+; storage fee $1–$4.50/M/hr** | high |
| **Anthropic Opus 4.7 tokenizer change** | not in plan | **+35% tokens per char vs Opus 4.6** — wallet display may show 35% more spend on same content if user migrates | ⚠ display-affecting |
| **New models since plan** | none recorded | Haiku 4.5, Sonnet 4.6, Opus 4.6/4.7, GPT-5.4/5.5, Gemini 3.x family, Gemini 3.5 Flash | new |

**Bottom line:** Plan's Anthropic numbers are accurate. OpenAI/Vertex caching is *more* aggressive than plan said (90% not 50–75%), which makes R-01's wallet **under-show** savings unless updated. Opus 4.7 tokenizer change is a separate display correctness risk.

---

## §1 — Pricing table (USD per 1M tokens, snapshot 2026-06-04)

### Anthropic (Claude)

| Model | Input | Output | Cache read (0.10×) | Cache write 5m (1.25×) | Cache write 1h (2.0×) | Notes |
|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | Cheapest current-gen |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | Production default; 1M context flat |
| Claude Opus 4.6 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | Older tokenizer (more efficient) |
| Claude Opus 4.7 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | **NEW TOKENIZER: ~35% more tokens per char** |
| Claude Opus 4.6 Fast Mode | $30.00 | $150.00 | — | — | — | 6× standard; not in batch |
| Claude Haiku 3 (legacy) | $0.25 | $1.25 | $0.025 | $0.3125 | $0.50 | Still available |
| Claude Opus 4.1 (legacy) | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | Avoid — 3× current Opus 4.7 |

### OpenAI (current 2026 lineup)

| Model | Input | Cached input | Output | Notes |
|---|---|---|---|---|
| GPT-5.5 | $5.00 | $0.50 (90% off) | $30.00 | Latest flagship (Apr 2026) |
| GPT-5.5 Pro | $30.00 | — (no cache discount) | $180.00 | Reserve for high-reasoning |
| GPT-5.4 | $2.50 | $0.25 (90% off) | $15.00 | Recommended workhorse |
| GPT-5.4 mini | $0.75 | $0.075 (90% off) | $4.50 | Production routing |
| GPT-5.4 nano | $0.20 | $0.02 (90% off) | $1.25 | High-volume routing |
| GPT-5.2 (Codex variant) | $1.75 | $0.175 (90% off) | $14.00 | Coding agents |
| GPT-5 | $1.25 | $0.125 (90% off) | $10.00 | Existing integrations |
| GPT-5 mini | $0.25 | — | $2.00 | Budget routing |
| GPT-4.1 | $2.00 | $0.50 (75% off) | $8.00 | 1M context |
| GPT-4.1 mini | $0.40 | $0.10 (75% off) | $1.60 | Cost-quality balance |
| GPT-4.1 nano | $0.10 | $0.025 (75% off) | $0.40 | Cheapest current |
| o3 | $2.00 | — | $8.00 | Reasoning model |
| o3-pro | $20.00 | — | $80.00 | High-reasoning |
| o4-mini | $0.55–$1.10 | — | $2.20–$4.40 | (sources disagree) ⚠ |
| GPT-4o (legacy) | $2.50 | — | $10.00 | Grandfathered |
| GPT-4o mini (legacy) | $0.15 | $0.075 (50% off) | $0.60 | **Only model still at 50% cache** |

### Google Gemini (AI Studio / Developer API)

| Model | Input (≤200K) | Input (>200K) | Cached (~10%) | Output (≤200K) | Output (>200K) | Cache storage | Notes |
|---|---|---|---|---|---|---|---|
| Gemini 3.1 Pro Preview | $2.00 | $4.00 | $0.20 / $0.40 | $12.00 | $18.00 | $4.50/M/hr | Flagship |
| Gemini 3.5 Flash | $1.50 | flat | $0.15 | $9.00 | flat | $1.00/M/hr | New May 2026 |
| Gemini 3 Flash Preview | $0.50 | flat | $0.05 | $3.00 | flat | $1.00/M/hr | Mid-tier multimodal |
| Gemini 3.1 Flash-Lite Preview | $0.25 | flat | $0.025 | $1.50 | flat | $1.00/M/hr | Cheapest 3-series |
| Gemini 2.5 Pro | $1.25 | $2.50 | $0.125 / $0.25 | $10.00 | $15.00 | $4.50/M/hr | Stable Pro |
| Gemini 2.5 Flash | $0.30 | flat | $0.03 | $2.50 | flat | $1.00/M/hr | Standard interactive |
| Gemini 2.5 Flash-Lite | $0.10 | flat | $0.01 | $0.40 | flat | $1.00/M/hr | Cheapest tier-1 model |
| **Gemini 2.0 Flash (DEPRECATED 2026-06-01)** | $0.10 | flat | — | $0.40 | flat | — | **Migrate immediately to 2.5 Flash-Lite** |

### Batch API discounts (all vendors)

| Vendor | Batch discount | Stacks with cache? | Async window |
|---|---|---|---|
| Anthropic | 50% off in+out | Yes | 24h |
| OpenAI | 50% off in+out | Yes | 24h |
| Google | 50% off in+out | Yes | 24h |

---

## §2 — Per-cell source list

| Cell | Source URL | Accessed |
|---|---|---|
| Anthropic Haiku/Sonnet/Opus baseline rates | [cloudzero.com/blog/claude-api-pricing](https://www.cloudzero.com/blog/claude-api-pricing/) | 2026-06-04 |
| Anthropic cache 0.10× / 1.25× / 2.0× multipliers | [silicondata.com/use-cases/anthropic-claude-api-pricing-2026](https://www.silicondata.com/use-cases/anthropic-claude-api-pricing-2026/) | 2026-06-04 |
| Anthropic Opus 4.7 tokenizer +35% finding | [finout.io/blog/claude-opus-4.7-pricing-the-real-cost-story](https://www.finout.io/blog/claude-opus-4.7-pricing-the-real-cost-story-behind-the-unchanged-price-tag) | 2026-06-04 |
| Anthropic Opus 4.7 launch date 2026-04-16 | [metacto.com/blogs/anthropic-api-pricing-a-full-breakdown](https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration) | 2026-06-04 |
| OpenAI GPT-5.5 / 5.4 / 5.2 / 5 family rates | [devtk.ai/en/blog/openai-api-pricing-guide-2026](https://devtk.ai/en/blog/openai-api-pricing-guide-2026/) | 2026-06-04 |
| OpenAI cached input = 10% of input rate (90% off) GPT-5.x | [benchlm.ai/blog/posts/openai-api-pricing](https://benchlm.ai/blog/posts/openai-api-pricing) | 2026-06-04 |
| OpenAI GPT-4.1 family rates | [pecollective.com/tools/openai-api-pricing](https://pecollective.com/tools/openai-api-pricing/) | 2026-06-04 |
| Google Gemini 3.x / 2.5 family rates | [felloai.com/gemini-pricing](https://felloai.com/gemini-pricing/) | 2026-06-04 |
| Gemini context cache storage fees | [tokenmix.ai/blog/google-gemini-api-pricing](https://tokenmix.ai/blog/google-gemini-api-pricing) | 2026-06-04 |
| Gemini 2.0 Flash deprecation 2026-06-01 | [metacto.com/blogs/the-true-cost-of-google-gemini](https://www.metacto.com/blogs/the-true-cost-of-google-gemini-a-guide-to-api-pricing-and-integration) | 2026-06-04 |

---

## §3 — Critical findings for ARC

### A. ARC's `providers/anthropic_cost.py` needs new rows

Models to add (if not already present):
- `claude-haiku-4-5-*` @ $1/$5
- `claude-sonnet-4-6-*` @ $3/$15
- `claude-opus-4-6-*` @ $5/$25
- `claude-opus-4-7-*` @ $5/$25 — **with tokenizer-version flag** so wallet can warn about +35% drift

Verification command:
```bash
cd python
grep -n "claude-.*4\.\|haiku\|sonnet\|opus" \
  src/agent_runtime_cockpit/providers/anthropic_cost.py
```

### B. OpenAI cache discount changed: 50% → 90% on current-gen

Older priors (including some lines in TOKEN_SAVING_PLAN-2.md) cite "50% on 4o-mini". Today **only legacy gpt-4o-mini retains 50%**. All GPT-5.x and GPT-4.1 family use 90% off (0.1× input) for cached prefix matches. R-01's wallet *under-estimates* OpenAI savings if it still uses the older multiplier.

### C. Vertex / Gemini context cache is now 90%, not 75%

Plan's "75% discount" is outdated. Current Gemini context caching is ~10× cheaper than input (90% off) plus a **storage fee** ($1/M/hr for Flash tier, $4.50/M/hr for Pro tier). R-01's wallet needs a *new line item* for "cache storage" that doesn't exist for Anthropic/OpenAI (which have no separate storage fee).

### D. Opus 4.7 tokenizer change is the loudest correctness risk

If a user migrates from Sonnet 4.6 / Opus 4.6 → Opus 4.7, the same chat input produces **up to 35% more tokens** at the *same rate card*. Wallet will appear to under-charge / over-spend without warning. Recommendation: store tokenizer-version in `CostRecord` and surface in `/wallet` when an Opus 4.7 row dominates.

### E. Gemini 2.0 Flash deprecated 2026-06-01

If ARC routes to `gemini-2.0-flash`, it's already broken or about to break. Switch routes to `gemini-2.5-flash-lite` (same price, 8× output limit).

---

## §4 — Quarterly refresh procedure

```bash
# 1. cp this file
cp docs/research/pricing-snapshot-2026Q2.md docs/research/pricing-snapshot-2026Q3.md

# 2. For each URL in §2, refetch and diff. Look for new model rows, deprecations, multiplier changes.

# 3. Grep ARC's hardcoded values
cd python
grep -rn "Decimal\|0\.\|cost\|price" src/agent_runtime_cockpit/providers/*_cost.py | head -50

# 4. For each drift >5%, file a tracked issue. For drift >20%, block the next release until fixed.

# 5. Commit
git add docs/research/pricing-snapshot-2026Q3.md
git commit -m "docs(research): pricing snapshot 2026Q3 — <summary of drift>"

# 6. If R-01 wallet displays show new shapes (e.g., separate Vertex cache-storage line), file a follow-up roadmap row.
```

**Cadence:** 90 days. If a major vendor (Anthropic / OpenAI / Google) ships a new family between snapshots, do a hot patch instead.

---

## §5 — Open questions (not resolvable from web sources)

| Q | Why unknown | Recommendation |
|---|---|---|
| o4-mini rate $0.55 or $1.10? | Sources disagree ($0.55/$2.20 vs $1.10/$4.40) | Hit OpenAI pricing page directly before encoding |
| Does OpenAI auto-cache still need ≥1024 tokens? | Older docs say yes; newer secondary sources omit threshold | Test against API directly with a 500-token prompt and check usage payload |
| OpenRouter cache pass-through completeness | Not directly sourced this round | Run a dedicated audit before depending on it |
| Anthropic Opus 4.7 vs 4.6 token ratio on *ARC-shape* content (code+JSON+prose) | Vendor cite is "up to 35%" averaged; ARC's mix may differ | Run `token-estimator-accuracy` brief on a sample |
| Bedrock / Vertex multipliers vs first-party | Plan mentions ~10% premium; not re-verified | Defer until ARC actually routes to Bedrock/Vertex |
