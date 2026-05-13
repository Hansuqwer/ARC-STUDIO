"""CrewAI listener that publishes adapter-native events to a queue."""
from __future__ import annotations

import asyncio
import time
from typing import Any


class ArcCrewAIListener:
    def __init__(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.queue = queue

    def _emit(self, native: dict[str, Any]) -> None:
        native.setdefault("ts", time.time())
        self.queue.put_nowait(native)

    def attach(self) -> None:
        from crewai.events import (  # type: ignore
            crewai_event_bus,
            CrewKickoffStartedEvent, CrewKickoffCompletedEvent, CrewKickoffFailedEvent,
            AgentExecutionStartedEvent, AgentExecutionCompletedEvent,
            TaskStartedEvent, TaskCompletedEvent,
            ToolUsageStartedEvent, ToolUsageFinishedEvent,
            LLMStreamChunkEvent,
        )

        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def _on_kickoff(_src: Any, event: Any) -> None:
            self._emit({"kind": "crew.start", "crew": getattr(event, "crew_name", "?")})

        @crewai_event_bus.on(CrewKickoffCompletedEvent)
        def _on_complete(_src: Any, event: Any) -> None:
            self._emit({"kind": "crew.finish", "output": str(getattr(event, "output", ""))})

        @crewai_event_bus.on(CrewKickoffFailedEvent)
        def _on_fail(_src: Any, event: Any) -> None:
            self._emit({"kind": "crew.error", "error": getattr(event, "error", "unknown")})

        @crewai_event_bus.on(AgentExecutionStartedEvent)
        def _on_agent_start(_src: Any, event: Any) -> None:
            self._emit({"kind": "agent.start", "agent": getattr(event.agent, "role", "?")})

        @crewai_event_bus.on(AgentExecutionCompletedEvent)
        def _on_agent_done(_src: Any, event: Any) -> None:
            self._emit({"kind": "agent.text",
                        "agent": getattr(event.agent, "role", "?"),
                        "text": str(getattr(event, "output", ""))})

        @crewai_event_bus.on(TaskStartedEvent)
        def _on_task_start(_src: Any, event: Any) -> None:
            self._emit({"kind": "task.start", "task": str(getattr(event, "task", ""))[:120]})

        @crewai_event_bus.on(TaskCompletedEvent)
        def _on_task_done(_src: Any, event: Any) -> None:
            self._emit({"kind": "task.finish", "task": str(getattr(event, "task", ""))[:120]})

        @crewai_event_bus.on(ToolUsageStartedEvent)
        def _on_tool_start(_src: Any, event: Any) -> None:
            self._emit({"kind": "tool.call",
                        "tool": {"id": f"tool-{int(time.time()*1000)}",
                                 "name": getattr(event, "tool_name", "tool"),
                                 "args": getattr(event, "tool_args", {})}})

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def _on_tool_done(_src: Any, event: Any) -> None:
            self._emit({"kind": "tool.result",
                        "tool_id": getattr(event, "tool_name", "tool"),
                        "result": getattr(event, "output", None)})

        @crewai_event_bus.on(LLMStreamChunkEvent)
        def _on_llm_chunk(_src: Any, event: Any) -> None:
            self._emit({"kind": "llm.chunk", "delta": getattr(event, "chunk", "")})
