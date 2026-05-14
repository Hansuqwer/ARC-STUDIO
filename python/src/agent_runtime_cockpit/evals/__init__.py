"""ARC Evaluation Framework — diff, compare, golden trace."""
from .diff import RunDiff, diff_runs
from .golden import GoldenTrace, EvalResult, eval_run

__all__ = ["RunDiff", "diff_runs", "GoldenTrace", "EvalResult", "eval_run"]
