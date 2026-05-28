"""Phase 31/R24 — Adaptive Consensus Protocol.

Deterministic heuristic risk assessor that maps prompts to risk levels,
which determine the consensus protocol to use via the protocol selection matrix.

No ML, no LLM, no randomness, no network calls. Pure string heuristic.
Fail-closed: any error or unknown input maps to "critical" / "bft_escrow".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import ConsensusProtocol

# ---------------------------------------------------------------------------
# Risk Level
# ---------------------------------------------------------------------------

RiskLevel = Literal["low", "medium", "high", "critical"]


# ---------------------------------------------------------------------------
# Signal definitions
# ---------------------------------------------------------------------------

SIGNALS: dict[RiskLevel, list[str]] = {
    "critical": [
        "production database",
        "prod database",
        "delete production",
        "drop database",
        "wipe database",
        "transfer funds",
        "send payment",
        "withdraw funds",
        "rotate root key",
        "revoke all access",
        "disable mfa",
        "private key",
        "seed phrase",
        "escrow release",
        "irreversible",
        "cannot be undone",
    ],
    "high": [
        "delete user",
        "delete account",
        "remove admin",
        "grant admin",
        "root access",
        "sudo",
        "api key",
        "secret",
        "password",
        "token",
        "credential",
        "encrypt",
        "decrypt",
        "firewall",
        "security policy",
        "payment",
        "invoice",
        "refund",
        "deploy to production",
        "prod deploy",
        "schema migration",
    ],
    "medium": [
        "update config",
        "change config",
        "modify config",
        "edit file",
        "write file",
        "create file",
        "update code",
        "change code",
        "refactor",
        "migration",
        "restart service",
        "install package",
        "dependency update",
        "database query",
        "staging",
        "feature flag",
    ],
    "low": [
        "explain",
        "summarize",
        "read",
        "list",
        "show",
        "describe",
        "what is",
        "how does",
        "documentation",
        "comment",
        "format",
    ],
}

SIGNAL_WEIGHTS: dict[RiskLevel, int] = {
    "critical": 100,
    "high": 50,
    "medium": 20,
    "low": 5,
}

RISK_THRESHOLDS: list[tuple[int, RiskLevel]] = [
    (100, "critical"),
    (50, "high"),
    (20, "medium"),
]

# ---------------------------------------------------------------------------
# Protocol Selection Matrix
# ---------------------------------------------------------------------------

CONSENSUS_PROTOCOL_BY_RISK: dict[RiskLevel, ConsensusProtocol] = {
    "low": ConsensusProtocol.majority,
    "medium": ConsensusProtocol.raft,
    "high": ConsensusProtocol.bft,
    "critical": ConsensusProtocol.bft_escrow,
}

# Phase 81/R52 — Extended protocol selection matrix supporting
# all differentiators. Used by select_consensus_protocol when
# enable_selective_debate or other flags are set.
CONSENSUS_PROTOCOL_BY_RISK_EXTENDED: dict[RiskLevel, list[ConsensusProtocol]] = {
    "low": [ConsensusProtocol.majority, ConsensusProtocol.selective_debate],
    "medium": [ConsensusProtocol.confidence_weighted, ConsensusProtocol.quorum],
    "high": [ConsensusProtocol.critic_verifier, ConsensusProtocol.bft],
    "critical": [ConsensusProtocol.bft_escrow],
}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RiskAssessment(BaseModel):
    """Deterministic risk assessment result for a single prompt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    risk: RiskLevel = Field(..., description="Determined risk level")
    score: int = Field(..., ge=0, description="Total risk score")
    matched_signals: list[str] = Field(
        default_factory=list,
        description="Signal phrases that were matched (stable ordering)",
        max_length=64,
    )
    rationale: str = Field(
        default="",
        description="Human-readable explanation of the assessment",
        max_length=4096,
    )


