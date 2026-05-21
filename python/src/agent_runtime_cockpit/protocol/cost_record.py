"""Provider-agnostic cost record schema (ADR-011/013).

``CostRecord`` v3 is the structured representation of a provider or turn
call's cost. It lives with the event envelope so any runtime can record
costs without importing per-provider modules.

v1 was an ad-hoc dict (the SWARMGRAPH_COST event fields). v2 adds a
typed Pydantic model with ``Decimal`` arithmetic, explicit source
tracking, and a migration path from v1.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class CostRecord(BaseModel):
    """Provider-agnostic cost record for a single provider call.

    ``source`` is always ``"measured"`` or ``"estimated"``.
    ``degraded`` is ``True`` iff ``source == "estimated"``.
    Cost arithmetic uses :const:`ROUND_HALF_EVEN` with 8-decimal-place
    quantization.
    """

    schema_version: int = 3
    provider_id: str
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cache_creation_input_tokens: int = Field(default=0, ge=0)
    cache_read_input_tokens: int = Field(default=0, ge=0)
    cost_usd: Decimal = Field(ge=Decimal("0"))
    source: Literal["measured", "estimated"]
    degraded: bool = False
    currency: str = "USD"
    cost_components: list[CostRecord] = Field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_creation_input_tokens + self.cache_read_input_tokens

    @model_validator(mode="after")
    def _check_source_degraded_consistency(self) -> "CostRecord":
        expected_degraded = self.source == "estimated"
        if self.degraded != expected_degraded:
            raise ValueError(
                f"CostRecord invariant violation: source={self.source!r} "
                f"requires degraded={expected_degraded}, got degraded={self.degraded}"
            )
        if self.cost_components:
            component_sum = sum((component.cost_usd for component in self.cost_components), Decimal("0"))
            quantum = Decimal("1.00000000")
            if component_sum.quantize(quantum, rounding=ROUND_HALF_EVEN) != self.cost_usd.quantize(quantum, rounding=ROUND_HALF_EVEN):
                raise ValueError(
                    "CostRecord invariant violation: cost_usd must equal "
                    "sum(cost_components.cost_usd) within 8 decimal places"
                )
        return self

    def quantized(self, places: int = 8) -> CostRecord:
        """Return a copy with ``cost_usd`` quantized to *places* decimals.

        Uses :const:`ROUND_HALF_EVEN` (banker's rounding).
        """
        quantum = Decimal("1." + "0" * places)
        return self.model_copy(update={"cost_usd": self.cost_usd.quantize(quantum, rounding=ROUND_HALF_EVEN)})


# ---------------------------------------------------------------------------
# v1 -> v2 migration
# ---------------------------------------------------------------------------

# Map of v1 field names to their v2 counterparts.
# v1 fields not listed here are dropped (they had no structured v2 equivalent).
_V1_TO_V2_FIELDS: dict[str, str] = {
    "provider": "provider_id",
    "promptTokens": "input_tokens",
    "completionTokens": "output_tokens",
    "totalCost": "cost_usd",
}

# v1 fields that are kept under their original name in v2.
_V1_KEPT_FIELDS: set[str] = {"model", "source"}


def migrate_v1_to_v2(payload: dict[str, Any]) -> dict[str, Any]:
    """Migrate a v1 cost-record dict to v2.

    Args:
        payload: A dict representing a v1 cost record (e.g. the ``data``
            portion of a SWARMGRAPH_COST event).

    Returns:
        A v2 dict ready for ``CostRecord.model_validate()``.

    Raises:
        ValueError: If the payload has an unsupported ``schema_version``
            or is missing required v1 fields.
        KeyError: If required v1 fields are absent.
    """
    sv = payload.get("schema_version", 1)
    if sv == 2:
        return dict(payload)  # already v2, no-op
    if sv != 1:
        raise ValueError(
            f"Unsupported schema_version={sv}. Only v1 -> v2 migration is supported."
        )

    # Check for required v1 source fields
    source = payload.get("source", "estimated")
    if source not in ("measured", "estimated"):
        raise ValueError(f"Invalid source={source!r}; must be 'measured' or 'estimated'.")

    migrated: dict[str, Any] = {"schema_version": 2}

    # Map renamed fields
    for v1_key, v2_key in _V1_TO_V2_FIELDS.items():
        if v1_key in payload:
            value = payload[v1_key]
            # Convert totalCost (float) -> cost_usd (Decimal)
            if v2_key == "cost_usd" and value is not None:
                migrated[v2_key] = str(Decimal(str(value)).quantize(Decimal("1.00000000"), rounding=ROUND_HALF_EVEN))
            elif value is not None:
                migrated[v2_key] = value

    # Copy kept fields
    for key in _V1_KEPT_FIELDS:
        if key in payload:
            migrated[key] = payload[key]

    # Set source default
    migrated.setdefault("source", "estimated")

    # degraded = True iff source == "estimated"
    migrated["degraded"] = migrated.get("source") == "estimated"

    # Always populate cache tokens (default to 0 if absent in v1)
    migrated["cache_creation_input_tokens"] = payload.get("cache_creation_input_tokens", 0)
    migrated["cache_read_input_tokens"] = payload.get("cache_read_input_tokens", 0)

    # currency default
    migrated.setdefault("currency", "USD")

    return migrated


def migrate_v2_to_v3(payload: dict[str, Any]) -> dict[str, Any]:
    """Migrate a v2 cost record to v3 with component breakdown.

    The migrated parent record carries one component copy of the original
    single-call record, preserving the parent-sum invariant without recursion.
    """
    sv = payload.get("schema_version", 2)
    if sv == 3:
        return dict(payload)
    if sv != 2:
        raise ValueError(f"Unsupported schema_version={sv}. Only v2 -> v3 migration is supported.")
    migrated = dict(payload)
    migrated["schema_version"] = 3
    component = dict(payload)
    component["schema_version"] = 3
    component["cost_components"] = []
    migrated["cost_components"] = [component]
    return migrated


def migrate_cost_record_to_latest(payload: dict[str, Any]) -> dict[str, Any]:
    """Migrate a cost record dict to the latest schema version (v3).

    Chains v1 → v2 → v3 migrations as needed.

    Args:
        payload: A dict representing a cost record at any supported version.

    Returns:
        A v3 dict ready for ``CostRecord.model_validate()``.

    Raises:
        ValueError: If the payload has an unsupported ``schema_version``
            or is missing required fields for its declared version.
    """
    sv = payload.get("schema_version", 1)
    
    if sv == 3:
        return dict(payload)
    elif sv == 2:
        return migrate_v2_to_v3(payload)
    elif sv == 1:
        v2 = migrate_v1_to_v2(payload)
        return migrate_v2_to_v3(v2)
    else:
        raise ValueError(
            f"Unsupported schema_version={sv}. "
            f"Only v1, v2, and v3 are supported."
        )
