"""Settings view — theme toggle, mode selector."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Button, Label, RadioButton, RadioSet

from .side_panel import SidePanel


class SettingsView(SidePanel):
    """Theme, mode, and isolation-backend settings."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    _ISOLATION_CHOICES = ("auto", "subprocess", "docker", "microvm", "none")

    def _current_isolation(self) -> str:
        from ...config.loader import load_config

        try:
            value = load_config(self.workspace).execution.isolation
        except Exception:
            value = "auto"
        return value if value in self._ISOLATION_CHOICES else "auto"

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
        current = self._current_isolation()
        yield Label("Isolation backend")
        with RadioSet(id="isolation-radio"):
            yield RadioButton("auto", id="iso-auto", value=(current == "auto"))
            yield RadioButton("subprocess", id="iso-subprocess", value=(current == "subprocess"))
            yield RadioButton("docker", id="iso-docker", value=(current == "docker"))
            yield RadioButton("microvm", id="iso-microvm", value=(current == "microvm"))
            yield RadioButton("none (disable)", id="iso-none", value=(current == "none"))
        yield Button("Apply", id="apply-btn")

    def _persist_isolation(self) -> str | None:
        """Persist the selected isolation backend to the workspace config."""
        from ...config.loader import set_isolation_backend

        radio = self.query_one("#isolation-radio", RadioSet)
        pressed = radio.pressed_button
        if pressed is None or pressed.id is None:
            return None
        name = pressed.id.removeprefix("iso-")
        set_isolation_backend(name, config_path=self.workspace / ".arc" / "config.yaml")
        return name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-btn":
            self._persist_isolation()
            self.dismiss()
