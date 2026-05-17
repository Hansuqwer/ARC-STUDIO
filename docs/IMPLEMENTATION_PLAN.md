# ARC Studio Implementation Plan

Generated: 2026-05-14

Source of truth: `docs/REALITY_AUDIT.md`, `docs/CLI_IDE_GAP_ANALYSIS.md`, current `README.md`, current code. `packages/arc-extension` is canonical. Legacy `theia-extensions/*` sources have been archived under `docs/archive/theia-extensions/` after useful release-scope UI was ported into `packages/arc-extension`.

## Executive Summary

ARC Studio currently has a real Python CLI/daemon, standalone runtime adapters, a canonical Theia extension under `packages/arc-extension`, and a vendored SwarmGraph runtime. It does not yet have the core product differentiator: shared SwarmGraph orchestration wrapping external runtimes with queen/worker decomposition, voting, consensus, HITL, deterministic orchestration, and signed audit records.

The practical path is:

1. Make repository truth coherent and runnable.
2. Stabilize standalone adapters and capability reporting.
3. Wire canonical `packages/arc-extension` into the browser app before further UI work.
4. Add execution-core infrastructure before adoption: versioned events, JSONL+SQLite index, live broker/supervisor, workspace trust, and subprocess isolation.
5. Introduce a small SwarmGraph adoption interface before adding integrations.
6. Implement `LangGraph + SwarmGraph` first because LangGraph is closest to SwarmGraph internals.
7. Add AG2, CrewAI, OpenAI Agents, and LlamaIndex adoption after the interface proves out.
8. Productize Theia around runtime selection, standalone/adoption mode, live runs, audit, replay, HITL, and cost controls.
9. Harden release packaging after the browser app + Python CLI/wheel release path is stable.

## Current Baseline

| Area | Current state | Main gap |
|---|---|---|
| Theia extension | `packages/arc-extension` is canonical, tested, and wired into `applications/browser`/`applications/electron` app deps | Legacy `theia-extensions/*` source is archived for rollback/history |
| Python CLI/daemon | Real CLI, aiohttp daemon, REST endpoints, JSONL trace store | SSE is replay-only; no live run stream |
| SwarmGraph runtime | Vendored, real queen/worker/consensus/HITL/HMAC audit/gateway/quota | ARC mostly calls it as CLI subprocess, not as shared adoption layer |
| SwarmGraph adoption | Not implemented | No external runtime is wrapped by SwarmGraph |
| Runtime adapters | SwarmGraph, LangGraph, CrewAI, OpenAI Agents, LlamaIndex, LM Arena; AG2 code unregistered | Mixed maturity; static exports; OpenAI hardcoded test agent; AG2 invisible; LM Arena is stub-default with gated live path that is not v0.1 scope |
| Audit/replay | JSONL traces and ARC SHA-256 hash chain | No exposed SwarmGraph HMAC audit chain or replay UI |
| Security | Loopback-only, optional bearer token, paid-call gates, partial env filtering | Auth off by default; subprocess model needs hardening |
| Tests | Unit/contract/web/storage/security tests | No real-runtime E2E proving product flows |

## Target Architecture

```text
Theia UI (packages/arc-extension)
  -> ARC frontend/backend service
  -> Python daemon / CLI
  -> Runtime router
      -> Standalone adapters
          -> SwarmGraph CLI/local
          -> LangGraph export
          -> CrewAI export
          -> OpenAI Agents export
          -> AG2 export
          -> LlamaIndex export
      -> SwarmGraph adoption adapters
          -> LangGraph + SwarmGraph
          -> CrewAI + SwarmGraph
          -> OpenAI Agents + SwarmGraph
          -> AG2 + SwarmGraph
          -> LlamaIndex + SwarmGraph
  -> Trace store + audit store + SSE live stream
```

### Core Concepts

| Concept | Definition |
|---|---|
| Standalone adapter | Runs a runtime directly through its native API or CLI. |
| SwarmGraph adoption adapter | Wraps another runtime as SwarmGraph worker execution inside queen/worker/consensus/HITL/audit orchestration. |
| Isolation provider | Backend-enforced execution boundary for untrusted runtime code. Theia configures and displays status; it does not enforce isolation. |
| Prompt optimizer | Optional prompt refinement layer that structures vague/natural-language prompts before execution. It must preserve intent, expose diffs, and record original + optimized prompts. |
| Provider gateway | Provider routing/quota/cost controls. Not enough to claim SwarmGraph adoption. |
| Combo execution | Sequential multi-adapter run. Not SwarmGraph adoption. |
| Audit record | Signed SwarmGraph audit entry, not just ARC trace event. |
| Trace event | ARC UI/event-stream record; may be derived from runtime/audit events. |

## CLI/IDE Product Surface Addendum

This addendum folds in `docs/CLI_IDE_GAP_ANALYSIS.md`. It is a target surface, not a claim about current implementation.

### CLI Surface To Add

| Phase | Commands | Purpose |
|---|---|---|
| P0 truth/discoverability | `arc version`, `arc health`, `arc status`, `arc doctor all`, `arc env check`, `arc adapter info`, `arc adapter detect` | Basic introspection, daemon health, adapter discoverability, env validation. |
| P0 daemon parity | `arc providers diagnostics`, `arc providers proxy`, `arc providers accounts enable`, `arc runs diff` | Expose functionality already present in daemon/helpers. |
| P1 run lifecycle/live stream | `arc runs status`, `arc runs cancel`, `arc runs delete`, `arc runs stream`, `arc runs tail --follow`, `arc runs export` | Make runs manageable from CLI; add live/replay stream UX. |
| P2 audit/replay/HITL | `arc runs import`, `arc runs replay`, `arc hitl pending`, `arc hitl approve`, `arc hitl reject`, `arc hitl respond`, `arc audit log`, `arc audit verify`, `arc audit export` | High-assurance workflow lifecycle: replay, approval, verifiable audit. |
| P3 adapter/product config | `arc providers quota`, `arc providers quota reset`, `arc profiles list`, `arc profiles show`, `arc profiles create`, `arc workspace init`, `arc workspace info`, `arc workspace config` | Profiles, quotas, workspace setup, and product-grade configuration. |
| P4 eval/observability | `arc eval save`, `arc eval delete`, `arc eval run --batch`, `arc eval report`, `arc runs search`, `arc doctor env`, `arc doctor network`, `arc doctor storage`, `arc bug-report` | Evaluation, trace search, diagnostics, support bundle. |
| P5 plugin/deploy/arena | `arc arena models`, `arc arena tags`, `arc arena chat`, `arc arena vote`, `arc arena adopt` | Arena remains stub/offline until real provider calls exist; later plugin/deploy commands need separate architecture. |

### IDE Surface To Add

