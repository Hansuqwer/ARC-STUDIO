"""Tests for ARC Debug — DAP adapter for agent run debugging (R99, Phase 324)."""

from __future__ import annotations

import json

from agent_runtime_cockpit.debug import (
    Breakpoint,
    DAPMessage,
    DebugAdapter,
    DebugSession,
    DebugState,
    StackFrame,
    Variable,
)


class TestDAPMessage:
    def test_create_message(self) -> None:
        msg = DAPMessage(seq=1, msg_type="request", body={"command": "initialize"})
        assert msg.seq == 1
        assert msg.type == "request"
        assert msg.body["command"] == "initialize"

    def test_to_dict(self) -> None:
        msg = DAPMessage(seq=1, msg_type="request", body={"command": "initialize"})
        d = msg.to_dict()
        assert d["seq"] == 1
        assert d["type"] == "request"
        assert d["command"] == "initialize"

    def test_to_json(self) -> None:
        msg = DAPMessage(seq=1, msg_type="request", body={"command": "initialize"})
        j = msg.to_json()
        data = json.loads(j)
        assert data["seq"] == 1
        assert data["type"] == "request"

    def test_from_dict(self) -> None:
        data = {"seq": 5, "type": "response", "command": "initialize", "success": True}
        msg = DAPMessage.from_dict(data)
        assert msg.seq == 5
        assert msg.type == "response"
        assert msg.body["command"] == "initialize"
        assert msg.body["success"] is True


class TestDebugSession:
    def test_create_session(self) -> None:
        session = DebugSession(session_id="test-session")
        assert session.session_id == "test-session"
        assert session.state == DebugState.IDLE
        assert session.breakpoints == []

    def test_session_with_breakpoints(self) -> None:
        session = DebugSession(
            session_id="test",
            breakpoints=[
                Breakpoint(id=1, source="main.py", line=10),
                Breakpoint(id=2, source="main.py", line=20),
            ],
        )
        assert len(session.breakpoints) == 2
        assert session.breakpoints[0].line == 10

    def test_session_with_frame(self) -> None:
        session = DebugSession(
            session_id="test",
            current_frame=StackFrame(id=1, name="main", source="main.py", line=15),
        )
        assert session.current_frame is not None
        assert session.current_frame.name == "main"

    def test_to_dict(self) -> None:
        session = DebugSession(
            session_id="test",
            state=DebugState.RUNNING,
            port=5678,
        )
        d = session.to_dict()
        assert d["session_id"] == "test"
        assert d["state"] == "running"
        assert d["port"] == 5678


class TestBreakpoint:
    def test_create_breakpoint(self) -> None:
        bp = Breakpoint(id=1, source="main.py", line=10)
        assert bp.id == 1
        assert bp.source == "main.py"
        assert bp.line == 10
        assert bp.enabled is True
        assert bp.hit_count == 0

    def test_conditional_breakpoint(self) -> None:
        bp = Breakpoint(id=1, source="main.py", line=10, condition="x > 5")
        assert bp.condition == "x > 5"


class TestVariable:
    def test_create_variable(self) -> None:
        var = Variable(name="x", value="42", type="int")
        assert var.name == "x"
        assert var.value == "42"
        assert var.type == "int"


class TestDebugAdapter:
    def test_create_adapter(self) -> None:
        adapter = DebugAdapter()
        assert adapter.host == "127.0.0.1"
        assert adapter.port == 0
        assert adapter.is_running is False

    def test_start_and_stop(self) -> None:
        adapter = DebugAdapter()
        port = adapter.start()
        assert port > 0
        assert adapter.is_running is True
        adapter.stop()
        assert adapter.is_running is False

    def test_start_returns_port(self) -> None:
        adapter = DebugAdapter(port=0)
        port = adapter.start()
        assert port > 0
        adapter.stop()

    def test_get_status(self) -> None:
        adapter = DebugAdapter()
        status = adapter.get_status()
        assert status["running"] is False
        assert status["host"] == "127.0.0.1"
        assert "sessions" in status

    def test_handle_initialize(self) -> None:
        adapter = DebugAdapter()
        msg = {"type": "request", "command": "initialize", "seq": 1}
        response = adapter._process_message(msg)
        assert response is not None
        assert response.type == "response"
        assert response.body["success"] is True
        assert response.body["command"] == "initialize"

    def test_handle_launch(self) -> None:
        adapter = DebugAdapter()
        msg = {
            "type": "request",
            "command": "launch",
            "seq": 2,
            "arguments": {"program": "test-workflow"},
        }
        response = adapter._process_message(msg)
        assert response is not None
        assert response.body["success"] is True
        assert "test-workflow" in adapter._sessions

    def test_handle_set_breakpoints(self) -> None:
        adapter = DebugAdapter()
        adapter._sessions["test"] = DebugSession(session_id="test")
        msg = {
            "type": "request",
            "command": "setBreakpoints",
            "seq": 3,
            "arguments": {
                "source": {"path": "main.py"},
                "breakpoints": [{"line": 10}, {"line": 20}],
            },
        }
        response = adapter._process_message(msg)
        assert response is not None
        assert response.body["success"] is True
        bps = response.body["body"]["breakpoints"]
        assert len(bps) == 2
        assert bps[0]["line"] == 10

    def test_handle_threads(self) -> None:
        adapter = DebugAdapter()
        msg = {"type": "request", "command": "threads", "seq": 4}
        response = adapter._process_message(msg)
        assert response is not None
        assert response.body["success"] is True
        threads = response.body["body"]["threads"]
        assert len(threads) == 1
        assert threads[0]["name"] == "Main Thread"

    def test_handle_disconnect(self) -> None:
        adapter = DebugAdapter()
        adapter._sessions["test"] = DebugSession(session_id="test")
        msg = {"type": "request", "command": "disconnect", "seq": 5}
        response = adapter._process_message(msg)
        assert response is not None
        assert response.body["success"] is True
        assert len(adapter._sessions) == 0


class TestDebugCLI:
    def test_debug_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["debug", "--help"])
        assert result.exit_code == 0
        assert "debug" in result.output.lower()

    def test_debug_status(self, tmp_path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["debug", "status", "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "running" in data["data"]

    def test_debug_launch(self, tmp_path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app, ["debug", "launch", "test-workflow", "--json", "-w", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["session_id"] == "test-workflow"
        assert data["data"]["port"] > 0

    def test_debug_attach(self, tmp_path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app, ["debug", "attach", "--port", "5678", "--json", "-w", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["port"] == 5678


class TestDebugError:
    """Phase 341 DoD elevation: structured error class + state coverage."""

    def test_debug_error_is_exception(self) -> None:
        from agent_runtime_cockpit.debug import DebugError

        assert issubclass(DebugError, Exception)
        err = DebugError("test message")
        assert str(err) == "test message"

    def test_debug_error_in_all(self) -> None:
        import agent_runtime_cockpit.debug as debug_mod

        assert "DebugError" in debug_mod.__all__

    def test_debug_state_enum_has_6_states(self) -> None:
        from agent_runtime_cockpit.debug import DebugState

        states = [s.value for s in DebugState]
        assert "idle" in states
        assert "launching" in states
        assert "running" in states
        assert "paused" in states
        assert "stopped" in states
        assert "error" in states
        assert len(states) == 6

    def test_debug_session_default_state_is_idle(self) -> None:
        from agent_runtime_cockpit.debug import DebugSession, DebugState

        session = DebugSession(session_id="test-1")
        assert session.state == DebugState.IDLE
        assert session.host == "127.0.0.1"
        assert session.variables == []
        assert session.breakpoints == []
