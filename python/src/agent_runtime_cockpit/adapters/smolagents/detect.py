"""Smolagents detection logic.

Detects Smolagents usage via import probes and workspace file scanning.
No workspace code is executed.
"""

from __future__ import annotations

import importlib.util
import logging
import warnings
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class SmolagentsDetectionResult(NamedTuple):
    """Result of Smolagents detection probe."""

    detected: bool
    confidence: float
    evidence: list[str]
    version: str | None
    has_agents: bool
    has_tools: bool
    has_models: bool
    has_code_execution: bool


def detect_smolagents_import() -> tuple[bool, str | None]:
    """Check if smolagents is importable and get version."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        spec = importlib.util.find_spec("smolagents")

    if spec is None:
        return False, None

    try:
        import smolagents

        version = getattr(smolagents, "__version__", None)
        return True, version
    except Exception as e:
        log.debug("smolagents import failed: %s", e)
        return False, None


def scan_workspace_for_smolagents(
    workspace: Path,
) -> tuple[list[str], bool, bool, bool, bool]:
    """Scan workspace for Smolagents usage patterns."""
    evidence: list[str] = []
    has_agents = False
    has_tools = False
    has_models = False
    has_code_execution = False

    import_patterns = ["import smolagents", "from smolagents"]
    agent_patterns = ["CodeAgent", "ToolCallingAgent", "ManagedAgent"]
    tool_patterns = ["@tool", "Tool(", "Tool.from_", "ToolCollection"]
    model_patterns = [
        "InferenceClientModel",
        "LiteLLMModel",
        "OpenAIModel",
        "TransformersModel",
        "AzureOpenAIModel",
        "AmazonBedrockModel",
        "OllamaModel",
    ]
    code_exec_patterns = ["CodeAgent", "LocalPythonExecutor", "Docker", "E2B", "Modal"]

    for py_file in workspace.rglob("*.py"):
        if ".venv" in py_file.parts or "venv" in py_file.parts:
            continue
        if "node_modules" in py_file.parts:
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if not any(pattern in content for pattern in import_patterns):
                continue
            evidence.append(str(py_file.relative_to(workspace)))
            has_agents = has_agents or any(pattern in content for pattern in agent_patterns)
            has_tools = has_tools or any(pattern in content for pattern in tool_patterns)
            has_models = has_models or any(pattern in content for pattern in model_patterns)
            has_code_execution = has_code_execution or any(
                pattern in content for pattern in code_exec_patterns
            )
        except Exception as e:
            log.debug("Failed to read %s: %s", py_file, e)

    for req_file in ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]:
        req_path = workspace / req_file
        if req_path.exists():
            try:
                content = req_path.read_text(encoding="utf-8", errors="ignore")
                if "smolagents" in content.lower():
                    evidence.append(req_file)
            except Exception as e:
                log.debug("Failed to read %s: %s", req_path, e)

    return evidence, has_agents, has_tools, has_models, has_code_execution


def detect_smolagents(workspace: Path) -> SmolagentsDetectionResult:
    """Detect Smolagents usage in workspace."""
    has_smolagents, version = detect_smolagents_import()
    workspace_evidence, has_agents, has_tools, has_models, has_code_execution = (
        scan_workspace_for_smolagents(workspace)
    )

    evidence: list[str] = []
    if has_smolagents:
        evidence.append(f"smolagents installed (version: {version or 'unknown'})")
    evidence.extend(workspace_evidence)

    detected = False
    confidence = 0.0

    if has_smolagents:
        detected = True
        confidence = 0.3
        if workspace_evidence:
            confidence += 0.3
    elif workspace_evidence:
        detected = True
        confidence = 0.2

    if detected:
        if has_agents:
            confidence += 0.2
        if has_tools:
            confidence += 0.1
        if has_models:
            confidence += 0.1
        if has_code_execution:
            confidence += 0.1
        confidence = min(confidence, 1.0)

    return SmolagentsDetectionResult(
        detected=detected,
        confidence=confidence,
        evidence=evidence,
        version=version,
        has_agents=has_agents,
        has_tools=has_tools,
        has_models=has_models,
        has_code_execution=has_code_execution,
    )
