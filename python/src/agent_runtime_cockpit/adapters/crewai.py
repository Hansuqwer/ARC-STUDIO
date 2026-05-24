from __future__ import annotations

import asyncio
import importlib
import importlib.util
import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ..adapters.base import CapabilityReport, DoctorAction
from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import RunEvent, RunRecord, RunStatus, WorkflowInfo
from ._static import dependency_evidence, import_evidence, static_workflow
from .base import RuntimeAdapter

EXPORT_ENV = "ARC_CREWAI_EXPORT"


class CrewAIAdapter(RuntimeAdapter):
    @property
    def adapter_id(self) -> str:
        return "crewai"

    @property
    def adapter_name(self) -> str:
        return "CrewAI"

    def capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(can_inspect=True, can_run=False, can_export_workflow=True)

    def capability_report(self, workspace: Path) -> CapabilityReport:
        detected, _, evidence = self.detect(workspace)
        importable, version = self._crewai_importable()
        if not importable:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="missing_dependency",
                reason="Install crewai in this Python environment.",
                detected_artifacts=evidence,
                required_env=[EXPORT_ENV],
                requires_paid_calls=True,
                doctor_actions=[
                    DoctorAction(
                        id="install-crewai",
                        label="Install CrewAI",
                        description="Install crewai in this Python environment",
                        command="pip install crewai",
                        safe_to_auto_run=False,
                    ),
                ],
            )
        if not os.environ.get(EXPORT_ENV):
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="missing_export_target",
                reason=f"Set {EXPORT_ENV}=module:attribute to a Crew, CrewBase instance, or factory.",
                detected_artifacts=evidence,
                required_env=[EXPORT_ENV],
                version=version,
                requires_paid_calls=True,
                doctor_actions=[
                    DoctorAction(
                        id="set-crewai-export",
                        label="Set ARC_CREWAI_EXPORT",
                        description=f"Set {EXPORT_ENV}=module:attribute to your Crew entry point",
                        command=f"export {EXPORT_ENV}=my_crew:crew",
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
            version=version,
            requires_paid_calls=True,
            doctor_actions=self._doctor_actions(workspace),
        )

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        return [
            DoctorAction(
                id="set-crewai-export",
                label="Set ARC_CREWAI_EXPORT",
                description=f"Set {EXPORT_ENV}=module:attribute to your Crew entry point",
                command=f"export {EXPORT_ENV}=my_crew:crew",
                safe_to_auto_run=False,
            ),
        ]

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        dep_score, evidence = dependency_evidence(workspace, ("crewai",))
        import_score, import_hits = import_evidence(workspace, ("from crewai", "import crewai"))
        evidence.extend(import_hits)
        if importlib.util.find_spec("crewai") is not None:
            evidence.append("crewai package importable")
            dep_score = max(dep_score, 0.4)
        score = min(dep_score + import_score, 1.0)
        return score > 0.3, score, evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        detected, _, evidence = self.detect(workspace)
        if not detected:
            return []
        return static_workflow(self.adapter_id, self.adapter_name, workspace, evidence)

    async def run_workflow(
        self, workflow_id: str, inputs: dict[str, Any] | None = None
    ) -> RunRecord:
        inputs = inputs or {}
        workspace = Path(str(inputs.get("workspace") or ".")).resolve()
        run_id = f"run-ca-{uuid.uuid4().hex[:8]}"
        started = datetime.now(timezone.utc)
        events = [
            self._event(
                run_id, 0, "RUN_STARTED", {"workflow_id": workflow_id, "runtime": self.adapter_id}
            )
        ]

        if not bool(inputs.get("allow_paid_calls")):
            return self._failed(
                workflow_id,
                run_id,
                started,
                events,
                "PAID_CALLS_BLOCKED",
                "CrewAI execution may call LLM providers. Set allow_paid_calls=true to run.",
            )

        report = self.capability_report(workspace)
        if not report.can_run:
            return self._failed(
                workflow_id,
                run_id,
                started,
                events,
                report.availability.upper(),
                report.reason or "CrewAI is not runnable.",
            )

        try:
            crew = self._resolve_crew(workspace, os.environ[EXPORT_ENV], inputs)
            result = await self._kickoff(crew, inputs)
        except asyncio.TimeoutError:
            return self._failed(
                workflow_id,
                run_id,
                started,
                events,
                "CREWAI_TIMEOUT",
                "CrewAI execution timed out before returning a result.",
            )
        except asyncio.CancelledError:
            return self._cancelled(workflow_id, run_id, started, events)
        except Exception as exc:
            return self._failed(
                workflow_id, run_id, started, events, "CREWAI_RUN_FAILED", self._redact(str(exc))
            )

        ended = datetime.now(timezone.utc)
        events.append(self._event(run_id, 1, "RUN_COMPLETED", self._normalize_output(result)))
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=RunStatus.COMPLETED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={
                "output": self._normalize_output(result),
                "_external_target": os.environ.get(EXPORT_ENV),
            },
        )

    def _crewai_importable(self) -> tuple[bool, str | None]:
        if importlib.util.find_spec("crewai") is None:
            return False, None
        try:
            module = importlib.import_module("crewai")
        except Exception:
            return False, None
        return True, getattr(module, "__version__", None)

    def _resolve_crew(self, workspace: Path, target: str, inputs: dict[str, Any]) -> Any:
        if ":" not in target:
            raise ValueError(f"{EXPORT_ENV} must be module:attribute")
        module_name, attr_name = target.split(":", 1)
        with _workspace_import_path(workspace):
            module = importlib.import_module(module_name)
        obj = getattr(module, attr_name)
        if callable(obj):
            try:
                obj = obj(inputs)
            except TypeError:
                obj = obj()
        if hasattr(obj, "kickoff") or hasattr(obj, "akickoff") or hasattr(obj, "kickoff_async"):
            return obj
        if hasattr(obj, "crew") and callable(obj.crew):
            crew = obj.crew()
            if hasattr(crew, "kickoff"):
                return crew
        raise TypeError(f"{target} did not resolve to an object with kickoff() or crew().kickoff()")

    async def _kickoff(self, crew: Any, inputs: dict[str, Any]) -> Any:
        timeout_seconds = self._timeout_seconds(inputs)
        if hasattr(crew, "akickoff"):
            task = crew.akickoff(inputs=inputs)
        elif hasattr(crew, "kickoff_async"):
            task = crew.kickoff_async(inputs=inputs)
        else:
            task = asyncio.to_thread(crew.kickoff, inputs=inputs)
        return (
            await asyncio.wait_for(task, timeout=timeout_seconds) if timeout_seconds else await task
        )

    def _timeout_seconds(self, inputs: dict[str, Any]) -> float | None:
        value = inputs.get("timeout_seconds")
        if value is None:
            return None
        try:
            timeout = float(value)
        except (TypeError, ValueError):
            return None
        return timeout if timeout > 0 else None

    def _normalize_output(self, result: Any) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for attr in ("raw", "json_dict", "token_usage"):
            value = getattr(result, attr, None)
            if value is not None:
                output[attr] = (
                    value if isinstance(value, (str, int, float, bool, dict, list)) else str(value)
                )
        pydantic_value = getattr(result, "pydantic", None)
        if pydantic_value is not None:
            output["pydantic"] = (
                pydantic_value.model_dump()
                if hasattr(pydantic_value, "model_dump")
                else str(pydantic_value)
            )
        tasks = getattr(result, "tasks_output", None)
        if tasks:
            output["tasks_output"] = [
                self._normalize_task_output(index, task) for index, task in enumerate(tasks)
            ]
        if not output:
            output["raw"] = str(result)
        return output

    def _normalize_task_output(self, index: int, task: Any) -> dict[str, Any]:
        raw = getattr(task, "raw", None)
        output_text = raw if isinstance(raw, str) else str(task)
        task_id = (
            getattr(task, "task_id", None)
            or getattr(task, "id", None)
            or getattr(task, "name", None)
            or f"task-{index}"
        )
        agent = getattr(task, "agent", None) or getattr(task, "agent_role", None)
        if agent is not None and not isinstance(agent, str):
            agent = getattr(agent, "role", None) or getattr(agent, "name", None) or str(agent)
        return {
            "task_id": str(task_id),
            "agent": str(agent) if agent is not None else "",
            "output_text": output_text,
            "raw": raw if isinstance(raw, (str, int, float, bool, dict, list)) else str(task),
        }

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
            self._event(run_id, len(events), "RUN_FAILED", {"code": code, "message": message})
        )
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=RunStatus.FAILED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={"error_code": code, "error": message},
        )

    def _cancelled(
        self, workflow_id: str, run_id: str, started: datetime, events: list[RunEvent]
    ) -> RunRecord:
        ended = datetime.now(timezone.utc)
        events.append(
            self._event(
                run_id,
                len(events),
                "RUN_CANCELLED",
                {
                    "code": "CREWAI_CANCELLED",
                    "message": "CrewAI execution was cancelled before returning a result.",
                },
            )
        )
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=RunStatus.CANCELLED,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={
                "error_code": "CREWAI_CANCELLED",
                "error": "CrewAI execution was cancelled before returning a result.",
            },
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
