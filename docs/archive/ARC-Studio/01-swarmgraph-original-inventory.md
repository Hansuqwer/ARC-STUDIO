# Original SwarmGraph Inventory

**Date:** 2026-05-19
**Source:** https://github.com/Hansuqwer/SwarmGraph (v0.8.1, 72 commits, main branch)
**Analysis:** Full package inventory from public repo structure and README.

---

## Package 1: swarm-shared

**PyPI:** `pip install swarm-shared`
**Location:** `packages/swarm-shared/swarm_shared/`

| File | Lines | Purpose |
|---|---|---|
| `__init__.py` | — | Package init |
| `audit.py` | 474 | HMAC-SHA256 + hash chain audit signing/verification, `AuditRecord`, `AuditChain`, `verify_chain`, JSONL persistence with fsync |
| `audit_backends.py` | — | S3 audit backend, conditional append, restore CLI |
| `atomic_write.py` | — | Atomic file writes |
| `bounded_list.py` | — | Bounded-size list utility |
| `checkpointing.py` | — | Checkpoint helpers |
| `hashing.py` | — | Hash utilities |
| `memory_adapters.py` | — | Memory adapter interfaces |
| `pricing.py` | — | Cost/pricing utilities |
| `redaction.py` | — | Output redaction (notably: ARC has its own `security/redaction.py`) |
| `time.py` | — | Time utilities |

**Key exports:** `AuditRecord`, `AuditChain`, `GENESIS_PREV_HASH`, `sign_record`, `verify_record`, `verify_chain`, `append_jsonl`, `load_jsonl_chain`, `AuditKind` (literal union)

---

## Package 2: hive-swarm

**PyPI:** `pip install hive-swarm`
**Version:** 1.1.0-patched
**Location:** `packages/hive-swarm/swarm/`

### Subpackage: `swarm/` (root)

| File | Lines | Purpose |
|---|---|---|
| `__init__.py` | ~80 | Full public API surface: `build_swarm_graph`, all models/types, consensus funcs, checkpoint stores |
| `_audit_helper.py` | — | Audit chain helper for swarm execution |

### Subpackage: `swarm/models/`

| File | Lines | Purpose |
|---|---|---|
| `__init__.py` | — | Package init |
| `agent.py` | — | `AgentSpec`, `AgentState`, `AgentVote`, `ApprovalDecision`, `WorkerResult` |
| `base.py` | — | Base model primitives |
| `config.py` | — | `SwarmConfig` |
| `consensus.py` | — | `ConsensusResult`, `run_consensus`, `raft_consensus`, `bft_consensus`, `gossip_consensus`, `majority_consensus`, `canonicalize_action` |
| `memory.py` | — | `SwarmMemory`, `SwarmMemoryEntry` |
| `state.py` | — | `SwarmCheckpoint`, `SwarmState` |
| `task.py` | — | `QueenDirective`, `SwarmTask` |
| `types.py` | — | `AgentRole`, `AgentStatus`, `ComplexityTier`, `ConsensusProtocol`, `SwarmFailureCause`, `SwarmStatus`, `SwarmStrategy`, `SwarmTopology`, `TaskPriority`, `TaskStatus` |

### Subpackage: `swarm/graphs/`

| File | Lines | Purpose |
|---|---|---|
| `__init__.py` | — | Package init |
| `factory.py` | — | `build_swarm_graph()` — LangGraph factory that constructs queen/worker graph |

### Subpackage: `swarm/nodes/`

| File | Lines | Purpose |
|---|---|---|
| `__init__.py` | — | Package init |
| `approval.py` | — | HITL approval node |
| `checkpointing.py` | — | `FileCheckpointStore`, `InProcessCheckpointStore`, `SwarmRedactingCheckpointer` |
| `consensus.py` | — | Consensus aggregation node |
| `judge.py` | — | Judge/evaluation node |
| `queen.py` | — | Queen orchestrator node (decomposes tasks, dispatches workers) |
| `router.py` | — | Conditional routing node |
| `scaling.py` | — | Resource-aware scaling logic |
| `sona.py` | — | SONA (Swarm-Optimized Neural Architecture) node |
| `worker.py` | — | Worker execution node (performs actual work) |

### Subpackage: `swarm/llm/`

| File | Lines | Purpose |
|---|---|---|
| `__init__.py` | — | Package init |
| `dispatch.py` | — | LLM call dispatch (routes to provider/mock) |
| `embeddings.py` | — | Embedding utilities (anti-drift similarity) |
| `prompts.py` | — | Prompt templates |

---

## Package 3: ai-provider-swarm-gateway

**PyPI:** `pip install ai-provider-swarm-gateway`
**Location:** `packages/ai-provider-swarm-gateway/src/ai_provider_swarm_gateway/`

Features:
- Provider registry and routing
- Provider adapters (OpenAI, etc.)
- Quota tracking
- Multi-tenant quota isolation
- Audit log verification
- `swarm` CLI entry point (`ai-provider-gateway`)
- Dashboard TUI (Textual)
- Encrypted account vault (Fernet)
- Semantic response cache (SQLite)
- Grok/xAI adapter

---

## Feature vs Product Surface Map

### Core Runtime (needed for ARC CLI/IDE)
- Pydantic v2 strict/frozen models
- Queen/worker graph topology
- Consensus protocols (raft, bft, majority, gossip)
- HITL approval
- Audit chain (HMAC-SHA256)
- Checkpoint/replay
- LLM dispatch (fake/stub + real)
- Cost tracking
- State management

### Optional/Product Surfaces (not needed for ARC CLI/IDE)
- Textual monitoring dashboard
- Standalone provider gateway product
- S3 audit backend
- Encrypted browser account import
- Multi-tenant quota isolation
- Semantic response cache
- xAI/Grok adapter
- Release provenance (GitHub attestation)
