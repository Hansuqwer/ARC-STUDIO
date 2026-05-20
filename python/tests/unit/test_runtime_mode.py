"""Unit tests for RuntimeMode and from_legacy()."""

from __future__ import annotations

import warnings

import pytest

from agent_runtime_cockpit.runtime.mode import RuntimeMode


# ---------------------------------------------------------------------------
# Enum values are locked
# ---------------------------------------------------------------------------


def test_runtime_mode_has_exactly_three_values():
    """ADR-011 locks three modes. If this fails, an ADR amendment is needed
    before adding or removing a mode."""
    assert {m.value for m in RuntimeMode} == {
        "fake",
        "gated_local",
        "provider_backed",
    }


def test_gated_local_value_is_snake_case():
    """The on-disk string must remain 'gated_local' for backward
    compatibility with Phase 0/1/2 session files. Do not rename."""
    assert RuntimeMode.GATED_LOCAL.value == "gated_local"


# ---------------------------------------------------------------------------
# Pass-through behavior
# ---------------------------------------------------------------------------


def test_from_legacy_passes_through_enum_instances():
    for mode in RuntimeMode:
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # any warning becomes a failure
            result = RuntimeMode.from_legacy(mode)
        assert result is mode


def test_from_legacy_accepts_canonical_strings_without_warning():
    for mode in RuntimeMode:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = RuntimeMode.from_legacy(mode.value)
        assert result is mode


# ---------------------------------------------------------------------------
# Legacy mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [
        ("offline", RuntimeMode.FAKE),
        ("local", RuntimeMode.GATED_LOCAL),
        ("gated", RuntimeMode.GATED_LOCAL),
        ("live", RuntimeMode.PROVIDER_BACKED),
    ],
)
def test_from_legacy_maps_legacy_strings(legacy, expected):
    with pytest.warns(DeprecationWarning, match=legacy):
        result = RuntimeMode.from_legacy(legacy)
    assert result is expected


def test_from_legacy_warning_names_canonical_replacement():
    """The deprecation warning must name the canonical replacement so
    fixing the offending code site is mechanical."""
    with pytest.warns(DeprecationWarning) as record:
        RuntimeMode.from_legacy("live")
    assert len(record) == 1
    message = str(record[0].message)
    assert "provider_backed" in message


def test_from_legacy_warning_mentions_phase_6_removal():
    """Future maintainers should know when the shim disappears."""
    with pytest.warns(DeprecationWarning) as record:
        RuntimeMode.from_legacy("offline")
    assert "Phase 6" in str(record[0].message)


# ---------------------------------------------------------------------------
# Case and whitespace tolerance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["FAKE", "Fake", "  fake  ", "fAkE"])
def test_from_legacy_is_case_and_whitespace_tolerant_for_canonical(value):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = RuntimeMode.from_legacy(value)
    assert result is RuntimeMode.FAKE


@pytest.mark.parametrize("value", ["OFFLINE", "Offline", "  offline  "])
def test_from_legacy_is_case_and_whitespace_tolerant_for_legacy(value):
    with pytest.warns(DeprecationWarning):
        result = RuntimeMode.from_legacy(value)
    assert result is RuntimeMode.FAKE


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_from_legacy_raises_on_unknown_string():
    with pytest.raises(ValueError, match="Unknown runtime mode"):
        RuntimeMode.from_legacy("turbo")


def test_from_legacy_error_lists_valid_values():
    with pytest.raises(ValueError) as excinfo:
        RuntimeMode.from_legacy("nope")
    message = str(excinfo.value)
    assert "fake" in message
    assert "gated_local" in message
    assert "provider_backed" in message
    assert "offline" in message  # legacy aliases listed too


def test_from_legacy_raises_typeerror_on_non_string():
    with pytest.raises(TypeError, match="expected str or RuntimeMode"):
        RuntimeMode.from_legacy(42)  # type: ignore[arg-type]


def test_from_legacy_raises_typeerror_on_none():
    with pytest.raises(TypeError):
        RuntimeMode.from_legacy(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Helper classmethods
# ---------------------------------------------------------------------------


def test_is_paid_only_true_for_provider_backed():
    assert RuntimeMode.is_paid(RuntimeMode.PROVIDER_BACKED) is True
    assert RuntimeMode.is_paid(RuntimeMode.FAKE) is False
    assert RuntimeMode.is_paid(RuntimeMode.GATED_LOCAL) is False


def test_requires_gate_false_only_for_fake():
    assert RuntimeMode.requires_gate(RuntimeMode.FAKE) is False
    assert RuntimeMode.requires_gate(RuntimeMode.GATED_LOCAL) is True
    assert RuntimeMode.requires_gate(RuntimeMode.PROVIDER_BACKED) is True


# ---------------------------------------------------------------------------
# Stacklevel: the warning should point at the caller, not at mode.py
# ---------------------------------------------------------------------------


def test_deprecation_warning_stacklevel_points_at_caller():
    """If stacklevel is wrong, every legacy call looks like it originates
    from mode.py and migration becomes impossible to drive."""
    with pytest.warns(DeprecationWarning) as record:
        RuntimeMode.from_legacy("live")  # this line is the caller

    assert len(record) == 1
    # The recorded filename must be this test file, not mode.py
    assert record[0].filename.endswith("test_runtime_mode.py")
