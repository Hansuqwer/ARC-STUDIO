"""Single- and multi-turn provider conversation manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from agent_runtime_cockpit.cli_repl.cancellation import Cancelled, CancellationToken
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.providers import ProviderClient, ProviderMessage, ProviderRequest, ProviderResponse, StreamChunk


EventSink = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True)
class TurnResult:
    """Result for one user-visible turn."""

    content: str
    response: ProviderResponse | None = None
    chunks: list[StreamChunk] = field(default_factory=list)
    degraded: bool = False
    degraded_reason: str | None = None
    partial: bool = False


class TurnManager:
    """Drive a user-visible turn against a provider client."""

    def __init__(
        self,
        provider_client: ProviderClient,
        *,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        event_sink: EventSink | None = None,
    ) -> None:
        self._provider_client = provider_client
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._event_sink = event_sink

    async def run_turn(
        self,
        session: ChatSession,
        prompt: str,
        *,
        cancellation_token: CancellationToken,
        stream: bool = False,
    ) -> TurnResult:
        """Run a single turn.

        Slice 5 intentionally handles one provider response only. Tool loops
        are added in slice 6.
        """
        self._emit("turn.started", {"session_id": session.id, "prompt_chars": len(prompt)})
        session.add_message("user", prompt)
        request = self._request_from_session(session)
        partial = ""
        try:
            cancellation_token.raise_if_cancelled()
            if stream:
                chunks: list[StreamChunk] = []
                async for chunk in self._provider_client.stream(request, cancellation_token=cancellation_token):
                    chunks.append(chunk)
                    self._emit("stream.chunk." + chunk.chunk_type, chunk.model_dump(mode="json"))
                    partial += chunk.delta
                session.add_message("assistant", partial)
                self._emit("turn.completed", {"session_id": session.id, "content_chars": len(partial)})
                return TurnResult(content=partial, chunks=chunks)

            response = await self._provider_client.complete(request, cancellation_token=cancellation_token)
            session.add_message("assistant", response.content)
            self._emit("turn.completed", {"session_id": session.id, "content_chars": len(response.content)})
            return TurnResult(content=response.content, response=response, degraded=response.degraded, degraded_reason=response.degraded_reason)
        except Cancelled as exc:
            if partial:
                session.history.append({
                    "role": "assistant",
                    "content": partial,
                    "partial": "true",
                })
            self._emit("turn.cancelled", {"session_id": session.id, "detail": exc.detail, "partial_chars": len(partial)})
            return TurnResult(content=partial, degraded=True, degraded_reason="cancelled", partial=True)

    def _request_from_session(self, session: ChatSession) -> ProviderRequest:
        messages = [
            ProviderMessage(role=message.get("role", "user"), content=message.get("content", ""))
            for message in session.history
            if message.get("role") in {"system", "user", "assistant", "tool"}
        ]
        return ProviderRequest(
            model=self._model,
            messages=messages,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )

    def _emit(self, name: str, payload: dict[str, Any]) -> None:
        if self._event_sink is not None:
            self._event_sink(name, payload)
