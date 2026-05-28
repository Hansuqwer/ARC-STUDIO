"""Tests for consensus protocol evaluation harness (Phase 81 / R52).

All tests are deterministic — no random, no LLM, no network.
"""

from __future__ import annotations

import json

from agent_runtime_cockpit.evals.consensus import (
    ALL_PROTOCOLS,
    ConsensusEvalConfig,
    ConsensusEvalResult,
    compare_protocols,
    run_consensus_eval,
)


# =========================================================================
# Config tests
# =========================================================================


class TestConsensusEvalConfig:
    def test_defaults_are_reasonable(self):
        """Default config should have reasonable values."""
        config = ConsensusEvalConfig()
        assert config.protocols == []
        assert config.num_workers == 4
        assert config.num_rounds == 3
        assert config.synthetic_votes is True
        assert config.consensus_escrow is False

    def test_custom_config(self):
        """Custom config values should be stored correctly."""
        config = ConsensusEvalConfig(
            protocols=["raft", "bft"],
            num_workers=8,
            num_rounds=5,
            synthetic_votes=True,
            consensus_escrow=True,
        )
        assert config.protocols == ["raft", "bft"]
        assert config.num_workers == 8
        assert config.num_rounds == 5

    def test_config_validates_ranges(self):
        """Config should accept edge-case values within bounds."""
        config = ConsensusEvalConfig(num_workers=1, num_rounds=1)
        assert config.num_workers == 1
        assert config.num_rounds == 1


# =========================================================================
# Run eval tests
# =========================================================================


class TestRunConsensusEval:
    def test_run_all_protocols(self):
        """Running eval with no protocol filter should benchmark all protocols."""
        results = run_consensus_eval(ConsensusEvalConfig(num_workers=4, num_rounds=3))
        assert len(results) == len(ALL_PROTOCOLS)
        protocols_found = {r.protocol for r in results}
        expected = {p.value for p in ALL_PROTOCOLS}
        assert protocols_found == expected

    def test_run_single_protocol(self):
        """Running eval for a single protocol should return one result."""
        results = run_consensus_eval(
            ConsensusEvalConfig(protocols=["raft"], num_workers=4, num_rounds=3)
        )
        assert len(results) == 1
        assert results[0].protocol == "raft"

    def test_run_single_protocol_bft_escrow(self):
        """Running eval for bft_escrow should return one result."""
        results = run_consensus_eval(
            ConsensusEvalConfig(protocols=["bft_escrow"], num_workers=4, num_rounds=3)
        )
        assert len(results) == 1
        assert results[0].protocol == "bft_escrow"

    def test_metrics_are_populated(self):
        """All metric fields should have meaningful values."""
        results = run_consensus_eval(ConsensusEvalConfig(num_workers=4, num_rounds=3))
        for r in results:
            assert r.total_votes > 0
            assert r.rounds == 3
            assert r.duration_ms >= 0
            assert 0.0 <= r.quality_score <= 1.0
            assert r.cost_score >= 0
            assert r.latency_ms >= 0
            assert 0.0 <= r.disagreement_rate <= 1.0
            assert 0.0 <= r.escalation_rate <= 1.0

    def test_deterministic_same_votes_same_result(self):
        """Running eval twice with the same config should produce identical results."""
        config = ConsensusEvalConfig(protocols=["majority"], num_workers=4, num_rounds=3)
        r1 = run_consensus_eval(config)
        r2 = run_consensus_eval(config)
        assert r1[0].protocol == r2[0].protocol
        assert r1[0].total_votes == r2[0].total_votes
        assert r1[0].approval_count == r2[0].approval_count
        assert r1[0].quality_score == r2[0].quality_score
        assert r1[0].cost_score == r2[0].cost_score
        assert r1[0].disagreement_rate == r2[0].disagreement_rate

    def test_different_workers_produce_different_votes(self):
        """Different worker counts should produce different vote totals."""
        r_small = run_consensus_eval(
            ConsensusEvalConfig(protocols=["majority"], num_workers=2, num_rounds=3)
        )
        r_large = run_consensus_eval(
            ConsensusEvalConfig(protocols=["majority"], num_workers=10, num_rounds=3)
        )
        assert r_small[0].total_votes < r_large[0].total_votes

    def test_json_output_stable(self):
        """JSON serialization of results should be stable."""
        results = run_consensus_eval(
            ConsensusEvalConfig(protocols=["majority"], num_workers=4, num_rounds=3)
        )
        json_str = json.dumps([r.model_dump() for r in results], sort_keys=True)
        parsed = json.loads(json_str)
        assert len(parsed) == 1
        assert parsed[0]["protocol"] == "majority"
        assert parsed[0]["total_votes"] > 0
        assert "quality_score" in parsed[0]
        assert "cost_score" in parsed[0]
        assert "latency_ms" in parsed[0]
        assert "disagreement_rate" in parsed[0]
        assert "escalation_rate" in parsed[0]
        assert "consensus_reached" in parsed[0]
        assert "approval_count" in parsed[0]
        assert "duration_ms" in parsed[0]

    def test_empty_protocols_list_means_all(self):
        """An empty protocols list should default to benchmarking all protocols."""
        config = ConsensusEvalConfig(protocols=[], num_workers=4, num_rounds=1)
        results = run_consensus_eval(config)
        assert len(results) == len(ALL_PROTOCOLS)

    def test_result_model_validation(self):
        """ConsensusEvalResult should validate field bounds."""
        r = ConsensusEvalResult(
            protocol="majority",
            total_votes=10,
            rounds=3,
            duration_ms=5,
            consensus_reached=True,
            approval_count=7,
            quality_score=0.85,
            cost_score=1500.0,
            latency_ms=1.5,
            disagreement_rate=0.3,
            escalation_rate=0.0,
        )
        assert r.protocol == "majority"
        assert r.total_votes == 10
        assert r.quality_score == 0.85


