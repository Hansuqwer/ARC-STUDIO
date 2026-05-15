"""
Adoption registry — resolves adoption modes to runners (P1b).

Provides ``AdoptionRegistry`` for registering, querying, and listing
adoption runners. Also provides ``parse_runtime_id()`` for resolving
``<runtime>+swarmgraph`` syntax.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .protocol import (
    AdoptionMode,
    AdoptionCapability,
    AdoptionStatus,
    AdoptionRunner,
)

log = logging.getLogger(__name__)


class AdoptionRegistry:
    """Registry of adoption runners keyed by AdoptionMode."""

    _runners: dict[AdoptionMode, AdoptionRunner] = {}

    @classmethod
    def _auto_register(cls) -> None:
        """Auto-register available adoption runners on first use."""
        if cls._runners:
            return
        # LangGraph runner
        try:
            from .langgraph_runner import LangGraphAdoptionRunner
            cls.register(LangGraphAdoptionRunner())
        except ImportError:
            pass
        # LlamaIndex runner
        try:
            from .llamaindex_runner import LlamaIndexAdoptionRunner
            cls.register(LlamaIndexAdoptionRunner())
        except ImportError:
            pass
        # OpenAI Agents runner
        try:
            from .openai_agents_runner import OpenAIAgentsAdoptionRunner
            cls.register(OpenAIAgentsAdoptionRunner())
        except ImportError:
            pass
        # CrewAI runner
        try:
            from .crewai_runner import CrewAIAdoptionRunner
            cls.register(CrewAIAdoptionRunner())
        except ImportError:
            pass
        # AG2 runner
        try:
            from .ag2_runner import AG2AdoptionRunner
            cls.register(AG2AdoptionRunner())
        except ImportError:
            pass

    @classmethod
    def register(cls, runner: AdoptionRunner) -> None:
        """Register a runner for its mode."""
        cls._runners[runner.mode] = runner

    @classmethod
    def get(cls, mode: AdoptionMode) -> Optional[AdoptionRunner]:
        """Look up a runner by adoption mode."""
        cls._auto_register()
        return cls._runners.get(mode)

    @classmethod
    def list_capabilities(cls, workspace: Path) -> list[AdoptionCapability]:
        """Report capability for every known adoption mode.

        Modes without a registered runner report NOT_IMPLEMENTED.
        Registered runners are asked via ``check_availability()``.
        """
        cls._auto_register()
        caps: list[AdoptionCapability] = []
        for mode in AdoptionMode:
            runner = cls._runners.get(mode)
            if runner is None:
                caps.append(AdoptionCapability(
                    mode=mode,
                    status=AdoptionStatus.NOT_IMPLEMENTED,
                    reason="Adoption runner not yet implemented",
                    doctor_actions=[{
                        "id": "implement",
                        "label": "Implement adoption runner",
                        "description": f"Implement {mode.value} adoption adapter",
                    }],
                ))
            else:
                caps.append(runner.check_availability(workspace))
        return caps

    @classmethod
    def parse_runtime_id(cls, runtime_id: str) -> tuple[str, Optional[AdoptionMode]]:
        """Parse a ``<runtime>+swarmgraph`` string into its base and mode.

        Returns ``(base, mode)`` where *mode* is ``None`` if the id does
        not end with ``+swarmgraph`` or the suffix is not a known mode.
        """
        if runtime_id.endswith("+swarmgraph"):
            base = runtime_id.removesuffix("+swarmgraph")
            mode_map = {m.value.split("+")[0]: m for m in AdoptionMode}
            mode = mode_map.get(base)
            return base, mode  # mode may be None for unknown base
        return runtime_id, None