| Phase | Views/panels | Source / backend need |
|---|---|---|
| P0 canonical shell | ARC dashboard, runtime readiness, runs panel, run launcher, status bar indicators, command palette contributions | Release-scope UI has been ported into `packages/arc-extension`; legacy sources are archived. |
| P1 run visualization | workflows graph, live event stream, trace timeline, schema inspector, run diff viewer, health monitor | Port from `arc-workflows`, `arc-event-stream`, `arc-runs`, `arc-schemas`, `arc-health`; requires live SSE architecture for true live mode. |
| P2 high-assurance UX | audit chain viewer, HITL approval inbox, replay stepper | Needs daemon endpoints for audit/HITL/replay; do not present as complete before backend exists. |
| P3 product setup | provider manager, profile selector, adapter setup wizard, workspace trust UI, context pack view, arena view | Port/adapt from `arc-adapters`, `arc-context`, `arc-arena`; arena remains stub/offline until backend changes. |
| P4 SwarmGraph insight | consensus/voting dashboard, queen/worker topology view, eval/golden trace manager, cost/token dashboard | Unique ARC/SwarmGraph differentiators; depends on adoption and audit event contracts. |

### Market Patterns To Copy

| Source | Pattern | ARC placement |
|---|---|---|
| LangGraph Studio | Graph/chat modes, time travel, checkpoint replay, inline prompt iteration | P1 graph/chat mode; P2 replay; P4 prompt/versioning only after prompt infra exists. |
| CrewAI | Interactive provider setup, chat mode, replay from task, train/test commands | P3 adapter setup wizard; P4 eval/train/test after runtime parity. |
| Temporal | Start-dev pattern, workflow reset, signal/query/cancel, saved views | P1 run cancel/status; P2 resume/replay/HITL; P4 saved filters. |
| Prefect/Dagster | Timeline/Gantt, logs, run detail, lineage graph where useful | P1 trace timeline/logs; P4 topology/lineage views. |
| LangSmith/Langfuse/Phoenix/MLflow | Trace tree, datasets/evals, prompt/version tracking, cost/token tracking, span replay, OTLP | P1 trace tree; P4 eval/cost/search/OTLP; prompt/versioning deferred. |

### Execution Isolation Policy

Approved architecture: isolation is a backend runtime execution provider, not a standalone Theia extension. Theia exposes setup, status, warnings, and configuration; the Python daemon/backend enforces isolation.

| Provider | Role | Phase |
|---|---|---|
| `none` / inspect-only | Disable execution for untrusted workspaces; allow detection/inspection only. | P0 |
| `subprocess` | Current fast trusted-local baseline with env/path restrictions. | P0 |
| `docker` | Cross-platform Docker-compatible container isolation. | P2 |
| `orbstack` | macOS Docker-compatible runtime auto-detected through Docker CLI; not a hard dependency. | P2 |
| `podman` / `colima` | Docker-compatible alternatives. | P3 |
| `firecracker` | Linux/KVM microVM provider for high-assurance deployments. Stretch/future; not required for P4. | P5+ |
| remote sandbox | Future remote isolation provider. | P5+ |

Required CLI surface: `arc isolation status`, `arc isolation doctor`, `arc isolation list`, `arc isolation set <provider>`, `arc isolation setup docker`, `arc isolation setup firecracker`, `arc isolation test --runtime <id>`, `arc isolation profiles list`, `arc isolation profiles create <name> --provider <provider>`.

Required IDE surface: execution isolation settings inside `packages/arc-extension`, detected runtime status (`Docker CLI`, `OrbStack`, `Podman`, `Firecracker/KVM`), workspace trust state, and per-runtime default isolation profile.

### Prompt Optimizer Policy

Approved architecture: add an optional ARC-native prompt optimizer/refiner. It should be local/template-based first, not an online optimizer by default. Provider-backed or SwarmGraph-consensus optimization may be added later behind explicit privacy, paid-call, and audit gates.

| Mode | Role | Default |
|---|---|---|
| `off` | Send prompt unchanged. | Allowed everywhere. |
| `local` | Rule/template cleanup: objective, requirements, constraints, verification, expected output. No provider calls. | Default for normal runs after preview support exists. |
| `local-model` | Local model rewrite through an installed local runtime. | Optional later. |
| `provider` | Paid/provider model rewrites prompt. | Off by default; requires explicit paid/privacy gate. |
| `swarmgraph` | Multiple optimizer candidates + SwarmGraph consensus over final prompt. | Future high-assurance mode. |

Required CLI surface: `arc prompt optimize`, `arc prompt optimize --file <path>`, `arc prompt optimize --mode off|local|local-model|provider|swarmgraph`, `arc prompt diff <original> <optimized>`, `arc run <workflow> --optimize-prompt`, `arc run <workflow> --no-optimize-prompt`.

Required IDE surface: prompt optimizer toggle near run input, mode selector, token estimate, preview, before/after diff, “use optimized” / “use original” actions, and warnings when provider-backed optimization would send prompt content outside the workstation.

Safety rules: never silently rewrite high-assurance prompts; preserve original prompt in trace metadata; store optimizer mode and warnings in audit metadata; redact secret-like values before provider-backed optimization; flag ambiguity instead of inventing requirements.

### Future Mobile Agent Framework Integration

Related external draft: `/Users/hansvilund/HansuQWER/WorkSpace/ARC/MobileFrameWork/mobileframework/mobile-agent-framework/MOBILE_AGENT_FRAMEWORK_IMPLEMENTATION_ROADMAP.md`.

This is a future ARC-adjacent initiative, not current ARC Studio capability. The existing mobile framework roadmap targets an AI-native mobile agent framework for Expo, React Native, Flutter, SwiftUI, Jetpack Compose, KMP, and Capacitor, with MCP tools, app state graph, UI semantic mirror, offline memory, mobile permission manifests, app-store compliance checks, Maestro replay, and mobile observability.

Before integrating with ARC Studio, it should be rewritten around SwarmGraph concepts:

| Mobile concept | SwarmGraph-oriented rewrite |
|---|---|
| App State Graph | Pydantic state model feeding SwarmGraph worker context. |
| UI Semantic Mirror | Auditable evidence source, not direct agent authority. |
| Mobile agent planner | SwarmGraph queen decomposition over mobile tasks. |
| Mobile tools/MCP | Worker tools gated by permission manifest, tenant, and cost/profile policy. |
| Permission Manifest | HITL and policy gate input for risky mobile actions. |
| Maestro replay | Deterministic replay/eval backend for mobile worker actions. |
| App-store compliance | Audit/eval checks attached to release workflow. |
| Offline memory | Tenant-scoped memory with explicit replay/audit semantics. |

Recommended positioning: add later as `Mobile + SwarmGraph` adoption track after core desktop/server runtimes are stable. It should not block P0-P4 ARC Studio work.

## Phase Plan

## Foundation ADR Review Gate

The ADR set in `docs/adr/` is accepted as a planning baseline, not as product claims. Edit ADRs before implementation if tests or platform spikes disprove assumptions.

| ADR | Plan action | Phase | Guardrails |
|---|---|---|---|
| `000-execution-core-contract` | Use as the execution-core integration contract | P0-P1 | Keep public `RunStatus` compatible; transient supervisor phases stay in metadata until protocol migration is explicit. |
| `001-config-model` | Add config schema/loader and `arc config init/show` | P0-P1 | Secrets remain env/keychain references only; existing env vars continue to override. |
| `002-run-lifecycle-state-machine` | Add `JobSupervisor`, targeted cancel, orphan recovery, live-event broker | P1 | Do not add new public statuses without TS/Python protocol migration. |
| `003-storage-strategy` | Wire SQLite as index beside canonical JSONL traces | P1 | JSONL stays source of truth; index failures must not corrupt traces. |
| `004-event-schema-versioning` | Add `schema_version` and event registry | P1 | Event naming must align with current ARC/AG-UI mapping before code changes. |
| `005-audit-key-management` | Add audit service, verify/export CLI/endpoints, key-management spike | P2-P4 | Keychain is preferred but dependency/platform behavior must be validated; env fallback must show degraded status. |
| `006-workspace-trust-isolation` | Add trust resolver and isolation provider interface | P1-P3 | Default is untrusted unless explicit approval; home-directory path is not trust evidence. |
| `007-provider-routing-unification` | Treat ARC providers as metadata/policy; gateway owns execution | P1-P3 | Do not remove existing provider commands until gateway integration is tested. |
| `008-daemon-bundling` | Add packaging spike before Electron bundling | P5 | No PyInstaller/embedded-Python decision until measured on target platforms. |

