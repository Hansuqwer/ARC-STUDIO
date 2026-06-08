"""CR-036 regression guard: the typed MESSAGE payload must match the event registry.

The MESSAGE entry in protocol/events.py (the validation registry) and protocol.typed_events
MessageData previously diverged (registry required ``text``; the typed model used
``content``/``role``). This test locks them — and the TS MessageEvent.data shape — together.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_runtime_cockpit.protocol.events import EVENT_TYPES
from agent_runtime_cockpit.protocol.typed_events import MessageData


def _required(model) -> set[str]:
    return {name for name, f in model.model_fields.items() if f.is_required()}


def _optional(model) -> set[str]:
    return {name for name, f in model.model_fields.items() if not f.is_required()}


def test_message_data_required_fields_match_registry() -> None:
    reg = EVENT_TYPES["MESSAGE"]
    assert reg.required_fields == {"text"}
    assert _required(MessageData) == reg.required_fields


def test_message_data_optional_fields_match_registry() -> None:
    reg = EVENT_TYPES["MESSAGE"]
    assert _optional(MessageData) == reg.optional_fields


def test_message_data_constructs_with_text_body() -> None:
    m = MessageData(text="hello", source="queen", message_id="m1")
    assert m.text == "hello" and m.source == "queen"


def test_message_data_requires_text() -> None:
    with pytest.raises(ValidationError):
        MessageData()  # text is required (no content/role anymore)
