"""Phase 64 offline memory evidence-pack tests."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.memory_graph.evidence import create_evidence_pack, evaluate_evidence_pack


def _samples(count: int, *, quality_delta: float = 0.12, cost_delta: float = 0.0) -> list[dict]:
    return [
        {
            "sample_id": f"s{i}",
            "baseline_quality": 1.0,
            "candidate_quality": 1.0 + quality_delta,
            "baseline_cost": 1.0,
            "candidate_cost": 1.0 + cost_delta,
            "reviewed_privacy": True,
            "redaction_applied": True,
            "memory_runtime_injection": False,
        }
        for i in range(count)
    ]


def test_evidence_pack_proceed_on_quality(tmp_path: Path) -> None:
    samples = tmp_path / "samples.json"
    pack_path = tmp_path / "pack.json"
    samples.write_text(json.dumps(_samples(10)), encoding="utf-8")
    pack = create_evidence_pack(samples, pack_path, pack_id="p1")
    assert pack.memory_runtime_injection is False
    report = evaluate_evidence_pack(pack_path)
    assert report.decision == "proceed"
    assert report.valid_sample_count == 10
    assert report.memory_runtime_injection is False


def test_evidence_pack_proceed_on_cost(tmp_path: Path) -> None:
    samples = tmp_path / "samples.json"
    pack_path = tmp_path / "pack.json"
    samples.write_text(
        json.dumps(_samples(10, quality_delta=0.0, cost_delta=-0.25)), encoding="utf-8"
    )
    create_evidence_pack(samples, pack_path, pack_id="p-cost")
    assert evaluate_evidence_pack(pack_path).decision == "proceed"


def test_evidence_pack_insufficient_valid_samples(tmp_path: Path) -> None:
    samples = tmp_path / "samples.json"
    pack_path = tmp_path / "pack.json"
    samples.write_text(json.dumps(_samples(9)), encoding="utf-8")
    create_evidence_pack(samples, pack_path, pack_id="p-small")
    report = evaluate_evidence_pack(pack_path)
    assert report.decision == "insufficient_evidence"
    assert "requires at least 10 valid samples" in "; ".join(report.reasons)


def test_evidence_pack_rejects_unreviewed_or_injection(tmp_path: Path) -> None:
    bad = _samples(10)
    bad[0]["reviewed_privacy"] = False
    bad[1]["redaction_applied"] = False
    bad[2]["memory_runtime_injection"] = True
    pack_path = tmp_path / "pack.json"
    (tmp_path / "samples.json").write_text(json.dumps(bad), encoding="utf-8")
    create_evidence_pack(tmp_path / "samples.json", pack_path, pack_id="p-bad")
    report = evaluate_evidence_pack(pack_path)
    assert report.decision == "insufficient_evidence"
    assert report.valid_sample_count == 7


def test_memory_evidence_cli_create_evaluate_show(tmp_path: Path) -> None:
    samples = tmp_path / "samples.json"
    pack = tmp_path / "pack.json"
    samples.write_text(json.dumps({"samples": _samples(10)}), encoding="utf-8")
    runner = CliRunner()
    created = runner.invoke(
        app,
        [
            "memory",
            "evidence",
            "create",
            "--samples",
            str(samples),
            "--output",
            str(pack),
            "--json",
        ],
    )
    assert created.exit_code == 0, created.stderr
    assert json.loads(created.stdout)["data"]["memory_runtime_injection"] is False
    evaluated = runner.invoke(app, ["memory", "evidence", "evaluate", str(pack), "--json"])
    assert evaluated.exit_code == 0, evaluated.stderr
    assert json.loads(evaluated.stdout)["data"]["decision"] == "proceed"
    shown = runner.invoke(app, ["memory", "evidence", "show", str(pack), "--json"])
    assert shown.exit_code == 0, shown.stderr


def test_memory_evaluate_accepts_evidence_pack(tmp_path: Path) -> None:
    samples = tmp_path / "samples.json"
    pack = tmp_path / "pack.json"
    samples.write_text(json.dumps(_samples(10)), encoding="utf-8")
    create_evidence_pack(samples, pack, pack_id="p-eval")
    result = CliRunner().invoke(app, ["memory", "evaluate", "--evidence-pack", str(pack), "--json"])
    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)["data"]
    assert payload["decision"] == "proceed"
    assert payload["memory_runtime_injection"] is False