### Research Dossier Execution Guardrails

The scaffolds in `docs/research/IMPLEMENTATION_RESEARCH.md` are reference designs, not paste-ready implementation. Each PR must adapt them to current repo APIs, existing file names, declared dependencies, tests, lint rules, and storage semantics before merge.

- The executable browser app target is `applications/browser` on Theia `1.71.0`; `packages/arc-extension` currently declares `^1.45.0`. Canonical wiring must include Theia version alignment or a build/smoke proof of compatibility.
- No scaffold may import undeclared dependencies. Before EventBroker/SSE implementation, choose manual `aiohttp.web.StreamResponse` or add `aiohttp-sse` explicitly to `python/pyproject.toml` and CI.
- Trust approval must not rely solely on workspace-local files such as `.arc/trusted`; repo contents can self-authorize that marker. Store trust outside the workspace or bind it cryptographically/user-profile-side.
- `keyring` remains a spike/optional dependency until PR #17 decides platform behavior. HMAC verify must support explicit env fallback with degraded status.
- Provider gateway and runtime adapters must stay fake/offline by default unless paid-call/privacy gates are explicit and tested.

## P0: Truth, Coherence, Runnability

Goal: remove contradictions, stabilize visible product behavior, and make every public claim falsifiable.

| Item | Outcome | Files/modules | Dependencies | Implementation notes | Verification tests | Risks/unknowns |
|---|---|---|---|---|---|---|
| Confirm canonical extension wiring | `packages/arc-extension` is documented, included in browser/electron app deps, and smoke-loadable | `README.md`, `applications/browser/package.json`, `applications/electron/package.json`, `packages/arc-extension/` | User decision done | Completed: canonical app deps use `arc-extension`; legacy duplicates archived for rollback/history | `pnpm --filter arc-extension build`; `pnpm --filter @arc-studio/browser build`; browser/e2e smoke | Keep archived legacy sources honest as rollback/history only |
| Inventory secondary Theia extensions | Decide port/archive/delete per extension | `docs/archive/theia-extensions/*` | Canonical extension decision | Completed for release scope: useful UI-only widgets ported; legacy source archived | Static docs review; browser/e2e smoke | Future salvage should happen from archive into canonical extension only |
| Register or explicitly hide AG2 | AG2 is either visible and tested or removed from claims | `python/src/agent_runtime_cockpit/adapters/registry.py`, `runtime_router.py`, `README.md` | Existing AG2 runner | Prefer register behind honest capability report if detect/run path works | `uv run pytest python/tests/adapters/ag2` plus CLI capabilities test | AG2 deps/API drift |
| Fix OpenAI Agents export target | No hardcoded internal TestAgent in product run path | `adapters/openai_agents.py`, `adapters/openai_agents/` | Env var design | Add `ARC_OPENAI_AGENTS_EXPORT=module:attr`, validate target inside workspace | Fake SDK/workspace test; CLI run test | SDK API volatility |
| Document LM Arena honestly | No stub/live-mode fiction; Arena excluded from v0.1 scope | `arena/service.py`, `adapters/lmarena.py`, docs | None | State stub-default behavior and gated live path; do not productize Arena CLI/UI until backend/tests are release-ready | Grep/docs truth check; arena tests | Arena may distract from core ARC/SwarmGraph flows |
| Normalize capability reports | UI can trust adapter status | `adapters/base.py`, each adapter, `protocol/capabilities.py` | Runtime inventory | Add fields: `support_level`, `execution_modes`, `adoption_modes` | Unit tests per adapter | Schema versioning |
| Update docs index | Docs match current architecture | `README.md`, `docs/RUNTIMES.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md` | Audit complete | Separate standalone vs adoption in all docs | Manual grep for banned claims | Historical docs may intentionally contradict |
| Add CLI truth/discoverability commands | Users can inspect ARC itself before running agents | `cli.py`, `web/routes.py`, docs | Existing daemon health + capability reports | Add `arc version`, `arc health`, `arc status`, `arc doctor all`, `arc env check`, `arc adapter info`, `arc adapter detect` | CLI tests for JSON envelopes and error cases | Command naming churn |
| Add CLI daemon-parity commands | CLI exposes helper/daemon functionality already present | `cli.py`, `providers.py`, `evals/diff.py`, `web/routes.py` | Existing helper functions/routes | Add `arc runs diff`, `arc providers diagnostics`, `arc providers proxy`, `arc providers accounts enable` | CLI tests against temp traces/env | Keep provider proxy dry-run by default |
| Add canonical shell migration spec | Shell porting is scoped and sequenced before code moves | `docs/EXTENSION_MIGRATION.md`, `packages/arc-extension`, `docs/archive/theia-extensions/*` | Canonical app wiring | Completed: release-scope port/archive sequence documented; archived sources retained for rollback/history | Docs review; browser app still builds | Future product work must target canonical extension |
| Document current isolation honestly | Users understand current subprocess trust boundary | `README.md`, security docs, `docs/IMPLEMENTATION_PLAN.md` | Current subprocess model | Mark subprocess as trusted-local only; inspect-only for untrusted workspaces | Docs review | Users may expect stronger isolation than exists |

### P0 Definition Of Done

- README and roadmap do not claim implemented adoption.
- `packages/arc-extension` is documented as canonical.
- Legacy `theia-extensions/*` has a migration inventory and is archived for rollback/history.
- No new product work lands in archived `theia-extensions/*`; future salvage must target `packages/arc-extension`.
- `arc runtimes --capabilities --json` reports honest support levels.
- AG2 status is no longer ambiguous.
- OpenAI Agents no longer runs only a hardcoded test agent in product path.
- `arc version`, `arc health`, `arc status`, and `arc doctor all` exist.
- CLI exposes existing diff/provider diagnostic/provider proxy functionality.
- Canonical extension is wired into the app and has a documented migration spec for shell/service/readiness/run UX.
- Current isolation posture is documented as subprocess/trusted-local, not container or microVM isolation.
- `applications/browser` includes `arc-extension` directly; duplicate `theia-extensions/*` sources are archived.
- `docs/RELEASE_CHECKLIST.md` exists and targets v0.1.0-alpha.
- v0.1 scope is explicit: browser app + Python CLI/wheel; Electron packaging is post-v0.1.

### Theia Extension Migration Policy

