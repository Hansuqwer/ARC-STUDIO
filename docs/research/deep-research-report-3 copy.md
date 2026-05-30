# ARC Studio Global Feature Discovery

## Executive summary

The strongest signal from the current agent-tooling market is convergence. The best products are no longer “just chat in an editor”; they are becoming full operating environments for autonomous and semi-autonomous software work. Cursor now combines cloud agents, worktrees, MCP, plugins, skills and a reviewable plan mode; Claude Code combines background sessions, worktrees, agent teams, hooks and plugins; Windsurf combines checkpoints, workflows, memories and a Kanban-style Agent Command Center; Codex now exposes parallel threads, worktrees, automations, plugins and skills in its desktop experience. citeturn8search0turn8search25turn8search2turn8search5turn8search17turn8search32turn7search11turn7search17turn7search21turn7search6turn7search12turn9search8turn9search2turn9search20turn9search13turn31search24turn31search16

For ARC Studio, that creates a very specific product problem and a very large opportunity. ARC already appears to have unusually strong primitives from your brief: local-first runtime control, a native multi-agent runtime, audit/HITL/replay/eval systems, workspace trust, MCP stdio, and a research memory graph. What it most needs is not raw capability invention everywhere; it needs **productisation of those primitives into decisive everyday workflows**. The fastest route to user delight is to make ARC feel like the best current AI IDEs on ergonomics, while going beyond them on runtime assurance, swarm orchestration, determinism, and security.

My highest-confidence recommendation is to organise the next year around five product themes:

| Theme | Why it is the right bet |
| --- | --- |
| Parallel agent operations | This is now table stakes for advanced users, but ARC can differentiate with stronger runtime visibility and safer isolation. citeturn7search11turn7search17turn8search25turn9search13turn31search24 |
| MCP-native tooling and extension ecosystem | MCP has shifted from curiosity to backbone: there is an official spec, official registry, inspector tooling and growing client support. citeturn18search3turn18search1turn18search16turn18search7turn8search2turn9search4turn26search2turn27search14 |
| Eval, trace, review and CI loops | Leading platforms increasingly unify tracing, datasets, experiments, human review and production monitoring. citeturn15search0turn15search19turn15search22turn14search0turn14search1turn13search12turn13search16turn13search10 |
| Layered sandboxing and policy | The state of the art is defence in depth: allowlists, profiles, container and microVM fallbacks, and verifiable artefacts. citeturn8search34turn7search25turn9search17turn19search1turn19search3turn19search0turn21search4turn20search0turn19search4turn20search2 |
| Durable memory and swarm intelligence | Graph memory, temporal memory and richer agent coordination patterns are still early enough to be a moat if ARC ships them well. citeturn17search13turn17search1turn17search5turn17search8turn30search0turn30search1turn30search14turn30search18 |

The single best near-term product move is to build an **ARC Agent Command Centre** that unifies runs, worktrees, plan/review, checkpoints, approvals, risk state and replay in one place. That feature alone would make ARC immediately more legible to users coming from Windsurf, Claude Code, Cursor and Codex, while showcasing ARC’s stronger runtime core. citeturn9search13turn7search11turn8search25turn31search24

## Market signals that should shape ARC

The agent IDE category is moving from a linear interaction model to a supervisory one. Claude Code’s agent view is explicitly designed to dispatch and manage many sessions from one screen; Windsurf’s Agent Command Center groups local and cloud agents by status on a Kanban board; Cursor supports cloud agents plus worktree-based parallel execution; Codex’s desktop app is now positioned as a place to work on threads in parallel with worktrees and automations. ARC’s Runs, Workflows, SwarmGraph Insight and Battle tabs already suggest the raw material for a better supervisory cockpit than any of these, but that potential needs to be surfaced in one coherent operational layer. citeturn7search11turn7search17turn9search13turn9search14turn8search0turn8search25turn31search24

The second strong signal is standardisation around configuration, skills and tools. Cursor has Project, Team and User Rules and supports AGENTS.md; Claude Code reads CLAUDE.md, hooks, skills, commands, subagents and auto memory from `.claude`; Windsurf supports AGENTS.md, skills, workflows and memories; Gemini CLI now has hierarchical `GEMINI.md`, subagents, extensions and MCP; Codex supports AGENTS.md and configurable approvals. Users increasingly expect AI behaviour to be programmable at project and team scope, not just promptable ad hoc. citeturn8search1turn7search9turn7search12turn9search0turn9search2turn9search20turn9search23turn26search9turn26search10turn26search11turn31search3turn31search4

