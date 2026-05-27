"""Phase 51 / R24 — Adaptive Consensus Protocol.

Extended interface wrapping the Phase 31 deterministic risk assessor
(`risk_assessment.py`). Adds workspace-trust, file-type, runtime, paid-call,
and keyword context signals on top of the base prompt heuristic.

No LLM dependency. Deterministic and fail-closed (any error → critical).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .config import ConsensusProtocol
from .risk_assessment import (
    CONSENSUS_PROTOCOL_BY_RISK,
    RISK_FIXTURES,
    RiskAssessment,
    RiskFixture,
    RiskLevel,
    assess_prompt_risk,
)

__all__ = [
    "AdaptiveRiskAssessment",
    "assess_risk",
    "CONSENSUS_PROTOCOL_BY_RISK",
    "RISK_FIXTURES",
    "RiskAssessment",
    "RiskFixture",
    "RiskLevel",
    "ConsensusProtocol",
]

# ---------------------------------------------------------------------------
# File-type risk uplift
# ---------------------------------------------------------------------------

# File types that elevate risk by one level
_HIGH_RISK_FILE_TYPES: frozenset[str] = frozenset(
    {
        ".env",
        ".pem",
        ".key",
        ".cert",
        ".p12",
        ".pfx",
        "secrets.yaml",
        "secrets.yml",
        ".kube/config",
    }
)

_MEDIUM_RISK_FILE_TYPES: frozenset[str] = frozenset(
    {
        ".sql",
        ".db",
        ".sqlite",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Dockerfile",
        ".tf",
        ".tfvars",
    }
)

# Runtimes that require elevated caution (at least medium risk)
_ELEVATED_RUNTIME_FLOOR: frozenset[str] = frozenset({"production", "prod", "staging", "live"})

# ---------------------------------------------------------------------------
# Extended model
# ---------------------------------------------------------------------------


class AdaptiveRiskAssessment(BaseModel):
    """Extended risk assessment result including workspace and runtime context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_level: RiskLevel = Field(..., description="Determined risk level")
    recommended_protocol: ConsensusProtocol = Field(
        ..., description="Recommended consensus protocol"
    )
    worker_count: int = Field(default=3, ge=1, description="Recommended worker count")
    hitl_required: bool = Field(
        default=False, description="Whether human-in-the-loop approval is required"
    )
    anti_drift: bool = Field(
        default=False, description="Whether anti-drift checks should be enabled"
    )
    cost_estimate_tokens: Optional[int] = Field(
        default=None,
        description="Conservative token cost estimate (None = not estimated for this risk level)",
    )
    rationale: str = Field(default="", description="Human-readable risk rationale", max_length=4096)

    # Internal assessment for tracing
    base_assessment: RiskAssessment = Field(
        ..., description="Base prompt risk assessment from Phase 31 heuristic"
    )


# ---------------------------------------------------------------------------
# Worker count by risk level
# ---------------------------------------------------------------------------

_WORKER_COUNT: dict[RiskLevel, int] = {
    "low": 1,
    "medium": 3,
    "high": 5,
    "critical": 7,
}

_COST_ESTIMATE: dict[RiskLevel, Optional[int]] = {
    "low": None,
    "medium": 500,
    "high": 2000,
    "critical": 5000,
}


# ---------------------------------------------------------------------------
# Context-aware risk escalation
# ---------------------------------------------------------------------------


