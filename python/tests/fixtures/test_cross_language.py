"""Cross-language fixture validation tests.

Tests that JSON fixtures in protocol/fixtures/ are valid according to
Python Pydantic models and can round-trip through serialization.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities
from agent_runtime_cockpit.protocol.errors import ArcErrorCode
from agent_runtime_cockpit.protocol.event_envelope import ArcEnvelope
from agent_runtime_cockpit.protocol.runtime_capability import RuntimeCapability
from agent_runtime_cockpit.protocol.schemas import RunEvent

from .loader import (
    list_categories,
    list_fixtures,
    load_and_validate,
    load_fixture,
    validate_round_trip,
)

ERROR_CODE_FIXTURE_DIR = Path(__file__).parents[3] / "protocol" / "fixtures" / "error-codes"


def _error_code_fixture_files() -> list[Path]:
    if not ERROR_CODE_FIXTURE_DIR.exists():
        return []
    return sorted(ERROR_CODE_FIXTURE_DIR.glob("*.json"))


def _kebab_to_upper_snake(value: str) -> str:
    return value.replace("-", "_").upper()


class TestFixtureLoader:
    """Test the fixture loader utility functions."""

    def test_list_categories(self):
        """Fixture categories are discoverable."""
        categories = list_categories()
        assert "arc-envelope" in categories
        assert "run-event" in categories
        assert "runtime-capabilities" in categories

    def test_list_fixtures(self):
        """Fixtures within a category are discoverable."""
        fixtures = list_fixtures("arc-envelope")
        assert "success" in fixtures
        assert "error-run-failed" in fixtures

    def test_load_fixture_success(self):
        """Can load a fixture as raw JSON."""
        data = load_fixture("arc-envelope", "success")
        assert data["ok"] is True
        assert data["version"] == "1.0"

    def test_load_fixture_not_found(self):
        """Loading nonexistent fixture raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Fixture not found"):
            load_fixture("arc-envelope", "nonexistent")


class TestArcEnvelopeFixtures:
    """Test ArcEnvelope fixtures validate correctly."""

    def test_success_fixture(self):
        """Success envelope fixture is valid."""
        envelope = load_and_validate("arc-envelope", "success", ArcEnvelope)
        assert envelope.ok is True
        assert envelope.error is None
        assert envelope.data is not None
        assert envelope.meta.adapter == "swarmgraph"

    def test_error_run_failed_fixture(self):
        """Error envelope fixture is valid."""
        envelope = load_and_validate("arc-envelope", "error-run-failed", ArcEnvelope)
        assert envelope.ok is False
        assert envelope.data is None
        assert envelope.error is not None
        assert envelope.error.code == "RUN_FAILED"

    def test_error_workspace_not_found_fixture(self):
        """Workspace not found error fixture is valid."""
        envelope = load_and_validate("arc-envelope", "error-workspace-not-found", ArcEnvelope)
        assert envelope.ok is False
        assert envelope.error.code == "WORKSPACE_NOT_FOUND"

    def test_round_trip_success(self):
        """Success envelope round-trips through serialization."""
        original, serialized, instance = validate_round_trip("arc-envelope", "success", ArcEnvelope)
        # Core fields must match
        assert original["ok"] == serialized["ok"]
        assert original["version"] == serialized["version"]
        # Meta fields must be present
        assert "meta" in serialized
        assert serialized["meta"]["adapter"] == original["meta"]["adapter"]


class TestRunEventFixtures:
    """Test RunEvent fixtures validate correctly."""

    def test_run_started_fixture(self):
        """RUN_STARTED event fixture is valid."""
        event = load_and_validate("run-event", "run-started", RunEvent)
        assert event.type == "RUN_STARTED"
        assert event.schema_version == 2
        assert event.data["workflow_id"] == "workflow-xyz789"

    def test_run_completed_fixture(self):
        """RUN_COMPLETED event fixture is valid."""
        event = load_and_validate("run-event", "run-completed", RunEvent)
        assert event.type == "RUN_COMPLETED"
        assert event.schema_version == 2
        assert "duration_ms" in event.data

    def test_run_failed_fixture(self):
        """RUN_FAILED event fixture is valid."""
        event = load_and_validate("run-event", "run-failed", RunEvent)
        assert event.type == "RUN_FAILED"
        assert event.schema_version == 2
        assert "error" in event.data

    def test_run_cancelled_fixture(self):
        """RUN_CANCELLED event fixture is valid."""
        event = load_and_validate("run-event", "run-cancelled", RunEvent)
        assert event.type == "RUN_CANCELLED"
        assert event.schema_version == 2
        assert event.data["cancel_reason"] == "user_requested"

    def test_round_trip_run_completed(self):
        """RUN_COMPLETED event round-trips through serialization."""
        original, serialized, instance = validate_round_trip("run-event", "run-completed", RunEvent)
        assert original["type"] == serialized["type"]
        assert original["schema_version"] == serialized["schema_version"]
        assert original["run_id"] == serialized["run_id"]


