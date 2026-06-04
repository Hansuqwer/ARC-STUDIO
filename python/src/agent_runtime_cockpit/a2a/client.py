"""Loopback-only outbound A2A client.

Constraints:
- Only 127.0.0.1 URLs accepted (no other hosts)
- Unsigned cards refused
- Per-card approval required
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from .models import AgentCard

_LOOPBACK_RE = re.compile(r"^http://127\.0\.0\.1:\d+(/|$)")

APPROVED_CARDS_FILE = "approved.json"


class A2AClientError(Exception):
    """Base error for A2A client."""


class NonLoopbackError(A2AClientError):
    """URL is not loopback."""


class UnsignedCardError(A2AClientError):
    """Card has no signature."""


class UnapprovedCardError(A2AClientError):
    """Card not in approved list."""


def _validate_url(url: str) -> None:
    if not _LOOPBACK_RE.match(url):
        raise NonLoopbackError(f"Non-loopback URL refused: {url}")


def _load_approved(arc_dir: Path) -> dict[str, Any]:
    path = arc_dir / "a2a" / APPROVED_CARDS_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _save_approved(arc_dir: Path, data: dict[str, Any]) -> None:
    path = arc_dir / "a2a" / APPROVED_CARDS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def is_card_approved(card: AgentCard, arc_dir: Optional[Path] = None) -> bool:
    """Check if a card is in the approved list."""
    base = arc_dir or Path.home() / ".arc"
    approved = _load_approved(base)
    return card.name in approved


def approve_card(card: AgentCard, arc_dir: Optional[Path] = None) -> None:
    """Add card to the approved list."""
    base = arc_dir or Path.home() / ".arc"
    approved = _load_approved(base)
    approved[card.name] = {"version": card.version, "url": card.url}
    _save_approved(base, approved)


def revoke_card(card_name: str, arc_dir: Optional[Path] = None) -> bool:
    """Remove card from approved list. Returns True if was present."""
    base = arc_dir or Path.home() / ".arc"
    approved = _load_approved(base)
    if card_name in approved:
        del approved[card_name]
        _save_approved(base, approved)
        return True
    return False


def _check_card(card: AgentCard, arc_dir: Path) -> None:
    """Validate card has signature and is approved."""
    if not card.signature:
        raise UnsignedCardError(f"Card '{card.name}' has no signature")
    if not is_card_approved(card, arc_dir):
        raise UnapprovedCardError(f"Card '{card.name}' is not approved")


def invoke_sync(
    card: AgentCard,
    *,
    payload: dict[str, Any],
    arc_dir: Optional[Path] = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Synchronous A2A invoke — loopback only, signed+approved cards only."""
    import httpx

    base = arc_dir or Path.home() / ".arc"
    _validate_url(card.url)
    _check_card(card, base)

    resp = httpx.post(card.url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


async def invoke_async(
    card: AgentCard,
    *,
    payload: dict[str, Any],
    arc_dir: Optional[Path] = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Async A2A invoke — loopback only, signed+approved cards only."""
    import httpx

    base = arc_dir or Path.home() / ".arc"
    _validate_url(card.url)
    _check_card(card, base)

    async with httpx.AsyncClient() as client:
        resp = await client.post(card.url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
