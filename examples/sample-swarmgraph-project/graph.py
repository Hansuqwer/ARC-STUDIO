"""
ResearchSwarm graph — sample SwarmGraph agent project.
This file is scanned by ARC's SwarmGraph adapter for workflow topology.
"""
from state import ResearchState


class Agent:
    """Base agent class (detected by ARC AST scan)."""
    def __init__(self, role: str):
        self.role = role

    def run(self, state: ResearchState) -> ResearchState:
        raise NotImplementedError


class ResearcherAgent(Agent):
    def run(self, state: ResearchState) -> ResearchState:
        # Simulated research
        state.research_notes.append(f"Research note on: {state.topic}")
        return state


class WriterAgent(Agent):
    def run(self, state: ResearchState) -> ResearchState:
        state.draft = f"Draft about {state.topic}: {' '.join(state.research_notes)}"
        return state


class ReviewerAgent(Agent):
    def run(self, state: ResearchState) -> ResearchState:
        if state.iteration < 1:
            state.feedback.append("Needs more detail")
            state.iteration += 1
        else:
            state.final_output = state.draft
        return state


# Graph definition (detected by ARC)
GRAPH = {
    "entry": "start",
    "agents": {
        "researcher": ResearcherAgent("researcher"),
        "writer": WriterAgent("writer"),
        "reviewer": ReviewerAgent("reviewer"),
    }
}
