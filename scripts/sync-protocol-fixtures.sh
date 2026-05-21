#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_FIXTURES="$ROOT/python/tests/contract/fixtures"
TS_FIXTURES="$ROOT/packages/arc-protocol-ts/test/fixtures/protocol"

mkdir -p "$TS_FIXTURES"

sync_dir() {
  local name="$1"
  rm -rf "$TS_FIXTURES/$name"
  mkdir -p "$TS_FIXTURES/$name"
  cp -R "$PY_FIXTURES/$name/." "$TS_FIXTURES/$name/"
}

sync_dir "cost-record"

mkdir -p "$TS_FIXTURES/cache-breakpoints" "$TS_FIXTURES/runtime-capability" "$TS_FIXTURES/event-envelope"

cat > "$TS_FIXTURES/cache-breakpoints/messages-basic.json" <<'JSON'
{
  "messages": [
    { "index": 0, "tokens": 512 },
    { "index": 1, "tokens": 2048 }
  ],
  "threshold_tokens": 1024,
  "expected": [
    { "position": "messages", "index": 1 }
  ]
}
JSON

cat > "$TS_FIXTURES/runtime-capability/v2-provider-backed.json" <<'JSON'
{
  "schema_version": 2,
  "mode": "provider_backed",
  "profile_id": "default",
  "isolation_id": "none",
  "allow_paid_calls": true,
  "cost_source_default": "measured",
  "supports_cancellation": true,
  "supports_streaming": false
}
JSON

cat > "$TS_FIXTURES/event-envelope/ok.json" <<'JSON'
{
  "version": "1.0",
  "ok": true,
  "data": { "status": "ok" },
  "error": null,
  "meta": { "timestamp": "2026-05-21T00:00:00Z" }
}
JSON

echo "Synced protocol fixtures to $TS_FIXTURES"
