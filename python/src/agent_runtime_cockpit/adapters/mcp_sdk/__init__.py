"""MCP Python SDK adapter for ARC Studio.

Adapter Phase 35: T1 detection and T2 static export only.

T3 execution is intentionally not implemented because:
- MCP servers require live transport (stdio/HTTP/SSE) and client-session
  lifecycle management that is inappropriate for a local static CLI.
- Trust posture is the most subtle of all adapters: an MCP server exposes
  tools and resources that may perform privileged operations; executing an
  arbitrary server without user-explicit trust gates would violate Phase 23.
- MCP Python SDK v2 is in pre-alpha; execution lifecycle APIs are unstable.

Detected constructs: FastMCP server instances, @tool/@resource/@prompt
decorators, low-level Server, ClientSession, transport helpers.
"""

from __future__ import annotations

from pathlib import Path

from ...protocol.capabilities import RuntimeCapabilities
from ...protocol.schemas import WorkflowInfo
from ..base import CapabilityReport, DoctorAction, RuntimeAdapter
from .capabilities import get_mcp_sdk_capabilities
from .detect import MCPSDKDetectionResult, detect_mcp_sdk
from .export import MCPSDKVisitor, export_mcp_sdk_workflows

__all__ = [
    "MCPSDKAdapter",
    "MCPSDKDetectionResult",
    "MCPSDKVisitor",
    "detect_mcp_sdk",
    "export_mcp_sdk_workflows",
]


class MCPSDKAdapter(RuntimeAdapter):
    """MCP Python SDK adapter with static detection/export only."""

    @property
    def adapter_id(self) -> str:
        return "mcp_sdk"

    @property
    def adapter_name(self) -> str:
        return "MCP Python SDK"

    def capabilities(self) -> RuntimeCapabilities:
        return get_mcp_sdk_capabilities()

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        result = detect_mcp_sdk(workspace)
        return result.detected, result.confidence, result.evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        return export_mcp_sdk_workflows(workspace)

    def capability_report(self, workspace: Path) -> CapabilityReport:
        result = detect_mcp_sdk(workspace)
        if not result.detected:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=False,
                can_run=False,
                availability="not_detected",
                reason="MCP Python SDK not detected in workspace",
                detected_artifacts=[],
                doctor_actions=[
                    DoctorAction(
                        id="install-mcp",
                        label="Install MCP Python SDK",
                        description="Install the MCP Python SDK in this Python environment",
                        command='pip install "mcp[cli]"',
                        safe_to_auto_run=False,
                    )
                ],
            )
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=True,
            can_run=False,
            availability="detected_not_runnable",
            reason=(
                "MCP Python SDK detected. T1 (detection) and T2 (static export) are available. "
                "T3 execution is intentionally not implemented: MCP servers require live "
                "transport/session lifecycle and have the most subtle trust posture of all "
                "adapters (tools and resources may perform privileged operations)."
            ),
            detected_artifacts=result.evidence,
            version=result.version,
            doctor_actions=[],
            test_level="unknown",
            fake_offline_supported=False,
            local_real_gated=False,
            local_real_available=False,
            provider_backed=False,
        )
