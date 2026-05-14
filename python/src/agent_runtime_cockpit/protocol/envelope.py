"""
ARC Protocol Envelope — standard JSON response wrapper.

All ARC daemon/CLI responses use this envelope.
Mirrors the TypeScript ArcEnvelope in arc-core/src/common/arc-protocol.ts
"""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

ARC_PROTOCOL_VERSION = "1.0"


class ArcError(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class ArcMeta(BaseModel):
    duration_ms: Optional[float] = None
    adapter: Optional[str] = None
    workspace: Optional[str] = None
    timestamp: Optional[str] = None


class ArcEnvelope(BaseModel, Generic[T]):
    version: str = ARC_PROTOCOL_VERSION
    ok: bool
    data: Optional[T] = None
    error: Optional[ArcError] = None
    meta: ArcMeta = Field(default_factory=ArcMeta)

    model_config = {"arbitrary_types_allowed": True}


def ok(data: T, *, adapter: str | None = None, workspace: str | None = None,
       duration_ms: float | None = None) -> ArcEnvelope[T]:
    """Build a successful ARC envelope."""
    import datetime
    return ArcEnvelope(
        ok=True,
        data=data,
        meta=ArcMeta(
            adapter=adapter,
            workspace=workspace,
            duration_ms=duration_ms,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        ),
    )


def err(code: str, message: str, details: dict | None = None) -> ArcEnvelope[None]:
    """Build an error ARC envelope."""
    import datetime
    return ArcEnvelope(
        ok=False,
        error=ArcError(code=code, message=message, details=details),
        meta=ArcMeta(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")),
    )
