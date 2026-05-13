"""
A2UI Extension (Experimental)

Detects and validates A2UI declarative UI payloads.
Source: https://github.com/google/A2UI
Status: EXPERIMENTAL — disabled by default.
"""
from __future__ import annotations
from pathlib import Path
from .base import ArcExtension

class A2UIExtension(ArcExtension):
    """EXPERIMENTAL: A2UI declarative UI payload support."""

    @property
    def extension_id(self) -> str: return "a2ui"
    @property
    def extension_name(self) -> str: return "A2UI (Experimental)"

    def detect(self, workspace: Path) -> bool:
        # Look for .a2ui files or a2ui.json
        return any([
            list(workspace.glob("*.a2ui")),
            (workspace / "a2ui.json").exists(),
            (workspace / "a2ui.yaml").exists(),
        ])

    def inspect(self, workspace: Path) -> dict:
        return {
            "detected": self.detect(workspace),
            "status": "experimental",
            "can_render": False,
            "reason": "A2UI v0.9 is experimental; renderer and validator are not implemented.",
            "spec": "https://github.com/google/A2UI/tree/main/specification/v0_9/docs",
        }

    def validate_payload(self, payload: dict) -> dict:
        """Stub validator — always returns experimental warning."""
        return {
            "valid": None,
            "status": "experimental",
            "warning": "A2UI validator is a stub. Real validation not yet implemented.",
            "payload_keys": list(payload.keys()),
        }
