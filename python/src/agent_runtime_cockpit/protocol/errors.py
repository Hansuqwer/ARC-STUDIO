"""ARC standard error codes.

Canonical list defined by ADR-023. Keep this enum in sync with
``packages/arc-extension/src/common/arc-protocol.ts``.
"""
from enum import Enum


class ArcErrorCode(str, Enum):
    # Workspace & runtime detection
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"
    NO_RUNTIME_DETECTED = "NO_RUNTIME_DETECTED"

    # Adapter layer
    ADAPTER_ERROR = "ADAPTER_ERROR"
    ADAPTER_NOT_SUPPORTED = "ADAPTER_NOT_SUPPORTED"

    # Schema & workflow export
    SCHEMA_EXPORT_FAILED = "SCHEMA_EXPORT_FAILED"
    WORKFLOW_EXPORT_FAILED = "WORKFLOW_EXPORT_FAILED"

    # Run execution
    RUN_FAILED = "RUN_FAILED"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"

    # Context & conformance
    CONTEXT_PROVIDER_ERROR = "CONTEXT_PROVIDER_ERROR"
    CONFORMANCE_FAILED = "CONFORMANCE_FAILED"

    # Generic errors
    INVALID_INPUT = "INVALID_INPUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # Fallback
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_legacy(cls, code: str) -> "ArcErrorCode":
        """Normalize deprecated TypeScript wire codes to canonical codes."""
        legacy_map = {
            "TRACE_NOT_FOUND": cls.RUN_NOT_FOUND,
            "EXECUTION_FAILED": cls.RUN_FAILED,
            "PARSE_ERROR": cls.INVALID_INPUT,
            "WORKFLOW_NOT_FOUND": cls.WORKSPACE_NOT_FOUND,
        }
        if code in legacy_map:
            return legacy_map[code]
        try:
            return cls(code)
        except ValueError:
            return cls.UNKNOWN
