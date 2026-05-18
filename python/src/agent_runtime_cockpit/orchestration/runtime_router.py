from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Literal, Sequence
import uuid

from ..adapters.base import CapabilityReport, RuntimeAdapter
from ..adapters.registry import default_registry
from ..adoption.protocol import AdoptionMode, AdoptionSpec
from ..adoption.registry import AdoptionRegistry
from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import RunEvent, RunRecord, RunStatus

RuntimeId = Literal["swarmgraph", "langgraph", "crewai", "lmarena"]
KNOWN_RUNTIMES: tuple[str, ...] = (
    "swarmgraph", "langgraph", "crewai", "openai-agents", "ag2", "llamaindex", "lmarena",
    "langgraph+swarmgraph", "ag2+swarmgraph", "crewai+swarmgraph",
    "openai_agents+swarmgraph", "llamaindex+swarmgraph",
)
AUTO_PRIORITY: tuple[RuntimeId, ...] = ("swarmgraph", "langgraph", "crewai", "lmarena")


class RuntimeRouterError(Exception):
    code = "RUNTIME_ROUTER_ERROR"


class UnknownRuntime(RuntimeRouterError):
    code = "UNKNOWN_RUNTIME"


class RuntimeNotRunnable(RuntimeRouterError):
    code = "RUNTIME_NOT_RUNNABLE"


class ComboNotRunnable(RuntimeRouterError):
    code = "COMBO_NOT_RUNNABLE"


@dataclass(frozen=True)
class RoutedRuntime:
    adapter: RuntimeAdapter
    report: CapabilityReport
    chosen_by: Literal["explicit", "auto", "combo"]


class ComboRuntimeAdapter(RuntimeAdapter):
    def __init__(self, adapters: Sequence[RuntimeAdapter]) -> None:
        self.adapters = list(adapters)

    @property
    def adapter_id(self) -> str:
        return "combo"

    @property
    def adapter_name(self) -> str:
        return "Combo"

    def capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(can_run=True, can_trace=True)

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        return True, 1.0, [f"combo member: {adapter.adapter_id}" for adapter in self.adapters]

    async def run_workflow(self, workflow_id: str, inputs: dict[str, Any] | None = None) -> RunRecord:
        inputs = inputs or {}
        run_id = f"run-combo-{uuid.uuid4().hex[:8]}"
        started = datetime.now(timezone.utc)
        events = [self._event(run_id, 0, "RUN_STARTED", {"workflow_id": workflow_id, "runtime": self.adapter_id})]
        child_runs: list[dict[str, Any]] = []
        for index, adapter in enumerate(self.adapters):
            child = await adapter.run_workflow(workflow_id, {**inputs, "combo_index": index, "combo_run_id": run_id})
            child_runs.append(child.model_dump())
            events.append(self._event(run_id, len(events), "NODE_UPDATE", {
                "runtime": adapter.adapter_id,
                "status": child.status.value if hasattr(child.status, "value") else str(child.status),
                "run_id": child.id,
            }))
            if child.status != RunStatus.COMPLETED:
                ended = datetime.now(timezone.utc)
                events.append(self._event(run_id, len(events), "RUN_FAILED", {"runtime": adapter.adapter_id, "run_id": child.id, "status": child.status.value}))
                return RunRecord(
                    id=run_id,
                    workflow_id=workflow_id,
                    runtime=self.adapter_id,
                    status=RunStatus.FAILED,
                    started_at=started.isoformat(),
                    ended_at=ended.isoformat(),
                    events=events,
                    metadata={"child_runs": child_runs, "runtimes": [adapter.adapter_id for adapter in self.adapters]},
                )
        ended = datetime.now(timezone.utc)
        events.append(self._event(run_id, len(events), "RUN_COMPLETED", {"child_run_count": len(child_runs)}))
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=RunStatus.COMPLETED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={"child_runs": child_runs, "runtimes": [adapter.adapter_id for adapter in self.adapters]},
        )

    def _event(self, run_id: str, sequence: int, event_type: str, data: dict[str, Any]) -> RunEvent:
        return RunEvent(type=event_type, timestamp=datetime.now(timezone.utc).isoformat(), run_id=run_id, sequence=sequence, data=data)