| Extension | Default action | Rationale |
|---|---|---|
| `arc-event-stream` | Port | Event stream UX belongs in canonical product. |
| `arc-runs` | Port | Run timeline/diff/chat launcher are product UX. |
| `arc-workflows` | Port | Workflow graph visualization is core cockpit UX. |
| `arc-schemas` | Port | Schema inspector is useful for runtime inspection. |
| `arc-adapters` | Port | Runtime readiness and doctor actions are product-critical. |
| `arc-health` | Port small pieces | Daemon/backend status is useful but simple. |
| `arc-context` | Port if context UX remains in scope | Thin wrapper over existing service. |
| `arc-settings` | Port prefs only | Low-risk preference contribution. |
| `arc-audit` | Archive or rewrite | Current implementation is stub/static; keep concept, not code. |
| `arc-arena` | Archive | LM Arena is out of v0.1 scope; keep stub-default/gated-live behavior out of the canonical shell until tested and intentionally productized. |
| `arc-product` | Archive/delete | Branding shell likely duplicates canonical extension. |
| `arc-core` | Archive/delete after salvage | Duplicate canonical extension architecture. |

Rule: UI-only, useful, product-relevant code may be ported. Backend/protocol duplicates should be deleted after any required behavior is represented in `packages/arc-extension` and Python daemon APIs. Stub/demo/static packages should be archived, not presented as product.

## P1a: Execution Core Infrastructure

Goal: build the backend/runtime infrastructure that adoption, live UI, audit, and trust depend on. Do this before implementing runtime-specific adoption modes.

| Item | Outcome | Files/modules | Dependencies | Implementation notes | Verification tests | Risks/unknowns |
|---|---|---|---|---|---|---|
| Add adoption capability fields | CLI/UI can show standalone vs adoption separately | `protocol/capabilities.py`, TS protocol types | P0 schema cleanup | Add schema version plus `support_level`, `execution_modes`, `adoption_modes`, `audit_level`, `hitl_level`; default to non-adoption | Python + TS contract tests | Backward compatibility for UI |
| Add event schema registry | Run/adoption/live events have versioned, validated contracts | `protocol/schemas.py`, `orchestration/events.py`, TS protocol | ADR-004 | Add `schema_version`, registry, validation helper; HITL event names may be reserved as additive values but implementation waits for persistence | Event serialization/validation tests | Event naming drift between ARC and AG-UI |
| Activate JSONL + SQLite index | Runs are searchable/status-queryable without scanning all trace files | `storage/jsonl.py`, `storage/sqlite.py`, `web/routes.py`, `cli.py` | ADR-003 | Keep JSONL source of truth; use SQLite as rebuildable index; write JSONL first, index second; add idempotent backfill/rebuild command | Store migration/backfill tests; crash/rebuild test; list/search tests | Dual-write consistency and SQLite corruption recovery |
| Replace combo semantics | Sequential combo no longer confused with adoption | `runtime_router.py` | Capability schema | Keep combo as explicit `sequence` mode; do not call it adoption | Router tests | Existing users may rely on combo |
| Add ARC trace/audit refs | Trace records can point to audit material without claiming HMAC signing yet | `audit/`, `tracing/`, `protocol/schemas.py` | Storage/index changes | Add top-level `audit_path` or typed metadata ref; distinguish ARC SHA-256 chain from SwarmGraph HMAC audit | Trace/audit unit test | HMAC wiring happens in P2 |
| Add live run supervisor and event broker | Runs can be backgrounded, cancelled, streamed, and recovered | `web/routes.py`, new supervisor module, `orchestration/events.py`, adapters | Event registry; storage index | Implement `JobSupervisor`, active SSE broker, replay fallback, orphan recovery; keep public `RunStatus` compatible | Streaming fake-run test; reconnect test; cancel/orphan tests | Race conditions/reconnect semantics |
| Split run lifecycle CLI | Safe run commands land before live-dependent commands | `cli.py`, `web/routes.py`, `storage/` | Supervisor/event broker for live commands | Add `arc runs status/delete/export` first; add `cancel/stream/tail --follow` after supervisor is in place | CLI + daemon tests | Cancellation support varies by adapter |
| Add workspace trust resolver | Execution can distinguish trusted vs untrusted workspaces before stronger sandboxes exist | new trust/security modules, `cli.py`, protocol | ADR-006 | P1a is advisory: default untrusted status is reported and warned, but existing trusted-local runs are not blocked until P2 enforcement | Trust resolver/CLI tests | UX friction |
| Add isolation provider interface | Execution boundary becomes pluggable and honestly reported | `python/src/agent_runtime_cockpit/isolation/`, CLI, protocol | Trust resolver | Implement provider protocol and `none`/`subprocess`; add `arc isolation status/doctor/list/set`; no Docker/Firecracker claims yet | Unit tests + CLI tests | Must not imply Docker/Firecracker are implemented; second-provider readiness will be reviewed before Docker |
| Harden subprocess env allowlists | Adapter subprocesses leak fewer secrets before container isolation exists | adapter subprocess code, `security/redaction.py`, profiles | Isolation interface | Enforce profile/adapter env allowlists consistently across adapters; add per-adapter cancellation/support capability fields | Env leakage/security tests; cancellation matrix contract test | User workflows may need env passthrough; cancellation semantics vary by adapter |

### P1a Definition Of Done

- Capability API distinguishes standalone and planned `+ SwarmGraph` modes.
- Event schema registry/versioning exists before live stream/adoption event work.
- JSONL remains canonical while SQLite indexes runs for listing/status/search.
- Sequential combo is explicitly `sequence`, not adoption.
- Run records can reference audit material without overclaiming signed audit.
- Job supervisor and event broker support fake live runs, cancellation, replay fallback, and orphan recovery.
- Workspace trust defaults to untrusted in reported state; P1a is advisory/warn-only until P2 enforcement flips execution behavior.
- Isolation provider interface exists with `none` and `subprocess`; CLI reports status honestly.
- Subprocess env allowlists are enforced consistently enough to reduce secret leakage.

## P1b: Adoption Foundation And Local Helpers

Goal: add the smallest reusable adoption interface and low-risk helper UX after the execution core can carry it.

| Item | Outcome | Files/modules | Dependencies | Implementation notes | Verification tests | Risks/unknowns |
|---|---|---|---|---|---|---|
| Define adoption protocol | Shared interface for all `runtime + SwarmGraph` modes | New `python/src/agent_runtime_cockpit/adoption/` | P1a capability/event schema | Model inputs/outputs as Pydantic: `AdoptionSpec`, `WorkerTask`, `Vote`, `ConsensusResult`, `AuditRef`; reserve `HitlRequest` until P2 persistence | Protocol unit tests | Interface may mirror SwarmGraph too closely or too loosely |
| Define adoption runtime ID syntax | CLI/API/UI can refer to adoption modes consistently | adoption protocol, router, docs | Adoption protocol | Use `<runtime>+swarmgraph` syntax, e.g. `langgraph+swarmgraph`; standalone IDs remain unchanged | Router/protocol tests | Syntax bikeshed |
| Add adoption runner skeleton | Runtime router can resolve adoption modes honestly | `orchestration/runtime_router.py`, new adoption registry | Adoption protocol | Return not-runnable with doctor actions until each runtime is implemented | Router tests | Mode discoverability before runtime support |
| SwarmGraph import path spike | Determine whether ARC can import vendored SwarmGraph as a library for adoption | `runtimes/swarmgraph/`, adapter packaging | Adoption skeleton | Prefer library API for adoption where feasible; keep CLI fallback for standalone | Import/smoke test | Vendored package path complexity |
| Port run visualization shell pieces | Canonical extension can inspect workflows/runs/traces at basic level | `packages/arc-extension`, archived `docs/archive/theia-extensions/*` for provenance | P0 shell basics; P1a live broker for true live stream | Release-scope widgets ported in priority order; legacy stubs archived | UI contract tests; browser smoke | Future protocol work should stay canonical |
| Add local prompt optimizer foundation | Vague prompts can be structured without provider calls | `python/src/agent_runtime_cockpit/prompt_optimizer/`, `cli.py`, protocol | Run input model; event/trace metadata fields for `prompt_original`, `prompt_optimized`, `optimizer_mode` | Add `arc prompt optimize`, `arc prompt optimize --file`, `arc prompt diff`; local mode only; preserve original/optimized prompt metadata | Unit tests with vague/broken-English prompts; no network tests | Must not change user intent |

