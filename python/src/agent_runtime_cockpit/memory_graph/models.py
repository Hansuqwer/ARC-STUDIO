"""Models for the Swarm Memory Graph research prototype."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


MemoryNodeType = Literal["concept", "decision", "pattern", "risk", "outcome"]
MemoryEdgeType = Literal["derived_from", "supports", "contradicts", "co_occurs"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class MemoryNode(BaseModel):
    """A persisted research memory extracted from stored local traces."""

    id: str
    type: MemoryNodeType
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    frequency: int = Field(default=1, ge=1)
    source_run_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class MemoryEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    type: MemoryEdgeType
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryGraphSnapshot(BaseModel):
    schema_version: str = "phase59.research.v1"
    nodes: list[MemoryNode] = Field(default_factory=list)
    edges: list[MemoryEdge] = Field(default_factory=list)
    privacy_mode: Literal["local_workspace_only"] = "local_workspace_only"
    tenant_isolation: Literal["not_claimed"] = "not_claimed"
    redaction_applied: bool = True


class MemoryEvaluationReport(BaseModel):
    """Research gate report for deciding whether memory can influence runs."""

    sample_run_count: int = 0
    node_count: int = 0
    edge_count: int = 0
    quality_delta: float | None = None
    cost_delta: float | None = None
    decision: Literal["proceed", "no_go", "insufficient_evidence"] = "insufficient_evidence"
    reasons: list[str] = Field(default_factory=list)
    memory_runtime_injection: bool = False
    evidence_source: Literal["manual_metrics", "evidence_pack"] = "manual_metrics"


class MemoryEvidenceSample(BaseModel):
    """Offline research sample; never runtime prompt input."""

    sample_id: str
    baseline_quality: float
    candidate_quality: float
    baseline_cost: float
    candidate_cost: float
    reviewed_privacy: bool = False
    redaction_applied: bool = False
    memory_runtime_injection: bool = False


class MemoryEvidencePack(BaseModel):
    schema_version: str = "phase64.memory_evidence.v1"
    pack_id: str
    created_at: str = Field(default_factory=utc_now)
    memory_runtime_injection: bool = False
    samples: list[MemoryEvidenceSample] = Field(default_factory=list)


class MemoryEvidenceRunResult(BaseModel):
    sample_id: str
    quality_delta: float
    cost_delta: float
    valid: bool
    reasons: list[str] = Field(default_factory=list)


class MemoryEvidenceReport(BaseModel):
    schema_version: str = "phase64.memory_evidence_report.v1"
    pack_id: str
    valid_sample_count: int
    quality_delta: float | None = None
    cost_delta: float | None = None
    memory_runtime_injection: bool = False
    decision: Literal["proceed", "no_go", "insufficient_evidence"] = "insufficient_evidence"
    reasons: list[str] = Field(default_factory=list)
    results: list[MemoryEvidenceRunResult] = Field(default_factory=list)
