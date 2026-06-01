"""Redacted provider E2E evidence artifacts."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


_ARTIFACT_PATH_ENV = "ARC_PROVIDER_E2E_ARTIFACT"
_ARTIFACT_DIR_ENV = "ARC_PROVIDER_E2E_ARTIFACT_DIR"
_DEFAULT_ARTIFACT_DIR = Path(".arc/evidence/provider-e2e")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


class ProviderE2EEvidence(BaseModel):
    """Durable proof envelope with raw prompt/output intentionally omitted."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    evidence_type: str = "provider_backed_swarmgraph_e2e"
    status: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    gate_env: str = Field(min_length=1)
    gate_enabled: bool
    live_provider_tests_enabled: bool
    prompt_length: int = Field(ge=0)
    prompt_sha256: str = Field(min_length=64, max_length=64)
    output_length: int = Field(ge=0)
    output_sha256: str = Field(min_length=64, max_length=64)
    completed_tasks: int = Field(ge=0)
    event_kinds: list[str]
    provider_call_count: int = Field(ge=0)
    provider_call_content_lengths: list[int] = Field(default_factory=list)
    degraded: bool
    started_at: str
    ended_at: str
    redaction_applied: bool = True
    raw_prompt_stored: bool = False
    raw_output_stored: bool = False
    notes: list[str] = Field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_provider_e2e_evidence(
    *,
    provider: str,
    model: str,
    prompt: str,
    output: str,
    status: str,
    completed_tasks: int,
    events: list[dict[str, Any]],
    calls: list[dict[str, Any]],
    started_at: str,
    ended_at: str,
    gate_env: str = "ARC_RUN_LIVE_PROVIDER_E2E",
) -> ProviderE2EEvidence:
    return ProviderE2EEvidence(
        status=status,
        provider=provider,
        model=model,
        gate_env=gate_env,
        gate_enabled=os.environ.get(gate_env) == "1",
        live_provider_tests_enabled=os.environ.get("ARC_ALLOW_LIVE_PROVIDER_TESTS") == "true",
        prompt_length=len(prompt),
        prompt_sha256=sha256_text(prompt),
        output_length=len(output),
        output_sha256=sha256_text(output),
        completed_tasks=completed_tasks,
        event_kinds=sorted({str(event.get("kind", "unknown")) for event in events}),
        provider_call_count=len(calls),
        provider_call_content_lengths=[int(call.get("content_length", 0) or 0) for call in calls],
        degraded=any(bool(call.get("degraded")) for call in calls),
        started_at=started_at,
        ended_at=ended_at,
        notes=[
            "redacted: raw prompt and model output are not stored",
            "evidence proves only the explicitly gated provider/model test run",
        ],
    )


def resolve_provider_e2e_artifact_path(*, provider: str, model: str) -> Path:
    explicit = os.environ.get(_ARTIFACT_PATH_ENV)
    if explicit:
        return Path(explicit)

    root = Path(os.environ.get(_ARTIFACT_DIR_ENV, str(_DEFAULT_ARTIFACT_DIR)))
    safe_provider = _safe_filename(provider)
    safe_model = _safe_filename(model)
    return root / f"provider-e2e-{safe_provider}-{safe_model}.json"


def write_provider_e2e_evidence(evidence: ProviderE2EEvidence, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(evidence.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def _safe_filename(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in value)
    return cleaned.strip("-.") or "unknown"
