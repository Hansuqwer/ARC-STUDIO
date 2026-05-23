"""
Policy bypass warning event types (Phase 22.1 / ADR-0022.1).

Provides warning events when agent execution bypasses enforcement boundaries
due to uninstrumented providers, custom clients, or upstream boundary violations.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from pydantic import BaseModel


class PolicyBypassReason(StrEnum):
    """Reason codes for policy bypass warnings."""

    UNKNOWN_PROVIDER_PLUGIN = "unknown_provider_plugin"
    CUSTOM_HTTP_CLIENT = "custom_http_client"
    CUSTOM_SUBPROCESS_RUNNER = "custom_subprocess_runner"
    UNINSTRUMENTED_TOOL = "uninstrumented_tool"
    UPSTREAM_BYPASSED_BOUNDARY = "upstream_bypassed_boundary"


class PolicyBypassWarningData(BaseModel):
    """Data payload for POLICY_BYPASS_WARNING event."""

    policy_id: str
    bypass_reason: PolicyBypassReason
    surface: str  # e.g., "provider_call", "tool_execution", "subprocess_spawn"
    surface_identifier: str  # e.g., "openai.chat.completions", "custom_http_client"
    suggested_remediation: str
    parent_run_id: str | None = None


class PolicyBypassWarning(BaseModel):
    """
    POLICY_BYPASS_WARNING event emitted when execution bypasses enforcement.

    Unlike denial events (TRUST_DENIED, PAID_CALL_DENIED), bypass warnings are
    non-blocking. They indicate that enforcement could not be applied due to
    architectural limitations (e.g., custom HTTP client, uninstrumented tool).
    """

    schema_version: int = 2
    type: Literal["POLICY_BYPASS_WARNING"]
    timestamp: str
    run_id: str
    sequence: int
    data: PolicyBypassWarningData
