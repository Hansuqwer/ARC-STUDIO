# v0.5.2-alpha Merge Notes

## What ships

**CostRate capability fields backfill — prerequisite for v0.6-alpha /models picker.**

Triggered by: Task 0 gap audit in v0.6-alpha sprint found that v0.5.1's `CostRate`
extension didn't include `supported_parameters` or `input_modalities`. The v0.6
`/models` picker requires per-model capability data for filtering (e.g.
`--has vision`, `--has tools`).

## Changes

### CostRates schema (`base.py`)

Two new fields, both additive with empty-list defaults:

```python
supported_parameters: list[str] = Field(default_factory=list)
input_modalities: list[str] = Field(default_factory=list)
```

All existing rows are unaffected (default `[]`). No migration needed.

### Vendor block backfill (`openai_compatible.py`)

48 of 57 Chinese-lab model rows updated with capability data from OpenRouter
(`architecture.input_modalities` + `supported_parameters`):

| Vendor | Rows updated | Notes |
|---|---|---|
| DeepSeek | 6 | All text-only; tools + reasoning + structured_outputs in params |
| Qwen | ~9/10 | 7 multimodal [text,image,video]; legacy `qwen2.5-72b` missed suffix match |
| Kimi | 5 | k2.5/k2.6 = [text,image]; k2 = [text] |
| GLM | 12 | v/vl models = [image,text,video]; others text-only |
| MiMo | 3 | mimo-v2.5 = [text,audio,image,video] — only model with audio in sprint |
| MiniMax | 6 | minimax-m3 = [text,image,video] |

Non-Chinese-lab vendors (OpenAI, Anthropic, Groq, etc.) left with empty defaults.
No OpenRouter data for these; v0.6 can backfill from native API schemas if needed.

### Sync script update

`scripts/sync_from_pricing_feed.py` now emits `supported_parameters` and
`input_modalities` in `render_vendor_block()` output. Future syncs will
automatically include capability data.

## Test delta

5030 (v0.5.1) → 5039 (+9). 9 new capability field tests.

## Pre-existing acceptable failures

Same as v0.5.1: `test_concurrent_accumulation` SQLite env flake + 5 xfailed.

## Branch

`spec/v0.5.2-capability-fields` — 4 commits — ready to merge.

**Do NOT tag yet. Awaiting your go.**
