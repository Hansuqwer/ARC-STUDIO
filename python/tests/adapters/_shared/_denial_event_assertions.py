"""Assert that a specific typed denial event fires under a context."""

from __future__ import annotations

from typing import Iterable, Literal

DenialKind = Literal[
    "TRUST_DENIED",
    "PAID_CALL_DENIED",
    "SHELL_DENIED",
    "NETWORK_DENIED",
    "PERMISSION_DENIED",
]


class DenialEventAssertions:
    def __init__(self, events: Iterable[object]) -> None:
        self._events = list(events)

    def assert_fired(self, kind: DenialKind) -> None:
        for event in self._events:
            if getattr(event, "kind", None) == kind:
                return
        raise AssertionError(f"expected denial event {kind!r}")

    def assert_not_fired(self, kind: DenialKind) -> None:
        for event in self._events:
            if getattr(event, "kind", None) == kind:
                raise AssertionError(f"unexpected denial event {kind!r} fired")


def assert_denial_event(events: Iterable[object], kind: DenialKind) -> None:
    DenialEventAssertions(events).assert_fired(kind)
