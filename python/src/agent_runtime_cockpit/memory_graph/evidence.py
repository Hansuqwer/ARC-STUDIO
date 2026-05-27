"""Offline memory evidence-pack evaluation.

Evidence packs are research artifacts only. They never enable runtime memory
injection or provider/network calls.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import (
    MemoryEvidencePack,
    MemoryEvidenceReport,
    MemoryEvidenceRunResult,
    MemoryEvidenceSample,
)


def create_evidence_pack(
    samples_path: Path, output_path: Path, *, pack_id: str
) -> MemoryEvidencePack:
    raw = json.loads(samples_path.read_text(encoding="utf-8"))
    samples_raw = raw.get("samples", raw) if isinstance(raw, dict) else raw
    if not isinstance(samples_raw, list):
        raise ValueError("samples file must contain a list or {samples: [...]}")
    pack = MemoryEvidencePack(
        pack_id=pack_id,
        memory_runtime_injection=False,
        samples=[MemoryEvidenceSample.model_validate(item) for item in samples_raw],
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(pack.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return pack


def load_evidence_pack(path: Path) -> MemoryEvidencePack:
    return MemoryEvidencePack.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_evidence_pack(path: Path, *, min_samples: int = 10) -> MemoryEvidenceReport:
    pack = load_evidence_pack(path)
    results: list[MemoryEvidenceRunResult] = []
    valid_quality: list[float] = []
    valid_cost: list[float] = []
    reasons: list[str] = []
    if pack.memory_runtime_injection:
        reasons.append("memory_runtime_injection must be false")
    for sample in pack.samples:
        sample_reasons: list[str] = []
        if sample.memory_runtime_injection:
            sample_reasons.append("sample memory_runtime_injection must be false")
        if not sample.reviewed_privacy:
            sample_reasons.append("privacy not reviewed")
        if not sample.redaction_applied:
            sample_reasons.append("redaction not applied")
        quality_delta = sample.candidate_quality - sample.baseline_quality
        cost_delta = sample.candidate_cost - sample.baseline_cost
        valid = not sample_reasons
        if valid:
            valid_quality.append(quality_delta)
            valid_cost.append(cost_delta)
        results.append(
            MemoryEvidenceRunResult(
                sample_id=sample.sample_id,
                quality_delta=quality_delta,
                cost_delta=cost_delta,
                valid=valid,
                reasons=sample_reasons,
            )
        )
    if len(valid_quality) < min_samples:
        reasons.append(f"requires at least {min_samples} valid samples; found {len(valid_quality)}")
    quality_avg = sum(valid_quality) / len(valid_quality) if valid_quality else None
    cost_avg = sum(valid_cost) / len(valid_cost) if valid_cost else None
    threshold_ok = (quality_avg is not None and quality_avg >= 0.10) or (
        cost_avg is not None and cost_avg <= -0.20
    )
    if len(valid_quality) >= min_samples and not threshold_ok:
        reasons.append("quality/cost thresholds not met")
    if len(valid_quality) < min_samples:
        decision = "insufficient_evidence"
    elif reasons or pack.memory_runtime_injection:
        decision = "no_go"
    else:
        decision = "proceed"
    return MemoryEvidenceReport(
        pack_id=pack.pack_id,
        valid_sample_count=len(valid_quality),
        quality_delta=quality_avg,
        cost_delta=cost_avg,
        memory_runtime_injection=False,
        decision=decision,
        reasons=reasons,
        results=results,
    )
