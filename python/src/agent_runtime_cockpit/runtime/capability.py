"""Runtime capability v2 schema and v1 migration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .mode import RuntimeMode


class RuntimeCapability(BaseModel):
    """Canonical runtime capability schema (version 2)."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal[2] = 2
    mode: RuntimeMode = RuntimeMode.FAKE
    profile_id: str = "default"
    isolation_id: str = "none"
    allow_paid_calls: bool = False
    cost_source_default: Literal["estimated", "measured"] = "estimated"
    supports_cancellation: bool = True
    supports_streaming: bool = False

    @field_validator("mode", mode="before")
    @classmethod
    def _coerce_mode(cls, value: Any) -> RuntimeMode:
        return RuntimeMode.from_legacy(value)

    @model_validator(mode="after")
    def _validate_paid_invariants(self) -> "RuntimeCapability":
        if self.allow_paid_calls and self.mode is not RuntimeMode.PROVIDER_BACKED:
            raise ValueError("allow_paid_calls=True requires mode=provider_backed")
        if self.cost_source_default == "measured" and self.mode is not RuntimeMode.PROVIDER_BACKED:
            raise ValueError("measured cost source requires mode=provider_backed")
        return self

    @classmethod
    def migrate_v1_to_v2(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Migrate a v1 capability payload to canonical v2.

        Idempotent for already-v2 payloads. Unknown v1 keys are preserved.
        """
        schema_version = payload["schema_version"]
        if schema_version == 2:
            capability = cls.model_validate(payload)
            return capability.model_dump(mode="json")
        if schema_version != 1:
            raise ValueError(f"Unsupported runtime capability schema_version: {schema_version!r}")

        migrated = dict(payload)
        mode = RuntimeMode.from_legacy(migrated.get("mode", RuntimeMode.FAKE))
        paid = mode is RuntimeMode.PROVIDER_BACKED

        migrated.update(
            {
                "schema_version": 2,
                "mode": mode.value,
                "profile_id": str(migrated.get("profile_id") or migrated.get("runtime_id") or "default"),
                "isolation_id": str(migrated.get("isolation_id") or "none"),
                "allow_paid_calls": bool(migrated.get("allow_paid_calls", paid)),
                "cost_source_default": str(migrated.get("cost_source_default") or ("measured" if paid else "estimated")),
                "supports_cancellation": bool(migrated.get("supports_cancellation", True)),
                "supports_streaming": bool(migrated.get("supports_streaming", False)),
            }
        )
        capability = cls.model_validate(migrated)
        return capability.model_dump(mode="json")
