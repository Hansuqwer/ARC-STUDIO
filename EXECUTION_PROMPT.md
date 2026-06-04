# ARC Studio + SwarmGraph — Full Execution Prompt

**Use this as the single prompt handed to the implementation agent (e.g. Codex, Claude Code, an internal engineer).**
Everything in this file is derived from `git clone --depth 1` of `Hansuqwer/arc-theia-studio` at HEAD `81ba4557` (2026-06-03), verified by direct `ls`, `grep`, and `wc -l` on 2026-06-04. Every file path and every line number cited is a real artifact in that tree.

---

## ROLE

You are a senior staff engineer implementing the ARC Studio + SwarmGraph "wire-and-enforce" sprint. You may use bash, Python, Pydantic, Typer, FastMCP, TypeScript, React, and Eclipse Theia. You may not call paid LLMs from production code; deterministic logic only for any security decision (CoSAI rule).

## NON-NEGOTIABLE CONSTRAINTS

1. **Local-first single-user.** Daemon binds 127.0.0.1; no inbound public HTTP.
2. **MCP stays stdio-first.** No streamable-HTTP server until 2026-07-28 RC + auth posture decision.
3. **Trust gates and paid-call gates always enforce.** `EnforcementContext` is the single source of truth; never bypass.
4. **No LLM in security decisions** (CoSAI). All risk re-scoring is regex/heuristic/pattern.
5. **Fail-closed.** Missing key, invalid signature, parse error → deny, not allow.
6. **Additive protocol only.** Add new typed events to the existing discriminated union; never rename, never remove, never reorder.
7. **No new framework adapters** in this sprint. Mastra, MAF, etc. are out of scope.
8. **No multi-tenant, no cloud, no marketplace, no generic chat/RAG UI.**
9. **Backwards-compatible.** Every new gate ships with an explicit opt-out (env var or CLI flag) for one release before becoming on-by-default.
10. **Honesty.** "Built" means a function exists and unit-tests pass; never claim test-pass without running `uv run pytest -q`.

## REPO REALITY (verified 2026-06-04 @ `81ba4557`)

Already built (do not rebuild — only wire/enforce):

| Subsystem | Verified files |
|---|---|
| Streaming audit verifier + HMAC | `python/src/agent_runtime_cockpit/audit/streaming_verifier.py` (469 LOC), `audit/hmac_chain.py` (124), `audit/key_manager.py` (121) |
| Typed RunEvent union | `python/src/agent_runtime_cockpit/protocol/typed_events.py` (958 LOC), `packages/arc-protocol-ts/src/run-events.ts` (496 LOC) |
| Typed denial events | `python/src/agent_runtime_cockpit/protocol/denial_events.py` (TrustDenied/PaidCallDenied/ShellDenied/NetworkDenied/PermissionDenied) |
| `EnforcementContext` | `python/src/agent_runtime_cockpit/security/context.py` (`EnforcementContext`, `DryRunAbort`, contextvars-backed get/set) |
| Trust + paid + shell + network enforcement | `python/src/agent_runtime_cockpit/security/enforcement.py` (525 LOC) |
| Workspace trust DB | `python/src/agent_runtime_cockpit/security/trust.py` (193 LOC; DB at `~/.arc/trusted-workspaces.json`) |
| MCP stdio server | `python/src/agent_runtime_cockpit/mcp/server.py` (739 LOC); `create_mcp_server()`, `_trusted()`, `_tool_result()`, 11 tools, 3 resources |
| MCP manifest pin + risk classifier | `python/src/agent_runtime_cockpit/mcp/manifests.py` (`McpToolRisk`, `ManifestStore.pin/load/check_drift`) |
| MCP server inventory | `python/src/agent_runtime_cockpit/mcp/registry.py` (`McpRegistryStore.register/approve_tool/block_tool/is_tool_approved/is_tool_blocked`) |
| Injection pattern scanner | `python/src/agent_runtime_cockpit/security/injection_patterns.py` (`scan`, `scan_structured`, `Severity.BLOCKED|DEGRADED`) |
| Capability Cards (models + signing + registry + builders) | `python/src/agent_runtime_cockpit/capabilities/{models,signing,registry,validation,hashing,from_ir,from_mcp,from_adapters,redaction,policy}.py` |
| Capability CLI | `python/src/agent_runtime_cockpit/cli/capabilities.py` (`generate`/`inspect`/`validate`/`diff`/`list`/`explain`/`sign`/`verify`/`generate-key`) |
| Consensus escrow | `python/packages/swarmgraph-sdk/swarmgraph/consensus_escrow.py` |
| Adaptive consensus | `python/packages/swarmgraph-sdk/swarmgraph/adaptive_consensus.py`, `risk_assessment.py` |
| Run diff (8 modes) | `python/src/agent_runtime_cockpit/run_diff/*.py` |
| Simulation engine | `python/src/agent_runtime_cockpit/simulation/simulator.py` (404 LOC) |
| SwarmGraph IR | `python/src/agent_runtime_cockpit/swarmgraph_ir/*.py` |
| Eval-to-policy *recommender* (loop not closed) | `python/src/agent_runtime_cockpit/evals/policy_recommend.py` (R1–R4 rules; emits `PolicyRecommendation`; saved at `.arc/evals/recommendations/`) |
| Flight Recorder | `python/src/agent_runtime_cockpit/flight_recorder/*.py` |
| Policy linter v1 (R1–R8) | `python/src/agent_runtime_cockpit/security/policy_linter.py` (307 LOC) |
| Profile system | `python/src/agent_runtime_cockpit/security/profiles.py` (`RunProfile`, `BUILTIN_PROFILES`, `load_custom_profiles`, `save_custom_profile`, `resolve_profile_strict`) |
| Observability/OTel/OpenInference scaffolding | `python/src/agent_runtime_cockpit/observability/{otel_mapping,openinference_mapping,otlp_exporter,exporters,mcp_drift,redaction,validation}.py` |
| Theia UI shell | `packages/arc-extension/src/browser/tabs/{AssuranceTab,ChatTab,ConfigTab,McpWorkbenchTab,RunsTab,SwarmGraphInsightTab,WorkflowsTab,...}.tsx`; backend at `packages/arc-extension/src/node/arc-backend-service.ts` |
| ArcService.getAuditChainInfo | `packages/arc-extension/src/node/arc-backend-service.ts` lines ~562-630, invokes `arc audit verify <runId> --chain <auditPath> --json` via `execFileSync` |
| CLI app composition | `python/src/agent_runtime_cockpit/cli/_app.py` and `cli/_subapps.py` (`capabilities_app`, `mcp_app`, `mcp_workbench_app`, `flight_app`, `obs_app`, `audit_app`, ...) |

Genuinely absent (build these):

| Gap | Verification |
|---|---|
| `capabilities/enforcement.py` runtime gate (refuse on invalid signature / insufficient audit_level / unmet HITL/trust) | `grep -rn "CapabilityCard\b" python/src/agent_runtime_cockpit | grep -v "/capabilities/" | grep -v "/cli/capabilities"` → only adapter `capabilities.py` *producers* — zero gate consumers |
| Outbound MCP per-call risk gate | `mcp/manifests.py` *scores*; `cli/mcp.py` *inspects*; no per-call enforcement on ARC's MCP client or proxy |
| AGENTS.md / SKILL.md workspace ingestion | `grep -rln "AGENTS\.md" python/src/agent_runtime_cockpit` → 0 |
| A2A AgentCard + local-loopback client | `find python/src packages -iname "*a2a*"` → 0 |
| Eval-to-Policy *apply* loop closure | `policy_recommend.py` produces objects; nothing maps them onto `RunProfile` and writes versioned profiles |
| Streaming verifier wired into Assurance tab via stable `{ok, mode, records_checked, reason, duration_ms}` contract | `arc-backend-service.ts` shells out to CLI but does not yet surface streaming `mode`/`records_checked`/`duration_ms` fields |

