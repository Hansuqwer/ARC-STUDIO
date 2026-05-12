"""Resolve `package.module:variable` entrypoints inside a workspace safely."""
from __future__ import annotations

import importlib
import pathlib
import sys
from typing import Any


def resolve_python_entrypoint(workspace: pathlib.Path, entrypoint: str) -> Any:
    if ":" not in entrypoint:
        raise ValueError(f"entrypoint must be 'module:object', got {entrypoint!r}")
    module_name, attr = entrypoint.split(":", 1)
    src = str(workspace.resolve())
    if src not in sys.path:
        sys.path.insert(0, src)
    module = importlib.import_module(module_name)
    if not hasattr(module, attr):
        raise AttributeError(f"{module_name!r} has no attribute {attr!r}")
    return getattr(module, attr)
