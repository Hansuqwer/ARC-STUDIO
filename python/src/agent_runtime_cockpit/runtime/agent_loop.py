"""Autonomous multi-turn coding agent loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.runtime.turn_manager import TurnManager, TurnResult

DEFAULT_AGENT_SYSTEM_PROMPT = """You are ARC Studio's autonomous coding agent.
Use available tools to complete the task: read_file, list_directory, write_file,
edit_file, create_file, bash, get_current_time. Prefer targeted edits. Run safe
read-only and workspace-local verification commands. Do not request network,
install, destructive, or privileged commands unless explicitly required. When the
task is complete, respond with a concise final summary beginning with Done."""


@dataclass(frozen=True)
class AgentLoopResult:
    content: str
    turns: int
    history: list[dict[str, str]]
    degraded: bool = False
    degraded_reason: str | None = None
    cost_summary: dict[str, Any] = field(default_factory=dict)


class AgentLoop:
    """Autonomous multi-turn coding agent loop."""

    def __init__(
        self,
        turn_manager: TurnManager,
        session: ChatSession,
        max_turns: int = 25,
        system_prompt: str | None = None,
    ) -> None:
        self.turn_manager = turn_manager
        self.session = session
        self.max_turns = max_turns
        self.system_prompt = system_prompt or DEFAULT_AGENT_SYSTEM_PROMPT

    async def run(self, task: str, cancellation_token: CancellationToken) -> AgentLoopResult:
        self._inject_system_prompt()
        prompt = task
        final: TurnResult | None = None
        turns = 0
        while turns < self.max_turns:
            cancellation_token.raise_if_cancelled()
            turns += 1
            final = await self.turn_manager.run_turn(
                self.session,
                prompt,
                cancellation_token=cancellation_token,
                stream=False,
            )
            if final.partial or final.degraded:
                return self._result(final, turns)
            response = final.response
            if response is None or (
                not response.tool_calls and response.finish_reason != "tool_use"
            ):
                return self._result(final, turns)
            prompt = "Continue the task. If complete, respond with Done and a concise summary."
        return AgentLoopResult(
            content=final.content if final else "",
            turns=turns,
            history=list(self.session.history),
            degraded=True,
            degraded_reason="max_turns_reached",
            cost_summary=self._cost_summary(final),
        )

    def _inject_system_prompt(self) -> None:
        if any(
            message.get("role") == "system" and message.get("content") == self.system_prompt
            for message in self.session.history
        ):
            return
        self.session.history.insert(0, {"role": "system", "content": self.system_prompt})

    def _result(self, result: TurnResult, turns: int) -> AgentLoopResult:
        return AgentLoopResult(
            content=result.content,
            turns=turns,
            history=list(self.session.history),
            degraded=result.degraded,
            degraded_reason=result.degraded_reason,
            cost_summary=self._cost_summary(result),
        )

    @staticmethod
    def _cost_summary(result: TurnResult | None) -> dict[str, Any]:
        if result is None or result.response is None:
            return {"available": False}
        usage = result.response.usage
        return {
            "available": usage.available,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_creation_input_tokens": usage.cache_creation_input_tokens,
            "cache_read_input_tokens": usage.cache_read_input_tokens,
        }
