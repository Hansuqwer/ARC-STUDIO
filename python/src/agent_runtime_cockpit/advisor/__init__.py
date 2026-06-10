"""ARC Advisor — local token cost optimization advisor (R94).

Analyzes usage history and recommends cost-saving strategies:
- Model switch (cheaper model for similar quality)
- Context compression (reduce prompt size)
- Caching (reuse repeated prompts)
- Batching (combine multiple requests)

All analysis is local and deterministic. No provider calls.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..optimizer.local import KNOWN_PRICING, ModelPricing

log = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    run_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Recommendation:
    strategy: str
    description: str
    estimated_savings_usd: float
    estimated_savings_percent: float
    confidence: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdvisorReport:
    total_runs: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    recommendations: list[Recommendation]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "total_cost_usd": self.total_cost_usd,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "recommendations": [
                {
                    "strategy": r.strategy,
                    "description": r.description,
                    "estimated_savings_usd": r.estimated_savings_usd,
                    "estimated_savings_percent": r.estimated_savings_percent,
                    "confidence": r.confidence,
                    "details": r.details,
                }
                for r in self.recommendations
            ],
            "generated_at": self.generated_at,
        }


class CostAdvisor:
    """Analyzes usage history and generates cost-saving recommendations."""

    def __init__(self, pricing: Optional[dict[str, ModelPricing]] = None) -> None:
        self._pricing = pricing or KNOWN_PRICING

    def load_usage_from_traces(self, workspace: Path, limit: int = 100) -> list[UsageRecord]:
        """Load usage records from workspace trace files."""
        traces_dir = workspace / ".arc" / "traces"
        if not traces_dir.exists():
            return []

        records = []
        for trace_file in sorted(traces_dir.glob("*.jsonl"), reverse=True)[:limit]:
            try:
                with open(trace_file, encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get("type") == "run_complete":
                            run_data = data.get("data", {})
                            records.append(
                                UsageRecord(
                                    run_id=run_data.get("run_id", trace_file.stem),
                                    model=run_data.get("model", "gpt-4"),
                                    input_tokens=run_data.get("input_tokens", 0),
                                    output_tokens=run_data.get("output_tokens", 0),
                                    cost_usd=run_data.get("cost_usd", 0.0),
                                    timestamp=run_data.get("timestamp", ""),
                                )
                            )
            except Exception as e:
                log.debug("Failed to parse trace %s: %s", trace_file, e)
                continue

        return records

    def analyze(self, records: list[UsageRecord]) -> AdvisorReport:
        """Analyze usage records and generate recommendations."""
        if not records:
            return AdvisorReport(
                total_runs=0,
                total_cost_usd=0.0,
                total_input_tokens=0,
                total_output_tokens=0,
                recommendations=[],
            )

        total_cost = sum(r.cost_usd for r in records)
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)

        recommendations = []
        recommendations.extend(self._recommend_model_switch(records, total_cost))
        recommendations.extend(self._recommend_context_compression(records, total_cost))
        recommendations.extend(self._recommend_caching(records, total_cost))
        recommendations.extend(self._recommend_batching(records, total_cost))

        return AdvisorReport(
            total_runs=len(records),
            total_cost_usd=total_cost,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            recommendations=recommendations,
        )

    def _recommend_model_switch(
        self, records: list[UsageRecord], total_cost: float
    ) -> list[Recommendation]:
        """Recommend switching to cheaper models where appropriate."""
        recommendations = []
        model_usage: dict[str, list[UsageRecord]] = {}
        for r in records:
            model_usage.setdefault(r.model, []).append(r)

        for model, model_records in model_usage.items():
            if model not in self._pricing:
                continue

            current_pricing = self._pricing[model]
            cheaper_models = [
                (m, p)
                for m, p in self._pricing.items()
                if p.input_per_1k < current_pricing.input_per_1k and m != model
            ]

            if cheaper_models:
                cheapest_model, cheapest_pricing = min(
                    cheaper_models, key=lambda x: x[1].input_per_1k
                )
                model_cost = sum(r.cost_usd for r in model_records)
                potential_savings = model_cost * 0.5
                recommendations.append(
                    Recommendation(
                        strategy="model_switch",
                        description=f"Consider switching from {model} to {cheapest_model} for similar tasks",
                        estimated_savings_usd=potential_savings,
                        estimated_savings_percent=(
                            (potential_savings / total_cost * 100) if total_cost > 0 else 0
                        ),
                        confidence="medium",
                        details={
                            "current_model": model,
                            "suggested_model": cheapest_model,
                            "current_cost_per_1k": current_pricing.input_per_1k,
                            "suggested_cost_per_1k": cheapest_pricing.input_per_1k,
                            "runs_affected": len(model_records),
                        },
                    )
                )

        return recommendations

    def _recommend_context_compression(
        self, records: list[UsageRecord], total_cost: float
    ) -> list[Recommendation]:
        """Recommend context compression for high-token prompts."""
        recommendations = []
        high_token_runs = [r for r in records if r.input_tokens > 5000]

        if high_token_runs:
            total_high_token_cost = sum(r.cost_usd for r in high_token_runs)
            potential_savings = total_high_token_cost * 0.3
            recommendations.append(
                Recommendation(
                    strategy="context_compression",
                    description=f"Compress context for {len(high_token_runs)} runs with >5K input tokens",
                    estimated_savings_usd=potential_savings,
                    estimated_savings_percent=(
                        (potential_savings / total_cost * 100) if total_cost > 0 else 0
                    ),
                    confidence="medium",
                    details={
                        "runs_affected": len(high_token_runs),
                        "avg_input_tokens": sum(r.input_tokens for r in high_token_runs)
                        / len(high_token_runs),
                    },
                )
            )

        return recommendations

    def _recommend_caching(
        self, records: list[UsageRecord], total_cost: float
    ) -> list[Recommendation]:
        """Recommend caching for repeated similar prompts."""
        recommendations = []
        seen_models = set(r.model for r in records)

        if len(records) > 10 and len(seen_models) < len(records) / 2:
            potential_savings = total_cost * 0.2
            recommendations.append(
                Recommendation(
                    strategy="caching",
                    description="Enable prompt caching for repeated similar requests",
                    estimated_savings_usd=potential_savings,
                    estimated_savings_percent=(
                        (potential_savings / total_cost * 100) if total_cost > 0 else 0
                    ),
                    confidence="low",
                    details={
                        "total_runs": len(records),
                        "unique_models": len(seen_models),
                    },
                )
            )

        return recommendations

    def _recommend_batching(
        self, records: list[UsageRecord], total_cost: float
    ) -> list[Recommendation]:
        """Recommend batching for multiple small requests."""
        recommendations = []
        small_runs = [r for r in records if r.input_tokens < 500]

        if len(small_runs) > len(records) * 0.5:
            potential_savings = total_cost * 0.15
            recommendations.append(
                Recommendation(
                    strategy="batching",
                    description=f"Batch {len(small_runs)} small requests (<500 tokens) into larger calls",
                    estimated_savings_usd=potential_savings,
                    estimated_savings_percent=(
                        (potential_savings / total_cost * 100) if total_cost > 0 else 0
                    ),
                    confidence="low",
                    details={
                        "small_runs": len(small_runs),
                        "total_runs": len(records),
                    },
                )
            )

        return recommendations

    def simulate(
        self,
        records: list[UsageRecord],
        strategy: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Simulate a cost-saving strategy and return projected savings."""
        params = params or {}
        total_cost = sum(r.cost_usd for r in records)

        if strategy == "model_switch":
            target_model = params.get("target_model", "gpt-4o-mini")
            if target_model not in self._pricing:
                return {"error": f"Unknown model: {target_model}"}

            target_pricing = self._pricing[target_model]
            projected_cost = 0.0
            for r in records:
                if r.model in self._pricing:
                    current_pricing = self._pricing[r.model]
                    ratio = target_pricing.input_per_1k / current_pricing.input_per_1k
                    projected_cost += r.cost_usd * ratio
                else:
                    projected_cost += r.cost_usd

            savings = total_cost - projected_cost
            return {
                "strategy": "model_switch",
                "target_model": target_model,
                "current_cost_usd": total_cost,
                "projected_cost_usd": projected_cost,
                "savings_usd": savings,
                "savings_percent": (savings / total_cost * 100) if total_cost > 0 else 0,
            }

        elif strategy == "context_compression":
            compression_ratio = params.get("compression_ratio", 0.3)
            high_token_runs = [r for r in records if r.input_tokens > 5000]
            high_token_cost = sum(r.cost_usd for r in high_token_runs)
            savings = high_token_cost * compression_ratio
            return {
                "strategy": "context_compression",
                "compression_ratio": compression_ratio,
                "runs_affected": len(high_token_runs),
                "current_cost_usd": total_cost,
                "savings_usd": savings,
                "savings_percent": (savings / total_cost * 100) if total_cost > 0 else 0,
            }

        elif strategy == "caching":
            cache_hit_rate = params.get("cache_hit_rate", 0.2)
            savings = total_cost * cache_hit_rate
            return {
                "strategy": "caching",
                "cache_hit_rate": cache_hit_rate,
                "current_cost_usd": total_cost,
                "savings_usd": savings,
                "savings_percent": (savings / total_cost * 100) if total_cost > 0 else 0,
            }

        elif strategy == "batching":
            batch_efficiency = params.get("batch_efficiency", 0.15)
            small_runs = [r for r in records if r.input_tokens < 500]
            small_run_cost = sum(r.cost_usd for r in small_runs)
            savings = small_run_cost * batch_efficiency
            return {
                "strategy": "batching",
                "batch_efficiency": batch_efficiency,
                "small_runs": len(small_runs),
                "current_cost_usd": total_cost,
                "savings_usd": savings,
                "savings_percent": (savings / total_cost * 100) if total_cost > 0 else 0,
            }

        return {"error": f"Unknown strategy: {strategy}"}


__all__ = [
    "UsageRecord",
    "Recommendation",
    "AdvisorReport",
    "CostAdvisor",
]
