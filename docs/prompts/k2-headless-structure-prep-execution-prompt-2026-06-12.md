# ARC v2 K2 Headless Structure/Prep Execution Prompt

Use this prompt before doing K2 headless structure/prep work.

## Intent

Execute the headless-safe subset of K2 for ARC v2 on branch `arc-v2/sprint-1-protocol-bridge`:
- promote the gpui shell-port seed into `rust/arc-shell` as a cfg-gated structure;
- keep `arc-shell --headless-status` working without framework features;
- do not claim window/pixel evidence from a headless environment;
- leave M4/display validation, screenshots, VoiceOver/IME, daemon live-kill pixel proof, and B1 hyperfine measurement to the CLI/M4 agent.

## Required pre-execution research/checks

Before editing code, use all available research tools and record any mismatch honestly:
1. **Context7**: fetch current docs/examples for `gpui` pinned at `=0.2.2` and any Rust cfg/feature-gating pattern needed for optional framework integration.
2. **Vercel Grep / code search**: search upstream/public examples for `gpui 0.2.x` app/window/view patterns, especially `Application::new`, `WindowOptions`, `Render`, `IntoElement`, `on_key_down`, `cx.notify`, and feature-gated framework wrappers.
3. **Web fetch**: fetch canonical docs.rs / GitHub raw docs for `gpui 0.2.2` and relevant Cargo feature docs if Context7/code-search results are incomplete.
4. **Local repo inspection**: read, at minimum:
   - `AGENTS.md`
   - `docs/planning/arc-v2-baton.md`
   - `docs/planning/arc-v2-kit-implementation-plan.md`
   - `rust/spikes/gpui-editor/src/shell_port.rs`
   - `rust/arc-shell/Cargo.toml`
   - `rust/arc-shell/src/{main.rs,lib.rs,shell.rs}`
   - `rust/arc-ui/src/lib.rs` and any model files imported by the shell port.

If Context7 or Vercel Grep are unavailable in the current environment, state that explicitly, use web fetch/search plus local source as the fallback, and avoid making external-API claims that were not verified.

## Execution constraints

- Native-only v2: no Electron/WebView/Tauri fallback.
- Additive only: do not remove/rename public commands, events, or API surfaces.
- No overclaiming: headless compile/test evidence is not pixel/window evidence.
- No framework imports outside `arc-ui` and cfg-gated K2 render modules as authorized by the kit plan; if this creates a facade-governance concern, document it in the baton.
- Default build must remain headless and framework-free.
- `arc-shell --window` may require a feature flag and may return a clear error when built without it.
- Preserve existing headless behavior and tests.
- Do not commit unless explicitly asked; if committing later, provide a git bundle for sync-loss recovery.

## Suggested implementation shape

1. Add a `framework-gpui` feature to `rust/arc-shell` that forwards to `arc-ui/framework-gpui`.
2. Add `rust/arc-shell/src/render_gpui.rs`, cfg-gated behind the feature, seeded from the gpui spike port but adapted to `ShellModel`/current arc-shell APIs.
3. Add a small public entrypoint such as `open_window()` behind the feature.
4. Add/adjust `arc-shell --window` CLI handling:
   - feature on: call the gpui render entrypoint;
   - feature off: return a deterministic unsupported-feature error/message.
5. Add headless-safe tests for CLI argument parsing / unsupported-window behavior / model-to-render helper functions, but do not run display-dependent tests in the sandbox.
6. Run formatting and feasible headless tests. Record exact commands and outcomes.
7. Update `docs/planning/arc-v2-baton.md` at handback with what changed, what was tested, and what remains M4-only.
