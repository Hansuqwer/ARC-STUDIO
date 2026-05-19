# ADR-014: Security Architecture — Trust Model and Defense Layers

Status: Accepted
Date: 2026-05-19
Accepted: 2026-05-19
Deciders: ARC Studio core team
Parent ADR: ADR-011 (Full Parity Framing)
Related: ADR-013 (SwarmGraph Architecture Lock)
         ADR-015 (IDE Compliance Mode)

## Context

Prompt injection remains a material AI security risk. ARC Studio consumes external content from files, MCP tool outputs, web search results, fetched URLs, and worker outputs. Workspace trust alone is insufficient because injection risk attaches to individual content objects.

## Decision

ARC Studio implements a four-tier trust model with six defense layers, using SwarmGraph's queen/worker architecture for CaMeL-style Privileged/Quarantined separation.

### Four-Tier Trust Model

- Level 1 system: ARC system prompts, configs, code.
- Level 2 user: direct CLI and IDE input.
- Level 3 workspace: trusted workspace files and procedural guidance.
- Level 4 untrusted: tool outputs, MCP responses, web results, fetched URLs, file content read mid-session, downstream worker outputs.

Level 4 is data only, never instructions. Level 3 can guide but never override user or system instructions for security-critical decisions.

### Tagging Convention

External content uses origin-annotated XML tags such as `<untrusted_input origin="mcp:slack:list-messages" trust="4">`, `<workspace_input origin="file:AGENTS.md" trust="3">`, and `<user_input trust="2">`.

### Six Defense Layers

1. Tagging: all external content tagged with origin and trust.
2. Classification: untrusted content scanned before primary worker context.
3. Architectural separation: queen is Privileged; workers are Quarantined.
4. Output validation: worker outputs validated against declared schema.
5. Action gating: sensitive actions require confirmation.
6. Audit emission: every trust transition and authorization emits an audit event.

### Privileged Action Boundary

Workers request escalation; queens decide. Queen-only operations include authorizing paid model calls, writes outside workspace, workspace trust changes, gate modifications, classifier configuration changes, MCP server additions, and memory fact writes.

Workers can never modify ARC source code, disable audit chain, modify retention policy, or modify this trust model.

### MCP-Specific Defense

MCP requires per-workspace allowlists, manifest pinning, per-tool authorization, tool description sanitization, output isolation, and sandboxed execution. HTTP/SSE transports require container or microVM isolation when enabled.

### Worker Tool Visibility

Worker tools are filtered by built-in ARC tools, workspace tools, MCP allowlist, step requirements, and role trust. Workers do not see tools outside their step requirements.

## Consequences

The model gives defense-in-depth and maps to compliance evidence. Costs include classifier latency/cost, schema discipline, and possible HITL fatigue.

## Banned Claims Specific to This ADR

- "ARC is prompt-injection resistant" is unsafe until canonical attack tests pass.
- "Workspace trust eliminates injection risk" is unsafe.
- "L2 classifier catches all injections" is unsafe.
- "Workers can elevate privileges" is unsafe.
- "ARC's MCP integration is impenetrable" is unsafe.
- "Tool poisoning is impossible in ARC" is unsafe.
- "MCP rug pulls are silently prevented" is unsafe; they are detected and require repin.
- "External content can be trusted after classifier scan" is unsafe; trust remains level 4.

## Acceptance Criteria (Phase 4 ship)

- All six defense layers implemented and tested.
- Five canonical injection attack tests pass.
- Tool poisoning and rug pull tests pass.
- Worker bypass attempts blocked with audit events.
- Trust tagging applies to files, MCP output, web/fetch results, and worker outputs.
- Audit events emitted for every trust transition and authorization decision.
- Banned-claims script passes.
- L2 classifier integrated as model or deterministic ruleset.