## OUTPUT FORMAT YOU MUST PRODUCE

For each work item below, you will:
1. Create the listed files exactly.
2. Add tests at the listed paths.
3. Make all listed edits with surgical diffs.
4. Run the listed verification commands locally and paste their output into the PR description.
5. Commit each work item as its own PR with the title shown. Do not bundle.
6. Update `docs/roadmap.md` with a new Status row (format the file already uses).
7. Update `CHANGELOG.md` `[Unreleased]` section under Added/Changed/Security.
8. Add an ADR if listed.

If any step fails locally, STOP, paste the failure, and request guidance. Do not "fix and continue silently."

---

# THE PLAN (7 work items, in order; nothing deferred)

Work items must be implemented in the order below. Each item lists files-to-create, files-to-edit (with the exact section to edit), CLI shape, MCP integration, security model, tests, and verification commands. Sequence matters because Items 1→2→3→4→5→6→7 each depend on the prior item's wiring.

Effort assumes a single experienced contributor. Multiply by 1.4 for typical review/cycle overhead.

---

## ITEM 1 — Capability Card Enforcement Gate (P0, ~2 days)

**PR title:** `feat(capabilities): runtime enforcement gate for signed Capability Cards`
**Branch:** `feat/capability-card-enforcement`
**Why first:** every upstream piece is built; this is the smallest wire that turns decorative cards into a runtime trust gate. Items 2, 5, and 7 reuse the denial event from this item.

### Files to create

1. **`python/src/agent_runtime_cockpit/capabilities/enforcement.py`** — new module. Public API:
    ```python
    from __future__ import annotations
    from dataclasses import dataclass
    from enum import Enum
    from typing import Literal, Optional
    from pathlib import Path

    from .models import CapabilityCard, AuditLevel, TrustLevel, HitlRequirement
    from .signing import SignedCapabilityCard, verify_card
    from .registry import CardRegistry
    from ..security.context import EnforcementContext, get_enforcement_context

    Decision = Literal["allow", "deny", "warn"]

    class DenialReason(str, Enum):
        SIGNATURE_INVALID = "capability_card_signature_invalid"
        SIGNATURE_MISSING = "capability_card_signature_missing"
        TRUST_LEVEL_REQUIRED = "capability_card_trust_level_required"
        PAID_CALL_NOT_ALLOWED = "capability_card_paid_call_not_allowed"
        AUDIT_LEVEL_INSUFFICIENT = "capability_card_audit_level_insufficient"
        HITL_REQUIRED = "capability_card_hitl_required"
        CARD_NOT_FOUND = "capability_card_not_found"
        CARD_OPAQUE = "capability_card_opaque"
        REQUIRES_REVIEW = "capability_card_requires_review"
        SCHEMA_VERSION_UNSUPPORTED = "capability_card_schema_version_unsupported"

    @dataclass(frozen=True)
    class EnforcementResult:
        decision: Decision
        reason: str  # DenialReason value or "ok"
        card_id: Optional[str]
        card_hash: Optional[str]
        correlation_id: str
        details: dict  # safe-to-serialize structured detail

    # Strict mode: missing card or unsigned card from untrusted workspace → deny.
    # Permissive: warn, allow.
    Mode = Literal["off", "warn", "strict"]

    def resolve_mode(env: dict | None = None, cli_override: Optional[Mode] = None) -> Mode: ...

    def enforce_card(
        *,
        card: Optional[CapabilityCard],
        signed: Optional[SignedCapabilityCard],
        ctx: Optional[EnforcementContext] = None,
        mode: Mode = "warn",
        verifier_secret_key: Optional[str] = None,
        verifier_public_key_pem: Optional[str] = None,
        current_audit_mode: Literal["sha256", "hmac"] = "sha256",
        run_has_hitl_gate: bool = False,
    ) -> EnforcementResult: ...

    def enforce_card_by_id(
        *,
        card_id: str,
        registry: CardRegistry,
        ctx: Optional[EnforcementContext] = None,
        mode: Mode = "warn",
        verifier_secret_key: Optional[str] = None,
        verifier_public_key_pem: Optional[str] = None,
        current_audit_mode: Literal["sha256", "hmac"] = "sha256",
        run_has_hitl_gate: bool = False,
    ) -> EnforcementResult: ...
    ```

    Decision rules (deterministic; evaluate in this order; first failing rule wins):
    - If `mode == "off"` → always `allow`.
    - If `card is None and signed is None`:
        - `mode == "strict"` → deny `CARD_NOT_FOUND`.
        - `mode == "warn"` → warn `CARD_NOT_FOUND`.
    - If `card.schema_version != CARD_SCHEMA_VERSION` → deny `SCHEMA_VERSION_UNSUPPORTED`.
    - If `card.opaque or card.requires_review` → deny in strict, warn in warn.
    - If `signed is not None`: call `verify_card(signed, secret_key=..., public_key_pem=...)`. If `False` → deny `SIGNATURE_INVALID`. If verifier inputs missing → deny `SIGNATURE_MISSING` (strict) / warn (warn).
    - If `signed is None and mode == "strict"` → deny `SIGNATURE_MISSING`.
    - If `card.trust.trust_level == TrustLevel.PRIVILEGED` and `ctx.trust_workspace is False` → deny `TRUST_LEVEL_REQUIRED`.
    - If `(card.capabilities.can_make_paid_calls or (card.cost and card.cost.paid_call_gate))` and `not ctx.allow_paid` → deny `PAID_CALL_NOT_ALLOWED`.
    - Audit level ordering: `NONE < ARC_SHA256 < SWARMGRAPH_HMAC < FULL`. Map `current_audit_mode="sha256"` → `ARC_SHA256`, `"hmac"` → `SWARMGRAPH_HMAC`. If `card.audit.audit_level > current` → deny `AUDIT_LEVEL_INSUFFICIENT`.
    - If `card.trust.hitl_requirement == HitlRequirement.BLOCKING and not run_has_hitl_gate` → deny `HITL_REQUIRED`.
    - Else → allow.

    Notes:
    - `EnforcementResult.correlation_id` reuses `EnforcementContext.generate_correlation_id()`.
    - Add `__all__` and update `capabilities/__init__.py` to re-export `enforce_card`, `enforce_card_by_id`, `EnforcementResult`, `DenialReason`, `Mode`, `resolve_mode`.

2. **`python/src/agent_runtime_cockpit/protocol/capability_card_events.py`** — new module, mirroring `denial_events.py` style. Exports:

    ```python
    class CapabilityCardDecisionData(BaseModel):
        action: str               # e.g. "run_workflow", "mcp_tool_dispatch", "swarmgraph_node_execute"
        decision: Literal["allow", "deny", "warn"]
        reason: str               # DenialReason value or "ok"
        card_id: str | None = None
        card_hash: str | None = None
        entity_type: str | None = None    # CapabilityCard.entity_type
        mode: Literal["off", "warn", "strict"]
        remediation: str = ""
        correlation_id: str | None = None
        details: dict[str, str] | None = None

    class CapabilityCardDecisionEvent(BaseModel):
        schema_version: int = 2
        type: Literal["CAPABILITY_CARD_DECISION"]
        timestamp: str
        run_id: str
        sequence: int
        data: CapabilityCardDecisionData
    ```