### P1b Definition Of Done

- Code has a formal adoption interface and canonical `<runtime>+swarmgraph` syntax.
- Router can represent adoption modes honestly, even if most are not runnable.
- SwarmGraph library import feasibility is proven or rejected with a documented fallback.
- Canonical extension has basic run/workflow/trace visualization ported without claiming unsupported backend features.
- Local prompt optimizer exists as previewable helper; no provider calls are made by default.

## P2: Runtime + SwarmGraph Integrations

Goal: implement adoption mode incrementally, starting with the runtime closest to SwarmGraph.

Approved adoption priority:

1. LangGraph + SwarmGraph
2. AG2 + SwarmGraph
3. CrewAI + SwarmGraph
4. OpenAI Agents + SwarmGraph
5. LlamaIndex + SwarmGraph
6. Semantic Kernel + SwarmGraph (deferred until after core P2 adoption proves out)
7. Haystack + SwarmGraph (deferred until after core P2 adoption proves out)
8. DSPy/PydanticAI selective typed-worker adapters (future typed-worker track)

| Item | Outcome | Files/modules | Dependencies | Implementation notes | Verification tests | Risks/unknowns |
|---|---|---|---|---|---|---|
| LangGraph + SwarmGraph | LangGraph node/graph execution wrapped as SG worker tasks | `adoption/langgraph.py`, `adapters/langgraph.py` | P1 | Convert LangGraph export into worker callable; SG queen assigns deliberation tasks; consensus signs result | Fake LangGraph graph adoption test; real minimal LangGraph smoke | State schema mismatch |
| AG2 + SwarmGraph | AG2 group chat produces proposals/votes under SG orchestration | `adoption/ag2.py`, `adapters/ag2/` | P0 AG2 registry | `a_run_group_chat`/`run_stream` events map to workers | Fake AG2 team adoption test | AG2 package naming/API drift |
| CrewAI + SwarmGraph | CrewAI crew/task runs inside SG worker role | `adoption/crewai.py`, `adapters/crewai.py` | P1, CrewAI export | Treat crew output as worker proposal/vote; preserve paid-call gating | Fake CrewAI export adoption test | CrewAI side effects/cancellation |
| OpenAI Agents + SwarmGraph | Agents SDK run produces SG worker proposal and audit trail | `adoption/openai_agents.py`, `adapters/openai_agents.py` | P0 OpenAI export | Hooks map lifecycle to ARC trace; final output becomes vote/action | Fake SDK test; no live provider | SDK hooks change |
| LlamaIndex + SwarmGraph | LlamaIndex workflows can participate as workers | `adoption/llamaindex.py`, `adapters/llamaindex.py` | LlamaIndex run path | First implement standalone run; then adoption wrapper | Fake LI workflow test | Broad LI API surface |
| Semantic Kernel + SwarmGraph | Deferred enterprise plugin/workflow candidate | `adoption/semantic_kernel.py`, new adapter if added | Core P2 adoption proven | Do not implement in P2 unless core integrations finish early and owner approves | Future fake SK workflow test | Zero current code; SDK surface/version drift |
| Haystack + SwarmGraph | Deferred RAG/pipeline candidate | `adoption/haystack.py`, new adapter if added | Core P2 adoption proven | Do not implement in P2 unless LlamaIndex path proves retrieval/evidence UX | Future fake Haystack pipeline test | Zero current code; may be pipeline-only |
| DSPy/PydanticAI typed workers | Future typed-worker candidate | `adoption/dspy.py`, `adoption/pydantic_ai.py` | Core adoption + typed-worker design | Selective support only; not full multi-agent orchestration | Future typed fake worker tests | Zero current code; lower product priority |
| SwarmGraph native adoption runner | ARC can run SG locally without only CLI subprocess where feasible | `adapters/swarmgraph/`, `runtimes/swarmgraph/` integration | Packaging/import path | Prefer library API when available; keep CLI fallback | Local SG smoke test | Vendored package import complexity |
| Wire SwarmGraph HMAC audit verify path | ARC can verify signed SwarmGraph audit records without claiming key-management UX is finished | `audit/`, `adapters/swarmgraph/`, vendored `swarm_shared.audit`, `web/routes.py`, `cli.py` | P1a audit refs; SwarmGraph import path | Add audit service, `arc audit verify/export`, verify endpoint; prefer keychain but allow explicit env fallback with degraded status | Tamper test; audit verify API/CLI test | Keyring/platform behavior needs spike |
| Add safer daemon auth default | Daemon has an explicit local auth story before high-assurance UX | `web/server.py`, Theia backend auth headers, CLI | Current optional token | Generate or require a local token for Theia-launched daemon; keep `/health` safe; add `arc auth status/rotate` if needed | Auth tests; Theia header injection test | Breaking local scripts |
| Enforce workspace trust before execution | Untrusted workspaces cannot silently run arbitrary code | CLI/daemon/UI protocol | P1a trust resolver; isolation provider interface | Add trust CLI and enforcement in run/profile resolution; flip from P1a advisory mode to explicit approval/blocking mode | Trust CLI/API tests | UX friction; migration from warn-only behavior |
| Complete eval CLI basics | Existing eval foundation becomes usable from CLI | `cli.py`, `evals/`, `storage/` | Existing golden trace evals | Add `arc eval save/delete`, `arc eval run --batch`, `arc eval report` where storage supports it | CLI tests | Reporting format churn |
| Add trace replay + HITL persistence/CLI contracts | High-assurance workflows are inspectable and resumable at the trace/API level | `cli.py`, `audit/`, `storage/`, `web/routes.py` | P1a event broker; P2 audit verify path | Add trace replay first; add minimal pending-approval persistence before HITL CLI/UI; pending approvals are single-user/workspace-local | HITL persistence/token tests; HITL fake-run test; trace replay test | HITL resume semantics and token expiry |
| Add high-assurance IDE views | User can handle approvals and verify audit chain | `packages/arc-extension` | Audit/HITL endpoints | Add audit chain viewer, HITL approval inbox, replay stepper | UI + API tests | Do not show signed audit unless HMAC wired |

### P2 Definition Of Done

