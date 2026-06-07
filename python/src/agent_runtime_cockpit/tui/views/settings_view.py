"""Settings view — theme toggle, mode selector."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Button, Label, RadioButton, RadioSet

from .side_panel import SidePanel


class SettingsView(SidePanel):
    """Theme, mode, and isolation-backend settings."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    _ISOLATION_CHOICES = ("auto", "subprocess", "docker", "microvm", "none")
    _MODE_CHOICES = ("build", "plan", "auto", "review")

    def __init__(
        self,
        workspace: Path | None = None,
        *,
        current_theme: str | None = None,
        current_mode: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(workspace=workspace, **kwargs)
        self._current_theme = current_theme
        self._current_mode = current_mode or "build"

    def _theme_choices(self) -> list[str]:
        from ..theme import theme_names

        try:
            names = theme_names()
            return names or ["dark", "light"]
        except Exception:
            return ["dark", "light"]

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
        themes = self._theme_choices()
        current_theme = self._current_theme if self._current_theme in themes else themes[0]
        with RadioSet(id="theme-radio"):
            for name in themes:
                yield RadioButton(name, id=f"theme-{name}", value=(name == current_theme))
        yield Label("Mode")
        with RadioSet(id="mode-radio"):
            for mode in self._MODE_CHOICES:
                yield RadioButton(mode, id=f"mode-{mode}", value=(mode == self._current_mode))
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

    def _selected(self, radio_id: str, prefix: str) -> str | None:
        radio = self.query_one(radio_id, RadioSet)
        pressed = radio.pressed_button
        if pressed is None or pressed.id is None:
            return None
        return pressed.id.removeprefix(prefix)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-btn":
            self._persist_isolation()
            # Theme + mode are applied live by the screen via the dismiss result
            # (the modal has no access to the theme manager / mode badge).
            self.dismiss(
                {
                    "theme": self._selected("#theme-radio", "theme-"),
                    "mode": self._selected("#mode-radio", "mode-"),
                }
            )
