"""Pydantic AI detection logic.

Detects Pydantic AI usage via import probes and workspace file scanning.
Phase 29 PR 29.1: Detection only (no execution).
"""

from __future__ import annotations

import importlib.util
import logging
import warnings
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class PydanticAIDetectionResult(NamedTuple):
    """Result of Pydantic AI detection probe."""

    detected: bool
    confidence: float
    evidence: list[str]
    version: str | None
    model_providers: list[str]


def detect_pydantic_ai_import() -> tuple[bool, str | None]:
    """Check if pydantic_ai is importable and get version.

    Returns:
        (is_installed, version_string)

    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        spec = importlib.util.find_spec("pydantic_ai")

    if spec is None:
        return False, None

    try:
        import pydantic_ai

        version = getattr(pydantic_ai, "__version__", None)
        return True, version
    except Exception as e:
        log.debug("pydantic_ai import failed: %s", e)
        return False, None


def detect_model_providers() -> list[str]:
    """Detect configured Pydantic AI model providers.

    Pydantic AI supports: OpenAI, Anthropic, Gemini, Groq, Mistral, Ollama.
    Returns list of detected provider package names.
    """
    providers = [
        "openai",  # OpenAI models
        "anthropic",  # Anthropic Claude models
        "google.generativeai",  # Google Gemini models
        "groq",  # Groq models
        "mistralai",  # Mistral models
        # Ollama doesn't require a package, uses HTTP API
    ]

    detected = []
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        for provider in providers:
            spec = importlib.util.find_spec(provider)
            if spec is not None:
                detected.append(provider)

    return detected


def scan_workspace_for_pydantic_ai(workspace: Path) -> list[str]:
    """Scan workspace for Pydantic AI usage patterns.

    Returns list of evidence (file paths with Pydantic AI imports).
    """
    evidence = []

    # Check for common Pydantic AI import patterns
    patterns = [
        "from pydantic_ai",
        "import pydantic_ai",
        "pydantic_ai.Agent",
        "pydantic_ai.models",
    ]

    # Scan Python files
    for py_file in workspace.rglob("*.py"):
        if ".venv" in py_file.parts or "venv" in py_file.parts:
            continue
        if "node_modules" in py_file.parts:
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern in content:
                    rel_path = py_file.relative_to(workspace)
                    evidence.append(str(rel_path))
                    break  # Only add file once
        except Exception as e:
            log.debug("Failed to read %s: %s", py_file, e)

    # Check for requirements.txt
    req_files = ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
    for req_file in req_files:
        req_path = workspace / req_file
        if req_path.exists():
            try:
                content = req_path.read_text(encoding="utf-8", errors="ignore")
                if "pydantic-ai" in content.lower() or "pydantic_ai" in content.lower():
                    evidence.append(req_file)
            except Exception as e:
                log.debug("Failed to read %s: %s", req_path, e)

    return evidence


def detect_pydantic_ai(workspace: Path) -> PydanticAIDetectionResult:
    """Detect Pydantic AI usage in workspace.

    Phase 29 PR 29.1: Import-only probe, no code execution.

    Returns:
        PydanticAIDetectionResult with detection status, confidence, and evidence.

    """
    # Check import availability
    has_pydantic_ai, version = detect_pydantic_ai_import()
    model_providers = detect_model_providers()

    # Scan workspace for usage
    workspace_evidence = scan_workspace_for_pydantic_ai(workspace)

    # Build evidence list
    evidence = []
    if has_pydantic_ai:
        evidence.append(f"pydantic_ai installed (version: {version or 'unknown'})")

    for provider in model_providers:
        evidence.append(f"{provider} provider installed")

    evidence.extend(workspace_evidence)

    # Calculate confidence
    detected = False
    confidence = 0.0

    if has_pydantic_ai:
        detected = True
        confidence = 0.4  # Base confidence for having the library

        if workspace_evidence:
            confidence += 0.4  # Boost for actual usage in workspace

        if model_providers:
            confidence += 0.2  # Boost for provider integrations

        # Cap at 1.0
        confidence = min(confidence, 1.0)

    return PydanticAIDetectionResult(
        detected=detected,
        confidence=confidence,
        evidence=evidence,
        version=version,
        model_providers=model_providers,
    )
