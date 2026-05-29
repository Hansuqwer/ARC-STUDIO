"""Deterministic terminal streaming envelopes for CLI command execution."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..isolation.subprocess import DEFAULT_SAFE_ENV_KEYS, _is_blocked_env_key, redact_output
from ..security.sandbox import utc_now


class StreamEventType(str, Enum):
    STARTED = "started"
    STDOUT = "stdout"
    STDERR = "stderr"
    TRUNCATED = "truncated"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    COMPLETED = "completed"
    DISCONNECTED = "disconnected"


class TerminalStreamEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    stream_id: str
    event: StreamEventType
    source: Literal["sandbox", "testbench", "provider_shell"]
    mode: Literal["live", "replay", "stub"] = "live"
    ts: str = Field(default_factory=utc_now)
    sequence: int
    stream: Literal["stdout", "stderr", "control"] = "control"
    data: str = ""
    command: list[str] = Field(default_factory=list)
    exit_code: int | None = None
    reason: str | None = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    redaction_applied: bool = False


class TerminalStreamResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stream_id: str
    source: str
    command: list[str]
    exit_code: int | None
    terminal_event: StreamEventType
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    redaction_applied: bool = False
    duration_ms: int = 0
    event_count: int = 0


def filtered_stream_env(safe_env_keys: frozenset[str] | None = None) -> dict[str, str]:
    keys = safe_env_keys or DEFAULT_SAFE_ENV_KEYS
    return {
        key: os.environ[key] for key in keys if key in os.environ and not _is_blocked_env_key(key)
    }


def stream_subprocess_events(
    command: list[str],
    *,
    cwd: Path,
    source: Literal["sandbox", "testbench", "provider_shell"],
    timeout_seconds: int = 30,
    max_output_bytes: int = 65_536,
    cancel_after_events: int | None = None,
    safe_env_keys: frozenset[str] | None = None,
) -> tuple[list[TerminalStreamEvent], TerminalStreamResult]:
    """Run argv and return incremental stream events plus final summary.

    Cancellation is deterministic for tests/CI: ``cancel_after_events`` kills the
    process group after that many stdout/stderr chunk events.
    """
    if not command:
        raise ValueError("command must not be empty")
    stream_id = f"stream-{uuid.uuid4().hex[:12]}"
    sequence = 0
    events: list[TerminalStreamEvent] = []

    def emit(event: StreamEventType, **kwargs: Any) -> None:
        nonlocal sequence
        events.append(
            TerminalStreamEvent(
                stream_id=stream_id,
                event=event,
                source=source,
                sequence=sequence,
                command=command,
                **kwargs,
            )
        )
        sequence += 1

    start = time.monotonic()
    emit(StreamEventType.STARTED)
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=filtered_stream_env(safe_env_keys),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ, "stdout")
    sel.register(proc.stderr, selectors.EVENT_READ, "stderr")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    truncated = {"stdout": False, "stderr": False}
    chunk_events = 0
    terminal = StreamEventType.COMPLETED
    reason: str | None = None
    while sel.get_map():
        if time.monotonic() - start > timeout_seconds:
            terminal = StreamEventType.TIMEOUT
            reason = "timeout"
            _kill_process_group(proc)
            break
        for key, _mask in sel.select(timeout=0.05):
            stream_name = str(key.data)
            raw = (
                key.fileobj.read1(4096) if hasattr(key.fileobj, "read1") else key.fileobj.read(4096)
            )
            if not raw:
                sel.unregister(key.fileobj)
                continue
            remaining = max_output_bytes - len(buffers[stream_name])
            stored = raw[: max(remaining, 0)]
            if stored:
                buffers[stream_name].extend(stored)
                text = redact_output(stored.decode("utf-8", errors="replace"))
                emit(
                    StreamEventType.STDOUT if stream_name == "stdout" else StreamEventType.STDERR,
                    stream=stream_name,
                    data=text,
                )
                chunk_events += 1
            if len(raw) > remaining:
                truncated[stream_name] = True
                emit(
                    StreamEventType.TRUNCATED,
                    stream=stream_name,
                    reason=f"{stream_name}_max_output_bytes",
                )
            if cancel_after_events is not None and chunk_events >= cancel_after_events:
                terminal = StreamEventType.CANCELLED
                reason = "cancel_after_events"
                _kill_process_group(proc)
                break
        if terminal in {StreamEventType.CANCELLED, StreamEventType.TIMEOUT}:
            break
        if proc.poll() is not None and not sel.select(timeout=0):
            for fileobj in list(sel.get_map().values()):
                try:
                    sel.unregister(fileobj.fileobj)
                except Exception:
                    pass
    if terminal in {StreamEventType.CANCELLED, StreamEventType.TIMEOUT}:
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            _kill_process_group(proc)
            proc.wait()
    else:
        proc.wait()
    stdout = bytes(buffers["stdout"]).decode("utf-8", errors="replace")
    stderr = bytes(buffers["stderr"]).decode("utf-8", errors="replace")
    redacted_stdout = redact_output(stdout)
    redacted_stderr = redact_output(stderr)
    redaction_applied = redacted_stdout != stdout or redacted_stderr != stderr
    stdout = redacted_stdout
    stderr = redacted_stderr
    emit(
        terminal,
        exit_code=proc.returncode,
        reason=reason,
        stdout_truncated=truncated["stdout"],
        stderr_truncated=truncated["stderr"],
        redaction_applied=redaction_applied,
    )
    result = TerminalStreamResult(
        stream_id=stream_id,
        source=source,
        command=command,
        exit_code=proc.returncode,
        terminal_event=terminal,
        stdout=stdout,
        stderr=stderr,
        stdout_truncated=truncated["stdout"],
        stderr_truncated=truncated["stderr"],
        redaction_applied=redaction_applied,
        duration_ms=int((time.monotonic() - start) * 1000),
        event_count=len(events),
    )
    return events, result


def disconnected_replay_event(
    stream_id: str,
    *,
    source: Literal["sandbox", "testbench", "provider_shell"],
    reason: str = "producer_disconnected",
) -> TerminalStreamEvent:
    return TerminalStreamEvent(
        stream_id=stream_id,
        event=StreamEventType.DISCONNECTED,
        source=source,
        mode="replay",
        sequence=0,
        reason=reason,
    )


def _kill_process_group(proc: subprocess.Popen[Any]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