MCP is now too important to treat as a side protocol. The official MCP spec now defines resources, prompts and tools on the server side, and sampling, roots and elicitation on the client side. There is an official registry for server metadata discovery, an official inspector for testing and debugging, official SDK tiers, and rapidly widening client support in Cursor, Windsurf, Gemini CLI, Sourcegraph and others. ARC’s current MCP stdio local control plane is a substantial asset, but the product gap is in registry browsing, install UX, diagnostics, policy, observability and certification. citeturn18search3turn18search16turn18search1turn18search7turn8search2turn9search4turn26search2turn27search14

Observability and eval platforms have quietly settled on a common loop: trace everything, promote important production traces into datasets, run experiments and automated judges, route failures into human review, and push results back into CI or deployment gates. LangSmith supports annotation queues, datasets from traces, automation rules and OpenTelemetry fan-out; Braintrust combines evals, tracing, prompts and a CLI that can even add instrumentation automatically; Phoenix tracks prompt versions and can replay spans; MLflow 3 positions tracing, evaluation and monitoring as one lifecycle; OpenTelemetry now has semantic conventions for GenAI spans, agent spans and evaluation events. ARC’s storage system and audit/replay/eval capabilities align well with this architecture and should be turned into a headline strength. citeturn15search0turn15search19turn15search22turn15search23turn14search0turn14search1turn14search24turn14search25turn13search12turn13search9turn13search15turn13search16turn13search13turn13search2turn13search17turn13search8

The memory landscape has also evolved beyond “vector store plus summary”. Zep positions itself as a context-engineering platform built on a temporal knowledge graph via Graphiti; Graphiti is explicitly designed for incremental, temporally aware graph updates; Mem0 now emphasises entity linking, hybrid retrieval, deletion and evaluation; LangGraph exposes both memory and durable agent workflows. That mix strongly supports pushing ARC’s memory graph prototype toward explicit user/project/workflow/episode memory with erasure, provenance and time-sensitive retrieval. citeturn17search13turn17search1turn17search5turn17search8turn17search12turn17search20turn30search0

Security is becoming more layered and more product-visible. Cursor, Claude Code and Windsurf all expose approval or permission systems. On the runtime side, gVisor explicitly optimises for defence in depth with some performance overhead; Firecracker is purpose-built for lightweight secure multi-tenant microVMs and adds a companion jailer; Firecracker snapshotting is now generally available; Linux Landlock lets unprivileged processes self-restrict; bubblewrap and nsjail provide namespace/seccomp-based low-level isolation; SLSA, SPDX and Sigstore now give practical supply-chain building blocks for provenance, SBOMs and verification. ARC’s security brief is already strong, but it should be turned into explicit runtime profiles, policy bundles and signed ecosystem components. citeturn8search34turn7search25turn9search17turn19search1turn19search3turn19search15turn19search0turn21search4turn21search1turn20search0turn19search4turn20search2turn24search17turn24search13turn24search6turn24search11

## Top feature opportunities

The table below is ordered from highest strategic value to lowest. “ARC fit” is how naturally the feature extends your current architecture as described in the prompt. “Priority” is product priority, not engineering sequence.

