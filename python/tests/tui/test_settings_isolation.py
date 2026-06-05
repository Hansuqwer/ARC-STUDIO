"""Tests for the isolation backend selector in the TUI SettingsView (task 7)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from textual.app import App
from textual.widgets import RadioButton

from agent_runtime_cockpit.config.loader import set_isolation_backend
from agent_runtime_cockpit.tui.views.settings_view import SettingsView


def _cfg(ws: Path) -> Path:
    return ws / ".arc" / "config.yaml"


def _iso(ws: Path) -> str:
    return yaml.safe_load(_cfg(ws).read_text())["execution"]["isolation"]


class _Harness(App):
    def __init__(self, view: SettingsView) -> None:
        super().__init__()
        self._view = view

    async def on_mount(self) -> None:
        await self.push_screen(self._view)


@pytest.mark.asyncio
async def test_settings_preselects_and_roundtrips_configured_isolation(tmp_path: Path) -> None:
    set_isolation_backend("microvm", config_path=_cfg(tmp_path))
    view = SettingsView(workspace=tmp_path)
    app = _Harness(view)
    async with app.run_test(size=(80, 40)) as pilot:
        await pilot.pause()
        # The configured backend is pre-selected in the radio set.
        assert view.query_one("#iso-microvm", RadioButton).value is True
        # Applying without changing selection round-trips the configured value.
        assert view._persist_isolation() == "microvm"
    assert _iso(tmp_path) == "microvm"


@pytest.mark.asyncio
async def test_settings_switch_to_none_disables(tmp_path: Path) -> None:
    set_isolation_backend("subprocess", config_path=_cfg(tmp_path))
    view = SettingsView(workspace=tmp_path)
    app = _Harness(view)
    async with app.run_test(size=(80, 40)) as pilot:
        await pilot.pause()
        view.query_one("#iso-none", RadioButton).value = True
        await pilot.pause()
        assert view._persist_isolation() == "none"
    assert _iso(tmp_path) == "none"
