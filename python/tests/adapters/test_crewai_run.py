from pathlib import Path
import sys

import pytest

from agent_runtime_cockpit.adapters.crewai import CrewAIAdapter, EXPORT_ENV
from agent_runtime_cockpit.protocol.schemas import RunStatus


def _copy_fixture(tmp_path: Path) -> None:
    sys.modules.pop("fixtures", None)
    sys.modules.pop("fixtures.fake_crewai_export", None)
    package = tmp_path / "fixtures"
    package.mkdir()
    package.joinpath("__init__.py").write_text("")
    source = Path(__file__).parents[1] / "fixtures" / "fake_crewai_export.py"
    package.joinpath("fake_crewai_export.py").write_text(source.read_text())


def _make_runnable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(CrewAIAdapter, "_crewai_importable", lambda self: (True, "test"))
    monkeypatch.setattr(CrewAIAdapter, "detect", lambda self, workspace: (True, 1.0, ["fixture"]))


@pytest.mark.asyncio
async def test_crewai_fake_export_normalizes_tasks_output(monkeypatch, tmp_path):
    _copy_fixture(tmp_path)
    _make_runnable(monkeypatch)
    monkeypatch.setenv(EXPORT_ENV, "fixtures.fake_crewai_export:make_crew")

    run = await CrewAIAdapter().run_workflow("wf-ca", {"workspace": str(tmp_path), "allow_paid_calls": True})

    assert run.status == RunStatus.COMPLETED
    output = run.events[-1].data
    assert output["raw"] == "crew raw output"
    assert output["tasks_output"] == [
        {"task_id": "research-task", "agent": "researcher", "output_text": "task raw output", "raw": "task raw output"}
    ]


@pytest.mark.asyncio
async def test_crewai_timeout_returns_truthful_failure(monkeypatch, tmp_path):
    _copy_fixture(tmp_path)
    _make_runnable(monkeypatch)
    monkeypatch.setenv(EXPORT_ENV, "fixtures.fake_crewai_export:make_slow_crew")

    run = await CrewAIAdapter().run_workflow(
        "wf-ca",
        {"workspace": str(tmp_path), "allow_paid_calls": True, "timeout_seconds": 0.01},
    )

    assert run.status == RunStatus.FAILED
    assert run.events[-1].data["code"] == "CREWAI_TIMEOUT"


@pytest.mark.asyncio
async def test_crewai_cancelled_returns_cancelled_record(monkeypatch, tmp_path):
    _copy_fixture(tmp_path)
    _make_runnable(monkeypatch)
    monkeypatch.setenv(EXPORT_ENV, "fixtures.fake_crewai_export:make_cancelled_crew")

    run = await CrewAIAdapter().run_workflow("wf-ca", {"workspace": str(tmp_path), "allow_paid_calls": True})

    assert run.status == RunStatus.CANCELLED
    assert run.events[-1].type == "RUN_CANCELLED"
    assert run.metadata["error_code"] == "CREWAI_CANCELLED"