| Feature | Inspiration/source | Why it matters | ARC fit | User value | Implementation complexity | Risk | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Agent Command Centre with worktrees, queueing, resume and ownership handoff | Windsurf Agent Command Center; Claude Code agent view + worktrees; Cursor cloud agents + CLI worktrees; Codex app parallel threads/worktrees. citeturn9search13turn9search14turn7search11turn7search17turn8search0turn8search25turn31search24turn31search16 | Makes multi-agent work manageable rather than chat-chaotic, and reduces edit collisions. | Very high | Very high | Medium | Medium | P0 |
| Reviewable Plan Mode with task ledger, cost estimate and risk estimate before writes | Cursor Plan Mode; AutoGen Magentic-One task/progress ledger. citeturn8search32turn30search20turn30search22 | Reduces accidental agent thrash and gives users a checkpoint to intervene before side effects. | Very high | Very high | Low to medium | Low | P0 |
| Checkpoints, rollback and fork-from-step for runs and workflows | Windsurf checkpoints; E2B snapshots/templates; Firecracker snapshotting. citeturn9search8turn22search0turn22search6turn21search7turn21search1 | Safe autonomy depends on cheap rollback and easy branching. | High | Very high | Medium | Medium | P0 |
| Trace-to-Workflow compiler that converts a successful run into a reusable playbook | Windsurf Workflows; CrewAI Flows; Prefect automations; Temporal durable workflows. citeturn9search2turn30search2turn30search13turn23search1turn23search8 | Turns one-off wins into repeatable operational assets. | Very high | High | Medium | Medium | P0 |
| Embedded MCP Registry browser with one-click install, config diff and health checks | Official MCP Registry; Cursor MCP install links; MCP SDKs. citeturn18search16turn18search10turn8search14turn18search7 | Cuts setup friction and makes ARC the easiest place to adopt MCP safely. | High | High | Medium | Medium | P0 |
| Embedded MCP Inspector and certification harness for servers and adapters | MCP Inspector; official SDK documentation. citeturn18search1turn18search7turn18search18 | Gives developers confidence that tools behave correctly before they are trusted in production runs. | High | High | Medium | Low | P0 |
| Provider gateway with routing, fallbacks, budgets and local/cloud model blending | LiteLLM gateway, routing, spend tracking and budgets; Ollama launch/tool support. citeturn16search8turn16search0turn16search1turn16search5turn16search20turn16search13turn16search3 | Users want one control plane for cost, latency, reliability and policy across providers. | Very high | Very high | Medium | Medium | P0 |
| OTel-native tracing with GenAI spans, agent spans and evaluation events | OpenTelemetry GenAI semantics; LangSmith OTel. citeturn13search2turn13search17turn13search8turn15search23 | Makes ARC interoperable with the broader observability ecosystem instead of becoming a closed trace silo. | Very high | High | Medium | Low | P0 |
| Dataset builder from production traces with automatic regression gates | Phoenix datasets from traces; MLflow datasets from traces; LangSmith datasets and automation rules. citeturn13search9turn13search10turn15search19turn15search22 | Lets teams convert field failures into permanent evaluations and deployment gates. | Very high | Very high | Medium | Low | P0 |
| Human review queues with pairwise comparison, assertions and approval routing | LangSmith annotation queues; n8n human-in-the-loop; GitHub PR reviews. citeturn15search0turn15search10turn23search2turn29search10turn29search1 | ARC already has HITL DNA; this packages it into a repeatable team workflow. | Very high | High | Medium | Low | P0 |
| Plugin and Skills SDK with signed manifests, dependency isolation and marketplace-ready packaging | Claude Code plugins; Cursor plugins + skills; CrewAI skills registry. citeturn7search12turn7search18turn8search5turn8search9turn8search17turn30search23 | Ecosystems win when custom behaviour is shareable, versioned and discoverable. | High | Very high | High | Medium | P1 |
| Team rules, policy bundles, shared workflows and recommended extensions | Cursor Project/Team/User Rules; Windsurf enterprise policies/RBAC; Theia recommended extensions; Sourcegraph context filters. citeturn8search1turn9search7turn9search11turn25search21turn27search10 | Teams need consistent agent behaviour, context boundaries and approved tooling. | Very high | High | Medium | Low | P1 |
| Layered local sandbox profiles on Linux and Windows | Landlock; bubblewrap; nsjail; gVisor; Firecracker + jailer; Codex Windows sandbox guidance. citeturn20search0turn19search4turn20search2turn19search1turn19search3turn19search15turn19search0turn21search4turn31search1turn31search16 | A profile-driven model is easier for users to understand and safer to operate than one “sandbox on/off” switch. | Very high | Very high | High | Medium | P1 |
| Fast sandbox warm starts via snapshot cache and reusable execution templates | E2B templates and snapshots; Daytona stateful snapshots/archive; Firecracker snapshots. citeturn22search3turn22search6turn22search9turn22search10turn21search7 | Startup latency is one of the biggest hidden taxes on agentic workflows. | High | High | High | Medium | P1 |
| Temporal graph memory with explicit user, project, workflow and episode scopes | Zep/Graphiti temporal graph; Mem0 entity linking, deletion and evaluation; LangGraph memory. citeturn17search13turn17search1turn17search5turn17search8turn17search20turn17search12turn30search0 | Improves cross-session recall while keeping provenance and erasure manageable. | Very high | High | High | Medium | P1 |
| SwarmGraph policy lab supporting multiple coordination patterns under one runtime | AutoGen swarm, debate and mixture-of-agents; LangGraph subgraphs; CrewAI crews/flows. citeturn30search4turn30search14turn30search18turn30search0turn30search2turn30search11 | Exposes ARC’s multi-agent runtime as a comparative lab rather than a fixed orchestrator. | Very high | High | High | Medium | P1 |
| Battle tab benchmark packs with scorer cards, replay diffing and judge debate | Braintrust eval workflow; LangSmith evaluation; OpenHands evaluation framework. citeturn14search0turn14search19turn15search16turn12search10 | Gives ARC a concrete way to prove swarm/risk/memory improvements rather than merely claim them. | Very high | High | Medium | Low | P1 |
| PR automation and code-scanning output | GitHub pull request review APIs; reusable workflows; SARIF uploads and code scanning. citeturn29search1turn29search4turn29search15turn29search21turn29search2turn29search5turn29search11 | Bridges ARC from local experimentation to team delivery and governance. | High | High | Medium | Low | P1 |
| VS Code and Theia extension bridge plus extension recommendations | Theia supports VS Code extensions and recommended extensions; Theia is desktop/browser and JSON-RPC based. citeturn25search0turn25search2turn25search3turn25search6turn25search21 | Lets ARC inherit ecosystem value quickly and reduce pressure to build every integration natively. | Very high | High | Medium | Medium | P1 |
| Adapter certification kit for agent frameworks and MCP servers | LangGraph workflows/memory/observability; AutoGen event-driven systems; CrewAI production flows; MCP SDK tiers. citeturn30search0turn30search1turn30search2turn30search21turn18search7 | Makes ARC the safest place to mix frameworks without subtle behavioural drift. | Very high | Medium to high | High | Medium | P1 |

