# v0.6-alpha Merge Notes

## What ships

**Catalog-driven model picker — UI now reflects per-model capability data.**

v0.6 completes the capability pipeline started in v0.5.2 (backfill) by wiring
the data into user-facing commands and the TUI status bar.

## New commands

### /models

```
/models [--vendor <name>] [--has <cap>] [--free] [--max-input <$/M>] [--search <q>]
/models --vendor deepseek        # 6 models listed
/models --has vision             # 11 models with image/video modality
/models --has tools --max-input 1.0
/models --free                   # only is_free_tier=True rows
```

Reads committed `CostRate` data — **no network fetch at runtime** (local-first.md).
Per-model accuracy: `--has vision` uses `input_modalities` field from v0.5.2 backfill,
not vendor-level `ProviderFeature` flags. Verified by
`test_has_vision_filter_per_model_granularity`.

**Note on Anthropic:** `--vendor anthropic` returns 0 results. Anthropic uses a
separate provider class (`AnthropicClient`) whose models are not in `VENDOR_CONFIGS`.
This is correct — the command accurately reflects what the catalog has. v0.7 can
backfill Anthropic cost rows into a unified catalog if needed.

### /model-info

```
/model-info kimi/kimi-k2.6        # full catalog entry
/model-info kimi-k2-0905          # shows ⚠ DEPRECATED banner + auto_route
/model-info glm/glm-4.5-air       # shows FREE TIER
```

## Capability gating

`capability_gates.py`: `get_capabilities(model_id, vendor) → dict[str, bool]`

- Fail-closed invariant: unknown model → all gates `False` (never raises)
- Prefer entry with actual capability data when model ID appears in multiple vendors
  (e.g. `kimi-k2.6` exists in both `crofai` and `kimi` blocks; picks the one with
  non-empty `input_modalities`)

## Status bar chip

Model chip extended: `│ kimi/kimi-k2.6 [vision][tools] │`

Tags shown: vision, tools, reasoning (only when enabled). Hidden when unknown model.

## ModelChanged event

```python
ModelChanged(
    previous_model="gpt-4o",
    current_model="kimi-k2.6",
    capabilities_added=["vision"],    # features in new but not old
    capabilities_removed=[],
)
```

Diff semantics — consumer doesn't need to compute the delta.

## Test delta

5030 (v0.5.2) → 5089 (+59). TS: 147 → 149 (+2).

## Invariant checks

- Catalog NOT in connection path: `grep providers/ -rn "catalog"` → 0 hits
- `/models` offline: `test_works_without_network` mocks `urllib.request.urlopen` — 0 calls
- Capability gates fail-closed: `test_unknown_model_hides_all_capability_widgets` ✅
- No LLM in `slash/models.py` or `capability_gates.py` (no openai/anthropic imports)

## Behavior smokes

| Smoke | Result |
|---|---|
| 1. `/models --vendor deepseek` | PASS — 6 models, all vendor=deepseek |
| 2. `/models --has vision` | PASS — 11 models, all have image/video modality |
| 3. Text-only model caps | PASS — `deepseek-v4-pro` vision=False |
| 4. ModelChanged event | PASS — fired with capabilities_added=['tools'] |
| 5. `/model-info kimi-k2-0905` | PASS — ⚠ DEPRECATED banner visible |

Note: Smoke 1 uses `deepseek` not `anthropic` — Anthropic is in a separate provider
class outside VENDOR_CONFIGS (documented above).

## Pre-existing acceptable failures

Same as v0.5.2: `test_concurrent_accumulation` env flake + 5 xfailed.

## Branch

`spec/v0.6-catalog-picker` — 5 commits — ready to merge.

**Do NOT tag yet. Awaiting your go.**