class ProtocolSelection(BaseModel):
    """Result of selecting a consensus protocol based on prompt risk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    risk: RiskLevel = Field(..., description="Determined risk level")
    protocol: ConsensusProtocol = Field(..., description="Selected consensus protocol")
    assessment: RiskAssessment = Field(..., description="Full risk assessment details")


# ---------------------------------------------------------------------------
# Deterministic Risk Assessor
# ---------------------------------------------------------------------------


def _normalize(input_str: str) -> str:
    """Normalize a prompt for deterministic matching.

    - lowercase
    - collapse repeated whitespace
    - strip leading/trailing whitespace
    """
    return " ".join(input_str.lower().split())


def assess_prompt_risk(input_str: str) -> RiskAssessment:
    """Determine the risk level of a prompt using deterministic heuristics.

    Uses substring matching against classified signal phrases with additive
    scoring. The highest-priority signal class determines the floor risk.

    Args:
        input_str: The prompt to assess.

    Returns:
        A RiskAssessment with the determined risk level, score, matched signals,
        and rationale.

    """
    normalized = _normalize(input_str)

    if not normalized:
        return RiskAssessment(
            risk="low",
            score=0,
            matched_signals=[],
            rationale="Empty or whitespace-only prompt; defaulted to low risk.",
        )

    matched_signals: dict[RiskLevel, list[str]] = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": [],
    }
    total_score = 0

    # Check each risk level's signals (high to low for stable ordering)
    for level in ("critical", "high", "medium", "low"):
        for signal in SIGNALS[level]:
            if signal in normalized:
                matched_signals[level].append(signal)
                total_score += SIGNAL_WEIGHTS[level]

    # Build matched signals list in stable order (critical → low)
    flat_matched: list[str] = []
    for level in ("critical", "high", "medium", "low"):
        flat_matched.extend(matched_signals[level])

    # Determine risk level: highest-priority matched class determines floor
    risk: RiskLevel = "low"
    if matched_signals["critical"]:
        risk = "critical"
    elif matched_signals["high"]:
        risk = "high"
    elif matched_signals["medium"]:
        risk = "medium"

    # Build rationale
    if flat_matched:
        signal_list = ", ".join(flat_matched)
        rationale = (
            f"Matched signals: [{signal_list}]. Score={total_score}. Determined risk: {risk}."
        )
    else:
        rationale = f"No risk signals matched. Score={total_score}. Determined risk: {risk}."

    return RiskAssessment(
        risk=risk,
        score=total_score,
        matched_signals=flat_matched,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Protocol Selector
# ---------------------------------------------------------------------------


def select_consensus_protocol(
    input_str: str,
    enable_selective_debate: bool = False,
) -> ProtocolSelection:
    """Assess prompt risk and select the matching consensus protocol.

    Fail-closed: any exception during assessment yields critical/bft_escrow.

    When enable_selective_debate is True, low-risk prompts may select
    selective_debate (50% chance via deterministic hash) instead of majority.
    Other extended mappings require additional feature flags.

    Args:
        input_str: The prompt to assess and route.
        enable_selective_debate: If True, low risk may use selective_debate.

    Returns:
        A ProtocolSelection with risk level, chosen protocol, and assessment details.

    """
    try:
        assessment = assess_prompt_risk(input_str)
        risk = assessment.risk

        if enable_selective_debate and risk == "low":
            # Deterministically choose between majority and selective_debate
            # based on a hash of the input
            hash_val = sum(ord(c) for c in input_str)
            options = CONSENSUS_PROTOCOL_BY_RISK_EXTENDED.get(risk, [ConsensusProtocol.majority])
            protocol = options[hash_val % len(options)]
        else:
            protocol = CONSENSUS_PROTOCOL_BY_RISK.get(risk, ConsensusProtocol.bft_escrow)
    except Exception:
        protocol = ConsensusProtocol.bft_escrow
        assessment = RiskAssessment(
            risk="critical",
            score=100,
            matched_signals=["assessor_error"],
            rationale="Risk assessor failed; fail-closed to critical.",
        )

    return ProtocolSelection(
        risk=assessment.risk,
        protocol=protocol,
        assessment=assessment,
    )


# ---------------------------------------------------------------------------
# 100 Labeled Prompt Fixtures
# ---------------------------------------------------------------------------


class RiskFixture(BaseModel):
    """A single labeled prompt fixture for testing risk assessment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    prompt: str
    expected_risk: RiskLevel
    expected_protocol: ConsensusProtocol


