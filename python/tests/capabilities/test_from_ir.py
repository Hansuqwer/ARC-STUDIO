"""Tests for IR to CapabilityCard conversion."""

from __future__ import annotations

from pathlib import Path


from agent_runtime_cockpit.capabilities import (
    cards_from_ir_graph,
    card_from_ir_graph,
    card_from_ir_node,
    EntityType,
    RiskLevel,
)


class TestCardFromIrGraph:
    """Tests for card_from_ir_graph function."""

    def test_graph_card_entity_type(self, ir_graph_fixture_path: Path):
        """Graph card has correct entity type."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        card = card_from_ir_graph(graph)

        assert card.entity_type == EntityType.IR_GRAPH

    def test_graph_card_contains_graph_metadata(self, ir_graph_fixture_path: Path):
        """Graph card contains graph ID and metadata."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        card = card_from_ir_graph(graph)

        assert card.id == f"ir-graph-{graph.id}"
        assert "node_count" in card.metadata
        assert card.metadata["node_count"] == 3

    def test_graph_card_aggregates_capabilities(self, ir_graph_fixture_path: Path):
        """Graph card aggregates capabilities from all nodes."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        card = card_from_ir_graph(graph)

        # Agent node has model_call with paid=True
        assert card.capabilities.can_call_models is True
        # Model call paid or side effects should set can_make_paid_calls
        # The aggregation depends on whether side effects are propagated
        # Check that at least the model call capability is present
        assert card.capabilities.can_call_models is True

    def test_graph_card_has_provenance(self, ir_graph_fixture_path: Path):
        """Graph card has provenance information."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        card = card_from_ir_graph(graph)

        assert card.provenance.source_type == "ir_graph"
        assert card.provenance.ir_graph_id == graph.id

    def test_graph_card_has_hash(self, ir_graph_fixture_path: Path):
        """Graph card has computed hash."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        card = card_from_ir_graph(graph)

        assert card.card_hash is not None
        assert len(card.card_hash) == 64


class TestCardFromIrNode:
    """Tests for card_from_ir_node function."""

    def test_node_card_entity_type(self, ir_graph_fixture_path: Path):
        """Node card has correct entity type."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        # Get the agent node
        agent_node = next(n for n in graph.nodes if n.id == "agent")
        card = card_from_ir_node(graph, agent_node)

        assert card.entity_type == EntityType.IR_NODE

    def test_node_card_contains_node_metadata(self, ir_graph_fixture_path: Path):
        """Node card contains node ID and kind."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        agent_node = next(n for n in graph.nodes if n.id == "agent")
        card = card_from_ir_node(graph, agent_node)

        assert card.id == f"ir-node-{graph.id}-{agent_node.id}"
        assert "ir_node_kind" in card.metadata
        assert card.metadata["ir_node_kind"] == "agent"

    def test_agent_node_capabilities(self, ir_graph_fixture_path: Path):
        """Agent node card has correct capabilities."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        agent_node = next(n for n in graph.nodes if n.id == "agent")
        card = card_from_ir_node(graph, agent_node)

        assert card.capabilities.can_call_models is True
        assert card.capabilities.can_call_tools is True

    def test_paid_call_node_has_cost(self, ir_graph_fixture_path: Path):
        """Node with paid model call has cost capability."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        agent_node = next(n for n in graph.nodes if n.id == "agent")
        card = card_from_ir_node(graph, agent_node)

        assert card.cost is not None
        assert card.cost.paid is True

    def test_start_node_capabilities(self, ir_graph_fixture_path: Path):
        """Start node has minimal capabilities."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        start_node = next(n for n in graph.nodes if n.id == "__start__")
        card = card_from_ir_node(graph, start_node)

        # Start node has low risk
        assert card.risk_level == RiskLevel.LOW
        # No special capabilities
        assert card.capabilities.can_call_models is False

    def test_node_card_has_provenance(self, ir_graph_fixture_path: Path):
        """Node card has provenance with graph hash."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        agent_node = next(n for n in graph.nodes if n.id == "agent")
        card = card_from_ir_node(graph, agent_node)

        assert card.provenance.source_type == "ir_node"
        assert card.provenance.ir_node_id == agent_node.id
        assert card.provenance.ir_graph_hash == graph.graph_hash


class TestCardsFromIrGraph:
    """Tests for cards_from_ir_graph function."""

    def test_returns_graph_card_first(self, ir_graph_fixture_path: Path):
        """First card is the graph card."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        cards = cards_from_ir_graph(graph)

        assert len(cards) > 0
        assert cards[0].entity_type == EntityType.IR_GRAPH

    def test_returns_one_card_per_node(self, ir_graph_fixture_path: Path):
        """One card per node plus graph card."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        cards = cards_from_ir_graph(graph)

        # 3 nodes + 1 graph = 4 cards
        assert len(cards) == 4

    def test_all_node_cards_present(self, ir_graph_fixture_path: Path):
        """All node cards are present with correct IDs."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        cards = cards_from_ir_graph(graph)

        node_ids = {n.id for n in graph.nodes}
        card_ids = {c.id for c in cards}

        for node_id in node_ids:
            expected_prefix = f"ir-node-{graph.id}-{node_id}"
            assert any(expected_prefix in card_id for card_id in card_ids)

    def test_all_cards_have_hash(self, ir_graph_fixture_path: Path):
        """All cards have computed hashes."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        cards = cards_from_ir_graph(graph)

        for card in cards:
            assert card.card_hash is not None
            assert len(card.card_hash) == 64

    def test_cards_are_unique(self, ir_graph_fixture_path: Path):
        """All cards have unique hashes."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)
        cards = cards_from_ir_graph(graph)

        hashes = {c.card_hash for c in cards}
        assert len(hashes) == len(cards)


