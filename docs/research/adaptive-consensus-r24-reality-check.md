# R24 Adaptive Consensus Reality Check

Date: 2026-06-01

## Summary

R24 is already implemented in the SwarmGraph SDK package. The stale `docs/roadmap.md` R24 section said Not Started, while `docs/phases.md` Phase 31 correctly said Complete. This pass verified the implementation and corrected the roadmap instead of duplicating code.

## Research Notes

| Source | Link/query | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 | `Pydantic` resolve call for deterministic risk assessment models | Tool failed: `Invalid API key. Please check your API key. API keys should start with 'ctx7sk' prefix.` | Recorded blocker; used repo code plus web/Vercel sources. | High | Context7 key needs repair before future research-gated work. |
| Existing code | `python/packages/swarmgraph-sdk/swarmgraph/risk_assessment.py` | Deterministic prompt heuristic, 100 labeled fixtures, risk-to-protocol matrix, no LLM/network dependency already exist. | No implementation needed for base R24; roadmap was stale. | High | Heuristic nuance remains limited by keyword matching. |
| Existing code | `python/packages/swarmgraph-sdk/swarmgraph/adaptive_consensus.py` | Context-aware wrapper accepts workspace trust, file types, runtime, paid-call flag, keywords; returns worker count, HITL flag, anti-drift, cost estimate. | R24 deliverables are present in SDK package, not `src/agent_runtime_cockpit/swarmgraph`. | High | Runtime-wide mandatory confirmation for high/critical risk remains integration follow-up. |
| Existing CLI | `arc swarmgraph assess-risk --task "Delete production database." --json` | CLI returns `critical`, `bft_escrow`, `hitl_required=true`, `cost_estimate_tokens=5000`. | Confirms user-facing stable JSON risk explanation path. | High | Broader runtime entrypoints may not all consume the assessment before execution. |
| Existing tests | `tests/swarmgraph/test_adaptive_consensus.py`, `test_adaptive_consensus_hardening.py` | 56 tests cover 100-fixture accuracy, protocol mapping, override audit event, no LLM dependency, context escalation, raft/BFT/bft_escrow dispatch, metadata persistence. | Treat R24 as Baseline Complete and update roadmap truth. | High | Full suite still recommended after docs correction. |
| Vercel Grep | `class RiskAssessment(BaseModel)` | Public examples commonly model risk with typed Pydantic-ish schemas, risk score/level/factors/recommendations. | Current typed/frozen Pydantic model pattern is consistent. | Medium | Examples were generic, not consensus-specific. |
| Vercel Grep | `recommended_protocol` | Results were mostly non-AI networking/protocol recommendation examples; no strong consensus-specific pattern found. | No code change from Vercel examples. | Low | Search corpus did not reveal a better local pattern. |
| Web | https://en.wikipedia.org/wiki/Byzantine_fault | BFT addresses agreement under arbitrary/faulty actors; classic requirement discusses >3f participants and supermajority-style resilience. | Supports higher-risk mapping to BFT/BFT+escrow, but ARC's implementation remains a heuristic safety policy, not formal distributed BFT proof. | Medium | ARC worker consensus is local/offline, not a formal networked BFT system. |
| Web | https://martinfowler.com/articles/patterns-of-distributed-systems/consensus.html | Fetch returned 404. | Recorded failure; no consequence. | High | None. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| R24 next action | Correct stale roadmap, do not reimplement | Duplicate adaptive consensus, move directly to new code | Phase 31/code/tests already implement R24; duplicate code would create drift. | `docs/roadmap.md` | High |
| Confirmation wording | Mark high/critical `hitl_required=true` as real, runtime-wide blocking confirmation as follow-up | Claim complete runtime-wide confirmation | Tests prove assessment/CLI/HITL flag; they do not prove every runtime entrypoint blocks. | `docs/roadmap.md` | High |
| Research artifact | Add reality-check research note | No doc update | User asked research/scope; this records sources and why implementation was cancelled. | `docs/research/adaptive-consensus-r24-reality-check.md` | High |

## Verified Commands

```bash
cd python && uv run pytest tests/swarmgraph/test_adaptive_consensus.py tests/swarmgraph/test_adaptive_consensus_hardening.py -q
```

Result: 56 passed.

```bash
cd python && uv run arc swarmgraph assess-risk --task "Delete production database." --json
```

Result: `risk_level=critical`, `recommended_protocol=bft_escrow`, `hitl_required=true`, `cost_estimate_tokens=5000`.

## What Is Real

- Deterministic risk assessment with 100 labeled fixtures.
- Risk-to-protocol matrix: low→majority, medium→raft, high→bft, critical→bft_escrow.
- Context escalation for untrusted workspace, high-risk file types, production/staging runtime, and extra keywords.
- CLI JSON explanation surface.
- Override audit event in the local event bus.
- No LLM/network/provider dependency in the assessor.

## Not Claimed

- Formal distributed BFT safety proof.
- Runtime-wide mandatory confirmation at every high/critical execution entrypoint.
- Provider-backed adaptive consensus execution.
