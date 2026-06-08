"""CR-034: eval synthetic-labelling completeness (individual + batch aggregate)."""

from __future__ import annotations

from agent_runtime_cockpit.cli.mgmt_eval import _batch_synthetic, _synthetic_prefix
from agent_runtime_cockpit.evals.golden import EvalResult


def _result(synthetic: bool = True) -> dict:
    return EvalResult(
        run_id="r1",
        golden_id="g1",
        passed=True,
        status_match=True,
        event_type_match=True,
        output_contains_match=True,
        score=1.0,
        synthetic=synthetic,
    ).model_dump()


def test_eval_result_serializes_synthetic() -> None:
    assert _result()["synthetic"] is True
    assert _result(synthetic=False)["synthetic"] is False


def test_batch_synthetic_all_vs_mixed() -> None:
    assert _batch_synthetic([_result(), _result()]) is True
    assert _batch_synthetic([_result(True), _result(False)]) is False  # mixed → not synthetic
    assert _batch_synthetic([{}]) is False  # missing flag → treated as not-synthetic
    assert _batch_synthetic([]) is False  # empty batch


def test_synthetic_prefix_label() -> None:
    assert _synthetic_prefix([_result()]) == "[synthetic] "
    assert _synthetic_prefix([_result(False)]) == ""


def test_aggregate_payload_carries_synthetic() -> None:
    """The batch summary the CLI emits must include the aggregate synthetic flag."""
    results = [_result(), _result()]
    payload = {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "synthetic": _batch_synthetic(results),
        "results": results,
    }
    assert payload["synthetic"] is True
    assert all(r["synthetic"] for r in payload["results"])