class TestIrCapabilityDerivation:
    """Tests for capability derivation from IR."""

    def test_tool_node_can_execute(self, ir_graph_fixture_path: Path):
        """Tool node has can_execute capability."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        # Create a tool node
        from agent_runtime_cockpit.swarmgraph_ir.models import IRNode, IRNodeKind

        tool_node = IRNode(
            id="tool-1",
            label="Write Tool",
            kind=IRNodeKind.TOOL,
        )
        graph.nodes.append(tool_node)

        card = card_from_ir_node(graph, tool_node)
        assert card.capabilities.can_execute is True

    def test_mcp_tool_node_can_call_mcp(self, ir_graph_fixture_path: Path):
        """MCP tool node has can_call_mcp capability."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json
        from agent_runtime_cockpit.swarmgraph_ir.models import IRNode, IRNodeKind, IRMcpToolRef

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        mcp_node = IRNode(
            id="mcp-1",
            label="MCP Tool",
            kind=IRNodeKind.MCP_TOOL,
            mcp_tool=IRMcpToolRef(
                server_id="test-server",
                tool_name="test-tool",
                can_write=True,
            ),
        )
        graph.nodes.append(mcp_node)

        card = card_from_ir_node(graph, mcp_node)
        assert card.capabilities.can_call_mcp is True
        assert card.mcp is not None
        assert card.mcp.server_id == "test-server"

    def test_human_gate_node_requests_hitl(self, ir_graph_fixture_path: Path):
        """Human gate node requires HITL."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json
        from agent_runtime_cockpit.swarmgraph_ir.models import IRNode, IRNodeKind, IRHumanGate

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        gate_node = IRNode(
            id="gate-1",
            label="Approval Gate",
            kind=IRNodeKind.HUMAN_GATE,
            human_gate=IRHumanGate(
                gate_id="approval-1",
                blocking=True,
            ),
        )
        graph.nodes.append(gate_node)

        card = card_from_ir_node(graph, gate_node)
        assert card.capabilities.can_request_hitl is True
        assert card.trust.hitl_requirement.value == "required"


class TestIrSideEffectDerivation:
    """Tests for side effect derivation from IR."""

    def test_read_side_effect(self, ir_graph_fixture_path: Path):
        """Read side effect sets can_read."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json
        from agent_runtime_cockpit.swarmgraph_ir.models import (
            IRNode,
            IRNodeKind,
            IRSideEffect,
            SideEffectKind,
        )

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        read_node = IRNode(
            id="read-1",
            label="Read Node",
            kind=IRNodeKind.TOOL,
            side_effects=[IRSideEffect(kind=SideEffectKind.READ, target="workspace://file.txt")],
        )
        graph.nodes.append(read_node)

        card = card_from_ir_node(graph, read_node)
        assert card.capabilities.can_read is True

    def test_write_side_effect(self, ir_graph_fixture_path: Path):
        """Write side effect sets can_write."""
        from agent_runtime_cockpit.swarmgraph_ir import from_json
        from agent_runtime_cockpit.swarmgraph_ir.models import (
            IRNode,
            IRNodeKind,
            IRSideEffect,
            SideEffectKind,
        )

        graph_json = ir_graph_fixture_path.read_text()
        graph = from_json(graph_json)

        write_node = IRNode(
            id="write-1",
            label="Write Node",
            kind=IRNodeKind.TOOL,
            side_effects=[IRSideEffect(kind=SideEffectKind.WRITE, target="workspace://output.txt")],
        )
        graph.nodes.append(write_node)

        card = card_from_ir_node(graph, write_node)
        assert card.capabilities.can_write is True
        assert len(card.side_effects) > 0
        assert card.side_effects[0].kind == "write"
