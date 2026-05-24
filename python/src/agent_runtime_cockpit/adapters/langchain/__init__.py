"""LangChain Runtime Adapter.

Phase 26 T1: Detection implemented.
Phase 26 T2: Export implemented (AST-based).
Phase 26 T3: Live streaming implemented (BaseCallbackHandler).

Detects, exports, and executes LangChain Runnable/LCEL pipelines.

Out of scope (per roadmap):
- AgentExecutor (redirected to LangGraph by upstream)
- ReAct loops (redirected to LangGraph by upstream)

Pinned version: langchain >=0.3,<2.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...protocol.capabilities import RuntimeCapabilities
from ...protocol.schemas import RunRecord, WorkflowInfo
from ..base import CapabilityReport, DoctorAction, RuntimeAdapter
from .capabilities import get_langchain_capabilities
from .detect import detect_langchain
from .export import export_langchain_workflows
from .runner import LangChainRunner

log = logging.getLogger(__name__)


class LangChainAdapter(RuntimeAdapter):
    """LangChain adapter for ARC Studio.

    Phase 26 T1: Detection implemented.
    Phase 26 T2: Export implemented (AST-based).
    Phase 26 T3: Live streaming implemented (BaseCallbackHandler).
    """

    @property
    def adapter_id(self) -> str:
        return "langchain"

    @property
    def adapter_name(self) -> str:
        return "LangChain"

    def capabilities(self) -> RuntimeCapabilities:
        """Return LangChain adapter capabilities."""
        return get_langchain_capabilities()

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        """Detect LangChain usage in workspace.

        Returns:
            (detected, confidence_0_to_1, evidence_list)

        Detection strategy:
        - Check for langchain, langchain_core, langchain_community imports
        - Detect provider integrations (langchain_openai, etc.)
        - Scan workspace for LangChain usage patterns
        - Check requirements.txt, pyproject.toml for langchain dependencies

        """
        result = detect_langchain(workspace)
        return result.detected, result.confidence, result.evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        """Export LangChain workflows from workspace.

        Phase 26 T2: AST-based export of Runnable/LCEL chains.

        Strategy:
        - AST scan for pipe operator (|) chains
        - AST scan for RunnableSequence instantiations
        - No code execution (static analysis only)
        - Maps chains to WorkflowInfo structure

        Returns:
            List of WorkflowInfo for detected chains

        """
        return export_langchain_workflows(workspace)

    def run_chain(
        self,
        workspace: Path,
        chain: Any,
        inputs: dict[str, Any],
        provider_registry: dict | None = None,
    ) -> RunRecord:
        """Run a LangChain chain with live event streaming.

        Phase 26 T3: Execute chain with ARCCallbackHandler for live streaming.

        Args:
            workspace: Workspace path
            chain: LangChain Runnable to execute
            inputs: Input dictionary for the chain
            provider_registry: Optional registry of known providers

        Returns:
            RunRecord with execution results and events

        """
        runner = LangChainRunner(workspace)
        return runner.run(chain, inputs, provider_registry)

    def capability_report(self, workspace: Path) -> CapabilityReport:
        """Return detailed capability report for LangChain adapter."""
        detected, confidence, evidence = self.detect(workspace)
        result = detect_langchain(workspace)

        # Check if langchain is installed
        if not result.detected:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=False,
                can_run=False,
                availability="not_detected",
                reason="LangChain not detected in workspace",
                detected_artifacts=[],
                doctor_actions=[
                    DoctorAction(
                        id="install-langchain",
                        label="Install LangChain",
                        description="Install langchain in this Python environment",
                        command="pip install 'langchain>=0.3,<2.0' langchain-core",
                        safe_to_auto_run=False,
                    ),
                ],
            )

        # LangChain detected with export capability
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=True,
            can_run=False,
            availability="detected_not_runnable",
            reason="LangChain detected. Workflow export available (T2). Live streaming (T3) not yet implemented.",
            detected_artifacts=evidence,
            version=result.version,
            doctor_actions=[],
            test_level="unknown",
            fake_offline_supported=False,
            local_real_gated=False,
            local_real_available=False,
            provider_backed=False,
        )


__all__ = ["LangChainAdapter"]
