"""Data models for ARC Arena — LM Arena protocol types."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ArenaMode(str, Enum):
    """The four LM Arena interaction modes."""
    BATTLE = "battle"
    DIRECT = "direct"
    CODE = "code"
    AGENT_ARENA_PREVIEW = "agent-arena-preview"


class PrivacyLevel(str, Enum):
    """Privacy settings for code sent to Arena."""
    PRIVATE = "Private"
    DEBUG = "Debug"
    RESEARCH = "Research"


class ArenaModelInfo(BaseModel):
    """Available model information from LM Arena."""
    id: str
    name: str
    provider: str
    tags: list[str] = Field(default_factory=list)
    supports_battle: bool = True
    supports_direct: bool = True
    supports_code: bool = False
    supports_agent_preview: bool = False
    input_cost: float = 0.0
    output_cost: float = 0.0


class ArenaCandidate(BaseModel):
    """A single response candidate from one model in a battle or direct call."""
    id: str
    model: str = ""
    text: str = ""
    patch: str = ""
    diff: str = ""
    plan: str = ""
    files_changed: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArenaRequest(BaseModel):
    """Request payload for LM Arena operations."""
    mode: ArenaMode = ArenaMode.BATTLE
    prompt: str = ""
    workspace: str = ""
    selected_files: list[str] = Field(default_factory=list)
    context: str = ""
    model: str = ""
    model_tags: list[str] = Field(default_factory=list)
    privacy: PrivacyLevel = PrivacyLevel.PRIVATE
    allow_paid_calls: bool = False
    profile_id: str = "local-safe"


class ArenaResponse(BaseModel):
    """Response payload from LM Arena."""
    run_id: str = ""
    mode: ArenaMode = ArenaMode.BATTLE
    candidates: list[ArenaCandidate] = Field(default_factory=list)
    recommended: str = ""
    warnings: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


class ArenaVote(BaseModel):
    """A user vote for a battle candidate."""
    run_id: str
    winner_candidate_id: str
    loser_candidate_id: str = ""
    profile_id: str = ""
    voter: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


class ArenaAdoptRequest(BaseModel):
    """Request to adopt a candidate's output."""
    run_id: str
    candidate_id: str
    target_file: str = ""
    workspace: str = ""


class ArenaAdoptResult(BaseModel):
    """Result of adopting a candidate's output."""
    applied: bool = False
    file_changed: str = ""
    patch_lines: int = 0
    message: str = ""
