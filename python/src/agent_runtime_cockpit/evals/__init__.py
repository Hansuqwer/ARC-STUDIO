"""ARC Evaluation Framework — diff, compare, golden trace, artifacts, consensus."""

from .artifact import EvalArtifact, EvalArtifactStore, build_artifact, build_inspect_export
from .consensus import (
    ConsensusEvalComparison,
    ConsensusEvalConfig,
    ConsensusEvalResult,
    compare_protocols,
    run_consensus_eval,
)
from .diff import RunDiff, diff_runs
from .golden import EvalResult, GoldenTrace, eval_run

__all__ = [
    "RunDiff",
    "diff_runs",
    "GoldenTrace",
    "EvalResult",
    "eval_run",
    "EvalArtifact",
    "EvalArtifactStore",
    "build_artifact",
    "build_inspect_export",
    "ConsensusEvalConfig",
    "ConsensusEvalResult",
    "ConsensusEvalComparison",
    "run_consensus_eval",
    "compare_protocols",
]
