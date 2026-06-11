# Facade-Cost Scoring Protocol (decision criterion #1 — defined BEFORE numbers exist)

The ADR-0002 addendum ranks clean candidates by (1) facade cost, (2) G8
sustainability, (3) a11y/IME evidence quality. Criteria (2) and (3) have
defined evidence formats; this document pins (1) so it cannot be scored
post-hoc to favor a preferred candidate. **Committed before any spike report
exists** — that is the point.

## What is measured

The cost of making `arc_ui::kit` real for the candidate: port the Sprint-2
ShellModel render surface (already specified as executable tests in
`rust/arc-ui` and `rust/arc-shell`) to the candidate framework:

1. **Palette overlay** — modal layer, query line, ≤50 result rows, selected-row
   highlight; keyboard events routed to `PaletteModel::key`; announcements
   surfaced (print/log acceptable at spike stage).
2. **Focus ring** — F6/Shift-F6 across the four spike views, visible focus
   indicator, `FocusRing` as source of truth.
3. **Status rail** — one line bottom-aligned, text from `ShellModel::status_rail()`,
   re-rendered on state change.
4. **Theme hook** — `NO_COLOR`/high-contrast from `arc_ui::Theme` actually
   changing rendered output.

Explicitly OUT of scope: editor text shaping, dock panels, settings — facade
cost is about the *shell chrome*, the part `arc-ui` abstracts.

## The four sub-scores (each 1–5, 5 = cheapest/safest)

| Sub-score | Definition | How measured |
|---|---|---|
| F-LOC | Size of the port | `tokei`-counted Rust LOC of the candidate-specific render layer (exclude the shared models — they don't change by design). 5: <300 LOC · 4: <600 · 3: <1000 · 2: <1600 · 1: ≥1600 |
| F-CONCEPT | Concept mismatch | Count of places where the candidate's model FORCED a change to arc-ui/arc-shell shared code (each is a facade leak). 5: 0 changes · 4: 1 · 3: 2–3 · 2: 4–6 · 1: >6 |
| F-EVENT | Input routing fit | Keyboard/focus events reach `PaletteModel::key` / `FocusRing` without shadow state. 5: direct · 3: needs a thin adapter layer · 1: needs a parallel state machine (disqualifying smell) |
| F-SWAP | Reversibility | Honest estimate (recorded with reasoning) of days to re-port to the runner-up candidate. 5: ≤3 days · 4: ≤5 · 3: ≤10 · 2: ≤15 · 1: >15 |

Facade score = sum (max 20). Ties on the total are broken by F-CONCEPT
(facade leaks are the most expensive long-term).

## Rules

- The port is done ONCE per candidate, during/after that candidate's spike
  sitting, by the same operator, against the same shared models (no model
  edits between candidates — if a model edit proves necessary, it lands
  first, then ALL candidates re-score F-CONCEPT against the updated models).
- The ported code lives in `rust/spikes/<candidate>-editor/src/shell_port.rs`
  (one file, to make F-LOC counting unambiguous). Throwaway-by-contract like
  the rest of the spike.
- LOC counted by `tokei --type Rust rust/spikes/<candidate>-editor/src/shell_port.rs`
  (code lines, not comments/blanks); the number and the tokei output go into
  the report notes.
- F-SWAP estimates must cite specifics ("event model identical to X, only
  paint differs" / "owns the event loop, re-port = rewrite") — a bare number
  is not evidence.
- Scores go into a `facade` block appended to `reports/spike-<candidate>.json`
  (additive key; the harness ignores unknown keys by design).

## Worked guardrails (so 1-vs-5 anchors are concrete)

- Sprint-2's headless ShellModel render in `arc-shell --headless-status` is
  ~60 LOC of plain `println!` — the F-LOC floor intuition for "model is doing
  all the work".
- A candidate needing its own focus concept *alongside* `FocusRing` (two
  sources of truth) scores F-EVENT ≤ 2 regardless of LOC.
- A candidate that renders the palette but cannot trap modal focus scores
  the gap under G5 (a11y), NOT here — no double-counting.
