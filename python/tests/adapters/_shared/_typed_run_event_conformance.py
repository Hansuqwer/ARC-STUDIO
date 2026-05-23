"""Assert that an event stream conforms to the Phase 22 TypedRunEvent union."""

from __future__ import annotations

from typing import Iterable, get_args

from agent_runtime_cockpit.protocol.events import TypedRunEvent


class TypedRunEventConformance:
    """Conformance checker for TypedRunEvent streams."""

    def __init__(self) -> None:
        self._known_variants = set(v.__name__ for v in get_args(TypedRunEvent))
        self._violations: list[str] = []

    def check(self, event: object) -> None:
        variant_name = type(event).__name__
        if variant_name not in self._known_variants:
            self._violations.append(f"event {variant_name!r} is not a TypedRunEvent variant")

    @property
    def violations(self) -> list[str]:
        return list(self._violations)


def assert_event_stream_conforms(events: Iterable[object]) -> None:
    checker = TypedRunEventConformance()
    for event in events:
        checker.check(event)
    if checker.violations:
        raise AssertionError(
            "TypedRunEvent conformance failed:\n  - " + "\n  - ".join(checker.violations)
        )
