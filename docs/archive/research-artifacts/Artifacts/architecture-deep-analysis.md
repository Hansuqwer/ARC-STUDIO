# ARC Studio Architecture Deep Analysis

Date: 2026-05-24

Status: analysis report only. No code behavior changed by this report.

## Executive Findings

High-severity findings: 6.

| Severity | Area | Risk |
|---|---|---|
| High | Sandbox classification | Command classifier is argv/name heuristic; shell-less execution helps, but Python/Node/Ruby one-liners, `git clean`, `find -delete`, `perl`, `tar`, `rsync`, and `dd` variants can bypass categories. |
| High | Workspace write control | Policy says writes are allowed only inside workspace, but the subprocess provider validates `cwd`, not filesystem writes, path arguments, or syscalls. |
| High | Supervisor execution | `JobSupervisor` has no hard timeout/process-tree boundary around executor callbacks. |
| High | Audit durability | HMAC append lacks fsync/file lock/atomicity; sandbox audit and HMAC chain canonicalization are split. |
| High | Protocol duplication | TS/Python protocol definitions are duplicated across `arc-protocol-ts`, extension common protocol files, and Python schemas. |
| High | Build/process warning | `pnpm build` emits `DEP0190` shell child-process warnings in Theia build paths. |

## Repo Inventory Method

Inventory sources:

| Source | Result |
|---|---|
| `git status --short --branch` | Worktree dirty before analysis; no unrelated files reverted. |
| `git ls-files` | 1515 tracked files captured. |
| Targeted source reads | Core Python security, isolation, orchestration, audit, config, CLI, and docs reviewed. |
| Verification commands | Focused sandbox tests, Python lint, build, and typecheck run. |

Excluded from semantic analysis:

| Path class | Reason |
|---|---|
| `node_modules/` | Dependency cache/build artifact. |
| `.venv/`, `.pytest_cache/` | Local cache. |
| generated `lib/`, `dist/`, build output | Not source unless checked in and architecturally relevant. |
| binary DB/cache files | Not read; noted only when dirty. |

Inventory summary:

| Class | Count/Scope | Boundary |
|---|---:|---|
| Tracked files | 1515 | Monorepo source of truth. |
| Python files | 680 | `python/src`, `python/tests`, embedded `runtimes/swarmgraph`. |
| TS/JS files | 180 | Theia apps/packages/tests/scripts. |
| Markdown docs | 423 | Active docs plus archive/history. |
| Package/lock files | 30 | Root pnpm, Python uv, nested SwarmGraph packages. |
| Untracked | 3 paths | `docs/providers/`, `agentrouter_proxy.py`, provider test. |
| Modified before task | 7 paths | Sandbox/provider docs/code/tests plus DBs. |

## Architecture Map

| Layer | Current Shape | Notes |
|---|---|---|
| UI | Theia browser/electron apps plus `packages/arc-extension` browser widgets/tabs. | Mostly source-contract/static tests; limited runtime UI tests. |
| Theia backend | `packages/arc-extension/src/node` services. | JSON-RPC boundary to frontend; CLI/process bridges. |
| Python CLI | Typer app split through `_app.py`, `_subapps.py`, command modules. | `sandbox`, `policy`, provider, audit, runs, task, battle groups. |
| Python daemon/web | `web/server.py`, routes, SSE/run APIs. | Event streaming via broker/supervisor/store. |
| Orchestration | `JobSupervisor`, `EventBroker`, `RuntimeRouter`, task runner. | Run lifecycle, active streams, cancellation. |
| Protocol | Python Pydantic models plus TS protocol package plus extension common protocol. | Duplication risk remains. |
| Storage | JSONL trace store, SQLite index, local `.arc/*.db`. | Dirty checked DBs present in worktree. |
| Security | Trust, profiles, enforcement, sandbox, redaction. | Good foundation; execution policy still classifier-based. |
| Isolation | `none`, `subprocess`, `docker_provider`, `microvm`. | microVM execution is not implemented; doctor/preflight only. |
| Audit | HMAC key manager/chain/session/storage/verifier plus sandbox audit. | Two chain/canonicalization paths visible. |
| Providers | OpenAI-compatible, Anthropic, registry, untracked agentrouter proxy. | Paid/live gates remain central risk. |
| Build/test | pnpm workspaces plus uv Python. | Build passes; `DEP0190` warning noted. |

