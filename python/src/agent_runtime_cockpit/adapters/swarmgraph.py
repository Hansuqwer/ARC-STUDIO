"""
SwarmGraph Runtime Adapter

Dual-path adapter: uses the native SwarmGraphRunner (internal Python runtime)
by default. Falls back to external CLI subprocess when ARC_SWARMGRAPH_CLI is
explicitly configured (provider-backed mode).

Source: https://github.com/Hansuqwer/SwarmGraph
"""
from __future__ import annotations

import ast
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..adapters.base import CapabilityReport, DoctorAction
from ..gating import require_dual_gate
from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import (
    WorkflowInfo, WorkflowNode, WorkflowEdge, SchemaInfo,
    NodeType, RunRecord, RunEvent, RunStatus
)
from ..security.redaction import Redactor
from ..workspace import iter_workspace_files
from ..swarmgraph import SwarmGraphRunner as NativeSwarmGraphRunner
from ..swarmgraph.config import ExecutionMode, SwarmGraphConfig
from ..swarmgraph.events import SwarmGraphEvent, SwarmGraphEventKind
from .base import RuntimeAdapter

log = logging.getLogger(__name__)

HEURISTIC_REASON = "SwarmGraph library not installed; using file-scan heuristics"
REAL_IMPLEMENTATION_PATH = "adapters/swarmgraph.py -> import swarmgraph; graph.export()"
LOCAL_FIX_STEPS = "pip install git+https://github.com/Hansuqwer/SwarmGraph"
OWNER = "SwarmGraph Adapter Agent"

# Environment variable allowlist for subprocess execution
# Only these system vars + ARC_SWARMGRAPH_* vars are passed to subprocess
SWARMGRAPH_ENV_ALLOWLIST = [
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "SHELL",
    "TMPDIR",
    "VIRTUAL_ENV",
]

# Detection signals for SwarmGraph projects
_DETECTION_SIGNALS = [
    ("swarmgraph.yaml",    0.9),
    ("swarmgraph.yml",     0.9),
    ("swarmgraph.toml",    0.8),
    ("swarmgraph",         0.7),
    ("graph.py",           0.3),
    ("swarm.py",           0.4),
    ("agents.py",          0.2),
    ("pyproject.toml",     0.1),  # needs swarmgraph in deps
]


