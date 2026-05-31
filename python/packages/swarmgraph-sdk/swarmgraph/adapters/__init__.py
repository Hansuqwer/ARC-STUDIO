"""Provider adapters for the SwarmGraph SDK.

These adapters implement the :class:`swarmgraph.providers.Provider` protocol and
have **no dependency on ARC**. They demonstrate how to plug external execution
backends into the SDK while keeping the offline/deterministic guarantees the
SDK relies on for testing.

Available adapters:

- :class:`EchoProvider` — fully deterministic, offline. Echoes the last user
  message. Safe to use anywhere, no network, no cost.
- :class:`HTTPChatProvider` — an OpenAI-style chat-completions shape. It does
  **not** perform any network I/O on its own: the caller must inject an async
  ``transport`` callable. Without a transport it raises, so it can never make a
  surprise live call in tests.
"""

from __future__ import annotations

from .echo import EchoProvider
from .gated import GatedProvider, PaidCallDeniedError
from .http_chat import HTTPChatProvider, HTTPTransport

__all__ = [
    "EchoProvider",
    "GatedProvider",
    "HTTPChatProvider",
    "HTTPTransport",
    "PaidCallDeniedError",
]
