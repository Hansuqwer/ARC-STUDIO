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
