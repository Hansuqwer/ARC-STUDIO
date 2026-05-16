# Invention Candidates

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

This file reviews the 20 requested invention directions and adds 10 more. Recommendations intentionally separate **ship**, **reserve**, **research**, and **reject** so v0.1 does not absorb large v0.2/v0.3 work.

| # | Candidate | Recommendation |
|---:|---|---|
| 1 | Intent Ledger | Ship minimal receipt now; full ledger v0.2. |
| 2 | Runtime Capability Negotiation | Reserve now; implement negotiation v0.2. |
| 3 | Evidence Cards | Ship small for file/test/run claims. |
| 4 | Cost-Risk Preview | Ship minimal conservative preview v0.1. |
| 5 | Graph-Native Commanding | Reserve now; ship explain/select/cross-highlight first. |
| 6 | Session Twin | Ship presence + mirrored approvals v0.1 if simple; richer v0.2. |
| 7 | Failure Autopsy | Ship minimal v0.1 replacement for default trace UI. |
| 8 | Policy Simulator | Reserve now; ship for known action classes v0.1/v0.2. |
| 9 | Trust Diff | Ship for trust/provider/policy changes early. |
| 10 | Handoff Workbench | Reserve v0.1; implement v0.2. |
| 11 | Visual Run Contracts | Top v0.1 reservation; minimal ship. |
| 12 | Agent Flight Recorder | Ship v0.1 compact receipt; expand v0.2. |
| 13 | Prompt/Workflow Differential Debugger | Reserve now; v0.3 full. |
| 14 | Runtime Black Box Tests | Ship small conformance for SwarmGraph v0.1/v0.2. |
| 15 | Local Agent Memory With Receipts | Research/reserve v0.2; do not ship broad v0.1. |
| 16 | Secure Delegation Tokens | Research; reserve IDs only. |
| 17 | Cockpit Command Palette | Ship small v0.1 state-aware commands. |
| 18 | Graph + Chat Cross-Highlighting | Easy v0.1 win if IDs exist. |
| 19 | User-Editable Agent Constitution | Ship structured policy; reserve constitution. |
| 20 | Agent Run Receipts | Ship v0.1. |
| 21 | Contract Stack | Research/reserve. |
| 22 | Agent Health Probes | Ship local probes early. |
| 23 | Evidence Budget | Research v0.2. |
| 24 | Capability Heatmap | Reserve now. |
| 25 | Runbook Generator | Research. |
| 26 | Workspace Time Capsule | Reserve. |
| 27 | Invariant Watchers | Ship simple invariants v0.2. |
| 28 | Review Queue as Control Plane | Reserve; minimal queue v0.1/v0.2. |
| 29 | Intent-to-Test Synthesis | Ship success criteria field early. |
| 30 | Agent Sandbox Bill of Materials | Ship minimal v0.2; reserve v0.1. |


## Intent Ledger

### What It Is
Persistent accountable timeline of user intent, agent decisions, tool calls, approvals, trust/cost changes, and edits.

### Why Competitors Don’t Have It
Adjacent tools expose logs, traces, or chat history; they rarely compress them into a human accountability record with why/what/evidence.

### Why ARC Can Build It
SwarmGraph events, JSONL traces, HMAC audit [needs internal verification], SQLite index, HITL and local daemon give ARC the raw material.

### User Wow Moment
After a run, the user clicks 'Why did this file change?' and sees intent -> node -> approval -> diff -> test evidence in one chain.

### Technical Shape
New event type `intent.ledger.entry`; daemon compacts raw events into decisions; IDE Ledger card; CLI `/ledger` and run receipt link.

### v0.1 Minimal Reservation
Reserve `decision_id`, `parent_intent_id`, `evidence_refs`, `audit_ref` on run events.

### v0.2/v0.3 Full Version
Ledger timeline, filtering by file/node/approval, PR export, support bundle.

### Risks
Over-compression can hide truth; privacy redaction; storage growth.

### Kill Criteria
Reject if it duplicates raw trace UI or cannot link to evidence.

### Recommendation
Ship minimal receipt now; full ledger v0.2.


## Runtime Capability Negotiation

### What It Is
Runtimes declare inspect/change/evidence/safety/cost/handoff capabilities and ARC negotiates the right runtime.