class CrewAISwarmGraphFakeAdapter(RuntimeAdapter):
    @property
    def adapter_id(self) -> str:
        return "crewai+swarmgraph"

    @property
    def adapter_name(self) -> str:
        return "CrewAI + SwarmGraph (fake/offline)"

    def capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(can_run=True, can_trace=True)

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        return True, 1.0, ["fake/offline adoption adapter"]

    def capability_report(self, workspace: Path) -> CapabilityReport:
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=True,
            can_run=True,
            availability="runnable",
            reason="Fake/offline CrewAI + SwarmGraph path; no provider calls",
            detected_artifacts=["fake/offline adoption adapter"],
            requires_paid_calls=False,
            test_level="fake_offline",
            fake_offline_supported=True,
            provider_backed=False,
        )

    async def run_workflow(self, workflow_id: str, inputs: dict[str, Any] | None = None) -> RunRecord:
        inputs = inputs or {}
        mode = inputs.get("runtime_mode", "fake/offline")
        if mode != "fake/offline":
            raise RuntimeNotRunnable("CrewAI + SwarmGraph real mode is gated behind opt-in smoke tests")
        runner = AdoptionRegistry.get(AdoptionMode.CREWAI)
        if runner is None:
            raise RuntimeNotRunnable("CrewAI adoption runner is not registered")
        run_id = f"run-crewai-sg-{uuid.uuid4().hex[:8]}"
        started = datetime.now(timezone.utc)
        events: list[RunEvent] = []

        def emit_event(event_run_id: str, event_type: str, data: dict[str, Any]) -> None:
            events.append(RunEvent(
                type=event_type,
                timestamp=datetime.now(timezone.utc).isoformat(),
                run_id=event_run_id,
                sequence=len(events),
                data=data,
            ))

        emit_event(run_id, "RUN_STARTED", {"workflow_id": workflow_id, "runtime": self.adapter_id, "runtime_mode": mode})
        spec = AdoptionSpec(
            mode=AdoptionMode.CREWAI,
            runtime_config={"crew": _FakeCrew(workflow_id), "inputs": inputs},
            swarmgraph_config={"mode": mode, "real_provider_call": False},
        )
        consensus = await runner.run(spec, run_id, emit_event)
        ended = datetime.now(timezone.utc)
        emit_event(run_id, "RUN_COMPLETED", {"confidence": consensus.confidence, "consensus_reached": consensus.consensus_reached})
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=RunStatus.COMPLETED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={
                "runtime_mode": mode,
                "adoption": True,
                "real_provider_call": False,
                "audit_path": None,
                "audit_absent_reason": "fake/offline adoption run does not create SwarmGraph HMAC audit records",
                "consensus": consensus.model_dump(),
            },
        )


