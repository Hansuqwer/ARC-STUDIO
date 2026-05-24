"""Cross-language fixture loader for Python tests.

Loads JSON fixtures from protocol/fixtures/ and validates them against
Pydantic models to ensure Python ↔ TypeScript schema consistency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Path to fixtures directory relative to this file
FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "protocol" / "fixtures"


def load_fixture(category: str, name: str) -> dict[str, Any]:
    """Load a JSON fixture by category and name.

    Args:
        category: Fixture category (e.g., 'arc-envelope', 'run-event')
        name: Fixture name without .json extension (e.g., 'success', 'run-completed')

    Returns:
        Parsed JSON as dictionary

    Raises:
        FileNotFoundError: If fixture file doesn't exist
        json.JSONDecodeError: If fixture is not valid JSON

    Example:
        >>> envelope = load_fixture("arc-envelope", "success")
        >>> assert envelope["ok"] is True

    """
    fixture_path = FIXTURES_DIR / category / f"{name}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture not found: {category}/{name}.json\nExpected at: {fixture_path}"
        )
    return json.loads(fixture_path.read_text())


def load_and_validate(category: str, name: str, model: type[T]) -> T:
    """Load a fixture and validate it against a Pydantic model.

    Args:
        category: Fixture category
        name: Fixture name without .json extension
        model: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        FileNotFoundError: If fixture file doesn't exist
        pydantic.ValidationError: If fixture doesn't match model schema

    Example:
        >>> from agent_runtime_cockpit.protocol.event_envelope import ArcEnvelope
        >>> envelope = load_and_validate("arc-envelope", "success", ArcEnvelope)
        >>> assert envelope.ok is True

    """
    data = load_fixture(category, name)
    return model.model_validate(data)


def validate_round_trip(category: str, name: str, model: type[T]) -> tuple[dict, dict, T]:
    """Load fixture, validate, serialize back to JSON, and compare.

    This tests that:
    1. Fixture is valid according to Pydantic model
    2. Model can serialize back to JSON
    3. Serialized JSON matches original fixture (schema stability)

    Args:
        category: Fixture category
        name: Fixture name without .json extension
        model: Pydantic model class

    Returns:
        Tuple of (original_json, serialized_json, model_instance)

    Example:
        >>> from agent_runtime_cockpit.protocol.schemas import RunEvent
        >>> original, serialized, instance = validate_round_trip("run-event", "run-completed", RunEvent)
        >>> assert original["type"] == serialized["type"]

    """
    original = load_fixture(category, name)
    instance = model.model_validate(original)
    serialized = instance.model_dump(mode="json", by_alias=True)
    return original, serialized, instance


def list_fixtures(category: str) -> list[str]:
    """List all fixture names in a category.

    Args:
        category: Fixture category

    Returns:
        List of fixture names (without .json extension)

    Example:
        >>> fixtures = list_fixtures("arc-envelope")
        >>> assert "success" in fixtures

    """
    category_dir = FIXTURES_DIR / category
    if not category_dir.exists():
        return []
    return [f.stem for f in category_dir.glob("*.json")]


def list_categories() -> list[str]:
    """List all fixture categories.

    Returns:
        List of category names

    Example:
        >>> categories = list_categories()
        >>> assert "arc-envelope" in categories

    """
    if not FIXTURES_DIR.exists():
        return []
    return [d.name for d in FIXTURES_DIR.iterdir() if d.is_dir()]
