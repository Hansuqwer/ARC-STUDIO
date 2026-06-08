"""Daemon orphan-route fate registry (B2P-18 / Batch 7 T28).

The daemon (loopback HTTP) exposes routes that have no direct CLI analog or active IDE consumer.
Each such "orphan" route must carry an explicit, terminal **fate** so doctor/daemon parity is
auditable and no silent orphans accumulate. This codifies the fates previously recorded only in
prose (docs/roadmap.md) into a machine-checkable registry, enforced by test_route_fate_parity.py.
"""

from __future__ import annotations

# Terminal fates an orphan route may carry. `cli-todo` is intentionally NOT terminal — a route
# left as `cli-todo` is an unresolved orphan and fails the parity guard.
VALID_FATES: frozenset[str] = frozenset(
    {"ui-deferred", "daemon-only-deprecated", "cli-added", "removed-410"}
)

# Orphan daemon routes → their resolved fate. Update in lockstep with web/routes.py.
ORPHAN_ROUTE_FATES: dict[str, str] = {
    "GET /api/runs/start": "removed-410",  # GET removed (410 Gone); use POST /api/runs/start
    "/api/runs/{run_id}/links": "cli-added",  # arc runs links
    "/api/context/pack": "cli-added",  # arc context pack
    "/api/telemetry/export/{run_id}": "daemon-only-deprecated",
    "/api/providers/accounts/{account_id}/test": "daemon-only-deprecated",
    "/api/sse/proof": "daemon-only-deprecated",
    "/api/arena/*": "daemon-only-deprecated",
}


def unresolved_orphans() -> list[str]:
    """Return any orphan routes whose fate is not terminal (would block a parity claim)."""
    return [route for route, fate in ORPHAN_ROUTE_FATES.items() if fate not in VALID_FATES]