### Why Competitors Don’t Have It
Competitors mostly expose model/runtime pickers or tool availability, not negotiated guarantees.

### Why ARC Can Build It
Runtime manifests are already reserved; ARC can add conformance and negotiation fields before UI hardens.

### User Wow Moment
ARC says: 'HotLoop can inspect screenshots but cannot produce rollback evidence; SwarmGraph can produce graph-node evidence. Choose contract.'

### Technical Shape
Extend manifest with capabilities, evidence obligations, cost model, accepted handoff schemas; daemon resolver scores runtimes.

### v0.1 Minimal Reservation
Add manifest fields but use only SwarmGraph in v0.1; show disabled explanation.

### v0.2/v0.3 Full Version
Multi-runtime sessions, router decisions, handoff validation, black-box certification.

### Risks
Manifest inflation; vendors may overclaim; false confidence.

### Kill Criteria
Reject runtime if manifest claims cannot be tested.

### Recommendation
Reserve now; implement negotiation v0.2.


## Evidence Cards

### What It Is
Every agent claim can cite file lines, graph state, run summary, audit record, test output, provider output, or screenshots.

### Why Competitors Don’t Have It
Chat answers often cite files or tool outputs, but rarely mark unsupported claims visually.

### Why ARC Can Build It
ARC owns graph/run/audit/event data locally and can build an evidence index.

### User Wow Moment
Agent says 'tests passed' with a card showing command, exit code, timestamp, and run node.

### Technical Shape
`EvidenceRef` schema; card component; CLI expandable `evidence:` blocks; unsupported claim badge.

### v0.1 Minimal Reservation
Add optional `evidence_refs[]` to assistant messages and run summaries.

### v0.2/v0.3 Full Version
Evidence browser, claim verification lint, PR receipt integration.

### Risks
Noisy UI; bad evidence can look authoritative; line drift.

### Kill Criteria
Kill if evidence creation slows all responses or becomes ceremonial.

### Recommendation
Ship small for file/test/run claims.


## Cost-Risk Preview

### What It Is
Preflight card showing likely tool categories, boundary crossings, paid-call likelihood, write likelihood, rollback, unknowns.

### Why Competitors Don’t Have It
Most tools ask permission at action time, not before a planned run.

### Why ARC Can Build It
ARC has mode, trust resolver, provider config, runtime manifests, and local session policy.

### User Wow Moment
Before Auto mode, ARC says: 'Will read 18 files, may call Anthropic, cannot rollback shell effects.'

### Technical Shape
Preflight estimator service; conservative labels; CLI `/preview`; IDE RunContractCard.

### v0.1 Minimal Reservation
Reserve `preflight` event and `unknowns[]`; show minimal paid/write/trust preview.

### v0.2/v0.3 Full Version
Cost/risk simulation, per-node projections, policy simulator integration.

### Risks
Overpromising exact costs; stale runtime capability info.

### Kill Criteria
Reject if estimates are presented as guarantees.

### Recommendation
Ship minimal conservative preview v0.1.


## Graph-Native Commanding

### What It Is
Users command graph nodes and edges directly: rerun, pause, explain edge, compare path, force handoff.

### Why Competitors Don’t Have It
Competitor graphs are mostly visualization/debugging; IDE chats command text, not topology.

### Why ARC Can Build It
SwarmGraph topology and node states are first-class in ARC.

### User Wow Moment
User right-clicks failed reviewer node: 'retry with previous writer output and stricter policy.'

### Technical Shape
Node command registry, run state machine, graph inspector actions, CLI `/graph node <id> ...`.

### v0.1 Minimal Reservation
Reserve node IDs stable across run, `allowed_node_actions[]`; expose explain-only in v0.1.

### v0.2/v0.3 Full Version
Rerun/pause/force handoff after replay/checkpoint support.

### Risks
Dangerous partial reruns; inconsistent state; UX overload.

### Kill Criteria
Reject mutating node commands until state checkpoints are reliable.

### Recommendation
Reserve now; ship explain/select/cross-highlight first.


## Session Twin

### What It Is
CLI and IDE are two views into the same live session with mirrored state and approvals.

### Why Competitors Don’t Have It
Some tools have CLI and IDE, but live co-presence with shared graph selection/approval is weak.

### Why ARC Can Build It
The plan already includes shared daemon/session lifecycle.