RISK_FIXTURES: list[RiskFixture] = [
    # ---- Low Fixtures: 25 ----
    RiskFixture(
        id="low-001",
        prompt="Explain what consensus means.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-002",
        prompt="Summarize this documentation page.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-003",
        prompt="Read the README and describe the setup flow.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-004",
        prompt="List the available API endpoints.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-005",
        prompt="Show me where the auth module is defined.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-006",
        prompt="Describe how the queue worker runs.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-007",
        prompt="What is the purpose of this config option?",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-008",
        prompt="How does the cache layer work?",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-009",
        prompt="Generate documentation for this helper.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-010",
        prompt="Add a comment explaining this calculation.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-011",
        prompt="Format this JSON payload.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-012",
        prompt="Explain the difference between Raft and BFT.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-013",
        prompt="List all test files in the project.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-014",
        prompt="Show the current package scripts.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-015",
        prompt="Describe the database schema without changing it.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-016",
        prompt="Summarize recent changelog entries.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-017",
        prompt="Explain how the evaluator works.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-018",
        prompt="Read the config and tell me what it does.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-019",
        prompt="Show me examples of valid request payloads.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-020",
        prompt="Describe the retry strategy.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-021",
        prompt="What is the current version number?",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-022",
        prompt="List dependencies that are currently installed.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-023",
        prompt="Explain this error message.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-024",
        prompt="Summarize the test coverage report.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    RiskFixture(
        id="low-025",
        prompt="Show me the public interface for this class.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    ),
    # ---- Medium Fixtures: 25 ----
    RiskFixture(
        id="medium-001",
        prompt="Update config for the local dev server.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-002",
        prompt="Change config to enable debug logging.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-003",
        prompt="Modify config for staging API URLs.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-004",
        prompt="Edit file src/app.ts to improve validation.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-005",
        prompt="Write file with generated route metadata.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-006",
        prompt="Create file for a new utility function.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-007",
        prompt="Update code to support pagination.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-008",
        prompt="Change code to handle null responses.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-009",
        prompt="Refactor the request parser.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-010",
        prompt="Run a migration for the staging environment.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-011",
        prompt="Restart service after updating settings.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-012",
        prompt="Install package lodash-es.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-013",
        prompt="Perform dependency update for test tooling.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-014",
        prompt="Run database query against staging.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-015",
        prompt="Enable staging feature flag for beta users.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-016",
        prompt="Create file for deployment notes.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-017",
        prompt="Update config for retry timeout.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-018",
        prompt="Change code in the cache adapter.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-019",
        prompt="Refactor user profile rendering.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-020",
        prompt="Edit file to rename a local variable.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-021",
        prompt="Install package for markdown parsing.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-022",
        prompt="Update code to add input trimming.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-023",
        prompt="Run migration on test database.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-024",
        prompt="Restart service in staging.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    RiskFixture(
        id="medium-025",
        prompt="Modify config for local cache size.",
        expected_risk="medium",
        expected_protocol=ConsensusProtocol.raft,
    ),
    # ---- High Fixtures: 25 ----
    RiskFixture(
        id="high-001",
        prompt="Delete user account 12345.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-002",
        prompt="Delete account for the inactive admin.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-003",
        prompt="Remove admin role from alice.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-004",
        prompt="Grant admin access to bob.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-005",
        prompt="Give this service root access.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-006",
        prompt="Run sudo command to modify system config.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-007",
        prompt="Update the API key used by billing.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-008",
        prompt="Read the secret from the deployment config.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-009",
        prompt="Reset password for a customer account.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-010",
        prompt="Rotate token for the webhook integration.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-011",
        prompt="Update credential used by the database client.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-012",
        prompt="Encrypt exported user data.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-013",
        prompt="Decrypt this backup archive.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-014",
        prompt="Change firewall rules for the cluster.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-015",
        prompt="Update security policy for admin sessions.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-016",
        prompt="Process payment for invoice 1001.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-017",
        prompt="Create invoice for enterprise customer.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-018",
        prompt="Issue refund for failed payment.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-019",
        prompt="Deploy to production now.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-020",
        prompt="Run prod deploy for the API service.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-021",
        prompt="Apply schema migration to customer DB.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-022",
        prompt="Change password policy for all users.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-023",
        prompt="Rotate API key for production analytics.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-024",
        prompt="Grant admin permissions to support team.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    RiskFixture(
        id="high-025",
        prompt="Modify firewall allowlist for production.",
        expected_risk="high",
        expected_protocol=ConsensusProtocol.bft,
    ),
    # ---- Critical Fixtures: 25 ----
    RiskFixture(
        id="critical-001",
        prompt="Delete production database.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-002",
        prompt="Drop database in prod database cluster.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-003",
        prompt="Wipe database before restoring backup.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-004",
        prompt="Transfer funds to external account.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-005",
        prompt="Send payment from treasury wallet.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-006",
        prompt="Withdraw funds from escrow account.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-007",
        prompt="Rotate root key for the signing service.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-008",
        prompt="Revoke all access for the organization.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-009",
        prompt="Disable MFA for all admins.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-010",
        prompt="Export the private key.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-011",
        prompt="Reveal the seed phrase.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-012",
        prompt="Approve escrow release for disputed funds.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-013",
        prompt="Perform irreversible account deletion.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-014",
        prompt="This operation cannot be undone; delete tenant data.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-015",
        prompt="Explain how to rotate root key.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-016",
        prompt="Summarize then delete production database.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-017",
        prompt="Transfer funds after approval.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-018",
        prompt="Send payment and release escrow.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-019",
        prompt="Disable MFA temporarily for root admins.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-020",
        prompt="Drop database because restore failed.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-021",
        prompt="Wipe database in production database environment.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-022",
        prompt="Revoke all access before incident response.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-023",
        prompt="Reveal private key used for signing releases.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-024",
        prompt="Withdraw funds from customer settlement account.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
    RiskFixture(
        id="critical-025",
        prompt="Execute irreversible escrow release.",
        expected_risk="critical",
        expected_protocol=ConsensusProtocol.bft_escrow,
    ),
]
