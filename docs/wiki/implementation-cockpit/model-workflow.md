# Model Workflow

## Lead

ChatGPT 5.5 or Gemini 3.1 Pro Preview owns scope, ordering, and final integration.

Use the lead model for:
- choosing the next implementation slice
- writing exact worker prompts
- resolving architecture ambiguity
- checking that scope did not expand
- final pre-commit review

## Coding

Qwen 3.6 Max handles TypeScript, Theia, React, protocol glue, and frontend integration.

GLM 5.1 Precision handles Python backend, Pydantic/schema work, CLI commands, storage, and tests.

Use non-precision variants for first-pass implementation when the slice is simple. Use precision variants for schema, storage, policy, security, or test failures.

## Review

DeepSeek v4 Pro Precision reviews code diffs, test failures, refactor risk, backend correctness, and security-sensitive changes.

Kimi 2.6 Precision reviews UX, graph behavior, visual flows, Theia panel interactions, and HotLoop/visual-agent research.

Mimo v2.5 Pro handles long-context docs, repo summarization, source mapping, and wiki expansion.

Gemini 3.1 Pro Preview reviews architecture, long-context consistency, and final spec/plan coherence.

## Rules

- One implementation slice at a time.
- One model owns a file at a time.
- Every slice must include tests or a clear reason tests are not applicable.
- Every slice must state forbidden scope before coding starts.
- Preserve unrelated worktree changes.
- No default Trace UI.
- No HotLoop implementation in v0.1.
- No paid provider calls in CI.
- No self-updating CLI.
- No global memory without receipts.
- No broad refactors unless the slice explicitly requires them.

## Slice Loop

1. Lead selects the next unblocked slice from `15-implementation-slices.md`.
2. Lead restates exact scope, files, acceptance criteria, tests, and forbidden scope.
3. Worker model implements the slice.
4. Local tests/builds run.
5. Reviewer model checks the diff and test output.
6. Worker fixes review findings.
7. Lead performs final scope and integration check.
8. Commit the green slice with a focused message.

## Model Routing

| Work Type | Primary | Reviewer |
|---|---|---|
| Python schemas/models | GLM 5.1 Precision | DeepSeek v4 Pro Precision |
| Python CLI/backend | GLM 5.1 Precision | DeepSeek v4 Pro Precision |
| TypeScript protocol | Qwen 3.6 Max | DeepSeek v4 Pro Precision |
| Theia UI cards | Qwen 3.6 Max | Kimi 2.6 Precision |
| Graph/React Flow | Qwen 3.6 Max | Kimi 2.6 Precision |
| Docs/wiki | Mimo v2.5 Pro | Gemini 3.1 Pro Preview |
| Security/trust/policy | GLM 5.1 Precision | DeepSeek v4 Pro Precision + ChatGPT 5.5 |
| Final architecture | ChatGPT 5.5 | Gemini 3.1 Pro Preview |

## First 10 Slice Assignments

| # | Slice | Primary | Reviewer |
|---:|---|---|---|
| 1 | Contract schemas | GLM 5.1 Precision + Qwen 3.6 Max | DeepSeek v4 Pro Precision |
| 2 | RunContract backend | GLM 5.1 Precision | DeepSeek v4 Pro Precision |
| 3 | RunReceipt backend | GLM 5.1 Precision | DeepSeek v4 Pro Precision |
| 4 | Receipt CLI | GLM 5.1 Precision | DeepSeek v4 Pro Precision |
| 5 | FailureAutopsy backend | GLM 5.1 Precision | DeepSeek v4 Pro Precision |
| 6 | EvidenceRef schema/render | GLM 5.1 Precision + Qwen 3.6 Max | DeepSeek v4 Pro Precision |
| 7 | Runtime capability manifests | GLM 5.1 Precision | DeepSeek v4 Pro Precision |
| 8 | TrustDiff model | GLM 5.1 Precision | DeepSeek v4 Pro Precision |
| 9 | Theia RunContractCard | Qwen 3.6 Max | Kimi 2.6 Precision |
| 10 | Theia FailureAutopsy | Qwen 3.6 Max | Kimi 2.6 Precision |

## Worker Prompt Template

```text
You are implementing one ARC Studio slice.

Repo:
`/Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio`

Read first:
- `docs/wiki/implementation-cockpit/00-index.md`
- `docs/wiki/implementation-cockpit/15-implementation-slices.md`
- the slice-specific wiki page
- relevant source files listed in the slice

Slice:
<slice title>

Scope:
<exact allowed work>

Forbidden scope:
<what not to touch>

Acceptance criteria:
<checklist>

Tests:
<test files/commands>

Rules:
- Preserve unrelated worktree changes.
- Make the smallest correct change.
- Add/update tests.
- Do not implement future reserved features.
- Do not add default Trace UI.
- Do not make paid provider calls.

Return:
- files changed
- tests run
- remaining risks
```

## Reviewer Prompt Template

```text
Review this ARC Studio slice diff as a senior engineer.

Focus on:
- correctness bugs
- schema/backcompat risks
- security/redaction issues
- over-scoping beyond the slice
- missing tests
- hidden coupling with future reserved features

Do not rewrite the implementation unless explicitly asked.
Return findings ordered by severity with file/line references.
If no findings, say so and list residual risks.
```
