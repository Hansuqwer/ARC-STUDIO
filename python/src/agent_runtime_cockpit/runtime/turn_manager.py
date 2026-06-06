"""Single- and multi-turn provider conversation manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken, Cancelled
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.providers import (
    ProviderClient,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    StreamChunk,
    UsageRecord,
)
from agent_runtime_cockpit.security.injection_patterns import Severity, scan_structured
from agent_runtime_cockpit.tools import ToolRegistry, wrap_tool_result

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
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._provider_client = provider_client
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._event_sink = event_sink
        self._tool_registry = tool_registry or ToolRegistry()

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
                tool_calls: list[dict[str, Any]] = []
                usage_payload: dict[str, Any] | None = None
                async for chunk in self._provider_client.stream(
                    request, cancellation_token=cancellation_token
                ):
                    chunks.append(chunk)
                    self._emit("stream.chunk." + chunk.chunk_type, chunk.model_dump(mode="json"))
                    partial += chunk.delta
                    if chunk.chunk_type == "tool_use":
                        payload = dict(chunk.payload)
                        if "tool_calls" in payload and isinstance(payload["tool_calls"], list):
                            tool_calls.extend(payload["tool_calls"])
                        else:
                            tool_calls.append(payload)
                    if chunk.chunk_type == "stop" and isinstance(chunk.payload.get("usage"), dict):
                        usage_payload = chunk.payload["usage"]
                response = ProviderResponse(
                    call_id=request.call_id,
                    model=self._model,
                    content=partial,
                    finish_reason="tool_use" if tool_calls else "stop",
                    usage=UsageRecord.model_validate(usage_payload)
                    if usage_payload
                    else UsageRecord(available=False, input_tokens=0, output_tokens=0),
                    tool_calls=tool_calls,
                    degraded=usage_payload is None,
                    degraded_reason=None if usage_payload else "provider usage data unavailable",
                )
                if session.tools_enabled and response.tool_calls:
                    response = await self._run_tool_loop(
                        session, response, cancellation_token=cancellation_token
                    )
                    session.add_message("assistant", response.content)
                    self._emit(
                        "turn.completed",
                        {"session_id": session.id, "content_chars": len(response.content)},
                    )
                    return TurnResult(
                        content=response.content,
                        response=response,
                        chunks=chunks,
                        degraded=response.degraded,
                        degraded_reason=response.degraded_reason,
                    )
                session.add_message("assistant", partial)
                self._emit(
                    "turn.completed", {"session_id": session.id, "content_chars": len(partial)}
                )
                return TurnResult(
                    content=partial,
                    response=response,
                    chunks=chunks,
                    degraded=response.degraded,
                    degraded_reason=response.degraded_reason,
                )

            response = await self._provider_client.complete(
                request, cancellation_token=cancellation_token
            )
            if session.tools_enabled:
                response = await self._run_tool_loop(
                    session, response, cancellation_token=cancellation_token
                )
            session.add_message("assistant", response.content)
            self._emit(
                "turn.completed", {"session_id": session.id, "content_chars": len(response.content)}
            )
            return TurnResult(
                content=response.content,
                response=response,
                degraded=response.degraded,
                degraded_reason=response.degraded_reason,
            )
        except Cancelled as exc:
            if partial:
                session.history.append(
                    {
                        "role": "assistant",
                        "content": partial,
                        "partial": "true",
                    }
                )
            self._emit(
                "turn.cancelled",
                {"session_id": session.id, "detail": exc.detail, "partial_chars": len(partial)},
            )
            return TurnResult(
                content=partial, degraded=True, degraded_reason="cancelled", partial=True
            )

    def _request_from_session(self, session: ChatSession) -> ProviderRequest:
        import os

        from ..providers.base import CacheBreakpoint

        messages = [
            ProviderMessage(role=message.get("role", "user"), content=message.get("content", ""))
            for message in session.history
            if message.get("role") in {"system", "user", "assistant", "tool"}
        ]
        request = ProviderRequest(
            model=self._model,
            messages=messages,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )
        # Populate the system-prompt cache breakpoint when opt-in env flag is set.
        # Anthropic requires ≥1024 tokens to benefit from caching; we proxy that
        # with a ≥2000-character system message so the breakpoint is only added
        # when it's actually cacheable. The flag must be explicitly set — default-off.
        if os.environ.get("ARC_ENABLE_PROMPT_CACHING") == "1":
            system_content = next((m.content for m in messages if m.role == "system"), "")
            if len(system_content) >= 2000:
                request.cache_control = [CacheBreakpoint(position="system", index=0)]

        if session.tools_enabled and self._tool_registry:
            request.tools = [
                {
                    "name": handler.name,
                    "description": handler.description,
                    "input_schema": handler.args_schema.model_json_schema(),
                }
                for handler in self._tool_registry.all_handlers()
                if session.available_tools is None or handler.name in session.available_tools
            ]
            # Add tools breakpoint (breakpoint 1 of 4) when caching is enabled
            # and tools are present. Anthropic caches the tools block separately
            # from the system block; breakpoints are additive.
            if os.environ.get("ARC_ENABLE_PROMPT_CACHING") == "1" and request.tools:
                request.cache_control = [
                    *request.cache_control,
                    CacheBreakpoint(position="tools", index=0),
                ]
        return request

    async def _run_tool_loop(
        self,
        session: ChatSession,
        response: ProviderResponse,
        *,
        cancellation_token: CancellationToken,
    ) -> ProviderResponse:
        iteration = 0
        current = response
        while current.tool_calls:
            if iteration >= session.max_tool_iterations:
                return current.model_copy(
                    update={
                        "degraded": True,
                        "degraded_reason": "max_tool_iterations_reached",
                        "finish_reason": "length",
                    }
                )
            iteration += 1
            for tool_call in current.tool_calls:
                cancellation_token.raise_if_cancelled()
                tool_name = str(tool_call.get("name") or tool_call.get("tool_name") or "")
                args_payload = tool_call.get("args") or tool_call.get("input") or {}
                args_preview = _preview_tool_args(args_payload)
                handler = self._tool_registry.get(tool_name)
                if handler is None:
                    wrapped = (
                        f'<tool_result trust="blocked" tool="{tool_name}" reason="unknown_tool"/>'
                    )
                    self._emit(
                        "tool.result.blocked",
                        {"tool": tool_name, "reason": "unknown_tool", "args_preview": args_preview},
                    )
                elif not self._tool_allowed(session, tool_name):
                    wrapped = f'<tool_result trust="blocked" tool="{tool_name}" reason="tool_not_allowed"/>'
                    self._emit(
                        "tool.result.blocked",
                        {
                            "tool": tool_name,
                            "reason": "tool_not_allowed",
                            "args_preview": args_preview,
                        },
                    )
                else:
                    self._emit(
                        "tool.requested",
                        {"tool": tool_name, "iteration": iteration, "args_preview": args_preview},
                    )
                    args = handler.args_schema.model_validate(args_payload)
                    result = handler.execute(args, cancellation_token)
                    detections = (
                        scan_structured(result.content)
                        if handler.output_trust_level == "untrusted"
                        else []
                    )
                    if any(detection.severity is Severity.BLOCKED for detection in detections):
                        wrapped = f'<tool_result trust="blocked" tool="{tool_name}" reason="injection_detected"/>'
                        self._emit(
                            "tool.result.blocked",
                            {
                                "tool": tool_name,
                                "reason": "injection_detected",
                                "args_preview": args_preview,
                            },
                        )
                    else:
                        wrapped = wrap_tool_result(tool_name, handler.output_trust_level, result)
                        self._emit(
                            "tool.executed",
                            {
                                "tool": tool_name,
                                "iteration": iteration,
                                "trust": handler.output_trust_level,
                                "args_preview": args_preview,
                                **_tool_result_event_payload(result.content),
                            },
                        )
                session.history.append({"role": "tool", "content": wrapped})
            request = self._request_from_session(session)
            current = await self._provider_client.complete(
                request, cancellation_token=cancellation_token
            )
        return current

    @staticmethod
    def _tool_allowed(session: ChatSession, tool_name: str) -> bool:
        return session.available_tools is None or tool_name in session.available_tools

    def _emit(self, name: str, payload: dict[str, Any]) -> None:
        if self._event_sink is not None:
            self._event_sink(name, payload)


def _preview_tool_args(args_payload: Any, max_chars: int = 240) -> str:
    text = str(args_payload)
    if len(text) > max_chars:
        return text[:max_chars] + "...[truncated]"
    return text


def _tool_result_event_payload(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        payload: dict[str, Any] = {}
        summary = content.get("summary")
        if isinstance(summary, str):
            payload["summary"] = summary
        diff = content.get("diff")
        if isinstance(diff, str) and diff:
            payload["diff"] = diff
        for key in ("path", "exit_code", "timed_out", "classification", "allowed"):
            if key in content:
                payload[key] = content[key]
        if not payload:
            payload["summary"] = _preview_tool_args(content)
        return payload
    return {"summary": _preview_tool_args(content)}