class LangGraphSwarmGraphFakeAdapter(RuntimeAdapter):
    @property
    def adapter_id(self) -> str:
        return "langgraph+swarmgraph"

    @property
    def adapter_name(self) -> str:
        return "LangGraph + SwarmGraph (fake/offline)"

    def capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(can_run=True, can_trace=True)

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        return True, 1.0, ["fake/offline deterministic adoption adapter"]

    def capability_report(self, workspace: Path) -> CapabilityReport:
        local_real_enabled = os.environ.get("ARC_LANGGRAPH_SWARMGRAPH_REAL") == "1"
        reason = (
            "fake/offline deterministic path plus gated local-real LangGraph + vendored SwarmGraph path; "
            "no provider-backed claim; no paid calls"
            if local_real_enabled
            else "fake/offline deterministic LangGraph + SwarmGraph path; no provider calls; "
            "gated local-real path requires ARC_LANGGRAPH_SWARMGRAPH_REAL=1"
        )
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=True,
            can_run=True,
            availability="runnable",
            reason=reason,
            detected_artifacts=[
                "fake/offline deterministic adoption adapter",
                *(["local-real gate ARC_LANGGRAPH_SWARMGRAPH_REAL=1"] if local_real_enabled else []),
            ],
            required_env=[] if local_real_enabled else ["ARC_LANGGRAPH_SWARMGRAPH_REAL"],
            requires_paid_calls=False,
            test_level="gated_local_real" if local_real_enabled else "fake_offline",
            fake_offline_supported=True,
            local_real_gated=not local_real_enabled,
            local_real_available=local_real_enabled,
            provider_backed=False,
        )

    async def run_workflow(self, workflow_id: str, inputs: dict[str, Any] | None = None) -> RunRecord:
        inputs = inputs or {}
        mode = inputs.get("runtime_mode", "fake/offline")
        if mode not in {"fake/offline", "local-real"}:
            raise RuntimeNotRunnable(
                "LangGraph + SwarmGraph supports runtime_mode fake/offline or local-real only; "
                "provider-backed real mode is not claimed"
            )
        local_real = mode == "local-real"
        if local_real and os.environ.get("ARC_LANGGRAPH_SWARMGRAPH_REAL") != "1":
            raise RuntimeNotRunnable("LangGraph + SwarmGraph local-real mode requires ARC_LANGGRAPH_SWARMGRAPH_REAL=1")
        runner = AdoptionRegistry.get(AdoptionMode.LANGGRAPH)
        if runner is None:
            raise RuntimeNotRunnable("LangGraph adoption runner is not registered")
        run_id = f"run-langgraph-sg-{uuid.uuid4().hex[:8]}"
        started = datetime.now(timezone.utc)
        events: list[RunEvent] = []

        def emit_event(event_run_id: str, event_type: str, data: dict[str, Any]) -> None:
            events.append(RunEvent(
                type=event_type,
                timestamp=datetime.now(timezone.utc).isoformat(),
                run_id=event_run_id,
                sequence=len(events),
                data=data,
            ))

        emit_event(run_id, "RUN_STARTED", {"workflow_id": workflow_id, "runtime": self.adapter_id, "runtime_mode": mode})
        graph = _LocalNoProviderLangGraph(workflow_id) if local_real else _FakeLangGraph(workflow_id)
        spec = AdoptionSpec(
            mode=AdoptionMode.LANGGRAPH,
            runtime_config={
                "graph": graph,
                "input": inputs,
                "objective": inputs.get("prompt") or workflow_id,
                "offline_deterministic": not local_real,
                "runtime_mode": mode,
            },
            swarmgraph_config={"mode": mode, "real_provider_call": False},
        )
        consensus = await runner.run(spec, run_id, emit_event)
        ended = datetime.now(timezone.utc)
        emit_event(run_id, "RUN_COMPLETED", {"confidence": consensus.confidence, "consensus_reached": consensus.consensus_reached})
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=RunStatus.COMPLETED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={
                "runtime_mode": mode,
                "adoption": True,
                "real_provider_call": False,
                "real_runtime_gated": not local_real,
                "real_path_absent_reason": (
                    "local-real uses local LangGraph plus vendored SwarmGraph only; no provider-backed claim"
                    if local_real
                    else "fake/offline deterministic; local-real requires ARC_LANGGRAPH_SWARMGRAPH_REAL=1"
                ),
                "audit_path": None,
                "audit_absent_reason": "fake/offline adoption run does not create SwarmGraph HMAC audit records",
                "consensus": consensus.model_dump(),
            },
        )


class _FakeLangGraph:
    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id

    def invoke(self, input_data: dict[str, Any]) -> dict[str, str]:
        prompt = input_data.get("prompt") or input_data.get("swarmgraph_task") or self.workflow_id
        return {"result": f"fake/offline LangGraph result for {prompt}"}


class _LocalNoProviderLangGraph:
    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id

    def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        prompt = input_data.get("prompt") or input_data.get("swarmgraph_task") or self.workflow_id
        return {
            "result": f"local-real LangGraph no-provider result for {prompt}",
            "runtime_mode": "local-real",
            "real_provider_call": False,
        }


class _FakeCrew:
    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id

    def kickoff(self, inputs: dict[str, Any]) -> object:
        prompt = inputs.get("prompt") or self.workflow_id
        return type("FakeCrewResult", (), {"raw": f"fake/offline CrewAI result for {prompt}"})()

def list_runtimes(workspace: Path) -> list[CapabilityReport]:
    reports = [adapter.capability_report(workspace) for adapter in default_registry().all()]
    for capability in AdoptionRegistry.list_capabilities(workspace):
        if capability.mode == AdoptionMode.LANGGRAPH:
            reports.append(LangGraphSwarmGraphFakeAdapter().capability_report(workspace))
            continue
        if capability.mode == AdoptionMode.CREWAI:
            reports.append(CrewAISwarmGraphFakeAdapter().capability_report(workspace))
            continue
        reason = capability.reason
        if capability.status.value == "runnable":
            reason = f"{capability.reason}; adoption runner ready but runtime router is not wired"
        reports.append(CapabilityReport(
            runtime_id=capability.mode.value,
            detected=False,
            can_run=False,
            availability="detected_not_runnable",
            reason=reason,
            doctor_actions=[_doctor_action_from_dict(action) for action in capability.doctor_actions],
        ))
    return reports


