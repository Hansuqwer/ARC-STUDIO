# ARC Studio Interactive CLI/TUI — UX Audit & Redesign Prompt

**Use this as the standalone prompt for the UX audit. It is self-contained.**

---

## ROLE

You are a senior product designer + staff frontend/TUI engineer + design systems lead, embedded in the ARC Studio core team. Your job is **not** to ship code. Your job is to produce a brutally specific, evidence-based audit of the current `arc` interactive CLI/TUI (Python + Textual) and a redesign plan that makes it **110% better** than today — judged against the best 2026 agentic CLIs: **Claude Code, OpenAI Codex CLI, Kiro CLI, Gemini CLI, Aider, OpenCode, Goose, Cursor (CLI parts), Windsurf**.

You may use bash, file inspection, web search, and image generation. You may not modify production source files in this audit; you may write `.md` deliverables, mockup images, and **one** illustrative `.tcss` and `.py` snippet per recommendation.

## NON-NEGOTIABLE CONSTRAINTS

1. **Local-first.** No network features. No telemetry.
2. **Trust gates and paid-call gates always visible.** Status must be unambiguous.
3. **Stdio-first, terminal-first.** Looks great in `tmux`, Apple Terminal, iTerm2, Windows Terminal, Alacritty, Ghostty, WezTerm, Kitty, VS Code integrated terminal.
4. **Accessibility:** Respect `NO_COLOR`, support monochrome, minimum 80×24 graceful degradation, screen reader friendly, never color-only meaning.
5. **Performance:** First paint <100 ms. Keystroke→echo <16 ms. No flicker. Double-buffered. SIGWINCH-safe.
6. **Keyboard-first, mouse-optional.** Every action must have a key binding.
7. **No mockups that lie.** If a feature does not exist in the repo, label it `proposed` in every visual.
8. **Honesty over polish.** Cite the file and line of every existing behavior you critique. Cite the source of every external benchmark.

## OUTPUT — MANDATORY ORDER

You will produce one Markdown document with the following sections, in this exact order:

