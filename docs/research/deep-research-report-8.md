# ARC Studio CI and Team Workflow Research

## Research framing

Public search results for “ARC Studio” were dominated by unrelated products, including an agency site and a screenwriting tool, so this report treats ARC as the local-first product described in your brief and builds a recommended CI/team design from the listed reference systems rather than from public ARC product documentation. That matters because the best benchmark for ARC is not another single product, but the combination of local-first software principles, PR-native AI review, hosted traces/evals, policy-as-code, and supply-chain attestation systems. Local-first software is explicitly about combining collaboration with user ownership, offline work, privacy, long-term preservation, and user control of data. citeturn17search0turn17search4turn21search0turn21search2

The strongest pattern across the reference set is that advisory AI and enforced governance should be separate layers. Continue’s checks run from repo-native markdown and surface pass/fail results on pull requests; Codex and Claude Code add contextual PR review and mention-driven workflows; GitHub provides the merge-control primitives through status checks, checks, comments, and rulesets; OPA provides enforceable policy decisions; and LangSmith, Braintrust, and Phoenix provide the trace/eval backplane. For ARC, that implies a simple architectural rule: **AI review should explain, while eval, policy, and provenance gates should decide**. Remote and team features can still fit a local-first product if they are optional, policy-bounded, and built as self-hosted or hybrid control planes rather than as mandatory sinks for raw local state. Continue explicitly frames safe cloud-agent operation around ownership, reviewability, least privilege, auditability, and constrained blast radius, while LangSmith, Braintrust, and Phoenix all expose hybrid or self-hosted deployment patterns that keep sensitive data under customer control. citeturn24search3turn3search1turn23search5turn10search2turn10search15turn1search2turn24search0turn22search0turn22search4turn22search5turn22search7

## CI/CD feature map

A clean ARC design is to organise `arc ci` around six layers: review, traces, evals, policy, signatures, and remote publication. Continue’s repo-native checks are the best precedent for local, versioned AI review; GitHub supplies the PR surfaces and reusable workflow mechanics; Codex and Claude show how mention-triggered review and repo guidance files improve usability; and LangSmith, Braintrust, and Phoenix show how traces, experiments, prompts, and datasets become a team workflow rather than just a local debugging aid. citeturn24search10turn24search3turn11search2turn11search3turn3search1turn3search7turn23search2turn6search0turn1search0turn13search10

| Proposed `arc ci` command | Purpose | Best public precedent |
|---|---|---|
| `arc ci review` | Run repo-native AI checks on the current diff or a PR, producing advisory findings and suggested fixes. | Continue checks in `.continue/checks/`; Codex PR review; Claude Code review citeturn24search10turn24search3turn3search1turn23search5 |
| `arc ci trace summarize` | Generate a PR-friendly summary of the run graph, major tool calls, timings, spend, and findings. | LangSmith traces/runs; Braintrust traces; Phoenix traces; GitHub PR comments/check summaries citeturn6search0turn8search6turn14search14turn10search10turn11search0 |
| `arc ci eval run` | Execute a versioned eval pack against the branch and record a comparable experiment result. | Braintrust experiments; LangSmith evaluation; Phoenix experiments citeturn1search0turn20search5turn18search1turn13search10 |
| `arc ci gate` | Compare the current run against a baseline and fail if thresholds regress. | Braintrust baseline comparison; LangSmith compare experiments; Phoenix baseline comparisons citeturn20search1turn20search3turn20search2turn20search6 |
| `arc ci policy check` | Evaluate trust rules over a canonical run manifest. | OPA/Rego and OPA in CI/CD citeturn1search2turn1search8turn1search11 |
| `arc ci sandbox validate` | Check requested filesystem, tool, and network permissions against policy before execution. | Codex sandbox and approvals; Claude Code sandboxing/auto mode citeturn12search0turn12search4turn16search1turn4search7turn4search10 |
| `arc ci spend check` | Enforce provider allowlists, model allowlists, and spend ceilings. | LangSmith cost tracking; Braintrust cost observability and org providers; Phoenix cost tracking/provider secrets citeturn14search0turn15search2turn14search2turn15search9 |
| `arc ci receipt sign` | Emit a canonical signed run receipt for a gated run. | SLSA provenance; in-toto; Sigstore/cosign; GitHub artifact attestations citeturn2search0turn2search12turn19search1turn19search2turn25search1 |
| `arc ci audit verify` | Verify signed receipts, audit bundles, and attached provenance offline or online. | Sigstore bundle verification; GitHub offline attestation verification; cosign verify-attestation citeturn2search6turn2search17turn19search2turn25search7 |
| `arc ci upload` | Upload only approved reports, receipts, and metadata to remote stores or team indexes. | GitHub workflow artifacts; linked artifacts metadata records/API citeturn26search5turn26search8turn26search0turn26search7 |