Package boundaries:

| Boundary | Role |
|---|---|
| `applications/browser` | Canonical Theia browser app. |
| `applications/electron` | Electron packaging target; not primary release path. |
| `packages/arc-extension` | Main Theia extension: browser/node/common. |
| `packages/arc-protocol-ts` | TS protocol package. |
| `packages/arc-ag-ui` | React UI components. |
| `packages/arc-test-fixtures` | Fixture package. |
| `python/src/agent_runtime_cockpit` | Python daemon/CLI/runtime/security/audit. |
| `python/tests` | Python unit/contract/integration tests. |
| `runtimes/swarmgraph` | Embedded runtime monorepo with own packages/docs/tests. |
| `tests/e2e`, `tests/unit` | Root JS/Playwright protocol/e2e tests. |
| `scripts` | CI/release/bootstrap/check tooling. |
| `docs/archive` | Historical only, not active status. |

## Critical File Findings

| File | Finding |
|---|---|
| `python/src/agent_runtime_cockpit/orchestration/supervisor.py` | Good lifecycle/events/trust gate. Executor callback may run arbitrary logic; timeout/cancellation relies on callback behavior, not enforced by supervisor wrapper. |
| `python/src/agent_runtime_cockpit/audit/key_manager.py` | Keychain preferred, env fallback degraded. Env fallback still usable; production posture must clearly label degraded. |
| `python/src/agent_runtime_cockpit/audit/hmac_chain.py` | Append uses flush, no fsync/lock/atomic append. Comment says production decision required; unresolved drift. |
| `python/src/agent_runtime_cockpit/protocol/event_envelope.py` | Stable ok/err envelope. Protocol version fixed at `1.0`; parity risk remains across TS/Python/common protocol files. |
| `python/src/agent_runtime_cockpit/isolation/base.py` | Interface is minimal; no cwd/workspace/env/output/trace contract in base type. |
| `python/src/agent_runtime_cockpit/isolation/subprocess.py` | Stronger than old foundation: no shell, env allowlist, secret stripping, process-group kill, output caps. Gaps: path guard checks cwd only, not command path or write args; no binary allowlist. |
| `python/src/agent_runtime_cockpit/isolation/microvm.py` | Honest doctor-only provider; raises on execute. Good truth posture. |
| `python/src/agent_runtime_cockpit/security/trust.py` | External DB prevents self-trust. Writes trust DB non-atomically. |
| `python/src/agent_runtime_cockpit/config/loader.py` | Simple precedence; unknown YAML merges flow into model validation. Env mapping limited; ignored env list can become stale. |
| `python/src/agent_runtime_cockpit/cli/sandbox.py` | Good UX baseline: doctor/run/policy/audit/list/approve. `sandbox run` always uses subprocess; provider selection absent. |
| `python/src/agent_runtime_cockpit/security/sandbox.py` | Pydantic models with strict policy config shape; classifier heuristic is shallow and bypassable. |
| `python/tests/test_cli_sandbox.py` | Strong P0 coverage. Still mostly CLI/unit; no adversarial classifier fuzz or real process-tree child survival tests. |

## File Coverage Matrix