### User Wow Moment
Run starts in terminal; IDE graph opens same run; approval in IDE updates terminal instantly.

### Technical Shape
Daemon pub/sub; session lock; client presence; action IDs; conflict policy.

### v0.1 Minimal Reservation
Expose `clients_attached`, `active_surface`, and action idempotency fields.

### v0.2/v0.3 Full Version
Selection mirroring, split controls, mobile approval, collaborative surfaces.

### Risks
Race conditions; duplicated approvals; confusing authority.

### Kill Criteria
Kill if write approvals can be double-submitted.

### Recommendation
Ship presence + mirrored approvals v0.1 if simple; richer v0.2.


## Failure Autopsy

### What It Is
Failed runs produce cause, failed node, last safe state, retry options, config/runtime/key hints, trace link, evidence vs guesses.

### Why Competitors Don’t Have It
Competitors show errors/logs; few produce structured honest autopsies per run.

### Why ARC Can Build It
ARC can combine node state, daemon diagnostics, runtime manifest, `/doctor`, cost, and traces.

### User Wow Moment
After failure: 'Reviewer timed out after tool X; last safe commit Y; retry only reviewer or switch model.'

### Technical Shape
Autopsy generator; `cause_confidence`; evidence refs; retry actions; CLI failure card.

### v0.1 Minimal Reservation
Add `failure_autopsy` field to RunSummary with evidence/guess split.

### v0.2/v0.3 Full Version
Self-diagnosing runs, automatic config fix suggestions, comparison to successful run.

### Risks
Bad guesses damage trust; may mask raw trace.

### Kill Criteria
Kill if confidence/evidence separation is absent.

### Recommendation
Ship minimal v0.1 replacement for default trace UI.


## Policy Simulator

### What It Is
Before Auto mode, simulate what policy would approve/deny for likely run actions.

### Why Competitors Don’t Have It
Claude Code auto mode uses permission classifiers; users rarely get a preview of policy behavior.

### Why ARC Can Build It
ARC has explicit Plan/Build/Auto policy and trust resolver.

### User Wow Moment
User toggles Auto and sees: 'Would still ask for shell, deny trust changes, ask paid calls.'

### Technical Shape
Policy evaluator over preflight action classes; CLI `/policy simulate`; IDE sheet.

### v0.1 Minimal Reservation
Reserve `policy_decision.preview` event and action categories.

### v0.2/v0.3 Full Version
Scenario fuzzing, per-runtime policy tests, Auto mode dry-run.

### Risks
Unknown future tools make simulation incomplete.

### Kill Criteria
Reject if UI implies exhaustive certainty.

### Recommendation
Reserve now; ship for known action classes v0.1/v0.2.


## Trust Diff

### What It Is
When trust/policy/provider config changes, ARC shows newly allowed capabilities, affected files/tools/providers, and risk increase.

### Why Competitors Don’t Have It
Most tools have settings; few show security diffs as first-class UX.

### Why ARC Can Build It
ARC already separates policy, trust, provider keys, workspace trust.

### User Wow Moment
User enables shell and sees exact new blast radius: 'shell_exec allowed for trusted workspace only, no network.'

### Technical Shape
Policy diff engine; config before/after; risk taxonomy; required confirmation.

### v0.1 Minimal Reservation
Reserve policy schema version and diff labels.

### v0.2/v0.3 Full Version
Mandatory trust diffs, PR review for policy changes, audit chain.

### Risks
Can annoy users; risk taxonomy might become stale.

### Kill Criteria
Kill if diffs are too generic to guide decisions.

### Recommendation
Ship for trust/provider/policy changes early.


## Handoff Workbench

### What It Is
Inspect/edit/validate phase handoff docs against next runtime schema with lost capabilities and risk/cost changes.

### Why Competitors Don’t Have It
Adjacent planners pass context, but handoff validation across runtimes is mostly absent.

### Why ARC Can Build It
Runtime manifests and `handoff` event are already reserved.

### User Wow Moment
ARC shows: 'HotLoop will not receive shell access or audit links unless you include these fields.'

### Technical Shape
Handoff schema, editor, validator, capability diff, phase boundary UI.

### v0.1 Minimal Reservation
Reserve handoff schema refs and `accepted_handoff_versions` in manifests.

### v0.2/v0.3 Full Version
Interactive workbench v0.2 planner/router; runtime migration assistant.

