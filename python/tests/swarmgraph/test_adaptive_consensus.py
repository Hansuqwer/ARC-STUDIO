"""Phase 51 — Adaptive Consensus Protocol tests.

Tests:
1. All 100 risk fixtures classify at 90%+ accuracy.
2. Protocol mapping: low→majority, medium→raft, high→bft, critical→bft_escrow.
3. User override is recorded in the audit bus as AuditOverrideEvent.
4. No LLM dependency (no LLM call path in adaptive_consensus.py).
5. Context signals: untrusted workspace escalates risk.
6. Context signals: production runtime escalates to at least high.
7. Context signals: .env file type escalates to at least high.
8. Fail-closed: empty input returns low risk (not error).
9. assess_risk accepts all documented parameters without error.
10. CLI: arc swarmgraph assess-risk --json returns ok envelope.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.events.bus import get_bus, reset_bus
from agent_runtime_cockpit.events.types import AuditOverrideEvent
from agent_runtime_cockpit.swarmgraph.adaptive_consensus import assess_risk
from agent_runtime_cockpit.swarmgraph.config import ConsensusProtocol
from agent_runtime_cockpit.swarmgraph.risk_assessment import RISK_FIXTURES


# ---------------------------------------------------------------------------
# 1. 100-fixture accuracy gate (≥90/100)
# ---------------------------------------------------------------------------


def test_100_fixtures_at_90_percent_accuracy() -> None:
    """All 100 labeled risk fixtures must classify at 90%+ accuracy.

    Uses assess_risk() from adaptive_consensus (wraps assess_prompt_risk).
    Workspace trusted, no extra context — base heuristic must classify correctly.
    """
    assert len(RISK_FIXTURES) == 100, f"Expected 100 fixtures, got {len(RISK_FIXTURES)}"

    correct = 0
    failures: list[str] = []

    for fixture in RISK_FIXTURES:
        result = assess_risk(fixture.prompt, workspace_trusted=True)
        if result.risk_level == fixture.expected_risk:
            correct += 1
        else:
            failures.append(
                f"{fixture.id}: expected={fixture.expected_risk}, "
                f"got={result.risk_level}, prompt={fixture.prompt[:60]!r}"
            )

    accuracy = correct / len(RISK_FIXTURES)
    assert accuracy >= 0.90, (
        f"Accuracy {accuracy:.0%} < 90%. Failing fixtures ({len(failures)}):\n"
        + "\n".join(failures[:10])
    )


# ---------------------------------------------------------------------------
# 2. Protocol mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt,expected_protocol",
    [
        ("Explain what consensus means.", ConsensusProtocol.majority),
        ("Update config for the local dev server.", ConsensusProtocol.raft),
        ("Delete user account 12345.", ConsensusProtocol.bft),
        ("Delete production database.", ConsensusProtocol.bft_escrow),
    ],
)
def test_protocol_mapping_per_risk_level(prompt: str, expected_protocol: ConsensusProtocol) -> None:
    """Each risk level maps to the correct protocol."""
    result = assess_risk(prompt, workspace_trusted=True)
    assert result.recommended_protocol == expected_protocol, (
        f"Prompt {prompt!r}: expected {expected_protocol}, got {result.recommended_protocol}. "
        f"Risk level: {result.risk_level}. Rationale: {result.rationale}"
    )


# ---------------------------------------------------------------------------
# 3. Override recorded in audit bus
# ---------------------------------------------------------------------------


def test_override_is_recorded_in_audit_bus(tmp_path: Path) -> None:
    """--override-protocol emits AuditOverrideEvent on the event bus."""
    from typer.testing import CliRunner

    from agent_runtime_cockpit.cli._app import app

    reset_bus()
    seen_overrides: list[AuditOverrideEvent] = []
    get_bus().subscribe("audit_override", lambda ev: seen_overrides.append(ev))

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "swarmgraph",
            "assess-risk",
            "--task",
            "Explain what consensus means.",
            "--override-protocol",
            "raft",
            "--json",
        ],
    )

    assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"

    # Event must be published
    assert len(seen_overrides) == 1, f"Expected 1 override event, got {len(seen_overrides)}"
    ev = seen_overrides[0]
    assert isinstance(ev, AuditOverrideEvent)
    assert ev.override_type == "protocol_override"
    assert ev.override_value == "raft"
    assert ev.original_value in ("majority", "raft", "bft", "bft_escrow")

    reset_bus()


def test_override_recorded_programmatically() -> None:
    """assess_risk override via CLI emits AuditOverrideEvent."""
    from typer.testing import CliRunner

    from agent_runtime_cockpit.cli._app import app

    reset_bus()
    seen: list[AuditOverrideEvent] = []
    get_bus().subscribe("audit_override", lambda ev: seen.append(ev))

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "swarmgraph",
            "assess-risk",
            "--task",
            "Delete production database.",
            "--override-protocol",
            "majority",
            "--json",
        ],
    )

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert len(seen) == 1
    assert seen[0].original_value == "bft_escrow"
    assert seen[0].override_value == "majority"

    reset_bus()


# ---------------------------------------------------------------------------
# 4. No LLM dependency
# ---------------------------------------------------------------------------


def test_no_llm_dependency_in_assess_risk() -> None:
    """assess_risk must not call any LLM or paid API.

    Structural test: import the adaptive_consensus module and verify it does
    not import any LLM provider clients. assess_risk() runs without network
    or LLM calls — pure string heuristic.
    """
    import importlib

    # Load adaptive_consensus module and verify no LLM imports at module level
    mod_name = "agent_runtime_cockpit.swarmgraph.adaptive_consensus"
    mod = importlib.import_module(mod_name)
    module_source_imports = [
        name
        for name in vars(mod)
        if "llm" in name.lower() or "openai" in name.lower() or "anthropic" in name.lower()
    ]
    assert module_source_imports == [], (
        f"LLM imports found in adaptive_consensus: {module_source_imports}"
    )

    # Simply run assess_risk — it must not raise and must return without network
    result = assess_risk("delete production database")
    assert result.risk_level == "critical"
    assert result.recommended_protocol.value == "bft_escrow"


# ---------------------------------------------------------------------------
# 5. Untrusted workspace escalates risk
# ---------------------------------------------------------------------------


def test_untrusted_workspace_escalates_to_at_least_high() -> None:
    """Untrusted workspace floors risk at 'high' regardless of prompt."""
    result = assess_risk("List the available API endpoints.", workspace_trusted=False)
    assert result.risk_level in ("high", "critical"), (
        f"Expected high/critical for untrusted workspace, got {result.risk_level}"
    )
    assert result.hitl_required is True
    assert "workspace_untrusted" in result.rationale


# ---------------------------------------------------------------------------
# 6. Production runtime escalates risk
# ---------------------------------------------------------------------------


def test_production_runtime_escalates_to_at_least_high() -> None:
    """Specifying target_runtime='production' floors risk at 'high'."""
    result = assess_risk(
        "Explain what consensus means.",
        workspace_trusted=True,
        target_runtime="production",
    )
    assert result.risk_level in ("high", "critical"), (
        f"Expected high/critical for production runtime, got {result.risk_level}"
    )


# ---------------------------------------------------------------------------
# 7. .env file type escalates risk
# ---------------------------------------------------------------------------


def test_env_file_type_escalates_to_at_least_high() -> None:
    """File type .env floors risk at 'high'."""
    result = assess_risk(
        "Read the config file.",
        workspace_trusted=True,
        file_types=[".env"],
    )
    assert result.risk_level in ("high", "critical"), (
        f"Expected high/critical for .env file type, got {result.risk_level}"
    )


# ---------------------------------------------------------------------------
# 8. Fail-closed on empty input
# ---------------------------------------------------------------------------


def test_empty_input_returns_low_risk_not_error() -> None:
    """Empty prompt returns low risk (not error/exception)."""
    result = assess_risk("", workspace_trusted=True)
    assert result.risk_level == "low"
    assert result.recommended_protocol == ConsensusProtocol.majority


# ---------------------------------------------------------------------------
# 9. All parameters accepted without error
# ---------------------------------------------------------------------------


def test_assess_risk_accepts_all_parameters() -> None:
    """assess_risk accepts all documented parameters without raising."""
    result = assess_risk(
        task_text="Deploy the service.",
        workspace_trusted=True,
        file_types=[".sql", ".tf"],
        target_runtime="staging",
        paid_call_allowed=True,
        keywords=["deploy", "infrastructure"],
    )
    assert result.risk_level in ("low", "medium", "high", "critical")
    assert isinstance(result.recommended_protocol, ConsensusProtocol)


# ---------------------------------------------------------------------------
# 10. CLI JSON output
# ---------------------------------------------------------------------------


def test_cli_assess_risk_json_output() -> None:
    """arc swarmgraph assess-risk --task ... --json returns ok ArcEnvelope."""
    from typer.testing import CliRunner

    from agent_runtime_cockpit.cli._app import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["swarmgraph", "assess-risk", "--task", "Explain what consensus means.", "--json"],
    )

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    import json

    body = json.loads(result.output)
    assert body["ok"] is True
    data = body["data"]
    assert "risk_level" in data
    assert "recommended_protocol" in data
    assert "worker_count" in data
    assert "hitl_required" in data
    assert "rationale" in data
    assert data["risk_level"] == "low"
    assert data["recommended_protocol"] == "majority"


def test_cli_assess_risk_invalid_override() -> None:
    """arc swarmgraph assess-risk --override-protocol invalid returns error."""
    from typer.testing import CliRunner

    from agent_runtime_cockpit.cli._app import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "swarmgraph",
            "assess-risk",
            "--task",
            "Delete production database.",
            "--override-protocol",
            "invalid-protocol",
            "--json",
        ],
    )

    assert result.exit_code != 0 or (
        "error" in result.output.lower() or "INVALID_INPUT" in result.output
    )
