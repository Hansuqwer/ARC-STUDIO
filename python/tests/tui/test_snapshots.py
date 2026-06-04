"""Textual snapshot tests — baseline visual regression guards.

Run with --snapshot-update to regenerate baselines:
    uv run pytest tests/tui/test_snapshots.py --snapshot-update -q

The ApprovalCard test is fully deterministic (no session ID / timestamp).
The ArcApp home tests are marked xfail until session-ID seeding is wired
into ArcApp (tracked: fix ArcApp to accept a seed for snapshot stability).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ARC_REDUCED_MOTION", raising=False)


@pytest.mark.xfail(
    strict=False,
    reason="ArcApp home embeds a random session ID; stable until ArcApp supports a seed",
)
def test_snapshot_home_dark(snap_compare) -> None:
    """ArcApp home screen — dark theme, 120×40."""
    from agent_runtime_cockpit.tui.app import ArcApp

    assert snap_compare(ArcApp(), terminal_size=(120, 40))


@pytest.mark.xfail(
    strict=False,
    reason="ArcApp home embeds a random session ID; NO_COLOR path stable once seed is wired",
)
def test_snapshot_home_no_color(snap_compare, monkeypatch: pytest.MonkeyPatch) -> None:
    """ArcApp home screen — NO_COLOR=1, 80×24."""
    monkeypatch.setenv("NO_COLOR", "1")
    from agent_runtime_cockpit.tui.app import ArcApp

    assert snap_compare(ArcApp(), terminal_size=(80, 24))


def test_snapshot_approval_card_capability_gate(snap_compare) -> None:
    """ApprovalCard modal — fully deterministic, no session state."""
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
