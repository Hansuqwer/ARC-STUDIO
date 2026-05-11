"""LangGraph agent state — detected by ARC schema inspector."""
from typing import TypedDict, Optional


class AgentState(TypedDict):
    messages: list[dict]
    next: Optional[str]
