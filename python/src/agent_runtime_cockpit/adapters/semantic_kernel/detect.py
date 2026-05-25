"""Semantic Kernel detection logic.

T1 detection is import/config/static-file based only. It never executes user code.
"""

from __future__ import annotations

import importlib.util
import logging
import warnings
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class SemanticKernelDetectionResult(NamedTuple):
    """Result of Semantic Kernel detection."""

    detected: bool
    confidence: float
    evidence: list[str]
    version: str | None
    has_kernel: bool
    has_plugins: bool
    has_agents: bool
    has_processes: bool


def detect_semantic_kernel_import() -> tuple[bool, str | None]:
    """Check whether ``semantic_kernel`` is importable."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        spec = importlib.util.find_spec("semantic_kernel")
    if spec is None:
        return False, None
    try:
        import semantic_kernel

        return True, getattr(semantic_kernel, "__version__", None)
    except Exception as exc:  # noqa: BLE001 - optional dependency probe must not fail detection.
        log.debug("semantic_kernel import failed: %s", exc)
        return False, None


def scan_workspace_for_semantic_kernel(
    workspace: Path,
) -> tuple[list[str], bool, bool, bool, bool]:
    """Scan workspace for Semantic Kernel usage patterns."""
    evidence: list[str] = []
    has_kernel = False
    has_plugins = False
    has_agents = False
    has_processes = False

    import_patterns = ("import semantic_kernel", "from semantic_kernel")
    kernel_patterns = (
        "Kernel(",
        "semantic_kernel.Kernel",
        ".add_service(",
        ".invoke(",
        ".invoke_prompt(",
    )
    plugin_patterns = ("@kernel_function", "kernel_function(", ".add_plugin(", "KernelPlugin")
    agent_patterns = (
        "ChatCompletionAgent",
        "SequentialOrchestration",
        "ConcurrentOrchestration",
        "HandoffOrchestration",
        "GroupChatOrchestration",
    )
    process_patterns = (
        "ProcessBuilder",
        "KernelProcess",
        "@kernel_process_step",
        "KernelProcessStep",
    )

    for py_file in workspace.rglob("*.py"):
        if _skip_path(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            log.debug("Failed to read %s: %s", py_file, exc)
            continue
        if not any(pattern in content for pattern in import_patterns):
            continue
        rel_path = str(py_file.relative_to(workspace))
        evidence.append(rel_path)
        has_kernel = has_kernel or any(pattern in content for pattern in kernel_patterns)
        has_plugins = has_plugins or any(pattern in content for pattern in plugin_patterns)
        has_agents = has_agents or any(pattern in content for pattern in agent_patterns)
        has_processes = has_processes or any(pattern in content for pattern in process_patterns)

    for req_file in ("requirements.txt", "requirements-dev.txt", "pyproject.toml"):
        req_path = workspace / req_file
        if not req_path.exists():
            continue
        try:
            content = req_path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError as exc:
            log.debug("Failed to read %s: %s", req_path, exc)
            continue
        if "semantic-kernel" in content or "semantic_kernel" in content:
            evidence.append(req_file)

    return evidence, has_kernel, has_plugins, has_agents, has_processes


def detect_semantic_kernel(workspace: Path) -> SemanticKernelDetectionResult:
    """Detect Semantic Kernel usage without executing workspace code."""
    installed, version = detect_semantic_kernel_import()
    workspace_evidence, has_kernel, has_plugins, has_agents, has_processes = (
        scan_workspace_for_semantic_kernel(workspace)
    )
    evidence: list[str] = []
    if installed:
        evidence.append(f"semantic-kernel installed (version: {version or 'unknown'})")
    evidence.extend(workspace_evidence)

    detected = installed or bool(workspace_evidence)
    confidence = 0.0
    if installed:
        confidence += 0.3
    if workspace_evidence:
        confidence += 0.25
    if has_kernel:
        confidence += 0.15
    if has_plugins:
        confidence += 0.15
    if has_agents:
        confidence += 0.1
    if has_processes:
        confidence += 0.05
    if not detected:
        confidence = 0.0
    return SemanticKernelDetectionResult(
        detected=detected,
        confidence=round(min(confidence, 1.0), 4),
        evidence=evidence,
        version=version,
        has_kernel=has_kernel,
        has_plugins=has_plugins,
        has_agents=has_agents,
        has_processes=has_processes,
    )


def _skip_path(path: Path) -> bool:
    ignored = {".venv", "venv", "node_modules", "__pycache__"}
    return any(part in ignored for part in path.parts)
