# OTel GenAI Semconv — Cache Attribute Names

> **Snapshot date:** 2026-06-04
> **Question:** Do ARC's R-03 attribute names match the OpenTelemetry GenAI
> semantic conventions?
> **Verdict:** ⚠ **DIVERGES** — ARC ships `gen_ai.usage.cache_read_input_tokens`
> (underscore). Spec uses `gen_ai.usage.cache_read.input_tokens` (**DOT**
> between `cache_read` and `input_tokens`). Same for cache_creation.
> Migration is small but should land in v0.4.0-alpha (alias both names).

---

## §1 — The verdict

| Attribute | ARC (R-03, shipped 2026-06-04) | OTel semconv | Match? |
|---|---|---|---|
| Cache-read tokens | `gen_ai.usage.cache_read_input_tokens` | `gen_ai.usage.cache_read.input_tokens` | ⚠ off-by-one-dot |
| Cache-write tokens | `gen_ai.usage.cache_creation_input_tokens` | `gen_ai.usage.cache_creation.input_tokens` | ⚠ off-by-one-dot |

The semantic intent matches exactly. The string form differs by one character per attribute. Downstream OTel-aware tooling (Portkey, Traceloop, Arize, Helicone) follows the dotted form per spec.

---

## §2 — Spec status

The cache attributes were added to OpenTelemetry semantic conventions in a release dated **2026-02-19** per the [open-telemetry/semantic-conventions releases page](https://github.com/open-telemetry/semantic-conventions/releases) (accessed 2026-06-04):

> gen-ai: Add cache token attributes and provider-specific normalization
> guidance for GenAI usage metrics (#1959)
> - Add `gen_ai.usage.cache_read.input_tokens` attribute for tokens served
>   from provider cache
> - Add `gen_ai.usage.cache_creation.input_tokens` attribute for tokens
>   written to provider cache
> - Add provider-specific token handling notes to OpenAI span
> - Add Anthropic span with computation guidance for `gen_ai.usage.input_tokens`

This is now **Development** status (not yet Stable), but the names are settled. The spec also lands provider-specific normalization guidance — see §4.

Sources verified:
- [opentelemetry.io/docs/specs/semconv/gen-ai/anthropic](https://opentelemetry.io/docs/specs/semconv/gen-ai/anthropic/) — uses `cache_read.input_tokens` (accessed 2026-06-04)
- [opentelemetry.io/docs/specs/semconv/gen-ai/openai](https://opentelemetry.io/docs/specs/semconv/gen-ai/openai/) — uses `cache_read.input_tokens` (accessed 2026-06-04)
- [opentelemetry.io/docs/specs/semconv/gen-ai/azure-ai-inference](https://opentelemetry.io/docs/specs/semconv/gen-ai/azure-ai-inference/) — same (accessed 2026-06-04)
- Origin issue: [github.com/open-telemetry/semantic-conventions/issues/1959](https://github.com/open-telemetry/semantic-conventions/issues/1959) (filed 2025-03-05, closed Feb 2026)
- Origin issue: [github.com/open-telemetry/semantic-conventions/issues/2094](https://github.com/open-telemetry/semantic-conventions/issues/2094) (filed 2025-04-12) — proposed `gen_ai.usage.input_cache_read_tokens` but spec ultimately adopted `cache_read.input_tokens` per the closed PR

---

## §3 — Industry comparison table

| Source | Cache-read attr | Cache-write attr | Aligned with spec? |
|---|---|---|---|
| **ARC R-03 (this repo)** | `gen_ai.usage.cache_read_input_tokens` | `gen_ai.usage.cache_creation_input_tokens` | ⚠ no |
| **OTel semconv** (Anthropic/OpenAI/Azure spans) | `gen_ai.usage.cache_read.input_tokens` | `gen_ai.usage.cache_creation.input_tokens` | (spec) |
| **Portkey** | `gen_ai.usage.cache_read.input_tokens` | `gen_ai.usage.cache_creation.input_tokens` | ✓ |
| **Traceloop openllmetry** (per article cite) | `gen_ai.usage.cached_tokens` (older form) | not split | ⚠ different — predates spec |
| **Anthropic SDK field names** (source data) | `cache_read_input_tokens` | `cache_creation_input_tokens` | (SDK, not OTel) |

ARC's names happen to match the **Anthropic SDK field shape exactly** (underscored, no dot), which is probably why R-03 ended up with them. The spec author chose a dotted hierarchy because `gen_ai.usage.cache_read.*` may later carry sub-attributes (modality, time-window, etc.).

Portkey docs are the most concrete confirmation that downstream tooling expects the dotted form. [portkey.ai/docs/product/observability/opentelemetry](https://portkey.ai/docs/product/observability/opentelemetry) (accessed 2026-06-04).

---

## §4 — One critical spec note ARC must verify separately

From the [Anthropic spec page](https://opentelemetry.io/docs/specs/semconv/gen-ai/anthropic/) (accessed 2026-06-04):

> `gen_ai.usage.input_tokens`: Anthropic `input_tokens` **excludes** cached
> tokens.
> Compute: `gen_ai.usage.input_tokens = input_tokens + cache_read_input_tokens + cache_creation_input_tokens`

**This means ARC's `observability/otel_mapping.py:181` may be emitting
the wrong `gen_ai.usage.input_tokens` value** if it copies Anthropic's raw
`usage.input_tokens` directly. The spec requires you to *add* the two cache
fields back in before emitting.

**Verification command:**
```bash
grep -n "input_tokens\|cache_read\|cache_creation" \
  python/src/agent_runtime_cockpit/observability/otel_mapping.py
```

If line ~181 sets `gen_ai.usage.input_tokens` directly from `usage.input_tokens`, it under-reports total input. This is a **separate bug** from the naming divergence and should be fixed in the same patch.

---

## §5 — Migration plan

### v0.4.0-alpha (recommended — bundle with R-01)

1. **Edit `observability/otel_mapping.py:181`:** emit *both* attribute names in parallel.

```python
attrs = {
    # Existing — keep for backward compat through one release
    "gen_ai.usage.cache_read_input_tokens": cache_read,
    "gen_ai.usage.cache_creation_input_tokens": cache_creation,
    # NEW — spec-aligned dotted form
    "gen_ai.usage.cache_read.input_tokens": cache_read,
    "gen_ai.usage.cache_creation.input_tokens": cache_creation,
    # FIX: compute spec-compliant input_tokens (Anthropic case)
    "gen_ai.usage.input_tokens": raw_input + cache_read + cache_creation,
    "gen_ai.usage.output_tokens": output,
}
```

2. **Edit `GENAI_REQUIRED_MODEL_CALL` tuple at `observability/otel_mapping.py:362-368`:** add the dotted-form names.

3. **CHANGELOG entry under `[Unreleased] → Changed`:**
```
- **Observability**: Now emits both the spec-aligned dotted form
  (`gen_ai.usage.cache_read.input_tokens`, etc.) AND the underscored form
  from R-03 for backward compat. Underscored form deprecated, removal
  planned for v0.6.0-alpha. Aligns ARC with OpenTelemetry GenAI semconv
  release 2026-02-19 (#1959).
- **Observability (fix)**: `gen_ai.usage.input_tokens` now correctly
  includes cached tokens for Anthropic spans per spec
  (input_tokens = base + cache_read + cache_creation).
```

### v0.5.0-alpha

Emit deprecation warning when downstream code reads the underscored name. Keep emitting both.

### v0.6.0-alpha

Drop underscored names. Keep dotted only. (Approximately 4 months of overlap window.)

---

## §6 — Action items

1. ✅ **Bundle into R-01 v0.4.0-alpha** — adds <30 LOC to `otel_mapping.py` + 2 test cases. Cheap.
2. ⚠ **Verify `gen_ai.usage.input_tokens` computation for Anthropic** — separate from naming, this may already be a quiet bug. Run grep, file separate issue if confirmed.
3. ⏳ **Watch the spec** — `gen_ai.usage` cache attributes are currently "Development" status. Stable release will likely happen alongside `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` becoming default. Re-snapshot in Q4 2026.
4. (Optional) **File an issue / discussion** at [open-telemetry/semantic-conventions](https://github.com/open-telemetry/semantic-conventions) flagging that ARC's deprecation timeline interacts with the spec stability transition; ask for guidance on the right alias period for consumers like us.

---

## §7 — Cross-references

- R-03 ship: `python/src/agent_runtime_cockpit/observability/otel_mapping.py:180-182`
- R-03 validator tuple: `observability/otel_mapping.py:362-368` (`GENAI_REQUIRED_MODEL_CALL`)
- R-03 patch: `patches/tokens/p0/005_otel_cache_fields.patch`
- Spec: [opentelemetry.io/docs/specs/semconv/gen-ai/anthropic](https://opentelemetry.io/docs/specs/semconv/gen-ai/anthropic/) (accessed 2026-06-04)
- Spec release notes: [github.com/open-telemetry/semantic-conventions/releases](https://github.com/open-telemetry/semantic-conventions/releases) (accessed 2026-06-04)