### Risks
Too heavy before real multi-phase workflows.

### Kill Criteria
Kill if runtime count remains one.

### Recommendation
Reserve v0.1; implement v0.2.


## Visual Run Contracts

### What It Is
Pre-run and post-run contract cards unify objective, tools, cost, writes, runtime, rollback, evidence expected.

### Why Competitors Don’t Have It
Competitors ask permissions but do not generally make a run into a contract with fulfillment status.

### Why ARC Can Build It
ARC’s HITL, trust, cost, runtime manifests, audit, graph states can back it.

### User Wow Moment
After run: green/red checklist shows which promises were fulfilled or violated.

### Technical Shape
`RunContract` schema; CLI `/contract`; IDE ContractCard; post-run verifier.

### v0.1 Minimal Reservation
Reserve `run_contract` in RunSummary; populate objective/mode/runtime/rollback/evidence.

### v0.2/v0.3 Full Version
Contract authoring, templates, policy constraints, PR export.

### Risks
False promises; friction for trivial tasks.

### Kill Criteria
Kill if every chat turn becomes bureaucratic.

### Recommendation
Top v0.1 reservation; minimal ship.


## Agent Flight Recorder

### What It Is
Local compact record of session summary, contract, graph changes, approvals, diffs, failure autopsy, evidence links.

### Why Competitors Don’t Have It
Trace systems store events; flight recorder stores meaningful operation state for humans/tools.

### Why ARC Can Build It
Local daemon/session files + JSONL + HMAC audit [needs internal verification].

### User Wow Moment
User exports one file for bug report: no secrets, enough to reproduce decisions.

### Technical Shape
SQLite/JSONL reducer; redaction; export command; support bundle format.

### v0.1 Minimal Reservation
Reserve `flight_recorder.jsonl` or run receipt artifact path.

### v0.2/v0.3 Full Version
Compliance, evals, support, PR attachment, replay seed.

### Risks
Sensitive data; schema stability.

### Kill Criteria
Kill if redaction cannot be trusted.

### Recommendation
Ship v0.1 compact receipt; expand v0.2.


## Prompt/Workflow Differential Debugger

### What It Is
Compare prompt, run, graph topology, cost, policy decisions, and outputs between successful/failed runs.

### Why Competitors Don’t Have It
Diffs exist for code, not agent workflow behavior.

### Why ARC Can Build It
ARC has graphs, traces, runs, policy decisions, manifests.

### User Wow Moment
User asks: 'Why did today’s run cost 3x?' ARC shows changed runtime and added tool loop.

### Technical Shape
Run comparison service; normalized event categories; CLI `/compare runs`; IDE diff view.

### v0.1 Minimal Reservation
Reserve comparable stable IDs and summary fields.

### v0.2/v0.3 Full Version
Prompt diff, graph diff, cost diff, policy diff, evidence diff.

### Risks
Hard normalization across runtimes.

### Kill Criteria
Kill if only raw JSON diff is available.

### Recommendation
Reserve now; v0.3 full.


## Runtime Black Box Tests

### What It Is
Before enabling a runtime, ARC runs probes for inspect/dry-run/events/redaction/cost/cancel/recover.

### Why Competitors Don’t Have It
Runtime tools often trust docs; conformance is uncommon in coding-agent UX.

### Why ARC Can Build It
Runtime manifests and `/doctor` are already planned.

### User Wow Moment
`/doctor runtime langgraph` says 'claims cost reporting but failed probe; disabled cost contract.'

### Technical Shape
Probe harness, fixture workspace, manifest claims, certification report.

### v0.1 Minimal Reservation
Add `conformance.required[]` and `doctor` probe IDs.

### v0.2/v0.3 Full Version
Certification badges, third-party runtime marketplace readiness.

### Risks
Probe maintenance; slow doctor.

### Kill Criteria
Kill if probes cannot run offline or safely.

### Recommendation
Ship small conformance for SwarmGraph v0.1/v0.2.


## Local Agent Memory With Receipts

### What It Is
Memory stores only facts with source receipt, approval, timestamp, expiry, and trust scope.

### Why Competitors Don’t Have It
Competitors have memories/rules, often opaque or global.

### Why ARC Can Build It
ARC local-first + evidence refs + trust resolver can make memory inspectable.

