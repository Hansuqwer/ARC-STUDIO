# ARC IDE/CLI Keys and CrewAI + SwarmGraph Roadmap

Generated: 2026-05-16

Status: planning baseline plus current-reality audit. This document is not a product claim.

## Research Notes

Context7 sources used:

- `/eclipse-theia/theia`: Theia extensions wire frontend/backend modules through `theiaExtensions` plus Inversify `ContainerModule`; preferences use `PreferenceContribution`/`PreferenceService`; user/workspace settings are preferences, not secure secret storage.
- `/crewaiinc/crewai`: CrewAI projects commonly run via `crew().kickoff(inputs=...)`; provider credentials are standard env vars such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, and tool-specific keys such as `SERPER_API_KEY`.
- `/fastapi/typer`: Typer supports command groups, options, prompts, hidden input, and `envvar` binding for CLI UX.
- `/pydantic/pydantic`: Pydantic `BaseModel` validates config payloads and is suitable for env-ref-only provider metadata.
- `/pnpm/pnpm`: Workspace commands use recursive scripts and filters such as `pnpm -r run build` and `pnpm --filter <pkg> build`.
- `/jestjs/jest`: `coverageThreshold` supports global and file-pattern thresholds; static UI contract tests remain viable for Theia-dependent React source.

Web search status: blocked in this environment by Antigravity authentication (`opencode auth login` required). Existing repository research in `docs/research/feature-roadmap-review/09-provider-keys-cost.md` was used for provider key/security context.

## Current Reality

### Key Management

| Surface | Current capability | Evidence | Gap | Risk | Minimal fix |
|---|---|---|---|---|---|
| CLI provider status | Shows env-var key presence only. | `python/src/agent_runtime_cockpit/providers.py:302` | Does not include account metadata in status. | Users cannot see configured env-ref accounts in the primary status command. | Add `arc providers key status` that combines env presence + `ProviderAccountStore`. |
| CLI provider account add | Can add env-var-backed account metadata; raw key is never printed. | `python/src/agent_runtime_cockpit/cli.py:901`, `providers.py:95` | Command is `arc providers accounts add --api-key-env`, not target flow `arc providers key set`. | Discoverability gap. | Add alias group `arc providers key set/status/unset`. |
| CLI direct key storage | Explicitly blocked; direct storage raises. | `python/src/agent_runtime_cockpit/providers.py:117` | No provider-key keychain implementation. | Spec/UX can overpromise keychain. | Keep env-ref baseline; add keychain later after platform spike. |
| CLI profiles | Built-ins plus external custom profiles can be listed/shown/created. | `security/profiles.py`, `cli.py` | Provider key-ref validation for paid profile creation is still metadata-only. | Users may confuse profile metadata with key storage. | Keep env-ref/keychain distinction explicit in UI/docs. |
| CLI paid-call gating | `arc run` resolves profiles strictly before adapter execution. | `cli.py`, `security/profiles.py` | Runtime-specific paid gates still live in adapters too. | Duplicate gates can produce different wording. | Keep preflight as the user-facing aggregation layer. |
| IDE key status | Config tab displays provider configured/source status; never raw values. | `ConfigTab.tsx:240`, `arc-protocol.ts:351`, `arc-backend-service.ts:407` | Display only; no IDE key-ref add/update UI. | User must leave IDE to configure keys. | Add non-secret env-ref editor calling backend method that shells to CLI/account store. |
| IDE config save | Saves only safe fields. | `arc-backend-service.ts:478` | No provider-account write path. | No real key setup from IDE. | Extend protocol with `saveProviderKeyRef(provider, envVar)`; reject plaintext. |
| Workspace config | Provider config stores account IDs/list only, not raw keys. | `config/model.py:31` | No explicit env-ref validation in `ArcConfig`. | Low, since account store is external. | Validate env var names when adding accounts. |
| Audit HMAC key | Separate audit key manager uses keychain/env fallback. | `audit/key_manager.py` | Separate from provider keys; no provider-key reuse. | Confusion if UI labels are vague. | Roadmap and UI must call it "audit key", not provider key. |

Verdict:

- Key setup CLI: PARTIAL. Env-ref account metadata exists; target `providers key` UX and profile creation are missing.
- Key setup IDE: PARTIAL. Safe status UI exists; no key-ref creation/update flow.

### CrewAI + SwarmGraph

| Surface | Current capability | Evidence | Gap | Risk | Minimal fix |
|---|---|---|---|---|---|
| Runtime ID syntax | `crewai+swarmgraph` is known, parsed, and routed to fake/offline mode. | `runtime_router.py`, `adoption/registry.py` | Real provider-backed mode remains gated. | Fake/offline may be overclaimed. | Label metadata as `runtime_mode: fake/offline`, `real_provider_call: false`. |
| Capability listing | `crewai+swarmgraph` reports fake/offline runnable; other adoption modes still fail closed. | `runtime_router.py` | IDE still does not consume adoption mode capabilities. | UI may lag CLI. | Add IDE selector/preflight next. |
| CrewAI standalone | Runnable when `crewai` is installed, `ARC_CREWAI_EXPORT` set, and paid calls allowed. | `adapters/crewai.py:36`, `adapters/crewai.py:119` | No CLI dry-run preflight command showing all blockers together. | Users discover blockers one at a time. | Add `arc run --dry-run` or `arc runtimes doctor crewai`. |
| CrewAI adoption runner | Runner can call `akickoff`/`kickoff_async`/`kickoff` and map output to proposals. | `adoption/crewai_runner.py:38` | Runner is not integrated into a `RuntimeAdapter`; consensus delegates to AG2 helper, not real SG queen/vote UX. | Overclaim risk if called SwarmGraph orchestration. | Wrap runner behind fail-closed adapter only after fake/offline tests. |
| Paid-call gating | Standalone CrewAI blocks without `allow_paid_calls`. | `adapters/crewai.py:126` | Adoption runner itself does not enforce paid/profile gates. | If wired directly later, paid calls could bypass gates. | Gate before creating `AdoptionSpec`. |
| CLI run | `arc run --runtime crewai` exists; `crewai+swarmgraph` supports dry-run and fake/offline execution. | `cli.py`, `runtime_router.py` | No real CrewAI provider-backed adoption path. | Overclaim risk. | Keep real mode behind `ARC_REAL_RUNTIME_SMOKE=1`. |
| IDE selection | Config and Chat tabs list `crewai+swarmgraph` as fake/offline. | `ConfigTab.tsx`, `ChatTab.tsx` | Capability-driven disabled states remain minimal/static. | UI may not show every CLI blocker until preflight runs. | Drive selector directly from `listRuntimeCapabilities()` later. |
| IDE run | Modern Chat tab can preflight and start fake/offline runs via backend service, link completed runs to Runs tab, and replay stored trace events. | `ChatTab.tsx`, `RunsTab.tsx`, `arc-backend-service.ts` | Run UX is still replay/status oriented; no live progress stream. | Users may expect live event delivery. | Label replay honestly; live stream remains future work. |
| Traces/audit refs | Fake/offline `crewai+swarmgraph` writes trace events and explicit audit absence reason. | `runtime_router.py` | No SwarmGraph HMAC audit record for fake/offline mode. | Cannot claim signed adoption audit. | Add real audit integration only when real adoption runtime lands. |

Verdict:

- CrewAI + SwarmGraph CLI: PARTIAL/RUNNABLE OFFLINE. Syntax, dry-run, and fake/offline run path exist; real provider-backed adoption remains gated/not claimed.
- CrewAI + SwarmGraph IDE: PARTIAL. Adoption mode is visible, preflight is wired, fake/offline run launch exists, run result links to Runs, and Runs tab exposes stored replay plus audit/HITL controls. Live progress stream remains incomplete.

## Target User Flow

CLI target:

```bash
arc providers key set openai --env OPENAI_API_KEY
arc profiles create local-paid --allow-paid-calls --provider openai
arc adapter detect crewai --json
arc run ./crew.py --runtime crewai+swarmgraph --profile local-paid --dry-run
arc run ./crew.py --runtime crewai+swarmgraph --profile local-paid
arc runs status <run_id>
arc runs replay <run_id>
arc audit verify <audit_path>
```

IDE target:

- Open Config tab.
- Add provider key reference, not plaintext.
- Select profile.
- See CrewAI readiness.
- Select `CrewAI + SwarmGraph`.
- Dry-run explains cost/key/deps/export target.
- Run starts.
- Event stream displays live/replay events.
- Runs tab shows receipt/audit/replay.

## Security Rules

- No plaintext provider secrets in workspace files.
- Prefer env var refs as v0.1 baseline; add OS keychain only after platform behavior is tested.
- Provider keys are distinct from audit HMAC keys.
- Paid-call profiles must be explicit.
- Bug reports redact secrets.
- Untrusted workspace blocks execution or requires trust.
- IDE never logs key material.
- Provider key UI stores env var names only until secure storage exists.

## Implementation Plan

Provider catalog prerequisite: ARC now keeps a broad provider metadata catalog and env-ref-only key UX as the baseline. Web-auth providers remain research-only unless official OAuth/API flows are verified.

### P0 — Truth Patch

- Patch review findings around `arc-arena`, `arc-product`, and test-count wording.
- Update docs to distinguish key refs vs real key storage.

Acceptance: docs/build/tests pass; no package claims archived code is removed when it still exists.

### P1 — CLI Key UX

- Done: add `arc providers catalog`.
- Done: add `arc providers key status`.
- Done: add `arc providers key set <provider> --env VAR` as an alias over env-backed provider accounts.
- Done: add `arc providers key unset <provider>` or `unset <account-id>`.
- Done: store only env var refs in `~/.arc/providers.json`.
- Done: validate env var names with explicit regex and reject raw key-looking values.
- Done: add tests proving raw key values are never persisted.
- Remaining: provider-key keychain storage remains future work.

### P2 — Profile UX

- Done: add/verify `arc profiles create`.
- Done: allow explicit paid-call profile creation.
- Validate provider key refs before enabling a paid profile.
- Done: add tests for no plaintext secret persistence.

### P3 — CrewAI + SwarmGraph CLI Dry Run

- Done: add `arc run ... --runtime crewai+swarmgraph --dry-run`.
- Done: show dependency/export/key/profile blockers in one response.
- Done: make no provider calls.
- Done: add tests for missing `ARC_CREWAI_EXPORT` and success preflight with fake env; CrewAI package absence is reported as dependency metadata, not a fake/offline blocker.

### P4 — CrewAI + SwarmGraph Fake Run

- Done: add offline fake CrewAI adoption path.
- Done: use `AdoptionSpec` with fake crew object.
- Done: emit trace events and explicit audit absence metadata.
- Keep real runtime gated behind `ARC_REAL_RUNTIME_SMOKE=1`.

### P5 — IDE Key/Profile UI

- Done: add ConfigTab provider dropdown and env-var key-ref editor.
- Add profile selector.
- Done: save only env var refs through backend service.
- Done: add UI contract tests for provider dropdown, env var input, save button, and web-auth warning.

### P6 — IDE CrewAI + SwarmGraph Run UX

- Done: runtime selector shows `CrewAI + SwarmGraph`.
- Done: add dry-run from UI.
- Done: add minimal fake/offline run launch from modern ChatTab.
- Done: capability-driven disabled state with reasons before dry-run.
- Done: add UI/protocol contract tests.

### P7 — Real Runtime Smoke

- Done: add `ARC_REAL_RUNTIME_SMOKE=1` CrewAI smoke test.
- Keep default CI offline.
- Never require live provider key in PR CI.

## Acceptance Criteria

- CLI can configure provider key refs safely.
- IDE can configure provider key refs safely.
- CLI can dry-run CrewAI + SwarmGraph with exact blockers.
- CLI can fake-run CrewAI + SwarmGraph offline.
- IDE can select and explain CrewAI + SwarmGraph.
- No plaintext secrets are committed or written to workspace config.
- Tests pass.
- Release docs avoid broad adoption claims.

## Risks

- CrewAI API drift around `kickoff`, `akickoff`, and `kickoff_async`.
- Provider costs if paid gates fail.
- Theia preferences are not secret storage.
- OS keychain behavior varies across macOS/Linux/headless SSH.
- Audit HMAC key vs provider key confusion.
- Fake-tested adoption can be overclaimed as real SwarmGraph orchestration.
