"""
LangGraph + SwarmGraph adoption runner — skeleton implementation (P1b).

Reports NOT_RUNNABLE until the actual adoption integration is implemented.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, AsyncIterator

from .protocol import (
    AdoptionMode,
    AdoptionSpec,
    AdoptionCapability,
    AdoptionStatus,
    AdoptionRunner,
    ConsensusResult,
)

log = logging.getLogger(__name__)


class LangGraphAdoptionRunner(AdoptionRunner):
    """Adoption runner for LangGraph + SwarmGraph (scaffold-only)."""

    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.LANGGRAPH

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        try:
            import langgraph  # noqa: F401
            version = getattr(langgraph, "__version__", "unknown")
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason=(
                    f"LangGraph {version} detected, "
                    "but adoption runner is scaffold-only. "
                    "Implementation pending P2."
                ),
                doctor_actions=[{
                    "id": "implement-langgraph-adoption",
                    "label": "Implement LangGraph adoption runner",
                    "description": "Implement LangGraph + SwarmGraph adoption logic",
                }],
            )
        except ImportError:
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason="LangGraph package not installed.",
                doctor_actions=[{
                    "id": "install-langgraph",
                    "label": "Install LangGraph",
                    "description": "Install LangGraph with: pip install langgraph",
                }],
            )

    async def run(
        self,
        spec: AdoptionSpec,
        run_id: str,
        emit_event,
    ) -> ConsensusResult:
        raise NotImplementedError(
            f"{self.mode.value} adoption runner is scaffold-only"
        )

    async def stream_worker_events(
        self,
        run_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        yield {}
