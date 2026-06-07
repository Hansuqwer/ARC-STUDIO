"""Workspace utilities for file scanning and entrypoint resolution."""

# Re-export from workspace.py module for backward compatibility
from pathlib import Path

from .entrypoint import resolve_python_entrypoint

# Import iter_workspace_files from the workspace.py module
parent_dir = Path(__file__).parent.parent
workspace_module_path = parent_dir / "workspace.py"
if workspace_module_path.exists():
    import importlib.util

    spec = importlib.util.spec_from_file_location("_workspace_compat", workspace_module_path)
    if spec and spec.loader:
        _workspace_compat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_workspace_compat)
        iter_workspace_files = _workspace_compat.iter_workspace_files
        IGNORED_DIRS = _workspace_compat.IGNORED_DIRS
        is_sensitive_file = _workspace_compat.is_sensitive_file
        SENSITIVE_FILENAMES = _workspace_compat.SENSITIVE_FILENAMES
        SENSITIVE_SUFFIXES = _workspace_compat.SENSITIVE_SUFFIXES

__all__ = [
    "resolve_python_entrypoint",
    "iter_workspace_files",
    "IGNORED_DIRS",
    "is_sensitive_file",
    "SENSITIVE_FILENAMES",
    "SENSITIVE_SUFFIXES",
]
