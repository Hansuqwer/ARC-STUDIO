"""LangChain detection logic.

Detects LangChain usage via import probes and workspace file scanning.
Phase 26 T1: Detection only (no execution).
"""

from __future__ import annotations

import importlib.util
import logging
import warnings
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class LangChainDetectionResult(NamedTuple):
    """Result of LangChain detection probe."""

    detected: bool
    confidence: float
    evidence: list[str]
    version: str | None
    has_core: bool
    has_community: bool
    provider_integrations: list[str]


def detect_langchain_import() -> tuple[bool, str | None]:
    """Check if langchain is importable and get version.

    Returns:
        (is_installed, version_string)

    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        spec = importlib.util.find_spec("langchain")

    if spec is None:
        return False, None

    try:
        import langchain

        version = getattr(langchain, "__version__", None)
        return True, version
    except Exception as e:
        log.debug("langchain import failed: %s", e)
        return False, None


def detect_langchain_core() -> bool:
    """Check if langchain_core is importable."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        spec = importlib.util.find_spec("langchain_core")
    return spec is not None


def detect_langchain_community() -> bool:
    """Check if langchain_community is importable."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        spec = importlib.util.find_spec("langchain_community")
    return spec is not None


def detect_provider_integrations() -> list[str]:
    """Detect importable LangChain provider integrations.

    Returns list of detected provider package names.
    """
    providers = [
        "langchain_openai",
        "langchain_anthropic",
        "langchain_google_genai",
        "langchain_cohere",
        "langchain_mistralai",
        "langchain_together",
        "langchain_groq",
        "langchain_fireworks",
        "langchain_huggingface",
    ]

    detected = []
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        for provider in providers:
            spec = importlib.util.find_spec(provider)
            if spec is not None:
                detected.append(provider)

    return detected


def scan_workspace_for_langchain(workspace: Path) -> list[str]:
    """Scan workspace for LangChain usage patterns.

    Returns list of evidence (file paths with LangChain imports).
    """
    evidence = []

    # Check for common LangChain import patterns
    patterns = [
        "from langchain",
        "import langchain",
        "from langchain_core",
        "from langchain_community",
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
                if "langchain" in content.lower():
                    evidence.append(req_file)
            except Exception as e:
                log.debug("Failed to read %s: %s", req_path, e)

    return evidence


def detect_langchain(workspace: Path) -> LangChainDetectionResult:
    """Detect LangChain usage in workspace.

    Phase 26 T1: Import-only probe, no code execution.

    Returns:
        LangChainDetectionResult with detection status, confidence, and evidence.

    """
    # Check import availability
    has_langchain, version = detect_langchain_import()
    has_core = detect_langchain_core()
    has_community = detect_langchain_community()
    provider_integrations = detect_provider_integrations()

    # Scan workspace for usage
    workspace_evidence = scan_workspace_for_langchain(workspace)

    # Build evidence list
    evidence = []
    if has_langchain:
        evidence.append(f"langchain installed (version: {version or 'unknown'})")
    if has_core:
        evidence.append("langchain_core installed")
    if has_community:
        evidence.append("langchain_community installed")
    for provider in provider_integrations:
        evidence.append(f"{provider} installed")

    evidence.extend(workspace_evidence)

    # Calculate confidence
    detected = False
    confidence = 0.0

    if has_langchain or has_core:
        detected = True
        confidence = 0.3  # Base confidence for having the library

        if workspace_evidence:
            confidence += 0.4  # Boost for actual usage in workspace

        if has_core and has_community:
            confidence += 0.1  # Boost for complete installation

        if provider_integrations:
            confidence += 0.2  # Boost for provider integrations

        # Cap at 1.0
        confidence = min(confidence, 1.0)

    return LangChainDetectionResult(
        detected=detected,
        confidence=confidence,
        evidence=evidence,
        version=version,
        has_core=has_core,
        has_community=has_community,
        provider_integrations=provider_integrations,
    )
