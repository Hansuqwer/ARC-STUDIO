# CLI Innovations

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

## Diagnosis

The planned CLI becomes respectable: chat-first `arc-studio`, global install, flat slash commands, mode toggles, `@file` and `@folder`, queued input, `/sessions`, `/undo`, `/redo`, `/runs`, `/graph`, `/doctor`, and advanced trace fallback. That is still mostly competitor parity. A differentiated CLI must feel like a **runtime cockpit in a terminal**, not a lower-fidelity IDE chat.

## CLI Concepts To Ship Or Reserve

| Concept | v0.1 shape | v0.2/v0.3 shape | Differentiation |
|---|---|---|---|
| Run Contract Card | Render before `/run`: objective, runtime, mode, write policy, cost ceiling, rollback, evidence expected. | Editable contract templates. | Turns execution into a bounded agreement. |
| Run Receipt | Always print after run; save `run_receipt.md/json`. | PR export and support bundle. | Makes CLI output trustworthy after terminal scroll disappears. |
| Failure Autopsy | Replace raw failure dumps with node/cause/last safe state/retry/evidence/guess split. | Compare with previous successful run. | Honest debugging without default Trace UI. |
| State-Aware Slash Commands | `/retry failed`, `/why blocked`, `/evidence`, `/contract`, `/receipt`. | Dynamic command palette in TUI. | Commands adapt to current run state. |
| Graph In Terminal As Control Surface | v0.1 explain/select/cross-highlight only. | Node rerun/pause/force handoff after checkpoints. | Graph is no longer decoration. |
| Policy Simulator | `/policy simulate auto` over known action classes. | Scenario library and policy fuzzing. | Safer Auto mode. |
| Trust Diff | Show before `trust`, provider, shell, paid-call policy changes. | Signed policy changes and review queue. | Security settings become reviewable. |
| Session Twin CLI Presence | Status line: attached IDE clients, pending approvals, mirrored selection. | Shared cursor/selection and collaborative approval. | CLI and IDE are one session. |
| Evidence Blocks | `claim -> evidence` expandable blocks in CLI. | Evidence search and filtering. | Makes terminal claims verifiable. |
| Flight Recorder Export | `/export flight-recorder --redacted`. | Import/replay/debug. | Support/evals/compliance without raw traces. |

## Proposed CLI Command Additions

```text
/contract          show or edit current run contract
/preview           preflight cost-risk-runtime-policy preview
/receipt           show last run receipt
/evidence          show evidence for last answer or selected claim
/ledger            show compact intent ledger for current run
/autopsy           show failure autopsy for failed run
/policy simulate   simulate policy against planned run classes
/trust diff        preview trust or policy change impact
/graph select      select node and cross-highlight related events
/compare runs      compare two run receipts/summaries
```

Keep them behind slash autocomplete groups. Do not expose a new nested command maze.

## Terminal UX Details

- **Contract banner** should be dense: one line summary plus expandable details.
- **Receipts** should be copyable Markdown, not pretty-only TUI output.
- **Autopsy** must label `Evidence` and `ARC guess`; never present LLM speculation as diagnosis.
- **Graph commands** must be read-only until checkpoint/replay support exists.
- **Approvals** must be idempotent: action IDs prevent double approval from CLI/IDE.
- **Cost-risk preview** must say `unknown` when unknown; no fake precision.

## Rejections

| Idea | Why reject |
|---|---|
| A full terminal replay scrubber in v0.1 | Violates no default Trace UI and adds implementation risk. |
| Fancy ASCII graph animations | Cute but not differentiated unless commandable. |
| Auto-run everything in terminal | Unsafe, especially with shell/write actions. |
| A second huge command tree | Recreates the original CLI problem. |
| Raw JSON-first debugging | Useful advanced fallback, terrible default UX. |

## v0.1 Lock Criteria Additions

1. Every run writes a minimal receipt.
2. Every failed run writes a minimal autopsy.
3. Event schema reserves `run_contract`, `evidence_refs`, `decision_id`, `node_id`, `approval_id`, `policy_decision_id`.
4. CLI status line shows attached clients and pending approvals.
5. `/doctor` includes runtime manifest validation hooks, even if only SwarmGraph uses them.