This surface keeps the same commands usable on a laptop, inside GitHub Actions, or in a self-hosted team runner. That is the right shape for ARC: local-first by default, but team-capable through shared policies, prompts, evals, and metadata when a workspace explicitly enables them. Continue’s cloud-agent guidance, LangSmith hybrid, Braintrust hybrid, and Phoenix self-hosting all point in that direction. citeturn24search1turn24search5turn22search1turn22search4turn22search0turn22search3turn22search5

## GitHub Action design

ARC should ship a **two-tier GitHub integration**. The first tier should be a reusable GitHub Actions workflow, because GitHub already supports reusable workflows through `workflow_call`, least-privilege `GITHUB_TOKEN` authentication, OIDC federation to cloud providers, and rulesets/required checks that block merges until jobs pass. That is enough for most teams to adopt ARC quickly. The second tier should be an optional ARC GitHub App for richer UX, because GitHub’s Checks API only allows write access from GitHub Apps; that is the path to custom check runs, line annotations, and “requested action” buttons such as re-run, accept fix, or promote pack. citeturn11search3turn10search11turn10search8turn10search15turn10search0turn10search7turn10search10turn11search14

A practical default workflow looks like this:

```yaml
name: ARC PR Guardrails

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  issue_comment:
    types: [created]

permissions:
  contents: read
  pull-requests: write
  id-token: write
  attestations: write
  artifact-metadata: write

jobs:
  arc:
    if: github.event_name == 'pull_request' || contains(github.event.comment.body, '/arc')
    uses: arc-studio/arc/.github/workflows/reusable-pr-guardrails.yml@v1
    with:
      baseline_ref: origin/main
      eval_pack: default
      trust_mode: team
    secrets: inherit
```

Inside the reusable workflow, ARC should follow one linear path: check out code, run `arc ci review`, generate `arc ci trace summarize`, execute `arc ci eval run`, enforce `arc ci gate`, run `arc ci policy check`, emit `arc ci receipt sign`, verify any imported bundles with `arc ci audit verify`, and finally upload only policy-approved outputs. If the workflow also publishes GitHub artifact attestations, GitHub’s current guidance is to grant `attestations: write`, `contents: read`, and `id-token: write`, with `packages: write` for OCI image publication; if storage records are pushed to the linked artifacts page in the same workflow, `artifact-metadata: write` is also required. citeturn25search8turn25search0

Trigger design should mirror what works elsewhere. Codex supports `@codex review` and repository-specific review guidance from `AGENTS.md`; Claude Code GitHub Actions supports `@claude` mentions on PRs and issues, while Claude Code review posts inline comments without itself approving or blocking the PR. ARC should copy that ergonomics but keep merge control separate: `@arc review` and `/arc rerun-eval` should be advisory or assistive flows, while `arc-eval`, `arc-policy`, and `arc-attest` remain the blocking required checks. citeturn3search1turn3search7turn23search2turn23search5turn10search2turn10search15

The PR trace summary should be terse enough for reviewers and rich enough for auditors. A good summary comment or check output should include changed files, models/providers used, token and cost totals, stage timings, top findings, eval deltas versus the chosen baseline, policy decisions, receipt digests, and links or digests for uploaded bundles. LangSmith’s project/trace/run model, Braintrust’s trace viewer, and Phoenix’s trace structure all support that level of execution detail, while GitHub check output natively supports titles, summaries, text, and annotations. citeturn6search0turn14search9turn8search13turn14search14turn10search10

