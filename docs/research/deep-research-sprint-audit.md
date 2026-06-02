# Audit: "Deep Research Sprint for ARC Studio and SwarmGraph" vs Current Repo

**Date:** 2026-06-02  
**Repo:** https://github.com/Hansuqwer/arc-theia-studio  
**Branch audited:** `main` @ `0e5cb80`  
**Document audited:** *Deep research sprint for ARC Studio and SwarmGraph* (downloaded docx)

---

## 1. What the document claims exists

The document's code audit section (§26–28) asserts the following things are already present in the repo:

| Claim | Verified? | Notes |
|---|---|---|
| Adapters for AG2, CrewAI, LangChain, LangGraph, OpenAI Agents, SwarmGraph, LlamaIndex | ✅ | All present in `adapters/` |
| `swarmgraph/consensus.py`, `risk_assessment.py`, `runner.py` etc. | ⚠️ Partial | These live in `runtimes/swarmgraph/` (the vendored workspace package), NOT in `python/src/agent_runtime_cockpit/swarmgraph/`. The `swarmgraph/` source package contains only `__init__.py` — a thin bridge |
| Discriminated RunEvent unions in TS | ✅ | `packages/arc-protocol-ts/src/run-events.ts` exists |
| Runtime capability v2 schema | ✅ | `packages/arc-protocol-ts/src/runtime-capability-v2.ts` exists |
| HITL, audit chain, evals, MCP server, trust enforcement | ✅ | All present |
| Assurance, Battle, Chat, Config, Runs, SwarmGraph Insight tabs in UI | ✅ | Confirmed in `packages/arc-extension/` |
| `security/enforcement.py`, `trust.py` | ✅ | Present |
| `mcp/server.py` with trust gate, redaction, audit | ✅ | Present |

**Key discrepancy:** The document treats the vendored `runtimes/swarmgraph/` package as if it were first-class source code in the main Python tree. The build/import boundary matters for the recommended new files (`policy_linter.py`, `compiler.py`, etc.).

---

## 2. Document's "roadmap drift" claim

The document (§29) flags that `SWARMGRAPH_FEATURE_LIST.md` marks discriminated TS unions and MCP work as "not started" while they already exist. 

**Current state:** Both `run-events.ts` (discriminated unions) and `mcp/server.py` (local MCP with trust) are committed and shipped. The document's observation was accurate at the time of writing. **This drift should be corrected in `SWARMGRAPH_FEATURE_LIST.md`.**

---

## 3. The eight "build now" features — current status

### Priority 1 — Consensus Policy Linter (score: 20/20)

**What it needs:** `swarmgraph/policy_linter.py`, `protocol/policy_report.py`, `cli/policy.py`, UI preflight drawer.

**Current state:**
- `security/sandbox.py` — classify_command, decide(), deny-by-default policy engine ✅ (strong foundation)
- `security/enforcement.py` — paid-call, shell, network, trust gates ✅
- `security/trust.py` — workspace trust ✅
- `runtimes/swarmgraph/risk_assessment.py` — risk scoring ✅ (in vendored package)
- **Missing:** `swarmgraph/policy_linter.py` ❌, `protocol/policy_report.py` ❌, `cli/policy.py` ❌
- **CLI:** `arc sandbox` and `arc policy` exist for command-level policy; workflow-level preflight linting does not exist ❌
- **UI preflight drawer:** Not present ❌

**Gap:** The substrate is strong (the sandbox engine is production-grade). The missing layer is a workflow-level linter that wraps the existing risk/consensus files and produces a structured `PolicyReport` before execution.

---

### Priority 2 — MCP Tool Risk Broker (score: 19/20)

**Current state:**
- `mcp/server.py` — stdio-first, trust-gated, redacted, audit-logged ✅
- `mcp/session.py` — session lifecycle ✅
- `security/enforcement.py` — trust gates ✅
- ADR-014 (audit) names manifest pinning and allowlists as the target ✅
- **Missing:** `mcp/registry.py` ❌, `mcp/manifests.py` ❌, `mcp/policy.py` ❌
- **Missing:** `protocol/mcp_manifest.py` + TS mirror ❌
- **Missing:** `arc mcp inspect / pin / diff-manifest` CLI commands ❌
- **Missing:** MCP Servers pane in Config tab ❌

**Gap:** The MCP server is a solid foundation. What's absent is the manifest-pinning and risk-scoring layer above it.

---

### Priority 3 — SwarmGraph Protocol Compiler (score: 19/20)

**Current state:**
- Adapter export functions exist for LangGraph, CrewAI, OpenAI Agents, AG2 ✅
- `runtimes/swarmgraph/graph.py`, `runner.py` exist in the vendored package ✅
- **Missing:** `swarmgraph/compiler.py` ❌, `swarmgraph/ir.py` ❌
- **Missing:** compiler annotations in `protocol/schemas.py` and TS mirror ❌
- **Missing:** "Compile to SwarmGraph IR" UI flow ❌

**Gap:** The adapters produce export metadata; no normalising compiler consumes that metadata into a typed IR.

---

### Priority 4 — Eval-to-Policy Loop (score: 18/20)

**Current state:**
- `evals/golden.py`, `evals/diff.py`, `evals/artifact.py`, `evals/consensus.py` ✅
- Run receipts, autopsies, trust-diff protocol entities ✅
- **Missing:** `evals/policy_recommend.py` ❌
- **Missing:** `arc evals recommend-policy` CLI ❌
- **Missing:** PolicyRecommendation cards in Assurance tab ❌

**Gap:** Good eval substrate; no feedback loop from eval failures to policy suggestions.

