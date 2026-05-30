# ARC Studio Innovation Critical Review Index

Date: 2026-05-16

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

## Files

| File | Purpose |
|---|---|
| [01-executive-critical-review.md](01-executive-critical-review.md) | Brutal diagnosis, top weaknesses/opportunities, stop/double-down guidance. |
| [02-competitor-frontier-map.md](02-competitor-frontier-map.md) | Competitor capability map and open frontier. |
| [03-invention-candidates.md](03-invention-candidates.md) | Full analysis of 20 requested + 10 added invention candidates. |
| [04-cli-innovations.md](04-cli-innovations.md) | Terminal UX, commands, receipts, policy simulation, co-presence. |
| [05-ide-innovations.md](05-ide-innovations.md) | Theia cockpit layout, evidence cards, cross-highlighting, review/apply. |
| [06-agent-runtime-orchestration.md](06-agent-runtime-orchestration.md) | Runtime negotiation, manifests, handoff contracts, certification. |
| [07-graph-observability-innovations.md](07-graph-observability-innovations.md) | Graph as cockpit, node commands, run comparison, pre-replay UX. |
| [08-safety-trust-cost-innovations.md](08-safety-trust-cost-innovations.md) | Trust diff, policy simulator, visual contracts, delegation tokens. |
| [09-mcp-acp-protocol-innovations.md](09-mcp-acp-protocol-innovations.md) | MCP/ACP opportunities, permission mapping, protocol extensions. |
| [10-hotloop-visual-agent-innovations.md](10-hotloop-visual-agent-innovations.md) | HotLoop frontier, frame receipts, visual contracts, multimodal risks. |
| [11-roadmap-impact.md](11-roadmap-impact.md) | Plan changes, v0.1 lock criteria, dependency graph, risk table. |
| [12-final-recommendation.md](12-final-recommendation.md) | Final verdict, must-add items, innovation bets, rejected gimmicks. |

## Executive Position

The current ARC Studio plan should **lock with changes**, not as-is. It is strong product cleanup but insufficient differentiation. The winning direction is not “better chat with files.” It is the first **Agent Runtime Cockpit**: local-first, graph-native, contract-led, evidence-backed, policy-aware, and multi-runtime.

## Top 10 Innovation Recommendations

1. Visual Run Contracts.
2. Agent Run Receipts.
3. Failure Autopsy.
4. Evidence Cards.
5. Runtime Capability Negotiation.
6. Graph/Chat/Evidence Cross-Highlighting.
7. Trust Diff.
8. Policy Simulator.
9. Session Twin.
10. Handoff Workbench.

## Top 5 Rejections

1. Default raw Trace UI in v0.1.
2. Full replay scrubber in v0.1.
3. Autonomous HotLoop before frame receipts and visual contracts.
4. Runtime marketplace before conformance tests.
5. Global unreceipted agent memory.

## Source Limitations

I used the uploaded ARC UX spec and CLI/IDE redesign plan. I could not directly inspect repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md`; GitHub repo selection was unavailable through the file search connector. Re-run this review after those files are accessible to validate ADR constraints and roadmap synthesis details.