## Priority cuts

The opportunities above are the full strategic set. The tables below recut them into the lists you explicitly asked for.

### Quick wins

These are the items I would expect to deliver meaningful user impact within one quarter without requiring deep new infrastructure.

| Quick win | Why now | Source signal |
| --- | --- | --- |
| Reviewable Plan Mode | High user trust gain for modest implementation cost. | Cursor Plan Mode. citeturn8search32 |
| Agent Command Centre shell | ARC already has the right tabs; the win is unification. | Windsurf Agent Command Center; Claude agent view. citeturn9search13turn7search11 |
| Worktree-first execution toggle | Immediate safety and collision reduction. | Claude worktrees; Cursor CLI worktrees; Windsurf worktrees. citeturn7search17turn8search25turn9search14 |
| MCP registry browser | Strong discoverability gain; widely expected by advanced users. | Official MCP Registry; Cursor install links. citeturn18search16turn8search14 |
| Embedded MCP Inspector | Great developer-experience upgrade with clear value. | MCP Inspector. citeturn18search1 |
| Provider profiles with fallback chains | Easy to understand and highly valuable in practice. | LiteLLM routing/budgets. citeturn16search0turn16search5 |
| Trace export via OpenTelemetry | Interoperability feature with outsized strategic value. | OpenTelemetry; LangSmith OTel. citeturn13search2turn15search23 |
| Shared ARC rules file | Users already understand project-scoped instruction files. | Cursor Rules; Claude `.claude`; Windsurf AGENTS.md; Gemini `GEMINI.md`; Codex AGENTS.md. citeturn8search1turn7search9turn9search23turn26search9turn31search3 |
| Run checkpoints and revert | Safety affordance users immediately understand. | Windsurf checkpoints; E2B snapshots. citeturn9search8turn22search0 |
| CI-friendly eval dataset builder | Converts existing ARC trace storage into practical team value. | Phoenix; MLflow; LangSmith. citeturn13search10turn15search19turn13search9 |

### Moat and deep-tech opportunities

These are the features with the best chance of making ARC meaningfully different rather than merely competitive.

