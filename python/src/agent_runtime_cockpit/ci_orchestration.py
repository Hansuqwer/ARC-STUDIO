"""Local CI matrix detection and sandboxed run models."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .security.sandbox import SandboxDecision, utc_now


class CiJob(BaseModel):
    """One detected CI/test command candidate."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    command: list[str]
    command_display: str
    cwd: str = "."
    source: str
    runner: str
    kind: Literal["python", "node", "workflow", "testbench", "custom"]
    confidence: Literal["high", "medium", "low", "explicit"] = "medium"
    runnable: bool = True
    blocked_reason: str | None = None
    artifacts: list[str] = Field(default_factory=list)


class CiMatrix(BaseModel):
    """Stable CI matrix envelope."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    workspace: str
    generated_at: str = Field(default_factory=utc_now)
    jobs: list[CiJob]
    count: int
    sources: list[str]


class CiRunResult(BaseModel):
    """Stable result for one sandboxed CI job run."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    run_id: str
    job: CiJob
    policy: str
    provider: str = "subprocess"
    status: Literal["passed", "failed", "denied", "cancelled", "timeout", "error"]
    exit_code: int | None = None
    duration_ms: int = 0
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    redaction_applied: bool = False
    summary: str
    decision: SandboxDecision
    audit_event: dict[str, Any]
    artifact_paths: list[str] = Field(default_factory=list)


SAFE_PACKAGE_SCRIPTS = {
    "build",
    "check",
    "check:pr",
    "lint",
    "test",
    "test:e2e",
    "typecheck",
}
SHELL_META_RE = re.compile(r"[|&;<>`$(){}\n]")


def build_ci_matrix(workspace: Path, *, include_workflows: bool = True) -> CiMatrix:
    """Detect local CI/test jobs from repo metadata without executing them."""
    ws = workspace.resolve()
    jobs: list[CiJob] = []
    jobs.extend(_detect_package_jobs(ws))
    jobs.extend(_detect_python_jobs(ws))
    jobs.extend(_detect_testbench_jobs(ws))
    if include_workflows:
        jobs.extend(_detect_workflow_jobs(ws))
    jobs = _dedupe_jobs(jobs)
    jobs.sort(key=lambda job: (job.kind, job.cwd, job.source, job.name, job.id))
    sources = sorted({job.source for job in jobs})
    return CiMatrix(workspace=str(ws), jobs=jobs, count=len(jobs), sources=sources)


def make_custom_ci_job(command: list[str], cwd: str = ".") -> CiJob:
    display = shlex.join(command)
    return CiJob(
        id="custom:" + _short_hash(f"{cwd}\0{display}"),
        name="custom command",
        command=command,
        command_display=display,
        cwd=cwd,
        source="explicit",
        runner=Path(command[0]).name if command else "custom",
        kind="custom",
        confidence="explicit",
    )


def write_ci_run_artifact(workspace: Path, run_id: str, result: CiRunResult) -> Path:
    """Persist one deterministic local CI run artifact."""
    safe_job_id = re.sub(r"[^A-Za-z0-9_.:-]+", "-", result.job.id)[:120]
    target = workspace / ".arc" / "ci" / "runs" / run_id / f"{safe_job_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


def _detect_package_jobs(workspace: Path) -> list[CiJob]:
    jobs: list[CiJob] = []
    for pkg_path in _package_json_paths(workspace):
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        scripts = pkg.get("scripts", {})
        if not isinstance(scripts, dict):
            continue
        cwd = _rel_cwd(pkg_path.parent, workspace)
        pm = _package_manager(workspace, pkg)
        package_name = str(pkg.get("name") or pkg_path.parent.name)
        for script_name in sorted(SAFE_PACKAGE_SCRIPTS & set(scripts)):
            command = [pm, script_name]
            display = shlex.join(command)
            jobs.append(
                CiJob(
                    id=_job_id("pkg", cwd, script_name, display),
                    name=f"{package_name}:{script_name}",
                    command=command,
                    command_display=display,
                    cwd=cwd,
                    source=str(pkg_path.relative_to(workspace)),
                    runner=pm,
                    kind="node",
                    confidence="high",
                )
            )
    return jobs


def _detect_python_jobs(workspace: Path) -> list[CiJob]:
    jobs: list[CiJob] = []
    for pyproject in sorted(workspace.glob("**/pyproject.toml")):
        if _ignored(pyproject):
            continue
        cwd = _rel_cwd(pyproject.parent, workspace)
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        if "[tool.ruff" in text:
            jobs.append(
                _simple_job(
                    "py",
                    cwd,
                    "ruff",
                    ["uv", "run", "ruff", "check", "src", "tests"],
                    pyproject,
                    workspace,
                )
            )
        if "[tool.pytest" in text or (pyproject.parent / "tests").is_dir():
            jobs.append(
                _simple_job(
                    "py",
                    cwd,
                    "pytest",
                    ["uv", "run", "pytest", "tests/", "-q"],
                    pyproject,
                    workspace,
                )
            )
        if "[tool.mypy" in text:
            jobs.append(
                _simple_job("py", cwd, "mypy", ["uv", "run", "mypy", "."], pyproject, workspace)
            )
    return jobs


