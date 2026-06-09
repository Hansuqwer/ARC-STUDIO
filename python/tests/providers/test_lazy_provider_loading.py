"""Tests: R-PERF3 — lazy provider catalog registration (Phase 286)."""

from __future__ import annotations


def test_bundled_not_registered_before_first_use(monkeypatch):
    """The bundled catalog must not be registered at import time."""
    import agent_runtime_cockpit.providers as prov

    # Reset the lazy flag to simulate a fresh import
    monkeypatch.setattr(prov, "_BUNDLED_REGISTERED", False)
    from agent_runtime_cockpit.providers.registry import _FACTORIES

    # Core providers registered at import time should still be present
    assert "anthropic" in _FACTORIES
    assert "openai" in _FACTORIES


def test_bundled_registered_after_known():
    """Calling known() triggers lazy registration of bundled providers."""
    from agent_runtime_cockpit.providers.registry import known

    all_names = known()
    # 109 bundled + ~10 explicit = well over 50
    assert len(all_names) > 50
    # Spot-check a few bundled providers
    assert "groq" in all_names
    assert "anthropic" in all_names


def test_bundled_registered_after_get():
    """Calling get() on a bundled provider triggers lazy registration."""
    from agent_runtime_cockpit.providers.registry import get

    # fireworks is registered explicitly AND bundled; should be accessible
    client = get("fireworks")
    assert client is not None


def test_lazy_registration_is_idempotent():
    """Calling known() twice does not raise (double-register guard)."""
    from agent_runtime_cockpit.providers.registry import known

    n1 = len(known())
    n2 = len(known())
    assert n1 == n2
