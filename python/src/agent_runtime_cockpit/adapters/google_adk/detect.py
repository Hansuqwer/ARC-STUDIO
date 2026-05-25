"""Google ADK detection logic.

T1 detection is import/config/static-file based only. It never executes user code.

Google ADK Python package: ``google-adk`` (``import google.adk``).
Agent types: LlmAgent, SequentialAgent, ParallelAgent, LoopAgent (and legacy Agent alias).
Tool types: FunctionTool, built-in tools via ``google.adk.tools``.
Runner types: Runner, InMemoryRunner (``google.adk.runners``).
"""

from __future__ import annotations

import importlib.util
import logging
import warnings
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class GoogleADKDetectionResult(NamedTuple):
    """Result of Google ADK detection probe."""

    detected: bool
    confidence: float
    evidence: list[str]
    version: str | None
    has_llm_agent: bool
    has_sequential_agent: bool
    has_parallel_agent: bool
    has_loop_agent: bool
    has_tools: bool
    has_runner: bool


def detect_google_adk_import() -> tuple[bool, str | None]:
    """Check whether ``google.adk`` is importable and return its version.

    ``importlib.util.find_spec("google.adk")`` raises ``ModuleNotFoundError``
    when the ``google`` namespace package itself does not exist. We catch that
    and treat it as "not installed".
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            spec = importlib.util.find_spec("google.adk")
    except (ModuleNotFoundError, ValueError):
        return False, None
    if spec is None:
        return False, None
    try:
        import google.adk  # noqa: PLC0415

        return True, getattr(google.adk, "__version__", None)
    except Exception as exc:  # noqa: BLE001 - optional dependency probe must not fail detection.
        log.debug("google.adk import failed: %s", exc)
        return False, None


def scan_workspace_for_google_adk(
    workspace: Path,
) -> tuple[list[str], bool, bool, bool, bool, bool, bool]:
    """Scan workspace for Google ADK usage patterns without executing any code.

    Returns:
        (evidence, has_llm_agent, has_sequential_agent, has_parallel_agent,
         has_loop_agent, has_tools, has_runner)
    """
    evidence: list[str] = []
    has_llm_agent = False
    has_sequential_agent = False
    has_parallel_agent = False
    has_loop_agent = False
    has_tools = False
    has_runner = False

    import_patterns = (
        "import google.adk",
        "from google.adk",
        "google-adk",
    )
    llm_agent_patterns = ("LlmAgent(", "LlmAgent(", "Agent(")
    sequential_patterns = ("SequentialAgent(",)
    parallel_patterns = ("ParallelAgent(",)
    loop_patterns = ("LoopAgent(",)
    tool_patterns = (
        "FunctionTool(",
        "google_search",
        "built_in_code_execution",
        "google.adk.tools",
        "@tool",
    )
    runner_patterns = ("Runner(", "InMemoryRunner(", "google.adk.runners")

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
        has_llm_agent = has_llm_agent or any(p in content for p in llm_agent_patterns)
        has_sequential_agent = has_sequential_agent or any(
            p in content for p in sequential_patterns
        )
        has_parallel_agent = has_parallel_agent or any(p in content for p in parallel_patterns)
        has_loop_agent = has_loop_agent or any(p in content for p in loop_patterns)
        has_tools = has_tools or any(p in content for p in tool_patterns)
        has_runner = has_runner or any(p in content for p in runner_patterns)

    for req_file in ("requirements.txt", "requirements-dev.txt", "pyproject.toml"):
        req_path = workspace / req_file
        if not req_path.exists():
            continue
        try:
            content = req_path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError as exc:
            log.debug("Failed to read %s: %s", req_path, exc)
            continue
        if "google-adk" in content or "google.adk" in content:
            evidence.append(req_file)

    return (
        evidence,
        has_llm_agent,
        has_sequential_agent,
        has_parallel_agent,
        has_loop_agent,
        has_tools,
        has_runner,
    )


def detect_google_adk(workspace: Path) -> GoogleADKDetectionResult:
    """Detect Google ADK usage in workspace without executing workspace code."""
    installed, version = detect_google_adk_import()
    (
        workspace_evidence,
        has_llm_agent,
        has_sequential_agent,
        has_parallel_agent,
        has_loop_agent,
        has_tools,
        has_runner,
    ) = scan_workspace_for_google_adk(workspace)

    evidence: list[str] = []
    if installed:
        evidence.append(f"google-adk installed (version: {version or 'unknown'})")
    evidence.extend(workspace_evidence)

    detected = installed or bool(workspace_evidence)
    confidence = 0.0
    if installed:
        confidence += 0.3
    if workspace_evidence:
        confidence += 0.25
    if has_llm_agent:
        confidence += 0.2
    if has_sequential_agent or has_parallel_agent or has_loop_agent:
        confidence += 0.1
    if has_tools:
        confidence += 0.1
    if has_runner:
        confidence += 0.05

    if not detected:
        confidence = 0.0

    return GoogleADKDetectionResult(
        detected=detected,
        confidence=round(min(confidence, 1.0), 4),
        evidence=evidence,
        version=version,
        has_llm_agent=has_llm_agent,
        has_sequential_agent=has_sequential_agent,
        has_parallel_agent=has_parallel_agent,
        has_loop_agent=has_loop_agent,
        has_tools=has_tools,
        has_runner=has_runner,
    )


def _skip_path(path: Path) -> bool:
    ignored = {".venv", "venv", "node_modules", "__pycache__", ".git"}
    return any(part in ignored for part in path.parts)
