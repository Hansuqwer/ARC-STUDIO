import pytest

from datetime import datetime, timezone

from agent_runtime_cockpit.adapters.base import CapabilityReport
from agent_runtime_cockpit.orchestration import runtime_router
from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus


class _FakeRegistry:
    def __init__(self, adapters):
        self._adapters = adapters

    def all(self):
        return list(self._adapters.values())

    def get(self, adapter_id):
        return self._adapters.get(adapter_id)


class _FakeAdapter:
    def __init__(self, runtime_id, can_run, requires_paid_calls=False):
        self.adapter_id = runtime_id
        self._report = CapabilityReport(
            runtime_id=runtime_id,
            detected=True,
            can_run=can_run,
            availability="runnable" if can_run else "detected_not_runnable",
            requires_paid_calls=requires_paid_calls,
        )

    def capability_report(self, workspace):
        return self._report

    async def run_workflow(self, workflow_id, inputs=None):
        now = datetime.now(timezone.utc).isoformat()
        return RunRecord(
            id=f"run-{self.adapter_id}",
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=RunStatus.COMPLETED,
            started_at=now,
            ended_at=now,
            events=[],
            metadata={"inputs": inputs or {}},
        )


def _install_fake_registry(monkeypatch, specs):
    adapters = {key: _FakeAdapter(key, **value) for key, value in specs.items()}
    monkeypatch.setattr(runtime_router, "default_registry", lambda: _FakeRegistry(adapters))


def test_resolve_unknown_runtime(tmp_path):
    with pytest.raises(runtime_router.UnknownRuntime):
        runtime_router.resolve(tmp_path, "nope")


def test_resolve_combo_requires_runnable_members(monkeypatch, tmp_path):
    _install_fake_registry(monkeypatch, {"crewai": {"can_run": False}, "swarmgraph": {"can_run": True}})

    with pytest.raises(runtime_router.ComboNotRunnable):
        runtime_router.resolve(tmp_path, ["crewai", "swarmgraph"])


def test_resolve_combo_returns_combo_adapter(monkeypatch, tmp_path):
    _install_fake_registry(monkeypatch, {"langgraph": {"can_run": True}, "swarmgraph": {"can_run": True}})

    routed = runtime_router.resolve(tmp_path, ["langgraph", "swarmgraph"])

    assert routed.adapter.adapter_id == "combo"
    assert routed.chosen_by == "combo"
    assert routed.report.can_run is True


@pytest.mark.asyncio
async def test_combo_adapter_runs_members_sequentially(monkeypatch, tmp_path):
    _install_fake_registry(monkeypatch, {"langgraph": {"can_run": True}, "swarmgraph": {"can_run": True}})
    routed = runtime_router.resolve(tmp_path, ["langgraph", "swarmgraph"])

    run = await routed.adapter.run_workflow("wf-combo", {"workspace": str(tmp_path)})

    assert run.status == RunStatus.COMPLETED
    assert run.runtime == "combo"
    assert run.metadata["runtimes"] == ["langgraph", "swarmgraph"]
    assert [child["runtime"] for child in run.metadata["child_runs"]] == ["langgraph", "swarmgraph"]


def test_auto_selects_swarmgraph_by_priority(monkeypatch, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    tools = tmp_path / "bin"
    tools.mkdir()
    cli = tools / "swarmgraph"
    cli.write_text("#!/usr/bin/env sh\nprintf '%s\n' '{\"status\":\"completed\"}'\n")
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    routed = runtime_router.resolve(ws, "auto")

    assert routed.adapter.adapter_id == "swarmgraph"
    assert routed.chosen_by == "auto"


def test_explicit_crewai_not_runnable_without_target(tmp_path):
    with pytest.raises(runtime_router.RuntimeNotRunnable):
        runtime_router.resolve(tmp_path, "crewai")


def test_langgraph_swarmgraph_resolves_as_fake_offline_runnable(tmp_path):
    routed = runtime_router.resolve(tmp_path, "langgraph+swarmgraph")

    assert routed.adapter.adapter_id == "langgraph+swarmgraph"
    assert routed.chosen_by == "explicit"
    assert routed.report.can_run is True
    assert routed.report.availability == "runnable"
    assert routed.report.requires_paid_calls is False
    assert "fake/offline" in (routed.report.reason or "")


def test_list_runtimes_includes_adoption_modes(monkeypatch, tmp_path):
    _install_fake_registry(monkeypatch, {"swarmgraph": {"can_run": False}})

    reports = runtime_router.list_runtimes(tmp_path)
    ids = {report.runtime_id for report in reports}

    assert "langgraph+swarmgraph" in ids
    adoption = next(report for report in reports if report.runtime_id == "langgraph+swarmgraph")
    assert adoption.can_run is True
    assert adoption.availability == "runnable"
    assert adoption.requires_paid_calls is False
    assert "fake/offline" in (adoption.reason or "")
    assert "real" in (adoption.reason or "")
    assert "gated" in (adoption.reason or "")


def test_auto_skips_paid_when_flag_off(monkeypatch, tmp_path):
    _install_fake_registry(monkeypatch, {
        "swarmgraph": {"can_run": False},
        "langgraph": {"can_run": False},
        "crewai": {"can_run": True, "requires_paid_calls": True},
    })

    with pytest.raises(runtime_router.RuntimeNotRunnable, match="paid-call runtimes"):
        runtime_router.resolve(tmp_path, "auto", allow_paid_calls=False)


def test_auto_picks_paid_when_flag_on(monkeypatch, tmp_path):
    _install_fake_registry(monkeypatch, {
        "swarmgraph": {"can_run": False},
        "langgraph": {"can_run": False},
        "crewai": {"can_run": True, "requires_paid_calls": True},
    })

    routed = runtime_router.resolve(tmp_path, "auto", allow_paid_calls=True)

    assert routed.adapter.adapter_id == "crewai"
    assert routed.chosen_by == "auto"


def test_explicit_paid_runtime_still_routes_without_flag(monkeypatch, tmp_path):
    _install_fake_registry(monkeypatch, {"crewai": {"can_run": True, "requires_paid_calls": True}})

    routed = runtime_router.resolve(tmp_path, "crewai", allow_paid_calls=False)

    assert routed.adapter.adapter_id == "crewai"


def test_auto_priority_holds_when_first_priority_is_paid_and_blocked(monkeypatch, tmp_path):
    _install_fake_registry(monkeypatch, {
        "swarmgraph": {"can_run": True, "requires_paid_calls": True},
        "langgraph": {"can_run": True},
        "crewai": {"can_run": False},
    })

    routed = runtime_router.resolve(tmp_path, "auto", allow_paid_calls=False)

    assert routed.adapter.adapter_id == "langgraph"
