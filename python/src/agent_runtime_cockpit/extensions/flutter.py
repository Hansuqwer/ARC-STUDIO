"""Flutter Extension.

Detects Flutter projects (pubspec.yaml) and provides basic inspection.
Disabled by default — enable via arc.extensions.enableFlutter preference.
"""

from __future__ import annotations

from pathlib import Path

from .base import ArcExtension


class FlutterExtension(ArcExtension):
    @property
    def extension_id(self) -> str:
        return "flutter"

    @property
    def extension_name(self) -> str:
        return "Flutter"

    def detect(self, workspace: Path) -> bool:
        return (workspace / "pubspec.yaml").exists()

    def inspect(self, workspace: Path) -> dict:
        pubspec = workspace / "pubspec.yaml"
        if not pubspec.exists():
            return {"detected": False}
        try:
            import yaml

            data = yaml.safe_load(pubspec.read_text())
            return {
                "detected": True,
                "name": data.get("name"),
                "version": data.get("version"),
                "flutter_sdk": data.get("environment", {}).get("flutter"),
                "dependencies": list((data.get("dependencies") or {}).keys()),
            }
        except Exception as e:
            return {"detected": True, "error": str(e)}
