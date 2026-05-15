"""
OpenAI Agents SDK Runtime Adapter

Detects and runs OpenAI Agents SDK-based agent projects.
Source: https://github.com/openai/openai-agents-python

This adapter uses the OpenAI Agents SDK's built-in RunHooks to capture
agent lifecycle events (agent start/end, tool calls, handoffs) and maps
them to AG-UI events via the canonical mapping layer.

Security: Dual gating enforced via centralized require_dual_gate("OPENAI").
Set ARC_OPENAI_RUN_BACKEND=stub (free) or local/gateway (requires ARC_OPENAI_ALLOW_COSTS=true).

Export target: The actual Agent/workflow is loaded via the
ARC_OPENAI_AGENTS_EXPORT environment variable in ``module:attr`` format
(e.g. ``my_project.agent:agent``). The module must reside inside the
workspace unless explicitly trusted.
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent_runtime_cockpit.gating import require_dual_gate, GatingError
from typing import Any

from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import (
    WorkflowInfo, RunRecord, RunEvent, RunStatus,
)
from ._static import dependency_evidence, import_evidence, static_workflow
from .base import RuntimeAdapter, CapabilityReport, DoctorAction

log = logging.getLogger(__name__)

# Environment variable name for the export target.
_EXPORT_ENV = "ARC_OPENAI_AGENTS_EXPORT"


# ---------------------------------------------------------------------------
# Export-target loader
# ---------------------------------------------------------------------------

class ExportTargetError(Exception):
    """Raised when the export target cannot be resolved."""


def _load_exported_agent(
    inputs: dict[str, Any] | None,
) -> tuple[Any, str]:
    """Load the Agent object from the ``ARC_OPENAI_AGENTS_EXPORT`` env var.

    Returns
    -------
    (agent_instance, source_descr)
        The imported Agent instance and a human-readable source string
        (e.g. ``"my_project.agent:my_agent"``).

    Raises
    ------
    ExportTargetError
        If the variable is unset, malformed, points outside the workspace
        (unless explicitly trusted), the module cannot be imported, or the
        exported attribute is not an ``Agent`` instance.
    """
    raw = os.environ.get(_EXPORT_ENV)
    if not raw:
        raise ExportTargetError(
            f"{_EXPORT_ENV} is not set. "
            "Specify an export target, e.g. "
            f"export {_EXPORT_ENV}=my_project.agent:my_agent"
        )

    # Parse module:attr
    parts = raw.rsplit(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ExportTargetError(
            f"Invalid {_EXPORT_ENV} format: {raw!r}. "
            "Expected ``module:attr``, e.g. ``my_project.agent:my_agent``."
        )
    module_name, attr_name = parts[0], parts[1]

    # Resolve module file path for workspace-boundary check.
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        raise ExportTargetError(
            f"Module {module_name!r} (from {_EXPORT_ENV}={raw!r}) "
            "not found. Make sure it is importable from the workspace."
        )
    module_path = Path(spec.origin).resolve()

    # Security: refuse targets outside the workspace unless explicitly trusted.
    workspace_str = (inputs or {}).get("workspace")
    trusted_env = os.environ.get("ARC_TRUSTED_PATHS", "")
    trusted_paths = {Path(p).resolve() for p in trusted_env.split(":") if p}

    if workspace_str:
        workspace_path = Path(workspace_str).resolve()
    else:
        workspace_path = Path.cwd().resolve()

    # Allow if module is inside workspace OR on an explicit trusted path.
    is_inside_workspace = _is_subpath(module_path, workspace_path)
    is_on_trusted_path = any(
        _is_subpath(module_path, tp) for tp in trusted_paths
    )

    if not is_inside_workspace and not is_on_trusted_path:
        raise ExportTargetError(
            f"Export target {raw!r} resolves to {module_path}, "
            "which is outside the workspace. "
            "Set ARC_TRUSTED_PATHS to allow additional directories."
        )

    # Import the module and extract the attribute.
    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:
        raise ExportTargetError(
            f"Failed to import module {module_name!r} "
            f"(from {_EXPORT_ENV}={raw!r}): {exc}"
        ) from exc

    agent = getattr(mod, attr_name, None)
    if agent is None:
        raise ExportTargetError(
            f"Module {module_name!r} has no attribute {attr_name!r} "
            f"(from {_EXPORT_ENV}={raw!r})."
        )

    # We import Agent lazily so the adapter module can be imported
    # without the SDK being installed.
    try:
        from agents import Agent as OpenAIAgent
    except ImportError as exc:
        raise ExportTargetError(
            "OpenAI Agents SDK is not installed."
        ) from exc

    if not isinstance(agent, OpenAIAgent):
        raise ExportTargetError(
            f"Export target {raw!r} resolved to {type(agent).__name__}, "
            "not an Agent instance."
        )

    return agent, raw


def _is_subpath(child: Path, parent: Path) -> bool:
    """Return True when *child* is a descendant of *parent*."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class OpenAIAgentsAdapter(RuntimeAdapter):
    @property
    def adapter_id(self) -> str:
        return "openai-agents"

    @property
    def adapter_name(self) -> str:
        return "OpenAI Agents"

    def capabilities(self) -> RuntimeCapabilities:
        # can_run=True only if SDK is importable
        can_run = importlib.util.find_spec("agents") is not None
        return RuntimeCapabilities(
            can_inspect=True,
            can_run=can_run,
            can_export_workflow=True,
            can_trace=True,
            can_stream_events=False,  # TODO: implement streaming
        )

    def capability_report(self, workspace: Path) -> CapabilityReport:
        detected, _, evidence = self.detect(workspace)
        caps = self.capabilities()
        
        if not caps.can_run:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="missing_dependency",
                reason="OpenAI Agents SDK not installed. Install with: pip install openai-agents",
                detected_artifacts=evidence,
                required_env=["OPENAI_API_KEY", _EXPORT_ENV],
                requires_paid_calls=True,
                doctor_actions=[
                    DoctorAction(
                        id="install-openai-agents",
                        label="Install OpenAI Agents SDK",
                        description="Install the openai-agents package",
                        command="pip install openai-agents",
                        safe_to_auto_run=False,
                    ),
                ],
            )
        
        # Check dual gating
        try:
            backend, allow_costs = require_dual_gate("OPENAI")
        except GatingError as exc:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="paid_calls_blocked",
                reason=str(exc),
                detected_artifacts=evidence,
                required_env=["ARC_OPENAI_RUN_BACKEND", "ARC_OPENAI_ALLOW_COSTS", "OPENAI_API_KEY", _EXPORT_ENV],
                requires_paid_calls=True,
                doctor_actions=[
                    DoctorAction(
                        id="config-openai-gating",
                        label="Configure OpenAI Gating",
                        description="Set ARC_OPENAI_RUN_BACKEND and ARC_OPENAI_ALLOW_COSTS",
                        command="export ARC_OPENAI_RUN_BACKEND=stub && export ARC_OPENAI_ALLOW_COSTS=true",
                        safe_to_auto_run=False,
                    ),
                ],
            )
        
        # Check export target configuration
        export_target = os.environ.get(_EXPORT_ENV)
        if not export_target:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="missing_export_target",
                reason=(
                    f"Export target not configured. "
                    f"Set {_EXPORT_ENV}=module:attr to specify the Agent to run."
                ),
                detected_artifacts=evidence,
                required_env=["ARC_OPENAI_RUN_BACKEND", "ARC_OPENAI_ALLOW_COSTS", "OPENAI_API_KEY", _EXPORT_ENV],
                requires_paid_calls=True,
                doctor_actions=[
                    DoctorAction(
                        id="set-openai-export-target",
                        label="Set OpenAI Agents Export Target",
                        description=(
                            f"Set {_EXPORT_ENV} to the module:attr "
                            "pointing to your Agent (e.g. my_agent:agent)"
                        ),
                        command=f"export {_EXPORT_ENV}=my_project.agent:my_agent",
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
            required_env=["ARC_OPENAI_RUN_BACKEND", "ARC_OPENAI_ALLOW_COSTS", "OPENAI_API_KEY", _EXPORT_ENV],
            requires_paid_calls=True,
        )

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        return [
            DoctorAction(
                id="install-openai-agents",
                label="Install OpenAI Agents SDK",
                description="Install the openai-agents package",
                command="pip install openai-agents",
                safe_to_auto_run=False,
            ),
            DoctorAction(
                id="config-openai-gating",
                label="Configure OpenAI Gating",
                description="Set ARC_OPENAI_RUN_BACKEND=stub and optionally ARC_OPENAI_ALLOW_COSTS=true",
                command="export ARC_OPENAI_RUN_BACKEND=stub",
                safe_to_auto_run=False,
            ),
        ]

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        dep_score, evidence = dependency_evidence(
            workspace, 
            ("openai-agents", "openai_agents", "agents")
        )
        import_score, import_hits = import_evidence(
            workspace, 
            ("from agents", "import agents", "from agents import")
        )
        evidence.extend(import_hits)
        
        if importlib.util.find_spec("agents") is not None:
            evidence.append("agents package importable")
            dep_score = max(dep_score, 0.4)
        
        score = min(dep_score + import_score, 1.0)
        return score > 0.3, score, evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        detected, _, evidence = self.detect(workspace)
        if not detected:
            return []
        return static_workflow(self.adapter_id, self.adapter_name, workspace, evidence)

    async def run_workflow(self, workflow_id: str, inputs: dict[str, Any] | None = None) -> RunRecord:
        """
        Execute an OpenAI Agents SDK workflow with dual gating.
        
        The Agent to run is loaded from the ``ARC_OPENAI_AGENTS_EXPORT``
        environment variable (``module:attr`` format).
        
        Dual gating enforced via require_dual_gate("OPENAI"):
        1. ARC_OPENAI_RUN_BACKEND must be set (stub/local/gateway)
        2. ARC_OPENAI_ALLOW_COSTS must be 'true' for non-stub backends
        
        Without both gates, this method raises GatingError.
        """
        inputs = inputs or {}
        
        # Dual gating check
        backend, allow_costs = require_dual_gate("OPENAI")
        
        run_id = f"run-openai-{uuid.uuid4().hex[:8]}"
        started = datetime.now(timezone.utc)
        events: list[RunEvent] = []
        
        # Check SDK availability
        if importlib.util.find_spec("agents") is None:
            events.append(self._event(run_id, 0, "RUN_FAILED", {
                "error": "OpenAI Agents SDK not installed. Install with: pip install openai-agents",
                "workflow_id": workflow_id,
            }))
            return RunRecord(
                id=run_id,
                workflow_id=workflow_id,
                runtime="openai-agents",
                status=RunStatus.FAILED,
                started_at=started.isoformat(),
                ended_at=datetime.now(timezone.utc).isoformat(),
                events=events,
                metadata={"error": "SDK not installed"},
            )
        
        # Import SDK (only after gating checks pass)
        try:
            from agents import Agent, Runner, RunHooks
        except ImportError as exc:
            events.append(self._event(run_id, 0, "RUN_FAILED", {
                "error": f"Failed to import OpenAI Agents SDK: {exc}",
                "workflow_id": workflow_id,
            }))
            return RunRecord(
                id=run_id,
                workflow_id=workflow_id,
                runtime="openai-agents",
                status=RunStatus.FAILED,
                started_at=started.isoformat(),
                ended_at=datetime.now(timezone.utc).isoformat(),
                events=events,
                metadata={"error": str(exc)},
            )
        
        # Load the actual Agent from the export target.
        try:
            agent, export_source = _load_exported_agent(inputs)
        except ExportTargetError as exc:
            events.append(self._event(run_id, 0, "RUN_FAILED", {
                "error": str(exc),
                "workflow_id": workflow_id,
            }))
            return RunRecord(
                id=run_id,
                workflow_id=workflow_id,
                runtime="openai-agents",
                status=RunStatus.FAILED,
                started_at=started.isoformat(),
                ended_at=datetime.now(timezone.utc).isoformat(),
                events=events,
                metadata={"export_error": str(exc)},
            )
        
        # Event capture hooks
        class ARCRunHooks(RunHooks):
            def __init__(self, run_id: str, events: list[RunEvent]):
                self.run_id = run_id
                self.events = events
                self.seq = 0
            
            def _add_event(self, event_type: str, data: dict[str, Any]):
                self.events.append(RunEvent(
                    type=event_type,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    run_id=self.run_id,
                    sequence=self.seq,
                    data=data,
                ))
                self.seq += 1
            
            async def on_agent_start(self, context, agent):
                self._add_event("AGENT_START", {
                    "agent_name": agent.name,
                    "instructions": agent.instructions[:200] if agent.instructions else None,
                })
            
            async def on_agent_end(self, context, agent, output):
                self._add_event("AGENT_END", {
                    "agent_name": agent.name,
                    "output": str(output)[:500],
                    "usage": str(context.usage) if hasattr(context, "usage") else None,
                })
            
            async def on_tool_start(self, context, agent, tool):
                self._add_event("TOOL_START", {
                    "agent_name": agent.name,
                    "tool_name": tool.name,
                })
            
            async def on_tool_end(self, context, agent, tool, result):
                self._add_event("TOOL_END", {
                    "agent_name": agent.name,
                    "tool_name": tool.name,
                    "result": str(result)[:500],
                })
            
            async def on_handoff(self, context, from_agent, to_agent):
                self._add_event("HANDOFF", {
                    "from_agent": from_agent.name,
                    "to_agent": to_agent.name,
                })
        
        hooks = ARCRunHooks(run_id, events)
        events.append(self._event(run_id, 0, "RUN_STARTED", {
            "workflow_id": workflow_id,
            "backend": backend,
            "cost_allowed": allow_costs,
            "export_target": export_source,
        }))
        
        prompt = str(inputs.get("prompt", ""))
        
        try:
            result = await Runner.run(
                agent,
                prompt,
                hooks=hooks,
            )
            
            events.append(self._event(run_id, len(events), "RUN_COMPLETED", {
                "final_output": str(result.final_output)[:1000],
            }))
            
            return RunRecord(
                id=run_id,
                workflow_id=workflow_id,
                runtime="openai-agents",
                status=RunStatus.COMPLETED,
                started_at=started.isoformat(),
                ended_at=datetime.now(timezone.utc).isoformat(),
                events=events,
                metadata={
                    "backend": backend,
                    "cost_allowed": allow_costs,
                    "prompt": prompt,
                    "export_target": export_source,
                },
            )
        
        except Exception as exc:
            log.exception("OpenAI Agents run failed")
            events.append(self._event(run_id, len(events), "RUN_FAILED", {
                "error": str(exc),
                "error_type": type(exc).__name__,
            }))
            
            return RunRecord(
                id=run_id,
                workflow_id=workflow_id,
                runtime="openai-agents",
                status=RunStatus.FAILED,
                started_at=started.isoformat(),
                ended_at=datetime.now(timezone.utc).isoformat(),
                events=events,
                metadata={
                    "backend": backend,
                    "cost_allowed": allow_costs,
                    "prompt": prompt,
                    "export_target": export_source,
                    "error": str(exc),
                },
            )
    
    def _event(self, run_id: str, seq: int, event_type: str, data: dict[str, Any]) -> RunEvent:
        """Helper to create a RunEvent."""
        return RunEvent(
            type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=run_id,
            sequence=seq,
            data=data,
        )
