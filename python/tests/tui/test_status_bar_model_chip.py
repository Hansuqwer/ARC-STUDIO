"""Tests for status bar model capability chip (v0.6 Task 4).

The chip logic is in get_capabilities() (capability_gates.py) which the
status bar calls. Tests verify the data layer that feeds the chip display.
Status bar integration is smoke-tested in test_status_bar_context_meter.py.
"""

from __future__ import annotations


from agent_runtime_cockpit.tui.widgets.capability_gates import get_capabilities


def _chip_tags(model_id: str, vendor: str = "") -> list[str]:
    """Simulate what the status bar chip renders."""
    caps = get_capabilities(model_id, vendor=vendor or None)
    return [
        tag for tag, enabled in caps.items() if enabled and tag in ("vision", "tools", "reasoning")
    ]


def test_chip_shows_vision_for_kimi_k2_6():
    assert "vision" in _chip_tags("kimi-k2.6", vendor="kimi")


def test_chip_shows_tools_for_deepseek_v4_pro():
    assert "tools" in _chip_tags("deepseek-v4-pro", vendor="deepseek")


def test_chip_shows_reasoning_for_qwen():
    assert "reasoning" in _chip_tags("qwen3.7-plus", vendor="qwen")


def test_chip_no_tags_for_unknown_model():
    tags = _chip_tags("totally-unknown-xyz")
    assert tags == []


def test_chip_updates_on_vendor_model_change():
    """Switching provider/model changes chip content."""
    tags_kimi = set(_chip_tags("kimi-k2.6", vendor="kimi"))
    tags_deepseek = set(_chip_tags("deepseek-v4-pro", vendor="deepseek"))
    # They're different models — chip content differs (vision vs tools focus)
    # kimi-k2.6 has vision; deepseek-v4-pro does not
    assert "vision" in tags_kimi
    assert "vision" not in tags_deepseek  # deepseek-v4-pro is text-only


def test_status_bar_import_doesnt_break():
    """Importing status_bar with capability_gates wired in doesn't raise."""
    from agent_runtime_cockpit.tui.widgets import status_bar  # noqa: F401
