from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence
import uuid

from ..adapters.base import CapabilityReport, RuntimeAdapter
from ..adapters.registry import default_registry
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


def list_runtimes(workspace: Path) -> list[CapabilityReport]:
    reports = [adapter.capability_report(workspace) for adapter in default_registry().all()]
    for capability in AdoptionRegistry.list_capabilities(workspace):
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
