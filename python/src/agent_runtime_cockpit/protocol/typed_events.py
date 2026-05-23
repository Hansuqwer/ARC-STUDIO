"""
Discriminated RunEvent union types for type-safe event handling (Phase 22).

Replaces unsafe `data: dict[str, Any]` with typed payloads for known event types.
Consumers can use type narrowing with isinstance() checks instead of unsafe dict access.

Architecture: Union of typed event variants for critical event types plus a generic
fallback for events that aren't yet typed. This allows incremental migration while
maintaining backward compatibility.
"""

from __future__ import annotations

from typing import Any, Literal, Union, TypeGuard
from pydantic import BaseModel, Field

from ._bypass import PolicyBypassWarning


# ─── Base Event Model ────────────────────────────────────────────────────────


class RunEventBase(BaseModel):
    """Base model for all run events with common fields."""

    schema_version: int = 2
    type: str
    timestamp: str
    run_id: str
    sequence: int


# ─── Run Lifecycle Events ────────────────────────────────────────────────────


class RunStartedData(BaseModel):
    """Data payload for RUN_STARTED event."""

    workflow_id: str
    runtime: str
    profile_id: str | None = None
    isolation: str | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class RunStartedEvent(BaseModel):
    """RUN_STARTED event with typed payload."""

    schema_version: int = 2
    type: Literal["RUN_STARTED"]
    timestamp: str
    run_id: str
    sequence: int
    data: RunStartedData


class RunCompletedData(BaseModel):
    """Data payload for RUN_COMPLETED event."""

    duration_ms: int
    output: Any | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class RunCompletedEvent(BaseModel):
    """RUN_COMPLETED event with typed payload."""

    schema_version: int = 2
    type: Literal["RUN_COMPLETED"]
    timestamp: str
    run_id: str
    sequence: int
    data: RunCompletedData


class RunFailedData(BaseModel):
    """Data payload for RUN_FAILED event."""

    error: str
    error_detail: str | None = None
    error_type: str | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class RunFailedEvent(BaseModel):
    """RUN_FAILED event with typed payload."""

    schema_version: int = 2
    type: Literal["RUN_FAILED"]
    timestamp: str
    run_id: str
    sequence: int
    data: RunFailedData


class RunCancelledData(BaseModel):
    """Data payload for RUN_CANCELLED event."""

    cancel_reason: str
    node_id: str | None = None
    message_id: str | None = None


class RunCancelledEvent(BaseModel):
    """RUN_CANCELLED event with typed payload."""

    schema_version: int = 2
    type: Literal["RUN_CANCELLED"]
    timestamp: str
    run_id: str
    sequence: int
    data: RunCancelledData


# ─── Step Lifecycle Events ───────────────────────────────────────────────────


class StepStartedData(BaseModel):
    """Data payload for STEP_STARTED event."""

    step_id: str
    step_name: str
    step_type: str | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class StepStartedEvent(BaseModel):
    """STEP_STARTED event with typed payload."""

    schema_version: int = 2
    type: Literal["STEP_STARTED"]
    timestamp: str
    run_id: str
    sequence: int
    data: StepStartedData


class StepCompletedData(BaseModel):
    """Data payload for STEP_COMPLETED event."""

    step_id: str
    output: Any | None = None
    duration_ms: int | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class StepCompletedEvent(BaseModel):
    """STEP_COMPLETED event with typed payload."""

    schema_version: int = 2
    type: Literal["STEP_COMPLETED"]
    timestamp: str
    run_id: str
    sequence: int
    data: StepCompletedData


class StepFailedData(BaseModel):
    """Data payload for STEP_FAILED event."""

    step_id: str
    error: str
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class StepFailedEvent(BaseModel):
    """STEP_FAILED event with typed payload."""

    schema_version: int = 2
    type: Literal["STEP_FAILED"]
    timestamp: str
    run_id: str
    sequence: int
    data: StepFailedData


# ─── Tool Call Events ────────────────────────────────────────────────────────


class ToolCallStartData(BaseModel):
    """Data payload for TOOL_CALL_START event."""

    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any] | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class ToolCallStartEvent(BaseModel):
    """TOOL_CALL_START event with typed payload."""

    schema_version: int = 2
    type: Literal["TOOL_CALL_START"]
    timestamp: str
    run_id: str
    sequence: int
    data: ToolCallStartData


