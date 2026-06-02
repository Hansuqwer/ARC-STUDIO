"""Generic side panel container used by domain views."""

from __future__ import annotations

from pathlib import Path

from textual.binding import Binding
from textual.screen import ModalScreen


class SidePanel(ModalScreen):
    """Base class for domain side-panel screens."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, workspace: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.workspace = workspace or Path.cwd()
