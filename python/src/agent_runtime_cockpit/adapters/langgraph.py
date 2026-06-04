"""LangGraph Runtime Adapter.

Detects and inspects LangGraph-based agent projects.
Source: https://docs.langchain.com/oss/python/langgraph/
"""

from __future__ import annotations

import ast
import importlib
import inspect
import logging
import os
import sys
import uuid
import warnings
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ..adapters.base import CapabilityReport, DoctorAction
from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import (
    NodeType,
    RunEvent,
    RunRecord,
    RunStatus,
    SchemaInfo,
    WorkflowEdge,
    WorkflowInfo,
    WorkflowNode,
)
from ..workspace import iter_workspace_files
from .base import RuntimeAdapter

log = logging.getLogger(__name__)

HEURISTIC_REASON = "LangGraph library not installed; using AST scan"
REAL_IMPLEMENTATION_PATH = "adapters/langgraph.py -> from langgraph.graph import StateGraph"
LOCAL_FIX_STEPS = "pip install langgraph && call graph.get_graph() directly"
OWNER = "LangGraph Adapter Agent"
EXPORT_ENV = "ARC_LANGGRAPH_EXPORT"
LG_DEP_MISSING = "LG_DEP_MISSING"
LG_EXPORT_UNSET = "LG_EXPORT_UNSET"
LG_EXPORT_NOT_FOUND = "LG_EXPORT_NOT_FOUND"
LG_TARGET_INVALID = "LG_TARGET_INVALID"
LG_INVOKE_FAILED = "LG_INVOKE_FAILED"


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
            can_run=False,  # requires installed library
            can_trace=False,
            can_replay=False,
            can_export_schema=True,
            can_export_workflow=True,
            can_stream_events=False,
            can_audit=False,
        )

    def capability_report(self, workspace: Path) -> CapabilityReport:
        detected, _, evidence = self.detect(workspace)
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=".*default value of `allowed_objects` will change.*",
            )
            langgraph_spec = importlib.util.find_spec("langgraph")
        if langgraph_spec is None:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="missing_dependency",
                reason=LG_DEP_MISSING,
                detected_artifacts=evidence,
                required_env=[EXPORT_ENV],
                doctor_actions=[
                    DoctorAction(
                        id="install-langgraph",
                        label="Install LangGraph",
                        description="Install langgraph in this Python environment",
                        command="pip install langgraph",
                        safe_to_auto_run=False,
                    ),
                ],
            )
        target = os.environ.get(EXPORT_ENV)
        if not target:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="missing_export_target",
                reason=LG_EXPORT_UNSET,
                detected_artifacts=evidence,
                required_env=[EXPORT_ENV],
                doctor_actions=[
                    DoctorAction(
                        id="set-langgraph-export",
                        label="Set ARC_LANGGRAPH_EXPORT",
                        description=f"Set {EXPORT_ENV}=module:function to your compiled LangGraph graph",
                        command=f"export {EXPORT_ENV}=my_graph:graph",
                        safe_to_auto_run=False,
                    ),
                ],
            )
        try:
            exported = self._resolve_export(workspace, target, load_target=True)
            if not callable(exported) and not self._is_graph_like(exported):
                raise LangGraphRunError(
                    LG_TARGET_INVALID, "LangGraph export must be a graph or factory"
                )
        except LangGraphRunError as exc:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="detected_not_runnable",
                reason=exc.code,
                detected_artifacts=evidence,
                required_env=[EXPORT_ENV],
                doctor_actions=[
                    DoctorAction(
                        id="fix-langgraph-export",
                        label="Fix LangGraph Export",
                        description=f"Check {target}: it must resolve to a compiled graph",
                        command=f"python -c \"import {target.split(':')[0]}; print('ok')\"",
                        safe_to_auto_run=False,
                    ),
                ],
            )
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=detected,
            can_run=True,
            availability="runnable",
            detected_artifacts=evidence,
            required_env=[EXPORT_ENV],
        )

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        target = os.environ.get(EXPORT_ENV, "")
        return [
            DoctorAction(
                id="install-langgraph",
                label="Install LangGraph",
                description="Install langgraph in this Python environment",
                command="pip install langgraph",
                safe_to_auto_run=False,
            ),
            DoctorAction(
                id="set-langgraph-export",
                label="Set ARC_LANGGRAPH_EXPORT",
                description=f"Set {EXPORT_ENV}=module:function to your compiled LangGraph graph",
                command=f"export {EXPORT_ENV}=my_graph:graph"
                if not target
                else f"export {EXPORT_ENV}={target}",
                safe_to_auto_run=False,
            ),
        ]

    async def run_workflow(
        self, workflow_id: str, inputs: dict[str, Any] | None = None
    ) -> RunRecord:
        inputs = inputs or {}
        workspace = Path(str(inputs.get("workspace") or ".")).resolve()
        run_id = f"run-lg-{uuid.uuid4().hex[:8]}"
        # D-01: Capability Card enforcement (default mode=warn; never blocks)
        try:
            _cc_payload = self.enforce_capability_card(
                workflow_id=workflow_id, workspace=workspace
            )
            log.debug("capability_card_decision: %s", _cc_payload)
            inputs.setdefault("_capability_card_decision", _cc_payload)
        except Exception as exc:  # pragma: no cover
            log.warning("capability_card enforcement skipped: %s", exc)
        started = datetime.now(timezone.utc)
        events = [
            self._event(
                run_id, 0, "RUN_STARTED", {"workflow_id": workflow_id, "runtime": self.adapter_id}
            )
        ]

        if importlib.util.find_spec("langgraph") is None:
            raise NotImplementedError("Install langgraph in this Python environment.")
        target = os.environ.get(EXPORT_ENV)
        if not target:
            raise NotImplementedError(f"Set {EXPORT_ENV}=module:function")
        try:
            exported = self._resolve_export(workspace, target, load_target=True)
            graph = await self._materialize_graph(exported)
            stream_result = self._stream_graph(run_id, events, graph, inputs)
            if stream_result is None:
                final_state = graph.invoke(inputs)
                streamed = False
            else:
                final_state = stream_result
                streamed = True
        except LangGraphRunError as exc:
            return self._failed(workflow_id, run_id, started, events, exc.code, exc.message)
        except Exception as exc:
            return self._failed(
                workflow_id, run_id, started, events, LG_INVOKE_FAILED, self._redact(str(exc))
            )

        ended = datetime.now(timezone.utc)
        payload = {
            "state": final_state if isinstance(final_state, dict) else {"value": final_state}
        }
        events.append(self._event(run_id, 1, "RUN_COMPLETED", payload))
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=RunStatus.COMPLETED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={"state": payload["state"], "_external_target": target, "streamed": streamed},
        )

    def _stream_graph(
        self, run_id: str, events: list[RunEvent], graph: Any, inputs: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not hasattr(graph, "stream"):
            return None

        final_state: dict[str, Any] = {}
        for part in graph.stream(inputs, stream_mode=["updates", "messages"]):
            mode, data = self._stream_part(part)
            if mode == "messages":
                # MESSAGE_CHUNK is intentionally ephemeral; persisted traces keep coalesced node updates only.
                continue
            if mode != "updates":
                continue
            update = data if isinstance(data, dict) else {"value": data}
            final_state.update(self._flatten_update(update))
            events.append(
                self._event(
                    run_id, len(events), "NODE_UPDATE", {"update": self._redact_value(update)}
                )
            )
        return final_state

    def _stream_part(self, part: Any) -> tuple[str | None, Any]:
        if isinstance(part, tuple) and len(part) == 2 and isinstance(part[0], str):
            return part[0], part[1]
        if isinstance(part, dict) and "type" in part:
            return str(part.get("type")), part.get("data")
        if isinstance(part, dict):
            return "updates", part
        return None, part

    def _flatten_update(self, update: dict[str, Any]) -> dict[str, Any]:
        flattened: dict[str, Any] = {}
        for key, value in update.items():
            if isinstance(value, dict):
                flattened.update(value)
            else:
                flattened[key] = value
        return flattened

    def _redact_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._redact(value)
        if isinstance(value, dict):
            return {str(key): self._redact_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._redact_value(item) for item in value]
        return value

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
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message=".*default value of `allowed_objects` will change.*"
            )
            from langgraph.graph import StateGraph  # type: ignore  # noqa: F401
        target = os.environ.get(EXPORT_ENV, "")
        if not target or ":" not in target:
            raise NotImplementedError(
                "Set ARC_LANGGRAPH_EXPORT=module:function to export a workspace LangGraph"
            )

        exported = self._resolve_export(workspace, target, load_target=True)
        graph = exported() if callable(exported) and not self._is_graph_like(exported) else exported

        return [self._workflow_from_graph(workspace, target, graph)]

    def _resolve_export(self, workspace: Path, target: str, load_target: bool) -> Any:
        module_name, attr_name = self._parse_export_target(target)
        with _workspace_import_path(workspace):
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                raise LangGraphRunError(
                    LG_EXPORT_NOT_FOUND, f"LangGraph export module not found: {module_name}"
                )
            origin = Path(str(spec.origin or "")).resolve()
            allowed = [workspace.resolve()]
            src = (workspace / "src").resolve()
            if src.exists():
                allowed.append(src)
            if not any(origin == base or base in origin.parents for base in allowed):
                raise LangGraphRunError(
                    LG_TARGET_INVALID,
                    f"LangGraph export module resolves outside workspace: {module_name}",
                )
            if not load_target:
                return None
            module = importlib.import_module(module_name)
        if not hasattr(module, attr_name):
            raise LangGraphRunError(
                LG_EXPORT_NOT_FOUND, f"LangGraph export attribute not found: {target}"
            )
        return getattr(module, attr_name)

    def _parse_export_target(self, target: str) -> tuple[str, str]:
        if ":" not in target:
            raise LangGraphRunError(LG_EXPORT_UNSET, f"{EXPORT_ENV} must be module:function")
        module_name, attr_name = target.split(":", 1)
        if not module_name or not attr_name:
            raise LangGraphRunError(LG_EXPORT_UNSET, f"{EXPORT_ENV} must be module:function")
        if any(part in target for part in ("/", "\\", "..")) or module_name.startswith("."):
            raise LangGraphRunError(
                LG_TARGET_INVALID, "LangGraph export target must be a dotted module name"
            )
        return module_name, attr_name

    async def _materialize_graph(self, exported: Any) -> Any:
        graph = exported
        if callable(graph) and not self._is_graph_like(graph):
            graph = graph()
            if inspect.isawaitable(graph):
                graph = await graph
        if hasattr(graph, "compile"):
            graph = graph.compile()
        if not hasattr(graph, "invoke"):
            raise LangGraphRunError(
                LG_TARGET_INVALID, "LangGraph export must resolve to an object with invoke()"
            )
        return graph

    def _is_graph_like(self, value: Any) -> bool:
        return hasattr(value, "compile") or hasattr(value, "invoke")

    def _failed(
        self,
        workflow_id: str,
        run_id: str,
        started: datetime,
        events: list[RunEvent],
        code: str,
        message: str,
    ) -> RunRecord:
        ended = datetime.now(timezone.utc)
        events.append(
            self._event(
                run_id,
                1,
                "RUN_FAILED",
                {"error_code": code, "redacted_message": self._redact(message)},
            )
        )
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=RunStatus.FAILED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={"error_code": code, "error": self._redact(message)},
        )

    def _event(self, run_id: str, sequence: int, event_type: str, data: dict[str, Any]) -> RunEvent:
        return RunEvent(
            type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=run_id,
            sequence=sequence,
            data=data,
        )

    def _redact(self, text: str, cap: int = 4000) -> str:
        lowered = text.lower()
        if any(
            hint in lowered for hint in ("api_key", "authorization", "bearer", "secret", "token=")
        ):
            return "[redacted: message contained possible secret material]"
        return text[:cap]

    def _workflow_from_graph(self, workspace: Path, target: str, graph: object) -> WorkflowInfo:
        drawable = graph.get_graph() if hasattr(graph, "get_graph") else graph
        raw_nodes = getattr(drawable, "nodes", {})
        raw_edges = getattr(drawable, "edges", [])
        nodes = [
            WorkflowNode(id=str(node_id), label=str(node_id), type=NodeType.AGENT, metadata={})
            for node_id in (raw_nodes.keys() if hasattr(raw_nodes, "keys") else raw_nodes)
        ]
        edges: list[WorkflowEdge] = []
        for index, edge in enumerate(raw_edges):
            source = (
                getattr(edge, "source", None)
                or getattr(edge, "start", None)
                or (edge[0] if isinstance(edge, (tuple, list)) and len(edge) > 1 else None)
            )
            target_node = (
                getattr(edge, "target", None)
                or getattr(edge, "end", None)
                or (edge[1] if isinstance(edge, (tuple, list)) and len(edge) > 1 else None)
            )
            if source is None or target_node is None:
                continue
            edges.append(
                WorkflowEdge(
                    id=f"e{index}",
                    from_node=str(source),
                    to_node=str(target_node),
                    conditional=False,
                    metadata={},
                )
            )
        if not nodes:
            raise ValueError("Exported LangGraph has no nodes")
        return WorkflowInfo(
            id=f"wf-langgraph-{hash(target) % 10000:04d}",
            name="LangGraph Project",
            runtime="langgraph",
            source_file=str(workspace),
            nodes=nodes,
            edges=edges,
            entry_points=[nodes[0].id],
            metadata={"_langgraph_export": target},
        )

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
                        if (
                            isinstance(node.func, ast.Attribute)
                            and node.func.attr == "add_node"
                            and node.args
                        ):
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
                        if (
                            isinstance(node.func, ast.Attribute)
                            and node.func.attr in ("add_edge", "add_conditional_edges")
                            and len(node.args) >= 2
                        ):
                            a, b = node.args[0], node.args[1]
                            if isinstance(a, ast.Constant) and isinstance(b, ast.Constant):
                                eid = f"e-{a.value}-{b.value}"
                                edges.append(
                                    WorkflowEdge(
                                        id=eid,
                                        from_node=str(a.value),
                                        to_node=str(b.value),
                                        conditional=node.func.attr == "add_conditional_edges",
                                        metadata={},
                                    )
                                )
                break
            except Exception:
                pass

        if not nodes:
            return []

        nodes.insert(
            0, WorkflowNode(id="__start__", label="START", type=NodeType.START, metadata={})
        )
        nodes.append(WorkflowNode(id="__end__", label="END", type=NodeType.END, metadata={}))

        return [
            WorkflowInfo(
                id=f"wf-langgraph-{hash(str(workspace)) % 10000:04d}",
                name="LangGraph Project",
                runtime="langgraph",
                source_file=source_file,
                nodes=nodes,
                edges=edges,
                entry_points=["__start__"],
                metadata={"_ast_scanned": True},
            )
        ]

    def _fixture_workflow(self) -> WorkflowInfo:
        return WorkflowInfo(
            id="wf-langgraph-fixture",
            name="ReActAgent (fixture)",
            runtime="langgraph",
            source_file="examples/sample-langgraph-project/agent.py",
            nodes=[
                WorkflowNode(id="__start__", label="START", type=NodeType.START, metadata={}),
                WorkflowNode(id="agent", label="Agent", type=NodeType.AGENT, metadata={}),
                WorkflowNode(id="tools", label="Tools", type=NodeType.TOOL, metadata={}),
                WorkflowNode(id="__end__", label="END", type=NodeType.END, metadata={}),
            ],
            edges=[
                WorkflowEdge(
                    id="e1", from_node="__start__", to_node="agent", conditional=False, metadata={}
                ),
                WorkflowEdge(
                    id="e2",
                    from_node="agent",
                    to_node="tools",
                    label="use_tool",
                    conditional=True,
                    metadata={},
                ),
                WorkflowEdge(
                    id="e3",
                    from_node="agent",
                    to_node="__end__",
                    label="done",
                    conditional=True,
                    metadata={},
                ),
                WorkflowEdge(
                    id="e4", from_node="tools", to_node="agent", conditional=False, metadata={}
                ),
            ],
            entry_points=["__start__"],
            metadata={"_mock": True},
        )

    def export_schemas(self, workspace: Path) -> list[SchemaInfo]:
        return [
            SchemaInfo(
                id="schema-langgraph-state-fixture",
                name="AgentState",
                runtime="langgraph",
                schema={
                    "title": "AgentState",
                    "type": "object",
                    "properties": {
                        "messages": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Message history",
                        },
                        "next": {"type": "string", "description": "Next node to route to"},
                    },
                    "description": "[MOCK] LangGraph fixture schema",
                },
                source_file="examples/sample-langgraph-project/state.py",
            )
        ]


class LangGraphRunError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@contextmanager
def _workspace_import_path(workspace: Path) -> Iterator[None]:
    added: list[str] = []
    for candidate in (workspace, workspace / "src"):
        if candidate.exists():
            value = str(candidate.resolve())
            if value not in sys.path:
                sys.path.insert(0, value)
                added.append(value)
    try:
        yield
    finally:
        for value in added:
            try:
                sys.path.remove(value)
            except ValueError:
                pass