class ToolCallData(BaseModel):
    """Data payload for TOOL_CALL event."""

    tool_call_id: str
    tool_name: str
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class ToolCallEvent(BaseModel):
    """TOOL_CALL event with typed payload."""

    schema_version: int = 2
    type: Literal["TOOL_CALL"]
    timestamp: str
    run_id: str
    sequence: int
    data: ToolCallData


class ToolCallResultData(BaseModel):
    """Data payload for TOOL_CALL_RESULT event."""

    tool_call_id: str
    result: Any
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class ToolCallResultEvent(BaseModel):
    """TOOL_CALL_RESULT event with typed payload."""

    schema_version: int = 2
    type: Literal["TOOL_CALL_RESULT"]
    timestamp: str
    run_id: str
    sequence: int
    data: ToolCallResultData


class ToolCallErrorData(BaseModel):
    """Data payload for TOOL_CALL_ERROR event."""

    tool_call_id: str
    error: str
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class ToolCallErrorEvent(BaseModel):
    """TOOL_CALL_ERROR event with typed payload."""

    schema_version: int = 2
    type: Literal["TOOL_CALL_ERROR"]
    timestamp: str
    run_id: str
    sequence: int
    data: ToolCallErrorData


# ─── HITL Events ─────────────────────────────────────────────────────────────


class HitlPromptData(BaseModel):
    """Data payload for HITL_PROMPT event."""

    hitl_id: str
    step_id: str
    prompt_text: str
    options: list[str]
    timeout_seconds: int
    context: Any | None = None
    created_at: str | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class HitlPromptEvent(BaseModel):
    """HITL_PROMPT event with typed payload."""

    schema_version: int = 2
    type: Literal["HITL_PROMPT"]
    timestamp: str
    run_id: str
    sequence: int
    data: HitlPromptData


class HitlResponseData(BaseModel):
    """Data payload for HITL_RESPONSE event."""

    hitl_id: str
    decision: str
    operator_id: str
    responded_at: str
    modified_data: Any | None = None
    notes: str | None = None
    node_id: str | None = None
    message_id: str | None = None


class HitlResponseEvent(BaseModel):
    """HITL_RESPONSE event with typed payload."""

    schema_version: int = 2
    type: Literal["HITL_RESPONSE"]
    timestamp: str
    run_id: str
    sequence: int
    data: HitlResponseData


class HitlTimeoutData(BaseModel):
    """Data payload for HITL_TIMEOUT event."""

    hitl_id: str
    step_id: str
    timeout_seconds: int
    node_id: str | None = None
    message_id: str | None = None


class HitlTimeoutEvent(BaseModel):
    """HITL_TIMEOUT event with typed payload."""

    schema_version: int = 2
    type: Literal["HITL_TIMEOUT"]
    timestamp: str
    run_id: str
    sequence: int
    data: HitlTimeoutData


# ─── SwarmGraph Events ───────────────────────────────────────────────────────


class SwarmGraphTopologyData(BaseModel):
    """Data payload for SWARMGRAPH_TOPOLOGY event."""

    nodes: list[Any]
    edges: list[Any]
    task_id: str | None = None
    strategy: str | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class SwarmGraphTopologyEvent(BaseModel):
    """SWARMGRAPH_TOPOLOGY event with typed payload."""

    schema_version: int = 2
    type: Literal["SWARMGRAPH_TOPOLOGY"]
    timestamp: str
    run_id: str
    sequence: int
    data: SwarmGraphTopologyData


class SwarmGraphConsensusData(BaseModel):
    """Data payload for SWARMGRAPH_CONSENSUS event."""

    votes: list[Any]
    decision: str | None = None
    strategy: str | None = None
    voters: list[str] | None = None
    confidence: float | None = None
    consensus_reached: bool | None = None
    task_id: str | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class SwarmGraphConsensusEvent(BaseModel):
    """SWARMGRAPH_CONSENSUS event with typed payload."""

    schema_version: int = 2
    type: Literal["SWARMGRAPH_CONSENSUS"]
    timestamp: str
    run_id: str
    sequence: int
    data: SwarmGraphConsensusData


class SwarmGraphCostData(BaseModel):
    """Data payload for SWARMGRAPH_COST event."""

    provider: str | None = None
    model: str | None = None
    promptTokens: int | None = Field(None, alias="promptTokens")
    completionTokens: int | None = Field(None, alias="completionTokens")
    totalCost: float | None = Field(None, alias="totalCost")
    totalTokens: int | None = Field(None, alias="totalTokens")
    currency: str | None = None
    items: list[Any] | None = None
    source: str | None = None
    runtime: str | None = None
    measured: str | None = None
    node_id: str | None = None
    message_id: str | None = None
    evidence_refs: list[str] | None = None


