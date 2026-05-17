# Chunk-Safe Prompt: ARC Studio Full Visual + UX Spec

You are producing `docs/research/ARC_STUDIO_UX_SPEC.md`, the definitive visual and UX specification for ARC Studio.

## Execution Rule

Do **not** attempt to generate the full document in one response. Work in fixed chunks and write directly to the target file.

1. Create or replace `docs/research/ARC_STUDIO_UX_SPEC.md` with the title, executive summary, and table of contents.
2. Write sections in this exact chunk order:
   - Chunk A: §1-§3
   - Chunk B: §4-§6
   - Chunk C: §7.1-§7.7
   - Chunk D: §7.8-§7.14
   - Chunk E: §8
   - Chunk F: §9
   - Chunk G: §10-§11
   - Chunk H: §12-§17 and “What would make this spec wrong”
3. After each chunk, verify the file contains that chunk’s section headings.
4. If output becomes too large, reduce prose, keep tables, keep exact decisions.
5. Never call a subagent to write the entire document. Only write one chunk at a time.

## Non-Negotiable Content

Include all requested sections §1-§17 in order:

- §1 Brand foundation
- §2 Colour system
- §3 Typography
- §4 Iconography
- §5 Layout and spacing
- §6 Motion
- §7 CLI full screen layouts
- §8 IDE full screen layouts
- §9 Component library
- §10 Content and microcopy
- §11 Graph visualiser
- §12 Backgrounds, textures, surface treatment
- §13 Sound and haptics
- §14 Accessibility specification
- §15 States and edge cases
- §16 Asset and deliverables list
- §17 Open questions
- Final page: What would make this spec wrong

## Required Product Decisions

- Product name: ARC Studio.
- Tagline: “Run agents. See everything.”
- Global CLI: `npm install -g arc-studio`, `pipx install arc-studio`.
- Default launch: `arc-studio` starts chat in CWD.
- Default runtime: SwarmGraph, bundled, `runtime.swarmgraph.cli = "bundled"`.
- Config: `.arc/config.yaml` and `~/.config/arc-studio/config.yaml`.
- Provider keys: OS keyring by default; env vars override; never logged.
- IDE panels: Chat, Plan, Graph, Runs/Trace, Review/Apply, Config.
- Modes: Plan / Build / Auto; Tab cycles in CLI; button cycles in IDE.
- Legacy: `arc` and `arc-studio advanced ...` preserved.
- Icon set: Lucide.
- UI sans: Inter.
- Mono: JetBrains Mono.
- Graph: Cytoscape.js in IDE, Unicode box drawing in CLI.

## Runtime Honesty Matrix

Use this matrix whenever showing runtime capability:

| Runtime | Current UI consequence |
|---|---|
| SwarmGraph | Default; can inspect/run/export schema/export workflow; graph shown as first-class. |
| LangGraph | Inspect/export; node events may be coalesced; badge `(coalesced)`. |
| CrewAI | Inspect/export; run path gated by export target and paid-call policy. |
| OpenAI Agents | Partial; run only if SDK/export target present; trace hooks available. |
| AG2 | Registered/detection/export only unless export target present. |
| LlamaIndex | Detection/static export only; no run button. |
| LM Arena | Stub-default; live path gated; no graph. |

## Style Rules

- No marketing words: “powerful”, “seamless”, “modern”, “intuitive”, “next-gen”.
- Every visual decision references a token.
- No hex outside §2.
- Every interactive component has default, hover, focus-visible, active, disabled states.
- CLI must work at 80 columns and degrade below.
- Use Markdown tables when possible.
- Use Unicode wireframes for CLI/IDE mockups.
- Mark uncertain values `[proposed]`.
