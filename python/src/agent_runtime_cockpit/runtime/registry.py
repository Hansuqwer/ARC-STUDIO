"""Minimal runtime registry for CLI runtime-mode introspection."""

from __future__ import annotations

from .capability import RuntimeCapability
from .mode import RuntimeMode


class RuntimeRegistry:
    def __init__(self) -> None:
        self._capabilities = {
            RuntimeMode.FAKE: RuntimeCapability(mode=RuntimeMode.FAKE),
            RuntimeMode.GATED_LOCAL: RuntimeCapability(mode=RuntimeMode.GATED_LOCAL),
            RuntimeMode.PROVIDER_BACKED: RuntimeCapability(
                mode=RuntimeMode.PROVIDER_BACKED,
                allow_paid_calls=True,
                cost_source_default="measured",
            ),
        }

    def get(self, mode: RuntimeMode | str) -> RuntimeCapability:
        return self._capabilities[RuntimeMode.from_legacy(mode)]

    def all(self) -> list[RuntimeCapability]:
        return list(self._capabilities.values())


def default_runtime_registry() -> RuntimeRegistry:
    return RuntimeRegistry()
