from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from agent_runtime_cockpit.protocol.cost_record import CostRecord, migrate_v2_to_v3, migrate_cost_record_to_latest


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


def test_migrate_to_latest_v1_to_v3():
    """Test v1 → v2 → v3 chained migration."""
    v1 = {
        "schema_version": 1,
        "provider": "anthropic",
        "model": "claude-sonnet-4",
        "promptTokens": 100,
        "completionTokens": 50,
        "totalCost": 0.00525,
        "source": "measured",
    }
    migrated = migrate_cost_record_to_latest(v1)
    record = CostRecord.model_validate(migrated)
    assert record.schema_version == 3
    assert record.provider_id == "anthropic"
    assert record.input_tokens == 100
    assert record.output_tokens == 50
    assert record.cost_usd == Decimal("0.00525000")
    assert record.source == "measured"
    assert record.degraded is False
    assert len(record.cost_components) == 1


def test_migrate_to_latest_v2_to_v3():
    """Test v2 → v3 single migration."""
    v2 = _record(schema_version=2).model_dump(mode="json")
    migrated = migrate_cost_record_to_latest(v2)
    record = CostRecord.model_validate(migrated)
    assert record.schema_version == 3
    assert len(record.cost_components) == 1


def test_migrate_to_latest_v3_noop():
    """Test v3 → v3 no-op."""
    v3 = _record(schema_version=3).model_dump(mode="json")
    migrated = migrate_cost_record_to_latest(v3)
    record = CostRecord.model_validate(migrated)
    assert record.schema_version == 3
    assert migrated == v3


def test_migrate_to_latest_unsupported_version():
    """Test unsupported schema_version raises clear error."""
    unsupported = {
        "schema_version": 99,
        "provider_id": "anthropic",
        "model": "claude-sonnet-4",
        "input_tokens": 10,
        "output_tokens": 5,
        "cost_usd": "0.00010500",
        "source": "measured",
    }
    with pytest.raises(ValueError, match=r"Unsupported schema_version=99.*v1, v2, and v3"):
        migrate_cost_record_to_latest(unsupported)