3. **`python/tests/capabilities/test_enforcement.py`** — at least these test cases (use the existing `minimal_card` / `full_card` fixtures from `python/tests/capabilities/conftest.py`):
    - `test_mode_off_always_allows`
    - `test_strict_mode_missing_card_denies`
    - `test_warn_mode_missing_card_warns`
    - `test_signed_card_valid_hmac_allows`
    - `test_signed_card_tampered_payload_denies_with_SIGNATURE_INVALID`
    - `test_signed_card_wrong_secret_denies`
    - `test_signed_card_invalid_ecdsa_denies`
    - `test_signed_card_missing_verifier_strict_denies` / `warn_warns`
    - `test_trust_level_privileged_without_workspace_trust_denies`
    - `test_paid_call_required_without_allow_paid_denies`
    - `test_audit_level_hmac_required_with_sha256_current_denies`
    - `test_audit_level_sha256_required_with_hmac_current_allows`
    - `test_hitl_blocking_without_gate_denies`
    - `test_opaque_card_strict_denies_warn_warns`
    - `test_requires_review_card_strict_denies`
    - `test_schema_version_mismatch_denies`
    - `test_correlation_id_is_12_hex` (regex `^[0-9a-f]{12}$`)
    - `test_enforce_card_by_id_uses_registry`
    - `test_enforce_card_by_id_card_not_found_strict_denies`
    - `test_decision_order_signature_before_audit_level` (regression)

4. **`python/tests/protocol/test_capability_card_events.py`** — schema-version assertion + JSON round-trip + denial-shape parity test for both Python and the (later) TS side.

5. **`docs/adr/026-capability-card-enforcement.md`** — ADR following the existing ADR-014 / ADR-019 voice. Sections: Status, Context, Decision, Consequences, Rollout (env flag → opt-in default → opt-out), Compatibility, References (`CAPABILITY_CARD_DECISION` schema location, `EnforcementContext` reuse).

### Files to edit

6. **`python/src/agent_runtime_cockpit/capabilities/__init__.py`** — add the three exports (`enforce_card`, `enforce_card_by_id`, `EnforcementResult`, `DenialReason`, `Mode`, `resolve_mode`).

7. **`python/src/agent_runtime_cockpit/protocol/typed_events.py`** — add `CapabilityCardDecisionEvent` to `KnownRunEvent`, to the `is_known_event` known-types set, and to the `parse_typed_event` `type_map`. Use the import `from .capability_card_events import CapabilityCardDecisionEvent`.

8. **`packages/arc-protocol-ts/src/run-events.ts`** — add (mirroring the Python shape; additive only):

    ```ts
    export interface CapabilityCardDecisionEvent extends RunEventBase {
      type: 'CAPABILITY_CARD_DECISION';
      data: {
        action: string;
        decision: 'allow' | 'deny' | 'warn';
        reason: string;
        card_id?: string;
        card_hash?: string;
        entity_type?: string;
        mode: 'off' | 'warn' | 'strict';
        remediation?: string;
        correlation_id?: string;
        details?: Record<string, string>;
      };
    }
    ```
    Append `CapabilityCardDecisionEvent` to `KnownRunEvent` and `'CAPABILITY_CARD_DECISION'` to `KNOWN_RUN_EVENT_TYPES`. Add a sibling `run-events.test.ts` case asserting parse round-trip.

9. **`protocol/fixtures/run-event-registry.json`** — add a registry row for `CAPABILITY_CARD_DECISION` with both `allow` and `deny` example fixtures. Add the corresponding files under `protocol/fixtures/run-event/`. Follow the existing pattern (the same directory already contains other typed-event fixtures).

10. **`python/src/agent_runtime_cockpit/adapters/base.py`** — extend `RuntimeAdapter` with a non-abstract helper (do **not** add it to the abstract method list; this avoids breaking the 13 existing adapters):

    ```python
    async def enforce_capability_card(
        self,
        *,
        workflow_id: str,
        run_id: str,
        sequence: int,
        workspace: Path,
        emit_event: Callable[[str, str, dict], None] | None = None,
    ) -> EnforcementResult:
        """Default: look up adapter-level card via CardRegistry.
        Subclasses may override to enforce per-node IR cards."""
        ...
    ```
    Implementation:
    - Build a deterministic adapter card via `card_from_adapter(self, workspace, ...)` if no signed card exists in registry; consult `CardRegistry(workspace).load(adapter_card_id)` and `.../<adapter>_signed.json` on disk.
    - Call `capabilities.enforcement.enforce_card`.
    - Emit a `CAPABILITY_CARD_DECISION` event via `emit_event`.
    - If `decision == "deny"` raise a new `CapabilityEnforcementError(EnforcementError)` (subclass of existing `EnforcementError` in `security/enforcement.py`).
    - `mode` resolution order: `ctx.dry_run` → `"strict"`; env `ARC_CAPABILITIES_ENFORCE` (`off|warn|strict`, default `warn`); CLI flag `--enforce-cards` / `--no-enforce-cards`.

11. **`python/src/agent_runtime_cockpit/adapters/swarmgraph.py`** — at the top of `async def run_workflow` (line 310), call `await self.enforce_capability_card(...)` before the existing `if os.environ.get("ARC_SWARMGRAPH_CLI"): ...` branch. Wire the event into the existing `events: list[RunEvent]` accumulator by appending using `self._event(run_id, sequence, "CAPABILITY_CARD_DECISION", data)`.

12. **`python/src/agent_runtime_cockpit/adapters/langgraph.py`** — same call at the top of `async def run_workflow` (line 174) before the `if importlib.util.find_spec("langgraph") is None:` check.

13. **`python/src/agent_runtime_cockpit/mcp/server.py`** — extend `_tool_result` (line 146): after `_trusted()` succeeds, look up an `McpCapability`-typed card for `(server_id="arc-local", tool_name=<tool_name>)` via `CardRegistry(ws)` and call `enforce_card`. Wire the event into `_persist_mcp_audit_event` with `type="capability_card_decision"`. Reuse the existing `_redacted_json_envelope` for output.

14. **`python/packages/swarmgraph-sdk/swarmgraph/runner.py`** — add a single optional pre-step hook in `SwarmGraphRunner`:
    ```python
    self._pre_node_hook: Callable[[NodeContext], None] | None = None
    ```
    invoked before each worker `process_worker_results`. ARC's adapter wires the hook to call `enforce_card_by_id` for the per-node card id `f"ir-node::{node_id}"`. Hook absence = no-op; SDK still ships standalone.

15. **`python/src/agent_runtime_cockpit/cli/capabilities.py`** — add three commands:
    - `arc capabilities verify-run <run-id> [--workspace .] [--mode warn|strict|off] [--secret KEY|--public-key PATH]` — loads the run's known cards from `CardRegistry` and runs `enforce_card` on each. Exits `0=allow`, `2=warn`, `3=deny`. JSON output uses the existing `_out` + `ok/err` helpers.
    - `arc capabilities enforce-mode [--set off|warn|strict]` — read/write the local `.arc/capabilities/enforce-mode` file (one line).
    - Extend `arc capabilities verify` with `--mode warn|strict|off` to drive `enforce_card` (today it only checks signature; extend to full enforcement).

16. **`python/src/agent_runtime_cockpit/cli/_app.py`** — add an `--enforce-cards` / `--no-enforce-cards` global option to the root callback that sets `EnforcementContext.copy_with(...)` with the resolved mode stored in a new `EnforcementContext.cards_mode` field. To avoid breaking the frozen dataclass, switch storage to a module-level `_cards_mode: ContextVar[str]` in `security/context.py` and add `get_cards_mode()` / `set_cards_mode()` accessors. Tests must pass with default `warn`.

17. **`packages/arc-extension/src/common/arc-protocol.ts`** — add:
    ```ts
    export interface CapabilityCardDecision {
        action: string;
        decision: 'allow' | 'deny' | 'warn';
        reason: string;
        cardId?: string;
        cardHash?: string;
        entityType?: string;
        mode: 'off' | 'warn' | 'strict';
        correlationId?: string;
        remediation?: string;
    }
    export interface CapabilityCardSummary {
        runId: string;
        decisions: CapabilityCardDecision[];
        mode: 'off' | 'warn' | 'strict';
    }
    export interface ArcService {
        // existing methods …
        getCapabilityCardSummary(runId: string): Promise<CapabilityCardSummary>;
    }
    ```