### User Wow Moment
ARC remembers 'use pytest' only because user approved it from a run receipt, scoped to repo.

### Technical Shape
Memory DB; receipt refs; edit UI; expiration; retrieval policy.

### v0.1 Minimal Reservation
Reserve `memory_receipt_ref` and project-local memory path.

### v0.2/v0.3 Full Version
Memory editor, decay, review queue, PR-sensitive memory rules.

### Risks
Creepy behavior; stale facts.

### Kill Criteria
Reject global unreceipted memory.

### Recommendation
Research/reserve v0.2; do not ship broad v0.1.


## Secure Delegation Tokens

### What It Is
Every tool/provider/runtime/write/handoff call gets scoped capability token with expiry, cost ceiling, trust binding, audit link.

### Why Competitors Don’t Have It
Most tools gate permissions centrally, not per-call cryptographic delegation.

### Why ARC Can Build It
ARC local daemon and audit trail can mint scoped local tokens [needs internal verification].

### User Wow Moment
Advanced user sees a tool call failed because token allowed read but not write; no silent escalation.

### Technical Shape
Capability token envelope; daemon enforces; providers/tools receive scoped handles.

### v0.1 Minimal Reservation
Reserve `capability_token_id` fields without cryptography in v0.1.

### v0.2/v0.3 Full Version
Per-call capability system, revocation, external runtime delegation.

### Risks
Complexity; false sense of security; integration cost.

### Kill Criteria
Kill if enforcement is only cosmetic.

### Recommendation
Research; reserve IDs only.


## Cockpit Command Palette

### What It Is
State-aware command palette suggests actions based on current run/session/runtime/policy/failure.

### Why Competitors Don’t Have It
Static slash commands are common; dynamic operational commands are less common.

### Why ARC Can Build It
ARC has daemon state, graph state, run summaries, policy decisions.

### User Wow Moment
Palette says 'Retry failed reviewer node' exactly when reviewer fails.

### Technical Shape
Command index subscribed to session events; CLI fuzzy commands; IDE palette provider.

### v0.1 Minimal Reservation
Reserve command context fields and action descriptors.

### v0.2/v0.3 Full Version
Cross-surface palette, macro recording, programmable workflows.

### Risks
Too many commands; inconsistent availability.

### Kill Criteria
Kill if it becomes a menu dump.

### Recommendation
Ship small v0.1 state-aware commands.


## Graph + Chat Cross-Highlighting

### What It Is
Selecting a graph node highlights chat messages, tool cards, approvals, run summary, and evidence cards.

### Why Competitors Don’t Have It
Some debuggers link traces to UI, but coding agents rarely make graph/chat/evidence coherent.

### Why ARC Can Build It
ARC’s graph and chat share run event IDs.

### User Wow Moment
Click reviewer node; chat scrolls to its decision and diff approval.

### Technical Shape
Shared `event_id`, `node_id`, `message_id`; selection bus; CLI numbered references.

### v0.1 Minimal Reservation
Reserve IDs and emit node-message associations.

### v0.2/v0.3 Full Version
Cross-highlight all surfaces, compare path, evidence filter.

### Risks
Broken links ruin trust; visual clutter.

### Kill Criteria
Kill if event IDs are unstable.

### Recommendation
Easy v0.1 win if IDs exist.


## User-Editable Agent Constitution

### What It Is
Project natural language + structured policy for allowed actions, style, risk/cost tolerance, review expectations, runtime preferences.

### Why Competitors Don’t Have It
Rules files exist, but enforceability is weak.

### Why ARC Can Build It
ARC can split prose guidance from enforceable policy and show diffs.

### User Wow Moment
User edits constitution; ARC shows which parts are enforceable vs advisory.

### Technical Shape
`.arc/constitution.md` + `.arc/policy.yaml`; parser; lint; trust diff.

### v0.1 Minimal Reservation
Reserve constitution file path and enforceability labels.

### v0.2/v0.3 Full Version
IDE editor with lint, policy simulator, team templates.

### Risks
Overpromising enforcement of prose.

### Kill Criteria
Kill if everything is just prompt injection.

### Recommendation
Ship structured policy; reserve constitution.


## Agent Run Receipts

### What It Is
After every run, emit what changed, why, evidence, cost, approvals, rollback command, boundary crossings, unresolved risks.