# =========================================================================
# Comparison tests
# =========================================================================


class TestCompareProtocols:
    def test_comparison_picks_best_protocol(self):
        """Comparison should identify the protocol with the highest composite score."""
        results = run_consensus_eval(ConsensusEvalConfig(num_workers=4, num_rounds=3))
        comparison = compare_protocols(results)
        assert comparison.best_protocol in {p.value for p in ALL_PROTOCOLS}
        assert len(comparison.results) == len(results)
        assert comparison.recommendation

    def test_comparison_ranking_order(self):
        """Results in comparison should be sorted by composite score descending."""
        results = run_consensus_eval(ConsensusEvalConfig(num_workers=4, num_rounds=3))
        comparison = compare_protocols(results)
        # First result should be the best
        assert comparison.results[0].protocol == comparison.best_protocol

    def test_comparison_empty_results(self):
        """Empty results should produce a safe fallback."""
        comparison = compare_protocols([])
        assert comparison.best_protocol == "none"
        assert comparison.recommendation == "No results to compare."

    def test_comparison_model_serialization(self):
        """ConsensusEvalComparison should serialize to JSON stably."""
        results = run_consensus_eval(
            ConsensusEvalConfig(protocols=["majority", "raft"], num_workers=4, num_rounds=2)
        )
        comparison = compare_protocols(results)
        dumped = comparison.model_dump()
        assert "results" in dumped
        assert "best_protocol" in dumped
        assert "recommendation" in dumped
        assert len(dumped["results"]) == 2

    def test_comparison_single_protocol(self):
        """Comparison with a single result should trivially pick that protocol."""
        results = run_consensus_eval(
            ConsensusEvalConfig(protocols=["bft"], num_workers=4, num_rounds=3)
        )
        comparison = compare_protocols(results)
        assert comparison.best_protocol == "bft"
        assert len(comparison.results) == 1


# =========================================================================
# ConsensusEvalResult model tests
# =========================================================================


class TestConsensusEvalResultModel:
    def test_model_defaults(self):
        """Model should have sensible defaults for optional fields."""
        r = ConsensusEvalResult(
            protocol="majority",
            total_votes=0,
            rounds=0,
            duration_ms=0,
            consensus_reached=False,
            approval_count=0,
        )
        assert r.quality_score == 0.0
        assert r.cost_score == 0.0
        assert r.latency_ms == 0.0
        assert r.disagreement_rate == 0.0
        assert r.escalation_rate == 0.0

    def test_model_field_bounds(self):
        """Score fields should enforce 0-1 bounds."""
        from pydantic import ValidationError

        try:
            ConsensusEvalResult(
                protocol="test",
                total_votes=0,
                rounds=0,
                duration_ms=0,
                consensus_reached=False,
                approval_count=0,
                quality_score=1.5,  # Out of bounds
            )
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass

    def test_model_json_roundtrip(self):
        """Model should survive JSON serialization/deserialization."""
        r = ConsensusEvalResult(
            protocol="raft",
            total_votes=12,
            rounds=3,
            duration_ms=15,
            consensus_reached=True,
            approval_count=8,
            quality_score=0.75,
            cost_score=2000.0,
            latency_ms=5.0,
            disagreement_rate=0.25,
            escalation_rate=0.0,
        )
        data = json.loads(r.model_dump_json())
        restored = ConsensusEvalResult.model_validate(data)
        assert restored.protocol == r.protocol
        assert restored.total_votes == r.total_votes
        assert restored.quality_score == r.quality_score
        assert restored.cost_score == r.cost_score
        assert restored.latency_ms == r.latency_ms
        assert restored.disagreement_rate == r.disagreement_rate
        assert restored.escalation_rate == r.escalation_rate


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    def test_single_worker_single_round(self):
        """Minimal config should still produce valid results."""
        results = run_consensus_eval(
            ConsensusEvalConfig(protocols=["majority"], num_workers=1, num_rounds=1)
        )
        assert len(results) == 1
        assert results[0].total_votes == 1
        assert results[0].rounds == 1

    def test_max_workers(self):
        """High worker count should produce valid results."""
        results = run_consensus_eval(
            ConsensusEvalConfig(protocols=["quorum"], num_workers=20, num_rounds=2)
        )
        assert len(results) == 1
        assert results[0].total_votes == 40  # 20 workers * 2 rounds

    def test_all_protocols_get_unique_results(self):
        """Each protocol should get its own result entry."""
        results = run_consensus_eval(ConsensusEvalConfig(num_workers=4, num_rounds=3))
        protocols = [r.protocol for r in results]
        assert len(set(protocols)) == len(protocols)  # All unique