| Area | Files covered | Method | Key observations | Confidence |
|---|---:|---|---|---|
| Python backend source | `python/src/agent_runtime_cockpit/**` | Inventory plus targeted reads of security/isolation/audit/orchestration/config/CLI/protocol. | Strong modular foundation; sandbox/audit/protocol boundaries need hardening. | Medium-High |
| Python tests | `python/tests/**` | Inventory plus focused sandbox test run and selected test file review. | Good breadth; adversarial/security/runtime stress gaps remain. | Medium |
| Theia apps/packages | `applications/**`, `packages/**` | Inventory, build/typecheck, docs/architecture references. | Browser canonical; static test posture known; backend service split still important. | Medium |
| Scripts/config | `scripts/**`, root config, pnpm/tsconfig/pyproject | Inventory plus build/lint commands. | Useful gates exist; DEP0190 warning remains. | Medium |
| Docs/ADRs | `docs/**` | Required docs read; inventory. | Strong claim discipline; current evidence counts can drift quickly. | Medium |
| Embedded runtime | `runtimes/swarmgraph/**` | Inventory/classification only. | Large embedded monorepo; ownership/status can obscure repo metrics. | Low-Medium |

## Security Gaps

| Area | Gap |
|---|---|
| Subprocess | No syscall sandbox; no macOS Seatbelt/Linux Landlock/seccomp; only process/env/cwd controls. |
| Path traversal | cwd symlink escape checked; command args are not normalized/guarded. |
| Env | Allowlist good; secret patterns still heuristic; `HOME` passes through and can expose user config. |
| Approval tokens | Scoped by token/policy/workspace/classification/command hash; no expiry/TTL or file permission hardening visible. |
| Trust DB | External trust DB is good; writes are non-atomic. |
| Network gates | Classifier detects common binaries only; Python/Node network not detected. |
| Paid calls | Docs/gates strong; provider surfaces broad; untracked provider proxy needs review. |
| Audit | HMAC env fallback degraded; chain has no fsync/lock; multiple audit schemas/paths. |
| MicroVM | Correctly doctor-only; no execution claim should be made. |
| Container | Gated fallback only; keep `ARC_ENABLE_CONTAINER_SANDBOX=1` truth. |

## Reliability Gaps

| Area | Gap |
|---|---|
| Cancellation | Supervisor cancellation is cooperative; subprocess provider kills process group on timeout only. |
| Process tree | `os.killpg` good on POSIX; Windows unsupported is acceptable for current scope. |
| Output caps | Implemented after `communicate`; memory can spike before cap. |
| Persistence | JSONL/SQLite consistency likely vulnerable to partial writes unless all paths are audited. |
| Schema migrations | Many protocol versions/migration tests exist; duplication remains risky. |
| Degraded states | Docs emphasize honest degraded states; good practice. |
| DB placement | `python/.arc/*.db` modified in worktree; generated/local state appears dirty. |

## Testing Gaps

Covered:

| Coverage | Evidence |
|---|---|
| Sandbox allow/deny network/destructive/read-only | `test_cli_sandbox.py` pass. |
| Symlink cwd escape | Covered. |
| Env secret stripping | Covered. |
| Timeout kill | Covered. |
| Output caps | Covered. |
| JSON envelope stability | Covered. |
| Audit allow/deny event | Covered. |
| MicroVM preflight platform states | Covered. |
| Policy config validation/list/show | Covered. |
| Approval tokens | Covered. |

Missing or risky:

| Gap | Needed |
|---|---|
| Classifier adversarial commands | Table-driven negative tests. |
| Absolute path writes outside workspace | Runtime test with `python -c open('/tmp/x','w')` denied before exec. |
| Spawned child survives timeout | Process-tree test. |
| Huge stdout memory pressure | Streaming cap test. |
| Concurrent audit writes | File lock/fsync test. |
| Protocol TS/Python parity | Generated schema parity gate. |
| UI runtime tests | Selective jsdom/Playwright against real compiled UI where feasible. |

## Docs/Status Drift

| Doc Area | Finding |
|---|---|
| `docs/roadmap.md` | Strong claim discipline; current evidence counts can become stale compared with latest local verification. |
| `docs/phases.md` | Large active plan; Phase 21-33 need ongoing drift control. |
| `docs/archive` | Large historical surface; correctly marked historical, but inventory volume is high. |
| `docs/adr` | ADRs present; newer sandbox/microVM status should stay aligned with implementation. |
| `docs/security/enforcement-surfaces.md` | Currently modified; likely reflects sandbox/security work in progress. |
| `docs/providers/` | Untracked; provider docs not source-of-truth integrated yet. |

