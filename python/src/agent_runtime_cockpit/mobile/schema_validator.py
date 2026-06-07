"""JSON Schema validation for ARC Mobile Runtime protocol objects.

Loads schemas from runtimes/mobile/spec/ (relative to repo root) or from the
bundled spec directory next to this file. Falls back to no-op if jsonschema
is not installed (validation is optional in lenient mode).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SPEC_DIR: Path | None = None


def _find_spec_dir() -> Path:
    """Locate runtimes/mobile/spec/ by walking up from this file."""
    global _SPEC_DIR
    if _SPEC_DIR is not None:
        return _SPEC_DIR
    here = Path(__file__).resolve()
    for ancestor in [here, *here.parents]:
        candidate = ancestor / "runtimes" / "mobile" / "spec"
        if candidate.is_dir():
            _SPEC_DIR = candidate
            return _SPEC_DIR
    raise FileNotFoundError("Cannot locate runtimes/mobile/spec/ directory")


_SCHEMA_FILES = {
    "manifest": "mobile-capability-manifest.schema.json",
    "action_plan": "mobile-action-plan.schema.json",
    "simulation_report": "mobile-simulation-report.schema.json",
    "event": "mobile-events.schema.json",
    "trace": "mobile-trace.schema.json",
    "policy_decision": "mobile-policy-decision.schema.json",
}


def load_schema(kind: str) -> dict[str, Any]:
    """Load a JSON Schema by kind name."""
    filename = _SCHEMA_FILES.get(kind)
    if not filename:
        raise ValueError(f"Unknown schema kind {kind!r}. Valid: {sorted(_SCHEMA_FILES)}")
    spec_dir = _find_spec_dir()
    schema_path = spec_dir / filename
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_against_schema(data: Any, kind: str) -> list[str]:
    """Validate data against the named schema. Returns list of error messages (empty = valid)."""
    try:
        import jsonschema  # type: ignore[import]
    except ImportError:
        return []  # graceful degradation if not installed

    schema = load_schema(kind)
    validator = jsonschema.Draft202012Validator(schema)
    return [e.message for e in validator.iter_errors(data)]


def list_schema_kinds() -> list[str]:
    return sorted(_SCHEMA_FILES)
