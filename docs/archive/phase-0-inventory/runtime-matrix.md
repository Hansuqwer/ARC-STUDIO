# Phase 0 — Runtime / Mode / Gate Matrix

Status: DRAFT (Phase 0 inventory, non-destructive)
Scope: every runtime × every mode × current implementation status.
This is the truth table the banned-claims list maps to.

## How to fill this file

1. Walk `python/src/agent_runtime_cockpit/adapters/` and `python/src/agent_runtime_cockpit/swarmgraph/`.
2. For each runtime, record real status per mode.
3. Status values: Implemented | Scaffolded | Enum-only | Absent.
4. Cite code reference (file:symbol or file:line).

## Runtime × Mode status

| Runtime | fake_offline | gated_local | provider_backed | Default mode | Owner | Notes |
|---|---|---|---|---|---|---|
| swarmgraph (native) | Implemented (`adapters/swarmgraph.py:305-374`, `swarmgraph/runner.py:40-110`) | Absent in native adapter | Absent in native adapter | fake_offline | ARC | native adapter forces `ExecutionMode.fake_offline` |
| swarmgraph (external CLI via ARC_SWARMGRAPH_CLI) | n/a | n/a | Implemented-delegated (`adapters/swarmgraph.py:401-532`) | n/a | external | legacy/delegation path; does NOT prove native completeness |
| langgraph+swarmgraph | Implemented-adoption (`runtime_router.py:195-335`) | Scaffolded/gated local-real (`ARC_REAL_RUNTIME_SMOKE`, `ARC_LANGGRAPH_SWARMGRAPH_REAL`) | Absent | fake_offline | adoption adapter | no provider calls; `provider_backed=False` |
| crewai+swarmgraph | Implemented-adoption fake/offline (`runtime_router.py:111-192`) | Absent | Absent | fake_offline | adoption adapter | non-fake mode raises `RuntimeNotRunnable` |
| langgraph | Scaffolded via registry | Unknown until capability report | Unknown until capability report | capability report | adapter | explicit runtime resolution required |
| crewai | Scaffolded via registry | Unknown until capability report | paid-gated if adapter requires | capability report | adapter | preflight marks CrewAI paid required in `cli.py:149-166` |
| openai-agents | Scaffolded via registry | Unknown until capability report | Unknown until capability report | capability report | adapter | listed in `KNOWN_RUNTIMES` |
| ag2 | Scaffolded via registry | Unknown until capability report | Unknown until capability report | capability report | adapter | listed in `KNOWN_RUNTIMES` |
| llamaindex | Scaffolded via registry | Unknown until capability report | Unknown until capability report | capability report | adapter | listed in `KNOWN_RUNTIMES` |
| lmarena | Scaffolded/stub | Unknown until capability report | Unknown until capability report | capability report | adapter | listed in `KNOWN_RUNTIMES`; no live Arena claim |
| combo (router) | Implemented composition (`runtime_router.py:49-109`) | n/a | n/a | explicit/combo | router | runs child adapters sequentially |

## Gate inventory per runtime

| Runtime | env gate | paid-call gate | confirmation gate | profile enforcement | Notes |
|---|---|---|---|---|
| swarmgraph (native) | n/a (fake_offline only today) | unused (`adapters/swarmgraph.py:312-320`) | n/a | preflight/profile outside native run path | provider_backed will need all three |
| swarmgraph (external CLI) | `ARC_SWARMGRAPH_RUN_BACKEND` via `require_dual_gate("SWARMGRAPH")` | `ARC_SWARMGRAPH_ALLOW_COSTS` | — | `require_dual_gate` | env allowlist + workspace-root reject + redaction (`adapters/swarmgraph.py:84-115`, `534-557`) |
| langgraph+swarmgraph | `ARC_REAL_RUNTIME_SMOKE`, `ARC_LANGGRAPH_SWARMGRAPH_REAL` for local-real | false | — | capability report | no provider calls (`runtime_router.py:195-335`) |
| crewai+swarmgraph | fake/offline only | false | — | capability report | non-fake blocked (`runtime_router.py:140-145`) |
| crewai | adapter/report dependent | `--allow-paid-calls` + paid profile | — | `enforce_profile` | `cli.py:149-166` |
| openai-agents | adapter/report dependent | adapter/report dependent | — | `enforce_profile` | status must come from capability report |
| providers.action (cross-cutting) | ARC_ALLOW_LIVE_PROVIDER_TESTS | --allow-paid-calls + --live | RUN_PROVIDER_ACTION:<provider>:<model> | — | 3-layer gate today |

## Capability report shape (proposed, Python-owned)

| Field | Type | Required | Notes |
|---|---|---|---|
| schema_version | int | yes | bump on breaking change |
| runtime_id | str | yes | |
| modes | list[enum] | yes | fake_offline / gated_local / provider_backed |
| default_mode | enum | yes | |
| gates | list[GateRequirement] | yes | env var names, paid-call flag, confirmation token |
| degraded_reasons | list[str] | yes | empty if fully ready |
| provider_requirements | optional | no | provider id, model id, key source |

Contract test (Phase 3): `tests/contract/test_runtime_capability_schema.py`
TS mirror fixture (Phase 3): `packages/protocol/src/__fixtures__/runtime-capability.json`

