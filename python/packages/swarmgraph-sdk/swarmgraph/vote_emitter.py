"""Arena vote emitter — POSTs votes to the arena server after consensus.

This module collects ArenaVoteEvents from a SwarmGraph run and sends them
to the arena server's /add_completion_outcome endpoint.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .events import ArenaVoteEvent

logger = logging.getLogger(__name__)


async def emit_arena_votes(
    events: list[ArenaVoteEvent],
    arena_client: Any,
) -> None:
    """Emit arena votes to the server.

    Args:
        events: List of ArenaVoteEvents from consensus.
        arena_client: ArenaClient instance (from agent_runtime_cockpit.arena.client).

    This function is fire-and-forget: errors are logged but do not block consensus.
    """
    if not events:
        return

    for event in events:
        try:
            pair_id = event.data["pair_id"]
            accepted_index = event.data["accepted_index"]
            winner_model = event.data["winner_model"]
            loser_model = event.data["loser_model"]

            # Build completion_items payload for the arena server
            completion_items = [
                {
                    "completionId": f"{pair_id}-0",
                    "model": winner_model if accepted_index == 0 else loser_model,
                    "completion": "",  # Content not needed for vote recording
                },
                {
                    "completionId": f"{pair_id}-1",
                    "model": loser_model if accepted_index == 0 else winner_model,
                    "completion": "",
                },
            ]

            await arena_client.add_completion_outcome(
                pair_id=pair_id,
                accepted_index=accepted_index,
                completion_items=completion_items,
            )
            logger.info(f"Arena vote emitted: pair_id={pair_id}, accepted={accepted_index}")
        except Exception as exc:
            logger.warning(f"Failed to emit arena vote for {event.data.get('pair_id')}: {exc}")


def emit_arena_votes_sync(
    events: list[ArenaVoteEvent],
    arena_client: Any,
) -> None:
    """Synchronous wrapper for emit_arena_votes.

    Runs the async function in a new event loop. Suitable for calling from
    synchronous SwarmGraph runner code.
    """
    if not events:
        return

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(emit_arena_votes(events, arena_client))
        finally:
            loop.close()
    except Exception as exc:
        logger.warning(f"Failed to emit arena votes (sync): {exc}")
