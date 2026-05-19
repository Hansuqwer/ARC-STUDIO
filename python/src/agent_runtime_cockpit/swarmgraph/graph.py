from __future__ import annotations

from .config import SwarmTopology
from .models import AgentRole
from .state import SwarmState


class GraphNode:
    def __init__(self, id: str, label: str, role: AgentRole, children: list[str] | None = None):
        self.id = id
        self.label = label
        self.role = role
        self.children = children or []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "role": self.role.value,
            "children": self.children,
        }


class GraphEdge:
    def __init__(self, source: str, target: str, label: str = ""):
        self.source = source
        self.target = target
        self.label = label

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "label": self.label,
        }


class SwarmGraphTopology:
    def __init__(self, nodes: list[GraphNode] | None = None, edges: list[GraphEdge] | None = None):
        self.nodes = nodes or []
        self.edges = edges or []

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }


def build_swarm_graph(state: SwarmState) -> SwarmGraphTopology:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    queen_node = GraphNode(
        id="queen-1",
        label="Queen",
        role=AgentRole.queen,
    )
    nodes.append(queen_node)

    worker_nodes: list[GraphNode] = []
    for aid, agent_state in state.agents.items():
        if aid != "queen-1":
            spec = state.spec_map.get(aid)
            label = spec.name if spec else aid
            wnode = GraphNode(id=aid, label=label, role=AgentRole.worker)
            worker_nodes.append(wnode)
            nodes.append(wnode)

    topology = state.config.topology
    if topology == SwarmTopology.star:
        for wn in worker_nodes:
            edges.append(GraphEdge(source="queen-1", target=wn.id, label="dispatch"))
            edges.append(GraphEdge(source=wn.id, target="queen-1", label="result"))
    elif topology == SwarmTopology.chain:
        prev = "queen-1"
        for wn in worker_nodes:
            edges.append(GraphEdge(source=prev, target=wn.id, label="chain"))
            prev = wn.id
        edges.append(GraphEdge(source=prev, target="queen-1", label="result"))
    else:
        for wn in worker_nodes:
            edges.append(GraphEdge(source="queen-1", target=wn.id, label="dispatch"))

    return SwarmGraphTopology(nodes=nodes, edges=edges)