### Why Competitors Don’t Have It
Some agents make PRs or summaries; receipts as trust artifacts are rare.

### Why ARC Can Build It
ARC has run summaries, diffs, cost, trust, audit, rollback.

### User Wow Moment
PR description includes ARC receipt with exact rollback command and unresolved risks.

### Technical Shape
Receipt markdown/json; CLI post-run output; IDE card; export to PR.

### v0.1 Minimal Reservation
Ship `run_receipt.md` generated from RunSummary.

### v0.2/v0.3 Full Version
Receipts feed ledger, evals, support, compliance.

### Risks
Verbose receipts ignored; redaction.

### Kill Criteria
Kill if receipts are generic marketing summaries.

### Recommendation
Ship v0.1.


## Contract Stack

### What It Is
A layered stack of workspace, session, run, phase, node, and tool contracts with inheritance and overrides.

### Why Competitors Don’t Have It
Competitors flatten permissions into modes or settings.

### Why ARC Can Build It
ARC can map contracts to graph hierarchy and policy precedence.

### User Wow Moment
Node contract says writer may edit docs but reviewer cannot write code.

### Technical Shape
Contract resolver; inherited scopes; conflict diagnostics.

### v0.1 Minimal Reservation
Reserve `contract_scope` on events.

### v0.2/v0.3 Full Version
Contract editor and graph overlay.

### Risks
Policy complexity.

### Kill Criteria
Kill if users cannot predict final policy.

### Recommendation
Research/reserve.


## Agent Health Probes

### What It Is
Continuous lightweight diagnostics for model/provider/runtime/tool health with run-specific relevance.

### Why Competitors Don’t Have It
Doctor commands exist, but not contextual health probes tied to failures.

### Why ARC Can Build It
ARC daemon can run local probes and tie results to autopsy.

### User Wow Moment
Failure card says Anthropic auth failed today, not reviewer logic.

### Technical Shape
Probe registry; cached status; failure correlation.

### v0.1 Minimal Reservation
Reserve probe result links in failure cards.

### v0.2/v0.3 Full Version
Health dashboard, auto-suppression of flaky runtime.

### Risks
Noise and cost.

### Kill Criteria
Kill if probes call paid providers without consent.

### Recommendation
Ship local probes early.


## Evidence Budget

### What It Is
A configurable expectation for how much evidence is required for different action classes before ARC can answer/apply.

### Why Competitors Don’t Have It
Most agents optimize speed, not evidentiary sufficiency.

### Why ARC Can Build It
ARC can count evidence refs per claim/action and enforce contracts.

### User Wow Moment
High-risk refactor requires tests + file evidence; docs change requires file diff only.

### Technical Shape
Policy field `evidence_budget`; verifier; visual gaps.

### v0.1 Minimal Reservation
Reserve `evidence_required` and `evidence_provided`.

### v0.2/v0.3 Full Version
Evidence linting, CI gates for receipts.

### Risks
Can slow runs.

### Kill Criteria
Kill if evidence metrics become arbitrary score theater.

### Recommendation
Research v0.2.


## Capability Heatmap

### What It Is
Visual map of which runtimes/tools can read/write/test/observe/cost/recover across workspace areas.

### Why Competitors Don’t Have It
Capability lists are static; heatmaps are rare.

### Why ARC Can Build It
Runtime manifests + workspace scan can generate it.

### User Wow Moment
ARC shows HotLoop sees UI frames but not database; SwarmGraph sees code but not browser.

### Technical Shape
Matrix UI; CLI table; manifest resolver.

### v0.1 Minimal Reservation
Reserve normalized capability taxonomy.

### v0.2/v0.3 Full Version
Interactive runtime choice, policy explanation.

### Risks
Could be too abstract.

### Kill Criteria
Kill if it does not affect decisions.

### Recommendation
Reserve now.


## Runbook Generator

### What It Is
ARC turns repeated failure/autopsy patterns into editable runbooks with evidence and safe commands.

### Why Competitors Don’t Have It
Competitors may suggest fixes but rarely create verified operational runbooks.

### Why ARC Can Build It
Flight recorder + failure autopsy + doctor provide data.

### User Wow Moment
After three flaky provider failures, ARC proposes a provider-key rotation runbook.

### Technical Shape
Pattern detector; runbook markdown; approval before creation.

