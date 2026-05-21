"""Tests for BudgetEnforcer — real-time budget enforcement at effect boundaries."""
from agent_runtime_cockpit.budget.legacy_vector import BudgetVectorEnforcer as BudgetEnforcer, BudgetExceededError
from agent_runtime_cockpit.protocol.schemas import BudgetVector


def test_enforcer_no_budget_no_checking():
    """Enforcer with no budget does not raise."""
    enforcer = BudgetEnforcer()
    enforcer.check_tokens(1000000)
    enforcer.check_cost(1e6)
    enforcer.check_latency(999999)
    assert enforcer.exhausted is False


def test_enforcer_token_limit_enforced():
    """Token limit raises BudgetExceededError."""
    enforcer = BudgetEnforcer(BudgetVector(tokens=1000))
    enforcer.check_tokens(500)  # OK
    enforcer.check_and_update(tokens=500)  # OK
    assert enforcer.tokens_used == 500
    enforcer.check_tokens(499)  # OK (projected 999 < 1000)
    enforcer.check_tokens(500)  # Would exceed (projected 1000 >= 1000)

    try:
        enforcer.check_tokens(501)
        assert False, "should have raised"
    except BudgetExceededError as exc:
        assert exc.dimension == "tokens"
        assert exc.limit == 1000
        assert exc.current == 1001
        assert "exceeded" in str(exc)


def test_enforcer_cost_limit_enforced():
    """Cost limit raises BudgetExceededError."""
    enforcer = BudgetEnforcer(BudgetVector(cost_usd=5.0))
    enforcer.check_and_update(cost=3.0)  # OK
    assert enforcer.cost_used == 3.0

    try:
        enforcer.check_and_update(cost=3.0)  # Would exceed (6.0 > 5.0)
        assert False, "should have raised"
    except BudgetExceededError as exc:
        assert exc.dimension == "cost_usd"


def test_enforcer_latency_limit_enforced():
    """Latency limit raises BudgetExceededError."""
    enforcer = BudgetEnforcer(BudgetVector(latency_ms=5000))
    enforcer.check_and_update(latency_ms=3000)  # OK
    assert enforcer.latency_ms_used == 3000

    try:
        enforcer.check_and_update(latency_ms=3000)  # Would exceed (6000 > 5000)
        assert False, "should have raised"
    except BudgetExceededError as exc:
        assert exc.dimension == "latency_ms"


def test_enforcer_atomic_check_and_update():
    """check_and_update checks all dimensions before updating any."""
    enforcer = BudgetEnforcer(BudgetVector(tokens=100, cost_usd=1.0))
    enforcer.check_and_update(tokens=50, cost=0.5)  # OK
    assert enforcer.tokens_used == 50
    assert enforcer.cost_used == 0.5

    # This would exceed tokens but not cost — should still raise before update
    try:
        enforcer.check_and_update(tokens=60, cost=0.1)
        assert False, "should have raised"
    except BudgetExceededError:
        pass
    # Counters should NOT have been updated
    assert enforcer.tokens_used == 50
    assert enforcer.cost_used == 0.5


def test_enforcer_exhausted_property():
    """exhausted returns True when any dimension is at or past limit."""
    enforcer = BudgetEnforcer(BudgetVector(tokens=100, cost_usd=1.0, latency_ms=1000))
    assert enforcer.exhausted is False

    enforcer.check_and_update(tokens=100)
    assert enforcer.exhausted is True

    enforcer.reset()
    assert enforcer.exhausted is False
    assert enforcer.tokens_used == 0


def test_enforcer_reset_clears_counters():
    """reset clears all accumulated usage."""
    enforcer = BudgetEnforcer(BudgetVector(tokens=100))
    enforcer.check_and_update(tokens=50)
    assert enforcer.tokens_used == 50
    enforcer.reset()
    assert enforcer.tokens_used == 0
    assert enforcer.cost_used == 0.0
    assert enforcer.latency_ms_used == 0
    assert enforcer.exhausted is False


def test_enforcer_to_usage_metadata():
    """to_usage_metadata returns serializable dict."""
    enforcer = BudgetEnforcer(BudgetVector(tokens=100, cost_usd=5.0))
    enforcer.check_and_update(tokens=30, cost=1.5)
    meta = enforcer.to_usage_metadata()
    assert meta["budget_enforcer"]["tokens_used"] == 30
    assert meta["budget_enforcer"]["cost_used"] == 1.5
    assert meta["budget_enforcer"]["exhausted"] is False
    assert meta["budget_enforcer"]["budget"]["tokens"] == 100


def test_enforcer_no_budget_exhausted_is_false():
    """exhausted is False when no budget is configured."""
    enforcer = BudgetEnforcer()
    assert enforcer.exhausted is False
    enforcer.check_and_update(tokens=999999)
    assert enforcer.exhausted is False


def test_enforcer_partial_budget():
    """Enforcer works with partially-defined budget."""
    enforcer = BudgetEnforcer(BudgetVector(tokens=500))
    enforcer.check_and_update(tokens=500)
    assert enforcer.exhausted is True
    # Cost and latency are not limited, so additional calls succeed
    enforcer.check_and_update(cost=100.0, latency_ms=99999)
    assert enforcer.tokens_used == 500  # tokens unchanged
    assert enforcer.cost_used == 100.0
