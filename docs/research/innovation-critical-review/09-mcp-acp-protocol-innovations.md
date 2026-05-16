# MCP / ACP Protocol Innovations

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

## Core Critique

Do not “add MCP” as a checkbox. MCP is becoming table stakes. ARC’s opportunity is to be the **safety, evidence, and orchestration cockpit over MCP/ACP-style tools and agents**.

## MCP Opportunities

| Opportunity | ARC-specific angle | Avoid |
|---|---|---|
| Tool permission mapping | Map MCP tools into ARC policy categories: read, write, shell, network, paid, credential, external state. | Trusting natural-language tool descriptions. |
| Tool evidence obligations | Require tools to return evidence refs or structured outputs for claims. | Letting tool text become unverified claims. |
| Tool risk preview | Show MCP server capabilities and trust boundary before first use. | Silent server enablement. |
| Signed descriptors | Verify descriptor integrity and detect changed tool definitions. | Blindly accepting server updates. |
| MCP flight recorder | Log tool descriptor hash, call args redacted, result summary, evidence, cost. | Dumping raw secrets into logs. |
| Error semantics | Normalize tool errors into recovery classes. | Letting agents guess from free-form errors. |

## ACP / External Agent Opportunities

ACP naming needs verification. If target means Agent Client Protocol, Agent2Agent, or another emerging protocol, ARC should still use the same product stance:

- External agents are **runtimes**, not magic peers.
- They need manifests/agent cards mapped into ARC capabilities.
- ARC should negotiate what they can inspect/change/prove/cost/recover.
- Handoff workbench should validate what state is sent and what evidence returns.
- External agent actions should produce ARC receipts.

## Protocol Extensions Worth Proposing

| Extension | Why it matters |
|---|---|
| `evidence_refs` | Lets tools/agents attach verifiable outputs to claims. |
| `risk_class` | Lets hosts preview and enforce policies consistently. |
| `cost_model` | Lets hosts budget and warn without fake precision. |
| `rollback_semantics` | Lets hosts distinguish reversible file edits from irreversible external actions. |
| `descriptor_hash` | Enables rug-pull detection and trust diff. |
| `handoff_schema` | Enables cross-agent/runtimes state transfer. |
| `policy_decision_ref` | Links tool call to approval/denial reason. |
| `redaction_report` | Records what was removed before display/export. |

## ARC As Cockpit Over External Agents

ARC should be able to attach to:

- Local runtimes (SwarmGraph).
- Graph frameworks (LangGraph, CrewAI, AG2, OpenAI Agents).
- MCP tool servers.
- ACP/A2A external coding agents [needs verification].
- Future HotLoop visual agents.

But every attachment must pass through one model: capabilities, contracts, evidence, policy, receipts.

## What To Avoid

- MCP server marketplace in v0.1.
- Trusting tool descriptions as policy.
- Auto-enabling remote tools from cloned repos.
- Sending full workspace roots to tools by default.
- Treating ACP/A2A agents as peers without ARC-controlled receipts.
- Protocol purity at the expense of user-visible safety.

## v0.1 Reservations

```ts
interface ExternalCapabilityDescriptor {
  source: 'runtime_manifest' | 'mcp_server' | 'agent_card';
  descriptorHash: string;
  riskClasses: string[];
  evidenceTypesProduced: string[];
  rollbackSemantics: 'none' | 'file_revert' | 'runtime_checkpoint' | 'external_unknown';
  costModel: 'none' | 'estimate' | 'actual' | 'unknown';
}
```

Reserve this without promising full MCP/ACP implementation.