## Policy-as-code design

OPA/Rego is the strongest fit for ARC’s policy layer. OPA is a general-purpose policy engine explicitly designed for policy-as-code, Rego is built to evaluate structured inputs, OPA already has a documented CI/CD operating model, and OPA Control Plane adds Git-based bundle management and promotion across environments. ARC should therefore use **one OPA policy bundle everywhere**: locally before a run, in CI before merge, and in any team control plane before accepting uploaded artifacts or pack promotions. citeturn1search2turn1search8turn1search11turn1search17turn16search15turn16search19

The input to policy should be a canonical ARC run manifest. At minimum it should include repository and commit identity, actor identity, trust mode (`private` or `team`), requested provider and model, estimated and actual spend, sandbox write paths, allowed network hosts, secrets referenced, upload destinations, prompt/eval pack digests, and output receipt or bundle digests. That single document lets ARC answer all the meaningful gate questions in one place: is this provider allowed for this repository; may this run use a public SaaS endpoint or only a self-hosted/team gateway; may it call a custom base URL; may it upload full traces or only summaries; and must a signed receipt be present before merge. LangSmith, Braintrust, and Phoenix already expose the building blocks for spend, provider secrets, workspace secrets, and provider-level configuration, and Phoenix explicitly warns that unrestricted custom base URLs can turn evaluation/playground systems into unintended access paths to internal services. citeturn14search0turn15search2turn15search4turn15search9turn15search16turn15search1

Sandbox policy validation should be a first-class policy decision, not a post-hoc warning. Codex describes the sandbox as the autonomy boundary and notes that automatic review does not change that boundary; Claude Code similarly depends on filesystem and network isolation to let the agent work with fewer approval prompts while staying safer than blanket permission skipping. ARC should therefore reject runs that ask for directories, tools, or network hosts outside the allowlist defined by the team trust policy. Because cosign can verify in-toto attestations and validate them against Rego policies, ARC can also use the same policy language after the run to verify signed outputs and imported bundles. citeturn16search1turn12search4turn4search7turn4search10turn19search2

A representative Rego shape would look like this:

```rego
package arc.trust

default allow = false

deny[msg] {
  input.mode == "private"
  count(input.upload.targets) > 0
  msg := "private mode may not upload remote artifacts"
}

deny[msg] {
  not input.provider.name in data.allowed_providers[input.repo]
  msg := sprintf("provider %s is not approved for %s", [input.provider.name, input.repo])
}

deny[msg] {
  input.spend.actual_usd > data.budgets[input.repo].max_usd
  msg := "run exceeded spend budget"
}

deny[msg] {
  some host
  host := input.sandbox.network_hosts[_]
  not host in data.allowed_hosts[input.repo]
  msg := sprintf("network host %s is not allowed", [host])
}

deny[msg] {
  input.merge_gate == true
  not input.receipt.verified
  msg := "merge-gating run must include a verified signed receipt"
}

allow {
  count(deny) == 0
}
```

## Team collaboration model

ARC should treat team collaboration as an **explicit workspace mode**, not as an invisible sync layer. In **Private Mode**, prompts, traces, local memory, receipts, and caches stay on the device unless the user exports them. In **Team Mode**, ARC connects to a workspace that stores shared policies, prompt libraries, eval datasets, provider configuration, and signed run metadata, while the actual data plane can still be self-hosted or hybrid. That is already the shape used by Braintrust hybrid deployments, LangSmith hybrid/self-hosted deployments, and Phoenix self-hosting, including fully air-gapped Phoenix setups. citeturn22search0turn22search3turn22search4turn22search7turn22search5turn22search2turn22search16