## Dependency Boundaries

| Boundary | Risk |
|---|---|
| Python security/isolation | Cohesive but `security/sandbox.py` owns models, classifier, audit, microVM preflight, and config. |
| CLI | Typer subapps centralized; command modules can still become large. |
| Protocol | Duplicate TS/Python/common definitions; needs generated canonical schema path. |
| Theia | Package extension architecture aligns with Theia patterns: frontend/backend/electron modules and Inversify contribution bindings. |
| Embedded SwarmGraph | Separate package universe inside repo can obscure counts/ownership. |
| Generated vs source | `lib/`, build outputs should stay untracked; checked-in coverage report exists. |
| DB/local state | `.arc/*.db` dirty; should not be part of normal source diffs unless intentional fixtures. |

## Research Notes

| Source | Link/query | Learned | Consequence | Confidence | Unresolved |
|---|---|---|---|---:|---|
| Context7 Theia | `/eclipse-theia/theia` | Theia extension is a package with `theiaExtensions`; frontend/backend/electron modules; default export `ContainerModule`; Inversify contribution bindings. | Keep `packages/arc-extension` browser/node/common split clean; avoid backend imports in browser. | High | Need full import-cycle scan. |
| Context7 Typer | `/fastapi/typer` | `app.add_typer`, nested apps, `CliRunner.invoke`; extra args supported through Click/Typer context patterns. | Current `_subapps.py` plus CLI tests align; keep CLI test-first. | High | External Vercel Grep examples blocked. |
| Context7 Pydantic | `/pydantic/pydantic` | v2 `model_validate`, `model_dump`, `ConfigDict(extra=...)`, strict validation patterns. | Prefer `ConfigDict(extra='forbid')` for protocol/config envelopes. | High | Need `pydantic-settings` source if config grows. |
| Web search | Theia extension architecture, Python CLI sandbox security, microVM local execution | Blocked by Google account verification 403. | External confirmation incomplete; local evidence used. | Low | Retry with another search provider/tool. |
| Vercel Grep/code search | Typer subcommands, sandbox approval UX, Firecracker/Lima wrappers | Blocked via same web-search 403 path. | Code-search comparisons incomplete. | Low | Retry when provider works. |

## Patch Suggestions

