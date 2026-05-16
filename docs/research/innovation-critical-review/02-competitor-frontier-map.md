# Competitor Frontier Map

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

Legend: **Catch-up** = ARC must match but should not brag. **Differentiated** = ARC can credibly own if implemented deeply. **Open frontier** = weakly served by competitors or emerging.

| Product / system | Current strong pattern | Catch-up features ARC must match | Differentiated frontier ARC can own | ARC can win if... |
|---|---|---|---|---|
| Claude Code | Terminal-native agent loop, permissions, MCP, hooks/skills/subagents [needs verification], emerging auto mode. | Chat-first CLI, resume, slash commands, permissions. | Contracted run accountability, graph-native multi-agent cockpit, policy simulation that explains scope gaps. | ARC shows why every decision happened and can command graph nodes, not just approve tool calls. |
| OpenCode | Fast TUI, provider flexibility, simple command surface [needs verification]. | TUI polish, model switching, session commands. | Runtime capability negotiation and multi-surface session twin. | ARC is less “CLI chat” and more a cockpit mirrored into IDE. |
| Codex CLI / Codex desktop | Sandboxed coding agent, desktop/app integrations, background agents, broader platform trajectory [needs verification]. | Approvals, sandbox language, AGENTS.md-style guidance. | Local-first flight recorder, secure delegation tokens, runtime manifests. | ARC becomes the transparent local control plane over many runtimes instead of one vendor agent. |
| Cursor | Agent mode, inline edits, rules, codebase context, smooth IDE-native flow. | Right-sidebar chat, model dropdown, diffs, code context. | Evidence-linked graph/run contracts and failure autopsy. | ARC avoids competing on editor magic alone and wins on operational trust. |
| Windsurf | Cascade, memories, rules, project-wide edits, collaborative feeling [needs verification]. | Chat + tasks + edit/revert basics. | Intent Ledger and graph/chat cross-highlighting. | ARC makes agent work inspectable rather than just conversational. |
| Kiro | Spec/steering workflow and planned implementation loops [needs verification]. | Spec-like tasks, steering/project rules. | Enforceable agent constitution + policy simulator + run contract fulfillment. | ARC makes “specs” executable and auditable, not just documents. |
| Replit Agent | End-to-end app building, previews, deployment, checkpoints [needs verification]. | Preview/deploy is not ARC v0.1’s lane. | HotLoop visual run contracts and frame receipts later. | ARC handles local professional workflows with stricter trust and evidence. |
| GitHub Copilot Workspace / Coding Agent | Issue/PR-native delegation, draft PRs, multi-agent sessions emerging in GitHub ecosystem [needs verification]. | PR descriptions, comments, reviews, task assignment. | Agent Run Receipts pasted into PRs with evidence/cost/risk/rollback. | ARC produces better PR accountability artifacts than GitHub-native agents. |
| VS Code Copilot | Ubiquitous IDE chat/edit/agent surface, settings integration. | Chat sidebar, model mode, inline/context actions. | Agent runtime cockpit panels, not another generic chat sidebar. | ARC exposes runtime graph + safety/cost contracts inside Theia. |
| JetBrains AI Assistant / Junie | Deep IDE model, inspections, code understanding, agentic development [needs verification]. | IDE integration and code navigation. | Evaluation/flight-recorder-first agent debugging. | ARC integrates run/eval/audit into the execution loop. |
| Sourcegraph Cody / Amp | Code search context and broad codebase understanding [needs verification]. | Strong search/context mentions. | Evidence Cards that distinguish search evidence from agent claims. | ARC turns context into verifiable claim cards. |
| LangGraph Studio | Graph debugging, interrupts, state visualization, time travel [needs verification]. | Graph state and run inspection. | Cross-runtime cockpit with runtime negotiation and HITL contracts. | ARC makes graphs operational across runtimes, not only LangGraph app debugging. |
| Temporal UI | Workflow history, retries, deterministic workflow operations. | Run history, retries, failure localization. | Agent-specific intent/evidence/cost/safety summaries. | ARC borrows operational rigor but speaks human agent accountability. |
| Prefect | Flow/task run visibility and orchestration UI [needs verification]. | State tables, retry/flow runs. | Human-in-the-loop contracts and evidence-linked agent decisions. | ARC maps orchestration concepts to AI-specific trust and cost. |
| Dagster | Asset graph, lineage, materializations [needs verification]. | Graph lineage and status. | Code-agent graph as command surface, not data pipeline observability. | ARC uses graph nodes as actuators with contracts. |
| Linear / Notion task systems | Clean task hierarchy, statuses, ownership, docs. | Task lists and phase cards. | Agent tasks tied to runtime evidence, policy, and receipts. | ARC makes tasks executable and accountable. |
| MCP ecosystem | Tool/data interoperability, fast adoption, but weak production safety semantics. | MCP client/server support. | Permission mapping, signed tool descriptors, cost/risk preview, evidence receipts. | ARC becomes the MCP safety/control plane. |
| ACP / A2A-style tools | Agent interoperability, cards/capability discovery [needs verification]. | Agent capability descriptors. | ARC-specific runtime capability negotiation and handoff workbench. | ARC treats external agents as runtimes with contracts and receipts. |
| Emerging skills systems | Reusable workflows/prompts/tool packs [needs verification]. | Skill discovery/invocation. | Skills with conformance tests, evidence obligations, and trust scopes. | ARC rejects opaque prompt packs and certifies skills as runtime artifacts. |
| AI browser/control loops | Visual observation/action loops and browser automation. | HotLoop reservation. | Frame receipts, visual diff contracts, multimodal risk gates. | ARC delays flashy browser control until it can audit every frame/action. |
| Local-first/security-first tools | Keyrings, sandboxing, local storage. | OS keyring, no self-updating binary, local daemon. | HMAC-linked flight recorder, trust diff, scoped delegation tokens. | ARC turns local-first into visible operational trust, not just architecture. |

## Frontier Synthesis

The open frontier is not “better chat.” It is **agent operations**: contracts, evidence, policy, runtime capabilities, replay/simulation, cost, failure recovery, and cross-surface control. Most competitors optimize how the agent writes code. ARC should optimize how developers **command, constrain, inspect, compare, and trust** agents.

## Competitor Claims To Verify Before Publication

- Claude Code exact number and semantics of permission modes, hooks, skills, and subagents.
- OpenCode current custom command and provider surface.
- Kiro current spec/steering/autopilot semantics.
- Cursor/Windsurf current memories/rules/MCP support.
- LangGraph Studio current replay/time-travel and interrupt UX.
- ACP naming: confirm whether the target is Agent Client Protocol, Agent2Agent, or another ACP artifact.