The workspace trust policy should govern membership, promotion rights, and secret use. LangSmith exposes organisation/workspace hierarchy, workspace roles, workspace secrets, SAML/SCIM-oriented user management, and application-level structure; Braintrust supports organisation-level AI provider keys, service tokens intended for CI/CD and automation, and project-specific access restrictions; Phoenix supports encrypted provider secrets, admin provisioning, and management APIs. For ARC, that means: personal provider keys remain a local convenience, but shared automation should require workspace-held credentials, a team gateway, or federated credentials. It also means workspace policy should determine who may publish packs, who may promote prompts or baselines, who may upload artifacts, and which repositories or projects may see which traces. citeturn15search0turn15search8turn15search12turn15search4turn15search2turn8search15turn15search14turn15search9turn22search8turn22search11

Shared content should be packaged and promoted, not ambient. Continue’s Hub rules are designed to be shared across teams; LangSmith prompts support owners, staging and production environments, commit tags, and update webhooks; Braintrust lets teams version and deploy prompts, manage environment tags, and snapshot datasets; Phoenix versions both prompts and datasets, recording authors and change history. ARC should use that model for **shared prompt libraries**, **shared eval datasets**, and **shared memory/eval packs**. A pack should be a signed bundle of prompts, repo rules, evaluators, scorer thresholds, reference traces, and small curated memory snippets extracted from traces or annotation flows. Installation should be pull-based and policy-checked, so no teammate wakes up to silently changed agent behaviour. Continue’s cloud-agent taxonomy is especially useful here: production agents need a shared place to review runs, a record of decisions, adjustable prompts and rules, and gradual automation rather than an immediate jump to fully autonomous execution. citeturn9search10turn7search0turn18search10turn8search0turn8search8turn8search12turn8search1turn8search9turn13search2turn13search8turn13search9turn24search1

The team control plane should also stay **metadata-first**. Continue Mission Control is a good model for this because it acts as a team control plane for tasks, agents, integrations, and workflow review rather than as a mandate that every developer abandon local tooling. ARC should follow the same principle: the workspace tracks shared state, trust decisions, and approved artifacts, but the local client remains authoritative for raw working context unless policy says otherwise. citeturn24search6turn24search9turn24search0turn21search0turn21search2

## Artifact and signature model

ARC should produce two signed outputs for merge-gating or release-relevant runs: a **signed run receipt** and a **signed audit bundle**. The standards pieces already exist. SLSA defines supply-chain levels and provenance predicates; GitHub artifact attestations use Sigstore and store a Sigstore bundle; a Sigstore bundle contains the material needed to verify a signature; the in-toto Attestation Framework is the standard way to express signed software-supply-chain claims; and cosign supports signing and verifying in-toto attestations. That combination is a better foundation for ARC than inventing a bespoke signature story. citeturn2search0turn2search4turn2search8turn2search12turn25search1turn25search3turn2search6turn19search1turn19search2turn19search10

For ARC, the run receipt should be a compact, canonical statement whose subject is the digest of the PR summary, patch set, eval report, or uploaded artifact associated with a single run. Its predicate should include the repository SHA, actor identity, trust mode, policy bundle digest, prompt pack digest, eval pack digest, sandbox configuration hash, provider/model identifiers, spend totals, timestamps, and the digests of any trace or report files. The audit bundle should then package that receipt together with policy results, eval reports, trace summaries, and verification material such as the Sigstore bundle. Verification should work both online and offline, mirroring GitHub’s documented offline verification path for attestations. Because cosign supports in-toto attestation verification and Rego-based policy validation, ARC can make bundle verification both cryptographic and policy-aware. citeturn2search17turn25search7turn19search2turn2search10

Remote artifact upload should follow GitHub’s **linked artifacts** pattern rather than a naive “sync every file” pattern. GitHub’s linked artifacts page is explicitly metadata-only: it provides an authoritative index of build, storage, deployment, provenance, and compliance information without storing the artifact files themselves. Records can be provided by workflow attestations, integrations, or the artifact metadata REST API. That is an excellent precedent for ARC’s remote artifact upload: upload metadata, provenance, and approved summaries to a team index, while leaving the true binary, trace archive, or pack file in the registry or object store your organisation already trusts. citeturn26search0turn26search1turn26search3turn26search7turn26search9

