"""Fixture registry for fixture-backed mobile simulation.

Maps capability IDs to fixture executors — functions that accept a step's
``inputs`` dict and return a deterministic ``outputs`` dict.
Used by the simulator when ``use_fixtures=True`` (Phase 4 default).

All executors are pure Python, no native calls, no I/O outside the MockStore.
"""

from __future__ import annotations

from typing import Any, Callable

from .mock_store import MockStore

FixtureExecutor = Callable[[dict[str, Any], MockStore], dict[str, Any]]

_REGISTRY: dict[str, FixtureExecutor] = {}


def register(capability_id: str) -> Callable[[FixtureExecutor], FixtureExecutor]:
    def decorator(fn: FixtureExecutor) -> FixtureExecutor:
        _REGISTRY[capability_id] = fn
        return fn

    return decorator


def get_fixture(capability_id: str) -> FixtureExecutor | None:
    return _REGISTRY.get(capability_id)


def list_fixtures() -> list[str]:
    return sorted(_REGISTRY)


# ── Built-in fixture executors ────────────────────────────────────────────────


@register("app.memory.write.mock")
def _memory_write(inputs: dict[str, Any], store: MockStore) -> dict[str, Any]:
    key = str(inputs.get("key", "last"))
    value = inputs.get("value", inputs.get("text", inputs))
    return store.write(key, value)


@register("app.memory.retrieve.mock")
def _memory_retrieve(inputs: dict[str, Any], store: MockStore) -> dict[str, Any]:
    key = str(inputs.get("key", "last"))
    return store.retrieve(key)


@register("app.local_search.query.mock")
def _local_search(inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    query = str(inputs.get("query", ""))
    return {
        "results": [
            {"id": "r1", "title": f"Result for '{query}'", "score": 0.95},
            {"id": "r2", "title": f"Another result for '{query}'", "score": 0.80},
        ],
        "total": 2,
        "query": query,
    }


@register("app.ui.action_plan.mock")
def _ui_action_plan(inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    return {
        "described": True,
        "steps_described": inputs.get("steps", []),
        "note": "Simulated UI action plan; no native UI execution.",
    }


@register("device.camera.capture.mock")
def _camera_capture(_inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    return {
        "captured": True,
        "uri": "fixture://mock-image.jpg",
        "width": 640,
        "height": 480,
        "mock": True,
    }


@register("device.location.current.mock")
def _location(_inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    return {"latitude": 37.7749, "longitude": -122.4194, "accuracy": 10.0, "mock": True}


@register("device.notifications.schedule.mock")
def _notification(inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    return {
        "scheduled": True,
        "notification_id": "mock-notif-001",
        "title": inputs.get("title", ""),
        "mock": True,
    }


@register("device.calendar.read.mock")
def _calendar_read(_inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    return {
        "events": [{"id": "e1", "title": "Mock Meeting", "date": "2026-01-15T10:00:00Z"}],
        "mock": True,
    }


@register("device.contacts.search.mock")
def _contacts_search(inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    return {
        "contacts": [{"id": "c1", "name": "Mock User", "email": "mock@example.com"}],
        "query": inputs.get("query", ""),
        "mock": True,
    }


@register("device.photos.pick.mock")
def _photos_pick(_inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    return {"uri": "fixture://mock-photo.jpg", "filename": "mock-photo.jpg", "mock": True}


@register("device.files.pick.mock")
def _files_pick(_inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    return {"uri": "fixture://mock-file.txt", "filename": "mock-file.txt", "mock": True}


@register("device.microphone.transcribe.mock")
def _microphone(_inputs: dict[str, Any], _store: MockStore) -> dict[str, Any]:
    return {"transcript": "Mock transcription result.", "confidence": 0.95, "mock": True}


@register("device.calendar.write.mock")
def _calendar_write(inputs: dict[str, Any], store: MockStore) -> dict[str, Any]:
    event_id = "mock-event-001"
    store.write(f"calendar:{event_id}", inputs)
    return {"created": True, "event_id": event_id, "mock": True}
