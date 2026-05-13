"""
ARC Adapter Registry

Discovers adapters, runs detection against a workspace, and routes calls
to the correct adapter.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..protocol.schemas import ConfidenceLevel, RuntimeInfo
from .base import RuntimeAdapter

log = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Central registry for all ARC runtime adapters.

    Usage:
        registry = AdapterRegistry()
        registry.register(SwarmGraphAdapter())
        registry.register(LangGraphAdapter())
        runtimes = registry.detect_all(workspace)
    """

    def __init__(self) -> None:
        self._adapters: dict[str, RuntimeAdapter] = {}

    def register(self, adapter: RuntimeAdapter) -> None:
        """Register a runtime adapter."""
        log.debug("Registering adapter: %s", adapter.adapter_id)
        self._adapters[adapter.adapter_id] = adapter

    def get(self, adapter_id: str) -> Optional[RuntimeAdapter]:
        """Get adapter by ID."""
        return self._adapters.get(adapter_id)

    def all(self) -> list[RuntimeAdapter]:
        """Return all registered adapters."""
        return list(self._adapters.values())

    def detect_all(self, workspace: Path) -> list[RuntimeInfo]:
        """
        Run all adapters' detect() against the workspace.
        Returns only adapters that were actually detected.
        """
        results: list[RuntimeInfo] = []

        for adapter in self._adapters.values():
            try:
                detected, confidence, evidence = adapter.detect(workspace)
                if not detected:
                    log.debug("Adapter %s: not detected in %s", adapter.adapter_id, workspace)
                    continue

                if confidence >= 0.7:
                    conf_level = ConfidenceLevel.HIGH
                elif confidence >= 0.4:
                    conf_level = ConfidenceLevel.MEDIUM
                else:
                    conf_level = ConfidenceLevel.LOW

                results.append(RuntimeInfo(
                    id=f"{adapter.adapter_id}-{hash(str(workspace)) % 10000:04d}",
                    name=f"{adapter.adapter_name} Project",
                    adapter=adapter.adapter_id,
                    confidence=conf_level,
                    evidence=evidence,
                    capabilities=adapter.capabilities(),
                ))
                log.info("Adapter %s detected (confidence=%.2f)", adapter.adapter_id, confidence)

            except Exception as e:
                log.warning("Adapter %s detection failed: %s", adapter.adapter_id, e)

        return results

    def build_default(self) -> "AdapterRegistry":
        """Build registry with all built-in adapters."""
        from .crewai import CrewAIAdapter
        from .swarmgraph import SwarmGraphAdapter
        from .langgraph import LangGraphAdapter
        from .llamaindex import LlamaIndexAdapter
        from .lmarena import LmarenaAdapter
        from .openai_agents import OpenAIAgentsAdapter
        self.register(SwarmGraphAdapter())
        self.register(LangGraphAdapter())
        self.register(CrewAIAdapter())
        self.register(OpenAIAgentsAdapter())
        self.register(LlamaIndexAdapter())
        self.register(LmarenaAdapter())
        return self


def default_registry() -> AdapterRegistry:
    return AdapterRegistry().build_default()


def get_adapter(adapter_id: str) -> Optional[RuntimeAdapter]:
    return default_registry().get(adapter_id)


def iter_adapters() -> list[RuntimeAdapter]:
    return default_registry().all()
