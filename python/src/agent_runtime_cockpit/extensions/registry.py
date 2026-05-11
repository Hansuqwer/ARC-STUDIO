"""Extension registry."""
from .base import ArcExtension

class ExtensionRegistry:
    def __init__(self) -> None:
        self._extensions: dict[str, ArcExtension] = {}

    def register(self, ext: ArcExtension) -> None:
        self._extensions[ext.extension_id] = ext

    def detect_all(self, workspace) -> list[ArcExtension]:
        return [e for e in self._extensions.values() if e.detect(workspace)]
