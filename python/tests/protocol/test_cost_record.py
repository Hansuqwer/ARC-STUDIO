from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from agent_runtime_cockpit.protocol.cost_record import CostRecord


def _record(**overrides):
    data = {
        "provider_id": "anthropic",
        "model": "claude-sonnet-4-6",
        "input_tokens": 10,
        "output_tokens": 5,
        "cost_usd": Decimal("0.00010500"),
        "source": "measured",
        "degraded": False,
    }
    data.update(overrides)
    return CostRecord(**data)


def test_measured_with_degraded_true_rejected():
    with pytest.raises(ValidationError, match="invariant violation"):
        _record(source="measured", degraded=True)


def test_estimated_with_degraded_false_rejected():
    with pytest.raises(ValidationError, match="invariant violation"):
        _record(source="estimated", degraded=False)


def test_estimated_with_degraded_true_accepted():
    record = _record(source="estimated", degraded=True)
    assert record.source == "estimated"
    assert record.degraded is True
