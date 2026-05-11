"""ResearchSwarm state model — detected by ARC schema inspector."""
from pydantic import BaseModel
from typing import Optional


class ResearchState(BaseModel):
    topic: str
    research_notes: list[str] = []
    draft: str = ""
    feedback: list[str] = []
    final_output: Optional[str] = None
    iteration: int = 0
