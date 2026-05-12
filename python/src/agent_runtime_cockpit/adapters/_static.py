from __future__ import annotations

from pathlib import Path

from ..protocol.schemas import NodeType, WorkflowInfo, WorkflowNode
from ..workspace import iter_workspace_files


def dependency_evidence(workspace: Path, needles: tuple[str, ...]) -> tuple[float, list[str]]:
    score = 0.0
    evidence: list[str] = []
    for req_file in ("pyproject.toml", "requirements.txt", "requirements-dev.txt"):
        path = workspace / req_file
        if not path.exists():
            continue
        try:
            text = path.read_text(errors="ignore").lower()
        except OSError:
            continue
        for needle in needles:
            if needle in text:
                evidence.append(f"{needle} in {req_file}")
                score += 0.8
                break
    return min(score, 1.0), evidence


def import_evidence(workspace: Path, needles: tuple[str, ...]) -> tuple[float, list[str]]:
    score = 0.0
    evidence: list[str] = []
    for py_file in iter_workspace_files(workspace, (".py",))[:40]:
        try:
            text = py_file.read_text(errors="ignore").lower()
        except OSError:
            continue
        if any(needle in text for needle in needles):
            evidence.append(f"import in {py_file.name}")
            score += 0.6
            break
    return min(score, 1.0), evidence


def static_workflow(runtime: str, name: str, workspace: Path, evidence: list[str]) -> list[WorkflowInfo]:
    source = evidence[0] if evidence else None
    return [
        WorkflowInfo(
            id=f"wf-{runtime}-static",
            name=f"{name} static export",
            runtime=runtime,
            source_file=source,
            nodes=[WorkflowNode(id="runtime", label=name, type=NodeType.AGENT)],
            metadata={"workspace": str(workspace), "can_run": False, "export_mode": "static"},
        )
    ]