| Deep-tech opportunity | Why it can be a moat | Research or product signal |
| --- | --- | --- |
| Adaptive quorum and early-stop consensus in SwarmGraph | Most tools expose multi-agent execution, but not principled stopping and disagreement handling. | Multi-agent debate with adaptive stability detection; consensus-vs-voting literature. citeturn28search9turn28search12turn28search20 |
| Commit-reveal escrow for agent actions or reward allocation | Unusual, defensible mechanism for fair arbitration and anti-gaming in agent competitions. | Commit-Reveal² and related escrow work. citeturn28search7turn28search25turn28search16 |
| Temporal graph memory with provenance | Few IDEs have durable memory that is explainable, time-aware and deletable. | Zep/Graphiti; Mem0. citeturn17search13turn17search1turn17search5turn17search8turn17search20 |
| SwarmGraph policy lab | Lets ARC compare orchestration patterns under one runtime. | AutoGen patterns; CrewAI flows; LangGraph subgraphs. citeturn30search4turn30search14turn30search18turn30search2turn30search0 |
| Risk-adaptive sandbox escalation | Better than binary “full access” modes. | gVisor, Firecracker, Landlock, bubblewrap. citeturn19search1turn19search0turn20search0turn19search4 |
| Deterministic replay diffing across runs | ARC’s JSONL plus SQLite architecture is naturally suited to this. | Braintrust, Phoenix, LangSmith all prove the value of trace comparison and replay. citeturn14search16turn13search15turn15search14 |
| Battle tab with benchmark packs tied to production traces | Distinctive because it connects research, product and operations. | OpenHands evaluation framework; LangSmith/Braintrust eval loops. citeturn12search10turn14search0turn15search16 |
| Signed plugins, MCP manifests and run attestations | Gives ARC a credible enterprise security story. | Sigstore, SLSA, SPDX. citeturn24search11turn24search13turn24search6 |
| Provider policy router with cost, latency and risk budgets | Strong differentiator for teams operating mixed local and hosted models. | LiteLLM budgets, spend tracking and routing. citeturn16search0turn16search1turn16search5 |
| Adapter certification and behavioural conformance suite | Hard for competitors to copy quickly because it compounds over time with ecosystem relationships. | MCP SDK tiers and mature framework behaviours. citeturn18search7turn30search0turn30search1turn30search2 |

### UX polish opportunities

These are mostly about packaging and legibility rather than deep architecture.

| UX polish opportunity | Why users will notice it |
| --- | --- |
| Single-pane Agent Command Centre | Makes ARC feel modern immediately and reduces tab-hopping. citeturn9search13turn7search11turn31search24 |
| Plan → run → diff → approve flow | Aligns with how Cursor, Claude and Codex frame autonomous coding. citeturn8search32turn7search25turn31search4 |
| Live run HUD with model, approval mode, sandbox, cost and risk | Users hate invisible defaults. This should be always-on. | Market pattern across configurable agent CLIs and IDEs. citeturn31search4turn8search34turn7search13 |
| One-click “save as workflow” from a successful run | A high-satisfaction moment that grows cumulative value. | Windsurf Workflows; CrewAI Flows. citeturn9search2turn30search2 |
| Diff timeline with checkpoint labels | Users understand history faster than logs. | Windsurf checkpoints; Phoenix span replay. citeturn9search8turn13search15 |
| Tool provenance side panel | “Why did the agent call this?” should be inspectable. | MCP schema descriptions and modern trace UIs make this natural. citeturn18search15turn14search16 |
| Memory inspector | Needed if ARC will ship graph memory credibly. | Zep graph and Graphiti explainability value. citeturn17search13turn17search25 |
| Keyboard-first slash and command palette flows | Power users now expect this in every CLI/IDE agent. | Claude commands; Aider commands; Windsurf terminal command mode. citeturn7search7turn10search16turn9search17 |
| In-IDE artifact/canvas panels for evals, dashboards and battle results | Helpful for non-code outputs. | Cursor canvases; Windsurf previews. citeturn8search33turn9search25 |
| Cross-run comparison view | Makes regressions obvious without external tools. | LangSmith, Braintrust and Phoenix all lean hard into trace examination and comparison. citeturn15search14turn14search16turn13search12 |

### Security hardening opportunities

| Security opportunity | What to implement |
| --- | --- |
| Policy-as-code for tool/server/command allowlists | Ship a readable policy file with inheritance and team overrides. Cursor’s `permissions.json` is a strong reference. citeturn8search34 |
| Layered Linux sandbox profile | Use Landlock plus bubblewrap and seccomp as the default local profile; reserve container or gVisor fallback for heavier cases. citeturn20search0turn19search4turn20search2turn19search1 |
| Container fallback with explicit defence-in-depth docs | Make the security posture legible. gVisor’s documentation is notably clear about trade-offs. citeturn19search3turn19search15 |
| MicroVM preflight recipes for high-risk workflows | Keep the default local-first posture, but offer a clear escalation path. citeturn19search0turn21search4turn21search7 |
| Network egress profiles | Offer no-network, allowlisted, and full-network modes, with visible labels in the UI. Similar patterns already exist in sandboxes such as Modal. citeturn22search23 |
| Signed plugins, MCP packages and skill bundles | Require signatures or checksums for marketplace installation. citeturn24search11turn24search15 |
| SBOM generation and provenance attestations on releases | Important for enterprise distribution. citeturn24search6turn24search13turn24search19 |
| Secret brokering with scope and TTL | Pair provider routing with secret boundaries rather than `.env` sprawl. GitHub deployment environments are a good mental model. citeturn29search21 |
| Audit-grade denied-operation logs | Landlock already supports audit logging; ARC should surface this profile-level telemetry. citeturn20search19 |
| Context boundary enforcement for repositories and MCP roots | Borrow from Sourcegraph context filters and MCP roots. citeturn27search10turn18search0 |

