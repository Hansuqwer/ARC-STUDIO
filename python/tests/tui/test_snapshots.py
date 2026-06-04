"""Textual snapshot tests — baseline visual regression guards.

Run with --snapshot-update to regenerate baselines:
    uv run pytest tests/tui/test_snapshots.py --snapshot-update -q

Notes on determinism:
- test_snapshot_approval_card_capability_gate: fully deterministic (passes).
- test_snapshot_home_*: marked xfail(strict=False) because pytest-textual-snapshot
  embeds a content-hash in SVG CSS class names (e.g. `terminal-4211798024-matrix`).
  That hash changes on every render even with identical visible content.
  DataStore.seed pins the session ID correctly, but cannot pin the SVG class hash.
  Fix requires either normalizing the SVG before comparison (upstream feature request)
  or waiting for pytest-textual-snapshot to offer a stable-hash mode.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ARC_REDUCED_MOTION", raising=False)


@pytest.mark.xfail(
    strict=False,
    reason="SVG class-hash in pytest-textual-snapshot changes on every render; "
    "session ID is now deterministic via DataStore(seed=0) — unblocked once "
    "snapshot library supports stable class names",
)
def test_snapshot_home_dark(snap_compare) -> None:
    """ArcApp home screen — dark theme, 120×40."""
    from agent_runtime_cockpit.tui.app import ArcApp
    from agent_runtime_cockpit.tui.data import DataStore

    assert snap_compare(ArcApp(data=DataStore(seed=0)), terminal_size=(120, 40))


@pytest.mark.xfail(
    strict=False,
    reason="SVG class-hash nondeterminism (same as test_snapshot_home_dark)",
)
def test_snapshot_home_no_color(snap_compare, monkeypatch: pytest.MonkeyPatch) -> None:
    """ArcApp home screen — NO_COLOR=1, 80×24."""
    monkeypatch.setenv("NO_COLOR", "1")
    from agent_runtime_cockpit.tui.app import ArcApp
    from agent_runtime_cockpit.tui.data import DataStore

    assert snap_compare(ArcApp(data=DataStore(seed=1)), terminal_size=(80, 24))


def test_snapshot_approval_card_capability_gate(snap_compare) -> None:
    """ApprovalCard modal — deterministic (no session state, stable SVG hash)."""
    from textual.app import App

    from agent_runtime_cockpit.tui.widgets.approval_card import ApprovalCard, ApprovalRequest

    class _TestApp(App):
        async def on_mount(self) -> None:
            req = ApprovalRequest(
                kind="capability",
                prompt_id="adapter::swarmgraph",
                detail="Signature invalid: HMAC mismatch",
                risk_level="high",
                remediation="Re-sign the card with arc capabilities sign",
            )
            await self.push_screen(ApprovalCard(request=req))

    assert snap_compare(_TestApp(), terminal_size=(120, 40))
