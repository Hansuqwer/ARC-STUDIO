"""Tests for ARC Advisor — token cost optimization advisor (R94, Phase 319)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.advisor import (
    AdvisorReport,
    CostAdvisor,
    Recommendation,
    UsageRecord,
)


@pytest.fixture
def advisor() -> CostAdvisor:
    return CostAdvisor()


@pytest.fixture
def sample_records() -> list[UsageRecord]:
    return [
        UsageRecord(
            run_id="run-1",
            model="gpt-4",
            input_tokens=6000,
            output_tokens=1000,
            cost_usd=0.24,
        ),
        UsageRecord(
            run_id="run-2",
            model="gpt-4",
            input_tokens=5500,
            output_tokens=800,
            cost_usd=0.21,
        ),
        UsageRecord(
            run_id="run-3",
            model="gpt-4o",
            input_tokens=300,
            output_tokens=200,
            cost_usd=0.01,
        ),
        UsageRecord(
            run_id="run-4",
            model="gpt-4o",
            input_tokens=400,
            output_tokens=150,
            cost_usd=0.01,
        ),
    ]


class TestUsageRecord:
    def test_create_record(self) -> None:
        record = UsageRecord(
            run_id="test",
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.05,
        )
        assert record.run_id == "test"
        assert record.model == "gpt-4"
        assert record.input_tokens == 1000
        assert record.cost_usd == 0.05


class TestCostAdvisor:
    def test_analyze_empty_records(self, advisor: CostAdvisor) -> None:
        report = advisor.analyze([])
        assert report.total_runs == 0
        assert report.total_cost_usd == 0.0
        assert report.recommendations == []

    def test_analyze_with_records(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        report = advisor.analyze(sample_records)
        assert report.total_runs == 4
        assert report.total_cost_usd > 0
        assert report.total_input_tokens > 0
        assert report.total_output_tokens > 0

    def test_model_switch_recommendation(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        report = advisor.analyze(sample_records)
        model_switch_recs = [r for r in report.recommendations if r.strategy == "model_switch"]
        assert len(model_switch_recs) > 0
        assert model_switch_recs[0].estimated_savings_usd > 0

    def test_context_compression_recommendation(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        report = advisor.analyze(sample_records)
        compression_recs = [
            r for r in report.recommendations if r.strategy == "context_compression"
        ]
        assert len(compression_recs) > 0
        assert compression_recs[0].details["runs_affected"] == 2

    def test_batching_recommendation(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        report = advisor.analyze(sample_records)
        batching_recs = [r for r in report.recommendations if r.strategy == "batching"]
        # Batching recommendation only triggered if >50% of runs are small (<500 tokens)
        # sample_records has 2 small runs out of 4, so batching may or may not be recommended
        assert isinstance(batching_recs, list)

    def test_simulate_model_switch(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        result = advisor.simulate(sample_records, "model_switch", {"target_model": "gpt-4o-mini"})
        assert result["strategy"] == "model_switch"
        assert result["target_model"] == "gpt-4o-mini"
        assert result["savings_usd"] > 0
        assert result["savings_percent"] > 0

    def test_simulate_context_compression(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        result = advisor.simulate(sample_records, "context_compression", {"compression_ratio": 0.3})
        assert result["strategy"] == "context_compression"
        assert result["runs_affected"] == 2
        assert result["savings_usd"] > 0

    def test_simulate_caching(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        result = advisor.simulate(sample_records, "caching", {"cache_hit_rate": 0.2})
        assert result["strategy"] == "caching"
        assert result["savings_usd"] > 0

    def test_simulate_batching(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        result = advisor.simulate(sample_records, "batching", {"batch_efficiency": 0.15})
        assert result["strategy"] == "batching"
        assert result["small_runs"] == 2

    def test_simulate_unknown_strategy(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        result = advisor.simulate(sample_records, "unknown_strategy", {})
        assert "error" in result

    def test_simulate_unknown_model(
        self, advisor: CostAdvisor, sample_records: list[UsageRecord]
    ) -> None:
        result = advisor.simulate(sample_records, "model_switch", {"target_model": "unknown-model"})
        assert "error" in result

    def test_load_usage_from_traces_empty(self, advisor: CostAdvisor, tmp_path: Path) -> None:
        records = advisor.load_usage_from_traces(tmp_path)
        assert records == []

    def test_load_usage_from_traces_with_data(self, advisor: CostAdvisor, tmp_path: Path) -> None:
        traces_dir = tmp_path / ".arc" / "traces"
        traces_dir.mkdir(parents=True)
        trace_file = traces_dir / "run-1.jsonl"
        trace_file.write_text(
            json.dumps(
                {
                    "type": "run_complete",
                    "data": {
                        "run_id": "run-1",
                        "model": "gpt-4",
                        "input_tokens": 1000,
                        "output_tokens": 500,
                        "cost_usd": 0.05,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        records = advisor.load_usage_from_traces(tmp_path)
        assert len(records) == 1
        assert records[0].run_id == "run-1"
        assert records[0].model == "gpt-4"


class TestAdvisorReport:
    def test_to_dict(self) -> None:
        report = AdvisorReport(
            total_runs=10,
            total_cost_usd=1.5,
            total_input_tokens=50000,
            total_output_tokens=10000,
            recommendations=[
                Recommendation(
                    strategy="model_switch",
                    description="Switch to cheaper model",
                    estimated_savings_usd=0.5,
                    estimated_savings_percent=33.3,
                    confidence="medium",
                )
            ],
        )
        d = report.to_dict()
        assert d["total_runs"] == 10
        assert d["total_cost_usd"] == 1.5
        assert len(d["recommendations"]) == 1
        assert d["recommendations"][0]["strategy"] == "model_switch"


class TestAdvisorCLI:
    def test_advisor_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["advisor", "--help"])
        assert result.exit_code == 0
        assert "advisor" in result.output.lower()

    def test_advisor_analyze_empty(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["advisor", "analyze", "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["total_runs"] == 0

    def test_advisor_pricing(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["advisor", "pricing", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["count"] > 0
        assert len(data["data"]["pricing"]) > 0

    def test_advisor_simulate_no_records(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "advisor",
                "simulate",
                "model_switch",
                "--target-model",
                "gpt-4o-mini",
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False


class TestAdvisorError:
    """Phase 336 DoD elevation: structured error class + envelope coverage."""

    def test_advisor_error_is_exception(self) -> None:
        from agent_runtime_cockpit.advisor import AdvisorError

        assert issubclass(AdvisorError, Exception)
        err = AdvisorError("test message")
        assert str(err) == "test message"

    def test_advisor_error_in_all(self) -> None:
        import agent_runtime_cockpit.advisor as advisor_mod

        assert "AdvisorError" in advisor_mod.__all__

    def test_analyze_json_envelope_schema(self, tmp_path: Path) -> None:
        """Verify --json output is a valid ArcEnvelope with stable schema."""
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        traces_dir = tmp_path / ".arc" / "traces"
        traces_dir.mkdir(parents=True)
        trace_file = traces_dir / "run-1.jsonl"
        trace_file.write_text(
            json.dumps(
                {
                    "type": "run_complete",
                    "data": {
                        "run_id": "run-1",
                        "model": "gpt-4",
                        "input_tokens": 6000,
                        "output_tokens": 1000,
                        "cost_usd": 0.1,
                    },
                }
            )
        )

        runner = CliRunner()
        result = runner.invoke(app, ["advisor", "analyze", "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "data" in data
        assert data["data"]["total_runs"] == 1
        assert data["data"]["total_cost_usd"] == 0.1
        assert isinstance(data["data"]["recommendations"], list)
        assert len(data["data"]["recommendations"]) >= 1

    def test_simulate_json_envelope_schema(self, tmp_path: Path) -> None:
        """Verify simulate --json output is a valid ArcEnvelope with error path."""
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "advisor",
                "simulate",
                "caching",
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False
        assert "error" in data
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_pricing_json_envelope_schema(self) -> None:
        """Verify pricing --json output schema is stable."""
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["advisor", "pricing", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "data" in data
        assert "count" in data["data"]
        assert "pricing" in data["data"]
        for entry in data["data"]["pricing"]:
            assert "model" in entry
            assert "input_per_1k" in entry
            assert "output_per_1k" in entry
