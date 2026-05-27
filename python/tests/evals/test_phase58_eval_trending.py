"""Tests for Phase 58 cross-session eval workflow and trend tracking."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from agent_runtime_cockpit.evals.artifact import (
    EvalArtifact,
    EvalTrending,
    compute_trending,
)
from agent_runtime_cockpit.events.types import EvalCompleted


class TestEvalTrendingModel:
    """EvalTrending model validation."""

    def test_valid_trending(self):
        """EvalTrending creates with valid data."""
        t = EvalTrending(
            run_ids=["r1", "r2"],
            pass_rates=[0.95, 0.87],
            timestamps=["2026-01-01T00:00:00", "2026-01-02T00:00:00"],
            delta_from_baseline=-0.08,
        )
        assert len(t.run_ids) == 2
        assert t.pass_rates[0] == 0.95
        assert t.delta_from_baseline == -0.08

    def test_empty_trending(self):
        """EvalTrending with defaults."""
        t = EvalTrending()
        assert t.run_ids == []
        assert t.pass_rates == []
        assert t.delta_from_baseline == 0.0

    def test_serialization(self):
        """EvalTrending can be serialized to JSON and back."""
        t = EvalTrending(
            run_ids=["r1"],
            pass_rates=[0.9],
            timestamps=["2026-01-01T00:00:00"],
            delta_from_baseline=0.1,
        )
        data = json.loads(t.model_dump_json())
        restored = EvalTrending.model_validate(data)
        assert restored.run_ids == ["r1"]
        assert restored.pass_rates == [0.9]


class TestComputeTrending:
    """compute_trending function."""

    def test_single_run(self):
        """Trending with one run returns correct pass_rate."""
        artifacts = {
            "r1": [
                EvalArtifact(
                    run_id="r1",
                    golden_id="g1",
                    pass_count=8,
                    fail_count=2,
                    total=10,
                    pass_rate=0.8,
                    eval_timestamp="2026-01-01T00:00:00",
                )
            ]
        }
        t = compute_trending(artifacts)
        assert t.run_ids == ["r1"]
        assert t.pass_rates[0] == 0.8

    def test_multiple_runs_delta(self):
        """Trending across runs computes delta correctly."""
        artifacts = {
            "r1": [
                EvalArtifact(
                    run_id="r1",
                    golden_id="g1",
                    pass_count=8,
                    fail_count=2,
                    total=10,
                    pass_rate=0.8,
                    eval_timestamp="2026-01-01T00:00:00",
                )
            ],
            "r2": [
                EvalArtifact(
                    run_id="r2",
                    golden_id="g1",
                    pass_count=9,
                    fail_count=1,
                    total=10,
                    pass_rate=0.9,
                    eval_timestamp="2026-01-02T00:00:00",
                )
            ],
        }
        t = compute_trending(artifacts, baseline_run_id="r1")
        assert len(t.run_ids) == 2
        assert t.run_ids == ["r1", "r2"]
        assert t.pass_rates == [0.8, 0.9]
        assert t.delta_from_baseline == 0.1

    def test_multiple_artifacts_per_run(self):
        """Aggregates multiple artifacts per run."""
        artifacts = {
            "r1": [
                EvalArtifact(
                    run_id="r1",
                    golden_id="g1",
                    pass_count=3,
                    fail_count=1,
                    total=4,
                    pass_rate=0.75,
                ),
                EvalArtifact(
                    run_id="r1",
                    golden_id="g2",
                    pass_count=5,
                    fail_count=1,
                    total=6,
                    pass_rate=0.8333,
                ),
            ]
        }
        t = compute_trending(artifacts)
        # (3+5) / (4+6) = 8/10 = 0.8
        assert t.pass_rates[0] == 0.8

    def test_no_artifacts(self):
        """Empty input returns empty trending."""
        t = compute_trending({})
        assert t.run_ids == []


class TestEvalCompletedEvent:
    """EvalCompleted event type validation."""

    def test_valid_event(self):
        """EvalCompleted creates with valid data."""
        ev = EvalCompleted(run_id="test-run", pass_rate=0.85, total=20, failures_count=3)
        assert ev.event_type == "eval_completed"
        assert ev.run_id == "test-run"
        assert ev.pass_rate == 0.85
        assert ev.total == 20
        assert ev.failures_count == 3

    def test_serialization(self):
        """EvalCompleted serializes to JSON and back."""
        ev = EvalCompleted(run_id="r1", pass_rate=1.0, total=5, failures_count=0)
        data = json.loads(ev.model_dump_json())
        assert data["event_type"] == "eval_completed"
        assert data["run_id"] == "r1"
        assert data["pass_rate"] == 1.0

    def test_in_event_type_map(self):
        """EvalCompleted is in EVENT_TYPE_MAP."""
        from agent_runtime_cockpit.events.types import EVENT_TYPE_MAP, parse_event

        assert "eval_completed" in EVENT_TYPE_MAP
        assert EVENT_TYPE_MAP["eval_completed"] is EvalCompleted

        payload = {
            "event_type": "eval_completed",
            "run_id": "r1",
            "pass_rate": 0.75,
            "total": 10,
            "failures_count": 3,
        }
        parsed = parse_event(payload)
        assert isinstance(parsed, EvalCompleted)
        assert parsed.run_id == "r1"


class TestEvalCLITrending:
    """Smoke tests for eval CLI trending/dashboard commands."""

    @pytest.fixture
    def tmp_evals(self) -> Generator[Path, None, None]:
        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            old = Path.cwd()
            os.chdir(str(cwd))

            # Create eval artifacts
            evals_dir = cwd / ".arc" / "evals" / "r1"
            evals_dir.mkdir(parents=True, exist_ok=True)
            art = EvalArtifact(
                run_id="r1",
                golden_id="g1",
                pass_count=8,
                fail_count=2,
                total=10,
                pass_rate=0.8,
                eval_timestamp="2026-01-01T00:00:00",
            )
            (evals_dir / "abc.json").write_text(art.model_dump_json())

            yield cwd
            os.chdir(str(old))

    def test_cli_trending_json(self, tmp_evals: Path):
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["eval", "trending", "--run-ids", "r1", "--json"])
        assert result.exit_code == 0, f"stderr={result.stderr}"
        data = json.loads(result.stdout)
        assert data.get("ok") is True
        payload = data.get("data", data)
        assert "run_ids" in payload
        assert "pass_rates" in payload

    def test_cli_trending_no_runs(self, tmp_evals: Path):
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["eval", "trending", "--run-ids", "nonexistent", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data.get("ok") is True

    def test_cli_dashboard_json(self, tmp_evals: Path):
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["eval", "dashboard", "--json"])
        assert result.exit_code == 0, f"stderr={result.stderr}"
        data = json.loads(result.stdout)
        assert data.get("ok") is True
        payload = data.get("data", data)
        assert "runs" in payload
        assert payload["count"] >= 1