18. **`packages/arc-extension/src/node/arc-backend-service.ts`** — implement `getCapabilityCardSummary` via `execFileSync('arc', ['capabilities', 'verify-run', runId, '--json'], ...)` mirroring the existing `getAuditChainInfo` pattern (~line 562). Add a `BackendServiceTestHarness` test like the existing audit tests.

19. **`packages/arc-extension/src/browser/tabs/AssuranceTab.tsx`** — add a new `<section className='arc-studio-assurance__cards'>` rendering `decisions[]`. Use the existing `auditStateCopy` pattern (info/success/warning variants). Add a button `Verify Capability Cards` next to `Verify Audit`. Reuse existing styles.

### Verification commands (run locally before opening PR)

```bash
cd python
uv sync --all-extras --dev
uv run ruff check src/agent_runtime_cockpit/capabilities src/agent_runtime_cockpit/protocol/capability_card_events.py tests/capabilities tests/protocol
uv run mypy src/agent_runtime_cockpit/capabilities src/agent_runtime_cockpit/protocol/capability_card_events.py
uv run pytest tests/capabilities -q
uv run pytest tests/protocol -q
uv run pytest tests/security -q
uv run pytest tests/adapters/test_base.py tests/adapters/test_swarmgraph.py tests/adapters/test_langgraph.py tests/mcp -q
# Quick smoke
uv run arc capabilities --help
uv run arc capabilities verify-run nonexistent --mode warn --json   # must exit 0 with warn payload
uv run arc capabilities enforce-mode --set strict
cd ..
pnpm install --frozen-lockfile
pnpm --filter arc-protocol-ts test
pnpm --filter arc-extension test
pnpm build
pnpm typecheck
pnpm check:pr
```

### CHANGELOG entry

```
### Added
- Capability Card runtime enforcement gate (ADR-026): refuses execution at adapter, MCP-tool, and SwarmGraph-node boundaries when signed cards are invalid or declared trust/audit/HITL/paid requirements are unmet.
- `CAPABILITY_CARD_DECISION` typed RunEvent (Python + TypeScript discriminated union; additive).
- `arc capabilities verify-run`, `arc capabilities enforce-mode`, and `--enforce-cards/--no-enforce-cards` global flag.
- Assurance tab "Capability Cards" section with allow/warn/deny rendering.

### Security
- Cards are fail-closed on invalid signature, missing verifier inputs (strict), and schema-version mismatch.
```

### Risks + mitigations

| Risk | Mitigation |
|---|---|
| Existing adapters break because card production isn't wired everywhere | Default mode is `warn`; `CARD_NOT_FOUND` emits warning only |
| `EnforcementContext` is a frozen dataclass; adding `cards_mode` is breaking | Use a separate `ContextVar` (`_cards_mode`) with `get_cards_mode/set_cards_mode`; do not touch the frozen class |
| `mcp/server.py` per-tool overhead | Card lookup is in-process file read; cap with an LRU cache `functools.lru_cache(maxsize=128)` keyed on `(server_id, tool_name)` |
| Per-node hook in SwarmGraph SDK adds dep | Hook is optional; SDK still installable standalone |

---

## ITEM 2 — MCP Outbound Per-Call Risk Gate (P0/P1, ~3 days)

**PR title:** `feat(mcp): outbound per-call risk gate + stdio↔stdio proxy + ledger`
**Branch:** `feat/mcp-outbound-risk-gate`
**Depends on:** Item 1's `CAPABILITY_CARD_DECISION` denial taxonomy (we reuse the same envelope shape).

### Files to create

