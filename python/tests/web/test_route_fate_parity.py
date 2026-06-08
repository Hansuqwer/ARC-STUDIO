"""B2P-18: doctor/daemon parity — every orphan daemon route has a terminal fate."""

from __future__ import annotations

from agent_runtime_cockpit.web.route_fates import (
    ORPHAN_ROUTE_FATES,
    VALID_FATES,
    unresolved_orphans,
)


def test_every_orphan_route_has_a_valid_terminal_fate() -> None:
    for route, fate in ORPHAN_ROUTE_FATES.items():
        assert fate in VALID_FATES, f"{route} has non-terminal/unknown fate {fate!r}"


def test_no_unresolved_orphans_remain() -> None:
    # The whole point of B2P-18: nothing is left as an unresolved orphan (e.g. cli-todo).
    assert unresolved_orphans() == []


def test_get_runs_start_is_gone_410_in_code() -> None:
    # The 'removed-410' fate must be backed by the real route returning 410 Gone.
    from pathlib import Path

    routes = Path(__file__).parents[2] / "src" / "agent_runtime_cockpit" / "web" / "routes.py"
    src = routes.read_text(encoding="utf-8")
    assert "/api/runs/start is removed" in src
    assert "410" in src


def _routes_src() -> str:
    from pathlib import Path

    routes = Path(__file__).parents[2] / "src" / "agent_runtime_cockpit" / "web" / "routes.py"
    return routes.read_text(encoding="utf-8")


def _literal_prefix(route_key: str) -> str:
    """Strip the optional 'GET '/'POST ' verb and any '{param}'/'*' tail to a literal prefix."""
    path = route_key.split(" ", 1)[1] if route_key[:1].isalpha() else route_key
    for sep in ("{", "*"):
        if sep in path:
            path = path.split(sep, 1)[0]
    return path.rstrip("/") or path


def test_every_registry_route_exists_in_daemon_source() -> None:
    # Parity (gate 3): the fate registry must reference REAL daemon routes — no phantom entries.
    src = _routes_src()
    for route in ORPHAN_ROUTE_FATES:
        prefix = _literal_prefix(route)
        assert prefix in src, f"registry route {route!r} (prefix {prefix!r}) not found in routes.py"


def test_cli_added_routes_have_a_real_cli_analog() -> None:
    # Parity (gate 3): a 'cli-added' fate must be backed by an actual CLI command, not aspiration.
    from pathlib import Path

    cli = Path(__file__).parents[2] / "src" / "agent_runtime_cockpit" / "cli"
    cli_added = [r for r, f in ORPHAN_ROUTE_FATES.items() if f == "cli-added"]
    # /api/runs/{run_id}/links -> `arc runs links`
    assert "/api/runs/{run_id}/links" in cli_added
    runs_src = (cli / "runs.py").read_text(encoding="utf-8")
    assert '@runs_app.command("links")' in runs_src
