"""
ARC domain models — workspace, runtimes, workflows, schemas, runs, events, context.
These are the canonical Python data structures; JSON Schema is generated from them.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from .capabilities import RuntimeCapabilities


# ─── Runtime ──────────────────────────────────────────────────────────────────

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RuntimeInfo(BaseModel):
    id: str
    name: str
    adapter: str
    confidence: ConfidenceLevel
    evidence: list[str] = Field(default_factory=list)
    capabilities: RuntimeCapabilities = Field(default_factory=RuntimeCapabilities)


class WorkspaceInfo(BaseModel):
    path: str
    runtimes: list[RuntimeInfo] = Field(default_factory=list)
    files_scanned: int = 0
    detection_warnings: list[str] = Field(default_factory=list)


# ─── Workflow ─────────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    ROUTER = "router"
    START = "start"
    END = "end"
    UNKNOWN = "unknown"


class SourceLocation(BaseModel):
    file: str
    line: int
    column: Optional[int] = None


class WorkflowNode(BaseModel):
    id: str
    label: str
    type: NodeType = NodeType.UNKNOWN
    source_location: Optional[SourceLocation] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    id: str
    from_node: str
    to_node: str
    label: Optional[str] = None
    conditional: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowInfo(BaseModel):
    id: str
    name: str
    runtime: str
    source_file: Optional[str] = None
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Schema ───────────────────────────────────────────────────────────────────

class SchemaInfo(BaseModel):
    id: str
    name: str
    runtime: str
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    source_file: Optional[str] = None

    model_config = {"populate_by_name": True}

    def model_dump_api(self) -> dict[str, Any]:
        d = self.model_dump(by_alias=True)
        return d


# ─── Run / Events ─────────────────────────────────────────────────────────────

class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunEvent(BaseModel):
    schema_version: int = 1  # Event schema version (ADR-004)
    type: str
    timestamp: str
    run_id: str
    sequence: int
    data: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    id: str
    workflow_id: str
    runtime: str
    status: RunStatus = RunStatus.PENDING
    started_at: str
    ended_at: Optional[str] = None
    events: list[RunEvent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    audit_path: Optional[str] = None  # Path to audit chain file (ADR-003)


# ─── Context ──────────────────────────────────────────────────────────────────

class SourceType(str, Enum):
    LOCAL_REPO = "local_repo"
    CONTEXT7 = "context7"
    VERCEL_GREP = "vercel_grep"
    GITHUB_SEARCH = "github_search"
    WEB_SEARCH = "web_search"


class ContextPackEntry(BaseModel):
    id: str
    task: str
    source: str
    source_type: SourceType
    content: str
    url: Optional[str] = None
    freshness: Optional[str] = None
    relevance_score: float = 0.0
