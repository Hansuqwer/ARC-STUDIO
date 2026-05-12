from pathlib import Path
import sys

import pytest

from agent_runtime_cockpit.adapters import langgraph as langgraph_module
from agent_runtime_cockpit.adapters.langgraph import (
    EXPORT_ENV,
    LG_DEP_MISSING,
    LG_EXPORT_NOT_FOUND,
    LG_EXPORT_UNSET,
    LG_INVOKE_FAILED,
    LG_TARGET_INVALID,
    LangGraphAdapter,
)
from agent_runtime_cockpit.protocol.schemas import RunStatus


def _copy_fixture(tmp_path: Path) -> None:
    sys.modules.pop("fixtures", None)
    sys.modules.pop("fixtures.fake_langgraph_export", None)
    package = tmp_path / "fixtures"
    package.mkdir()
    package.joinpath("__init__.py").write_text("")
    source = Path(__file__).parents[1] / "fixtures" / "fake_langgraph_export.py"
    package.joinpath("fake_langgraph_export.py").write_text(source.read_text())


@pytest.mark.asyncio
async def test_langgraph_missing_dependency_returns_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(langgraph_module.importlib.util, "find_spec", lambda name: None if name == "langgraph" else langgraph_module.importlib.util.find_spec(name))

    run = await LangGraphAdapter().run_workflow("wf-lg", {"workspace": str(tmp_path)})

    assert run.status == RunStatus.FAILED
    assert run.events[-1].data["error_code"] == LG_DEP_MISSING


@pytest.mark.asyncio
async def test_langgraph_export_unset_returns_failed(monkeypatch, tmp_path):
    monkeypatch.delenv(EXPORT_ENV, raising=False)

    run = await LangGraphAdapter().run_workflow("wf-lg", {"workspace": str(tmp_path)})

    assert run.status == RunStatus.FAILED
    assert run.events[-1].data["error_code"] == LG_EXPORT_UNSET


@pytest.mark.asyncio
async def test_langgraph_export_target_not_found(monkeypatch, tmp_path):
    _copy_fixture(tmp_path)
    monkeypatch.setenv(EXPORT_ENV, "fixtures.fake_langgraph_export:missing")

    run = await LangGraphAdapter().run_workflow("wf-lg", {"workspace": str(tmp_path)})

    assert run.status == RunStatus.FAILED
    assert run.events[-1].data["error_code"] == LG_EXPORT_NOT_FOUND


@pytest.mark.asyncio
async def test_langgraph_fake_graph_happy_path(monkeypatch, tmp_path):
    _copy_fixture(tmp_path)
    monkeypatch.setenv(EXPORT_ENV, "fixtures.fake_langgraph_export:make_graph")

    run = await LangGraphAdapter().run_workflow("wf-lg", {"workspace": str(tmp_path), "prompt": "hi"})

    assert run.status == RunStatus.COMPLETED
    assert [event.type for event in run.events] == ["RUN_STARTED", "RUN_COMPLETED"]
    assert run.events[-1].data["state"]["messages"] == ["ok"]
    assert run.events[-1].data["state"]["inputs"]["prompt"] == "hi"


@pytest.mark.asyncio
async def test_langgraph_failed_invoke_returns_redacted_error(monkeypatch, tmp_path):
    _copy_fixture(tmp_path)
    monkeypatch.setenv(EXPORT_ENV, "fixtures.fake_langgraph_export:make_failing_graph")

    run = await LangGraphAdapter().run_workflow("wf-lg", {"workspace": str(tmp_path)})

    assert run.status == RunStatus.FAILED
    assert run.events[-1].data["error_code"] == LG_INVOKE_FAILED
    assert "sk-test-redacted" not in run.events[-1].data["redacted_message"]


@pytest.mark.asyncio
async def test_langgraph_rejects_export_outside_workspace(monkeypatch, tmp_path):
    monkeypatch.setenv(EXPORT_ENV, "os:getcwd")

    run = await LangGraphAdapter().run_workflow("wf-lg", {"workspace": str(tmp_path)})

    assert run.status == RunStatus.FAILED
    assert run.events[-1].data["error_code"] == LG_TARGET_INVALID
