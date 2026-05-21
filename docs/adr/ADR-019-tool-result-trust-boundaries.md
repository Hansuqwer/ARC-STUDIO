# ADR-019: Tool Result Trust Boundaries

**Status:** Accepted  
**Date:** 2026-05-21  
**Context:** Phase 5 — Streaming, Tool Use, and Multi-Turn Sessions  
**Related:** ADR-011, ADR-014, ADR-018

## Context

Phase 5 introduces tool execution: the model emits a tool call, ARC executes a `ToolHandler`, and the result re-enters model context as a tool result. Tool code may be trusted while tool output is not. For example, `read_file` returns user-controlled file contents and `list_directory` returns attacker-controlled filenames. `get_current_time` returns system-controlled clock data.

ADR-014 requires external input and provider output to be explicitly trust-tagged before entering model context. Tool results need the same explicit boundary.

## Decision

Every `ToolHandler` declares `output_trust_level` at registration time:

- `untrusted` (default posture): output is wrapped as `<tool_result trust="untrusted" tool="...">...</tool_result>` and scanned before entering history. Filesystem, network, environment, subprocess, and user-controlled data MUST use this level.
- `trusted`: output is wrapped as `<tool_result trust="trusted" tool="...">...</tool_result>` and bypasses the injection scanner. Reserved for output with no user-controlled or externally-controlled component.
- `mixed`: reserved contract for future structured outputs with per-field trust. Phase 5 defines the type but wrapper execution raises `NotImplementedError`; implementation is deferred until a real mixed-trust tool exists.

`ToolRegistry` rejects handlers that omit `output_trust_level` or declare an invalid value. Tool results marked untrusted are scanned using ADR-014 patterns before they are appended to message history. Scanner blocks replace the result with `<tool_result trust="blocked" tool="..." reason="..."/>` and emit `tool.result.blocked`.

Phase 5 built-in declarations:

- `read_file`: `untrusted`
- `list_directory`: `untrusted`
- `get_current_time`: `trusted`

## Consequences

Positive:

- Tool trust is visible at definition and review time.
- New tools are safe by default because the secure posture is untrusted.
- Trusted output avoids scanner noise where the source is genuinely system-controlled.
- Mixed trust has a documented future contract without adding an unproven Phase 5 runtime path.

Negative:

- Tool authors must declare trust explicitly.
- A tool author can misdeclare trust; code review must validate the declaration.
- Mixed trust remains a deferred capability until a future phase needs it.

## Phase 5 Test Requirements

- Every registered tool has a declared `output_trust_level`.
- Trusted tools bypass the scanner.
- Untrusted tools are wrapped with `trust="untrusted"` and scanned.
- Scanner blocks produce a blocked wrapper plus `tool.result.blocked`.
- Mixed wrapper execution raises `NotImplementedError` with a deferral message.
- Built-in tools declare the trust levels above.

## Migration

No migration required. `ToolHandler` is introduced in Phase 5.