def resolve(workspace: Path, runtime: str | Sequence[str] | None = "auto", allow_paid_calls: bool = False) -> RoutedRuntime:
    if runtime is None or runtime == "auto":
        return _resolve_auto(workspace, allow_paid_calls=allow_paid_calls)
    if isinstance(runtime, str):
        base_runtime, adoption_mode = AdoptionRegistry.parse_runtime_id(runtime)
        if adoption_mode is not None:
            if adoption_mode == AdoptionMode.LANGGRAPH:
                adapter = LangGraphSwarmGraphFakeAdapter()
                report = adapter.capability_report(workspace)
                return RoutedRuntime(adapter=adapter, report=report, chosen_by="explicit")
            if adoption_mode == AdoptionMode.CREWAI:
                adapter = CrewAISwarmGraphFakeAdapter()
                report = adapter.capability_report(workspace)
                return RoutedRuntime(adapter=adapter, report=report, chosen_by="explicit")
            capability = next(
                cap for cap in AdoptionRegistry.list_capabilities(workspace)
                if cap.mode == adoption_mode
            )
            raise RuntimeNotRunnable(
                f"Runtime '{runtime}' is not runnable: {capability.status.value} ({capability.reason or 'no detail'})"
            )
        if runtime not in KNOWN_RUNTIMES:
            raise UnknownRuntime(f"Unknown runtime '{runtime}'. Known: {', '.join(KNOWN_RUNTIMES)}")
        adapter = default_registry().get(runtime)
        if adapter is None:
            raise UnknownRuntime(f"No adapter registered for '{runtime}'")
        report = adapter.capability_report(workspace)
        if not report.can_run:
            raise RuntimeNotRunnable(
                f"Runtime '{runtime}' is not runnable: {report.availability} ({report.reason or 'no detail'})"
            )
        return RoutedRuntime(adapter=adapter, report=report, chosen_by="explicit")
    return _resolve_combo(workspace, runtime, allow_paid_calls=allow_paid_calls)


def _resolve_combo(workspace: Path, runtimes: Sequence[str], allow_paid_calls: bool) -> RoutedRuntime:
    if len(runtimes) < 2:
        raise ComboNotRunnable("Combo runtime selection requires at least two runtime ids.")
    registry = default_registry()
    adapters: list[RuntimeAdapter] = []
    reports: list[CapabilityReport] = []
    for runtime_id in runtimes:
        if runtime_id not in KNOWN_RUNTIMES:
            raise UnknownRuntime(f"Unknown runtime '{runtime_id}'. Known: {', '.join(KNOWN_RUNTIMES)}")
        adapter = registry.get(runtime_id)
        if adapter is None:
            raise UnknownRuntime(f"No adapter registered for '{runtime_id}'")
        report = adapter.capability_report(workspace)
        if not report.can_run:
            raise ComboNotRunnable(f"Combo runtime '{runtime_id}' is not runnable: {report.availability} ({report.reason or 'no detail'})")
        if report.requires_paid_calls and not allow_paid_calls:
            raise ComboNotRunnable(f"Combo runtime '{runtime_id}' requires paid-call approval.")
        adapters.append(adapter)
        reports.append(report)
    combo_report = CapabilityReport(
        runtime_id="combo",
        detected=True,
        can_run=True,
        availability="runnable",
        detected_artifacts=[artifact for report in reports for artifact in report.detected_artifacts],
        required_env=sorted({env for report in reports for env in report.required_env}),
        requires_paid_calls=any(report.requires_paid_calls for report in reports),
    )
    return RoutedRuntime(adapter=ComboRuntimeAdapter(adapters), report=combo_report, chosen_by="combo")


def _resolve_auto(workspace: Path, allow_paid_calls: bool) -> RoutedRuntime:
    registry = default_registry()
    skipped_paid: list[str] = []
    for runtime_id in AUTO_PRIORITY:
        adapter = registry.get(runtime_id)
        if adapter is None:
            continue
        report = adapter.capability_report(workspace)
        if report.can_run:
            if report.requires_paid_calls and not allow_paid_calls:
                skipped_paid.append(runtime_id)
                continue
            return RoutedRuntime(adapter=adapter, report=report, chosen_by="auto")
    if skipped_paid:
        raise RuntimeNotRunnable(
            "No runnable runtime detected under auto-selection. Skipped paid-call runtimes "
            f"(pass --allow-paid-calls to include): {', '.join(skipped_paid)}."
        )
    raise RuntimeNotRunnable("No runnable runtime detected. Set --runtime and verify dependencies/export targets.")


def _doctor_action_from_dict(action: dict[str, str]):
    from ..adapters.base import DoctorAction

    return DoctorAction(
        id=action.get("id", "adoption-action"),
        label=action.get("label", "Adoption action"),
        description=action.get("description", ""),
        command=action.get("command", ""),
        safe_to_auto_run=False,
    )