class SwarmGraphCostEvent(BaseModel):
    """SWARMGRAPH_COST event with typed payload."""

    schema_version: int = 2
    type: Literal["SWARMGRAPH_COST"]
    timestamp: str
    run_id: str
    sequence: int
    data: SwarmGraphCostData


# ─── Message Events ──────────────────────────────────────────────────────────


class MessageData(BaseModel):
    """Data payload for MESSAGE event."""

    message_id: str
    role: str
    content: str
    node_id: str | None = None
    evidence_refs: list[str] | None = None


class MessageEvent(BaseModel):
    """MESSAGE event with typed payload."""

    schema_version: int = 2
    type: Literal["MESSAGE"]
    timestamp: str
    run_id: str
    sequence: int
    data: MessageData


# ─── Node Events ─────────────────────────────────────────────────────────────


class NodeStartedData(BaseModel):
    """Data payload for NODE_STARTED event."""

    node_id: str
    node_name: str
    node_type: str | None = None
    evidence_refs: list[str] | None = None


class NodeStartedEvent(BaseModel):
    """NODE_STARTED event with typed payload."""

    schema_version: int = 2
    type: Literal["NODE_STARTED"]
    timestamp: str
    run_id: str
    sequence: int
    data: NodeStartedData


class NodeFailedData(BaseModel):
    """Data payload for NODE_FAILED event."""

    node_id: str
    error: str
    node_name: str | None = None
    evidence_refs: list[str] | None = None


class NodeFailedEvent(BaseModel):
    """NODE_FAILED event with typed payload."""

    schema_version: int = 2
    type: Literal["NODE_FAILED"]
    timestamp: str
    run_id: str
    sequence: int
    data: NodeFailedData


# ─── Battle Mode Events (Phase 34/R26A) ──────────────────────────────────────


class BattleStartedData(BaseModel):
    """Data payload for BATTLE_STARTED event."""

    battle_id: str
    prompt: str
    workers: int
    topology: str
    consensus_protocol: str
    runtime_mode: str | None = None
    consensus_escrow: bool | None = None
    require_hitl: bool | None = None
    node_id: str | None = None
    message_id: str | None = None


class BattleStartedEvent(BaseModel):
    """BATTLE_STARTED event with typed payload."""

    schema_version: int = 2
    type: Literal["BATTLE_STARTED"]
    timestamp: str
    run_id: str
    sequence: int
    data: BattleStartedData


class BattleCandidateReadyData(BaseModel):
    """Data payload for BATTLE_CANDIDATE_READY event."""

    battle_id: str
    candidate_id: str
    worker_id: str
    model_id: str
    output_preview: str | None = None
    node_id: str | None = None
    message_id: str | None = None


class BattleCandidateReadyEvent(BaseModel):
    """BATTLE_CANDIDATE_READY event with typed payload."""

    schema_version: int = 2
    type: Literal["BATTLE_CANDIDATE_READY"]
    timestamp: str
    run_id: str
    sequence: int
    data: BattleCandidateReadyData


class BattleVoteCommittedData(BaseModel):
    """Data payload for BATTLE_VOTE_COMMITTED event."""

    battle_id: str
    vote_id: str
    commit_hash: str
    voter: str | None = None
    node_id: str | None = None
    message_id: str | None = None


class BattleVoteCommittedEvent(BaseModel):
    """BATTLE_VOTE_COMMITTED event with typed payload."""

    schema_version: int = 2
    type: Literal["BATTLE_VOTE_COMMITTED"]
    timestamp: str
    run_id: str
    sequence: int
    data: BattleVoteCommittedData


class BattleVoteRevealedData(BaseModel):
    """Data payload for BATTLE_VOTE_REVEALED event."""

    battle_id: str
    vote_id: str
    candidate_id: str
    approved: bool
    voter: str | None = None
    reasoning: str | None = None
    node_id: str | None = None
    message_id: str | None = None


class BattleVoteRevealedEvent(BaseModel):
    """BATTLE_VOTE_REVEALED event with typed payload."""

    schema_version: int = 2
    type: Literal["BATTLE_VOTE_REVEALED"]
    timestamp: str
    run_id: str
    sequence: int
    data: BattleVoteRevealedData


class BattleConsensusReachedData(BaseModel):
    """Data payload for BATTLE_CONSENSUS_REACHED event."""

    battle_id: str
    consensus_reached: bool
    winner_candidate_id: str | None = None
    consensus_result: dict[str, Any] | None = None
    node_id: str | None = None
    message_id: str | None = None


