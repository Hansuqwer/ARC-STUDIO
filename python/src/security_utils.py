"""Security Utilities.

Provides input validation, sanitization, and security checks
for the ARC Studio Python backend.
"""

import re
from pathlib import Path


class SecurityError(Exception):
    """Raised when a security validation fails."""

    pass


def sanitize_prompt(prompt: str) -> str:
    """Validates and sanitizes user prompts to prevent command injection.

    Args:
        prompt: User-provided prompt string

    Returns:
        Sanitized prompt string

    Raises:
        SecurityError: If prompt is invalid or contains dangerous characters

    """
    if not prompt or not isinstance(prompt, str):
        raise SecurityError("Invalid prompt: must be a non-empty string")

    # Limit prompt length to prevent DoS
    MAX_PROMPT_LENGTH = 10000
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise SecurityError(f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters")

    # Remove null bytes and control characters
    sanitized = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", prompt)

    # Check for shell metacharacters that could enable command injection
    dangerous_patterns = [
        r"[;&|`$<>]",  # Shell metacharacters
        r"\$\(",  # Command substitution
        r"`",  # Backtick command substitution
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, sanitized):
            raise SecurityError("Prompt contains potentially dangerous characters")

    return sanitized.strip()


def validate_trace_id(trace_id: str) -> str:
    """Validates trace ID to prevent path traversal attacks.

    Args:
        trace_id: Trace identifier

    Returns:
        Validated trace ID

    Raises:
        SecurityError: If trace ID is invalid

    """
    if not trace_id or not isinstance(trace_id, str):
        raise SecurityError("Invalid trace ID: must be a non-empty string")

    # Trace IDs should match the pattern: run-[prefix]-[hexadecimal]
    # Supports: sg (SwarmGraph), lg (LangGraph), ca (Claude), openai
    if not re.match(r"^run-(sg|lg|ca|openai)-[a-f0-9]+$", trace_id):
        raise SecurityError("Invalid trace ID format")

    # Additional check: ensure no path traversal characters
    if ".." in trace_id or "/" in trace_id or "\\" in trace_id:
        raise SecurityError("Trace ID contains invalid path characters")

    return trace_id


def validate_file_path(file_path: str, workspace_root: str) -> Path:
    """Validates and normalizes file paths to prevent directory traversal.

    Args:
        file_path: File path to validate
        workspace_root: Root directory of the workspace

    Returns:
        Validated absolute Path object

    Raises:
        SecurityError: If path is invalid or outside workspace

    """
    if not file_path or not isinstance(file_path, str):
        raise SecurityError("Invalid file path: must be a non-empty string")

    # Check for null bytes BEFORE path resolution (Path.resolve() throws on null bytes)
    if "\0" in file_path:
        raise SecurityError("File path contains null bytes")

    # Resolve absolute paths
    workspace_path = Path(workspace_root).resolve()
    target_path = (workspace_path / file_path).resolve()

    # Ensure the resolved path is within the workspace
    try:
        target_path.relative_to(workspace_path)
    except ValueError:
        raise SecurityError("File path is outside workspace boundaries")

    return target_path


def validate_backend(backend: str) -> str:
    """Validates backend option.
    Canonical set: stub | local | gateway.

    Args:
        backend: Backend identifier

    Returns:
        Validated backend string

    Raises:
        SecurityError: If backend is invalid

    """
    allowed_backends = ["stub", "local", "gateway"]

    if not backend or not isinstance(backend, str):
        raise SecurityError("Invalid backend: must be a non-empty string")

    backend_lower = backend.lower()
    if backend_lower not in allowed_backends:
        raise SecurityError(f"Invalid backend: must be one of {', '.join(allowed_backends)}")

    return backend_lower


def sanitize_error_message(error: Exception) -> str:
    """Sanitizes error messages to prevent information leakage.

    Args:
        error: Exception object

    Returns:
        Safe error message string

    """
    error_str = str(error).lower()

    # Map specific errors to safe messages
    if "no such file" in error_str or "not found" in error_str:
        return "Resource not found"

    if "permission denied" in error_str or "access" in error_str:
        return "Permission denied"

    if "timeout" in error_str:
        return "Operation timed out"

    if "command" in error_str or "spawn" in error_str:
        return "Failed to execute command"

    # For SecurityError, we can expose the message as it's user-facing
    if isinstance(error, SecurityError):
        return str(error)

    # Generic error message for everything else
    return "An error occurred while processing your request"


def validate_workspace_root(workspace_root: str) -> Path:
    """Validates workspace root directory.

    Args:
        workspace_root: Workspace root path

    Returns:
        Validated absolute Path object

    Raises:
        SecurityError: If workspace root is invalid

    """
    if not workspace_root or not isinstance(workspace_root, str):
        raise SecurityError("Invalid workspace root")

    workspace_path = Path(workspace_root).resolve()

    # Ensure it's an absolute path
    if not workspace_path.is_absolute():
        raise SecurityError("Workspace root must be an absolute path")

    return workspace_path
