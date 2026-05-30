# GitHub Actions Workflow Audit

Date: 2026-05-25

Scope: `.github/workflows/*` on `build/no-mockups-handoff`.

## Research Notes

| Source | Link | What was learned | Implementation consequence | Confidence | Open questions |
| --- | --- | --- | --- | --- | --- |
| Context7: GitHub Actions workflow syntax | https://docs.github.com/en/actions/automating-your-workflow-with-github-actions/workflow-syntax-for-github-actions | Workflow-level `permissions` restrict `GITHUB_TOKEN`; unspecified granular scopes become `none`. | Added `permissions: contents: read` to read-only CI workflows. | High | None. |
| Context7: GitHub Actions concurrency | https://docs.github.com/en/actions/using-jobs/using-concurrency | Workflow-level concurrency can cancel superseded runs by workflow/ref. | Added concurrency to PR/push workflows to reduce stale CI load. | High | Whether release workflows should opt out if added later. |
| Context7: GitHub Actions security hardening | https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions | Least privilege for `GITHUB_TOKEN`; avoid unsafe untrusted context interpolation; pin actions to SHA for immutability. | Restricted permissions; documented SHA pinning as next policy decision rather than converting in one broad patch. | High | Repo policy for SHA pinning vs Dependabot tag updates. |
| GitHub Security Lab | https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/ | `pull_request_target` plus untrusted checkout/build is dangerous; checkout token persistence increases risk if write tokens are present. | Confirmed no `pull_request_target`; set `persist-credentials: false` because workflows do not push. | High | None. |
| GitHub docs web fetch | https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions | Third-party actions can access job tokens/secrets; full SHA pinning is strongest but has maintenance tradeoffs. | Kept trusted tag pins for now; recommend explicit follow-up if organization wants strict supply-chain policy. | High | Owner preference for strict pinning. |
| Google Search | https://github.com/Hansuqwer/arc-theia-studio/actions | Search tool returned 403 account verification, so live Actions-page inspection was unavailable. | Local workflow audit completed; remote run history not reviewed. | Medium | Current failing/passing run causes on GitHub UI. |
| Vercel Grep/code search | N/A | No Vercel Grep tool is exposed in this execution environment. | Documented gap; used Context7 and direct docs fetch instead. | Medium | External examples still worth sampling in a follow-up environment with Vercel Grep access. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
| --- | --- | --- | --- | --- | --- |
| Token permissions | Add `permissions: contents: read` to all workflows | Leave repo defaults; use `read-all` | These workflows only need checkout/read; granular least privilege is clearer. | `.github/workflows/*.yml` | High |
| Checkout credentials | Set `persist-credentials: false` | Keep default token persisted | No workflow pushes/tags/comments; less token exposure during build/test. | `.github/workflows/*.yml` | High |
| Stale run control | Add concurrency to PR/push workflows | No cancellation; job-level concurrency | Saves CI minutes and reduces stale signal. | PR/push workflows | High |
| Scheduled smoke concurrency | Do not add concurrency | Add same ref-based concurrency | Scheduled/manual smoke should not be unexpectedly canceled by a manual diagnostic run. | `real-runtime-smoke.yml` | Medium |
| Job timeouts | Add conservative job `timeout-minutes` | Step-level timeouts only; no timeouts | Prevents hung installs/tests while leaving enough time for current workload. | `.github/workflows/*.yml` | Medium |
| Action SHA pinning | Defer to policy follow-up | Convert all action refs to SHAs now | Stronger security but worse maintenance; needs owner policy/Dependabot config. | Docs only | Medium |
| Tool version drift | Update `setup-uv@v3` to `@v5`; pin pnpm setup to `9.15.9` where absent | Leave as-is | Aligns workflows with repo `packageManager` and other CI files. | `node.yml`, `perf.yml` | High |
| Native apt installs | Use `--no-install-recommends` | Leave default recommends | Smaller install surface; same named build deps. | Linux workflows | Medium |

## Findings Fixed

| Finding | Risk | Fix |
| --- | --- | --- |
| Missing explicit token permissions | Default token scope can be broader than needed. | Added `permissions: contents: read`. |
| Checkout persisted credentials | Build/test code can read checkout token from git config. | Added `persist-credentials: false`. |
| No job timeouts | Hung builds consume minutes indefinitely up to platform max. | Added conservative `timeout-minutes`. |
| No PR/push concurrency | Stale runs waste CI and obscure current status. | Added workflow concurrency where safe. |
| `setup-uv@v3` drift | Older setup action than rest of repo. | Updated to `astral-sh/setup-uv@v5`. |
| Inconsistent pnpm setup version | Relies on inferred package-manager behavior in some workflows. | Added explicit `version: 9.15.9`. |
| Apt recommends installed | Larger package surface than required. | Added `--no-install-recommends`. |

## Intentionally Not Fixed

| Item | Reason |
| --- | --- |
| Full SHA pinning for actions | Security-positive but broad operational policy change; tag pins are common with Dependabot. Decide as separate supply-chain PR. |
| Workflow deduplication | Node and roadmap gate overlap, but removing coverage can change branch protection semantics. Needs run-history/branch-rule review. |
| Live Actions-page failure audit | Search/fetch access to Actions page was blocked in this environment. |

## Remaining Risks

- Third-party actions remain tag-pinned, not immutable SHA-pinned.
- Workflow duplication still exists between `node.yml` and `arc-roadmap-gate.yml`.
- Remote Actions history was not reviewed due tool access limits.
