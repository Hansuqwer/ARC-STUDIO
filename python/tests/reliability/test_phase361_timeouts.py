from __future__ import annotations

from agent_runtime_cockpit.debug import DEFAULT_CONNECT_TIMEOUT_SECONDS, DebugAdapter
from agent_runtime_cockpit.tasks.scheduler import ScheduleConfig
from agent_runtime_cockpit.voice import (
    DEFAULT_LISTEN_TIMEOUT_SECONDS,
    FakeVoiceDriver,
    VoicePipeline,
)


def test_voice_listen_timeout_state():
    result = VoicePipeline(FakeVoiceDriver()).listen()
    assert result["state"] == "degraded"
    assert result["timeout_seconds"] == DEFAULT_LISTEN_TIMEOUT_SECONDS


def test_debug_connect_refused_degraded():
    adapter = DebugAdapter()
    result = adapter.connect(port=9, timeout_seconds=0.01)
    assert result["ok"] is False
    assert result["state"] in {"degraded", "timeout"}
    assert DEFAULT_CONNECT_TIMEOUT_SECONDS == 10.0


def test_scheduler_timeout_config_visible():
    config = ScheduleConfig(task_timeout_seconds=1.5)
    assert config.task_timeout_seconds == 1.5