def _detect_testbench_jobs(workspace: Path) -> list[CiJob]:
    try:
        from .cli.testbench import _detect_commands
    except Exception:
        return []
    jobs: list[CiJob] = []
    for item in _detect_commands(workspace):
        command_display = str(item.get("command") or "").strip()
        if not command_display:
            continue
        command, runnable, reason = _argv_from_display(command_display)
        cwd = str(item.get("cwd") or ".")
        jobs.append(
            CiJob(
                id=_job_id("testbench", cwd, str(item.get("runner") or "job"), command_display),
                name=f"testbench:{item.get('runner') or 'job'}:{cwd}",
                command=command,
                command_display=command_display,
                cwd=cwd,
                source=f"testbench:{item.get('source') or 'unknown'}",
                runner=str(item.get("runner") or "custom"),
                kind="testbench",
                confidence=str(item.get("confidence") or "medium"),
                runnable=runnable,
                blocked_reason=reason,
            )
        )
    return jobs


def _detect_workflow_jobs(workspace: Path) -> list[CiJob]:
    jobs: list[CiJob] = []
    workflow_dir = workspace / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return jobs
    for workflow_path in sorted(
        list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
    ):
        try:
            import yaml

            workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        workflow_jobs = workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
        if not isinstance(workflow_jobs, dict):
            continue
        for job_name, job_def in workflow_jobs.items():
            if not isinstance(job_def, dict):
                continue
            for step_index, step in enumerate(job_def.get("steps", []) or []):
                if not isinstance(step, dict) or "run" not in step:
                    continue
                step_name = str(step.get("name") or f"step-{step_index + 1}")
                cwd = str(step.get("working-directory") or ".")
                for line_index, line in enumerate(str(step["run"]).splitlines()):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    command, runnable, reason = _argv_from_display(line)
                    source = str(workflow_path.relative_to(workspace))
                    jobs.append(
                        CiJob(
                            id=_job_id("gha", str(job_name), f"{step_index}-{line_index}", line),
                            name=f"{workflow_path.stem}:{job_name}:{step_name}",
                            command=command,
                            command_display=line,
                            cwd=cwd,
                            source=source,
                            runner=command[0] if command else "workflow",
                            kind="workflow",
                            confidence="medium" if runnable else "low",
                            runnable=runnable,
                            blocked_reason=reason,
                        )
                    )
    return jobs


def _package_json_paths(workspace: Path) -> list[Path]:
    paths = [workspace / "package.json"]
    pnpm_workspace = workspace / "pnpm-workspace.yaml"
    if pnpm_workspace.is_file():
        try:
            import yaml

            data = yaml.safe_load(pnpm_workspace.read_text(encoding="utf-8")) or {}
            for pattern in data.get("packages", []) or []:
                if isinstance(pattern, str):
                    paths.extend(p / "package.json" for p in workspace.glob(pattern))
        except Exception:
            pass
    try:
        root_pkg = json.loads((workspace / "package.json").read_text(encoding="utf-8"))
        workspaces = root_pkg.get("workspaces")
        if isinstance(workspaces, dict):
            workspaces = workspaces.get("packages", [])
        if isinstance(workspaces, list):
            for pattern in workspaces:
                if isinstance(pattern, str):
                    paths.extend(p / "package.json" for p in workspace.glob(pattern))
    except Exception:
        pass
    return sorted({p.resolve() for p in paths if p.is_file() and not _ignored(p)})


def _package_manager(workspace: Path, pkg: dict[str, Any]) -> str:
    field = str(pkg.get("packageManager") or "").split("@")[0]
    if field in {"pnpm", "yarn", "npm"}:
        return field
    if (workspace / "pnpm-lock.yaml").exists() or (workspace / "pnpm-workspace.yaml").exists():
        return "pnpm"
    if (workspace / "yarn.lock").exists():
        return "yarn"
    return "npm"


def _simple_job(
    prefix: str, cwd: str, name: str, command: list[str], source_path: Path, workspace: Path
) -> CiJob:
    display = shlex.join(command)
    return CiJob(
        id=_job_id(prefix, cwd, name, display),
        name=f"python:{name}:{cwd}",
        command=command,
        command_display=display,
        cwd=cwd,
        source=str(source_path.relative_to(workspace)),
        runner=command[0],
        kind="python",
        confidence="high",
    )


def _argv_from_display(command_display: str) -> tuple[list[str], bool, str | None]:
    if SHELL_META_RE.search(command_display):
        return ["sh", "-lc", command_display], False, "shell syntax requires explicit shell support"
    try:
        argv = shlex.split(command_display)
    except ValueError as exc:
        return ["sh", "-lc", command_display], False, str(exc)
    if not argv:
        return [], False, "empty command"
    return argv, True, None


def _dedupe_jobs(jobs: list[CiJob]) -> list[CiJob]:
    seen: set[tuple[str, str, str]] = set()
    result: list[CiJob] = []
    for job in jobs:
        key = (job.cwd, job.command_display, job.source)
        if key in seen:
            continue
        seen.add(key)
        result.append(job)
    return result


def _rel_cwd(path: Path, workspace: Path) -> str:
    try:
        rel = path.resolve().relative_to(workspace.resolve())
    except ValueError:
        return str(path)
    return "." if str(rel) == "." else str(rel)


def _ignored(path: Path) -> bool:
    ignored = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
    return any(part in ignored for part in path.parts)


def _job_id(prefix: str, cwd: str, name: str, command_display: str) -> str:
    safe_cwd = re.sub(r"[^A-Za-z0-9_.:-]+", "-", cwd).strip("-") or "root"
    safe_name = re.sub(r"[^A-Za-z0-9_.:-]+", "-", name).strip("-") or "job"
    return f"{prefix}:{safe_cwd}:{safe_name}:{_short_hash(command_display)}"


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
