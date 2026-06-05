# Catalog-Driven Connection: Tradeoffs Analysis

> **Date:** 2026-06-04
> **Question:** Should ARC use a model catalog (OpenRouter / models.dev) to
> drive provider connection metadata (`base_url`, auth header, request shape)
> the way opencode does?
> **Verdict:** **No, not for the v0.x alpha series.** Catalog informs pricing
> + capability UI; hand-coded adapters drive the wire. This document locks
> the reasoning so future spec authors don't re-litigate it without
> understanding the threat-model implications.

---

## TL;DR

| What the catalog drives | Risk | Recommendation |
|---|---|---|
| **Pricing display** (wallet shows accurate $) | Low (worst case: wrong number displayed) | ✓ Adopted in v0.5.1-alpha-v3 |
| **Model picker UI** (which models can I switch to) | Low (worst case: dead model listed; user gets API error on use) | ✓ Recommended for v0.6-alpha |
| **Capability gating** (don't show vision toggle for text-only model) | Low-medium (worst case: feature available where it shouldn't be) | ✓ Recommended for v0.6-alpha |
| **Auth header pattern** (e.g., `Authorization: Bearer X` vs `x-api-key: X`) | **High** (worst case: API key sent to wrong endpoint with wrong header → credential leak) | ✗ Stays hand-coded |
| **Base URL** for actual requests | **High** (worst case: prompts routed to typosquat or compromised endpoint) | ✗ Stays hand-coded |
| **Request body shape** (OpenAI Chat Completions vs Anthropic Messages vs custom) | High (worst case: malformed request rejected, or worse, succeeds at wrong endpoint) | ✗ Stays hand-coded |
| **Response parsing** (where `cache_read_input_tokens` lives in the JSON) | Medium (worst case: silent wrong-cost calculation) | ✗ Stays hand-coded per vendor |

The pattern: **catalog informs surfaces the user sees and the wallet displays. Hand-coded adapters drive every byte that actually leaves the machine or carries a secret.**

---

## Three plausible architectures

### Architecture A — Catalog-informed UI (recommended)

```
┌────────────────────────────┐
│  models.dev / OpenRouter    │  (the catalog)
└────────────┬───────────────┘
             │ models, prices, capabilities
             ▼
┌────────────────────────────┐
│  /wallet, /models, picker  │  (UI surfaces; user-facing)
└────────────────────────────┘

┌────────────────────────────┐
│  AGENTS.md, user config     │  (the connection truth)
└────────────┬───────────────┘
             │ base_url, auth header, vendor block name
             ▼
┌────────────────────────────┐
│  providers/anthropic.py     │  (hand-coded adapters)
│  providers/openai_compatible.py
└────────────────────────────┘
```

Catalog and adapter layers are **independent**. Catalog data shapes UI; user config + hand-coded adapter blocks shape the wire.

This is what opencode does in practice (per their public README + the fact that openai_compatible-style providers exist in their codebase, not auto-generated from models.dev).

### Architecture B — Catalog-driven connections (Possibility 3)

```
┌────────────────────────────┐
│  models.dev / OpenRouter    │
└────────────┬───────────────┘
             │ models, prices, base_url, auth_pattern
             ▼
┌────────────────────────────┐
│  Dynamic adapter            │  (interprets catalog → makes request)
└────────────────────────────┘
```

Catalog drives both UI and wire. Adding a new vendor to the catalog auto-enables it in ARC.

**This is what opencode does NOT do** — and what ARC should not do — for the reasons in §"Why hand-coded adapters."

### Architecture C — Hybrid with allowlist

```
Catalog → list all models
Catalog → propose base_url + auth pattern for new vendors
User → reviews + approves in config
Hand-coded adapter → handles the wire after approval
```

This is a middle path. Useful if ARC's vendor surface grows much faster than dev-time. Not needed today.

---

## Why hand-coded adapters (Architecture A)

### 1. Auth header patterns are security-critical and provider-specific

Each vendor has slightly different conventions:
- Anthropic: `x-api-key: <key>` + `anthropic-version: 2023-06-01`
- OpenAI: `Authorization: Bearer <key>`
- Some Google endpoints: `?key=<key>` query string
- Vertex AI: GCP service account credentials, OAuth flow, or `Authorization: Bearer <token>` with token from gcloud
- Custom self-hosted: any of the above + custom

A catalog that says "use Bearer auth" can be wrong; even when right, sending the wrong key under the right header (e.g., your Anthropic key over `Authorization: Bearer`) **leaks the key to the wrong vendor's logs**.

Hand-coded adapter: the developer who wrote the adapter verified the auth pattern against vendor docs. The catalog cannot replace that audit.

### 2. Typosquat / impersonation resistance

If the catalog source is compromised (or a malicious PR slips through), it could add an entry pointing `base_url` to `https://api.anthopic.com/` (note the typo). ARC's request goes to attacker-controlled infrastructure carrying the user's Anthropic API key. Catastrophic.

Hand-coded `base_url`: the value lives in ARC's source code, reviewed by ARC's contributors, change-tracked in git. The threat model is the same as any other supply-chain attack on ARC's source.

### 3. Request shape isn't standardized

The illusion that "they're all OpenAI-compatible" is partly true and partly false:
- OpenAI Chat Completions: `{"messages": [...], "model": "...", "temperature": ...}`
- Anthropic Messages: `{"messages": [...], "model": "...", "max_tokens": ...}` — `max_tokens` REQUIRED, system goes outside `messages`
- Google Gemini native: `{"contents": [...], "generationConfig": {...}}` — entirely different shape
- OpenRouter (when used as gateway): OpenAI-compatible shape, but supports extra fields like `provider.api_key`
- Cohere, Mistral, etc.: variations