class SwarmGraphAdapter(RuntimeAdapter):

    def __init__(self):
        """Initialize SwarmGraph adapter with redactor for output sanitization."""
        super().__init__()
        self._redactor = Redactor()

    @property
    def adapter_id(self) -> str:
        return "swarmgraph"

    @property
    def adapter_name(self) -> str:
        return "SwarmGraph"

    def _filtered_env(self) -> dict[str, str]:
        """Return filtered environment variables safe for subprocess execution.
        
        Only passes through:
        - Allowlisted system variables (PATH, HOME, etc.)
        - ARC_SWARMGRAPH_* prefixed variables
        - PYTHONPATH if present
        - PYTHONWARNINGS override
        
        This prevents leaking sensitive environment variables like API keys,
        AWS credentials, GitHub tokens, etc. to subprocess execution.
        """
        env = {}
        
        # Add allowlisted system vars
        for key in SWARMGRAPH_ENV_ALLOWLIST:
            if key in os.environ:
                env[key] = os.environ[key]
        
        # Add all ARC_SWARMGRAPH_* vars
        for key, value in os.environ.items():
            if key.startswith("ARC_SWARMGRAPH_"):
                env[key] = value
        
        # Add PYTHONPATH if present
        if "PYTHONPATH" in os.environ:
            env["PYTHONPATH"] = os.environ["PYTHONPATH"]
        
        # Add PYTHONWARNINGS override
        env["PYTHONWARNINGS"] = "ignore"
        
        return env

    def capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(
            can_inspect=True,
            can_run=True,
            can_trace=True,
            can_replay=False,
            can_export_schema=True,
            can_export_workflow=True,
            can_stream_events=False,
            can_audit=False,
        )

    def capability_report(self, workspace: Path) -> CapabilityReport:
        detected, _, evidence = self.detect(workspace)
        doctor: list[DoctorAction] = []
        cli_available = False
        try:
            self._resolve_cli(workspace)
            cli_available = True
        except Exception:
            doctor.append(DoctorAction(
                id="install-swarmgraph",
                label="Install SwarmGraph",
                description="Install the SwarmGraph Python package",
                command="pip install git+https://github.com/Hansuqwer/SwarmGraph",
                safe_to_auto_run=False,
            ))

        if detected or cli_available:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=True,
                availability="runnable",
                reason=None if cli_available else "Using native SwarmGraph runtime (fake_offline mode)",
                detected_artifacts=evidence,
                required_env=["ARC_SWARMGRAPH_CLI"] if cli_available else [],
                doctor_actions=doctor if not cli_available else [],
                fake_offline_supported=True,
                local_real_gated=cli_available,
            )
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=False,
            can_run=False,
            availability="not_detected",
            detected_artifacts=evidence,
            doctor_actions=doctor,
        )

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        """Return fix actions for SwarmGraph configuration issues."""
        actions: list[DoctorAction] = []
        try:
            self._resolve_cli(workspace)
        except Exception:
            actions.append(DoctorAction(
                id="install-swarmgraph",
                label="Install SwarmGraph",
                description="Install the SwarmGraph Python package",
                command="pip install git+https://github.com/Hansuqwer/SwarmGraph",
                safe_to_auto_run=False,
            ))
        if not os.environ.get("ARC_SWARMGRAPH_CLI"):
            actions.append(DoctorAction(
                id="set-swarmgraph-cli",
                label="Set ARC_SWARMGRAPH_CLI",
                description="Set the SwarmGraph CLI environment variable",
                command="export ARC_SWARMGRAPH_CLI=swarmgraph",
                safe_to_auto_run=False,
            ))
        return actions

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        evidence: list[str] = []
        score = 0.0

        for filename, weight in _DETECTION_SIGNALS:
            p = workspace / filename
            if p.exists():
                evidence.append(f"{filename} found")
                score += weight

        # Check pyproject.toml for swarmgraph dependency
        pyproject = workspace / "pyproject.toml"
        if pyproject.exists():
            try:
                text = pyproject.read_text()
                if "swarmgraph" in text.lower():
                    evidence.append("swarmgraph in pyproject.toml dependencies")
                    score += 0.8
            except Exception:
                pass

        # Check Python files for SwarmGraph imports
        py_files = iter_workspace_files(workspace, (".py",))
        for py_file in py_files[:20]:  # cap scan
            try:
                text = py_file.read_text(errors="ignore")
                if "swarmgraph" in text.lower() or "SwarmGraph" in text:
                    evidence.append(f"swarmgraph import in {py_file.name}")
                    score += 0.5
                    break
            except Exception:
                pass

        # Check example fixture dir
        if (workspace / "examples" / "sample-swarmgraph-project").exists():
            evidence.append("sample-swarmgraph-project fixture present")
            score += 0.6

        detected = score > 0.3
        confidence = min(score, 1.0)
        return detected, confidence, evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        """
        Export workflow topology.
        Uses AST-based heuristics when SwarmGraph library unavailable.
        """
        try:
            return self._scan_workflow(workspace)
        except Exception as e:
            log.warning("SwarmGraph workflow scan failed: %s — using fixture", e)
            return [self._fixture_workflow()]

    def _scan_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        """Best-effort AST scan for agent graph structure."""
        nodes: list[WorkflowNode] = []
        edges: list[WorkflowEdge] = []

        py_files = iter_workspace_files(workspace, (".py",))

        for py_file in py_files[:30]:
            try:
                tree = ast.parse(py_file.read_text(errors="ignore"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if any(b.id == "Agent" for b in node.bases if isinstance(b, ast.Name)):
                            wnode = WorkflowNode(
                                id=node.name.lower(),
                                label=node.name,
                                type=NodeType.AGENT,
                                metadata={"source_file": str(py_file)},
                            )
                            if not any(n.id == wnode.id for n in nodes):
                                nodes.append(wnode)
            except Exception:
                pass

        if not nodes:
            return [self._fixture_workflow()]

        # Synthesize start/end
        nodes.insert(0, WorkflowNode(id="start", label="Start", type=NodeType.START, metadata={}))
        nodes.append(WorkflowNode(id="end", label="End", type=NodeType.END, metadata={}))

        # Simple linear edges for scanned agents
        for i in range(len(nodes) - 1):
            edges.append(WorkflowEdge(
                id=f"e{i}",
                from_node=nodes[i].id,
                to_node=nodes[i + 1].id,
                conditional=False,
                metadata={},
            ))

        return [WorkflowInfo(
            id=f"wf-swarmgraph-{hash(str(workspace)) % 10000:04d}",
            name="SwarmGraph Project",
            runtime="swarmgraph",
            source_file=str(py_files[0]) if py_files else None,
            nodes=nodes,
            edges=edges,
            entry_points=["start"],
            metadata={"_scanned": True},
        )]

    async def run_workflow(self, workflow_id: str, inputs: dict[str, Any] | None = None) -> RunRecord:
        inputs = inputs or {}
        workspace = Path(str(inputs.get("workspace") or ".")).resolve()
        prompt = str(inputs.get("prompt") or f"Run ARC workflow {workflow_id}")

        if os.environ.get("ARC_SWARMGRAPH_CLI"):
            self._resolve_cli(workspace)
            return await self._run_cli_workflow(workflow_id, workspace, prompt, inputs)
        return await self._run_native_workflow(workflow_id, prompt, inputs)

    async def _run_native_workflow(
        self, workflow_id: str, prompt: str, inputs: dict[str, Any] | None = None,
    ) -> RunRecord:
        inputs = inputs or {}
        num_workers = int(inputs.get("max_agents", 3))
        max_rounds = int(inputs.get("max_rounds", 1))

        cfg = SwarmGraphConfig(
            num_workers=num_workers,
            max_rounds=max_rounds,
            execution_mode=ExecutionMode.fake_offline,
            allow_paid_calls=False,
            require_hitl=False,
            enable_audit=False,
            enable_budget=False,
        )
        runner = NativeSwarmGraphRunner(config=cfg)

        def _run() -> dict[str, Any]:
            return runner.run(prompt=prompt)

        run_id = f"run-sg-{uuid.uuid4().hex[:8]}"
        started = datetime.now(timezone.utc)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _run)

        events: list[RunEvent] = []
        events.append(self._event(run_id, 0, "RUN_STARTED", {
            "workflow_id": workflow_id,
            "prompt": prompt,
            "mode": "native_fake_offline",
        }))

        sw_events = runner.get_events() or []
        for i, sw_evt in enumerate(sw_events, start=1):
            proto_events = self._map_swarmgraph_event(sw_evt, run_id, i)
            events.extend(proto_events)

        worker_count = num_workers
        swarm_status = result.get("status", "completed")

        seq = len(events)
        events.append(self._event(run_id, seq, "RUN_COMPLETED", {
            "swarm_id": result.get("swarm_id"),
            "worker_count": worker_count,
            "total_tasks": result.get("total_tasks", 0),
            "completed_tasks": result.get("completed_tasks", 0),
            "mode": "native_fake_offline",
        }))

        ended = datetime.now(timezone.utc)
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime="swarmgraph",
            status=RunStatus.COMPLETED if swarm_status == "completed" else RunStatus.FAILED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={
                "mode": "native_fake_offline",
                "swarm_id": result.get("swarm_id"),
                "swarm_status": swarm_status,
                "worker_count": worker_count,
                "total_tasks": result.get("total_tasks", 0),
                "completed_tasks": result.get("completed_tasks", 0),
                "results": result.get("results", []),
            },
        )

    def _map_swarmgraph_event(
        self, sw_evt: SwarmGraphEvent, run_id: str, sequence: int,
    ) -> list[RunEvent]:
        kind = sw_evt.kind
        data = dict(sw_evt.data)
        if kind == SwarmGraphEventKind.worker:
            return [self._event(run_id, sequence, "NODE_COMPLETED", {
                "node": data.get("worker_id", "unknown"),
                "task_id": data.get("task_id", ""),
                "duration_seconds": data.get("duration_seconds", 0),
                "cost_usd": data.get("cost_usd", 0),
                "status": "completed" if not data.get("has_error") else "failed",
            })]
        if kind == SwarmGraphEventKind.consensus:
            return [self._event(run_id, sequence, "SWARMGRAPH_CONSENSUS", data)]
        if kind == SwarmGraphEventKind.budget:
            return [self._event(run_id, sequence, "BUDGET_UPDATE", data)]
        if kind == SwarmGraphEventKind.hitl:
            return [self._event(run_id, sequence, "HITL_REQUIRED", data)]
        if kind == SwarmGraphEventKind.error:
            return [self._event(run_id, sequence, "RUN_FAILED", data)]
        if kind == SwarmGraphEventKind.topology:
            return [self._event(run_id, sequence, "SWARMGRAPH_TOPOLOGY", data)]
        return [self._event(run_id, sequence, "STATE_CHANGE", data)]

    async def _run_cli_workflow(
        self, workflow_id: str, workspace: Path, prompt: str, inputs: dict[str, Any] | None = None,
    ) -> RunRecord:
        """Run via external SwarmGraph CLI subprocess (provider-backed mode)."""
        inputs = inputs or {}
        cli = self._resolve_cli(workspace)
        backend, allow_costs = require_dual_gate("SWARMGRAPH")
        provider = os.environ.get("AI_PROVIDER_SWARM_GATEWAY_DEFAULT_PROVIDER", "openai")
        run_id = f"run-sg-{uuid.uuid4().hex[:8]}"
        started = datetime.now(timezone.utc)

        cmd = [
            str(cli),
            "swarm",
            "--prompt",
            prompt,
            "--backend",
            backend.value,
            "--provider",
            provider,
            "--max-agents",
            str(inputs.get("max_agents", 1)),
            "--max-tokens",
            str(inputs.get("max_tokens", 128)),
            "--json",
        ]
        if not allow_costs:
            cmd.insert(-1, "--no-cost")

        events = [self._event(run_id, 0, "RUN_STARTED", {"workflow_id": workflow_id, "backend": backend.value, "prompt": prompt, "cost_allowed": allow_costs})]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._filtered_env(),
        )
        stdout_b, stderr_b = await proc.communicate()
        stdout = stdout_b.decode(errors="replace").strip()
        stderr = stderr_b.decode(errors="replace").strip()
        ended = datetime.now(timezone.utc)

        if proc.returncode != 0:
            events.append(self._event(run_id, 1, "RUN_FAILED", {"exit_code": proc.returncode, "stderr": self._redactor.redact_string(stderr[-2000:]), "stdout": self._redactor.redact_string(stdout[-2000:])}))
            return RunRecord(
                id=run_id,
                workflow_id=workflow_id,
                runtime="swarmgraph",
                status=RunStatus.FAILED,
                started_at=started.isoformat(),
                ended_at=ended.isoformat(),
                events=events,
                metadata={
                    "backend": backend,
                    "provider": provider,
                    "prompt": prompt,
                    "cost_allowed": allow_costs,
                    "exit_code": proc.returncode,
                    "stderr": self._redactor.redact_string(stderr[-2000:]),
                    "_external_command": "swarmgraph swarm --json",
                },
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            events.append(self._event(run_id, 1, "RUN_FAILED", {"error": f"Invalid SwarmGraph JSON: {exc}", "stdout": self._redactor.redact_string(stdout[:2000]), "stderr": self._redactor.redact_string(stderr[-2000:])}))
            return RunRecord(
                id=run_id,
                workflow_id=workflow_id,
                runtime="swarmgraph",
                status=RunStatus.FAILED,
                started_at=started.isoformat(),
                ended_at=ended.isoformat(),
                events=events,
                metadata={
                    "backend": backend,
                    "provider": provider,
                    "prompt": prompt,
                    "cost_allowed": allow_costs,
                    "stdout": self._redactor.redact_string(stdout[:2000]),
                    "stderr": self._redactor.redact_string(stderr[-2000:]),
                    "_external_command": "swarmgraph swarm --json",
                },
            )

        worker_count = int(payload.get("worker_count", 0))
        topology_nodes = [{"id": "queen", "role": "queen", "label": "SwarmGraph Queen"}]
        topology_edges: list[dict[str, str]] = []
        for i in range(worker_count):
            worker_id = f"worker-{i + 1}"
            topology_nodes.append({"id": worker_id, "role": "worker", "label": worker_id})
            topology_edges.append({"source": "queen", "target": worker_id, "type": "assignment"})
        events.append(self._event(run_id, 1, "SWARMGRAPH_TOPOLOGY", {
            "nodes": topology_nodes,
            "edges": topology_edges,
            "source": "swarmgraph_standalone",
            "task_id": payload.get("swarm_id", ""),
            "worker_count": worker_count,
        }))

        events.append(self._event(run_id, 2, "SWARMGRAPH_CONSENSUS", {
            "task_id": payload.get("swarm_id", ""),
            "consensus_reached": payload.get("status") == "completed",
            "confidence": 1.0 if payload.get("status") == "completed" else 0.0,
            "strategy": "standalone_swarmgraph",
            "voters": [f"worker-{i + 1}" for i in range(worker_count)],
            "source": "swarmgraph_standalone",
        }))

        events.append(self._event(run_id, 3, "NODE_COMPLETED", {"node": "swarmgraph.cli", "status": payload.get("status")}))
        events.append(self._event(run_id, 4, "MESSAGE", {"output": payload.get("final_output", "")}))
        events.append(self._event(run_id, 5, "RUN_COMPLETED", {"swarm_id": payload.get("swarm_id"), "worker_count": worker_count}))
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime="swarmgraph",
            status=RunStatus.COMPLETED if payload.get("status") == "completed" else RunStatus.FAILED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={
                "backend": backend,
                "provider": provider,
                "prompt": prompt,
                "cost_allowed": allow_costs,
                "swarm_id": payload.get("swarm_id"),
                "swarm_status": payload.get("status"),
                "final_output": payload.get("final_output", ""),
                "_external_command": "swarmgraph swarm --json",
            },
        )

    def _resolve_cli(self, workspace: Path) -> Path:
        configured = os.environ.get("ARC_SWARMGRAPH_CLI")
        if not configured:
            raise FileNotFoundError(
                "SwarmGraph launcher not configured. Set ARC_SWARMGRAPH_CLI to "
                "a trusted launcher outside the workspace."
            )

        cli = Path(configured).expanduser().resolve()
        root = workspace.resolve()

        if not cli.exists() or not cli.is_file():
            raise FileNotFoundError(f"Configured SwarmGraph launcher not found: {cli}")
        if root in cli.parents or cli == root:
            raise PermissionError(
                "ARC_SWARMGRAPH_CLI must not point inside the workspace. "
                "Workspace-rooted launchers are rejected for security."
            )
        if not os.access(str(cli), os.X_OK):
            raise PermissionError(
                f"Configured SwarmGraph launcher is not executable: {cli}"
            )

        return cli

    def _event(self, run_id: str, sequence: int, event_type: str, data: dict[str, Any]) -> RunEvent:
        return RunEvent(
            type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=run_id,
            sequence=sequence,
            data=data,
        )

    def _fixture_workflow(self) -> WorkflowInfo:
        """Return fixture workflow for demo/testing."""
        return WorkflowInfo(
            id="wf-swarmgraph-fixture",
            name="ResearchSwarm (fixture)",
            runtime="swarmgraph",
            source_file="examples/sample-swarmgraph-project/graph.py",
            nodes=[
                WorkflowNode(id="start",      label="Start",          type=NodeType.START,  metadata={}),
                WorkflowNode(id="researcher", label="Researcher",     type=NodeType.AGENT,  metadata={"role": "researcher"}),
                WorkflowNode(id="writer",     label="Writer",         type=NodeType.AGENT,  metadata={"role": "writer"}),
                WorkflowNode(id="reviewer",   label="Reviewer",       type=NodeType.AGENT,  metadata={"role": "reviewer"}),
                WorkflowNode(id="end",        label="End",            type=NodeType.END,    metadata={}),
            ],
            edges=[
                WorkflowEdge(id="e1", from_node="start",      to_node="researcher", conditional=False, metadata={}),
                WorkflowEdge(id="e2", from_node="researcher", to_node="writer",     conditional=False, metadata={}),
                WorkflowEdge(id="e3", from_node="writer",     to_node="reviewer",   conditional=False, metadata={}),
                WorkflowEdge(id="e4", from_node="reviewer",   to_node="end",        label="approved",       conditional=True, metadata={}),
                WorkflowEdge(id="e5", from_node="reviewer",   to_node="writer",     label="needs_revision", conditional=True, metadata={}),
            ],
            entry_points=["start"],
            metadata={"_mock": True},
        )

    def export_schemas(self, workspace: Path) -> list[SchemaInfo]:
        """Export state schemas."""
        schemas = self._scan_schemas(workspace)
        if not schemas:
            schemas = [self._fixture_schema()]
        return schemas

    def _scan_schemas(self, workspace: Path) -> list[SchemaInfo]:
        """Scan for Pydantic/dataclass state models."""
        results: list[SchemaInfo] = []
        py_files = iter_workspace_files(workspace, (".py",))

        for py_file in py_files[:20]:
            try:
                text = py_file.read_text(errors="ignore")
                if "BaseModel" in text or "TypedDict" in text:
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if any(
                                (isinstance(b, ast.Name) and b.id in ("BaseModel", "TypedDict"))
                                or (isinstance(b, ast.Attribute) and b.attr in ("BaseModel",))
                                for b in node.bases
                            ):
                                schema = self._class_to_schema(node, text)
                                results.append(SchemaInfo(
                                    id=f"schema-{node.name.lower()}-{hash(str(py_file)):x}",
                                    name=node.name,
                                    runtime="swarmgraph",
                                    schema=schema,
                                    source_file=str(py_file),
                                ))
            except Exception:
                pass

        return results

    def _class_to_schema(self, node: ast.ClassDef, source: str) -> dict[str, Any]:
        """Convert AST class node to rough JSON Schema."""
        props: dict[str, Any] = {}
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fname = item.target.id
                ftype = ast.unparse(item.annotation) if hasattr(ast, "unparse") else "unknown"
                props[fname] = {"type": self._py_type_to_json(ftype), "description": ""}
        return {
            "title": node.name,
            "type": "object",
            "properties": props,
            "additionalProperties": False,
        }

    def _py_type_to_json(self, py_type: str) -> str:
        mapping = {"str": "string", "int": "integer", "float": "number",
                   "bool": "boolean", "list": "array", "dict": "object"}
        base = py_type.split("[")[0].strip()
        return mapping.get(base, "string")

    def _fixture_schema(self) -> SchemaInfo:
        return SchemaInfo(
            id="schema-researchstate-fixture",
            name="ResearchState",
            runtime="swarmgraph",
            schema={
                "title": "ResearchState",
                "type": "object",
                "properties": {
                    "topic":          {"type": "string",  "description": "Research topic"},
                    "research_notes": {"type": "array",   "items": {"type": "string"}, "description": "Collected notes"},
                    "draft":          {"type": "string",  "description": "Current draft"},
                    "feedback":       {"type": "array",   "items": {"type": "string"}, "description": "Review feedback"},
                    "final_output":   {"type": "string",  "description": "Approved output"},
                    "iteration":      {"type": "integer", "description": "Revision count", "default": 0},
                },
                "required": ["topic"],
                "additionalProperties": False,
                "description": "[MOCK] Fixture schema",
            },
            source_file="examples/sample-swarmgraph-project/state.py",
        )

    async def demo_run_workflow(self, workflow_id: str, inputs: dict | None = None) -> RunRecord:
        """Return a clearly marked demo run for tests/manual demos only."""
        import datetime
        run_id = f"run-sg-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc)

        events = [
            RunEvent(type="RUN_STARTED",      timestamp=now.isoformat()+"Z", run_id=run_id, sequence=0, data={"workflow": workflow_id}),
            RunEvent(type="NODE_STARTED",     timestamp=now.isoformat()+"Z", run_id=run_id, sequence=1, data={"node": "researcher"}),
            RunEvent(type="NODE_COMPLETED",   timestamp=now.isoformat()+"Z", run_id=run_id, sequence=2, data={"node": "researcher", "output": "Research complete"}),
            RunEvent(type="NODE_STARTED",     timestamp=now.isoformat()+"Z", run_id=run_id, sequence=3, data={"node": "writer"}),
            RunEvent(type="NODE_COMPLETED",   timestamp=now.isoformat()+"Z", run_id=run_id, sequence=4, data={"node": "writer", "output": "Draft ready"}),
            RunEvent(type="RUN_COMPLETED",    timestamp=now.isoformat()+"Z", run_id=run_id, sequence=5, data={"status": "success"}),
        ]

        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime="swarmgraph",
            status=RunStatus.COMPLETED,
            started_at=now.isoformat()+"Z",
            ended_at=now.isoformat()+"Z",
            events=events,
            metadata={"_mock": True},
        )
