# v0.7-alpha Merge Notes

## What shipped in this sprint

Three independent opt-in cloud features, **all default OFF**. With no env vars
set, ARC makes zero outbound calls beyond the user's configured LLM vendor.

### 1. Pricing feed (`cloud/pricing_feed.py`)
- `ARC_PRICING_FEED_ENABLED=1` to activate
- Primary: OpenRouter. Fallback: models.dev (`ARC_PRICING_FEED_SOURCE=models-dev`)
- **Hash-pinning** (not Ed25519 — neither source signs their feed): any change
  from the pinned SHA-256 is rejected; user runs `arc pricing-feed accept-new-hash`
- Fail-closed: network down / parse fail / hash mismatch → keep local
- 12 tests

### 2. Budget broker (`cloud/budget_broker.py`)
- Requires `ARC_BUDGET_BROKER_URL` + `_TOKEN` + `ARC_BUDGET_TEAM_ID`
- Sends only `{team_id, scope, amount}` — no prompts, no code
- Fail-closed: unreachable + `fallback_to_local=False` → DENY
- Local cap always the floor; broker can only further-restrict
- 12 tests

### 3. Observability bridge (`cloud/observability_bridge.py`)
- Requires `ARC_OBSERVABILITY_BRIDGE_URL` + per-session consent
- `sanitize_attributes()` strips prompt/code/context keys (defense-in-depth)
- otel-exporter-otlp is an optional extra; missing → graceful no-op
- 10 tests

### Cross-cutting
- 3 typed events mirrored Python + TS (6 TS tests)
- `/wallet` "Active opt-ins" section + status bar `cloud:` chip
- `docs/threat-models/v0.7-opt-in.md` (required by local-first.md)
- 6 default-off invariant tests

## Inherited from main since v0.6-alpha tag (NOT v0.7 work)

This branch was created from main HEAD `1aa2da5`, which is two commits past the
v0.6-alpha tag (`4de0eae`). v0.7 inherits but did not author:

- `86043fe` — non-Chinese-lab capability backfill + models.dev catalog (109
  providers) + `/models --max-context` filter (arena.ai follow-on session)
- `1aa2da5` — `capability_gates` fail-closed fix when vendor hint given but
  vendor not found

These are real changes that ride along to the v0.7 tag. They are not claimed
as v0.7 sprint work.

## Test delta

5091 baseline (1aa2da5) → 5131 (+40). TS: 149 → 155 (+6).

## Verification gates

| Gate | Result |
|------|--------|
| `ruff check src/ tests/` | ✅ clean |
| `pytest` (Python) | ✅ 5131 passed |
| TS build + test | ✅ 155 passed |
| Threat model exists | ✅ `docs/threat-models/v0.7-opt-in.md`, 3 feature sections |
| `test_no_outbound_calls_when_all_disabled` | ✅ |
| `test_no_export_without_consent` | ✅ |
| Protocol parity (Py ↔ TS) | ✅ |

## Behavior smokes

| Smoke | Result |
|-------|--------|
| 1. Default-off (no env) → 0 outbound calls | PASS (`test_no_outbound_calls_when_all_disabled`) |
| 2. Pricing feed happy path | SKIP-no-feed-deployed (verified by 12 unit tests w/ mocked urlopen) |
| 3. Budget broker | SKIP-no-broker-deployed (verified by 12 unit tests) |
| 4. Observability export | SKIP-no-destination (verified by 10 unit tests + consent gating) |

Live smokes deferred — no real feed/broker/OTLP endpoints deployed. All paths
verified by unit tests with mocked network per honesty-over-polish.md.

## Pre-existing acceptable failures

Same as v0.6: `test_concurrent_accumulation` SQLite env flake + 5 xfailed.

## Branch

`spec/v0.7-opt-in-cloud-features` — 7 commits — ready to merge.

**Do NOT tag yet. Awaiting your go.**
