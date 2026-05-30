# Production-Grade Expansion Prompt: ARC Studio Visual + UX Spec

You are upgrading `docs/research/ARC_STUDIO_UX_SPEC.md` from a complete draft into a production-grade implementation specification.

## Execution Safety

Do not generate the whole document in one model response. Expand in deterministic chunks and write directly to `docs/research/ARC_STUDIO_UX_SPEC.md`.

Chunk order:

1. Expand §2 to include a full token table, high-contrast notes, ANSI palette, theme resolution, and custom theme YAML.
2. Expand §7 so every CLI screen has: 100-column layout target, 80-column fallback, region map, keybindings, colour tokens, exact placeholders.
3. Expand §8 so every IDE layout has: wireframe, dimensions, state table, components, shortcuts.
4. Expand §9 so every reusable component has: visual spec, variants, props sketch, ARIA/focus behaviour, and five states.
5. Expand §10-§15 with exact copy, graph visualiser design, accessibility flow, and state matrix.
6. Expand §16-§17 with asset filenames, formats, dimensions, colour space, and open decisions.
7. Verify headings §1-§17 remain in order.

## Production Bar

The final spec is complete only when an implementer can:

- Implement dark/light/high-contrast themes without choosing any new hex value.
- Render every CLI screen from the mockups and fallback rules.
- Build every component from the component spec and TypeScript prop sketch.
- Use exact copy for errors, empty states, loading, confirmation, and help text.
- Implement the Graph panel and CLI graph with consistent node/edge/state styling.
- Pass WCAG AA with the stated colour and keyboard rules.

## Mandatory Rules

- No marketing words: powerful, seamless, modern, intuitive, next-gen.
- Do not invent runtime capabilities.
- Use the runtime honesty matrix exactly.
- No provider secrets appear in output examples.
- Every interactive component has default, hover, focus-visible, active, disabled.
- Every CLI element works at 80 columns and degrades below.
- Use `[proposed]` for uncertain implementation values.

## Required Runtime Honesty Matrix

| Runtime | UI consequence |
|---|---|
| SwarmGraph | Default; inspect/run/export schema/export workflow; first-class graph. |
| LangGraph | Inspect/export; node updates may be coalesced; graph badge `(coalesced)`. |
| CrewAI | Inspect/export; run gated by export target and paid-call policy. |
| OpenAI Agents | Partial; run only if SDK/export target present; trace hooks available. |
| AG2 | Registered/detection/export unless export target present. |
| LlamaIndex | Detection/static export only; no run button. |
| LM Arena | Stub-default; live path gated; no graph. |

## Required Output

Update `docs/research/ARC_STUDIO_UX_SPEC.md` in place. Do not create a summary-only document.
