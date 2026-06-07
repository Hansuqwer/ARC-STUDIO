"""Tests for run profiles."""

from agent_runtime_cockpit.gating import BackendMode, GatingError
from agent_runtime_cockpit.security.profiles import (
    BUILTIN_PROFILES,
    RunProfile,
    enforce_profile,
    resolve_profile,
)


def test_builtin_profiles_exist():
    assert "stub" in BUILTIN_PROFILES
    assert "local-safe" in BUILTIN_PROFILES
    assert "local-paid" in BUILTIN_PROFILES
    assert "gateway" in BUILTIN_PROFILES


def test_resolve_profile():
    p = resolve_profile("stub")
    assert p.id == "stub"
    assert not p.allow_paid_calls
    assert not p.allow_network


def test_resolve_unknown_falls_back_to_stub():
    p = resolve_profile("nonexistent")
    assert p.id == "stub"


def test_local_paid_has_right_permissions():
    p = resolve_profile("local-paid")
    assert p.allow_paid_calls
    assert p.allow_network


def test_gateway_has_full_access():
    p = resolve_profile("gateway")
    assert p.allow_paid_calls
    assert p.allow_network
    assert p.allow_shell
    assert p.allow_secrets


def test_enforce_stub_profile(monkeypatch):
    profile = resolve_profile("stub")
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "stub")
    monkeypatch.setenv("ARC_SWARMGRAPH_ALLOW_COSTS", "")
    # Should not raise
    enforce_profile(profile, "SWARMGRAPH")


def test_enforce_stub_rejects_costs(monkeypatch):
    profile = resolve_profile("stub")
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "stub")
    monkeypatch.setenv("ARC_SWARMGRAPH_ALLOW_COSTS", "true")
    try:
        enforce_profile(profile, "SWARMGRAPH")
        assert False, "Should have raised GatingError"
    except GatingError:
        pass


def test_enforce_local_safe_no_paid(monkeypatch):
    profile = resolve_profile("local-safe")
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "stub")
    monkeypatch.setenv("ARC_SWARMGRAPH_ALLOW_COSTS", "")
    # local-safe uses stub backend, no paid calls
    enforce_profile(profile, "SWARMGRAPH")


def test_enforce_local_safe_rejects_paid_when_disallowed(monkeypatch):
    profile = resolve_profile("local-safe")  # allow_paid_calls=False
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "local")
    monkeypatch.setenv("ARC_SWARMGRAPH_ALLOW_COSTS", "true")
    try:
        enforce_profile(profile, "SWARMGRAPH")
        assert False, "Should have raised GatingError"
    except GatingError:
        pass


def test_enforce_local_backend_allows_network_denied_profile(monkeypatch):
    profile = RunProfile(
        id="local-no-network",
        name="Local No Network",
        allow_paid_calls=True,
        backend=BackendMode.LOCAL,
    )
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "local")
    monkeypatch.setenv("ARC_SWARMGRAPH_ALLOW_COSTS", "true")

    enforce_profile(profile, "SWARMGRAPH")


# ─── CR-019: profile schema version guard ───────────────────────────────────


def test_load_custom_profiles_rejects_future_schema(tmp_path):
    import json

    import pytest

    from agent_runtime_cockpit.security.profiles import (
        PROFILE_SCHEMA_VERSION,
        load_custom_profiles,
    )

    store = tmp_path / "profiles.json"
    store.write_text(json.dumps({"version": PROFILE_SCHEMA_VERSION + 1, "profiles": []}))
    with pytest.raises(ValueError, match="Unsupported profile schema version"):
        load_custom_profiles(store)


def test_load_custom_profiles_accepts_v1_additively(tmp_path):
    import json

    from agent_runtime_cockpit.security.profiles import load_custom_profiles

    # A v1 store missing newer optional fields loads with safe defaults.
    store = tmp_path / "profiles.json"
    store.write_text(
        json.dumps({"version": 1, "profiles": [{"id": "old", "name": "Old", "backend": "stub"}]})
    )
    profiles = load_custom_profiles(store)
    assert "old" in profiles
    assert profiles["old"].allow_paid_calls is False
    assert profiles["old"].env_allowlist == ()


def test_load_custom_profiles_accepts_current_version(tmp_path):
    import json

    from agent_runtime_cockpit.security.profiles import (
        PROFILE_SCHEMA_VERSION,
        load_custom_profiles,
    )

    store = tmp_path / "profiles.json"
    store.write_text(
        json.dumps(
            {
                "version": PROFILE_SCHEMA_VERSION,
                "profiles": [
                    {"id": "p2", "name": "P2", "backend": "local", "allow_paid_calls": True}
                ],
            }
        )
    )
    profiles = load_custom_profiles(store)
    assert profiles["p2"].allow_paid_calls is True
