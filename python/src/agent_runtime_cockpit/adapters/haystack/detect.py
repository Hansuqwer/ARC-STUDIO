"""Haystack detection logic.

Detects Haystack usage via import probes and workspace file scanning.
Phase 31: Detection only (no execution).
"""

from __future__ import annotations

import importlib.util
import logging
import warnings
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class HaystackDetectionResult(NamedTuple):
    """Result of Haystack detection probe."""

    detected: bool
    confidence: float
    evidence: list[str]
    version: str | None
    has_pipelines: bool
    has_components: bool
    has_yaml_pipelines: bool


def detect_haystack_import() -> tuple[bool, str | None]:
    """Check if haystack is importable and get version.

    Returns:
        (is_installed, version_string)

    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        spec = importlib.util.find_spec("haystack")

    if spec is None:
        return False, None

    try:
        import haystack

        version = getattr(haystack, "__version__", None)
        return True, version
    except Exception as e:
        log.debug("haystack import failed: %s", e)
        return False, None


def scan_workspace_for_haystack(
    workspace: Path,
) -> tuple[list[str], bool, bool, bool]:
    """Scan workspace for Haystack usage patterns.

    Returns:
        (evidence_list, has_pipelines, has_components, has_yaml_pipelines)

    """
    evidence = []
    has_pipelines = False
    has_components = False
    has_yaml_pipelines = False

    import_patterns = [
        "import haystack",
        "from haystack",
        "from haystack.components",
        "from haystack.core",
    ]

    pipeline_patterns = [
        "Pipeline()",
        "Pipeline.from_dict",
        "Pipeline.from_yaml",
        ".add_component(",
        ".connect(",
    ]

    component_patterns = [
        "@component",
        "from haystack import component",
        "from haystack.core.component import component",
        "@component.output_types",
    ]

    for py_file in workspace.rglob("*.py"):
        if ".venv" in py_file.parts or "venv" in py_file.parts:
            continue
        if "node_modules" in py_file.parts:
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")

            has_import = False
            for pattern in import_patterns:
                if pattern in content:
                    has_import = True
                    break

            if not has_import:
                continue

            rel_path = py_file.relative_to(workspace)
            evidence.append(str(rel_path))

            for pattern in pipeline_patterns:
                if pattern in content:
                    has_pipelines = True
                    break

            for pattern in component_patterns:
                if pattern in content:
                    has_components = True
                    break

        except Exception as e:
            log.debug("Failed to read %s: %s", py_file, e)

    for yaml_file in workspace.rglob("*.yaml"):
        if ".venv" in yaml_file.parts or "venv" in yaml_file.parts:
            continue
        try:
            content = yaml_file.read_text(encoding="utf-8", errors="ignore")
            if "haystack" in content.lower() and "components" in content.lower():
                has_yaml_pipelines = True
                rel_path = yaml_file.relative_to(workspace)
                evidence.append(str(rel_path))
        except Exception as e:
            log.debug("Failed to read %s: %s", yaml_file, e)

    for yml_file in workspace.rglob("*.yml"):
        if ".venv" in yml_file.parts or "venv" in yml_file.parts:
            continue
        try:
            content = yml_file.read_text(encoding="utf-8", errors="ignore")
            if "haystack" in content.lower() and "components" in content.lower():
                has_yaml_pipelines = True
                rel_path = yml_file.relative_to(workspace)
                evidence.append(str(rel_path))
        except Exception as e:
            log.debug("Failed to read %s: %s", yml_file, e)

    req_files = ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
    for req_file in req_files:
        req_path = workspace / req_file
        if req_path.exists():
            try:
                content = req_path.read_text(encoding="utf-8", errors="ignore")
                if "haystack-ai" in content.lower() or "farm-haystack" in content.lower():
                    evidence.append(req_file)
            except Exception as e:
                log.debug("Failed to read %s: %s", req_path, e)

    return evidence, has_pipelines, has_components, has_yaml_pipelines


def detect_haystack(workspace: Path) -> HaystackDetectionResult:
    """Detect Haystack usage in workspace.

    Phase 31: Import-only probe, no code execution.

    Returns:
        HaystackDetectionResult with detection status, confidence, and evidence.

    """
    has_haystack, version = detect_haystack_import()

    workspace_evidence, has_pipelines, has_components, has_yaml_pipelines = (
        scan_workspace_for_haystack(workspace)
    )

    evidence = []
    if has_haystack:
        evidence.append(f"haystack installed (version: {version or 'unknown'})")

    evidence.extend(workspace_evidence)

    detected = False
    confidence = 0.0

    if has_haystack:
        detected = True
        confidence = 0.3

        if workspace_evidence:
            confidence += 0.3

        if has_pipelines:
            confidence += 0.15

        if has_components:
            confidence += 0.15

        if has_yaml_pipelines:
            confidence += 0.1

        confidence = min(confidence, 1.0)

    elif workspace_evidence:
        detected = True
        confidence = 0.2

        if has_pipelines:
            confidence += 0.15

        if has_components:
            confidence += 0.15

        if has_yaml_pipelines:
            confidence += 0.1

        confidence = min(confidence, 1.0)

    return HaystackDetectionResult(
        detected=detected,
        confidence=confidence,
        evidence=evidence,
        version=version,
        has_pipelines=has_pipelines,
        has_components=has_components,
        has_yaml_pipelines=has_yaml_pipelines,
    )
