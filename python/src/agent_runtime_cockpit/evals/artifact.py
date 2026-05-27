"""Eval artifact schema and persistent store (Phase 53).

EvalArtifact captures a single golden-trace evaluation result as a
repeatable, deterministic artifact on disk.

Artifact paths: <workspace>/.arc/evals/<run_id>/<sha256(golden_id)[:12]>.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

EVALS_DIR = ".arc/evals"


class EvalArtifact(BaseModel):
    run_id: str
    golden_id: str
    eval_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pass_count: int = 0
    fail_count: int = 0
    total: int = 0
    pass_rate: float = 0.0
    failures: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _artifact_path(workspace: Path, run_id: str, golden_id: str) -> Path:
    deterministic_id = hashlib.sha256(golden_id.encode()).hexdigest()[:12]
    return workspace / EVALS_DIR / run_id / f"{deterministic_id}.json"


class EvalArtifactStore:
    """Persists and loads EvalArtifacts under .arc/evals/<run_id>/."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    def _run_dir(self, run_id: str) -> Path:
        d = self._workspace / EVALS_DIR / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write(self, artifact: EvalArtifact) -> Path:
        """Write an artifact to disk. Returns the path written."""
        path = _artifact_path(self._workspace, artifact.run_id, artifact.golden_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(artifact.model_dump_json(indent=2))
        return path

    def load(self, run_id: str, golden_id: str) -> Optional[EvalArtifact]:
        """Load an artifact by run_id and golden_id."""
        path = _artifact_path(self._workspace, run_id, golden_id)
        if not path.exists():
            return None
        try:
            return EvalArtifact.model_validate(json.loads(path.read_text()))
        except Exception:
            log.warning("Failed to load eval artifact: %s", path)
            return None

    def list_by_run(self, run_id: str) -> list[EvalArtifact]:
        """List all artifacts for a given run_id."""
        d = self._run_dir(run_id)
        if not d.exists():
            return []
        results: list[EvalArtifact] = []
        for f in sorted(d.iterdir()):
            if f.suffix == ".json":
                try:
                    results.append(EvalArtifact.model_validate(json.loads(f.read_text())))
                except Exception:
                    continue
        return results

    def list_run_ids(self) -> list[str]:
        """List all run IDs that have eval artifacts."""
        base = self._workspace / EVALS_DIR
        if not base.exists():
            return []
        return sorted(p.name for p in base.iterdir() if p.is_dir())

    def prune(self, max_age_days: int = 90) -> int:
        """Remove artifacts older than max_age_days. Returns count removed."""
        base = self._workspace / EVALS_DIR
        if not base.exists():
            return 0
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_days * 86400
        removed = 0
        for run_dir in base.iterdir():
            if not run_dir.is_dir():
                continue
            for f in list(run_dir.iterdir()):
                if f.suffix == ".json" and f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            if list(run_dir.iterdir()) == []:
                shutil.rmtree(run_dir, ignore_errors=True)
        return removed


def build_artifact(
    run_id: str,
    golden_id: str,
    eval_results: list[dict[str, Any]],
) -> EvalArtifact:
    """Build an EvalArtifact from a list of eval result dicts (from eval_run())."""
    pass_count = sum(1 for r in eval_results if r.get("passed"))
    fail_count = sum(1 for r in eval_results if not r.get("passed"))
    total = len(eval_results)
    pass_rate = round(pass_count / total, 4) if total > 0 else 0.0
    failures = [
        f"{r.get('golden_id', '?')}: {r.get('details', '')}"
        for r in eval_results
        if not r.get("passed")
    ]
    return EvalArtifact(
        run_id=run_id,
        golden_id=golden_id,
        pass_count=pass_count,
        fail_count=fail_count,
        total=total,
        pass_rate=pass_rate,
        failures=failures,
    )


def build_inspect_export(run_id: str, artifacts: list[EvalArtifact]) -> dict[str, Any]:
    """Build an Inspect-AI-compatible export shape from eval artifacts."""
    samples: list[dict[str, Any]] = []
    for art in artifacts:
        samples.append(
            {
                "id": art.golden_id,
                "input": {"run_id": art.run_id, "golden_id": art.golden_id},
                "target": {"pass_rate": art.pass_rate, "total": art.total},
                "output": {
                    "pass_count": art.pass_count,
                    "fail_count": art.fail_count,
                    "failures": art.failures,
                },
                "scores": {"pass_rate": art.pass_rate},
            }
        )
    return {
        "version": "1",
        "samples": samples,
    }