class TestRuntimeCapabilitiesFixtures:
    """Test RuntimeCapabilities fixtures validate correctly."""

    def test_v1_basic_fixture(self):
        """RuntimeCapabilities v1 fixture is valid."""
        caps = load_and_validate("runtime-capabilities", "v1-basic", RuntimeCapabilities)
        assert caps.schema_version == 1
        assert caps.support_level.value == "stable"
        assert caps.can_run is True

    def test_v2_gated_local_fixture(self):
        """RuntimeCapability v2 gated_local fixture is valid."""
        caps = load_and_validate("runtime-capabilities", "v2-gated-local", RuntimeCapability)
        assert caps.schema_version == 2
        assert caps.mode.value == "gated_local"
        assert caps.allow_paid_calls is False

    def test_v2_provider_backed_fixture(self):
        """RuntimeCapability v2 provider_backed fixture is valid."""
        caps = load_and_validate("runtime-capabilities", "v2-provider-backed", RuntimeCapability)
        assert caps.schema_version == 2
        assert caps.mode.value == "provider_backed"
        assert caps.allow_paid_calls is True
        assert caps.cost_source_default == "measured"

    def test_v2_paid_call_invariant(self):
        """RuntimeCapability v2 validates paid-call invariants."""
        # This fixture should pass validation
        caps = load_and_validate("runtime-capabilities", "v2-provider-backed", RuntimeCapability)
        assert caps.allow_paid_calls is True
        assert caps.mode.value == "provider_backed"

    def test_round_trip_v2(self):
        """RuntimeCapability v2 round-trips through serialization."""
        original, serialized, instance = validate_round_trip(
            "runtime-capabilities", "v2-provider-backed", RuntimeCapability
        )
        assert original["schema_version"] == serialized["schema_version"]
        assert original["mode"] == serialized["mode"]
        assert original["allow_paid_calls"] == serialized["allow_paid_calls"]


class TestErrorCodeFixtures:
    """Test ADR-023 error-code fixtures validate correctly."""

    def test_error_code_fixture_count(self):
        """Error-code fixtures are present for cross-language validation."""
        assert len(_error_code_fixture_files()) >= 5

    @pytest.mark.parametrize("fixture_path", _error_code_fixture_files(), ids=lambda p: p.stem)
    def test_error_code_fixture_shape(self, fixture_path: Path):
        """Every error-code fixture has the protocol error shape."""
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert isinstance(data.get("code"), str)
        assert data["code"] in {code.value for code in ArcErrorCode}
        assert isinstance(data.get("message"), str)
        assert data["message"]
        assert isinstance(data.get("details", {}), dict)

    @pytest.mark.parametrize("fixture_path", _error_code_fixture_files(), ids=lambda p: p.stem)
    def test_error_code_filename_round_trips(self, fixture_path: Path):
        """Fixture filename kebab-case maps to enum UPPER_SNAKE_CASE."""
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert _kebab_to_upper_snake(fixture_path.stem) == data["code"]
        assert ArcErrorCode(data["code"]).name == data["code"]

    @pytest.mark.parametrize("fixture_path", _error_code_fixture_files(), ids=lambda p: p.stem)
    def test_error_code_fixture_round_trips(self, fixture_path: Path):
        """Error-code fixtures re-serialize without semantic changes."""
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert json.loads(json.dumps(data)) == data

    def test_error_code_enum_has_canonical_adr_023_codes(self):
        """Python ArcErrorCode contains exactly the ADR-023 canonical set."""
        expected = {
            "WORKSPACE_NOT_FOUND",
            "NO_RUNTIME_DETECTED",
            "ADAPTER_ERROR",
            "ADAPTER_NOT_SUPPORTED",
            "SCHEMA_EXPORT_FAILED",
            "WORKFLOW_EXPORT_FAILED",
            "RUN_FAILED",
            "RUN_NOT_FOUND",
            "CONTEXT_PROVIDER_ERROR",
            "CONFORMANCE_FAILED",
            "INVALID_INPUT",
            "INTERNAL_ERROR",
            "TIMEOUT",
            "NOT_IMPLEMENTED",
            "PERMISSION_DENIED",
            "LOCK_CONTENTION",
            "UNKNOWN",
        }
        assert {code.name for code in ArcErrorCode} == expected
        assert issubclass(ArcErrorCode, str)

    @pytest.mark.parametrize(
        ("legacy", "canonical"),
        [
            ("TRACE_NOT_FOUND", ArcErrorCode.RUN_NOT_FOUND),
            ("EXECUTION_FAILED", ArcErrorCode.RUN_FAILED),
            ("PARSE_ERROR", ArcErrorCode.INVALID_INPUT),
            ("WORKFLOW_NOT_FOUND", ArcErrorCode.WORKSPACE_NOT_FOUND),
        ],
    )
    def test_legacy_error_codes_normalize(self, legacy: str, canonical: ArcErrorCode):
        """Deprecated TypeScript wire codes normalize on Python read path."""
        assert ArcErrorCode.from_legacy(legacy) is canonical
        assert ArcErrorCode.from_legacy(canonical.value) is canonical
        assert ArcErrorCode.from_legacy("NOT_A_CODE") is ArcErrorCode.UNKNOWN


class TestCrossLanguageConsistency:
    """Test that fixtures work for cross-language validation."""

    def test_all_fixtures_load(self):
        """All fixtures in all categories can be loaded as JSON."""
        categories = list_categories()
        for category in categories:
            fixtures = list_fixtures(category)
            for fixture_name in fixtures:
                # Should not raise
                data = load_fixture(category, fixture_name)
                assert isinstance(data, dict), f"{category}/{fixture_name} is not a dict"

    def test_event_schema_version_consistency(self):
        """All RunEvent fixtures use schema_version 2."""
        fixtures = list_fixtures("run-event")
        for fixture_name in fixtures:
            event = load_and_validate("run-event", fixture_name, RunEvent)
            assert event.schema_version == 2, f"{fixture_name} has wrong schema_version"

    def test_envelope_version_consistency(self):
        """All ArcEnvelope fixtures use version 1.0."""
        fixtures = list_fixtures("arc-envelope")
        for fixture_name in fixtures:
            envelope = load_and_validate("arc-envelope", fixture_name, ArcEnvelope)
            assert envelope.version == "1.0", f"{fixture_name} has wrong version"