1. **`python/src/agent_runtime_cockpit/mcp/risk.py`** — pure scoring; LLM-free.
    ```python
    @dataclass(frozen=True)
    class CallRiskAssessment:
        score: Literal["low", "medium", "high", "critical"]
        risk_signals: list[str]      # e.g. ["mcp:can_write", "injection:tool_hijacking", "fs:outside_roots"]
        injection_severity: Literal["none", "degraded", "blocked"]
        drift: Literal["pinned_match", "pinned_drift", "unpinned"]
        manifest_risk: Literal["low", "medium", "high"]
        roots_violation: bool
        details: dict

    def assess_call(
        *,
        server_id: str,
        tool_name: str,
        args: dict,
        workspace: Path,
        manifest_store: ManifestStore | None = None,
        registry: McpRegistryStore | None = None,
    ) -> CallRiskAssessment: ...
    ```
    Score table (deterministic; first match wins):
    - `critical` if `injection_severity == "blocked"` AND `manifest_risk == "high"`.
    - `critical` if `roots_violation` AND `manifest_risk in {"medium", "high"}`.
    - `high` if `manifest_risk == "high"` OR `injection_severity == "blocked"`.
    - `medium` if `manifest_risk == "medium"` OR `injection_severity == "degraded"` OR `drift == "pinned_drift"`.
    - `low` otherwise.
    Pull manifest risk via `manifest_store.load(server_id)` and match `tool_name` against `tool_risks`. Pull approve/block state via `registry.is_tool_approved/blocked(server_id, tool_name)`. Roots check via existing `workspace.iter_workspace_files` semantics (reuse helpers in `security/sandbox.py`'s path resolution).

2. **`python/src/agent_runtime_cockpit/mcp/sandbox.py`** — policy decision combining risk + user policy.
    ```python
    class Policy(str, Enum):
        AUTO_LOW = "auto_low"     # auto-approve low, prompt medium+, block high/critical
        AUTO_MEDIUM = "auto_medium"  # auto-approve low+medium, prompt high, block critical
        STRICT = "strict"         # auto-approve low, prompt medium, block high/critical (default)

    @dataclass(frozen=True)
    class CallDecision:
        decision: Literal["allow", "block", "require_approval"]
        risk: CallRiskAssessment
        policy: Policy
        correlation_id: str
        reason: str

    def decide(
        *,
        risk: CallRiskAssessment,
        policy: Policy = Policy.STRICT,
        explicit_allow: bool = False,    # for replay / pre-approved tool
    ) -> CallDecision: ...
    ```
    Audit-chain integration: every decision appended to `.arc/mcp/decisions.jsonl` (one JSON line per decision, UTC ISO timestamp, includes `correlation_id`).

3. **`python/src/agent_runtime_cockpit/mcp/proxy.py`** — stdio↔stdio proxy. Use `asyncio` + `anyio` (already imported in `cli/mcp.py`). Public entry: `async def run_proxy(upstream_cmd: list[str], *, workspace: Path, policy: Policy, decision_writer: DecisionWriter) -> int`. Behaviour:
    - Spawn upstream MCP server with `SubprocessIsolationProvider` (reuse existing pattern from `cli/mcp.py`).
    - Forward all `initialize` and `tools/list` calls unmodified. On `tools/list` response, also pin via `ManifestStore.pin(server_id, tools)` and refresh `McpRegistryStore`.
    - On `tools/call`: call `assess_call` then `decide`. If `allow`, forward and emit `MCP_CALL_ALLOWED` event. If `block`, return JSON-RPC error and emit `MCP_CALL_DENIED`. If `require_approval`, return a structured "pending" envelope and emit `MCP_CALL_PENDING_APPROVAL`.
    - Bounded 1 MB output cap (reuse `_MAX_MCP_OUTPUT_BYTES = 1_048_576` from `server.py`).

4. **`python/src/agent_runtime_cockpit/protocol/mcp_decision_events.py`** — typed event:
    ```python
    class McpCallDecisionData(BaseModel):
        server_id: str
        tool_name: str
        decision: Literal["allow", "block", "require_approval"]
        risk_score: Literal["low", "medium", "high", "critical"]
        risk_signals: list[str]
        policy: Literal["auto_low", "auto_medium", "strict"]
        injection_severity: Literal["none", "degraded", "blocked"]
        drift: Literal["pinned_match", "pinned_drift", "unpinned"]
        manifest_risk: Literal["low", "medium", "high"]
        correlation_id: str | None = None
        remediation: str = ""
        args_hash: str | None = None      # never raw args

    class McpCallDecisionEvent(BaseModel):
        schema_version: int = 2
        type: Literal["MCP_CALL_DECISION"]
        timestamp: str
        run_id: str
        sequence: int
        data: McpCallDecisionData
    ```
    Add to `protocol/typed_events.py` `KnownRunEvent`, `is_known_event`, `parse_typed_event`. Add TS mirror to `packages/arc-protocol-ts/src/run-events.ts`.

5. **Tests:**
    - `python/tests/mcp/test_risk.py` — score table coverage (≥20 cases including labeled-fixture poisoned-tool corpus). Include fixture for the public OWASP MCP poisoned-tool examples (test data only, no live network calls).
    - `python/tests/mcp/test_sandbox.py` — decision matrix per policy.
    - `python/tests/mcp/test_proxy.py` — uses `pytest-asyncio` to spin up a fake upstream stdio server (`tests/mcp/_fake_upstream.py`) and assert allow/block/pending behaviour without real network.

### Files to edit

6. **`python/src/agent_runtime_cockpit/cli/mcp.py`** — add commands:
    - `arc mcp proxy --upstream <cmd ...> [--policy strict|auto_medium|auto_low] [--workspace .]` (stdio↔stdio; blocks until upstream exits or SIGINT).
    - `arc mcp risk scan <server-id> [--json]` (LLM-free; uses `assess_call` against a synthetic empty-args probe per tool; warns on >50 ms total).
    - `arc mcp decisions list [--since TIME] [--limit N] [--json]` (tails `.arc/mcp/decisions.jsonl`).
    - `arc mcp policy explain <server-id> <tool-name> [--args JSON]` (dry-run scorer).

7. **`python/src/agent_runtime_cockpit/cli/_subapps.py`** — add `mcp_risk_app = typer.Typer(name="risk", help="MCP outbound call risk")`, `mcp_decisions_app = typer.Typer(name="decisions", ...)`, `mcp_policy_app = typer.Typer(name="policy", ...)`. Mount under `mcp_app.add_typer(...)`.

8. **`python/src/agent_runtime_cockpit/mcp/server.py`** — add per-call risk classification inside `_tool_result` (after Item 1's card enforcement). Tools ARC *itself* exposes are local, but classifying them gives the ledger a complete picture. Re-use Item 1's denial event shape; never silently bypass.

9. **`packages/arc-extension/src/browser/tabs/McpWorkbenchTab.tsx`** — add a `<section>` for "Recent MCP Decisions" with allow/block/pending colour coding (green/red/amber). Use existing `arcService` pattern. Add a backend method `getMcpDecisions(opts)` in `arc-protocol.ts` + `arc-backend-service.ts` invoking `arc mcp decisions list --json`.

10. **`packages/arc-protocol-ts/src/run-events.ts`** — add `McpCallDecisionEvent` to `KnownRunEvent` + `KNOWN_RUN_EVENT_TYPES`. Mirror Python.

### Verification

```bash
cd python
uv run ruff check src/agent_runtime_cockpit/mcp src/agent_runtime_cockpit/protocol/mcp_decision_events.py tests/mcp
uv run mypy src/agent_runtime_cockpit/mcp
uv run pytest tests/mcp -q
# stdio proxy smoke against the fake upstream
uv run pytest tests/mcp/test_proxy.py::test_allow_block_pending -q
uv run arc mcp risk scan example-server --json
uv run arc mcp policy explain example-server example_tool --args '{"x":1}' --json
uv run arc mcp decisions list --json
cd ..
pnpm --filter arc-protocol-ts test
pnpm --filter arc-extension test
pnpm build && pnpm typecheck && pnpm check:pr
```

### CHANGELOG

```
### Added
- MCP outbound per-call risk gate (LLM-free): `mcp/risk.py` + `mcp/sandbox.py` + `mcp/proxy.py`.
- `MCP_CALL_DECISION` typed event (Python + TS).
- CLI: `arc mcp proxy`, `arc mcp risk scan`, `arc mcp decisions list`, `arc mcp policy explain`.
- MCP Workbench: Recent MCP Decisions panel.
### Security
- Outbound MCP tool calls are deterministically classified (manifest risk × injection patterns × roots × drift) and blocked at "high" / "critical" by default policy "strict".
```

### Risks + mitigations

| Risk | Mitigation |
|---|---|
| Decision latency per call | < 5 ms target; in-process Pydantic only; LRU cache for manifest+registry lookups |
| Drift false positives on benign field reordering | `_hash_tools` already sorts by name; tested |
| Proxy hangs on misbehaving upstream | Inherit `SubprocessIsolationProvider` timeout (already enforced in `cli/mcp.py`) |

---

## ITEM 3 — AGENTS.md Workspace Ingestion + SKILL.md Catalog (P0, ~2-3 days)

**PR title:** `feat(workspace): AGENTS.md ingestion, pin + sign, drift, SKILL.md read-only catalog`
**Branch:** `feat/agents-md-ingestion`
**Depends on:** Item 1 (Capability Card signer reused; new EntityType added).

### Files to create

1. **`python/src/agent_runtime_cockpit/context/agents_md.py`** — discovery, hashing, nearest-wins, override.
    ```python
    @dataclass(frozen=True)
    class AgentsMdEntry:
        path: Path
        relative: str
        size_bytes: int
        sha256: str
        is_override: bool         # True if filename is AGENTS.override.md
        suspected_llm_generated: bool
        size_warning: bool        # >32_768 (Codex cap)

    def discover(root: Path, *, max_depth: int = 10) -> list[AgentsMdEntry]: ...
    def nearest_for(path: Path, entries: list[AgentsMdEntry]) -> AgentsMdEntry | None: ...
    def detect_llm_generated(text: str) -> bool: ...   # deterministic heuristic only
    def pin(workspace: Path, entries: list[AgentsMdEntry]) -> Path: ...   # writes .arc/agents-md/index.json
    def load_pin(workspace: Path) -> list[AgentsMdEntry]: ...
    def check_drift(workspace: Path) -> dict: ...   # returns {drifted: bool, added: [...], removed: [...], changed: [...]}
    ```
    Excludes: `node_modules`, `.git`, `dist`, `build`, `coverage`, `.venv`, `__pycache__`, any path matching `.gitignore` (best-effort via `pathspec` if importable; else fixed list).
    LLM-generated heuristic (deterministic): combine four signals: emoji density >2%, repeated bullet phrasing ("Ensure", "Make sure", "Always" appear ≥6 times), Shannon-entropy-based stop-word ratio outside [0.3, 0.6], absence of project-specific identifiers (no occurrence of the workspace dir-name in body). Three of four → True. Document precisely in module docstring.

2. **`python/src/agent_runtime_cockpit/context/skill_md.py`** — read-only catalog only. Discovers `.claude/skills/<name>/SKILL.md` and any top-level `SKILL.md`. Parses YAML frontmatter (use `pyyaml` already in deps). Does **not** execute. Outputs `SkillEntry(name, path, description, allowed_tools, scripts)`.

3. **`python/src/agent_runtime_cockpit/cli/agents_md.py`** — new module mounted on a new `agents_app`.
    Commands: `arc agents-md list [--json]`, `arc agents-md pin`, `arc agents-md drift [--json]`, `arc agents-md explain <path>`, `arc agents-md sign --key <id>`, `arc skills list [--json]` (under same `agents_app` for simplicity).

4. **Tests**:
    - `python/tests/context/test_agents_md.py` — nearest-wins on a nested fixture (use `python/tests/fixtures/agents_md/{root,sub_a,sub_a/deep}/AGENTS.md`). Override-file priority. Size-cap detection at 32 KiB. LLM-heuristic on 6 labelled fixtures (3 hand-written, 3 LLM-shaped). Signed pin round-trip.
    - `python/tests/context/test_skill_md.py` — frontmatter parsing, allowed_tools surface, no execution path.

5. **Fixtures**: under `python/tests/fixtures/agents_md/` create at least:
    - `root/AGENTS.md` (5 KB, hand-shaped)
    - `root/AGENTS.override.md` (1 KB)
    - `root/sub_a/AGENTS.md`
    - `root/sub_a/deep/AGENTS.md`
    - `root/node_modules/AGENTS.md` (should be excluded)
    - `root/over_cap/AGENTS.md` (40 KB)
    - `root/llm_generated/AGENTS.md` (emoji-dense, repetitive)
    - `root/hand_written/AGENTS.md` (project-specific identifiers, sparse emoji)

### Files to edit

6. **`python/src/agent_runtime_cockpit/cli/_subapps.py`** — add `agents_app = typer.Typer(name="agents-md", help="AGENTS.md ingestion + SKILL.md catalog")` and `skills_app = typer.Typer(name="skills", ...)`.

7. **`python/src/agent_runtime_cockpit/cli/_app.py`** — `app.add_typer(agents_app); app.add_typer(skills_app)`. Import from new module.

8. **`python/src/agent_runtime_cockpit/capabilities/models.py`** — extend `EntityType` enum with `AGENTS_MD = "agents_md"` and `SKILL = "skill"`.

9. **`python/src/agent_runtime_cockpit/capabilities/from_adapters.py`** — leave alone. Instead add a new builder in **`python/src/agent_runtime_cockpit/capabilities/from_workspace.py`** (new file):
    ```python
    def card_from_agents_md(entry: AgentsMdEntry) -> CapabilityCard: ...
    def cards_from_agents_md(workspace: Path) -> list[CapabilityCard]: ...
    def card_from_skill(entry: SkillEntry) -> CapabilityCard: ...
    ```
    Cards are produced with `entity_type=EntityType.AGENTS_MD`, `audit.audit_level=AuditLevel.ARC_SHA256`, `trust.requires_workspace_trust=True`, `metadata={"sha256": entry.sha256, "size_bytes": ..., "is_override": ..., "suspected_llm_generated": ...}`.

10. **`python/src/agent_runtime_cockpit/capabilities/__init__.py`** — re-export `card_from_agents_md`, `cards_from_agents_md`, `card_from_skill`.

11. **`packages/arc-extension/src/browser/tabs/ConfigTab.tsx`** — add an "Agent Context" sub-section listing AGENTS.md entries with hash, size warning, override flag, LLM-heuristic flag, and Pin / Verify drift buttons. Backend method `getAgentsMdSummary()` in `arc-protocol.ts` + `arc-backend-service.ts` shelling out to `arc agents-md list --json`.

### Verification

```bash
cd python
uv run ruff check src/agent_runtime_cockpit/context src/agent_runtime_cockpit/cli/agents_md.py tests/context
uv run mypy src/agent_runtime_cockpit/context
uv run pytest tests/context -q
uv run arc agents-md list --json
uv run arc agents-md pin
uv run arc agents-md drift --json
uv run arc agents-md sign --key dev
uv run arc skills list --json
cd ..
pnpm --filter arc-extension test
pnpm build && pnpm typecheck && pnpm check:pr
```

### CHANGELOG

```
### Added
- AGENTS.md workspace ingestion: discovery (nearest-wins, override priority, exclusions), 32 KiB cap warning, deterministic LLM-generated heuristic, signed pin + drift detection (reuses Capability Card signer).
- SKILL.md read-only catalog (`arc skills list`).
- ConfigTab Agent Context section.
### Security
- AGENTS.md content is fail-closed: drift requires explicit re-pin before adapters may consume new content.
```

---

## ITEM 4 — Eval-to-Policy Auto-Apply Loop (P1, ~2 days)

**PR title:** `feat(evals): close eval-to-policy loop with append-only profile versioning`
**Branch:** `feat/eval-policy-loop`

### Files to create

1. **`python/src/agent_runtime_cockpit/evals/apply.py`** — maps `PolicyRecommendation.action` strings → `RunProfile` mutations. Append-only `.arc/profiles/<id>.v<n>.yaml`. Never overwrites builtin profiles. Returns a `ProfileApplyResult(new_path, diff_summary, correlation_id)`.

    Mapping table (initial; deterministic):
    | action | mutation |
    |---|---|
    | `add_consensus_check=majority_voting` | `extra.consensus="majority"` |
    | `add_hitl_checkpoint=before_completion` | `extra.require_hitl=True` |
    | `require_tool_approval=side_effect_tools` | `allow_shell=False`, `extra.require_tool_approval=True` |
    | `review_paid_call_gate=enabled` | `allow_paid_calls=False`, `extra.review_required=True` |

    Profiles support `extra: dict` via a new field added in step 4 below.

2. **Tests:**
    - `python/tests/evals/test_apply.py` — golden fixture: 5 failing `EvalResult`s → recommendation set → applied profile diff matches expected YAML. Dry-run default. Idempotence (apply twice → same `v<n>`, not `v<n+1>`).

### Files to edit

3. **`python/src/agent_runtime_cockpit/evals/policy_recommend.py`** — add a public `apply_to_profile(recommendation, profile_id, *, dry_run=True, workspace=None)` that calls `evals.apply.apply_recommendations(...)`.

4. **`python/src/agent_runtime_cockpit/security/profiles.py`** — add an optional `extra: dict[str, str] = field(default_factory=dict)` field on `RunProfile`. Migrate `_profile_to_json` to round-trip `extra`. Migrate `load_custom_profiles` to default `extra = item.get("extra", {})`. Schema-version bump: introduce `PROFILE_SCHEMA_VERSION = 2`; old files default to v1 with empty `extra`.

5. **`python/src/agent_runtime_cockpit/cli/eval.py`** (or wherever `eval_app` commands live — check `grep -n "@eval_app" python/src/agent_runtime_cockpit/cli/*.py`) — add:
    - `arc eval recommend --apply --profile <name> [--dry-run|--no-dry-run] [--json]`
    - Defaults to `--dry-run`; explicit `--no-dry-run` writes the new profile file.

6. **`python/src/agent_runtime_cockpit/protocol/typed_events.py`** — add `EVAL_POLICY_RECOMMENDED` and `EVAL_POLICY_APPLIED` typed events. TS mirror.

7. **`packages/arc-extension/src/browser/tabs/AssuranceTab.tsx`** — add a third sub-section "Eval Recommendations" with apply-as-profile button (calls a new backend method).

### Verification

```bash
cd python
uv run pytest tests/evals -q
uv run arc eval recommend --json
uv run arc eval recommend --apply --profile demo --dry-run --json
```

### CHANGELOG

```
### Added
- Eval-to-Policy auto-apply loop: maps PolicyRecommendation.action → RunProfile mutation; append-only versioned profile files at .arc/profiles/<id>.v<n>.yaml.
- `EVAL_POLICY_RECOMMENDED` and `EVAL_POLICY_APPLIED` typed events.
- `arc eval recommend --apply --profile <name>` (dry-run default).
- RunProfile.extra dict (PROFILE_SCHEMA_VERSION=2; v1 files auto-migrate).
```

---

## ITEM 5 — Streaming Verifier → IDE Assurance Tab + Daemon SSE (P1, ~1 day)

**PR title:** `feat(audit): wire streaming verifier into Assurance tab and daemon SSE`
**Branch:** `feat/streaming-verifier-ui`

### Files to edit

1. **`python/src/agent_runtime_cockpit/web/routes.py`** (currently has `audit_verified` SSE event at line ~1270 + stream at line 1283) — add new route `GET /api/audit/verify/{run_id}?mode=sha256|hmac|auto` returning the stable `VerificationResult` JSON `{ok, mode, records_checked, reason, duration_ms, file_size_bytes, peak_memory_mb}`. Implement using `StreamingAuditVerifier` directly (in-process; no subprocess). Add an SSE-side push of `audit_verified` after completion (route handler emits onto existing bus).

2. **`python/src/agent_runtime_cockpit/cli/audit.py`** — ensure `arc audit verify <run-id> --mode sha256|hmac|auto --json` returns the exact same JSON shape. If not already, refactor to use `StreamingAuditVerifier.verify_sha256/verify_hmac/auto` and emit `VerificationResult.model_dump_json()`.

3. **`packages/arc-extension/src/node/arc-backend-service.ts`** — replace the `execFileSync` in `getAuditChainInfo` (line ~562) with a `fetch('http://127.0.0.1:7777/api/audit/verify/' + runId + '?mode=auto')` call when daemon is up; fall back to the existing CLI subprocess. Surface the new `mode`, `records_checked`, `duration_ms` fields in the returned `AuditChainInfo`.

4. **`packages/arc-extension/src/common/arc-protocol.ts`** — extend `AuditChainInfo`:
    ```ts
    export interface AuditChainInfo {
        ok: boolean;
        mode?: 'sha256' | 'hmac';
        recordCount?: number;
        recordsChecked?: number;
        durationMs?: number;
        peakMemoryMb?: number;
        auditPath?: string;
        reason?: string;
    }
    ```

5. **`packages/arc-extension/src/browser/tabs/AssuranceTab.tsx`** — render `mode`, `recordsChecked`, `durationMs` in the audit panel. Update `auditStateCopy` to include "verified via streaming verifier (X records in Yms)" copy.

6. **Tests:**
    - `python/tests/web/test_audit_verify_route.py` — covers SHA-256 / HMAC / auto / tampered.
    - `packages/arc-extension/src/browser/__tests__/AssuranceTab.test.tsx` — render with new fields.

### Verification

```bash
cd python
uv run pytest tests/web/test_audit_verify_route.py tests/audit/test_streaming_verifier.py -q
uv run arc serve &
SERVE_PID=$!
sleep 1
curl -s http://127.0.0.1:7777/api/audit/verify/run-demo?mode=auto | python -m json.tool
kill $SERVE_PID
cd ..
pnpm --filter arc-extension test
pnpm build && pnpm typecheck
```

---

## ITEM 6 — A2A Local AgentCard Generator + Loopback Client (P2, ~3-5 days)

**PR title:** `feat(a2a): local AgentCard generator + loopback-only client for SwarmGraph workers`
**Branch:** `feat/a2a-local-client`

### Constraints

- **No inbound HTTP server.** ARC generates `agent-card.json` to disk only (file path is `.arc/a2a/agent-card.json`).
- Outbound client: only resolves Agent Cards from local files or `http://127.0.0.1:*` (loopback regex enforced).
- All outbound calls require the workspace to be trusted AND a per-card approval entry in `.arc/a2a/approved.json`.

### Files to create

1. **`python/src/agent_runtime_cockpit/a2a/__init__.py`**
2. **`python/src/agent_runtime_cockpit/a2a/models.py`** — Pydantic `AgentCard`, `AgentCardSkill`, `AgentCardCapability`, mirroring A2A spec v1.2 shape (`name`, `description`, `version`, `protocolVersion`, `url`, `provider.{name,url}`, `capabilities.{streaming,pushNotifications,...}`, `skills:[]`, `signature:{algorithm,signature,signer_id,public_key_pem}` (reuse Item 1's signer)).
3. **`python/src/agent_runtime_cockpit/a2a/generator.py`** — `generate_agent_card(workspace: Path, *, signer_secret: Optional[str], private_key_pem: Optional[str]) -> AgentCard` describing the local SwarmGraph runner's verifiable-consensus capability. Writes signed card to `.arc/a2a/agent-card.json`.
4. **`python/src/agent_runtime_cockpit/a2a/client.py`** — loopback-only outbound A2A client (httpx, sync + async). Signature verification mandatory; loopback regex `^http://127\.0\.0\.1:\d+(/|$)` for `url`. Honour per-card approval file.
5. **`python/src/agent_runtime_cockpit/cli/a2a.py`** — commands: `arc a2a generate [--workspace .]`, `arc a2a list`, `arc a2a verify <card-path>`, `arc a2a inspect <card-path>`, `arc a2a approve <card-id>`, `arc a2a invoke <card-path> <skill> [--input JSON] [--json]`.

### Files to edit

6. **`python/src/agent_runtime_cockpit/cli/_subapps.py`** — `a2a_app = typer.Typer(name="a2a", help="Agent-to-Agent (A2A) local AgentCard + loopback client")`.
7. **`python/src/agent_runtime_cockpit/cli/_app.py`** — register.
8. **`python/src/agent_runtime_cockpit/capabilities/models.py`** — add `EntityType.A2A_AGENT = "a2a_agent"`.

### Tests

- `python/tests/a2a/test_models.py` — round-trip + spec-conformance fixtures (use 3 sample cards inline; cite A2A v1.2 schema in module docstring).
- `python/tests/a2a/test_generator.py` — generator output is deterministic given fixed inputs.
- `python/tests/a2a/test_client.py` — loopback regex enforced; non-loopback URL refused; unsigned card refused; approval file required.

### Verification

```bash
cd python
uv run pytest tests/a2a -q
uv run arc a2a generate
uv run arc a2a verify .arc/a2a/agent-card.json --json
```

### CHANGELOG

```
### Added
- A2A v1.2 local AgentCard generator (file-only, no inbound HTTP) describing SwarmGraph verifiable-consensus capability.
- A2A loopback-only outbound client with mandatory signature verification + per-card approval.
- `arc a2a generate|list|verify|inspect|approve|invoke` CLI.
### Security
- Outbound A2A calls restricted to 127.0.0.1; non-loopback URLs are refused; unsigned cards are refused.
```

---

## ITEM 7 — OTel `gen_ai.*` Semconv Conformance + `openinference-instrumentation-mcp` Bridge (P1, ~2-3 days)

**PR title:** `feat(observability): GenAI semconv conformance audit + OpenInference MCP bridge`
**Branch:** `feat/otel-genai-semconv`

### Files to edit / verify

1. **`python/src/agent_runtime_cockpit/observability/otel_mapping.py`** — audit each emitted span against the current `gen_ai.*` semconv (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens / output_tokens`, `gen_ai.response.finish_reasons`, `gen_ai.agent.name`, `gen_ai.agent.description`, `gen_ai.tool.name`, `gen_ai.tool.description`). Add missing attributes; never log prompt/completion content by default (matches Uptrace + Datadog guidance).

2. **`python/src/agent_runtime_cockpit/observability/openinference_mapping.py`** — add `MCPContextPropagator` that:
    - On outbound MCP call, injects W3C `traceparent` into JSON-RPC `_meta` envelope (forward-compatible with MCP 2026-07-28 RC's `_meta` field).
    - On inbound MCP call, extracts `traceparent` from `_meta` and attaches as remote context.
    - Falls back gracefully when `_meta` absent (today's spec).

3. **`python/src/agent_runtime_cockpit/observability/otlp_exporter.py`** — add `arc obs export --format otlp --endpoint http://127.0.0.1:4318 [--dry-run]` end-to-end test against an in-process collector mock.

4. **`python/src/agent_runtime_cockpit/cli/obs.py`** — add `arc obs semconv-check [--json]` that validates the last N spans against the stable semconv set and exits non-zero on missing required attributes.

### Tests

- `python/tests/observability/test_genai_semconv.py` — every span emitted from `RunEvent` mapping includes the required attributes; missing attributes → test failure listing each.
- `python/tests/observability/test_mcp_propagator.py` — round-trip W3C `traceparent` through a synthetic JSON-RPC envelope.
- `python/tests/observability/test_otlp_export.py` — collector mock receives N spans.

### Verification

```bash
cd python
uv run pytest tests/observability -q
uv run arc obs semconv-check --json
uv run arc obs export --format otlp --dry-run --json
```

### CHANGELOG

```
### Added
- OTel GenAI semantic conventions (gen_ai.*) end-to-end conformance for RunEvent → span mapping.
- OpenInference MCP context propagator (W3C traceparent through MCP _meta envelope).
- `arc obs semconv-check` and end-to-end OTLP export smoke.
```

---

# CROSS-CUTTING REQUIREMENTS

For **every** PR above:

## Tests

- New code requires unit + (where applicable) integration tests in the listed paths.
- Coverage must not drop. Run `uv run pytest tests/ -q --cov=src/agent_runtime_cockpit --cov-report=term-missing` and paste delta into PR.
- TS: `pnpm --filter arc-protocol-ts test && pnpm --filter arc-extension test`.
- For any security-touching change include at least 2 adversarial tests (tampered signature, traversal attempt, fuzz arg) and document them under "Adversarial tests" in the PR description.

## Hygiene

```bash
cd python
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
cd ..
pnpm install --frozen-lockfile
pnpm build
pnpm typecheck
pnpm check:pr
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/roadmap.md docs/phases.md docs/release/checklist.md
```

## Docs

- Update `docs/roadmap.md` adding new Status rows. Use the existing format `Status: <Value> | Evidence: <commit/run/test anchor> | Notes: <one sentence>`.
- Update `docs/phases.md` only if adding a numbered phase (Item 1 = Phase 111 Capability Card Enforcement; Item 2 = Phase 112; etc. — verify the next free number).
- Update `CHANGELOG.md` `[Unreleased]` sections (Added/Changed/Security/Deprecated).
- Add an ADR for Item 1 (ADR-026), Item 2 (ADR-027), Item 6 (ADR-028). Items 3, 4, 5, 7 do not need an ADR.

## Commit hygiene

- One PR per work item; conventional-commit subject (`feat(...)`, `fix(...)`).
- Reference the issue draft from REPORT.md.
- Each PR must include a "Verification" section pasting actual local test output (no fabrications).
- If `pnpm install --frozen-lockfile` fails in CI but works locally, regenerate lockfile in a separate PR; do not silently bypass.

## Failure protocol

- If `uv sync` fails because of missing system deps (libpq, libcrypto, etc.) document the exact `apt-get`/`brew` command in the PR description and fix in `docs/DEVELOPMENT.md`.
- If a test fails, do not skip it with `@pytest.mark.skip`. Either fix the root cause or mark `@pytest.mark.xfail(strict=True, reason="...")` with a tracking issue.
- If a TypeScript build fails on Theia API drift, do not downgrade Theia. Open a separate fix PR.

---

# COMMON LANDMINES (from real repo inspection)

1. **`EnforcementContext` is a `@dataclass(frozen=True)`.** Do not add fields. Use a sibling `ContextVar` (as repo already does for `_enforcement_context`).
2. **The `swarmgraph` package name has a MetaPathFinder bridge** rewriting `agent_runtime_cockpit.swarmgraph.*`. Never put new code under that sub-package. Use `capabilities/`, `swarmgraph_ir/`, `simulation/`, or new top-level dirs.
3. **`@mcp.tool()` decorators in `mcp/server.py` are nested inside `create_mcp_server`.** New tools must follow the same `_trusted()` + `_tool_result(name, callback, args)` pattern. Do not bypass `_persist_mcp_audit_event`.
4. **`RuntimeAdapter.run_workflow` raises `NotImplementedError` by default** (line 155 of `adapters/base.py`). Card enforcement must be added as a **non-abstract** helper. Adapters that don't override it inherit it; tests must mock it for adapters that don't yet have a `card_from_adapter` producer wired.
5. **CLI sub-apps live in `cli/_subapps.py`, not `cli/_app.py`.** Add new typers there and register on `app` in `_app.py`. The `capabilities_app` Typer already exists at line 81 of `_subapps.py`.
6. **Typed events MUST be added in three places** (`KnownRunEvent` union, `is_known_event` set, `parse_typed_event` type_map) in `protocol/typed_events.py` AND mirrored in `packages/arc-protocol-ts/src/run-events.ts` (`KnownRunEvent` + `KNOWN_RUN_EVENT_TYPES`). Missing any one breaks tests.
7. **The legacy `RunEvent` type in `arc-protocol-types.ts` is intentionally separate** (see comment in `run-events.ts`). Do not replace; only extend.
8. **`auditStateCopy` and `auditState` patterns in `AssuranceTab.tsx`** are reused; new card section should mirror their `variant: 'info' | 'success' | 'warning'` shape so styling is free.
9. **`ManifestStore` writes to `.arc/mcp/pins/<server_id>.json`**. `McpRegistryStore` writes to `~/.arc/mcp/servers.json` (global). Item 2's `decisions.jsonl` goes to `.arc/mcp/decisions.jsonl` (workspace-local), not global, so secrets never leak across workspaces.
10. **The signed card secret_hash is recorded as SHA-256 of the secret**, not the secret itself (see `signing.py` line 198). Verification rejects when secret_hash differs — preserve this on every new code path.
11. **`StreamingAuditVerifier.verify_*` returns a `VerificationResult` Pydantic model**. The CLI must `.model_dump_json()` it, not hand-build a dict, to keep the contract stable.
12. **`SubprocessIsolationProvider`** is the project-blessed subprocess spawner. Do not call `subprocess.run`/`Popen` directly in new code; reuse it (Item 2 proxy depends on this).
13. **`scripts/check-banned-claims.sh`** scans for forbidden marketing phrases. Run it before committing.
14. **`pnpm-workspace.yaml` excludes legacy `theia-extensions/*`.** Do not edit those dirs.
15. **`extra="ignore"` on Pydantic models** is the repo's forward-compat convention — preserve when adding new fields to existing models.

---

# DELIVERY CHECKLIST (PR-by-PR)

For each PR, the assignee must paste this filled-in into the PR description:

```
- [ ] All new files match the paths in EXECUTION_PROMPT.md
- [ ] All edits made; no extra files
- [ ] ADR added (if listed)
- [ ] CHANGELOG.md [Unreleased] updated
- [ ] docs/roadmap.md Status row added
- [ ] uv run ruff check src tests          (paste output)
- [ ] uv run mypy src                       (paste output)
- [ ] uv run pytest <listed paths> -q       (paste output)
- [ ] pnpm build && pnpm typecheck          (paste output)
- [ ] pnpm check:pr                         (paste output)
- [ ] bash scripts/check-banned-claims.sh   (paste output)
- [ ] Adversarial tests included (list)
- [ ] Backward compatibility flag/env documented
- [ ] No public HTTP added; no LLM in security path; no frozen-dataclass mutation
```

---

# FINAL NOTE TO THE IMPLEMENTER

You are not building net-new exotic features. You are **closing wires** between subsystems that already exist, **adding enforcement** to subsystems that already classify, and **adopting three ecosystem standards** (Capability Card enforcement, AGENTS.md ingestion, A2A loopback client) that ARC is uniquely positioned to do *locally and signedly*.

If at any point you find yourself rewriting a subsystem from §"REPO REALITY", stop. The plan was wrong about its absence; verify with `grep`/`ls` against HEAD and adjust scope downward (treat as hardening) before continuing.

Begin with Item 1. Do not start Item 2 until Item 1's PR is merged or at least passing all tests locally — every later item depends on its denial event shape and `EnforcementContext` extensions.

**End of execution prompt.**
