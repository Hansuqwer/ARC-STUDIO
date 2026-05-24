"""Contract test: CostRecord v1 -> v2 migration.

Pins the structured CostRecord schema introduced in Phase 4.

Test strategy:
1. Every v1 fixture in fixtures/cost-record/v1/ must migrate cleanly.
2. Migration is idempotent: migrate(v1) -> v2, migrate(v2) -> v2 unchanged.
3. Every new v2 field has a deterministic default derived from v1 content.
4. schema_version is bumped exactly once.
5. No v1 field with a v2 equivalent is silently dropped.
6. Migrated payloads validate against the v2 Pydantic model.
7. ``degraded`` is ``True`` iff ``source == "estimated"``.

Adding a fixture:
- Drop a new JSON file in fixtures/cost-record/v1/
- Add the v2 counterpart in fixtures/cost-record/v2/
- The migration test will pick it up automatically.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from agent_runtime_cockpit.protocol.cost_record import CostRecord, migrate_v1_to_v2

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "cost-record"
V1_DIR = FIXTURE_ROOT / "v1"
V2_DIR = FIXTURE_ROOT / "v2"


# ---------------------------------------------------------------------------
# Fixture discovery
# ---------------------------------------------------------------------------


def _v1_fixture_paths() -> list[Path]:
    if not V1_DIR.exists():
        return []
    return sorted(V1_DIR.glob("*.json"))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Directory existence
# ---------------------------------------------------------------------------


def test_v1_fixture_directory_exists():
    """Without v1 fixtures we cannot prove migration works."""
    assert V1_DIR.exists(), f"Missing v1 fixture directory: {V1_DIR}"
    fixtures = _v1_fixture_paths()
    assert len(fixtures) > 0, f"No v1 fixtures in {V1_DIR}"


def test_v2_fixture_directory_exists():
    assert V2_DIR.exists(), f"Missing v2 fixture directory: {V2_DIR}"


# ---------------------------------------------------------------------------
# Per-fixture migration tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_path",
    _v1_fixture_paths(),
    ids=lambda p: p.stem,
)
class TestPerFixtureMigration:
    def test_v1_fixture_has_schema_version_1(self, fixture_path):
        payload = _load(fixture_path)
        assert payload.get("schema_version") == 1, (
            f"{fixture_path.name} is not a v1 fixture; move it to the correct directory."
        )

    def test_migrate_bumps_schema_version_to_2(self, fixture_path):
        migrated = migrate_v1_to_v2(_load(fixture_path))
        assert migrated["schema_version"] == 2

    def test_migrate_result_validates_as_v2(self, fixture_path):
        """The migrated dict must round-trip through the v2 Pydantic model."""
        migrated = migrate_v1_to_v2(_load(fixture_path))
        record = CostRecord.model_validate(migrated)
        assert record.schema_version == 2

    def test_migration_is_idempotent(self, fixture_path):
        """migrate(v1) -> v2; migrate(v2) -> v2 unchanged."""
        once = migrate_v1_to_v2(_load(fixture_path))
        twice = migrate_v1_to_v2(once)
        assert once == twice

    def test_no_v1_field_silently_dropped(self, fixture_path):
        """Every v1 field that has a v2 equivalent must survive migration."""
        v1_payload = _load(fixture_path)
        migrated = migrate_v1_to_v2(v1_payload)

        for key, value in v1_payload.items():
            if key == "schema_version":
                continue
            # Fields that are kept under original name
            if key in ("model", "source", "cache_creation_input_tokens", "cache_read_input_tokens"):
                if key in v1_payload:
                    assert key in migrated, (
                        f"v1 field {key!r} dropped during migration of {fixture_path.name}"
                    )
            # Fields that are renamed
            elif key == "provider":
                assert "provider_id" in migrated, (
                    f"v1 field 'provider' not mapped to 'provider_id' in {fixture_path.name}"
                )
            elif key == "promptTokens":
                assert "input_tokens" in migrated
            elif key == "completionTokens":
                assert "output_tokens" in migrated
            elif key == "totalCost":
                assert "cost_usd" in migrated
            # v1-only fields (no v2 equivalent): totalTokens, items, currency
            # are allowed to be dropped silently

    def test_degraded_flag_consistent_with_source(self, fixture_path):
        """degraded=True iff source='estimated'."""
        migrated = migrate_v1_to_v2(_load(fixture_path))
        source = migrated.get("source", "estimated")
        degraded = migrated.get("degraded", False)
        if source == "estimated":
            assert degraded is True, f"{fixture_path.name}: source='estimated' but degraded=False"
        else:
            assert degraded is False, f"{fixture_path.name}: source='measured' but degraded=True"

    def test_cost_usd_is_decimal_string(self, fixture_path):
        """cost_usd in v2 must be a string (for Decimal round-trip)."""
        migrated = migrate_v1_to_v2(_load(fixture_path))
        cost_usd = migrated.get("cost_usd")
        assert cost_usd is not None, f"{fixture_path.name}: cost_usd is missing"
        assert isinstance(cost_usd, str), (
            f"{fixture_path.name}: cost_usd={cost_usd!r} is {type(cost_usd).__name__}, expected str"
        )

    def test_v2_model_quantized(self, fixture_path):
        """CostRecord.quantized() produces a valid record."""
        migrated = migrate_v1_to_v2(_load(fixture_path))
        record = CostRecord.model_validate(migrated)
        quantized = record.quantized()
        assert isinstance(quantized.cost_usd, type(record.cost_usd))
        assert quantized.schema_version == 2


# ---------------------------------------------------------------------------
# Global invariants
# ---------------------------------------------------------------------------


def test_migration_raises_on_v0_or_unknown_schema():
    with pytest.raises(ValueError, match="schema_version"):
        migrate_v1_to_v2({"schema_version": 0})
    with pytest.raises(ValueError, match="schema_version"):
        migrate_v1_to_v2({"schema_version": 3})


def test_migration_raises_on_invalid_source():
    """Source must be 'measured' or 'estimated'."""
    payload = {
        "schema_version": 1,
        "provider": "openai",
        "model": "gpt-4",
        "promptTokens": 10,
        "completionTokens": 5,
        "totalCost": 0.0001,
        "source": "invalid",
    }
    with pytest.raises(ValueError, match="source"):
        migrate_v1_to_v2(payload)


def test_v2_defaults_are_locked():
    """Minimal v1 payload produces expected v2 defaults."""
    v1 = {
        "schema_version": 1,
        "provider": "openai",
        "model": "gpt-4",
        "promptTokens": 10,
        "completionTokens": 5,
        "totalCost": 0.0001,
    }
    migrated = migrate_v1_to_v2(v1)

    assert migrated["schema_version"] == 2
    assert migrated["provider_id"] == "openai"
    assert migrated["input_tokens"] == 10
    assert migrated["output_tokens"] == 5
    assert isinstance(migrated["cost_usd"], str)
    assert migrated["source"] == "estimated"  # default
    assert migrated["degraded"] is True  # because source=estimated
    assert migrated["currency"] == "USD"
    assert migrated.get("cache_creation_input_tokens", 0) == 0


def test_v2_model_validates_decimal_cost():
    """CostRecord.cost_usd is a Decimal, not float."""
    record = CostRecord(
        provider_id="anthropic",
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=30,
        cost_usd="0.00091500",
        source="measured",
    )
    assert record.cost_usd == Decimal("0.00091500")
    assert record.total_tokens == 130


# ---------------------------------------------------------------------------
# Cross-check: every v2 fixture is byte-identical to migrating its v1 sibling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v1_path",
    _v1_fixture_paths(),
    ids=lambda p: p.stem,
)
def test_v2_fixture_matches_migrated_v1(v1_path):
    """For every v1 fixture, the corresponding v2 fixture (same stem)
    must equal the migration output. This prevents drift between
    hand-edited v2 fixtures and the migration function.
    """
    v2_path = V2_DIR / v1_path.name
    if not v2_path.exists():
        pytest.skip(
            f"No v2 counterpart for {v1_path.name}. Generate it by running the migration function."
        )

    migrated = migrate_v1_to_v2(_load(v1_path))
    expected = _load(v2_path)
    assert migrated == expected, f"v2 fixture {v2_path.name} drifted from migration output. "
