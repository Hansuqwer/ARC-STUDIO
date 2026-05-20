from __future__ import annotations

import threading
import time
from enum import Enum


class CancellationReason(str, Enum):
    USER = "user"
    TIMEOUT = "timeout"
    BUDGET = "budget"
    GATE_REVOKED = "gate_revoked"
    PARENT = "parent"


class Cancelled(Exception):
    def __init__(self, reason: CancellationReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.detail:
            return f"cancelled: {self.reason.value}: {self.detail}"
        return f"cancelled: {self.reason.value}"


class CancellationToken:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._event = threading.Event()
        self._reason: CancellationReason | None = None
        self._detail = ""
        self._cancelled_at: float | None = None
        self._children: list[CancellationToken] = []

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> CancellationReason | None:
        return self._reason

    @property
    def detail(self) -> str:
        return self._detail

    @property
    def cancelled_at(self) -> float | None:
        return self._cancelled_at

    def cancel(self, reason: CancellationReason, detail: str = "") -> None:
        with self._lock:
            if self._event.is_set():
                return
            self._reason = reason
            self._detail = detail
            self._cancelled_at = time.monotonic()
            self._event.set()
            children = list(self._children)
        child_detail = detail or reason.value
        for child in children:
            child.cancel(CancellationReason.PARENT, child_detail)

    def child(self) -> CancellationToken:
        child = CancellationToken()
        with self._lock:
            self._children.append(child)
            if self._event.is_set():
                reason = self._reason or CancellationReason.PARENT
                detail = self._detail or reason.value
                child.cancel(CancellationReason.PARENT, detail)
        return child

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise Cancelled(self._reason or CancellationReason.USER, self._detail)

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)


class _NeverCancelled(CancellationToken):
    def cancel(self, reason: CancellationReason, detail: str = "") -> None:
        return None

    def child(self) -> CancellationToken:
        return self


_NEVER = _NeverCancelled()


def never_cancelled() -> CancellationToken:
    return _NEVER