A catalog that says "this vendor speaks OpenAI Chat Completions" might be 95% right and the 5% (e.g., a vendor that drops `temperature` and requires `top_p` instead) causes silent failures.

Hand-coded adapter: the developer wrote a test against the live endpoint and confirmed the shape. The catalog cannot do this.

### 4. Response parsing for token accounting

Cache token field names are notoriously non-standard:
- Anthropic: `cache_creation_input_tokens`, `cache_read_input_tokens`
- DeepSeek: `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens`
- OpenAI Responses API: nested in `usage.input_tokens_details.cached_tokens`
- OpenRouter (when proxying): tries to normalize, may not perfectly mirror upstream

ARC's wallet display depends on this. A catalog that gets it wrong → wallet under-counts cache savings → users mis-estimate spend. Bug, not catastrophic, but user-trust-eroding.

Hand-coded `cache_field_names` map: per-vendor, in source code, reviewed. Same approach v0.5.1-alpha-v3 takes.

---

## Why catalog-informed UI is fine (Architecture A subset)

The risks above all stem from **catalog driving requests that go on the wire**. Catalog driving **display** has different failure modes:

| Catalog-driven UI failure | Worst case | User impact |
|---|---|---|
| Wrong price shown | Wallet under/over by X% | User notices; reviews; files bug |
| Dead model listed in picker | User selects; gets API error | Annoying; recoverable; user blames vendor or ARC, neither leaks secrets |
| Capability flag wrong (e.g., "vision" listed for text-only model) | User uploads image; vendor returns error | Same as above |
| Catalog briefly down | Picker shows last cached state | UX degradation; not security issue |

All of these are **recoverable** and **non-secret-leaking**. The catalog-informed UI fails closed: bad data → user gets an error from the vendor; no key leak, no wrong-endpoint routing.

---

## What opencode actually does (best read from public sources)

opencode is open-source [github.com/sst/opencode](https://github.com/sst/opencode); their public-facing usage of models.dev:

1. **Lists models in the UI picker** — pulled from models.dev
2. **Shows price per model in the picker** — pulled from models.dev
3. **Capability gating** (e.g., shows file-attachment toggle only for models with `attachment: true` in models.dev) — pulled from models.dev
4. **Connection layer** — opencode has hand-coded adapters per provider. Adding a vendor to models.dev does NOT auto-enable it in opencode; opencode must ship an adapter for that vendor's connection pattern.

So opencode is **Architecture A**, same recommendation as this document.

If anyone claims opencode does dynamic catalog-driven connections, they're conflating "the picker UI is dynamic" with "the connection layer is dynamic." Those are separate.

---

## What would have to change to adopt Possibility 3

If ARC ever wanted catalog-driven connections, it would need:

1. **A signed catalog source** (current OpenRouter + models.dev are NOT signed). Hash-pinning isn't enough; you need cryptographic provenance because a hash change is just "something changed," not "this change came from trusted authority."

2. **A capability-restricted runtime sandbox** — even with signatures, the connection layer should run in a context where the worst-case outcome of "catalog said send to X" is bounded (e.g., outbound traffic allow-list enforced at OS level, not just in ARC code).

3. **Per-vendor auth-pattern templates with type-safety** — not just "auth_header_name: Authorization", but a typed enum of (BearerToken, ApiKey, OAuthFlow, ...) where each pattern has explicit code paths.

4. **Explicit user opt-in per new vendor** — `arc provider trust <vendor-id> --review-config` showing the auth pattern, base_url, and request shape derived from the catalog, requiring user typed confirmation.

5. **Policy update** — `docs/policy/local-first.md` and `docs/policy/cosai-llm-in-path.md` companions or replacements describing the new threat model.

None of this is impossible. It's just a year of engineering work for a feature that **doesn't reduce token spend** (the actual North Star of the current token-saving sprint series). Out of scope for v0.x.

---

## Decision

| Question | Answer | Where it's implemented |
|---|---|---|
| Should catalog drive pricing display? | Yes | v0.5.1-alpha-v3 |
| Should catalog drive `/wallet` cost calculation? | Yes (via committed cost rows synced from catalog) | v0.5.1-alpha-v3 |
| Should catalog drive `/models` picker UI? | Recommended | v0.6-alpha (to be specced) |
| Should catalog drive capability gating in TUI? | Recommended | v0.6-alpha |
| Should catalog drive `base_url`? | **No** | Stays in `providers/openai_compatible.py` vendor blocks + `providers/anthropic.py` |
| Should catalog drive auth headers? | **No** | Stays hand-coded |
| Should catalog drive request body shape? | **No** | Stays hand-coded |
| Should catalog drive response parsing? | **No** | Stays hand-coded; `cache_field_names` per vendor in CostRate |

The pattern from `docs/policy/local-first.md` § L4 applies: third-party data
should **inform** ARC, not **drive** ARC's security-relevant behavior.

---

## Cross-references

- Source comparison: `docs/research/pricing-feed-sources-comparison.md`
- Pricing data sprint: `docs/spec/v0.5.1-alpha-chinese-labs-adoption-v3.md`
- UI catalog sprint (next): `docs/spec/v0.6-alpha-catalog-driven-picker.md`
- Policies: `docs/policy/local-first.md` (L4 no-surprise-exfiltration; this doc operationalizes it for catalogs), `docs/policy/cosai-llm-in-path.md`
- opencode reference: [github.com/sst/opencode](https://github.com/sst/opencode), [github.com/anomalyco/models.dev](https://github.com/anomalyco/models.dev)
- OpenRouter as alternative routing layer (different feature, not this sprint): user adds `https://openrouter.ai/api/v1` as a vendor block in openai_compatible.py with a manually configured base_url + Bearer auth; treated as one vendor among many, not as ARC's connection layer
