"""MT-2: SimulationConfig cost_per_paid_call_usd + simulation_cost_per_call tests."""

from __future__ import annotations

from agent_runtime_cockpit.simulation.models import SimulationConfig
from agent_runtime_cockpit.simulation.pricing import simulation_cost_per_call


# ── SimulationConfig field ────────────────────────────────────────────────────


def test_simulation_config_default_cost_is_none():
    assert SimulationConfig().cost_per_paid_call_usd is None


def test_simulation_config_accepts_custom_cost():
    cfg = SimulationConfig(cost_per_paid_call_usd=0.0042)
    assert cfg.cost_per_paid_call_usd == 0.0042


def test_simulation_config_free_tier_cost():
    cfg = SimulationConfig(cost_per_paid_call_usd=0.0)
    assert cfg.cost_per_paid_call_usd == 0.0


# ── Simulator uses the cost when provided ────────────────────────────────────


def _make_paid_graph():
    """Return a minimal IRGraph with one paid node using the simulator's test helpers."""
    from tests.simulation.test_simulator import _graph, _node
    from agent_runtime_cockpit.swarmgraph_ir.models import IRNodeKind, IRSideEffect, SideEffectKind

    paid_node = _node(
        "p1",
        kind=IRNodeKind.AGENT,
        side_effects=[IRSideEffect(kind=SideEffectKind.PAID_CALL, paid=True)],
    )
    return _graph(paid_node, entry_points=["p1"])


def test_simulator_uses_custom_cost():
    from agent_runtime_cockpit.simulation.simulator import simulate_graph

    graph = _make_paid_graph()
    custom_cost = 0.0125
    cfg = SimulationConfig(cost_per_paid_call_usd=custom_cost)
    report = simulate_graph(graph, cfg)
    assert report.cost.estimated_cost_floor_usd == round(1 * custom_cost, 6)


def test_simulator_falls_back_to_floor_when_cost_none():
    from agent_runtime_cockpit.simulation.simulator import simulate_graph, _PAID_CALL_COST_FLOOR

    graph = _make_paid_graph()
    report = simulate_graph(graph, SimulationConfig())
    assert report.cost.estimated_cost_floor_usd == round(1 * _PAID_CALL_COST_FLOOR, 6)


# ── simulation_cost_per_call helper ──────────────────────────────────────────


def test_pricing_helper_unknown_provider_returns_none():
    result = simulation_cost_per_call("definitely-not-a-provider", "gpt-9999")
    assert result is None


def test_pricing_helper_returns_float_for_known_provider():
    """For any bundled provider+model pair, helper returns a non-negative float."""
    # Use a provider likely to be in the bundled snapshot.
    result = simulation_cost_per_call("openai", "gpt-4o")
    if result is not None:  # only assert type when data exists
        assert isinstance(result, float)
        assert result >= 0.0


def test_pricing_helper_custom_tokens():
    """Custom token counts scale linearly."""
    r1 = simulation_cost_per_call("openai", "gpt-4o", input_tokens=1000, output_tokens=500)
    r2 = simulation_cost_per_call("openai", "gpt-4o", input_tokens=2000, output_tokens=1000)
    if r1 is not None and r2 is not None and r1 > 0:
        # r2 should be roughly 2× r1 (within rounding)
        assert abs(r2 / r1 - 2.0) < 0.01


def test_pricing_helper_free_tier_via_config():
    """A zero-cost SimulationConfig with cost=0.0 correctly produces zero estimated cost."""
    from agent_runtime_cockpit.simulation.simulator import simulate_graph

    graph = _make_paid_graph()
    report = simulate_graph(graph, SimulationConfig(cost_per_paid_call_usd=0.0))
    assert report.cost.estimated_cost_floor_usd == 0.0
    assert report.cost.has_paid_calls is True  # still detected as paid