A further nuance from GitHub’s attestation guidance is worth copying: not every scratch build needs the same provenance overhead as release-worthy outputs. GitHub explicitly recommends signing software you are releasing, not every frequent automated test build. ARC should therefore sign all merge-gating runs and release candidates by default, while keeping ad-hoc local scratch runs unsigned unless policy opts in. That gives teams strong auditability where it matters without turning every quick experiment into supply-chain ceremony. citeturn25search1

## Eval gate roadmap

ARC’s eval roadmap should start with reproducible offline gates and only later expand into richer online learning loops. Braintrust already treats experiments as immutable, comparable records that fit naturally into CI/CD and baseline comparison; LangSmith separates offline evaluation on curated datasets from online evaluation on production traces and lets automations add traces to datasets, annotation queues, webhooks, and evaluations; Phoenix provides versioned datasets and experiment comparison to isolate improvements or regressions introduced by prompt, model, or dataset changes. Together, those systems suggest a clear ARC sequence. citeturn1search0turn20search5turn20search1turn18search4turn18search0turn18search3turn13search8turn13search10turn20search6

The first ARC milestone should be **smoke evals on pull requests** with a fixed baseline and hard fail thresholds. The second should be **slice-aware regression gates** that compare averages and deltas across important dataset segments instead of trusting a single noisy run; Braintrust’s own best-practices guidance warns that one experiment run can mask a real regression or improvement, and recommends larger datasets or more trials plus average-based comparison when differences are small. The third milestone should be **trace-to-dataset mining**, where production or CI traces that show low quality, errors, or policy edge-cases are promoted into new dataset examples. The fourth should be **online evaluators** for live quality monitoring, with sampled feedback feeding back into datasets. The final milestone should be **signed benchmark packs** that become release-promotion requirements alongside signed run receipts and provenance verification. Throughout that roadmap, AI review comments remain explanatory; only deterministic scorer thresholds, policy decisions, and verified receipts should block merge. citeturn20search0turn20search1turn20search15turn18search4turn18search8turn18search18turn18search0turn20search2turn23search5turn10search15

## Top CI and team features

The table below ranks the highest-value ARC features for CI and team workflows. Complexity and priority are estimated for ARC rather than copied from any source product.