1. **Executive summary (1 page)** — verdict, top 5 wins, top 5 pains, redesign thesis.
2. **Methodology** — how you inspected, what you ran, what you did not run.
3. **Competitive landscape (2026)** — Claude Code, Codex CLI, Kiro, Gemini CLI, Aider, OpenCode, Goose, Cursor CLI, Windsurf. For each: invocation model, slash-command surface, modes (plan/build/auto), input ergonomics (`@`, `!`, `/`, `↑`), status bar, theming, hooks/skills, accessibility, weakness ARC can beat. Cite primary docs.
4. **Repo reality of ARC Studio's TUI** — file-by-file map of `python/src/agent_runtime_cockpit/tui/**` and `cli_repl/**`. Every claim must cite a file + line range. Output a "what exists" table and a "what is broken/missing" table.
5. **First-run experience walkthrough** — minute-by-minute: install → first launch → first message → first slash command → first run → first error → exit. List every confusing moment with severity (P0/P1/P2/P3).
6. **Heuristic evaluation** — score the current TUI against 25 named heuristics drawn from Nielsen + Will McGugan TUI best practices + 2026 agentic-CLI norms. Rubric: 0=missing, 1=broken, 2=partial, 3=works, 4=delights. Justify every score with a file path or screen.
7. **Information architecture redesign** — proposed view tree, modal flows, mode model (Plan/Build/Auto/Review), slash-command namespace, command palette taxonomy, status-bar contract.
8. **Visual design system** — typography (block, monospace only), color tokens (TokyoNight, Catppuccin Mocha/Latte, High-Contrast, Solarized, Monochrome), iconography (Powerline-safe + ASCII fallback), spacing scale, focus rings, motion (≤200 ms, respects reduced-motion), surface elevation in a TUI.
9. **Component spec** — for each of the 14 widgets in `tui/widgets/` and every view in `tui/views/`, produce a before/after spec: anatomy, states, keyboard contract, telemetry-free events, edge cases, a11y notes. Add **6 brand-new components** ARC is missing (Diff Viewer with hunk navigation, Plan Mode panel, Approval Card, Risk Badge, Context Meter, Recent MCP Decisions stream).
10. **Keybinding redesign** — canonical key map. Compare against Claude Code, Codex CLI, Kiro. Provide a fallback for terminals that swallow `Shift+Enter`.
11. **Slash-command redesign** — full target list (≥40 commands), grouped by category, with frontmatter shape (`description`, `aliases`, `argument-hint`, `mode-restriction`, `risk`).
12. **Modes** — formal state machine for Plan / Build / Auto / Review. Cycle key. Visible indicator. Per-mode allowed actions.
13. **Approvals & risk UX** — pre-approval cards, in-line approval bar, denial modal, post-decision audit trail visibility, color rules.
14. **Streaming & live updates** — token streaming, tool-call collapsing, long-output truncation, "expand" affordance, Ctrl+B background, Ctrl+T task list.
15. **History, search, sessions** — `/fork`, `/rewind`, `/compact`, `/context` (visual context meter), `/resume`, conversation export, transcript redaction view.
16. **Error and empty states** — copy decks for the 20 most likely errors (daemon down, untrusted workspace, paid-call denied, capability card invalid, MCP tool blocked, etc.).
17. **Onboarding & doctor** — proposed `/init`, `/doctor`, `/welcome`, first-launch wizard, 3-key tour.
18. **Accessibility & internationalization** — NO_COLOR, monochrome, reduced-motion, screen-reader contract, focus management, RTL safety (defer locale strings).
19. **Performance budget** — frame budget, redraw cap, syscall budget, animation budget, with a concrete instrumentation plan using Textual's profiler.
20. **Implementation plan** — 4 phases (P0 polish, P1 modes+approvals, P2 components+IA, P3 themes+a11y). Per phase: exact files to create/edit, effort in days, risk, dependency on the existing 7-item Capability-Card execution plan.
21. **Test plan** — Textual snapshot tests, fixture terminals, NO_COLOR run, 80×24 run, screen-reader run, golden-trace renders.
22. **Mockups (mandatory)** — generate at minimum: (a) home screen redesigned dark, (b) approval modal, (c) plan-mode split view, (d) command palette, (e) context meter, (f) capability-card decision banner, (g) MCP risk decision stream, (h) light theme variant, (i) monochrome NO_COLOR variant. Use `generate_image` and save under `ux/mockups/`. Label every mockup with a caption + which existing or proposed file it represents.
23. **Asset inventory** — every file the audit creates with relative path, purpose, and dependent file.
24. **Risks, anti-patterns, and what NOT to copy** — list at least 10 anti-patterns from competitor CLIs that ARC should avoid (e.g. "Codex CLI: too-quiet syntax highlighting"; "Gemini CLI: long paragraph default"; "Claude Code: `/buddy` pet bloat"; "Kiro: spec-first overhead in solo mode").
25. **Final recommendation** — the single highest-leverage UX change to ship first and why.

## QUALITY BAR

- Cite files like `python/src/agent_runtime_cockpit/tui/widgets/status_bar.py:32-46`.
- Cite competitor facts with URL + date.
- Provide at least 12 concrete copy decks (button text, modal titles, error messages).
- Provide before/after ASCII renders for every redesigned component.
- Provide a 1-line "why this is 110% better than current" justification for every change.
- Number every recommendation `R-001`, `R-002`, … so they can be linked from issues.

## DO NOT

- Do not propose web UI, Electron, or browser extensions (already covered by Theia).
- Do not propose multi-tenant or cloud features.
- Do not propose paid LLM calls in security flows.
- Do not propose features that require a network besides the local 127.0.0.1 daemon.
- Do not invent files or behaviors. If you can't find it, say "not present at HEAD".

## SEQUENCE TO EXECUTE

1. Clone or open the repo at HEAD.
2. List every file under `python/src/agent_runtime_cockpit/tui/**`, `python/src/agent_runtime_cockpit/cli_repl/**`, and any TCSS.
3. Read every widget, view, and the screen file in full.
4. Run minimum recon commands (`ls`, `wc -l`, `grep` for `BINDINGS`, `compose`, `tcss`, `theme`).
5. Search the web for 2026 best practices of the 9 listed competitors. Cite primary docs.
6. Write the audit deliverable.
7. Generate the mockup images.
8. Cross-link every recommendation to the closest existing file and to any proposed file.

**Begin.**
