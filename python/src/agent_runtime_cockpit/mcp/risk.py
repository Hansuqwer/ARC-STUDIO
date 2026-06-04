"""Pure deterministic MCP outbound call risk scorer (no LLM).

Score table:
- critical: injection_severity==blocked AND manifest_risk==high
- critical: roots_violation AND manifest_risk in {medium, high}
- high: manifest_risk==high OR injection_severity==blocked
- medium: manifest_risk==medium OR injection_severity==degraded OR drift==pinned_drift
- low: otherwise
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from ..security.injection_patterns import highest_severity, scan


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskSignals(BaseModel):
    """Collected signals for a single MCP call."""

    manifest_risk: str = "low"  # from McpToolRisk.risk_level
    injection_severity: str | None = None  # "blocked" | "degraded" | None
    roots_violation: bool = False
    drift: str | None = None  # "pinned_drift" | None


class RiskScore(BaseModel):
    """Final risk score for an MCP outbound call."""

    level: RiskLevel
    signals: RiskSignals
    reasons: list[str] = Field(default_factory=list)


def score_call(signals: RiskSignals) -> RiskScore:
    """Deterministic risk scoring from collected signals."""
    reasons: list[str] = []
    manifest = signals.manifest_risk
    inj = signals.injection_severity
    roots = signals.roots_violation
    drift = signals.drift

    # Critical: injection blocked + high manifest
    if inj == "blocked" and manifest == "high":
        reasons.append("injection_blocked+manifest_high")
        return RiskScore(level=RiskLevel.CRITICAL, signals=signals, reasons=reasons)

    # Critical: roots violation + medium/high manifest
    if roots and manifest in ("medium", "high"):
        reasons.append("roots_violation+manifest_risk")
        return RiskScore(level=RiskLevel.CRITICAL, signals=signals, reasons=reasons)

    # High: manifest high OR injection blocked
    if manifest == "high":
        reasons.append("manifest_high")
        return RiskScore(level=RiskLevel.HIGH, signals=signals, reasons=reasons)
    if inj == "blocked":
        reasons.append("injection_blocked")
        return RiskScore(level=RiskLevel.HIGH, signals=signals, reasons=reasons)

    # Medium: manifest medium OR injection degraded OR pinned_drift
    if manifest == "medium":
        reasons.append("manifest_medium")
        return RiskScore(level=RiskLevel.MEDIUM, signals=signals, reasons=reasons)
    if inj == "degraded":
        reasons.append("injection_degraded")
        return RiskScore(level=RiskLevel.MEDIUM, signals=signals, reasons=reasons)
    if drift == "pinned_drift":
        reasons.append("pinned_drift")
        return RiskScore(level=RiskLevel.MEDIUM, signals=signals, reasons=reasons)

    return RiskScore(level=RiskLevel.LOW, signals=signals, reasons=reasons)


def scan_call_arguments(arguments: dict[str, Any] | None) -> str | None:
    """Scan MCP call arguments for injection patterns. Returns severity or None."""
    if not arguments:
        return None
    text = " ".join(str(v) for v in arguments.values() if isinstance(v, str))
    detections = scan(text)
    sev = highest_severity(detections)
    return sev.value if sev else None
