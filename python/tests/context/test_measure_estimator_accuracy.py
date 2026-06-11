from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_script():
    root = Path(__file__).resolve().parents[3]
    script = root / "scripts" / "research" / "measure_estimator_accuracy.py"
    spec = importlib.util.spec_from_file_location("measure_estimator_accuracy", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_summary_marks_small_single_category_corpus_not_representative() -> None:
    module = _load_script()
    rows = [
        {
            "category": "prose",
            "rel_error_pct": 12.5,
        }
    ]
    summary = module._summary(rows, requested_samples=100, corpus_size=1)
    assert summary["status"] == "measured"
    assert summary["measured_samples"] == 1
    assert summary["categories_seen"] == ["prose"]


def test_deferred_writes_stable_json_summary(tmp_path, capsys) -> None:
    module = _load_script()
    out = tmp_path / "summary.json"
    rc = module._deferred("deferred", "no trace corpus", json_output=True, summary_out=out)
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload == {"status": "deferred", "reason": "no trace corpus"}
    assert '"status": "deferred"' in capsys.readouterr().out
