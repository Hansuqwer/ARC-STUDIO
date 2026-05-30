# Executive Critical Review

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

## Brutal Summary

The current ARC Studio CLI/IDE redesign is good product hygiene, not a moat. It fixes the obvious sins: no chat-first launch, too many nested commands, no session model, weak IDE navigation, no visible model/runtime selection, no apply/review loop, and scattered trace widgets. Those moves are necessary, but they mostly reposition ARC Studio at the 2025 baseline of Claude Code, Codex CLI, Cursor, Windsurf, Kiro, VS Code Copilot, and OpenCode.

The differentiated raw material is present but underexploited: SwarmGraph, runtime manifests, local daemon/session co-presence, HMAC/audit trail assumptions, HITL gates, trust resolver, JSONL traces, graph topology, and an explicit “no default Trace UI” choice. The current plan says “Run agents. See everything.” The product still risks becoming “chat with a decorative graph.”

ARC should become the **Agent Runtime Cockpit**: a control surface where every run has a contract, every decision has evidence, every permission change has a diff, every failure has an autopsy, every runtime declares capabilities, and every graph node can be commanded. That is more defensible than another chat sidebar.

## Top 10 Weaknesses

1. **The plan catches up before it invents.** Chat-first CLI, slash commands, sessions, config UI, status bars, and diff review are table stakes.
2. **Graph is still too passive.** Live graph is useful, but without node commands, evidence linkage, run contracts, or failure inspection it is an animated diagram.
3. **No accountability primitive.** Runs have summaries and advanced traces, but there is no human-readable “why did ARC do this?” ledger.
4. **Runtime switching is still a picker.** Runtime manifests are reserved, but the plan does not yet turn them into negotiation, conformance, or handoff contracts.
5. **Safety UX is mostly approval prompts.** Workspace trust, paid-call confirmation, and keyring are necessary, but competitors can copy them quickly.
6. **The v0.1 “no Trace UI” decision needs a replacement.** If raw trace UI is removed, ARC needs Failure Autopsy, Evidence Cards, Intent Ledger, and Run Receipts immediately as summaries.
7. **Session co-presence is underspecified.** CLI/IDE shared lifecycle is promising, but needs conflict semantics, mirrored approvals, and live command parity.
8. **Cost is too shallow.** Status line and paid-call confirmation do not make ARC cost-aware; users need risk/cost preflight and post-run receipts.
9. **HITL is treated as prompts, not contracts.** ARC can define phase/run/node-level contracts with fulfilled/violated outcomes.
10. **HotLoop is deferred without enough protocol shape.** Reserving panels is fine, but visual evidence, frame receipts, and multimodal safety contracts need hooks now.

## Top 10 Opportunities

1. **Visual Run Contracts**: pre-run card for objective, allowed tools, max cost, write policy, runtime, rollback, evidence expected; post-run fulfillment report.
2. **Intent Ledger**: compact accountable timeline above raw traces, backed by audit chain and evidence links.
3. **Runtime Capability Negotiation**: runtime manifests become a protocol for what a runtime can inspect/change/prove/cost/recover.
4. **Evidence Cards**: every claim links to file lines, graph state, test output, audit entry, tool output, or screenshot/frame.
5. **Graph-Native Commanding**: commands attach to nodes and edges, not just chat prompts.
6. **Failure Autopsy**: failed runs produce honest cause/evidence/retry/rollback panels instead of dumping logs.
7. **Trust Diff + Policy Simulator**: permission changes become previewable and reviewable like code diffs.
8. **Session Twin**: CLI and IDE are two synchronized surfaces over one live run/session, including approvals and selection state.
9. **Agent Flight Recorder**: local-first compact operational artifact that powers support, export, evals, compliance, and PR descriptions.
10. **Runtime Black Box Tests**: `/doctor runtime` proves manifest claims before ARC enables a runtime.

## What To Stop Doing

- Stop treating “chat-first” as differentiation. It is the entrance fee.
- Stop building graph visualization without command affordances.
- Stop relying on “advanced trace fallback” as the only escape hatch for truth.
- Stop adding panels before defining what decision each panel lets the user make.
- Stop exposing runtime choices as names; expose guarantees, costs, evidence, and recovery behavior.
- Stop making Auto mode a confidence vibe. Make it a policy contract with simulation.
- Stop copying Cursor/Windsurf inline diff as the aspirational endpoint; ARC’s value is run accountability, not just edit ergonomics.

## What To Double Down On

- Local-first daemon/session model.
- SwarmGraph topology and node semantics.
- Honest runtime capability labels.
- HMAC/audit trail assumptions [needs internal verification].
- HITL gates as first-class graph nodes and contracts.
- Git-backed reversible apply, but connect it to receipts and run contracts.
- Advanced trace as fallback only; human summaries as primary.
- Theia-native layout, because ARC should avoid rebuilding the IDE shell.

## Lock Verdict Preview

**Lock with changes.** Do not block v0.1 on huge features, but add protocol/schema/UI reservations now for run contracts, evidence cards, intent ledger, trust diff, runtime negotiation, node command metadata, and flight recorder receipts. Without those reservations, v0.2 will repaint core storage, event, and UI assumptions.
