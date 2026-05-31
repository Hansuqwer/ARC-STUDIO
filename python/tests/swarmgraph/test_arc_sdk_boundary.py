"""Enforce the ARC -> SwarmGraph SDK import boundary.

Source ownership lives in the standalone ``swarmgraph-sdk`` package; ARC
(``agent_runtime_cockpit.swarmgraph``) is a compatibility bridge. New ARC code
should depend on the SDK's *public* API via the top-level package
(``from ..swarmgraph import X``) rather than reaching into private submodules.

This test scans ARC source and tests for deep imports into ``swarmgraph``
submodules and fails if any submodule outside the grandfathered allowlist is
imported. To add a new deep import, either use the public top-level API or, if
genuinely required, extend ``ALLOWED_DEEP_SUBMODULES`` deliberately (which is a
reviewable signal).
"""

from __future__ import annotations

import ast
from pathlib import Path

_PYTHON_ROOT = Path(__file__).resolve().parents[2]
_ARC_SRC = _PYTHON_ROOT / "src" / "agent_runtime_cockpit"
_TESTS_ROOT = _PYTHON_ROOT / "tests"
_BRIDGE_INIT = _ARC_SRC / "swarmgraph" / "__init__.py"
_SCAN_ROOTS = (_ARC_SRC, _TESTS_ROOT)

# Submodules ARC is currently allowed to import directly. Keep this list small
# and intentional; prefer the public top-level API for new code.
ALLOWED_DEEP_SUBMODULES = frozenset(
    {
        "config",
        "consensus",
        "consensus_escrow",
        "models",
        "events",
        "adaptive_consensus",
        "adapters",
        "checkpoint",
        "cli",
        "nodes.approval",
        "nodes.worker",
        "nodes.queen",
        "nodes.consensus",
        "providers",
        "runner",
        "state",
        "decomposition",
        "detectors",
        "fixtures",
        "graph",
        "risk_assessment",
    }
)


_SDK_PKGS = ("agent_runtime_cockpit.swarmgraph", "swarmgraph")


def _containing_package(path: Path) -> str:
    """Return the dotted package that contains a scanned Python file.

    For ``a/b/c.py`` -> ``a.b``. For ``a/b/__init__.py`` -> ``a.b``.
    """
    if path.is_relative_to(_ARC_SRC.parent):
        rel = path.relative_to(_ARC_SRC.parent)
    else:
        rel = path.relative_to(_PYTHON_ROOT)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts[:-1]) if parts else ""


def _resolve(module: str | None, level: int, path: Path) -> str | None:
    """Resolve an import to an absolute module name (handles relative imports).

    Python relative imports are rooted at the containing package and go up
    ``level - 1`` additional packages.
    """
    if level == 0:
        return module
    pkg_parts = _containing_package(path).split(".")
    base = pkg_parts[: len(pkg_parts) - (level - 1)] if level > 1 else pkg_parts
    abs_name = ".".join(base)
    return f"{abs_name}.{module}" if module else abs_name


def _swarmgraph_submodule(module: str | None, level: int, path: Path) -> str | None:
    """Return the SDK ``swarmgraph`` submodule path for an import, or None.

    Matches either the ARC bridge package ``agent_runtime_cockpit.swarmgraph``
    or the standalone SDK package ``swarmgraph``. Sibling packages such as
    ``agent_runtime_cockpit.adapters.swarmgraph`` are NOT the SDK and are
    ignored. Returns "" for a bare top-level import of the SDK package (always
    allowed).
    """
    resolved = _resolve(module, level, path)
    if not resolved:
        return None
    for sdk_pkg in _SDK_PKGS:
        if resolved == sdk_pkg:
            return ""
        prefix = sdk_pkg + "."
        if resolved.startswith(prefix):
            return resolved[len(prefix) :]
    return None


def _iter_arc_python_files():
    for root in _SCAN_ROOTS:
        for path in root.rglob("*.py"):
            # The bridge package itself legitimately wires up swarmgraph internals.
            if path == _BRIDGE_INIT:
                continue
            if path.is_relative_to(_BRIDGE_INIT.parent):
                continue
            yield path


def _deep_imports() -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    for path in _iter_arc_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                sub = _swarmgraph_submodule(node.module, node.level, path)
                if sub is None or sub == "":
                    continue  # not the SDK, or top-level public import
                if sub not in ALLOWED_DEEP_SUBMODULES:
                    violations.append((path, node.lineno, sub))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    sub = _swarmgraph_submodule(alias.name, 0, path)
                    if sub and sub not in ALLOWED_DEEP_SUBMODULES:
                        violations.append((path, node.lineno, sub))
    return violations


def test_arc_has_no_unapproved_deep_swarmgraph_imports() -> None:
    violations = _deep_imports()
    assert not violations, "Unapproved deep swarmgraph imports:\n" + "\n".join(
        f"  {p.relative_to(_PYTHON_ROOT)}:{line} -> swarmgraph.{sub}" for p, line, sub in violations
    )


def test_allowlist_entries_are_actually_used() -> None:
    """Keep the allowlist honest: every entry must be imported somewhere."""
    used: set[str] = set()
    for path in _iter_arc_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                sub = _swarmgraph_submodule(node.module, node.level, path)
                if sub:
                    used.add(sub)
    stale = ALLOWED_DEEP_SUBMODULES - used
    assert not stale, f"Allowlist entries no longer imported (remove them): {sorted(stale)}"
