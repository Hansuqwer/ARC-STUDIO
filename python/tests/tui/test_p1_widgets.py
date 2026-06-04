"""Tests for P1 UX widgets: ApprovalCard, CapabilityCardBanner, McpDecisionBanner, ActivityTray."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.tui.widgets.approval_card import ApprovalCard, ApprovalRequest
from agent_runtime_cockpit.tui.widgets.capability_banner import CapabilityCardBanner
from agent_runtime_cockpit.tui.widgets.mcp_banner import McpDecisionBanner
from agent_runtime_cockpit.tui.widgets.activity_tray import ActivityTray


# ── ApprovalCard ─────────────────────────────────────────────────────────────


def test_approval_request_fields() -> None:
    req = ApprovalRequest(kind="hitl", prompt_id="p-001", detail="some detail")
    assert req.kind == "hitl"
    assert req.prompt_id == "p-001"
    assert req.detail == "some detail"
    assert req.remediation == ""


def test_approval_card_constructs_without_error() -> None:
    req = ApprovalRequest(kind="capability", prompt_id="cap-001", detail="sig invalid")
    card = ApprovalCard(request=req)
    assert card.request.kind == "capability"


def test_approval_card_no_color_constructs() -> None:
    req = ApprovalRequest(kind="mcp", prompt_id="mcp-001", risk_level="high")
    card = ApprovalCard(request=req, no_color=True)
    assert card.no_color is True


@pytest.mark.parametrize("kind", ["hitl", "capability", "mcp", "paid", "trust", "shell"])
def test_approval_request_all_kinds(kind: str) -> None:
    req = ApprovalRequest(kind=kind, prompt_id=f"{kind}-001")  # type: ignore[arg-type]
    assert req.kind == kind


def test_on_decision_callback_called() -> None:
    received: list[str] = []

    def cb(d: str) -> None:
        received.append(d)

    req = ApprovalRequest(kind="hitl", prompt_id="x", on_decision=cb)
    ApprovalCard(request=req)  # construct to validate; callback tested below
    # Simulate callback directly (without running the full app event loop)
    req.on_decision("allow")
    assert received == ["allow"]


# ── CapabilityCardBanner ──────────────────────────────────────────────────────


@pytest.mark.parametrize("decision", ["allow", "warn", "deny"])
def test_capability_banner_render_contains_decision_info(decision: str) -> None:
    banner = CapabilityCardBanner(
        decision=decision,
        reason=f"capability_card_{decision}_reason",
        card_id="adapter::test",
        no_color=False,
    )
    out = banner.render()
    assert decision in out or decision.upper() in out


def test_capability_banner_no_color_uses_ascii_glyph() -> None:
    banner = CapabilityCardBanner(decision="deny", reason="sig_invalid", no_color=True)
    out = banner.render()
    assert "[DENY]" in out


def test_capability_banner_has_correct_css_class() -> None:
    banner = CapabilityCardBanner(decision="warn", reason="opaque", no_color=False)
    assert "warn" in banner.classes


# ── McpDecisionBanner ────────────────────────────────────────────────────────


@pytest.mark.parametrize("decision,risk", [("allow", "low"), ("warn", "medium"), ("deny", "high")])
def test_mcp_banner_render(decision: str, risk: str) -> None:
    banner = McpDecisionBanner(
        server_id="my-server",
        tool_name="write_file",
        decision=decision,
        risk_score=risk,
        no_color=False,
    )
    out = banner.render()
    assert "my-server" in out
    assert "write_file" in out


def test_mcp_banner_no_color() -> None:
    banner = McpDecisionBanner(
        server_id="s",
        tool_name="t",
        decision="deny",
        risk_score="critical",
        no_color=True,
    )
    out = banner.render()
    assert "[DENY]" in out
    assert "CRITICAL" in out


# ── ActivityTray ──────────────────────────────────────────────────────────────


def test_activity_tray_constructs() -> None:
    tray = ActivityTray(no_color=False)
    assert tray.no_color is False


def test_activity_tray_toggle_adds_visible_class() -> None:
    tray = ActivityTray()
    assert "visible" not in tray.classes
    tray.toggle()
    assert "visible" in tray.classes
    tray.toggle()
    assert "visible" not in tray.classes


def test_activity_tray_push_mcp_adds_entry() -> None:
    tray = ActivityTray(no_color=True)
    tray.push_mcp_decision({"server_id": "s", "tool_name": "t", "decision": "deny", "risk_score": "high"})
    assert len(tray._entries) == 1
    assert tray._entries[0].kind == "mcp_call"


def test_activity_tray_push_capability_adds_entry() -> None:
    tray = ActivityTray()
    tray.push_capability_decision({"decision": "warn", "reason": "opaque", "card_id": "c"})
    assert len(tray._entries) == 1
    assert tray._entries[0].kind == "capability_card"


def test_activity_tray_maxlen_respected() -> None:
    from agent_runtime_cockpit.tui.widgets.activity_tray import N_MAX

    tray = ActivityTray()
    for i in range(N_MAX + 5):
        tray.push_mcp_decision({"server_id": f"s{i}", "tool_name": "t", "decision": "allow", "risk_score": "low"})
    assert len(tray._entries) == N_MAX
