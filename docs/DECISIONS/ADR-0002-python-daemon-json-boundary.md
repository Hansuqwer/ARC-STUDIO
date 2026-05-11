# ADR-0002: Python Daemon JSON Boundary

**Status:** Accepted  
**Date:** 2025

## Decision

The Theia backend service communicates with the Python ARC daemon via:

1. **Process execution** (CLI mode): spawn `uv run arc <cmd> --json` and parse stdout.
2. **HTTP** (daemon mode): `arc serve` starts a local HTTP server on `localhost:7777`.

All responses use the ARC Protocol Envelope:

```json
{
  "version": "1.0",
  "ok": true,
  "data": {},
  "error": null,
  "meta": { "duration_ms": 42 }
}
```

TypeScript validates every response before rendering. Invalid responses show an error state.

## Rationale

- JSON is language-agnostic and debuggable.
- Process execution works without a running daemon (useful for CI/tests).
- HTTP daemon enables real-time event streaming via SSE.
- Both modes use identical schemas (validated by Pydantic on Python side, Zod on TS side).
