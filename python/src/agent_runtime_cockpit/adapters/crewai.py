from __future__ import annotations

import importlib.util
import importlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..adapters.base import CapabilityReport
from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import WorkflowInfo, RunRecord, RunEvent, RunStatus
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
        )

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

    async def run_workflow(self, workflow_id: str, inputs: dict[str, Any] | None = None) -> RunRecord:
        inputs = inputs or {}
        workspace = Path(str(inputs.get("workspace") or ".")).resolve()
        run_id = f"run-ca-{uuid.uuid4().hex[:8]}"
        started = datetime.now(timezone.utc)
        events = [self._event(run_id, 0, "RUN_STARTED", {"workflow_id": workflow_id, "runtime": self.adapter_id})]

        if not bool(inputs.get("allow_paid_calls")):
            return self._failed(workflow_id, run_id, started, events, "PAID_CALLS_BLOCKED", "CrewAI execution may call LLM providers. Set allow_paid_calls=true to run.")

        report = self.capability_report(workspace)
        if not report.can_run:
            return self._failed(workflow_id, run_id, started, events, report.availability.upper(), report.reason or "CrewAI is not runnable.")

        try:
            crew = self._resolve_crew(os.environ[EXPORT_ENV], inputs)
            result = await self._kickoff(crew, inputs)
        except Exception as exc:
            return self._failed(workflow_id, run_id, started, events, "CREWAI_RUN_FAILED", self._redact(str(exc)))

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
            metadata={"output": self._normalize_output(result), "_external_target": os.environ.get(EXPORT_ENV)},
        )

    def _crewai_importable(self) -> tuple[bool, str | None]:
        if importlib.util.find_spec("crewai") is None:
            return False, None
        try:
            module = importlib.import_module("crewai")
        except Exception:
            return False, None
        return True, getattr(module, "__version__", None)

    def _resolve_crew(self, target: str, inputs: dict[str, Any]) -> Any:
        if ":" not in target:
            raise ValueError(f"{EXPORT_ENV} must be module:attribute")
        module_name, attr_name = target.split(":", 1)
        module = importlib.import_module(module_name)
        obj = getattr(module, attr_name)
        if callable(obj):
            try:
                obj = obj(inputs)
            except TypeError:
                obj = obj()
        if hasattr(obj, "kickoff"):
            return obj
        if hasattr(obj, "crew") and callable(obj.crew):
            crew = obj.crew()
            if hasattr(crew, "kickoff"):
                return crew
        raise TypeError(f"{target} did not resolve to an object with kickoff() or crew().kickoff()")

    async def _kickoff(self, crew: Any, inputs: dict[str, Any]) -> Any:
        if hasattr(crew, "akickoff"):
            return await crew.akickoff(inputs=inputs)
        if hasattr(crew, "kickoff_async"):
            return await crew.kickoff_async(inputs=inputs)
        import asyncio
        return await asyncio.to_thread(crew.kickoff, inputs=inputs)

    def _normalize_output(self, result: Any) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for attr in ("raw", "json_dict", "token_usage"):
            value = getattr(result, attr, None)
            if value is not None:
                output[attr] = value if isinstance(value, (str, int, float, bool, dict, list)) else str(value)
        pydantic_value = getattr(result, "pydantic", None)
        if pydantic_value is not None:
            output["pydantic"] = pydantic_value.model_dump() if hasattr(pydantic_value, "model_dump") else str(pydantic_value)
        tasks = getattr(result, "tasks_output", None)
        if tasks:
            output["tasks_output"] = [str(task) for task in tasks]
        if not output:
            output["raw"] = str(result)
        return output

    def _failed(self, workflow_id: str, run_id: str, started: datetime, events: list[RunEvent], code: str, message: str) -> RunRecord:
        ended = datetime.now(timezone.utc)
        events.append(self._event(run_id, len(events), "RUN_FAILED", {"code": code, "message": message}))
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

    def _event(self, run_id: str, sequence: int, event_type: str, data: dict[str, Any]) -> RunEvent:
        return RunEvent(type=event_type, timestamp=datetime.now(timezone.utc).isoformat(), run_id=run_id, sequence=sequence, data=data)

    def _redact(self, text: str, cap: int = 4000) -> str:
        lowered = text.lower()
        if any(hint in lowered for hint in ("api_key", "authorization", "bearer", "secret", "token=")):
            return "[redacted: message contained possible secret material]"
        return text[:cap]
