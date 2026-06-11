# ARC v2 Continue Implementation Prompt

You are continuing ARC v2 on branch `arc-v2/sprint-1-protocol-bridge`.

Start by reading:

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-sprint-3-spike-runbook.md`
4. `docs/planning/arc-v2-sprint-3-decision-matrix.md`
5. `docs/planning/arc-v2-facade-cost-protocol.md`
6. `docs/planning/arc-v2-macos-g5-g6-protocol.md`
7. `docs/planning/arc-v2-hitl-decision-api-proposal.md`

Before editing, verify the current lineage:

```bash
git log --oneline -5
```

Expected recent commits include:

```text
9f344f11 sprint-8: HitlModal + DiffReview + HITL API proposal; baton updated
ececa198 Sprint 5+6: arc-workspace, arc-index, arc-terminal
a60c6199 arc-editor + arc-dock + streams: Sprint-4 buffer + Sprint-7 panel layer
```

## Current State

Framework-free ARC v2 cores are built and tested across 9 Rust crates:

- `arc-protocol-rs`
- `arc-daemon-client`
- `arc-ui`
- `arc-shell`
- `arc-editor`
- `arc-dock`
- `arc-workspace`
- `arc-index`
- `arc-terminal`

Mac workspace verification at this point:

```bash
cd rust
cargo fmt --all --check
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
```

Known macOS result: 117 tests pass. Linux expected: 104 tests plus Linux-only watcher and terminal throughput rows. CI compile evidence is not runtime evidence.

## Baton

The baton is split:

- **M4 local CLI:** Sprint-3 framework spike is the critical path.
- **Arena/sandbox:** framework-free cores are done; idle until `reports/spike-<candidate>.json` files land, except for owner-authorized HITL daemon endpoint work.

If you hand the baton over, update `docs/planning/arc-v2-baton.md` in the same commit as your final change.

## Primary Task: M4 Framework Spike

Run in this order:

1. Trigger `arc-v2-spike-xcompile` with `workflow_dispatch` to catch Linux/Windows compile breakage before hook work.
2. Implement/run **floem** first.
3. Implement/run **gpui**.
4. Implement/run **gpui-ce**.
5. Implement/run **bespoke** last.

Per candidate:

1. Move the candidate crate from `exclude` to `members` in `rust/spikes/Cargo.toml`.
2. Bind `FrameScript` `Action` arms to `spike_harness::views` types:
   - `TextDoc`
   - `DiffDoc`
   - `EventTable`
   - `TypeBox`
   - `bidi_sample_lines()`
3. Use exactly one app/window/event loop per candidate.
4. Call `script.on_present(Instant::now())` only from a trustworthy present/frame-complete callback.
5. Apply at most one returned `Action` per present.
6. Run the script and produce:
   - `reports/spike-<candidate>.json`
   - `reports/spike-raw-<candidate>-g2.json`
   - `reports/spike-raw-<candidate>-g3.json`
   - `reports/spike-raw-<candidate>-g4.json`
7. Add `rust/spikes/<candidate>-editor/src/shell_port.rs` and score facade cost per `arc-v2-facade-cost-protocol.md`.
8. Record macOS G5/G6 evidence per `arc-v2-macos-g5-g6-protocol.md` under `reports/evidence/`.
9. Commit the candidate report, raw data, evidence paths/notes, and any source changes.

## Stop Conditions

Stop and report a finding if:

- A gate is ambiguous.
- A framework only exposes render-return timing, not a trustworthy present/frame-complete callback.
- All candidates fail cleanly; do not self-start a bespoke sprint.

For an untrustworthy callback, record it as candidate evidence and continue to the next candidate. Do not approximate silently.

## Owner-Gated Task: HITL Daemon Endpoint

Do not implement daemon HITL mutation routes unless the owner explicitly checks/approves the proposal in:

`docs/planning/arc-v2-hitl-decision-api-proposal.md`

If approved, implement additively only:

- `POST /api/hitl/{hitl_id}/decision`
- standard `ArcEnvelope` response
- daemon-side validation and audit
- idempotency key behavior
- no shell-side authorization logic
- tests listed in the proposal

## Constraints

- Native-only v2. No Electron/WebView/Tauri fallback.
- Additive protocol only. Do not remove or rename existing events, commands, or public API surfaces.
- Deterministic security only. No LLM allow/deny decisions.
- No framework imports outside `arc-ui` and `rust/spikes/*-editor` throwaway crates.
- No overclaiming. M4 numbers remain indicative unless the owner pins the M4 as benchmark hardware. CI runners are compile evidence only.
- Keep v1 shippable. When touching shared/protocol/web surfaces, preserve:

```bash
cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q
```

Known prior result: 220 passed.

## Verification Before Commit

Run the narrowest relevant checks plus these when Rust workspace changes:

```bash
cd rust
cargo fmt --all --check
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
```

Run banned-claims checks for any planning/docs updates:

```bash
bash scripts/check-banned-claims.sh docs/planning docs/prompts
```

Before committing, inspect:

```bash
git status --short --branch
```

Do not stage build artifacts such as `target/` or candidate-crate local `Cargo.lock` files unless intentionally documenting a dependency lock for that throwaway spike crate.
