"""Eval-to-policy feedback loop.

Aggregates failures from golden-trace eval runs and produces concrete
policy recommendations (stronger consensus, new HITL checkpoints, tool
gate changes).  Never auto-applies changes; always returns dry recommendations
the user can accept, reject, or save as a profile.

Usage:
    from agent_runtime_cockpit.evals.policy_recommend import recommend_policy
    results = [eval_run(record, golden) for record, golden in runs]
    report = recommend_policy(results)
    print(report.recommendations)
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from .golden import EvalResult


class PolicyRecommendation(BaseModel):
    """A single concrete policy suggestion derived from eval failures."""

    id: str
    confidence: float  # 0.0–1.0
    category: str  # "consensus" | "hitl" | "tool_gate" | "paid_call"
    title: str
    description: str
    action: str  # machine-readable, e.g. "set_consensus=majority_plus_hitl"
    supporting_run_ids: list[str] = Field(default_factory=list)


class PolicyRecommendationReport(BaseModel):
    """Set of recommendations produced from a batch of eval results."""

    total_runs: int
    failed_runs: int
    failure_rate: float
    recommendations: list[PolicyRecommendation] = Field(default_factory=list)

    @property
    def has_recommendations(self) -> bool:
        return bool(self.recommendations)


def recommend_policy(
    results: list[EvalResult],
    *,
    min_failure_rate: float = 0.2,
    min_sample: int = 3,
) -> PolicyRecommendationReport:
    """Analyse eval failures and return actionable policy recommendations.

    Args:
        results: List of EvalResult from eval_run().
        min_failure_rate: Only emit a recommendation if the failure rate for
            the relevant failure mode exceeds this threshold.
        min_sample: Minimum number of results required to emit anything.

    Returns:
        PolicyRecommendationReport with zero or more recommendations.
    """
    total = len(results)
    if total < min_sample:
        return PolicyRecommendationReport(
            total_runs=total,
            failed_runs=0,
            failure_rate=0.0,
        )

    failures = [r for r in results if not r.passed]
    failure_rate = len(failures) / total

    recs: list[PolicyRecommendation] = []
    rec_id = 0

    def _next_id() -> str:
        nonlocal rec_id
        rec_id += 1
        return f"rec-{rec_id:03d}"

    # ── R1: High overall failure rate → suggest stronger consensus ────────
    if failure_rate >= min_failure_rate:
        recs.append(
            PolicyRecommendation(
                id=_next_id(),
                confidence=min(1.0, failure_rate * 1.5),
                category="consensus",
                title="Increase consensus strength",
                description=(
                    f"{len(failures)}/{total} runs failed ({failure_rate:.0%}). "
                    "Switching to majority+HITL consensus for high-risk branches may improve reliability."
                ),
                action="set_consensus=majority_plus_hitl",
                supporting_run_ids=[r.run_id for r in failures],
            )
        )

    # ── R2: Status mismatches suggest missing HITL checkpoint ─────────────
    status_failures = [r for r in failures if not r.status_match]
    sf_rate = len(status_failures) / total
    if sf_rate >= min_failure_rate:
        recs.append(
            PolicyRecommendation(
                id=_next_id(),
                confidence=min(1.0, sf_rate * 2.0),
                category="hitl",
                title="Add HITL checkpoint before final action",
                description=(
                    f"{len(status_failures)}/{total} runs completed with wrong status. "
                    "A human approval gate before the final action could catch these failures."
                ),
                action="add_hitl_checkpoint=before_completion",
                supporting_run_ids=[r.run_id for r in status_failures],
            )
        )

    # ── R3: Event-type mismatches suggest tool gate tightening ────────────
    event_failures = [r for r in failures if not r.event_type_match]
    ef_rate = len(event_failures) / total
    if ef_rate >= min_failure_rate:
        recs.append(
            PolicyRecommendation(
                id=_next_id(),
                confidence=min(1.0, ef_rate * 1.8),
                category="tool_gate",
                title="Tighten tool execution gate",
                description=(
                    f"{len(event_failures)}/{total} runs had unexpected event types. "
                    "Consider requiring explicit approval for tool invocations that produce side effects."
                ),
                action="require_tool_approval=side_effect_tools",
                supporting_run_ids=[r.run_id for r in event_failures],
            )
        )

    # ── R4: High failure rate without status/event issues → paid-call gate ─
    unexplained = [r for r in failures if r.status_match and r.event_type_match and not r.passed]
    ue_rate = len(unexplained) / total
    if ue_rate >= min_failure_rate:
        recs.append(
            PolicyRecommendation(
                id=_next_id(),
                confidence=min(1.0, ue_rate * 1.2),
                category="paid_call",
                title="Review paid-call gate configuration",
                description=(
                    f"{len(unexplained)}/{total} runs failed despite correct status and events. "
                    "Output-quality failures often indicate unreliable model routing or missing paid-call guards."
                ),
                action="review_paid_call_gate=enabled",
                supporting_run_ids=[r.run_id for r in unexplained],
            )
        )

    # Sort by confidence descending
    recs.sort(key=lambda r: r.confidence, reverse=True)

    return PolicyRecommendationReport(
        total_runs=total,
        failed_runs=len(failures),
        failure_rate=round(failure_rate, 3),
        recommendations=recs,
    )


def save_recommendations(
    report: PolicyRecommendationReport,
    workspace: Path,
    run_id: str = "latest",
) -> Path:
    """Persist a recommendation report under .arc/evals/recommendations/."""

    d = workspace / ".arc" / "evals" / "recommendations"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{run_id}.json"
    p.write_text(report.model_dump_json(indent=2))
    return p