class BattleConsensusReachedEvent(BaseModel):
    """BATTLE_CONSENSUS_REACHED event with typed payload."""

    schema_version: int = 2
    type: Literal["BATTLE_CONSENSUS_REACHED"]
    timestamp: str
    run_id: str
    sequence: int
    data: BattleConsensusReachedData


class BattleHitlRequiredData(BaseModel):
    """Data payload for BATTLE_HITL_REQUIRED event."""

    battle_id: str
    hitl_id: str
    candidates: list[dict[str, Any]]
    prompt: str | None = None
    timeout_seconds: int | None = None
    node_id: str | None = None
    message_id: str | None = None


class BattleHitlRequiredEvent(BaseModel):
    """BATTLE_HITL_REQUIRED event with typed payload."""

    schema_version: int = 2
    type: Literal["BATTLE_HITL_REQUIRED"]
    timestamp: str
    run_id: str
    sequence: int
    data: BattleHitlRequiredData


class BattleCompletedData(BaseModel):
    """Data payload for BATTLE_COMPLETED event."""

    battle_id: str
    status: str
    winner_candidate_id: str | None = None
    duration_ms: int | None = None
    error: str | None = None
    node_id: str | None = None
    message_id: str | None = None


class BattleCompletedEvent(BaseModel):
    """BATTLE_COMPLETED event with typed payload."""

    schema_version: int = 2
    type: Literal["BATTLE_COMPLETED"]
    timestamp: str
    run_id: str
    sequence: int
    data: BattleCompletedData


# ─── Raw/Unknown Events ──────────────────────────────────────────────────────


class RawEventData(BaseModel):
    """Data payload for RAW event."""

    raw: Any
    source: str | None = None
    node_id: str | None = None
    message_id: str | None = None


class RawEvent(BaseModel):
    """RAW event for unknown/untyped events."""

    schema_version: int = 2
    type: Literal["RAW"]
    timestamp: str
    run_id: str
    sequence: int
    data: RawEventData


class UnknownEvent(BaseModel):
    """Generic fallback for event types that aren't yet typed."""

    schema_version: int = 2
    type: str
    timestamp: str
    run_id: str
    sequence: int
    data: dict[str, Any] = Field(default_factory=dict)


# ─── Discriminated Union ─────────────────────────────────────────────────────

# Union of all known typed event variants
KnownRunEvent = Union[
    RunStartedEvent,
    RunCompletedEvent,
    RunFailedEvent,
    RunCancelledEvent,
    StepStartedEvent,
    StepCompletedEvent,
    StepFailedEvent,
    ToolCallStartEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    ToolCallErrorEvent,
    HitlPromptEvent,
    HitlResponseEvent,
    HitlTimeoutEvent,
    MessageEvent,
    NodeStartedEvent,
    NodeFailedEvent,
    SwarmGraphTopologyEvent,
    SwarmGraphConsensusEvent,
    SwarmGraphCostEvent,
    PolicyBypassWarning,
    BattleStartedEvent,
    BattleCandidateReadyEvent,
    BattleVoteCommittedEvent,
    BattleVoteRevealedEvent,
    BattleConsensusReachedEvent,
    BattleHitlRequiredEvent,
    BattleCompletedEvent,
    RawEvent,
]

# Full RunEvent type: known typed events + unknown fallback
TypedRunEvent = Union[KnownRunEvent, UnknownEvent]


# ─── Type Guards ─────────────────────────────────────────────────────────────


def is_run_started(event: TypedRunEvent) -> TypeGuard[RunStartedEvent]:
    """Type guard for RUN_STARTED events."""
    return event.type == "RUN_STARTED"


def is_run_completed(event: TypedRunEvent) -> TypeGuard[RunCompletedEvent]:
    """Type guard for RUN_COMPLETED events."""
    return event.type == "RUN_COMPLETED"


def is_run_failed(event: TypedRunEvent) -> TypeGuard[RunFailedEvent]:
    """Type guard for RUN_FAILED events."""
    return event.type == "RUN_FAILED"


def is_step_started(event: TypedRunEvent) -> TypeGuard[StepStartedEvent]:
    """Type guard for STEP_STARTED events."""
    return event.type == "STEP_STARTED"


def is_tool_call_result(event: TypedRunEvent) -> TypeGuard[ToolCallResultEvent]:
    """Type guard for TOOL_CALL_RESULT events."""
    return event.type == "TOOL_CALL_RESULT"