- At least `LangGraph + SwarmGraph` is runnable end-to-end in tests.
- Each adoption mode reports honest runnable/not-runnable status.
- Paid-call gating applies before any external runtime invocation.
- Adoption runs produce ARC traces plus SwarmGraph audit refs.
- No docs imply all adoption modes are complete unless tests prove it.
- Runtime adoption implementation follows the approved priority order unless a dependency blocks progress; Semantic Kernel, Haystack, and DSPy/PydanticAI remain deferred unless explicitly approved.
- A vendored SwarmGraph audit verify/export path exists and is honest about SHA-256 ARC traces vs the vendored SwarmGraph HMAC-signed audit implementation.
- Daemon auth and workspace trust are explicit and tested before high-assurance UI is presented.
- Eval CLI basics are complete enough to support later reports/search UX.
- Trace replay exists; HITL CLI/UI are implemented only with minimal pending approval persistence and single-use token tests.
- Canonical extension has audit viewer, HITL inbox, and replay stepper backed by real endpoints.

## P3: Theia UX Productization

Goal: make Theia feel like the product, not status cards over CLI output.

| Item | Outcome | Files/modules | Dependencies | Implementation notes | Verification tests | Risks/unknowns |
|---|---|---|---|---|---|---|
| Runtime selection UI | User selects runtime and mode | `packages/arc-extension/src/browser/arc-widget.tsx`, components | P1 capabilities | Show standalone/adoption separately; disable unsupported modes with reasons | Static component contract tests | React/Theia test limits |
| Adapter config UI | User can configure export targets/env-backed settings | `arc-extension` components, backend service, Python daemon config endpoints | P0 capability schema | Do not store secrets directly; env var references only | Unit + UI contract tests | Secure local config storage |
| Run launch UX | Start runs with prompt/input/profile/cost gate | `WorkflowExecutionSection`, backend service | Runtime selection UI | Include dry-run preview of selected adapter/cost gate | E2E browser test | Async state complexity |
| Live event stream | Running jobs emit live SSE events in the IDE | Python daemon SSE, `TraceViewerSection` or new component | P1a active event broker + replay fallback | Wire UI to the P1a broker; do not reimplement backend streaming in the UI phase | Web integration test with streaming fake run | Concurrency/reconnect |
| Audit viewer | User can inspect/verify audit chain | New component in `arc-extension`; daemon audit endpoints | P1 audit refs | Show hash/HMAC verification, chain breaks, event correlation | API + UI tests | HMAC secret UX |
| HITL approval dialog | User approves/denies SwarmGraph interrupt | New component; daemon resume endpoint | P2 HITL persistence/CLI contracts | Require single-use decision token; log decision; do not ship UI if persistence/resume semantics are not implemented | E2E HITL test; token single-use UI/API test | Resume semantics |
| Provider/cost controls | User sees provider status and gates paid calls | Existing provider endpoints + UI | Security profiles | Dry-run by default; explicit paid profile | UI contract + API tests | Avoid secret leakage |
| Add product config CLI | Profiles/workspaces/quotas become user-manageable | `cli.py`, `providers.py`, `security/profiles.py`, workspace config modules | P0/P1 command base | Add `arc providers quota`, `arc providers quota reset`, `arc profiles list/show/create`, `arc workspace init/info/config` | CLI tests with temp home/workspace | Profile persistence design |
| Add product setup IDE | Users can configure adapters safely from UI | `packages/arc-extension` | Config endpoints | Add provider manager, profile selector, adapter setup wizard, workspace trust UI, context pack view, arena view (stub/offline label) | UI tests; no plaintext secrets | Arena may distract if productized too early |
| Add Docker-compatible isolation | Safer local execution for untrusted workspaces | `isolation/docker.py`, CLI, Theia settings | P1a isolation provider interface; workspace trust enforcement | Support Docker CLI; detect OrbStack as Docker-compatible on macOS; no OrbStack-specific dependency; backend feature with Theia status only | Integration test gated on Docker availability | Container escape/resource-limit caveats |
| Add prompt optimizer IDE toggle | Prompt refinement becomes visible and user-controlled | `packages/arc-extension`, prompt optimizer API | P1 local optimizer | Add toggle, mode selector, token estimate, preview/diff, use original/optimized buttons | UI contract tests; prompt diff tests | Token estimate may be approximate |

### P3 Definition Of Done

- Theia can select runtime + mode, configure adapters, launch runs, view live events, inspect traces, and show audit status.
- Unsupported modes are visible but disabled with precise reasons.
- HITL approval works for at least one SwarmGraph adoption test flow, with persistence and single-use token tests; otherwise HITL UI remains disabled/preview-only.
- No UI stores plaintext provider API keys.
- CLI exposes profiles, workspace config, provider quota, and quota reset.
- IDE includes provider manager, profile selector, adapter setup wizard, workspace trust UI, context pack view, and clearly labeled stub/offline arena view if retained.
- Docker-compatible isolation is available when Docker/OrbStack is installed, or explicitly deferred if P1a trust/isolation prerequisites are not mature; Theia displays detected isolation status only after backend support exists.
- IDE prompt optimizer preview/diff is available; provider-backed optimization still disabled unless explicitly implemented and gated.

## P4: Audit, Replay, HITL, Security Hardening

Goal: raise trust level from developer demo to high-assurance local tool.

| Item | Outcome | Files/modules | Dependencies | Implementation notes | Verification tests | Risks/unknowns |
|---|---|---|---|---|---|---|
| Deterministic replay API | Deterministic replay metadata available beyond trace replay | `web/routes.py`, `storage/`, `evals/` | P2 trace replay; audit integration | Separate trace replay from runtime replay; re-gate paid/provider runs before re-execution | API tests | True deterministic replay may need SG support |
| HITL persistence hardening | Pending approvals survive UI reload/restart with expiry and replay-attack protection | `storage/`, `web/routes.py` | P2 minimal HITL persistence; P3 HITL UI | Harden storage, expiry, replay protection, and recovery semantics beyond the minimal P2 implementation | Restart/expiry/replay-attack tests | Expiry/replay attacks |
| Advanced subprocess isolation hardening | Less env/secret leakage beyond P1a baseline | Adapter subprocess code, `security/redaction.py`, isolation providers | P1a env allowlist; P3 Docker if implemented | Add resource limits, stronger launcher checks, network/proxy policy where feasible | Security tests | User workflows may need env/network passthrough |
| Add eval/observability CLI | Evaluation and trace search become product workflows | `cli.py`, `evals/`, `storage/`, telemetry | P1a SQLite index; P2 eval CLI completion | Add `arc eval save`, `arc eval delete`, `arc eval run --batch`, `arc eval report`, `arc runs search`, `arc doctor env/network/storage`, `arc bug-report` | CLI tests; support bundle redaction test | Need indexed store for search |
| Add SwarmGraph insight IDE | SwarmGraph-specific value is visible | `packages/arc-extension`, daemon endpoints | Adoption/audit events | Add consensus/voting dashboard, queen/worker topology view, eval/golden trace manager, cost/token dashboard | API + UI tests | Requires stable event schema |
| Add gated prompt optimizer providers | Advanced prompt improvement can use local/provider/SwarmGraph modes safely | `prompt_optimizer/`, providers, SwarmGraph adoption | P1 local optimizer; P3 UI | Add `local-model` and `provider` modes behind privacy/paid gates; record prompt metadata in traces/audit | Gating tests; redaction tests | Privacy leakage if gates fail |

### P4 Definition Of Done

