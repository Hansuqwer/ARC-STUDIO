from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from agent_runtime_cockpit.protocol.cost_record import CostRecord, migrate_v2_to_v3


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


def test_cost_components_sum_must_equal_parent_cost():
    component = _record(cost_usd=Decimal("0.10000000"))
    parent = _record(cost_usd=Decimal("0.10000000"), cost_components=[component.model_dump()])
    assert parent.cost_components[0].cost_usd == Decimal("0.10000000")


def test_cost_components_sum_mismatch_rejected():
    component = _record(cost_usd=Decimal("0.10000000"))
    with pytest.raises(ValidationError, match=r"sum\(cost_components.cost_usd\)"):
        _record(cost_usd=Decimal("0.20000000"), cost_components=[component.model_dump()])


def test_migrate_v2_to_v3_sets_single_component():
    v2 = _record(schema_version=2).model_dump(mode="json")
    migrated = migrate_v2_to_v3(v2)
    record = CostRecord.model_validate(migrated)
    assert record.schema_version == 3
    assert len(record.cost_components) == 1
    assert record.cost_usd == record.cost_components[0].cost_usd
    assert record.cost_components[0].cost_components == []