def is_hitl_prompt(event: TypedRunEvent) -> TypeGuard[HitlPromptEvent]:
    """Type guard for HITL_PROMPT events."""
    return event.type == "HITL_PROMPT"


def is_policy_bypass_warning(event: TypedRunEvent) -> TypeGuard[PolicyBypassWarning]:
    """Type guard for POLICY_BYPASS_WARNING events."""
    return event.type == "POLICY_BYPASS_WARNING"


def is_known_event(event: TypedRunEvent) -> TypeGuard[KnownRunEvent]:
    """Type guard to check if an event is a known typed event."""
    known_types = {
        "RUN_STARTED",
        "RUN_COMPLETED",
        "RUN_FAILED",
        "RUN_CANCELLED",
        "STEP_STARTED",
        "STEP_COMPLETED",
        "STEP_FAILED",
        "TOOL_CALL_START",
        "TOOL_CALL",
        "TOOL_CALL_RESULT",
        "TOOL_CALL_ERROR",
        "HITL_PROMPT",
        "HITL_RESPONSE",
        "HITL_TIMEOUT",
        "MESSAGE",
        "NODE_STARTED",
        "NODE_FAILED",
        "SWARMGRAPH_TOPOLOGY",
        "SWARMGRAPH_CONSENSUS",
        "SWARMGRAPH_COST",
        "POLICY_BYPASS_WARNING",
        "BATTLE_STARTED",
        "BATTLE_CANDIDATE_READY",
        "BATTLE_VOTE_COMMITTED",
        "BATTLE_VOTE_REVEALED",
        "BATTLE_CONSENSUS_REACHED",
        "BATTLE_HITL_REQUIRED",
        "BATTLE_COMPLETED",
        "RAW",
    }
    return event.type in known_types


def parse_typed_event(raw: dict[str, Any]) -> TypedRunEvent:
    """
    Parse a raw event dict into a typed RunEvent.

    Attempts to parse as a known typed event first, falls back to UnknownEvent
    for event types that aren't yet typed.

    Args:
        raw: Raw event dictionary from JSON parsing

    Returns:
        Typed RunEvent (known or unknown)

    Raises:
        ValueError: If the event is malformed
    """
    event_type = raw.get("type")
    if not isinstance(event_type, str):
        raise ValueError("Invalid event: missing or invalid type field")

    # Map event types to their Pydantic models
    type_map: dict[str, type[KnownRunEvent]] = {
        "RUN_STARTED": RunStartedEvent,
        "RUN_COMPLETED": RunCompletedEvent,
        "RUN_FAILED": RunFailedEvent,
        "RUN_CANCELLED": RunCancelledEvent,
        "STEP_STARTED": StepStartedEvent,
        "STEP_COMPLETED": StepCompletedEvent,
        "STEP_FAILED": StepFailedEvent,
        "TOOL_CALL_START": ToolCallStartEvent,
        "TOOL_CALL": ToolCallEvent,
        "TOOL_CALL_RESULT": ToolCallResultEvent,
        "TOOL_CALL_ERROR": ToolCallErrorEvent,
        "HITL_PROMPT": HitlPromptEvent,
        "HITL_RESPONSE": HitlResponseEvent,
        "HITL_TIMEOUT": HitlTimeoutEvent,
        "MESSAGE": MessageEvent,
        "NODE_STARTED": NodeStartedEvent,
        "NODE_FAILED": NodeFailedEvent,
        "SWARMGRAPH_TOPOLOGY": SwarmGraphTopologyEvent,
        "SWARMGRAPH_CONSENSUS": SwarmGraphConsensusEvent,
        "SWARMGRAPH_COST": SwarmGraphCostEvent,
        "POLICY_BYPASS_WARNING": PolicyBypassWarning,
        "BATTLE_STARTED": BattleStartedEvent,
        "BATTLE_CANDIDATE_READY": BattleCandidateReadyEvent,
        "BATTLE_VOTE_COMMITTED": BattleVoteCommittedEvent,
        "BATTLE_VOTE_REVEALED": BattleVoteRevealedEvent,
        "BATTLE_CONSENSUS_REACHED": BattleConsensusReachedEvent,
        "BATTLE_HITL_REQUIRED": BattleHitlRequiredEvent,
        "BATTLE_COMPLETED": BattleCompletedEvent,
        "RAW": RawEvent,
    }

    model_class = type_map.get(event_type)
    if model_class:
        return model_class.model_validate(raw)

    # Fallback to UnknownEvent for untyped events
    return UnknownEvent.model_validate(raw)
