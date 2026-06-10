"""Tests for ARC Time Travel — run replay & diff debugger (R101, Phase 326)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime_cockpit.time_travel import (
    TIME_TRAVEL_SCHEMA_VERSION,
    Branch,
    StateSnapshot,
    StepType,
    TimeTravelSession,
    compare_paths,
    create_session,
    load_session,
    save_session,
)


class TestStateSnapshot:
    def test_create_snapshot(self) -> None:
        snap = StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL)
        assert snap.step_id == "s1"
        assert snap.step_type == StepType.TOOL_CALL
        assert snap.context == {}
        assert snap.tool_calls == []

    def test_snapshot_to_dict(self) -> None:
        snap = StateSnapshot(
            step_id="s1",
            step_type=StepType.MODEL_OUTPUT,
            context={"key": "value"},
            model_outputs=[{"text": "hello"}],
        )
        d = snap.to_dict()
        assert d["step_id"] == "s1"
        assert d["step_type"] == "model_output"
        assert d["context"]["key"] == "value"
        assert len(d["model_outputs"]) == 1

    def test_snapshot_from_dict(self) -> None:
        data = {
            "step_id": "s2",
            "step_type": "sandbox_decision",
            "timestamp": "2026-01-01T00:00:00",
            "sandbox_decisions": [{"allowed": True}],
        }
        snap = StateSnapshot.from_dict(data)
        assert snap.step_id == "s2"
        assert snap.step_type == StepType.SANDBOX_DECISION
        assert len(snap.sandbox_decisions) == 1


class TestBranch:
    def test_create_branch(self) -> None:
        branch = Branch(branch_id="b1", parent_step_id="s1")
        assert branch.branch_id == "b1"
        assert branch.parent_step_id == "s1"
        assert branch.steps == []

    def test_branch_to_dict(self) -> None:
        branch = Branch(
            branch_id="b1",
            parent_step_id="s1",
            steps=[StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL)],
        )
        d = branch.to_dict()
        assert d["branch_id"] == "b1"
        assert len(d["steps"]) == 1

    def test_branch_from_dict(self) -> None:
        data = {
            "branch_id": "b2",
            "parent_step_id": "s2",
            "steps": [{"step_id": "s2", "step_type": "context_change"}],
        }
        branch = Branch.from_dict(data)
        assert branch.branch_id == "b2"
        assert len(branch.steps) == 1


class TestTimeTravelSession:
    def test_create_session(self) -> None:
        session = TimeTravelSession(session_id="sess1", run_id="run1")
        assert session.session_id == "sess1"
        assert session.run_id == "run1"
        assert session.schema_version == TIME_TRAVEL_SCHEMA_VERSION
        assert session.steps == []
        assert session.current_step_index == -1

    def test_add_step(self) -> None:
        session = create_session("sess1", "run1")
        snap = StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL)
        idx = session.add_step(snap)
        assert idx == 0
        assert len(session.steps) == 1
        assert session.current_step_index == 0

    def test_get_current_step(self) -> None:
        session = create_session("sess1", "run1")
        assert session.get_current_step() is None
        snap = StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL)
        session.add_step(snap)
        current = session.get_current_step()
        assert current is not None
        assert current.step_id == "s1"

    def test_step_forward(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session.add_step(StateSnapshot(step_id="s2", step_type=StepType.MODEL_OUTPUT))
        session.current_step_index = 0
        step = session.step_forward()
        assert step is not None
        assert step.step_id == "s2"
        assert session.current_step_index == 1

    def test_step_forward_at_end(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        step = session.step_forward()
        assert step is None

    def test_step_backward(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session.add_step(StateSnapshot(step_id="s2", step_type=StepType.MODEL_OUTPUT))
        step = session.step_backward()
        assert step is not None
        assert step.step_id == "s1"
        assert session.current_step_index == 0

    def test_step_backward_at_start(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session.current_step_index = 0
        step = session.step_backward()
        assert step is None

    def test_jump_to_step(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session.add_step(StateSnapshot(step_id="s2", step_type=StepType.MODEL_OUTPUT))
        session.add_step(StateSnapshot(step_id="s3", step_type=StepType.SANDBOX_DECISION))
        step = session.jump_to_step(1)
        assert step is not None
        assert step.step_id == "s2"
        assert session.current_step_index == 1

    def test_jump_to_invalid_step(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        step = session.jump_to_step(10)
        assert step is None

    def test_branch_from_step(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session.add_step(StateSnapshot(step_id="s2", step_type=StepType.MODEL_OUTPUT))
        branch = session.branch_from_step(0, "branch1")
        assert branch is not None
        assert branch.branch_id == "branch1"
        assert branch.parent_step_id == "s1"
        assert len(branch.steps) == 1
        assert len(session.branches) == 1

    def test_branch_from_invalid_step(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        branch = session.branch_from_step(10, "branch1")
        assert branch is None

    def test_get_branch(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session.branch_from_step(0, "branch1")
        branch = session.get_branch("branch1")
        assert branch is not None
        assert branch.branch_id == "branch1"
        assert session.get_branch("nonexistent") is None

    def test_to_dict(self) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        d = session.to_dict()
        assert d["session_id"] == "sess1"
        assert d["run_id"] == "run1"
        assert len(d["steps"]) == 1

    def test_from_dict(self) -> None:
        data = {
            "session_id": "sess2",
            "run_id": "run2",
            "steps": [{"step_id": "s1", "step_type": "tool_call"}],
            "branches": [],
            "current_step_index": 0,
        }
        session = TimeTravelSession.from_dict(data)
        assert session.session_id == "sess2"
        assert len(session.steps) == 1

    def test_save_and_load(self, tmp_path: Path) -> None:
        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        path = tmp_path / "test.arctt"
        save_session(session, path)
        assert path.exists()

        loaded = load_session(path)
        assert loaded.session_id == "sess1"
        assert len(loaded.steps) == 1


class TestComparePaths:
    def test_identical_paths(self) -> None:
        session1 = create_session("s1", "r1")
        session1.add_step(
            StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL, context={"x": 1})
        )
        session2 = create_session("s2", "r2")
        session2.add_step(
            StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL, context={"x": 1})
        )
        report = compare_paths(session1, session2)
        assert report["paths_identical"] is True
        assert report["difference_count"] == 0

    def test_different_step_types(self) -> None:
        session1 = create_session("s1", "r1")
        session1.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session2 = create_session("s2", "r2")
        session2.add_step(StateSnapshot(step_id="s1", step_type=StepType.MODEL_OUTPUT))
        report = compare_paths(session1, session2)
        assert report["paths_identical"] is False
        assert report["diverged_at"] == 0

    def test_different_contexts(self) -> None:
        session1 = create_session("s1", "r1")
        session1.add_step(
            StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL, context={"x": 1})
        )
        session2 = create_session("s2", "r2")
        session2.add_step(
            StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL, context={"x": 2})
        )
        report = compare_paths(session1, session2)
        assert report["paths_identical"] is False
        assert any(d["type"] == "context_diff" for d in report["differences"])

    def test_different_lengths(self) -> None:
        session1 = create_session("s1", "r1")
        session1.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session2 = create_session("s2", "r2")
        session2.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session2.add_step(StateSnapshot(step_id="s2", step_type=StepType.MODEL_OUTPUT))
        report = compare_paths(session1, session2)
        assert report["paths_identical"] is False
        assert any(d["type"] == "length_mismatch" for d in report["differences"])


class TestTimeTravelCLI:
    def test_time_travel_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["time-travel", "--help"])
        assert result.exit_code == 0
        assert "time-travel" in result.output.lower()

    def test_time_travel_record(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        output = tmp_path / "test.arctt"
        result = runner.invoke(
            app,
            [
                "time-travel",
                "record",
                "run-123",
                "--output",
                str(output),
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert output.exists()

    def test_time_travel_show(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        path = tmp_path / "show.arctt"
        save_session(session, path)

        runner = CliRunner()
        result = runner.invoke(
            app, ["time-travel", "show", str(path), "--json", "-w", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["session_id"] == "sess1"

    def test_time_travel_replay(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        session.add_step(StateSnapshot(step_id="s2", step_type=StepType.MODEL_OUTPUT))
        session.current_step_index = 0
        path = tmp_path / "replay.arctt"
        save_session(session, path)

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "time-travel",
                "replay",
                str(path),
                "--direction",
                "forward",
                "--steps",
                "1",
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["current_index"] == 1

    def test_time_travel_branch(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        session = create_session("sess1", "run1")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        path = tmp_path / "branch.arctt"
        save_session(session, path)

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "time-travel",
                "branch",
                str(path),
                "--step",
                "0",
                "--branch-id",
                "b1",
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["branch_id"] == "b1"

    def test_time_travel_compare(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        session1 = create_session("s1", "r1")
        session1.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        path1 = tmp_path / "s1.arctt"
        save_session(session1, path1)

        session2 = create_session("s2", "r2")
        session2.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        path2 = tmp_path / "s2.arctt"
        save_session(session2, path2)

        runner = CliRunner()
        result = runner.invoke(
            app, ["time-travel", "compare", str(path1), str(path2), "--json", "-w", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["paths_identical"] is True


class TestTimeTravelError:
    """Phase 343 DoD elevation: structured error class + state coverage."""

    def test_time_travel_error_is_exception(self) -> None:
        from agent_runtime_cockpit.time_travel import TimeTravelError

        assert issubclass(TimeTravelError, Exception)
        err = TimeTravelError("test message")
        assert str(err) == "test message"

    def test_time_travel_error_in_all(self) -> None:
        import agent_runtime_cockpit.time_travel as tt_mod

        assert "TimeTravelError" in tt_mod.__all__

    def test_step_type_has_7_values(self) -> None:
        from agent_runtime_cockpit.time_travel import StepType

        values = [v.value for v in StepType]
        assert "tool_call" in values
        assert "model_output" in values
        assert "sandbox_decision" in values
        assert "context_change" in values
        assert "hitl_gate" in values
        assert "consensus" in values
        assert "branch_point" in values
        assert len(values) == 7

    def test_step_forward_at_end_returns_none(self) -> None:
        """step_forward() past end returns None (explicit done indicator)."""
        from agent_runtime_cockpit.time_travel import StateSnapshot, StepType, create_session

        session = create_session("test-session", "test-run")
        session.add_step(StateSnapshot(step_id="s1", step_type=StepType.TOOL_CALL))
        # Step forward past the only step — at end, returns None
        step = session.step_forward()
        assert step is None
