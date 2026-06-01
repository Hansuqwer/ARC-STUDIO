"""Async HTTP client for the open-source Copilot Arena server.

Wraps the FastAPI endpoints from https://github.com/lmarena/copilot-arena/server:
- POST /create_pair          — autocomplete battle (2 completions)
- POST /create_edit_pair     — inline-edit battle (2 responses)
- PUT  /add_completion_outcome — record a vote

Default-off: no network calls unless ARC_ARENA_SERVER_URL is set and
ARC_ALLOW_LIVE_ARENA=true.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Any

import aiohttp


@dataclass(frozen=True)
class ArenaCompletionItem:
    """One candidate from a /create_pair response."""

    completion_id: str
    model: str
    completion: str
    pair_index: int
    pair_completion_id: str
    latency: float = 0.0


@dataclass(frozen=True)
class ArenaPairResponse:
    """Parsed response from /create_pair."""

    pair_id: str
    items: list[ArenaCompletionItem] = field(default_factory=list)


@dataclass(frozen=True)
class ArenaEditItem:
    """One candidate from a /create_edit_pair response."""

    response_id: str
    model: str
    response: str
    pair_index: int
    pair_response_id: str
    latency: float = 0.0


@dataclass(frozen=True)
class ArenaEditResponse:
    """Parsed response from /create_edit_pair."""

    pair_id: str
    items: list[ArenaEditItem] = field(default_factory=list)


class ArenaClientError(Exception):
    """Raised when the arena server returns an error or is unreachable."""


class ArenaClient:
    """Async HTTP client for a Copilot Arena server instance.

    Args:
        base_url: Server base URL (e.g. "http://localhost:8000").
        user_id: Identifier sent with every request.
        privacy: One of "Private", "Debug", "Research".
        timeout: Per-request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        *,
        user_id: str = "arc-user",
        privacy: str = "Private",
        timeout: float = 20.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_id = user_id
        self._privacy = privacy
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @staticmethod
    def from_env() -> ArenaClient | None:
        """Build an ArenaClient from environment variables, or None if not configured."""
        url = os.environ.get("ARC_ARENA_SERVER_URL", "").strip()
        if not url:
            return None
        return ArenaClient(
            base_url=url,
            user_id=os.environ.get("ARC_ARENA_USER_ID", "arc-user"),
            privacy=os.environ.get("ARC_ARENA_PRIVACY", "Private"),
        )

    async def create_pair(
        self,
        prefix: str,
        suffix: str = "",
        *,
        model_tags: list[str] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> ArenaPairResponse:
        """POST /create_pair — autocomplete battle returning 2 completions."""
        payload: dict[str, Any] = {
            "pairId": str(uuid.uuid4()),
            "prefix": prefix,
            "suffix": suffix,
            "userId": self._user_id,
            "privacy": self._privacy,
            "modelTags": model_tags or [],
            "temperature": temperature,
            "maxTokens": max_tokens,
        }
        data = await self._post("/create_pair", payload)
        items = [
            ArenaCompletionItem(
                completion_id=item["completionId"],
                model=item["model"],
                completion=item["completion"],
                pair_index=item["pairIndex"],
                pair_completion_id=item["pairCompletionId"],
                latency=item.get("latency", 0.0),
            )
            for item in data.get("completionItems", [])
        ]
        return ArenaPairResponse(pair_id=data["pairId"], items=items)

    async def create_edit_pair(
        self,
        prefix: str,
        code_to_edit: str,
        user_input: str,
        language: str,
        suffix: str = "",
        *,
        model_tags: list[str] | None = None,
    ) -> ArenaEditResponse:
        """POST /create_edit_pair — inline-edit battle returning 2 responses."""
        payload: dict[str, Any] = {
            "pairId": str(uuid.uuid4()),
            "prefix": prefix,
            "codeToEdit": code_to_edit,
            "userInput": user_input,
            "language": language,
            "suffix": suffix,
            "userId": self._user_id,
            "privacy": self._privacy,
            "modelTags": model_tags or [],
        }
        data = await self._post("/create_edit_pair", payload)
        items = [
            ArenaEditItem(
                response_id=item["responseId"],
                model=item["model"],
                response=item["response"],
                pair_index=item["pairIndex"],
                pair_response_id=item["pairResponseId"],
                latency=item.get("latency", 0.0),
            )
            for item in data.get("responseItems", [])
        ]
        return ArenaEditResponse(pair_id=data["pairId"], items=items)

    async def add_completion_outcome(
        self,
        pair_id: str,
        accepted_index: int,
        completion_items: list[dict[str, Any]],
        *,
        version: str = "arc-0.1",
    ) -> None:
        """PUT /add_completion_outcome — record a vote (which completion was accepted)."""
        payload: dict[str, Any] = {
            "pairId": pair_id,
            "userId": self._user_id,
            "acceptedIndex": accepted_index,
            "version": version,
            "completionItems": completion_items,
        }
        await self._put("/add_completion_outcome", payload)

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        raise ArenaClientError(
                            f"Arena server {path} returned {resp.status}: {body[:500]}"
                        )
                    return await resp.json()
        except aiohttp.ClientError as exc:
            raise ArenaClientError(f"Arena server unreachable at {url}: {exc}") from exc

    async def _put(self, path: str, payload: dict[str, Any]) -> None:
        url = f"{self._base_url}{path}"
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.put(url, json=payload) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        raise ArenaClientError(
                            f"Arena server {path} returned {resp.status}: {body[:500]}"
                        )
        except aiohttp.ClientError as exc:
            raise ArenaClientError(f"Arena server unreachable at {url}: {exc}") from exc
