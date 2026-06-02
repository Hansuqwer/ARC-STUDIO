"""Settings view — theme toggle, mode selector."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Button, Label, RadioButton, RadioSet

from .side_panel import SidePanel


class SettingsView(SidePanel):
    """Theme and mode settings."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Label("Settings")
        yield Label("Theme")
        with RadioSet(id="theme-radio"):
            yield RadioButton("Dark", id="dark", value=True)
            yield RadioButton("Light", id="light")
        yield Label("Mode")
        with RadioSet(id="mode-radio"):
            yield RadioButton("build", id="build", value=True)
            yield RadioButton("plan", id="plan")
            yield RadioButton("auto", id="auto")
        yield Button("Apply", id="apply-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-btn":
            self.dismiss()