### Integrations ARC should support

These are the external integrations I would prioritise beyond the framework adapters you already named.

| Integration | Why it belongs in the top tier |
| --- | --- |
| Official MCP Registry | Discovery, install metadata and a de facto ecosystem index. citeturn18search16turn18search10 |
| Sourcegraph MCP Server | Gives agents cross-repo code intelligence and deep search. citeturn27search14turn27search1 |
| LiteLLM Gateway | Best current open gateway for routing, fallback, budgets and spend tracking. citeturn16search8turn16search0turn16search1turn16search5 |
| Ollama | Essential for serious local-first model workflows. citeturn16search3turn16search7turn16search13 |
| GitHub pull requests, review APIs and Actions | Still the centre of team delivery and approvals. citeturn29search1turn29search15turn29search21turn29search24 |
| GitHub SARIF/code scanning | Natural bridge from ARC assurance to repository security surfaces. citeturn29search2turn29search5turn29search11 |
| LangSmith | Strong option for teams already in LangChain/LangGraph ecosystems. citeturn15search5turn15search0turn15search23 |
| Braintrust | Strong option for eval-heavy teams that need prompt and trace operations. citeturn14search0turn14search1turn14search24 |
| Phoenix and OpenTelemetry Collector | Best path to open observability and prompt replay. citeturn13search12turn13search15turn13search2 |
| Temporal | Best-in-class inspiration and integration point for durable workflows. citeturn23search8turn23search0turn23search16 |

## Competitive gap analysis

### Features competitors have that are not explicit in the ARC brief

Based on the capability list you provided, the features below are **not explicitly visible** in ARC today. If some already exist internally, I would still treat this list as a packaging/discoverability backlog, because the market leaders are making these capabilities very obvious.

| Competitor feature | Evidence | Recommendation |
| --- | --- | --- |
| Worktree-native parallelism | Claude, Cursor, Windsurf and Codex all make this visible. citeturn7search17turn8search25turn9search14turn31search24 | Match quickly. This is now baseline for safe parallel agent editing. |
| Kanban or supervisor-style multi-agent command centre | Windsurf and Claude expose explicit multi-agent oversight UIs; Codex app emphasises parallel threads. citeturn9search13turn7search11turn31search24 | Match, but exceed with runtime risk and replay overlays. |
| Reviewable plan-before-execute flow | Cursor makes this a first-class mode. citeturn8search32 | Match immediately. |
| Checkpoints and quick revert | Windsurf surfaces checkpoints directly. citeturn9search8 | Match immediately. |
| Plugin/skills marketplace packaging | Claude, Cursor and CrewAI all package custom behaviour as shareable units. citeturn7search12turn8search5turn8search17turn30search23 | Match in SDK form first; marketplace later. |
| One-click MCP install links and registry-style discovery | Cursor and official MCP infrastructure already support this mental model. citeturn8search14turn18search16 | Match. ARC should feel native to the MCP ecosystem. |
| Pairwise human review queues | LangSmith supports pairwise queues; GitHub review workflows remain central. citeturn15search0turn29search10 | Match in Assurance/Battle. |
| Datasets from traces with automation | LangSmith, Phoenix and MLflow make this explicit. citeturn15search19turn15search22turn13search10 | Match; this directly fits ARC’s trace and replay model. |
| Fine-grained provider routing and budgeting | LiteLLM makes this concrete and operational. citeturn16search0turn16search1turn16search5 | Match. |
| Context boundaries and admin policy surfaces | Sourcegraph and enterprise IDEs expose this very visibly. citeturn27search10turn9search7turn9search11 | Match with team policy bundles. |

