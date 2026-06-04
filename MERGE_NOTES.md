# v0.5.1-alpha Merge Notes

## What ships

**Chinese-lab / open-weight vendor adoption — first batch.**

6 new vendor families route via `providers/openai_compatible.py`. No new provider class. No new mandatory dependencies. Gemini block (`if self._vendor == "gemini"` caching guard at `8cdc378`) untouched.

### Vendors

| Vendor | Native API | Models | Notes |
|---|---|---|---|
| DeepSeek | `api.deepseek.com/v1` | 6 | Cache field names: `prompt_cache_hit_tokens`; `deepseek-chat` deprecated 2026-07-24 |
| Qwen (Alibaba) | `dashscope.aliyuncs.com/compatible-mode/v1` | 10 | `tokenizer_family=qwen`; all rows get `≈` qualifier in `/wallet` |
| Kimi (Moonshot) | `api.moonshot.ai/v1` | 5 | `kimi-k2-0905` deprecated 2026-05-25; K2.6 is current flagship |
| GLM (Z.AI) | `open.bigmodel.cn/api/paas/v4/` | 12 | `glm-4.5-air` is free-tier per OpenRouter; `tokenizer_family=glm` |
| MiMo (Xiaomi) | `api.xiaomimimo.com/v1` | 3 | OpenRouter has 3 active models (legacy V2-Pro/Omni absent from OpenRouter) |
| MiniMax | `api.minimax.io/v1` | 6 | `minimax-m3` is new flagship ($0.30/$1.20/M) |
| CrofAI proxy | `crof.ai/v1` | 17 | Unified proxy; all of the above under one `CROFAI` key |

**Total: 91 OpenRouter-sourced model rows** (pricing cross-checked against OpenRouter `/api/v1/models` on 2026-06-05 via `scripts/sync_from_pricing_feed.py`).

### OpenRouter `:free` tier vs vendor-direct free

4 rows are marked `is_free_tier=True`: `glm-4.5-air:free`, `kimi-k2.6:free`, `qwen3-next:free`, `qwen3-coder:free`. These are **OpenRouter rate-limited free-tier variants**, not vendor-direct perpetually free models. `/wallet` shows `FREE TIER (via OpenRouter free tier; rate-limited)` — not `$0.00` to avoid confusion with exhausted caps.

### CostRates schema extension

6 new optional fields on `CostRates` (additive; all existing rows unaffected):

| Field | Purpose |
|---|---|
| `is_free_tier` | Wallet skips enforcement; shows "FREE TIER" |
| `pricing_valid_until` | ISO date; triggers ⚠ EXPIRED warning |
| `auto_route_to` | Server-side routing alias; shown in wallet |
| `cache_field_names` | Per-vendor cache token field names (e.g. DeepSeek) |
| `tokenizer_family` | Non-cl100k → `≈` qualifier in wallet |
| `cache_storage_usd_per_million_per_hour` | Vertex/Gemini storage fee (reserved) |

### Wallet display

`/wallet` now shows per-model annotations when a provider+model is active in session:
- `is_free_tier=True` → `FREE TIER (via OpenRouter free tier; rate-limited)`
- Expired `pricing_valid_until` → `⚠ EXPIRED — use <auto_route_to>`
- Non-cl100k tokenizer → `≈ cost (tokenizer_family=X; heuristic accuracy unverified)`
- `auto_route_to` (non-expired) → `(routed to X)`

## Pricing source decision

OpenRouter (`/api/v1/models`) chosen over models.dev. Rationale locked in `docs/research/pricing-feed-sources-comparison.md`. Decision fields (`is_free`, `deprecation_date`, `canonical_slug`) are native in OpenRouter; addendum overlay applied for 2 IDs not flagged by OpenRouter (`deepseek-chat` 2026-07-24, `kimi-k2-0905` 2026-05-25).

## Test delta

Python: 4979 (v0.5.0) → 5030 passed (+51). TS: 147 (unchanged).

Pre-existing acceptable failures (same as v0.5.0):
- `test_concurrent_accumulation` — SQLite lock, env-specific
- 5 xfailed: 2 CLI doctor exit-code, 1 CLI runs mode, 2 TUI snapshot SVG-hash

## Behavior smokes

**Smoke 1 (DeepSeek round-trip):** SKIP-no-key — no DeepSeek native account. Pricing verified by unit test (`test_deepseek_v4_pro_openrouter_price`).

**Smoke 2 (GLM free tier):** SKIP-no-key — no GLM native account. Free-tier rendering verified by `test_free_tier_shows_free_tier_label`. CrofAI key available for end-to-end test: `CROFAI_VENDOR=crofai ARC_MODEL=glm-4.7-flash uv run arc` will show FREE TIER annotation.

## Branch

`spec/v0.5.1-chinese-labs` — 9 commits — ready to merge to `main`.

**Do NOT tag yet. Awaiting your go.**
