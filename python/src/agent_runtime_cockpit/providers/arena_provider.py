"""ArenaProvider — ProviderClient that routes through a Copilot Arena server.

Implements the ProviderClient Protocol by mapping chat-style ProviderRequest
messages into FIM-style prefix/suffix calls against the open-source Copilot Arena
server (https://github.com/lmarena/copilot-arena).

Each ``complete()`` call triggers a /create_pair battle (2 models, 2 completions).
The winner (first item or server-recommended) is returned as ProviderResponse.content.
The losing candidate and pairId are stashed in metadata for later voting.

Default-off: requires ARC_ARENA_SERVER_URL + ARC_ALLOW_LIVE_ARENA=true.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from ..arena.client import ArenaClient, ArenaClientError, ArenaPairResponse
from ..cli_repl.cancellation import CancellationToken
from .base import (
    CostRates,
    NetworkError,
    ProviderCapability,
    ProviderFeature,
    ProviderRequest,
    ProviderResponse,
    StreamChunk,
    UsageRecord,
)


def _messages_to_prefix_suffix(messages: list[dict[str, Any]]) -> tuple[str, str]:
    """Extract FIM-style prefix/suffix from chat messages.

    Strategy: concatenate all user messages as prefix; suffix is empty.
    System messages are prepended as comments.
    """
    system_parts: list[str] = []
    user_parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            user_parts.append(content)
    prefix = "\n".join(system_parts + user_parts)
    return prefix, ""


class ArenaProvider:
    """ProviderClient implementation backed by a Copilot Arena server.

    Each complete() call sends a /create_pair request (autocomplete battle)
    and returns the winning completion. The losing candidate and pairId
    are stored in response metadata for downstream voting.
    """

    def __init__(self, client: ArenaClient | None = None) -> None:
        self._client = client or ArenaClient.from_env()

    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="arena",
            provider_name="Copilot Arena",
            supported_models=["arena-battle"],
            default_model="arena-battle",
            features=[ProviderFeature.SYSTEM_PROMPT],
            max_context_tokens=8192,
            cost_rates={
                "arena-battle": CostRates(
                    input_per_million=0.0,
                    output_per_million=0.0,
                )
            },
            timeout_seconds=20,
        )

    async def complete(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationToken,
    ) -> ProviderResponse:
        cancellation_token.raise_if_cancelled()

        if self._client is None:
            raise NetworkError("ArenaProvider not configured: set ARC_ARENA_SERVER_URL")

        messages = [msg.model_dump() for msg in request.messages]
        prefix, suffix = _messages_to_prefix_suffix(messages)

        model_tags = request.metadata.get("arena_tags", [])
        if not isinstance(model_tags, list):
            model_tags = []

        try:
            pair: ArenaPairResponse = await self._client.create_pair(
                prefix=prefix,
                suffix=suffix,
                model_tags=model_tags,
                temperature=min(request.temperature, 1.0),
                max_tokens=min(request.max_tokens, 1024),
            )
        except ArenaClientError as exc:
            raise NetworkError(str(exc), retryable=True) from exc

        cancellation_token.raise_if_cancelled()

        if not pair.items:
            return ProviderResponse(
                call_id=request.call_id,
                model="arena-battle",
                content="",
                finish_reason="error",
                usage=UsageRecord(
                    available=False,
                    input_tokens=0,
                    output_tokens=0,
                ),
                degraded=True,
                degraded_reason="arena returned no completions",
            )

        winner = pair.items[0]
        loser = pair.items[1] if len(pair.items) > 1 else None

        metadata: dict[str, Any] = {
            "arena_pair_id": pair.pair_id,
            "arena_winner_model": winner.model,
            "arena_winner_index": winner.pair_index,
            "arena_winner_completion_id": winner.completion_id,
        }
        if loser:
            metadata["arena_loser_model"] = loser.model
            metadata["arena_loser_index"] = loser.pair_index
            metadata["arena_loser_completion_id"] = loser.completion_id
            metadata["arena_loser_content"] = loser.completion[:500]

        return ProviderResponse(
            call_id=request.call_id,
            model=winner.model,
            content=winner.completion,
            finish_reason="stop",
            usage=UsageRecord(
                input_tokens=len(prefix.split()),
                output_tokens=len(winner.completion.split()),
            ),
            metadata=metadata,
        )

    async def stream(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationToken,
    ) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError("ArenaProvider does not support streaming")

    async def cancel(self, call_id: str) -> None:
        pass
