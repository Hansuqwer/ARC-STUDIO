"""JobSupervisor — owns run lifecycle, cancellation, and orphan recovery (ADR-002).

Wires the EventBroker for live event streaming during execution.
Enforces workspace trust before starting runs (ADR-006 P2).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from ..audit.hitl import HitlPrompt, HitlResponse
from ..audit.key_manager import AuditKeyManager
from ..protocol.evidence_refs import EvidenceKind, EvidenceRef
from ..protocol.failure_autopsy import FailureAutopsy, RetryOption
from ..protocol.run_contract import ContractStatus, RunContract
from ..protocol.run_receipt import RunReceipt
from ..protocol.schemas import RunRecord, RunStatus
from ..security.redaction import Redactor
from ..security.trust import ensure_trusted
from ..storage.jsonl import JsonlTraceStore
from .event_broker import EventBroker
from .events import create_event

log = logging.getLogger(__name__)

ALLOWED_EVIDENCE_KINDS = {EvidenceKind.FILE, EvidenceKind.TOOL_OUTPUT}


class RunRequest(BaseModel):
    """Input for starting a run via the supervisor."""

    workflow_id: str
    runtime: Optional[str] = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    prompt: Optional[str] = None
    profile_id: str = "stub"
    timeout_seconds: int = 300
    metadata: dict[str, Any] = Field(default_factory=dict)
    workspace_root: Optional[str] = None
    """Workspace root path for trust enforcement.

    If set, ``start_run()`` enforces workspace trust before execution.
    Untrusted workspaces raise ``WorkspaceUntrusted``.
    """
    workspace_trust_db: Optional[str] = None
    """Optional external trust DB path, primarily for tests/embedded daemons."""


@dataclass
class ActiveRun:
    """A currently-executing run managed by the supervisor."""

    run_id: str
    task: Optional[asyncio.Task] = None
    cancelled: bool = False


class HitlTimeoutError(TimeoutError):
    """Raised when a HITL prompt receives no response before timeout."""


class HitlNotFoundError(KeyError):
    """Raised when responding to an unknown or expired HITL prompt."""


class JobSupervisor:
    """Manages run lifecycle, cancellation, and orphan recovery.

    Delegates actual execution to an ``executor_fn`` callback.
    Events during execution are emitted through the EventBroker.
    """

    def __init__(
        self,
        store: JsonlTraceStore,
        broker: Optional[EventBroker] = None,
    ) -> None:
        self.store = store
        self.broker = broker or EventBroker(store)
        self._active_runs: dict[str, ActiveRun] = {}
        self._sequence_counters: dict[str, int] = {}
        self._pending_hitl: dict[str, asyncio.Future[HitlResponse]] = {}
        self._redactor = Redactor()

    async def start_run(
        self,
        request: RunRequest,
        executor_fn: Callable,
    ) -> RunRecord:
        """Start a run asynchronously.

        ``executor_fn`` receives ``(run_id, request, emit_event)`` where
        ``emit_event`` is a callable to publish events during execution.

        Enforces workspace trust (ADR-006 P2): if ``request.workspace_root``
        is set, the workspace must be trusted. Raises ``WorkspaceUntrusted``
        if the workspace is not in the external trust database.
        """
        if request.workspace_root:
            trust_db = Path(request.workspace_trust_db) if request.workspace_trust_db else None
            if trust_db:
                ensure_trusted(Path(request.workspace_root), trust_db=trust_db)
            else:
                ensure_trusted(Path(request.workspace_root))

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        run = RunRecord(
            id=run_id,
            workflow_id=request.workflow_id,
            runtime=request.runtime or "unknown",
            status=RunStatus.PENDING,
            started_at=now,
            metadata=request.metadata,
        )
        self.store.save(run)
        self._sequence_counters[run_id] = 0
        contract = self._build_contract(run, request)
        self.store.save_contract(contract)
        run.metadata["contract_id"] = contract.contract_id
        self.store.save(run)
        active = ActiveRun(run_id=run_id)
        self._active_runs[run_id] = active
        self.broker.mark_active(run_id)
        task = asyncio.create_task(
            self._execute_run(run_id, request, executor_fn),
            name=f"run-{run_id}",
        )
        active.task = task
        return run

    async def _execute_run(
        self,
        run_id: str,
        request: RunRequest,
        executor_fn: Callable,
    ) -> None:
        """Internal: execute a run with lifecycle event emission."""
        start_ms = self._now_ms()
        try:
            contract = self.store.load_contract(run_id)
            if contract:
                self._emit_event(
                    run_id,
                    "CONTRACT_PROPOSED",
                    {
                        "contract": self._redacted(contract.model_dump(mode="json")),
                    },
                )
            self._emit_event(
                run_id,
                "RUN_STARTED",
                {
                    "workflow_id": request.workflow_id,
                    "runtime": request.runtime or "unknown",
                },
            )
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.RUNNING
                self.store.save(run)

            await asyncio.wait_for(
                executor_fn(run_id, request, self._emit_event),
                timeout=request.timeout_seconds,
            )

            duration = self._now_ms() - start_ms
            self._emit_event(run_id, "RUN_COMPLETED", {"duration_ms": duration})
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.COMPLETED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)
                self._finalize_run_artifacts(run_id, request, RunStatus.COMPLETED, duration)

        except asyncio.CancelledError:
            duration = self._now_ms() - start_ms
            self._emit_event(run_id, "RUN_CANCELLED", {"cancel_reason": "user_requested"})
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.CANCELLED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)
                self._finalize_run_artifacts(run_id, request, RunStatus.CANCELLED, duration)

        except TimeoutError as e:
            duration = self._now_ms() - start_ms
            self._emit_event(
                run_id,
                "RUN_FAILED",
                {
                    "error": f"run timed out after {request.timeout_seconds}s",
                    "error_detail": "TimeoutError",
                    "timeout_seconds": request.timeout_seconds,
                },
            )
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.FAILED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)
                autopsy = self._generate_autopsy(run, e)
                self.store.save_autopsy(autopsy)
                self._emit_event(
                    run_id,
                    "FAILURE_AUTOPSY_GENERATED",
                    {
                        "autopsy": self._redacted(autopsy.model_dump(mode="json", by_alias=True)),
                    },
                )
                self._finalize_run_artifacts(run_id, request, RunStatus.FAILED, duration)

        except Exception as e:
            duration = self._now_ms() - start_ms
            self._emit_event(
                run_id,
                "RUN_FAILED",
                {
                    "error": self._redactor.redact_string(str(e)),
                    "error_detail": type(e).__name__,
                },
            )
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.FAILED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)
                autopsy = self._generate_autopsy(run, e)
                self.store.save_autopsy(autopsy)
                self._emit_event(
                    run_id,
                    "FAILURE_AUTOPSY_GENERATED",
                    {
                        "autopsy": self._redacted(autopsy.model_dump(mode="json", by_alias=True)),
                    },
                )
                self._finalize_run_artifacts(run_id, request, RunStatus.FAILED, duration)

        finally:
            self.broker.end_run(run_id)
            self._active_runs.pop(run_id, None)
            self._sequence_counters.pop(run_id, None)

    def _emit_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Create a schema-validated event and publish it through the broker."""
        seq = self._sequence_counters.get(run_id, 0)
        data = self._redacted(self._attach_verified_evidence(run_id, seq, event_type, data))
        event = create_event(run_id, seq, event_type, data)
        event.data = self._redacted(event.data)
        self._sequence_counters[run_id] = seq + 1
        run = self.store.load(run_id)
        if run:
            run.events.append(event)
            self.store.save(run)
        self.broker.publish(run_id, event.model_dump())

    def _build_contract(self, run: RunRecord, request: RunRequest) -> RunContract:
        objective = request.prompt or str(request.inputs.get("objective") or request.workflow_id)
        mode = str(request.metadata.get("mode", "auto"))
        if mode not in ("plan", "build", "auto"):
            mode = "auto"
        return RunContract(
            contract_id="ctr_" + secrets.token_urlsafe(16),
            run_id=run.id,
            session_id=str(request.metadata.get("session_id", run.id)),
            objective=self._redactor.redact_string(objective),
            runtime=request.runtime or "unknown",
            mode=mode,
            allowed_tools=list(request.metadata.get("allowed_tools", [])),
            cost_ceiling_usd=request.metadata.get("cost_ceiling_usd", "unknown"),
            approval_policy=str(request.metadata.get("approval_policy", "auto")),
            rollback_plan=str(request.metadata.get("rollback_plan", "none")),
            evidence_expected=["tool_output"],
            metadata={
                "workflow_id": request.workflow_id,
                "profile_id": request.profile_id,
                "workspace_path": str(Path(request.workspace_root).resolve())
                if request.workspace_root
                else "unknown",
                "input_hash": self._input_hash(request.inputs),
                "timeout_seconds": request.timeout_seconds,
            },
        )

    def _finalize_run_artifacts(
        self, run_id: str, request: RunRequest, status: RunStatus, duration_ms: int
    ) -> None:
        run = self.store.load(run_id)
        contract = self.store.load_contract(run_id)
        evidence_refs = self._run_evidence_refs(run) if run else []
        receipt = RunReceipt(
            receipt_id="rcpt_" + secrets.token_urlsafe(16),
            run_id=run_id,
            session_id=contract.session_id if contract else run_id,
            contract_id=contract.contract_id if contract else None,
            status=status.value,
            summary=self._receipt_summary(run),
            cost_usd=self._run_cost_usd(run, request),
            duration_ms=duration_ms,
            evidence_refs=evidence_refs,
            audit_chain_ref=run.audit_path if run else None,
        )
        key, _ = AuditKeyManager().get_key()
        if key:
            receipt.sign(key.decode("utf-8", errors="ignore"))
        self.store.save_receipt(receipt)
        if contract and status == RunStatus.COMPLETED and contract.is_satisfied_by(receipt):
            contract.status = ContractStatus.FULFILLED
            contract.fulfilled_at = datetime.now(timezone.utc).isoformat()
            self.store.save_contract(contract)
            self._emit_event(
                run_id,
                "CONTRACT_FULFILLED",
                {
                    "contract_id": contract.contract_id,
                    "run_id": run_id,
                },
            )
        elif contract and status == RunStatus.COMPLETED:
            contract.status = ContractStatus.VIOLATED
            self.store.save_contract(contract)
            self._emit_event(
                run_id,
                "CONTRACT_VIOLATED",
                {
                    "contract_id": contract.contract_id,
                    "run_id": run_id,
                    "reason": "contract terms not satisfied",
                },
            )
        if run:
            run = self.store.load(run_id)
        if run:
            run.metadata["receipt_id"] = receipt.receipt_id
            self.store.save(run)
        self._emit_event(
            run_id,
            "RECEIPT_GENERATED",
            {
                "receipt": self._redacted(receipt.model_dump(mode="json", by_alias=True)),
            },
        )

    def _generate_autopsy(self, run: RunRecord, error: Exception) -> FailureAutopsy:
        safe_error = self._redactor.redact_string(str(error))
        error_detail = type(error).__name__
        failed_node = self._last_event_value(run, "node_id")
        evidence_refs = self._run_evidence_refs(run)[-5:]
        return FailureAutopsy(
            run_id=run.id,
            probable_cause=safe_error or "unknown",
            confidence="medium" if safe_error else "unknown",
            failed_node=failed_node,
            retry_options=[RetryOption(label="Retry with same input", risk="low")],
            knows=[f"Run {run.id} failed with {error_detail}"],
            guesses=self._autopsy_guesses(error_detail),
            evidence_refs=evidence_refs,
            error_category=self._error_category(error_detail),
            stack_summary=safe_error[:500],
        )

    def _attach_verified_evidence(
        self, run_id: str, sequence: int, event_type: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        if "evidence_refs" in data:
            data = dict(data)
            data["evidence_refs"] = self._valid_evidence(data.get("evidence_refs"))
            return data
        if event_type in {"TOOL_CALL_RESULT", "TOOL_CALL_ERROR"}:
            data = dict(data)
            data["evidence_refs"] = [
                self._tool_evidence(run_id, sequence).model_dump(by_alias=True)
            ]
        return data

    def _run_evidence_refs(self, run: RunRecord) -> list[EvidenceRef]:
        refs: list[EvidenceRef] = []
        seen: set[str] = set()
        for event in run.events:
            for ref in self._valid_evidence(event.data.get("evidence_refs", [])):
                if ref.evidence_id in seen:
                    continue
                seen.add(ref.evidence_id)
                refs.append(ref)
        return refs

    def _valid_evidence(self, refs: Any) -> list[EvidenceRef]:
        valid: list[EvidenceRef] = []
        if not isinstance(refs, list):
            return valid
        for ref in refs:
            try:
                ev = EvidenceRef.model_validate(
                    ref.model_dump(by_alias=True) if isinstance(ref, EvidenceRef) else ref
                )
            except Exception:
                continue
            if ev.kind not in ALLOWED_EVIDENCE_KINDS:
                continue
            ev.target = self._redactor.redact_string(ev.target)
            valid.append(ev)
        return valid

    def _run_cost_usd(self, run: RunRecord | None, request: RunRequest) -> float | str:
        sources = [
            request.metadata.get("cost_usd"),
            request.metadata.get("estimated_cost_usd"),
            run.metadata.get("cost_usd") if run else None,
            run.metadata.get("estimated_cost_usd") if run else None,
        ]
        for value in sources:
            if isinstance(value, (int, float)) and value >= 0:
                return float(value)
        return "unknown"

    def _tool_evidence(self, run_id: str, sequence: int) -> EvidenceRef:
        return EvidenceRef(
            evidence_id="ev_" + secrets.token_urlsafe(16),
            kind="tool_output",
            target=f"{run_id}/events/{sequence}",
        )

    def _receipt_summary(self, run: RunRecord | None) -> str:
        if run is None or not run.events:
            return ""
        for event in reversed(run.events):
            if event.type in {"RUN_COMPLETED", "RUN_FAILED", "RUN_CANCELLED"}:
                return self._redactor.redact_string(json.dumps(event.data, default=str)[:500])
        return ""

    def _input_hash(self, inputs: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(inputs, sort_keys=True, default=str).encode()).hexdigest()

    def _redacted(self, data: Any) -> Any:
        return self._redactor.redact_dict(data)

    def _last_event_value(self, run: RunRecord, key: str) -> Optional[str]:
        for event in reversed(run.events):
            value = event.data.get(key)
            if value:
                return str(value)
        return None

    def _autopsy_guesses(self, error_detail: str) -> list[str]:
        if error_detail == "TimeoutError":
            return ["A runtime step may have exceeded its timeout"]
        if "Hitl" in error_detail:
            return ["A required human approval may not have arrived in time"]
        return ["Runtime adapter or tool execution failed"]

    def _error_category(self, error_detail: str) -> str:
        if error_detail == "TimeoutError":
            return "tool_timeout"
        if "Provider" in error_detail:
            return "provider_error"
        return "internal"

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel an active run. Returns True if cancellation was requested."""
        active = self._active_runs.get(run_id)
        if active is None or active.task is None:
            return False
        active.cancelled = True
        active.task.cancel()
        try:
            await active.task
        except asyncio.CancelledError:
            pass
        return True

    async def recover_orphans(self) -> int:
        """Mark RUNNING runs from a previous supervisor session as FAILED."""
        recovered = 0
        for run_id in self.store.list_runs():
            run = self.store.load(run_id)
            if run and run.status == RunStatus.RUNNING:
                run.status = RunStatus.FAILED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                run.metadata["failure_reason"] = "supervisor_orphan"
                self.store.save(run)
                recovered += 1
        return recovered

    def get_active_run(self, run_id: str) -> Optional[ActiveRun]:
        """Return the ActiveRun for a run_id, or None if not active."""
        return self._active_runs.get(run_id)

    async def request_hitl(self, prompt: HitlPrompt) -> HitlResponse:
        """Emit a HITL prompt and wait for a single-user response.

        The prompt is persisted as a run event and streamed through the broker.
        ``respond_hitl()`` completes the pending future. On timeout the prompt
        is closed, a timeout event is emitted, and ``HitlTimeoutError`` is raised.
        """
        if prompt.hitl_id in self._pending_hitl:
            raise ValueError(f"HITL prompt already pending: {prompt.hitl_id}")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[HitlResponse] = loop.create_future()
        self._pending_hitl[prompt.hitl_id] = future
        self._emit_event(
            prompt.run_id,
            "HITL_PROMPT",
            {
                "hitl_id": prompt.hitl_id,
                "step_id": prompt.step_id,
                "prompt_text": prompt.prompt_text,
                "context": prompt.context,
                "options": prompt.options,
                "timeout_seconds": prompt.timeout_seconds,
                "created_at": prompt.created_at,
            },
        )
        try:
            return await asyncio.wait_for(future, timeout=prompt.timeout_seconds)
        except asyncio.TimeoutError as exc:
            self._emit_event(
                prompt.run_id,
                "HITL_TIMEOUT",
                {
                    "hitl_id": prompt.hitl_id,
                    "timeout_seconds": prompt.timeout_seconds,
                },
            )
            raise HitlTimeoutError(f"HITL prompt timed out: {prompt.hitl_id}") from exc
        finally:
            self._pending_hitl.pop(prompt.hitl_id, None)

    def respond_hitl(self, response: HitlResponse) -> None:
        """Resolve a pending HITL prompt and emit the response event."""
        future = self._pending_hitl.get(response.hitl_id)
        if future is None or future.done():
            raise HitlNotFoundError(response.hitl_id)
        future.set_result(response)
        self._emit_event(
            response.run_id,
            "HITL_RESPONSE",
            {
                "hitl_id": response.hitl_id,
                "decision": response.decision.value,
                "operator_id": response.operator_id,
                "modified_data": response.modified_data,
                "notes": response.notes,
                "responded_at": response.responded_at,
            },
        )

    def pending_hitl(self, run_id: str | None = None) -> list[dict[str, str]]:
        """Return pending HITL ids. Kept minimal until persistence/CLI lands."""
        items: list[dict[str, str]] = []
        for hitl_id, future in self._pending_hitl.items():
            if future.done():
                continue
            items.append({"hitl_id": hitl_id})
        return items

    @staticmethod
    def _now_ms() -> int:
        import time

        return int(time.time() * 1000)