### Features ARC can have that competitors do not

This is where ARC should aim to lead, not follow.

| ARC opportunity | Why it is differentiated |
| --- | --- |
| SwarmGraph consensus debugger | Most tools show agent outputs; ARC can show **how agreement formed**, which agent dissented, and what changed consensus. |
| Risk-adaptive swarm policy | Competing tools expose approvals; ARC can expose dynamic quorum, escalation and sandbox changes based on observed risk. |
| Commit-reveal escrow for contested actions or reward allocation | This is not normal IDE territory and could make ARC unique in agent tournaments, contracts and battle-style evaluation. citeturn28search7turn28search25 |
| Battle tab as a live bench harness | A visible research-to-product surface is rare among AI IDEs. |
| Deterministic replay over local-first traces | Competitors trace; ARC can make reproducibility a first-class offline capability. |
| Memory graph with temporal provenance and deletion | More explainable than a hidden prompt cache; stronger for enterprise governance. citeturn17search13turn17search20 |
| Assurance as a product, not a sidecar | Most IDEs leave evaluation to external tools; ARC can make assurance part of the coding loop. |
| MicroVM preflight only when risk merits it | Stronger than always-on container overhead or unsafe host execution. citeturn19search0turn21search7 |
| Open adapter certification across frameworks | ARC already has broad adapter ambitions; formalising conformance would compound over time. |
| Local-first, team-grade agent cockpit | The combination of private local control with enterprise review/policy is still not well served by the market. |

## Recommended roadmaps

The roadmap below assumes ARC wants to become both immediately credible to users switching from rival AI IDEs and strategically differentiated in multi-agent runtime operations. The sequencing is designed to first close the biggest ergonomics gaps, then deepen observability and policy, then bet on moats. This follows the direction of the broader market: plan-before-act, parallel worktrees, MCP ecosystems, trace-to-eval loops and safer execution are already established expectations. citeturn8search32turn7search11turn9search13turn18search16turn15search19turn19search1turn19search0

### Three-month roadmap

| Time slice | Outcomes | Concrete deliverables |
| --- | --- | --- |
| First month | Make ARC feel current | Agent Command Centre alpha; Plan Mode; run HUD showing model/approval/sandbox/risk; worktree execution option; checkpoint/revert for runs. |
| Second month | Make ARC feel extensible | MCP registry browser; embedded MCP Inspector; shared ARC rules file; provider profiles backed by LiteLLM-style concepts; adapter conformance smoke tests. |
| Third month | Make ARC feel trustworthy | OTel export; dataset-from-traces flow; human review queue MVP; GitHub PR + SARIF integration; policy-as-code allowlists; signed plugin/skills manifest format draft. |

If the team can only ship **three** things in the next quarter, I would pick: **Agent Command Centre**, **Plan Mode**, and **MCP Registry + Inspector**. Those three close the biggest visible user-experience gap while reinforcing ARC’s architecture instead of distracting from it. citeturn9search13turn7search11turn8search32turn18search1turn18search16

### Twelve-month roadmap

| Phase | Goal | Recommended scope |
| --- | --- | --- |
| Early phase | Match the best current AI IDE ergonomics | Full command centre, worktree flow, plan/review loops, checkpoints, better CLI/REPL, project and team rules, extension bridge for VS Code/Theia packaging. |
| Middle phase | Own the assurance and operations loop | OTel-native tracing, eval datasets from traces, pairwise review, CI gates, GitHub SARIF, replay diffing, provider routing, policy bundles, secrets scopes. |
| Late phase | Turn ARC into a true runtime cockpit | Temporal graph memory, sandbox profile engine, snapshot cache, SwarmGraph policy lab, benchmark packs, adapter certification suite. |
| Frontier phase | Build the moat | Adaptive consensus termination, commit-reveal escrow experiments, consensus debugger, risk-adaptive sandbox escalation, signed ecosystem components, verifiable artefacts. |

A practical way to phrase the twelve-month ambition internally would be:

**By the end of the year, ARC should be the product where teams can**  
**design** agents,  
**run** them safely in parallel,  
**observe** every decision,  
**review** and replay failures,  
**govern** tools and models with policy, and  
**prove** improvements with battle-grade evaluation.

If ARC executes that sequence well, it does not need to out-Cursor Cursor or out-Claude Claude. It can become the leading **agent runtime cockpit**: the place where serious teams operate, govern and improve agent systems, not just prompt them.