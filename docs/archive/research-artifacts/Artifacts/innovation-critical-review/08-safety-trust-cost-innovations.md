# Safety, Trust, and Cost Innovations

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

## Core Critique

The current plan has good safety basics: workspace trust gate, paid-call confirmation, keyring, redaction, Plan/Build/Auto, no self-updating binary, local-first daemon. Competitors can copy those. ARC needs safety UX that makes risk **visible, diffable, simulated, and receipted**.

## Trust Diff

Trust/policy/provider changes should show:

| Diff dimension | Example |
|---|---|
| Newly allowed | `shell_exec: deny -> ask` |
| Newly reachable | `tools: npm, git, pytest` |
| Provider impact | `Anthropic paid calls now allowed after approval` |
| File impact | `writes allowed under /src only` |
| Rollback availability | `git-backed file edits reversible; shell effects not reversible` |
| Audit impact | `all trust changes logged to audit chain` [needs internal verification] |

Trust changes should require explicit confirmation after diff review.

## Policy Simulator

Policy simulation must be honest:

- Simulates known planned action classes only.
- Shows `unknown future tool calls` separately.
- Does not claim exact costs.
- Shows what Auto would approve, ask, or deny.
- Links to policy source and precedence.

## Visual Run Contracts

Run contracts unify safety and cost:

```yaml
objective: string
runtime: swarmgraph
mode: build
allowed_tools: [read_file, propose_patch, run_tests]
blocked_tools: [shell_network, destructive_delete]
max_cost: unknown | 0.08
write_policy: propose_only | apply_after_approval | auto_apply
rollback_plan: git_revert | unavailable
trust_boundaries: [provider_call, workspace_write]
evidence_expected: [file_diff, test_output, run_summary]
```

Post-run status should mark `fulfilled`, `violated`, or `unknown`.

## Secure Delegation Tokens

This is likely too much for v0.1, but reserve IDs now. A future token should carry:

- Capability.
- Expiry.
- Cost ceiling.
- Workspace trust binding.
- Runtime/provider/tool scope.
- Audit link.

Do not ship fake tokens. If not enforced, call them `action_id`, not security.

## Cost-Risk Preview

Minimum useful v0.1 preview:

| Field | Allowed copy |
|---|---|
| Paid-call likelihood | `none`, `possible`, `likely`, `unknown` |
| Write likelihood | `none`, `propose only`, `may request apply`, `unknown` |
| Tool categories | `read files`, `run tests`, `provider call`, `shell` |
| Trust boundary | `workspace write`, `network`, `provider`, `shell` |
| Rollback | `git revert available`, `not available`, `unknown` |
| Runtime confidence | `manifest verified`, `partial`, `unknown` |

## Local-First Audit

Local-first is a product claim only if surfaced:

- Show storage path in `/status`.
- Show audit/receipt path after run.
- Redaction report in export.
- HMAC verification command if HMAC chain exists [needs internal verification].
- Never make users inspect raw JSON for trust.

## Risk Table

| Innovation | Security risk | UX risk | Cost risk | Mitigation |
|---|---|---|---|---|
| Run Contracts | Users may overtrust contract. | Too much friction. | Preview can be wrong. | Unknown labels, lightweight defaults. |
| Policy Simulator | Incomplete future action coverage. | Confusing if too abstract. | None. | Known/unknown split. |
| Trust Diff | Users click through. | Modal fatigue. | None. | Only for weakened policy/trust. |
| Delegation Tokens | Security theater if unenforced. | Invisible complexity. | Low. | Reserve IDs; enforce before branding. |
| Evidence Cards | Bad evidence can mislead. | UI noise. | Token/storage overhead. | Evidence type labels and collapse. |

## v0.1 Must Add

1. `run_contract` schema reservation.
2. `evidence_refs` schema reservation.
3. `policy_decision` event shape.
4. `trust_diff` data model for weakened settings.
5. Conservative cost-risk preview copy rules.
6. Post-run receipt artifact.