- Deterministic runtime replay is available or explicitly scoped behind runtime support; trace replay is already covered by P2.
- HITL decisions are single-use and persisted.
- Advanced subprocess isolation hardening is implemented beyond the P1a env-allowlist baseline.
- Firecracker is documented as P5+/future unless a separate owner-approved implementation track exists.
- Eval/golden trace workflows are available from CLI and IDE.
- Diagnostic support bundle is redacted and tested.
- Consensus/voting, queen/worker topology, and cost/token dashboards are backed by real run data.
- Provider/local-model prompt optimization is gated, auditable, and optional.

## P5: Release Readiness

Goal: make installation, CI, packaging, and docs reproducible. v0.1 release scope is the browser app plus Python CLI/wheel. Electron packaging is post-v0.1 until canonical extension wiring and daemon bundling are proven.

| Item | Outcome | Files/modules | Dependencies | Implementation notes | Verification tests | Risks/unknowns |
|---|---|---|---|---|---|---|
| Full CI gate | Main branch proves build/test/docs | `.github/workflows/`, `scripts/check-pr.sh` | P0-P4 | Separate fast PR gate from nightly real-runtime smoke | CI required checks | Runtime deps slow CI |
| Real-runtime smoke suite | Minimal real smoke tests for runtimes actually delivered by P2 | `python/tests/integration/real_runtime/` | Delivered adapters stable | Start with vendored SwarmGraph/LangGraph; add CrewAI only if P2 delivery includes it; mark network/provider tests opt-in | CI nightly/offline split | Flaky external deps |
| Electron packaging spike (post-v0.1) | Local unsigned + signed release path is measured before commitment | `applications/electron/`, package scripts, ADR-008 | Canonical extension wiring; daemon bundling spike | Compare PyInstaller/embedded Python/uv-managed venv; do not block v0.1 browser+CLI release | Packaging smoke/spike report | macOS signing complexity; daemon bundling unknowns |
| Docs freeze | Public docs match implemented features | `README.md`, `docs/` | All previous phases | Add doc truth checklist | Manual + grep checks | Historical docs noise |
| Release checklist | Falsifiable release criteria | `docs/RELEASE_CHECKLIST.md` | CI gate | Include security, tests, package, docs | Checklist dry run | None |
| Add arena CLI after real backend | Arena commands exist only when provider-backed path is intentionally productized | `cli.py`, `arena/`, provider gateway | Real provider calls, gates, and product approval | Add `arc arena models/tags/chat/vote/adopt`; keep Arena out of v0.1 scope | Stub + live-gated tests | Avoid overclaiming arena |
| Delete stale deploy script | Remove misleading deployment script until deploy architecture exists | `scripts/deploy.sh` | None | Delete script referencing obsolete app path; future deploy work must start from architecture doc | Repo hygiene check | None |
| Define deploy/plugin architecture | Avoid premature marketplace/deploy work | new docs/modules TBD | Product decision | Specify before adding `arc deploy` or plugin marketplace | Architecture review | Scope creep |
| Signed/reproducible sandbox images | Isolation providers are releasable and auditable | Dockerfiles, Firecracker image build scripts, release docs | Docker/Firecracker providers | Pin base images, produce SBOM/provenance, document update process | Build reproducibility check | Supply-chain maintenance |

### P5 Definition Of Done

- Fresh clone can install, build, run CLI, start browser shell, and run smoke tests.
- Release docs do not overclaim adoption support.
- Browser app + Python CLI/wheel release path is documented and tested; Electron packaging is documented as post-v0.1 unless the spike is complete.
- CI distinguishes required offline tests from opt-in live provider tests.

## Do Not Overclaim

Avoid these claims unless tests prove them:

- “ARC supports SwarmGraph adoption for CrewAI/LangGraph/OpenAI Agents/AG2/LlamaIndex.”
- “ARC has live streaming” if the endpoint only replays stored trace events.
- “ARC has signed audit trails” unless using SwarmGraph HMAC audit or equivalent keyed signature.
- “AG2 support” until registered and visible in `arc runtimes`.
- “OpenAI Agents project support” until user-supplied export target is implemented.
- “LM Arena live mode” as a v0.1 product feature until gated-live behavior is tested, documented, and intentionally productized.
- “Production ready,” “multi-user,” or “tenant-isolated” for ARC daemon before auth/workspace trust/audit hardening.

Safe language:

- “Standalone adapter exists.”
- “Detection/static export only.”
- “Stub/offline mode only.”
- “Stub-default with gated live path (not v0.1 scope).”
- “Planned SwarmGraph adoption mode.”
- “Vendored SwarmGraph runtime includes HMAC audit, HITL, quota, and consensus.”

## Do Not Build Yet

These sound useful but are premature until prerequisite product surfaces exist.

| Feature | Defer until | Reason |
|---|---|---|
| Plugin marketplace | P5 plugin architecture is defined | No plugin loading/registration mechanism exists yet. |
| Multi-tenant UI | Tenant model is wired through daemon/storage/runtime | ARC daemon is currently single-user/local. |
| Deployment CLI/UI | Deployment target and package model are defined | ARC is local-first; deploy semantics are undefined. |
| No-code workflow builder | Runtime/adoption/run/replay surfaces are stable | Visual builder would distract from high-assurance cockpit work. |
| Cloud deployment | Product explicitly expands beyond local mode | Current README/security posture is loopback-only. |
| Multi-user daemon | Auth, storage isolation, tenant model are redesigned | Current daemon is not multi-user safe. |
| Browser-use agents | Workspace trust + browser sandbox exist | High side-effect/security risk. |
| Firecracker as default | Docker-compatible provider and workspace trust are mature | Linux/KVM-only and high ops burden; should remain advanced. |
| Prompt playground | Prompt storage/versioning infra exists | Otherwise it becomes an untracked text box. |
| Provider-backed prompt optimization by default | Local optimizer, redaction, paid-call gates, and audit metadata are implemented | Online optimizers can leak sensitive prompt/workspace data. |
| SwarmGraph consensus prompt optimization | Basic local/provider optimizer and adoption protocol are stable | Consensus optimization is expensive and should be high-assurance opt-in only. |
| Dataset management | Eval/golden trace infrastructure exists | Dataset UX depends on real eval workflows. |
| Annotation queues | HITL and eval workflows exist | Queues need persisted human-review state. |

## Cross-Cutting Risk Backlog

These risks cut across phases and must be tracked explicitly during PR review.

| Risk | Why it matters | First mitigation |
|---|---|---|
| SwarmGraph vendoring/licensing/upstream sync | ARC relies on vendored runtime code for the differentiator and audit/HITL claims. | Add owner, license check, upstream sync cadence, and security patch policy before public release. |
| Secret storage cross-platform behavior | Audit keys and daemon tokens may behave differently across macOS/Linux/headless/Windows. | PR #17 validates `keyring`/env fallback and records Windows posture. |
| SSE through proxies/corporate networks | Live event UX may fail under buffering/proxy timeouts. | Event broker spike includes heartbeat/keepalive behavior and reconnect tests. |
| JSONL+SQLite dual-write atomicity | Crashes can leave index stale or corrupt. | JSONL-first writes plus rebuildable SQLite index and crash/rebuild test. |
| Cancellation semantics per adapter | `arc runs cancel` may not mean the same thing for every runtime. | Capability schema includes cancellation support; P1a adds cancellation matrix test. |
| Python packaging on Windows | Current scripts and environment are Unix-heavy. | Decide Windows v0.1 support posture before release checklist freezes. |
| OpenAI Agents SDK churn | Product path depends on a volatile SDK. | Keep fake SDK tests and workspace export adapter boundary small. |
| Theia upstream churn | Widget/API changes can break canonical shell porting. | Port in small PRs with browser smoke tests. |
| Trace retention/data growth | JSONL traces and audit files can grow without bound. | Keep/extend `arc runs prune`; add retention policy before long-lived workspace release. |
| Telemetry/support bundle privacy | Observability and `arc bug-report` can leak sensitive trace/env data. | Default no outbound telemetry; support bundle redaction test before feature ships. |