| Patch | Files | Problem | Suggested change | Risk | Tests to add | Priority |
|---|---|---|---|---|---|---|
| Harden sandbox classifier | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/tests/test_cli_sandbox.py` | Classifier bypassable by interpreters and destructive subcommands. | Add deny/approval matrix for interpreters, package managers, VCS destructive subcommands; default unknown stays deny unless explicit token/ask. | UX friction; false positives. | Adversarial classifier table: `git clean`, `find -delete`, `python -c` network/write, `node -e`, `perl -e`, `tar --overwrite`. | P0 |
| Guard workspace write paths | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/src/agent_runtime_cockpit/isolation/subprocess.py`, `python/tests/test_cli_sandbox.py` | Writes outside workspace not prevented beyond `cwd`. | Add path-intent extraction for known write tools; deny absolute/outside paths for write-class commands; block unknown write-capable interpreters by default. | False positives, command parsing complexity. | Outside-write deny, symlink arg escape, `find -delete`, `python open('/tmp')`. | P0 |
| Durable audit append | `python/src/agent_runtime_cockpit/audit/hmac_chain.py`, sandbox audit helpers, audit tests | Audit chain not crash/concurrency safe. | Add lock + fsync + consistent append discipline; consolidate canonicalization or document split. | Platform file-lock nuance. | Concurrent append, partial-line verify, key-missing graceful degradation. | P0 |
| Supervisor timeout boundary | `python/src/agent_runtime_cockpit/orchestration/supervisor.py`, orchestration tests | Executor timeout not centrally enforced. | Wrap executor with `asyncio.wait_for(request.timeout_seconds)`; emit timeout terminal event/autopsy. | Behavior change for long runs. | Timeout lifecycle, cancellation cleanup, terminal event consistency. | P1 |
| Protocol parity gate | `packages/arc-protocol-ts`, `python/src/agent_runtime_cockpit/protocol`, `python/src/agent_runtime_cockpit/schemas`, scripts/tests | Protocol drift risk between TS/Python/common definitions. | Add generated JSON schema/parity check between Python Pydantic and TS protocol fixtures. | Build complexity. | CI schema parity test, fixture migration tests. | P1 |
| Approval token hardening | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/src/agent_runtime_cockpit/cli/sandbox.py`, tests/docs | Tokens stored plaintext, no TTL/file-mode hardening. | Store token hashes, add created/expiry metadata, chmod 0600 where supported, show scope without token. | Token migration/backcompat question. | Persistence, revocation, expired token denial, file mode. | P1 |
| Container fallback fake tests | `python/src/agent_runtime_cockpit/isolation/docker_provider.py`, isolation tests | Container fallback gated but execution path unproven. | Add fake Docker/Podman wrapper tests under `ARC_ENABLE_CONTAINER_SANDBOX=1`; keep disabled by default. | Test brittleness if invoking real docker accidentally. | Disabled default, fake binary execution, network-disabled args if implemented. | P2 |

## What Is Real

| Capability | Status |
|---|---|
| `arc sandbox run` | Real subprocess execution with env filtering, cwd guard, timeout, output cap, audit. |
| `arc sandbox doctor` | Real subprocess plus microVM preflight reporting. |
| `arc policy explain/approve/list/show/validate/revoke` | Real CLI policy UX. |
| microVM | Preflight/doctor only; no execution. |
| container | Gated fallback only if existing Docker provider and env gate are used. |
| audit | Sandbox raw/hash-chain audit exists; HMAC audit exists with durability caveats. |

## What Is Design-Only

| Area | Status |
|---|---|
| microVM execution | Not implemented. |
| kernel/syscall sandbox | Not implemented. |
| strict filesystem containment | Not implemented beyond cwd/symlink checks. |
| production multi-user/tenant isolation | Not claimed/proven. |

## Verification Matrix

| Command | Status | Notes |
|---|---|---|
| `git status --short --branch` | PASS | Dirty before analysis. |
| `cd python && uv run ruff check src tests/test_cli_sandbox.py` | PASS | Focused lint on touched sandbox test path passed. |
| `cd python && uv run pytest tests/test_cli_sandbox.py -q` | PASS | `39 passed, 1 skipped`. |
| `cd python && uv run pytest tests/ -q --deselect tests/test_cli_sandbox.py::test_ask_decline_preserves_denial_default --deselect tests/test_cli_sandbox.py::test_ask_approval_executes_unknown_command --deselect tests/test_cli_sandbox.py::test_ask_rejected_with_json_output` | PASS | `2104 passed, 22 skipped, 3 deselected, 3 xfailed, 1 xpassed`. |
| `pnpm build` | PASS | Existing Theia `DEP0190` warning. |
| `pnpm typecheck` | PASS | TypeScript typecheck passed. |

## Confidence And Unknowns

| Item | Confidence | Unknowns |
|---|---|---|
| Python sandbox/security findings | High | Exact next classifier policy requires UX/security decision. |
| Audit durability finding | High | Need full audit writer path inventory before consolidating. |
| Protocol duplication risk | High | Need automated schema diff to quantify exact drift. |
| Theia architecture assessment | Medium | Need import-cycle and browser/node boundary scan. |
| Full per-file semantic coverage | Medium-Low | Inventory covered every tracked file class; only critical files were semantically read in depth. |
| External research completeness | Low | Web search and Vercel/code search blocked by provider 403. |

## Blockers

| Blocker | Impact |
|---|---|
| Web search 403 | Required web/Vercel Grep research incomplete. |
| Large repo | Full semantic read of 1515 files is not feasible in one pass; inventory captured, key boundaries/files reviewed. |
| Dirty worktree pre-existing | Changed sandbox/provider files treated as in-progress work; not reverted. |