def _escalate(
    current: RiskLevel,
    *,
    workspace_trusted: bool,
    file_types: list[str],
    target_runtime: Optional[str],
    keywords: list[str],
) -> tuple[RiskLevel, list[str]]:
    """Apply context signals to potentially escalate base risk.

    Returns the (possibly elevated) risk level and a list of escalation reasons.
    Fail-closed: any error returns (critical, ["escalation_error"]).
    """
    reasons: list[str] = []

    _ORDER: list[RiskLevel] = ["low", "medium", "high", "critical"]

    def _floor(level: RiskLevel, new_level: RiskLevel, reason: str) -> RiskLevel:
        if _ORDER.index(new_level) > _ORDER.index(level):
            reasons.append(reason)
            return new_level
        return level

    risk = current

    # Untrusted workspace → floor at high
    if not workspace_trusted:
        risk = _floor(risk, "high", "workspace_untrusted")

    # High-risk file types → floor at high
    ft_lower = [ft.lower() for ft in (file_types or [])]
    for ft in ft_lower:
        for hrf in _HIGH_RISK_FILE_TYPES:
            if hrf in ft or ft.endswith(hrf):
                risk = _floor(risk, "high", f"high_risk_file_type:{ft}")
                break
        for mrf in _MEDIUM_RISK_FILE_TYPES:
            if mrf in ft or ft.endswith(mrf):
                risk = _floor(risk, "medium", f"medium_risk_file_type:{ft}")
                break

    # Production/staging runtime → floor at high
    rt = (target_runtime or "").lower()
    if any(r in rt for r in _ELEVATED_RUNTIME_FLOOR):
        risk = _floor(risk, "high", f"elevated_runtime:{target_runtime}")

    # Extra keywords
    joined_kw = " ".join(kw.lower() for kw in (keywords or []))
    if any(
        sig in joined_kw
        for sig in (
            "private key",
            "seed phrase",
            "production database",
            "drop database",
            "transfer funds",
            "disable mfa",
            "irreversible",
        )
    ):
        risk = _floor(risk, "critical", "keyword_critical_signal")
    elif any(
        sig in joined_kw
        for sig in ("secret", "token", "api key", "password", "credential", "sudo", "root access")
    ):
        risk = _floor(risk, "high", "keyword_high_signal")

    return risk, reasons


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assess_risk(
    task_text: str,
    workspace_trusted: bool = True,
    file_types: Optional[list[str]] = None,
    target_runtime: Optional[str] = None,
    paid_call_allowed: bool = False,
    keywords: Optional[list[str]] = None,
) -> AdaptiveRiskAssessment:
    """Assess risk for a task and return an AdaptiveRiskAssessment.

    Wraps the Phase 31 deterministic heuristic (`assess_prompt_risk`) and
    applies additional context signals: workspace trust, file types,
    target runtime, and extra keyword hints.

    Fail-closed: any exception results in a critical/bft_escrow assessment.

    Args:
        task_text: The task prompt to assess.
        workspace_trusted: Whether the workspace is trusted. Default True.
        file_types: List of file extension hints (e.g. ['.env', '.sql']).
        target_runtime: Runtime hint (e.g. 'production', 'staging').
        paid_call_allowed: Whether paid calls are allowed (not used for risk
            calculation; included for forward compatibility).
        keywords: Additional keyword hints for risk escalation.

    Returns:
        AdaptiveRiskAssessment with risk level, protocol, and context.

    """
    try:
        base = assess_prompt_risk(task_text)
        escalated_risk, escalation_reasons = _escalate(
            base.risk,
            workspace_trusted=workspace_trusted,
            file_types=file_types or [],
            target_runtime=target_runtime,
            keywords=keywords or [],
        )

        protocol = CONSENSUS_PROTOCOL_BY_RISK.get(escalated_risk, ConsensusProtocol.bft_escrow)
        worker_count = _WORKER_COUNT.get(escalated_risk, 3)
        hitl = escalated_risk in ("high", "critical")
        anti_drift = escalated_risk in ("high", "critical")
        cost = _COST_ESTIMATE.get(escalated_risk)

        rationale_parts = [base.rationale]
        if escalation_reasons:
            rationale_parts.append("Context escalation: " + ", ".join(escalation_reasons) + ".")
        if escalated_risk != base.risk:
            rationale_parts.append(
                f"Risk elevated from '{base.risk}' to '{escalated_risk}' by context signals."
            )
        rationale = " ".join(rationale_parts)

        return AdaptiveRiskAssessment(
            risk_level=escalated_risk,
            recommended_protocol=protocol,
            worker_count=worker_count,
            hitl_required=hitl,
            anti_drift=anti_drift,
            cost_estimate_tokens=cost,
            rationale=rationale,
            base_assessment=base,
        )
    except Exception as exc:  # noqa: BLE001
        base_err = RiskAssessment(
            risk="critical",
            score=100,
            matched_signals=["assessor_error"],
            rationale=f"Risk assessor failed with: {exc}; fail-closed to critical.",
        )
        return AdaptiveRiskAssessment(
            risk_level="critical",
            recommended_protocol=ConsensusProtocol.bft_escrow,
            worker_count=7,
            hitl_required=True,
            anti_drift=True,
            cost_estimate_tokens=5000,
            rationale=base_err.rationale,
            base_assessment=base_err,
        )
