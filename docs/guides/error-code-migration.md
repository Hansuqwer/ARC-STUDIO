# Error Code Migration Guide

ADR-023 syncs Python and TypeScript error codes around one canonical 16-code vocabulary.

## TypeScript Replacements

| Deprecated | Use | Removal |
| --- | --- | --- |
| `TRACE_NOT_FOUND` | `RUN_NOT_FOUND` | v0.3.0 |
| `EXECUTION_FAILED` | `RUN_FAILED` | v0.3.0 |
| `PARSE_ERROR` | `INVALID_INPUT` | v0.3.0 |
| `WORKFLOW_NOT_FOUND` | `WORKSPACE_NOT_FOUND` | v0.3.0 |

## TypeScript

Before:

```ts
throw new ArcError(ArcErrorCode.TRACE_NOT_FOUND, `Trace not found: ${traceId}`);
```

After:

```ts
throw new ArcError(ArcErrorCode.RUN_NOT_FOUND, `Trace not found: ${traceId}`);
```

When reading older traces, normalize first:

```ts
const code = canonicalErrorCode(rawError.code);
```

## Python

Python gained `PERMISSION_DENIED`, `UNKNOWN`, and a read-path legacy mapper:

```py
ArcErrorCode.from_legacy("TRACE_NOT_FOUND")  # ArcErrorCode.RUN_NOT_FOUND
ArcErrorCode.from_legacy("UNKNOWN_NEW_CODE")  # ArcErrorCode.UNKNOWN
```

## Timeline

| Version | Behavior |
| --- | --- |
| v0.2.0 | Canonical codes available. Deprecated TS codes retained with original wire strings. |
| v0.3.0 | Deprecated TS enum members removed. |
| v0.4.0 | Python read-path shim may be removed after archived trace compatibility review. |

See ADR-023: `docs/adr/023-error-code-standardization.md`.
