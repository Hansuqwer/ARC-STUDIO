"""
OpenAI Agents SDK Runtime Adapter

Detects and runs OpenAI Agents SDK-based agent projects.
Source: https://github.com/openai/openai-agents-python

This adapter uses the OpenAI Agents SDK's built-in RunHooks to capture
agent lifecycle events (agent start/end, tool calls, handoffs) and maps
them to AG-UI events via the canonical mapping layer.

Security: Dual gating enforced via centralized require_dual_gate("OPENAI").
Set ARC_OPENAI_RUN_BACKEND=stub (free) or local/gateway (requires ARC_OPENAI_ALLOW_COSTS=true).
"""
from __future__ import annotations

import importlib.util
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent_runtime_cockpit.gating import require_dual_gate, GatingError
from typing import Any

from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import (
    WorkflowInfo, RunRecord, RunEvent, RunStatus
)
from ._static import dependency_evidence, import_evidence, static_workflow
from .base import RuntimeAdapter, CapabilityReport, DoctorAction

log = logging.getLogger(__name__)


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
                required_env=["OPENAI_API_KEY"],
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
                required_env=["ARC_OPENAI_RUN_BACKEND", "ARC_OPENAI_ALLOW_COSTS", "OPENAI_API_KEY"],
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
        
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=detected,
            can_run=True,
            availability="runnable",
            detected_artifacts=evidence,
            required_env=["ARC_OPENAI_RUN_BACKEND", "ARC_OPENAI_ALLOW_COSTS", "OPENAI_API_KEY"],
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
        }))
        
        # Create a simple agent for testing
        # In production, this would load the actual workflow from workspace
        prompt = str(inputs.get("prompt", "Hello, test the agent system."))
        
        try:
            agent = Agent(
                name="TestAgent",
                instructions="You are a helpful assistant. Be concise.",
            )
            
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