## Recommended First 23 PRs

| PR | Title | Scope | Tests | Why now |
|---:|---|---|---|---|
| 1 | Docs truth cleanup | Fix README/runtime/audit docs; correct LM Arena wording; define banned-claims list and add grep script | Script exits clean | Prevents building on false claims |
| 2 | Promote release checklist | Restore/update `docs/RELEASE_CHECKLIST.md` for v0.1.0-alpha and browser+CLI scope | Checklist dry run | Defines release criteria before implementation |
| 3 | Theia version-skew audit | Compare `packages/arc-extension` `^1.45.0` APIs against browser app Theia `1.71.0`; produce compatibility matrix before changing deps | Audit doc; API grep; no build changes | Avoids hiding a 26-version jump inside wiring |
| 4 | Extension build on Theia 1.71 | Align `packages/arc-extension` deps to browser app Theia `1.71.0`; no browser wiring yet | `pnpm --filter arc-extension build/test` | Proves canonical extension can compile on target Theia |
| 5 | Browser app canonical wiring | Add `arc-extension` to browser app deps; keep duplicate extensions during transition | `pnpm --filter @arc-studio/browser build`; browser smoke | Makes canonical claim real after compatibility proof |
| 6 | Extension migration inventory | Exact port/archive/delete order for `theia-extensions/*` | Docs review | Prevents ad hoc UI porting |
| 7 | CLI discoverability A | Add `arc version` and `arc health` | CLI JSON envelope tests | Small immediate user value |
| 8 | CLI discoverability B | Add `arc status` and `arc doctor all` | CLI + daemon-offline tests | Completes basic inspection |
| 9 | Register/hide AG2 | Register AG2 with honest capabilities or explicitly hide/remove claim | `arc runtimes --capabilities --json` test | Resolves adapter ambiguity |
| 10 | Capability schema v1 | Add schema version, support level, standalone/adoption execution fields, TS mirror | Python + TS contract tests | Required for honest UI/adoption modes |
| 11 | OpenAI Agents export target | Implement `ARC_OPENAI_AGENTS_EXPORT=module:attr`; remove hardcoded product path; refuse targets outside workspace unless explicitly trusted | Fake SDK/workspace run test; path validation test | Fixes partial adapter support without waiting for full trust enforcement |
| 12 | CLI daemon parity A | Add `arc runs diff` | Temp trace diff test | Exposes existing helper logic |
| 13 | CLI daemon parity B | Add provider diagnostics/proxy with dry-run/metadata wording | Dry-run provider proxy test | Exposes existing provider helpers safely |
| 14 | Event schema registry | Add ADR-004 `schema_version`, registry, validation helper | Event serialization/validation tests | Precedes live/adoption/HITL events |
| 15 | Adoption protocol skeleton | Add `agent_runtime_cockpit.adoption` models and `<runtime>+swarmgraph` syntax; metadata only, no executable adoption mode | Protocol unit tests | Foundation for adoption work without bypassing P1a gates |
| 16 | Adoption router skeleton | Router resolves adoption modes as not-runnable with doctor actions; no executable adoption mode until event schema, indexed storage, trust/isolation status, and paid-call gating pass | Router tests | Makes future modes visible honestly |
| 17 | Delete stale deploy script | Remove `scripts/deploy.sh` until deploy architecture exists | Repo hygiene check | Removes misleading dead path |
| 18 | Manual SSE proof | Choose manual `StreamResponse` or declare `aiohttp-sse`; prove fake replay stream with heartbeat | Streaming fake-run test; dependency check | De-risks SSE dependency/proxy behavior before broker |
| 19 | Event broker core | Add bounded-queue EventBroker with slow-client policy and reconnect semantics; no supervisor integration | Broker unit tests; reconnect tests; slow-client test | Prevents unbounded memory growth and stream ambiguity |
| 20 | Supervisor wiring | Wire JobSupervisor to broker for fake-run live stream, cancel, and orphan recovery | Cancel/orphan/reconnect tests | Completes P1a live-run infra incrementally |
| 21 | Secret storage/platform spike | Validate ADR-005 keychain/env fallback behavior on macOS/Linux/headless and document Windows posture; do not add hard `keyring` dependency before this decision | Spike report; optional dependency check | Long-lead risk for HMAC audit and daemon auth |
| 22 | Trust resolver external store | Implement advisory trust DB outside workspace; committed `.arc/trusted` must be ignored | External trust DB tests; malicious committed marker test | Closes self-authorizing repo risk before enforcement |
| 23 | Dossier scaffold hardening | Patch scaffold contradictions: fail-closed adoption runners, audit-chain verifier decision, pricing staleness, redaction regex, Appendix C labels | Grep banned claims; docs review | Prevents copy-paste of dangerous research code |

## Open Questions

| Question | Why it matters | Suggested owner |
|---|---|---|
| Which exact widgets from `theia-extensions/*` should be ported first? | Approved policy is selective port then archive/delete; ordering still matters | Product/maintainer |
| Should SwarmGraph be imported as vendored library or invoked only via CLI? | Adoption layer needs tighter integration than subprocess JSON | Runtime owner |
| Where should HMAC audit keys live? | Determines security posture and UX | Security owner |
| What is the canonical syntax for adoption runtime IDs? | Affects CLI/API/UI contract | Protocol owner |
| Is LM Arena in scope for ARC Studio v0.1? | Avoids distracting stub surface | Product owner |
| Is multi-user daemon support a goal? | Changes auth, storage, tenant model | Product/security owner |
| What is the SwarmGraph vendoring/upstream-sync policy? | Determines license/security patch responsibility for the core differentiator | Runtime/security owner |
| Is Windows a v0.1 target, best-effort, or out of scope? | Affects Python packaging, daemon auth/token storage, and release checklist | Product/release owner |
| What is the default telemetry posture? | Observability and bug reports must not leak data by default | Product/security owner |
| What is the trace retention/pruning policy? | JSONL/audit files can grow indefinitely in long-lived workspaces | Product/storage owner |
| How should out-of-workspace `ARC_OPENAI_AGENTS_EXPORT` targets behave? | User-supplied imports execute arbitrary code | Security/protocol owner |
| Are HITL approvals single-machine, single-user, or per-workspace? | Affects persistence schema and replay-attack protection | Product/security owner |
| On SQLite index corruption, rebuild from JSONL or fail loudly? | Defines recovery behavior and user trust | Storage owner |
| Does daemon auth get a compatibility window? | Auto-auth may break local scripts using the daemon directly | Security/product owner |
