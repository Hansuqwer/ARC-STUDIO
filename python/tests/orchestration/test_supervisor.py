"""Tests: JobSupervisor — run lifecycle, cancel, and orphan recovery (PR 20).

Uses fake executor functions to simulate successful, failing,
cancelling, and orphaned runs.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agent_runtime_cockpit.audit.hitl import HitlDecision, HitlPrompt, HitlResponse
from agent_runtime_cockpit.orchestration.event_broker import EventBroker
from agent_runtime_cockpit.orchestration.supervisor import (
    HitlNotFoundError,
    JobSupervisor,
    RunRequest,
)
from agent_runtime_cockpit.protocol.events import create_event
from agent_runtime_cockpit.protocol.evidence_refs import EvidenceKind, EvidenceRef
from agent_runtime_cockpit.protocol.schemas import RunStatus
from agent_runtime_cockpit.security.trust import WorkspaceUntrusted, trust_workspace
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore


@pytest.fixture
def supervisor(tmp_path: Path) -> JobSupervisor:
    store = JsonlTraceStore(base_dir=tmp_path / "traces")
    broker = EventBroker(store=store)
    return JobSupervisor(store=store, broker=broker)


def _make_request(workflow_id: str = "wf-test", runtime: str = "swarmgraph") -> RunRequest:
    return RunRequest(workflow_id=workflow_id, runtime=runtime)


class TestStartRun:
    """Starting a run creates a PENDING record and launches execution."""

    @pytest.mark.asyncio
    async def test_start_run_returns_pending_record(self, supervisor: JobSupervisor):
        run = await supervisor.start_run(
            _make_request(),
            lambda run_id, req, emit: asyncio.sleep(0.01),
        )
        assert run.id.startswith("run-")
        assert run.status == RunStatus.PENDING
        assert run.workflow_id == "wf-test"

    @pytest.mark.asyncio
    async def test_run_completes_successfully(self, supervisor: JobSupervisor):
        async def fake_executor(run_id, req, emit_event):
            emit_event(run_id, "STEP_STARTED", {"step_id": "s1", "step_name": "fake"})
            await asyncio.sleep(0.01)

        run = await supervisor.start_run(_make_request(), fake_executor)
        run_id = run.id

        # Wait for completion
        await asyncio.sleep(0.2)

        loaded = supervisor.store.load(run_id)
        assert loaded is not None
        assert loaded.status == RunStatus.COMPLETED
        assert loaded.ended_at is not None
        assert [event.type for event in loaded.events] == [
            "CONTRACT_PROPOSED",
            "RUN_STARTED",
            "STEP_STARTED",
            "RUN_COMPLETED",
            "CONTRACT_FULFILLED",
            "RECEIPT_GENERATED",
        ]
        assert supervisor.store.load_contract(run_id) is not None
        assert supervisor.store.load_receipt(run_id) is not None

    @pytest.mark.asyncio
    async def test_receipt_cost_enforces_contract_ceiling(self, supervisor: JobSupervisor):
        request = RunRequest(
            workflow_id="wf-test",
            runtime="swarmgraph",
            metadata={"cost_ceiling_usd": 1.0, "cost_usd": 2.5},
        )

        run = await supervisor.start_run(request, lambda run_id, req, emit: asyncio.sleep(0.01))
        await asyncio.sleep(0.2)

        receipt = supervisor.store.load_receipt(run.id)
        contract = supervisor.store.load_contract(run.id)
        loaded = supervisor.store.load(run.id)
        assert receipt is not None
        assert receipt.cost_usd == 2.5
        assert contract is not None
        assert contract.status.value == "violated"
        assert loaded is not None
        assert "CONTRACT_VIOLATED" in [event.type for event in loaded.events]

    @pytest.mark.asyncio
    async def test_receipt_evidence_refs_allowlisted_and_deduped(self, supervisor: JobSupervisor):
        evidence = {
            "schema_version": 1,
            "evidence_id": "ev_01JDEADBEEF1234567890",
            "kind": "file",
            "target": "a.py",
            "redacted": False,
            "metadata": {},
        }
        ledger = {**evidence, "evidence_id": "ev_01JDEADBEEF1234567891", "kind": "ledger"}

        async def fake_executor(run_id, req, emit_event):
            emit_event(run_id, "MESSAGE", {"text": "one", "evidence_refs": [evidence, ledger]})
            emit_event(run_id, "MESSAGE", {"text": "two", "evidence_refs": [evidence]})

        run = await supervisor.start_run(_make_request(), fake_executor)
        await asyncio.sleep(0.2)

        receipt = supervisor.store.load_receipt(run.id)
        assert receipt is not None
        assert len(receipt.evidence_refs) == 1
        assert receipt.evidence_refs[0].kind.value == "file"

    def test_valid_evidence_does_not_mutate_caller(self, supervisor: JobSupervisor):
        ref = EvidenceRef(
            evidence_id="ev_01JDEADBEEF1234567890",
            kind=EvidenceKind.FILE,
            target="/abs/secret",
        )

        valid = supervisor._valid_evidence([ref])

        assert valid[0].target == "/abs/secret"
        assert ref.target == "/abs/secret"

    @pytest.mark.asyncio
    async def test_untrusted_workspace_is_blocked(
        self,
        supervisor: JobSupervisor,
        tmp_path: Path,
    ):
        trust_db = tmp_path / "trust-db.json"
        request = RunRequest(
            workflow_id="wf-test",
            runtime="swarmgraph",
            workspace_root=str(tmp_path / "workspace"),
            workspace_trust_db=str(trust_db),
        )

        with pytest.raises(WorkspaceUntrusted):
            await supervisor.start_run(request, lambda run_id, req, emit: asyncio.sleep(0.01))

        assert supervisor.store.list_runs() == []

    @pytest.mark.asyncio
    async def test_trusted_workspace_can_start_run(
        self,
        supervisor: JobSupervisor,
        tmp_path: Path,
    ):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        trust_db = tmp_path / "trust-db.json"
        trust_workspace(workspace, trust_db=trust_db)
        request = RunRequest(
            workflow_id="wf-test",
            runtime="swarmgraph",
            workspace_root=str(workspace),
            workspace_trust_db=str(trust_db),
        )

        run = await supervisor.start_run(request, lambda run_id, req, emit: asyncio.sleep(0.01))

        assert run.status == RunStatus.PENDING


class TestCancelRun:
    """Cancelling a run marks it as CANCELLED."""

    @pytest.mark.asyncio
    async def test_cancel_active_run(self, supervisor: JobSupervisor):
        async def slow_executor(run_id, req, emit_event):
            emit_event(run_id, "STEP_STARTED", {"step_id": "s1", "step_name": "slow"})
            await asyncio.sleep(10)  # will be cancelled

        run = await supervisor.start_run(_make_request(), slow_executor)
        run_id = run.id
        await asyncio.sleep(0.05)  # let it start

        cancelled = await supervisor.cancel_run(run_id)
        assert cancelled is True, (
            f"cancel_run returned False. Active runs: {list(supervisor._active_runs.keys())}"
        )

        loaded = supervisor.store.load(run_id)
        assert loaded is not None
        assert loaded.status == RunStatus.CANCELLED
        receipt = supervisor.store.load_receipt(run_id)
        assert receipt is not None
        assert receipt.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_run(self, supervisor: JobSupervisor):
        cancelled = await supervisor.cancel_run("nonexistent")
        assert cancelled is False

    @pytest.mark.asyncio
    async def test_cancel_completed_run_is_noop(self, supervisor: JobSupervisor):
        async def fast_executor(run_id, req, emit_event):
            await asyncio.sleep(0.01)

        run = await supervisor.start_run(_make_request(), fast_executor)
        run_id = run.id
        await asyncio.sleep(0.1)  # let it finish

        cancelled = await supervisor.cancel_run(run_id)
        assert cancelled is False  # already completed

        loaded = supervisor.store.load(run_id)
        assert loaded.status == RunStatus.COMPLETED


class TestOrphanRecovery:
    """Recover orphans marks stale RUNNING runs as FAILED."""

    @pytest.mark.asyncio
    async def test_recover_orphans(self, supervisor: JobSupervisor, tmp_path: Path):
        # Manually create a RUNNING run in the store (simulating orphan)
        from datetime import datetime, timezone

        from agent_runtime_cockpit.protocol.schemas import RunRecord

        orphan = RunRecord(
            id="orphan-001",
            workflow_id="wf",
            runtime="swarmgraph",
            status=RunStatus.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        supervisor.store.save(orphan)

        recovered = await supervisor.recover_orphans()
        assert recovered == 1

        loaded = supervisor.store.load("orphan-001")
        assert loaded is not None
        assert loaded.status == RunStatus.FAILED
        assert loaded.metadata.get("failure_reason") == "supervisor_orphan"

    @pytest.mark.asyncio
    async def test_recover_orphans_skips_completed(self, supervisor: JobSupervisor, tmp_path: Path):
        from datetime import datetime, timezone

        from agent_runtime_cockpit.protocol.schemas import RunRecord

        completed = RunRecord(
            id="completed-001",
            workflow_id="wf",
            runtime="swarmgraph",
            status=RunStatus.COMPLETED,
            started_at=datetime.now(timezone.utc).isoformat(),
            ended_at=datetime.now(timezone.utc).isoformat(),
        )
        supervisor.store.save(completed)

        recovered = await supervisor.recover_orphans()
        assert recovered == 0

    @pytest.mark.asyncio
    async def test_recover_orphans_empty_store(self, supervisor: JobSupervisor):
        recovered = await supervisor.recover_orphans()
        assert recovered == 0


class TestBrokerIntegration:
    """Supervisor publishes events through the EventBroker."""

    @pytest.mark.asyncio
    async def test_broker_receives_run_events(self, supervisor: JobSupervisor):
        broker = supervisor.broker

        async def fake_executor(run_id, req, emit_event):
            emit_event(run_id, "STEP_STARTED", {"step_id": "s1", "step_name": "fake"})
            await asyncio.sleep(0.01)

        run = await supervisor.start_run(_make_request(), fake_executor)
        run_id = run.id

        # Subscribe to broker events BEFORE execution completes
        queue = broker.subscribe(run_id)
        await asyncio.sleep(0.2)

        # Collect published events
        collected = []
        while not queue.empty():
            ev = queue.get_nowait()
            if ev is not None:
                collected.append(ev)

        # Should have RUN_STARTED, STEP_STARTED, RUN_COMPLETED
        types = {e["type"] for e in collected}
        assert "RUN_STARTED" in types, f"Got types: {types}"
        assert "STEP_STARTED" in types, f"Got types: {types}"
        assert "RUN_COMPLETED" in types, f"Got types: {types}"

    @pytest.mark.asyncio
    async def test_sg_events_are_created_stored_and_published(self, supervisor: JobSupervisor):
        queue_by_run: dict[str, asyncio.Queue] = {}

        async def fake_executor(run_id, req, emit_event):
            queue_by_run[run_id] = supervisor.broker.subscribe(run_id)
            for sequence, event_type, data in [
                (
                    2,
                    "SWARMGRAPH_TOPOLOGY",
                    {
                        "nodes": [{"id": "queen", "label": "Queen"}],
                        "edges": [{"source": "queen", "target": "worker-1"}],
                    },
                ),
                (
                    3,
                    "SWARMGRAPH_CONSENSUS",
                    {
                        "votes": [{"voter": "worker-1", "vote": "approve"}],
                        "decision": "approve",
                        "strategy": "majority",
                        "voters": ["worker-1"],
                        "confidence": 0.9,
                        "consensus_reached": True,
                        "task_id": "task-1",
                    },
                ),
                (
                    4,
                    "SWARMGRAPH_COST",
                    {
                        "totalCost": 0.012,
                        "totalTokens": 1200,
                        "currency": "USD",
                        "items": [{"provider": "stub", "tokens": 1200, "cost": 0.012}],
                        "provider": "stub",
                        "runtime": "swarmgraph",
                    },
                ),
            ]:
                create_event(run_id, sequence, event_type, data)
                emit_event(run_id, event_type, data)

        run = await supervisor.start_run(_make_request(), fake_executor)
        await asyncio.sleep(0.2)

        loaded = supervisor.store.load(run.id)
        assert loaded is not None
        sg_events = [event for event in loaded.events if event.type.startswith("SWARMGRAPH_")]
        assert [event.type for event in sg_events] == [
            "SWARMGRAPH_TOPOLOGY",
            "SWARMGRAPH_CONSENSUS",
            "SWARMGRAPH_COST",
        ]
        assert sg_events[0].data["nodes"][0]["id"] == "queen"
        assert sg_events[1].data["votes"][0]["vote"] == "approve"
        assert sg_events[2].data["totalCost"] == 0.012

        queue = queue_by_run[run.id]
        published = []
        while not queue.empty():
            event = queue.get_nowait()
            if event is not None and event["type"].startswith("SWARMGRAPH_"):
                published.append(event)
        assert [event["type"] for event in published] == [
            "SWARMGRAPH_TOPOLOGY",
            "SWARMGRAPH_CONSENSUS",
            "SWARMGRAPH_COST",
        ]


class TestHitlFlow:
    """Supervisor can pause execution for single-user HITL responses."""

    @pytest.mark.asyncio
    async def test_request_hitl_emits_prompt_and_returns_response(self, supervisor: JobSupervisor):
        captured: list[HitlResponse] = []

        async def executor(run_id, req, emit_event):
            prompt = HitlPrompt(
                hitl_id="hitl-1",
                run_id=run_id,
                step_id="step-1",
                prompt_text="Approve?",
                timeout_seconds=1,
            )
            task = asyncio.create_task(supervisor.request_hitl(prompt))
            await asyncio.sleep(0)
            supervisor.respond_hitl(
                HitlResponse(
                    hitl_id="hitl-1",
                    run_id=run_id,
                    decision=HitlDecision.APPROVE,
                    operator_id="tester",
                )
            )
            captured.append(await task)

        run = await supervisor.start_run(_make_request(), executor)
        await asyncio.sleep(0.2)

        assert captured[0].decision == HitlDecision.APPROVE
        loaded = supervisor.store.load(run.id)
        assert loaded is not None
        assert [event.type for event in loaded.events] == [
            "CONTRACT_PROPOSED",
            "RUN_STARTED",
            "HITL_PROMPT",
            "HITL_RESPONSE",
            "RUN_COMPLETED",
            "CONTRACT_FULFILLED",
            "RECEIPT_GENERATED",
        ]

    @pytest.mark.asyncio
    async def test_request_hitl_timeout_fails_run(self, supervisor: JobSupervisor):
        async def executor(run_id, req, emit_event):
            await supervisor.request_hitl(
                HitlPrompt(
                    hitl_id="hitl-timeout",
                    run_id=run_id,
                    step_id="step-1",
                    prompt_text="Approve?",
                    timeout_seconds=0,
                )
            )

        run = await supervisor.start_run(_make_request(), executor)
        await asyncio.sleep(0.2)

        loaded = supervisor.store.load(run.id)
        assert loaded is not None
        assert loaded.status == RunStatus.FAILED
        assert "HITL_TIMEOUT" in [event.type for event in loaded.events]
        assert supervisor.store.load_autopsy(run.id) is not None


class TestCockpitArtifacts:
    @pytest.mark.asyncio
    async def test_failed_run_gets_receipt_autopsy_and_redacted_output(
        self,
        supervisor: JobSupervisor,
    ):
        async def executor(run_id, req, emit_event):
            emit_event(
                run_id,
                "TOOL_CALL_ERROR",
                {
                    "tool_call_id": "tool-1",
                    "error": "api_key=supersecret12345 failed",
                },
            )
            raise RuntimeError("password=supersecret12345 failed")

        run = await supervisor.start_run(_make_request(), executor)
        await asyncio.sleep(0.2)

        receipt = supervisor.store.load_receipt(run.id)
        autopsy = supervisor.store.load_autopsy(run.id)
        loaded = supervisor.store.load(run.id)

        assert receipt is not None
        assert receipt.status == "failed"
        assert receipt.evidence_refs
        assert "supersecret" not in receipt.summary
        assert autopsy is not None
        assert autopsy.knows
        assert autopsy.guesses
        assert "supersecret" not in autopsy.stack_summary
        assert loaded is not None
        assert "FAILURE_AUTOPSY_GENERATED" in [event.type for event in loaded.events]

    @pytest.mark.asyncio
    async def test_invalid_evidence_refs_are_stripped(self, supervisor: JobSupervisor):
        async def executor(run_id, req, emit_event):
            emit_event(
                run_id,
                "TOOL_CALL_RESULT",
                {
                    "tool_call_id": "tool-1",
                    "result": "ok",
                    "evidence_refs": [
                        {"evidence_id": "bad", "kind": "file", "target": "x"},
                        {
                            "evidence_id": "ev_01JDEADBEEF1234567890",
                            "kind": "ledger",
                            "target": "x",
                        },
                        {
                            "evidence_id": "ev_01JDEADBEEF1234567891",
                            "kind": "file",
                            "target": "a.py",
                        },
                    ],
                },
            )

        run = await supervisor.start_run(_make_request(), executor)
        await asyncio.sleep(0.2)

        receipt = supervisor.store.load_receipt(run.id)
        assert receipt is not None
        assert [ref.target for ref in receipt.evidence_refs] == ["a.py"]

    def test_respond_hitl_unknown_prompt_raises(self, supervisor: JobSupervisor):
        with pytest.raises(HitlNotFoundError):
            supervisor.respond_hitl(
                HitlResponse(
                    hitl_id="missing",
                    run_id="run-missing",
                    decision=HitlDecision.REJECT,
                )
            )
