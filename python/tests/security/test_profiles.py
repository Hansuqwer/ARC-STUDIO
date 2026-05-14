"""Tests for run profiles."""
from agent_runtime_cockpit.security.profiles import (
    BUILTIN_PROFILES,
    resolve_profile,
    enforce_profile,
)
from agent_runtime_cockpit.gating import GatingError


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
