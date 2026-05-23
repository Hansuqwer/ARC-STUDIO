"""Registry of ProviderClient implementations. Populated by Phases 27+."""

from __future__ import annotations

from typing import Callable

from .client import ProviderClient

_FACTORIES: dict[str, Callable[[], ProviderClient]] = {}


def register(name: str, factory: Callable[[], ProviderClient]) -> None:
    if name in _FACTORIES:
        raise ValueError(f"ProviderClient {name!r} already registered")
    _FACTORIES[name] = factory


def get(name: str) -> ProviderClient:
    if name not in _FACTORIES:
        raise KeyError(f"ProviderClient {name!r} not registered; known: {sorted(_FACTORIES)}")
    return _FACTORIES[name]()


def known() -> list[str]:
    return sorted(_FACTORIES)