## Banned-claims mapping

| Claim | Permitted only when | Current status |
|---|---|---|
| "SwarmGraph has real model intelligence" | native provider_backed = Implemented + tested | BANNED |
| "SwarmGraph is provider-backed" | native provider_backed = Implemented + tested | BANNED |
| "Provider-backed mode exists in native SwarmGraph" | same as above | BANNED |
| "External SwarmGraph CLI proves native provider-backed" | never | PERMANENTLY BANNED |
| "End-to-end real SwarmGraph agents" | CLI + IDE both wired to native provider_backed + tested | BANNED |
| "Broad provider-backed SwarmGraph adoption" | locked roadmap explicitly forbids | PERMANENTLY BANNED until lock changes |

## Acceptance for this file

- Every runtime × mode cell filled with one of the four status values.
- Every gate per runtime cited to code.
- Capability shape table complete.
- Banned-claims mapping has no Unknown rows.

## Planning Support Per Runtime

| Runtime | Plan | Build | Auto | Current evidence | Notes |
|---|---|---|---|---|---|
| `arc-studio` local shell | mode switch only | mode switch only | mode switch only | `cli_studio.py:35-38`, `220-233` | no agent execution |
| `arc studio chat` + native SwarmGraph | absent named `/plan`; prompt decomposes directly | direct fake/offline run | absent | `cli_repl/chat_repl.py:92-101`, `swarmgraph/runner.py:50-93` | target adds explicit plan approval |
| `langgraph+swarmgraph` adoption | scaffolded by fake objective | scaffolded run | absent | `runtime_router.py:251-335` | no provider-backed planning claim |
| external CLI SwarmGraph | delegated/unknown | delegated | delegated/unknown | `adapters/swarmgraph.py:401-532` | external behavior not native proof |

## Runtime Switching Policy

- Default runtime: `swarmgraph`.
- Default mode: `fake_offline` (`fake/offline` display alias accepted).
- Runtime selector source: Python capability reports only; TS/IDE may mirror shape but must not invent readiness.
- Blocked runtime rows may display remediation but must not be selectable for execution.
- Switching runtime updates session `runtime_id`, resets incompatible `runtime_model`, keeps transcript.
- Provider-backed switch requires profile + paid-call + confirmation gates before any live call.

## SwarmGraph-Specific Capabilities (per ADR-013)

| Capability | Default | Configurable | Phase |
|---|---|---|---|
| Orchestrator-worker pattern | enabled | no (architectural) | 4 |
| Hierarchical levels | 1 | yes, max 3 | 4 |
| Fan-out gate | enabled | yes (threshold, default 0.6) | 4 |
| Worker context isolation | strict | yes (filter rules) | 4 |
| Worker roles | generic | yes (add via prompts/) | 4 |
| Consensus: judge-arbitrated | default | yes | 4 |
| Consensus: majority | available | yes | 4 |
| Consensus: weighted | available | yes | 4 |
| Consensus: debate-N | available | yes | 4 |
| Consensus: proof-of-thought | available | yes | 4.7 |
| Consensus: symbolic | available | yes | 4 |
| Checkpoint-restore | per-step | yes (retention) | 4 |
| Failure mode detection (13) | enabled | yes (per detector) | 4.7 |
| MASS topology optimization | absent | enable in Phase 6.5 | 6.5 |

## Security Capabilities (per ADR-014)

| Capability | Status | Phase |
|---|---|---|
| L1 Tagging (untrusted_input/workspace_input/user_input) | mandatory | 4 |
| L2 Classification (injection detector) | mandatory | 4 |
| L3 CaMeL-style architectural separation | mandatory | 4 |
| L4 Output validation (schema-checked worker outputs) | mandatory | 4 |
| L5 Action gating (HITL on security-sensitive) | mandatory | 4 |
| L6 Audit emission | mandatory | 4 |
| Four-tier trust model | mandatory | 4 |
| MCP server allowlist | mandatory if MCP enabled | 5.6 |
| MCP manifest pinning + verification | mandatory if MCP enabled | 5.6 |
| MCP per-tool authorization | mandatory if MCP enabled | 5.6 |
| MCP tool description sanitization | mandatory if MCP enabled | 5.6 |
| MCP output isolation | mandatory if MCP enabled | 5.6 |
| Sandbox: subprocess (stdio MCP) | available | 4 |
| Sandbox: container (HTTP/SSE MCP) | available | 3 |
| Sandbox: microvm (high-risk) | available | 3 |

## Compliance Capabilities (per ADR-015)

| Capability | Status | Phase |
|---|---|---|
| AssuranceTab Developer mode | scaffolded | 5 |
| AssuranceTab Compliance mode | absent | 5 |
| AssuranceTab Both mode | absent | 5 |
| Receipt schema v2 (compliance-grade) | absent | 4 |
| Compliance bundle export | absent | 5 |
| Receipt verification | partial (v1) | 4 |
| Audit chain (tamper-evident) | partial | 4 |
| Retention policy enforcement | absent | 4 |
| Cryptographic signatures | absent (optional) | 5 |
| External timestamping (RFC 3161) | deferred | 8+ |
