"""
LangGraph Runtime Adapter

Detects and inspects LangGraph-based agent projects.
Source: https://docs.langchain.com/oss/python/langgraph/

MOCK_REASON: LangGraph library may not be installed. AST heuristics used as fallback.
REAL_IMPLEMENTATION_PATH: from langgraph.graph import StateGraph; graph.get_graph()
LOCAL_FIX_STEPS: pip install langgraph && use graph.get_graph().draw_mermaid_png() or .nodes/.edges
OWNER: LangGraph Adapter Agent
REMOVE_BEFORE: Beta
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path

from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import (
    WorkflowInfo, WorkflowNode, WorkflowEdge, SchemaInfo,
    NodeType
)
from ..workspace import iter_workspace_files
from .base import RuntimeAdapter

log = logging.getLogger(__name__)

MOCK_REASON = "LangGraph library not installed; using AST scan + fixture"
REAL_IMPLEMENTATION_PATH = "adapters/langgraph.py → from langgraph.graph import StateGraph"
LOCAL_FIX_STEPS = "pip install langgraph && call graph.get_graph() directly"
OWNER = "LangGraph Adapter Agent"
REMOVE_BEFORE = "Beta"


class LangGraphAdapter(RuntimeAdapter):

    @property
    def adapter_id(self) -> str:
        return "langgraph"

    @property
    def adapter_name(self) -> str:
        return "LangGraph"

    def capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(
            can_inspect=True,
            can_run=False,          # requires installed library
            can_trace=False,
            can_replay=False,
            can_export_schema=True,
            can_export_workflow=True,
            can_stream_events=False,
            can_audit=False,
        )

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        evidence: list[str] = []
        score = 0.0

        # Check pyproject.toml / requirements.txt for langgraph
        for req_file in ["pyproject.toml", "requirements.txt", "requirements-dev.txt"]:
            p = workspace / req_file
            if p.exists():
                try:
                    text = p.read_text()
                    if "langgraph" in text.lower():
                        evidence.append(f"langgraph in {req_file}")
                        score += 0.9
                except Exception:
                    pass

        # Check Python files for StateGraph / langgraph imports
        py_files = iter_workspace_files(workspace, (".py",))
        for py_file in py_files[:20]:
            try:
                text = py_file.read_text(errors="ignore")
                if "StateGraph" in text or "from langgraph" in text or "import langgraph" in text:
                    evidence.append(f"langgraph import in {py_file.name}")
                    score += 0.7
                    break
            except Exception:
                pass

        # Check example fixture dir
        if (workspace / "examples" / "sample-langgraph-project").exists():
            evidence.append("sample-langgraph-project fixture present")
            score += 0.6

        detected = score > 0.3
        return detected, min(score, 1.0), evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        """Try real LangGraph export, fallback to AST scan, then fixture."""
        # Try real import
        try:
            return self._real_export(workspace)
        except ImportError:
            log.debug("langgraph not installed, using AST scan")
        except Exception as e:
            log.warning("LangGraph real export failed: %s", e)

        # AST scan
        try:
            result = self._ast_scan(workspace)
            if result:
                return result
        except Exception as e:
            log.warning("LangGraph AST scan failed: %s", e)

        return [self._fixture_workflow()]

    def _real_export(self, workspace: Path) -> list[WorkflowInfo]:
        """Attempt real LangGraph export using the installed library."""
        from langgraph.graph import StateGraph  # type: ignore  # noqa
        # TODO: dynamically load workspace graphs
        raise NotImplementedError("Dynamic LangGraph workspace loading not yet implemented")

    def _ast_scan(self, workspace: Path) -> list[WorkflowInfo]:
        """Scan for StateGraph definitions via AST."""
        nodes: list[WorkflowNode] = []
        edges: list[WorkflowEdge] = []
        source_file = None

        py_files = iter_workspace_files(workspace, (".py",))

        for py_file in py_files[:20]:
            try:
                text = py_file.read_text(errors="ignore")
                if "StateGraph" not in text:
                    continue
                source_file = str(py_file)
                tree = ast.parse(text)

                # Find graph.add_node("name", ...) calls
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if (isinstance(node.func, ast.Attribute)
                                and node.func.attr == "add_node"
                                and node.args):
                            arg = node.args[0]
                            if isinstance(arg, ast.Constant):
                                nid = str(arg.value)
                                wnode = WorkflowNode(
                                    id=nid, label=nid, type=NodeType.AGENT, metadata={}
                                )
                                if not any(n.id == nid for n in nodes):
                                    nodes.append(wnode)

                # Find graph.add_edge(from, to) calls
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if (isinstance(node.func, ast.Attribute)
                                and node.func.attr in ("add_edge", "add_conditional_edges")
                                and len(node.args) >= 2):
                            a, b = node.args[0], node.args[1]
                            if isinstance(a, ast.Constant) and isinstance(b, ast.Constant):
                                eid = f"e-{a.value}-{b.value}"
                                edges.append(WorkflowEdge(
                                    id=eid, from_node=str(a.value), to_node=str(b.value),
                                    conditional=node.func.attr == "add_conditional_edges",
                                    metadata={},
                                ))
                break
            except Exception:
                pass

        if not nodes:
            return []

        nodes.insert(0, WorkflowNode(id="__start__", label="START", type=NodeType.START, metadata={}))
        nodes.append(WorkflowNode(id="__end__", label="END", type=NodeType.END, metadata={}))

        return [WorkflowInfo(
            id=f"wf-langgraph-{hash(str(workspace)) % 10000:04d}",
            name="LangGraph Project",
            runtime="langgraph",
            source_file=source_file,
            nodes=nodes,
            edges=edges,
            entry_points=["__start__"],
            metadata={"_ast_scanned": True},
        )]

    def _fixture_workflow(self) -> WorkflowInfo:
        return WorkflowInfo(
            id="wf-langgraph-fixture",
            name="ReActAgent (fixture)",
            runtime="langgraph",
            source_file="examples/sample-langgraph-project/agent.py",
            nodes=[
                WorkflowNode(id="__start__", label="START",      type=NodeType.START,  metadata={}),
                WorkflowNode(id="agent",      label="Agent",      type=NodeType.AGENT,  metadata={}),
                WorkflowNode(id="tools",      label="Tools",      type=NodeType.TOOL,   metadata={}),
                WorkflowNode(id="__end__",    label="END",        type=NodeType.END,    metadata={}),
            ],
            edges=[
                WorkflowEdge(id="e1", from_node="__start__", to_node="agent",     conditional=False, metadata={}),
                WorkflowEdge(id="e2", from_node="agent",      to_node="tools",    label="use_tool",  conditional=True, metadata={}),
                WorkflowEdge(id="e3", from_node="agent",      to_node="__end__",  label="done",      conditional=True, metadata={}),
                WorkflowEdge(id="e4", from_node="tools",      to_node="agent",    conditional=False, metadata={}),
            ],
            entry_points=["__start__"],
            metadata={"_mock": True},
        )

    def export_schemas(self, workspace: Path) -> list[SchemaInfo]:
        return [SchemaInfo(
            id="schema-langgraph-state-fixture",
            name="AgentState",
            runtime="langgraph",
            schema={
                "title": "AgentState",
                "type": "object",
                "properties": {
                    "messages": {"type": "array", "items": {"type": "object"}, "description": "Message history"},
                    "next":     {"type": "string", "description": "Next node to route to"},
                },
                "description": "[MOCK] LangGraph fixture schema",
            },
            source_file="examples/sample-langgraph-project/state.py",
        )]
