"""DSPy detection logic.

Detects DSPy usage via import probes and workspace file scanning.
Phase 30: Detection only (no execution).
"""

from __future__ import annotations

import importlib.util
import logging
import warnings
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class DSPyDetectionResult(NamedTuple):
    """Result of DSPy detection probe."""

    detected: bool
    confidence: float
    evidence: list[str]
    version: str | None
    has_signatures: bool
    has_modules: bool
    has_optimizers: bool


def detect_dspy_import() -> tuple[bool, str | None]:
    """Check if dspy is importable and get version.

    Returns:
        (is_installed, version_string)

    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        spec = importlib.util.find_spec("dspy")

    if spec is None:
        return False, None

    try:
        import dspy

        version = getattr(dspy, "__version__", None)
        return True, version
    except Exception as e:
        log.debug("dspy import failed: %s", e)
        return False, None


def scan_workspace_for_dspy(workspace: Path) -> tuple[list[str], bool, bool, bool]:
    """Scan workspace for DSPy usage patterns.

    Returns:
        (evidence_list, has_signatures, has_modules, has_optimizers)

    """
    evidence = []
    has_signatures = False
    has_modules = False
    has_optimizers = False

    import_patterns = [
        "import dspy",
        "from dspy",
        "import dspy_ai",
        "from dspy_ai",
    ]

    signature_patterns = [
        "dspy.Signature",
        "dspy.InputField",
        "dspy.OutputField",
    ]

    module_patterns = [
        "dspy.Predict",
        "dspy.ChainOfThought",
        "dspy.ReAct",
        "dspy.ProgramOfThought",
        "dspy.Module",
        "dspy.MultiChainComparison",
        "dspy.Parallel",
        "dspy.BestOfN",
        "dspy.Refine",
        "dspy.CodeAct",
    ]

    optimizer_patterns = [
        "dspy.BootstrapFewShot",
        "dspy.MIPROv2",
        "dspy.BootstrapRS",
        "dspy.COPRO",
        "dspy.BootstrapFinetune",
        "dspy.GEPA",
        "dspy.LabeledFewShot",
        "dspy.Ensemble",
        "dspy.BetterTogether",
        "dspy.SIMBA",
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

            for pattern in signature_patterns:
                if pattern in content:
                    has_signatures = True
                    break

            for pattern in module_patterns:
                if pattern in content:
                    has_modules = True
                    break

            for pattern in optimizer_patterns:
                if pattern in content:
                    has_optimizers = True
                    break

        except Exception as e:
            log.debug("Failed to read %s: %s", py_file, e)

    req_files = ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
    for req_file in req_files:
        req_path = workspace / req_file
        if req_path.exists():
            try:
                content = req_path.read_text(encoding="utf-8", errors="ignore")
                if "dspy" in content.lower() or "dspy-ai" in content.lower():
                    evidence.append(req_file)
            except Exception as e:
                log.debug("Failed to read %s: %s", req_path, e)

    return evidence, has_signatures, has_modules, has_optimizers


def detect_dspy(workspace: Path) -> DSPyDetectionResult:
    """Detect DSPy usage in workspace.

    Phase 30: Import-only probe, no code execution.

    Returns:
        DSPyDetectionResult with detection status, confidence, and evidence.

    """
    has_dspy, version = detect_dspy_import()

    workspace_evidence, has_signatures, has_modules, has_optimizers = scan_workspace_for_dspy(
        workspace
    )

    evidence = []
    if has_dspy:
        evidence.append(f"dspy installed (version: {version or 'unknown'})")

    evidence.extend(workspace_evidence)

    detected = False
    confidence = 0.0

    if has_dspy:
        detected = True
        confidence = 0.3

        if workspace_evidence:
            confidence += 0.3

        if has_signatures:
            confidence += 0.15

        if has_modules:
            confidence += 0.15

        if has_optimizers:
            confidence += 0.1

        confidence = min(confidence, 1.0)

    elif workspace_evidence:
        detected = True
        confidence = 0.2

        if has_signatures:
            confidence += 0.15

        if has_modules:
            confidence += 0.15

        if has_optimizers:
            confidence += 0.1

        confidence = min(confidence, 1.0)

    return DSPyDetectionResult(
        detected=detected,
        confidence=confidence,
        evidence=evidence,
        version=version,
        has_signatures=has_signatures,
        has_modules=has_modules,
        has_optimizers=has_optimizers,
    )