| Feature | Source | CI/team user story | Security concern | Complexity | Priority |
|---|---|---|---|---|---|
| Repo-native AI checks | Continue checks and repo-local rule files; Codex repo guidance files citeturn24search10turn24search3turn9search10turn3search7 | As a maintainer, I want team review rules versioned with code so local runs and PR checks behave the same way. | Weak prompts or changed-file prompt injection can produce noisy or gamed review results. | Medium | P0 |
| Reusable ARC GitHub Action | Continue PR review bot; Claude Code GitHub Actions; GitHub reusable workflows and OIDC citeturn9search1turn23search2turn23search0turn11search3turn10search8 | As a repo owner, I want one standard workflow I can roll out across many repositories with minimal YAML drift. | Over-broad workflow permissions or secret exposure in CI. | Medium | P0 |
| PR trace summaries | LangSmith traces; Braintrust trace viewer; Phoenix traces; GitHub check output/comments citeturn6search0turn8search6turn14search14turn10search10turn11search0 | As a reviewer, I want one concise PR summary explaining what ARC ran, found, and spent. | Accidental leakage of prompts, secrets, or sensitive trace content into comments. | Medium | P0 |
| Eval regression gates | Braintrust CI experiments and baselines; LangSmith experiment comparison; Phoenix experiment comparison citeturn1search0turn20search1turn20search3turn20search2turn20search6 | As a release owner, I want merges blocked when quality regresses against a known baseline. | Flaky datasets, nondeterminism, or poorly chosen thresholds can create false blocks. | High | P0 |
| Policy checks | OPA/Rego; OPA in CI/CD; OPA Control Plane citeturn1search2turn1search11turn16search15 | As a platform team, I want one policy engine evaluating trust rules locally and in CI. | Policy bypass, drift between environments, or unreviewed bundle changes. | Medium | P0 |
| Sandbox policy validation | Codex sandbox and approvals; Claude Code sandboxing and auto mode citeturn12search0turn16search1turn4search7turn4search10 | As a security reviewer, I want ARC to reject runs that ask for broader file, tool, or network access than policy allows. | Data exfiltration, malware download, or host escape via over-broad permissions. | High | P0 |
| Team provider policies and spend checks | Braintrust org-level providers/service tokens; LangSmith cost tracking/workspace secrets; Phoenix provider secrets/cost tracking citeturn15search2turn14search0turn15search4turn14search2turn15search9 | As an admin, I want approved providers, approved models, and budget ceilings enforced across the team. | Budget blowouts, data residency issues, and unauthorised model endpoint usage. | Medium | P0 |
| Audit bundle verification | GitHub artifact attestations; Sigstore bundle format; GitHub offline verification; cosign verify-attestation citeturn25search1turn2search6turn2search17turn19search2 | As an auditor, I want to verify ARC evidence offline before trusting a run or release. | Trust-root confusion, forged bundles, or skipped verification steps. | High | P0 |
| Team workspace trust policy | Continue Mission Control/taxonomy; LangSmith hierarchy and roles; Braintrust project restrictions citeturn24search1turn24search6turn15search0turn15search12turn8search15 | As an organisation, I want workspace-level rules for who can publish packs, use providers, or upload artifacts. | Insider misuse or over-exposed cross-project visibility. | High | P0 |
| Signed run receipts | SLSA provenance; in-toto attestation framework; Sigstore/cosign; GitHub attestations citeturn2search0turn2search12turn19search1turn19search2turn25search7 | As a maintainer, I want every merge-gating ARC run to leave a tamper-evident receipt. | Signature key compromise or incomplete predicates that prove too little. | High | P1 |
| Shared prompt libraries | LangSmith prompt management; Braintrust prompt deployment; Phoenix prompt versioning/tags citeturn7search0turn7search5turn8search0turn8search12turn13search2turn13search9 | As a team, I want prompts versioned, promotable, and reusable across repos and workflows. | Unreviewed prompt promotions or hidden behavioural changes. | Medium | P1 |
| Shared eval datasets | LangSmith versioned datasets; Braintrust datasets and snapshots; Phoenix versioned datasets citeturn7search4turn7search1turn8search1turn8search9turn13search8turn13search16 | As an eval owner, I want approved golden datasets shared across local and CI runs. | PII in datasets, stale labels, or test-data poisoning. | Medium | P1 |
| Shared memory/eval packs | Continue Hub rules; LangSmith prompt/GitHub sync; Braintrust immutable experiment snapshots; Phoenix prompt comparison/versioning citeturn9search10turn18search10turn20search5turn13search6turn13search2 | As a staff engineer, I want installable signed bundles of prompts, rules, datasets, scorers, and memory snippets. | Malicious pack contents or incompatible pack updates changing agent behaviour. | High | P1 |
| Remote artifact upload | GitHub workflow artifacts; linked artifacts metadata API; linked artifacts page citeturn26search5turn26search8turn26search7turn26search0 | As a compliance team, I want approved receipts, reports, and metadata uploaded without forcing full source sync. | Uploading raw code or sensitive traces instead of minimal metadata. | Medium | P1 |
| Private and team modes | Local-first software principles; Braintrust hybrid; LangSmith hybrid/self-hosted; Phoenix self-hosted air-gapped citeturn21search0turn21search2turn22search0turn22search4turn22search5turn22search7 | As a developer, I want ARC to stay fully private by default, but become shareable and governable when I opt into team mode. | Silent mode escalation, surprise syncing, or hidden remote retention. | High | P0 |

Taken together, these features let ARC stay local-first in the way Ink & Switch defines it—preserving user control and offline ownership—while still adding the collaboration, auditability, and governance patterns that the current AI engineering stack has converged on for production use. citeturn21search0turn21search2turn24search1turn25search1