---

### Priority 5 — Local Agent Flight Recorder (score: 18/20)

**Current state:**
- `storage/jsonl.py`, `storage/indexed_store.py`, HMAC audit chain ✅
- Run receipts, autopsy, events JSONL ✅
- **Missing:** `tracing/flight_recorder.py` ❌ (only `tracing/jsonl_writer.py` exists)
- **Missing:** bounded retention, crash-safe segments, exportable forensic bundles ❌

**Gap:** Per-run JSONL exists; always-on bounded recorder with segment export does not.

---

### Priority 6 — Run Diff and Trace Time Travel (score: 17/20)

**Current state:**
- `evals/diff.py` — run comparison ✅
- `arc runs diff <a> <b>` CLI ✅
- Runs tab with replay ✅ (basic)
- **Missing:** node-by-node decision time travel in the UI ❌
- Trace viewer exists but is JSON-heavy ⚠️

**Gap:** The diff infrastructure exists; the fine-grained visual replay is the missing piece.

---

### Priority 7 — SwarmGraph Action Simulator (score: 17/20)

**Current state:**
- Sandbox `decide()` + `classify_command()` engine — simulates command-level decisions ✅
- `arc policy explain -- <cmd>` — explains decisions ✅
- **Missing:** workflow-level simulation (what would happen if this graph ran with these inputs?) ❌

**Gap:** Command-level simulation is solid. Workflow-level pre-execution simulation is absent.

---

### Priority 8 — Consensus Escrow DevKit (score: 17/20)

**Current state:**
- `runtimes/swarmgraph/consensus_escrow.py` in vendored package ✅
- **Missing:** developer-facing DevKit CLI (`arc swarmgraph escrow replay`) ❌
- **Missing:** UI components for escrow vote inspection ❌

**Gap:** Escrow logic exists in the runtime; no developer-facing surface to inspect/replay escrow decisions.

---

## 4. What the document misses (shipped since the document was written)

The research document predates the work done on this branch. These features are **already shipped** and should be reflected in any follow-up roadmap:

| Feature | Shipped commit |
|---|---|
| Full-screen Textual TUI (Phases 4.1–4.9) | `846ffac` |
| Interactive `/providers` widget — full models.dev catalog, API key setup, model select | `12f8625` |
| Live slash menu with descriptions, command palette, help screen | `10b055c` |
| Landlock LSM detection/preflight + `arc sandbox doctor` | `51d6862` |
| Plain-JSON piped output (machine-readable) | `51d6862` |
| 13+ provider snapshot (Groq, OpenRouter, Cerebras, NVIDIA, OpenAI, etc.) | `d6ffc5c` |
| `ARC_MODELS_DEV_LIVE=1` live catalog flag | `d6ffc5c` |
| Enter-key fix (TextArea key routing) | `f6ea60b` |

---

## 5. Ecosystem alignment gaps (document §9–13)

The document flags five ecosystem shifts and their implications for ARC:

| Shift | ARC current posture | Gap |
|---|---|---|
| Durable / resumable execution | Per-run JSONL, run receipts, replay CLI | No explicit checkpointing or resume boundaries in the protocol |
| MCP as governed tool fabric | Local stdio MCP, trust-gated | No manifest pinning, no registry, no risk scoring |
| Observability as typed spans | JSONL traces, HMAC chain, evals | No OTel spans; no policy feedback from traces |
| Multi-agent normalised around orchestration | SwarmGraph vendored, adapters present | No compiler from foreign workflows to SwarmGraph IR |
| Policy surfaces living with the code | `AGENTS.md` in repo, sandbox policy files | No workflow-level preflight linter |

---

## 6. Recommended next actions (ranked by readiness)

These are ordered by how much substrate already exists — smallest to largest implementation gap:

1. **Fix `SWARMGRAPH_FEATURE_LIST.md` status drift** — 1 hour. Mark discriminated TS unions and MCP server as shipped.

2. **`cli/policy.py` — workflow preflight command** (`arc policy preflight --workflow <id>`) — uses existing `security/enforcement.py` + vendored risk_assessment. Day-1 deliverable.

3. **`swarmgraph/policy_linter.py`** — wraps existing sandbox + risk files into a workflow-level linter with structured `PolicyReport` output. Week-1 deliverable.

4. **`mcp/registry.py` + `mcp/manifests.py`** — manifest hash pinning and drift detection on top of the existing MCP server. Week-1 deliverable.

5. **`evals/policy_recommend.py`** — aggregate golden-trace failures into policy suggestions. Week-2 deliverable.

6. **`swarmgraph/ir.py` + `swarmgraph/compiler.py`** — normalising compiler from adapter export metadata. Week-2 to Week-3 deliverable.

7. **Flight recorder** (`tracing/flight_recorder.py`) — bounded retention on top of existing JSONL store. Week-2 deliverable.

---

## 7. Verdict

The document's strategic framing is accurate: **ARC does not need reinvention, it needs a policy-control layer on top of its existing substrate.** The substrate is stronger than the document realised (especially on the security/sandbox side, which has since received a full H1–H9 hardening pass and Landlock detection). The TUI and provider setup — two major UX gaps the document implicitly flagged — have been shipped since the document was written.

The three highest-leverage next PRs are:

```
1. workflow-level policy linter (cli/policy.py + swarmgraph/policy_linter.py)
2. MCP manifest pinning (mcp/manifests.py + mcp/registry.py)  
3. eval → policy feedback loop (evals/policy_recommend.py)
```

All three have strong existing substrate and clear single-file entry points.