### v0.1 Minimal Reservation
Reserve `runbook_suggestion` events.

### v0.2/v0.3 Full Version
Team-shared runbooks, policy tests.

### Risks
Could create stale docs.

### Kill Criteria
Kill if generated runbooks lack evidence receipts.

### Recommendation
Research.


## Workspace Time Capsule

### What It Is
Portable snapshot of config, manifest versions, receipts, graph topology, and prompts without code secrets.

### Why Competitors Don’t Have It
Session export exists in some tools; reproducible agent-state capsules are uncommon.

### Why ARC Can Build It
Local-first session layout and manifests make this feasible.

### User Wow Moment
Developer shares a failed run capsule without leaking codebase.

### Technical Shape
Exporter; redaction; manifest hash; replay seed.

### v0.1 Minimal Reservation
Reserve manifest hashes and redaction report.

### v0.2/v0.3 Full Version
Support/eval/import into another machine.

### Risks
Privacy risk; incomplete reproduction.

### Kill Criteria
Kill if capsule cannot be safely redacted.

### Recommendation
Reserve.


## Invariant Watchers

### What It Is
User-defined invariants watched during run: no file outside src, no dependency changes, tests must pass, no paid calls.

### Why Competitors Don’t Have It
Permissions exist, but live invariants with graph failure nodes are weaker in competitors.

### Why ARC Can Build It
ARC policy + graph + diff + cost events can enforce.

### User Wow Moment
Run stops at node when invariant 'no package.json edits' is violated.

### Technical Shape
Invariant DSL; watcher service; graph annotations.

### v0.1 Minimal Reservation
Reserve `invariant_violation` event.

### v0.2/v0.3 Full Version
Invariant library, team policy templates.

### Risks
DSL complexity.

### Kill Criteria
Kill if invariants are only post-hoc warnings.

### Recommendation
Ship simple invariants v0.2.


## Review Queue as Control Plane

### What It Is
HITL approvals become a durable queue with ownership, SLA, evidence, and batch actions.

### Why Competitors Don’t Have It
Most IDE agents show transient prompts.

### Why ARC Can Build It
ARC local daemon can persist and mirror approvals across surfaces.

### User Wow Moment
User leaves terminal; IDE shows pending approvals with evidence and risk.

### Technical Shape
Approval table; idempotent actions; notifications.

### v0.1 Minimal Reservation
Reserve approval IDs and states.

### v0.2/v0.3 Full Version
Team approval, mobile/web, policy audit.

### Risks
Overkill for solo v0.1.

### Kill Criteria
Kill if prompt latency is worse.

### Recommendation
Reserve; minimal queue v0.1/v0.2.


## Intent-to-Test Synthesis

### What It Is
For each user intent, ARC proposes tests/checks needed to prove fulfillment before coding.

### Why Competitors Don’t Have It
Agents often run tests after edits; few negotiate proof before run.

### Why ARC Can Build It
Run contracts and evidence cards provide proof targets.

### User Wow Moment
ARC says: 'To prove this, I need unit tests A and smoke test B.'

### Technical Shape
Preflight proof planner; test evidence refs.

### v0.1 Minimal Reservation
Reserve `success_criteria[]` in run contract.

### v0.2/v0.3 Full Version
Auto-generated evals, PR checks.

### Risks
Can overfit tests; extra cost.

### Kill Criteria
Kill if tests are not executed or evidenced.

### Recommendation
Ship success criteria field early.


## Agent Sandbox Bill of Materials

### What It Is
A per-run SBOM-like record of tools, providers, runtimes, env vars, permissions, model IDs, and network calls.

### Why Competitors Don’t Have It
Security tools have SBOMs; coding agents rarely emit agent-runtime BOMs.

### Why ARC Can Build It
ARC config, keyring provenance, runtime manifests, tool events, audit.

### User Wow Moment
Security reviewer sees exactly which external services the run touched.

### Technical Shape
`agent_bom.json`; receipt section; redaction.

### v0.1 Minimal Reservation
Reserve `runtime_bom` in run receipt.

### v0.2/v0.3 Full Version
Compliance export, policy gates.

### Risks
Sensitive metadata; noisy.

### Kill Criteria
Kill if it lists secrets or low-value internals.

### Recommendation
Ship minimal v0.2; reserve v0.1.
