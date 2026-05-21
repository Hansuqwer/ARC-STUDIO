"""Contract test: RuntimeCapability v1 -> v2 migration.

Pins the schema bump from Phase 0 baseline (v1) to Phase 3 (v2).

Lock references:
- docs/adr/ADR-011-full-parity-framing.md (capability shape)
- docs/archive/phase-0-inventory/runtime-matrix.md (v1 baseline)
- docs/phases.md Phase 3 row (v2 deliverables)

Test strategy:
1. Every v1 fixture in fixtures/runtime-capability/v1/ must migrate cleanly.
2. Migration is idempotent: migrate(v1) -> v2, migrate(v2) -> v2 unchanged.
3. Every new v2 field has a deterministic default derived from v1 content.
4. schema_version is bumped exactly once.
5. No v1 field is silently dropped.
6. Migrated payloads validate against the v2 Pydantic model.

Adding a fixture:
- Drop a new JSON file in fixtures/runtime-capability/v1/
- Add an entry to V1_EXPECTED_DEFAULTS below if it needs non-default
  expectations for the new v2 fields.
- The migration test will pick it up automatically.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agent_runtime_cockpit.protocol.runtime_capability import RuntimeCapability
from agent_runtime_cockpit.runtime.mode import RuntimeMode


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "runtime-capability"
V1_DIR = FIXTURE_ROOT / "v1"
V2_DIR = FIXTURE_ROOT / "v2"


# ---------------------------------------------------------------------------
# Per-fixture expectations for v2 fields that should NOT take the global
# default. Keyed by fixture stem (filename without .json).
#
# Anything not listed here is expected to take the defaults asserted in
# test_v2_defaults_are_locked below.
# ---------------------------------------------------------------------------

V1_EXPECTED_DEFAULTS: dict[str, dict[str, Any]] = {
    # Example: a fixture explicitly representing a paid runtime.
    # "provider_backed_anthropic_v1": {
    #     "mode": RuntimeMode.PROVIDER_BACKED,
    #     "allow_paid_calls": True,
    #     "cost_source_default": "measured",
    # },
}


# ---------------------------------------------------------------------------
# Fixture discovery
# ---------------------------------------------------------------------------


def _v1_fixture_paths() -> list[Path]:
    if not V1_DIR.exists():
        return []
    return sorted(V1_DIR.glob("*.json"))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def test_v1_fixture_directory_exists():
    """Without v1 fixtures we cannot prove migration works. The Phase 3
    branch must include at least one v1 fixture before this test passes."""
    assert V1_DIR.exists(), (
        f"Missing v1 fixture directory: {V1_DIR}. "
        "Phase 3 must preserve Phase 0 baseline fixtures."
    )
    fixtures = _v1_fixture_paths()
    assert len(fixtures) > 0, (
        f"No v1 fixtures in {V1_DIR}. "
        "Copy the Phase 0 baseline fixture(s) here before migrating."
    )


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
            f"{fixture_path.name} is not a v1 fixture; "
            "move it to the correct directory."
        )

    def test_migrate_bumps_schema_version_to_2(self, fixture_path):
        migrated = RuntimeCapability.migrate_v1_to_v2(_load(fixture_path))
        assert migrated["schema_version"] == 2

    def test_migrate_result_validates_as_v2(self, fixture_path):
        """The migrated dict must round-trip through the v2 Pydantic model."""
        migrated = RuntimeCapability.migrate_v1_to_v2(_load(fixture_path))
        capability = RuntimeCapability.model_validate(migrated)
        assert capability.schema_version == 2

    def test_migration_is_idempotent(self, fixture_path):
        """migrate(v1) -> v2; migrate(v2) -> v2 unchanged.

        Idempotency matters because legacy code paths may call migrate
        defensively without checking schema_version.
        """
        once = RuntimeCapability.migrate_v1_to_v2(_load(fixture_path))
        twice = RuntimeCapability.migrate_v1_to_v2(once)
        assert once == twice

    def test_no_v1_field_silently_dropped(self, fixture_path):
        """Every key present in v1 must appear in v2 (possibly with a
        renamed key, but never dropped silently)."""
        v1_payload = _load(fixture_path)
        migrated = RuntimeCapability.migrate_v1_to_v2(v1_payload)

        # schema_version is allowed to change; everything else must survive
        # either under the same key or via a documented rename.
        for key, value in v1_payload.items():
            if key == "schema_version":
                continue
            assert (
                key in migrated
                or key in _DOCUMENTED_RENAMES
            ), (
                f"v1 field {key!r} dropped during migration of "
                f"{fixture_path.name}. If this is intentional, add it to "
                f"_DOCUMENTED_RENAMES with the new field name."
            )

    def test_v2_required_fields_present(self, fixture_path):
        """Every v2 field added in Phase 3 must be populated after migration."""
        migrated = RuntimeCapability.migrate_v1_to_v2(_load(fixture_path))

        for required in V2_REQUIRED_FIELDS:
            assert required in migrated, (
                f"v2 field {required!r} missing after migration of "
                f"{fixture_path.name}"
            )

    def test_v2_field_defaults_match_expectations(self, fixture_path):
        """Per-fixture expected values for v2-only fields.

        If a fixture is missing from V1_EXPECTED_DEFAULTS, the global
        defaults asserted below apply.
        """
        migrated = RuntimeCapability.migrate_v1_to_v2(_load(fixture_path))
        expected = V1_EXPECTED_DEFAULTS.get(fixture_path.stem, {})

        for field, expected_value in expected.items():
            actual = migrated[field]
            # Handle enum equality across str/Enum boundary
            if isinstance(expected_value, RuntimeMode):
                assert RuntimeMode(actual) is expected_value
            else:
                assert actual == expected_value

    def test_allow_paid_calls_consistent_with_mode(self, fixture_path):
        """Invariant: allow_paid_calls=True is only valid when
        mode=PROVIDER_BACKED. Migration must never produce an inconsistent
        capability."""
        migrated = RuntimeCapability.migrate_v1_to_v2(_load(fixture_path))
        mode = RuntimeMode(migrated["mode"])
        allow_paid = migrated["allow_paid_calls"]
        if allow_paid:
            assert mode is RuntimeMode.PROVIDER_BACKED, (
                f"{fixture_path.name}: allow_paid_calls=True but mode={mode}. "
                "Migration produced an invalid capability."
            )

    def test_cost_source_consistent_with_mode(self, fixture_path):
        """Invariant: cost_source_default='measured' is only valid for
        provider_backed. Other modes must default to 'estimated'."""
        migrated = RuntimeCapability.migrate_v1_to_v2(_load(fixture_path))
        mode = RuntimeMode(migrated["mode"])
        cost_source = migrated["cost_source_default"]

        if cost_source == "measured":
            assert mode is RuntimeMode.PROVIDER_BACKED
        else:
            assert cost_source == "estimated"


# ---------------------------------------------------------------------------
# Global invariants (not per-fixture)
# ---------------------------------------------------------------------------


V2_REQUIRED_FIELDS = (
    "schema_version",
    "mode",
    "profile_id",
    "isolation_id",
    "allow_paid_calls",
    "cost_source_default",
    "supports_cancellation",
    "supports_streaming",
)


# If a v1 field is renamed in v2, list it here with a comment explaining why.
# An empty dict means "no renames; every v1 field keeps its name in v2".
_DOCUMENTED_RENAMES: dict[str, str] = {
    # "old_name": "new_name",  # ADR-XXX justifies the rename
}


def test_v2_defaults_are_locked():
    """The default v2 capability (FAKE mode) has locked field values.

    If this test needs to change, ADR-011 needs an amendment.
    """
    minimal_v1 = {"schema_version": 1}
    migrated = RuntimeCapability.migrate_v1_to_v2(minimal_v1)

    assert migrated["schema_version"] == 2
    assert RuntimeMode(migrated["mode"]) is RuntimeMode.FAKE
    assert migrated["allow_paid_calls"] is False
    assert migrated["cost_source_default"] == "estimated"
    # Cancellation is required for any non-fake runtime; fake itself
    # advertises support too because cancellation is a no-op there.
    assert migrated["supports_cancellation"] is True
    assert isinstance(migrated["supports_streaming"], bool)
    assert isinstance(migrated["profile_id"], str)
    assert isinstance(migrated["isolation_id"], str)


def test_provider_backed_v1_migrates_with_paid_calls_inferred():
    """A v1 fixture whose mode (under any legacy name) maps to
    provider_backed must come out of migration with allow_paid_calls=True
    and cost_source_default='measured'."""
    v1 = {"schema_version": 1, "mode": "live"}  # legacy 'live' -> provider_backed
    migrated = RuntimeCapability.migrate_v1_to_v2(v1)

    assert RuntimeMode(migrated["mode"]) is RuntimeMode.PROVIDER_BACKED
    assert migrated["allow_paid_calls"] is True
    assert migrated["cost_source_default"] == "measured"


def test_migration_raises_on_v0_or_unknown_schema():
    """We only support v1 -> v2 in this phase. v0 or v3+ should fail loudly."""
    with pytest.raises(ValueError, match="schema_version"):
        RuntimeCapability.migrate_v1_to_v2({"schema_version": 0})
    with pytest.raises(ValueError, match="schema_version"):
        RuntimeCapability.migrate_v1_to_v2({"schema_version": 3})


def test_migration_raises_on_missing_schema_version():
    """A payload without schema_version cannot be safely migrated."""
    with pytest.raises((KeyError, ValueError)):
        RuntimeCapability.migrate_v1_to_v2({"mode": "fake"})


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
    hand-edited v2 fixtures and the migration function."""
    v2_path = V2_DIR / v1_path.name
    if not v2_path.exists():
        pytest.skip(
            f"No v2 counterpart for {v1_path.name}. "
            "Generate it with: scripts/regen-fixtures.sh runtime-capability"
        )

    migrated = RuntimeCapability.migrate_v1_to_v2(_load(v1_path))
    expected = _load(v2_path)
    assert migrated == expected, (
        f"v2 fixture {v2_path.name} drifted from migration output. "
        "Regenerate with scripts/regen-fixtures.sh runtime-capability."
    )
