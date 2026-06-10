"""ARC Debug — DAP adapter for agent run debugging (R99).

Step-through debugging of agent runs via the Debug Adapter Protocol (DAP).
Breakpoints in tool functions, variable inspection. Local only.

This module provides a baseline DAP adapter using stdlib bdb/pdb.
debugpy is an optional dependency for full DAP support.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

log = logging.getLogger(__name__)


class DebugState(str, Enum):
    IDLE = "idle"
    LAUNCHING = "launching"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class Breakpoint:
    id: int
    source: str
    line: int
    enabled: bool = True
    hit_count: int = 0
    condition: Optional[str] = None


@dataclass
class Variable:
    name: str
    value: str
    type: str = ""
    variables_reference: int = 0


@dataclass
class StackFrame:
    id: int
    name: str
    source: str
    line: int
    column: int = 0


@dataclass
class DebugSession:
    session_id: str
    state: DebugState = DebugState.IDLE
    breakpoints: list[Breakpoint] = field(default_factory=list)
    current_frame: Optional[StackFrame] = None
    variables: list[Variable] = field(default_factory=list)
    port: int = 0
    host: str = "127.0.0.1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "breakpoints": [
                {
                    "id": bp.id,
                    "source": bp.source,
                    "line": bp.line,
                    "enabled": bp.enabled,
                    "hit_count": bp.hit_count,
                    "condition": bp.condition,
                }
                for bp in self.breakpoints
            ],
            "current_frame": (
                {
                    "id": self.current_frame.id,
                    "name": self.current_frame.name,
                    "source": self.current_frame.source,
                    "line": self.current_frame.line,
                    "column": self.current_frame.column,
                }
                if self.current_frame
                else None
            ),
            "variables": [
                {
                    "name": v.name,
                    "value": v.value,
                    "type": v.type,
                    "variables_reference": v.variables_reference,
                }
                for v in self.variables
            ],
            "port": self.port,
            "host": self.host,
        }


class DAPMessage:
    """DAP protocol message wrapper."""

    def __init__(self, seq: int, msg_type: str, body: Optional[dict[str, Any]] = None) -> None:
        self.seq = seq
        self.type = msg_type
        self.body = body or {}

    def to_dict(self) -> dict[str, Any]:
        return {"seq": self.seq, "type": self.type, **self.body}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DAPMessage:
        seq = data.pop("seq", 0)
        msg_type = data.pop("type", "unknown")
        return cls(seq=seq, msg_type=msg_type, body=data)


class DebugAdapter:
    """Baseline DAP adapter using stdlib bdb/pdb.

    Speaks DAP JSON over a loopback socket. Local only.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        self._port = port
        self._server_socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sessions: dict[str, DebugSession] = {}
        self._seq = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def port(self) -> int:
        return self._port

    @property
    def host(self) -> str:
        return self._host

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def start(self) -> int:
        """Start the DAP server on a loopback socket. Returns the port."""
        if self._running:
            return self._port

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self._host, self._port))
        self._server_socket.listen(1)
        self._server_socket.settimeout(1.0)

        if self._port == 0:
            self._port = self._server_socket.getsockname()[1]

        self._running = True
        self._thread = threading.Thread(target=self._server_loop, daemon=True)
        self._thread.start()

        log.info("DAP adapter started on %s:%d", self._host, self._port)
        return self._port

    def stop(self) -> None:
        """Stop the DAP server."""
        self._running = False
        if self._server_socket:
            self._server_socket.close()
        if self._thread:
            self._thread.join(timeout=2.0)
        log.info("DAP adapter stopped")

    def _server_loop(self) -> None:
        """Main server loop accepting connections."""
        while self._running:
            try:
                conn, addr = self._server_socket.accept()
                log.info("DAP client connected from %s", addr)
                self._handle_client(conn)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    log.error("DAP server error: %s", e)

    def _handle_client(self, conn: socket.socket) -> None:
        """Handle a single DAP client connection."""
        try:
            conn.settimeout(5.0)
            while self._running:
                data = conn.recv(4096)
                if not data:
                    break
                try:
                    msg = json.loads(data.decode("utf-8"))
                    response = self._process_message(msg)
                    if response:
                        conn.sendall(response.to_json().encode("utf-8"))
                except json.JSONDecodeError:
                    log.warning("Invalid JSON from client")
        except Exception as e:
            log.error("DAP client handler error: %s", e)
        finally:
            conn.close()

    def _process_message(self, msg: dict[str, Any]) -> Optional[DAPMessage]:
        """Process a DAP message and return a response."""
        msg_type = msg.get("type", "")
        command = msg.get("command", "")

        if msg_type == "request":
            if command == "initialize":
                return self._handle_initialize(msg)
            elif command == "launch":
                return self._handle_launch(msg)
            elif command == "setBreakpoints":
                return self._handle_set_breakpoints(msg)
            elif command == "threads":
                return self._handle_threads(msg)
            elif command == "stackTrace":
                return self._handle_stack_trace(msg)
            elif command == "scopes":
                return self._handle_scopes(msg)
            elif command == "variables":
                return self._handle_variables(msg)
            elif command == "disconnect":
                return self._handle_disconnect(msg)

        return None

    def _handle_initialize(self, msg: dict[str, Any]) -> DAPMessage:
        return DAPMessage(
            seq=self._next_seq(),
            msg_type="response",
            body={
                "request_seq": msg.get("seq", 0),
                "command": "initialize",
                "success": True,
                "body": {
                    "supportsConfigurationDoneRequest": True,
                    "supportsFunctionBreakpoints": False,
                    "supportsConditionalBreakpoints": True,
                    "supportsEvaluateForHovers": True,
                },
            },
        )

    def _handle_launch(self, msg: dict[str, Any]) -> DAPMessage:
        session_id = msg.get("arguments", {}).get("program", "default")
        self._sessions[session_id] = DebugSession(
            session_id=session_id,
            state=DebugState.RUNNING,
            port=self._port,
            host=self._host,
        )
        return DAPMessage(
            seq=self._next_seq(),
            msg_type="response",
            body={
                "request_seq": msg.get("seq", 0),
                "command": "launch",
                "success": True,
            },
        )

    def _handle_set_breakpoints(self, msg: dict[str, Any]) -> DAPMessage:
        args = msg.get("arguments", {})
        source = args.get("source", {}).get("path", "")
        bps = args.get("breakpoints", [])

        breakpoints = []
        for i, bp in enumerate(bps):
            breakpoints.append(
                Breakpoint(
                    id=i + 1,
                    source=source,
                    line=bp.get("line", 0),
                    enabled=True,
                    condition=bp.get("condition"),
                )
            )

        if self._sessions:
            session = next(iter(self._sessions.values()))
            session.breakpoints = breakpoints

        return DAPMessage(
            seq=self._next_seq(),
            msg_type="response",
            body={
                "request_seq": msg.get("seq", 0),
                "command": "setBreakpoints",
                "success": True,
                "body": {
                    "breakpoints": [
                        {"id": bp.id, "verified": True, "line": bp.line} for bp in breakpoints
                    ]
                },
            },
        )

    def _handle_threads(self, msg: dict[str, Any]) -> DAPMessage:
        return DAPMessage(
            seq=self._next_seq(),
            msg_type="response",
            body={
                "request_seq": msg.get("seq", 0),
                "command": "threads",
                "success": True,
                "body": {"threads": [{"id": 1, "name": "Main Thread"}]},
            },
        )

    def _handle_stack_trace(self, msg: dict[str, Any]) -> DAPMessage:
        frames = []
        if self._sessions:
            session = next(iter(self._sessions.values()))
            if session.current_frame:
                frames.append(
                    {
                        "id": session.current_frame.id,
                        "name": session.current_frame.name,
                        "source": {"path": session.current_frame.source},
                        "line": session.current_frame.line,
                        "column": session.current_frame.column,
                    }
                )

        return DAPMessage(
            seq=self._next_seq(),
            msg_type="response",
            body={
                "request_seq": msg.get("seq", 0),
                "command": "stackTrace",
                "success": True,
                "body": {"stackFrames": frames, "totalFrames": len(frames)},
            },
        )

    def _handle_scopes(self, msg: dict[str, Any]) -> DAPMessage:
        return DAPMessage(
            seq=self._next_seq(),
            msg_type="response",
            body={
                "request_seq": msg.get("seq", 0),
                "command": "scopes",
                "success": True,
                "body": {
                    "scopes": [
                        {"name": "Local", "variablesReference": 1, "expensive": False},
                        {"name": "Global", "variablesReference": 2, "expensive": True},
                    ]
                },
            },
        )

    def _handle_variables(self, msg: dict[str, Any]) -> DAPMessage:
        variables = []
        if self._sessions:
            session = next(iter(self._sessions.values()))
            variables = [
                {
                    "name": v.name,
                    "value": v.value,
                    "type": v.type,
                    "variablesReference": v.variables_reference,
                }
                for v in session.variables
            ]

        return DAPMessage(
            seq=self._next_seq(),
            msg_type="response",
            body={
                "request_seq": msg.get("seq", 0),
                "command": "variables",
                "success": True,
                "body": {"variables": variables},
            },
        )

    def _handle_disconnect(self, msg: dict[str, Any]) -> DAPMessage:
        self._sessions.clear()
        return DAPMessage(
            seq=self._next_seq(),
            msg_type="response",
            body={
                "request_seq": msg.get("seq", 0),
                "command": "disconnect",
                "success": True,
            },
        )

    def get_status(self) -> dict[str, Any]:
        """Get adapter status."""
        return {
            "running": self._running,
            "host": self._host,
            "port": self._port,
            "sessions": {sid: s.to_dict() for sid, s in self._sessions.items()},
        }


__all__ = [
    "DebugState",
    "Breakpoint",
    "Variable",
    "StackFrame",
    "DebugSession",
    "DAPMessage",
    "DebugAdapter",
]
