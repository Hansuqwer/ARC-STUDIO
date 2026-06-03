"""Export utilities for RunDiffReport."""

from __future__ import annotations

import json
from pathlib import Path

from .models import RunDiffReport
from .redaction import redact_report


def to_json(report, redact=True, indent=2, exclude_hash=False):
    data = report.model_dump(mode="json")
    if redact:
        data = redact_report(data)
    if exclude_hash:
        data.pop("diff_hash", None)
    return json.dumps(data, indent=indent, sort_keys=False)


def to_dict(report, redact=True):
    data = report.model_dump(mode="json")
    if redact:
        data = redact_report(data)
    return data


def write_json(report, path, redact=True, indent=2):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(to_json(report, redact=redact, indent=indent), encoding="utf-8")


def from_json(json_str):
    data = json.loads(json_str)
    return RunDiffReport.model_validate(data)


def load_report(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Report file not found: {p}")
    return from_json(p.read_text(encoding="utf-8"))


def summary_text(report):
    lines = [
        "=== Run Diff Report ===",
        f"Schema: {report.schema_version}  Mode: {report.mode}",
        f"Left:  {report.left.id} [{report.left.kind.value}]",
        f"Right: {report.right.id} [{report.right.kind.value}]",
        f"Hash:  {report.diff_hash[:16] if report.diff_hash else 'n/a'}...",
        "",
    ]
    s = report.summary
    lines.extend(
        [
            "Summary:",
            f"  Nodes:  +{s.nodes_added} -{s.nodes_removed} ~{s.nodes_changed}",
            f"  Edges:  +{s.edges_added} -{s.edges_removed} ~{s.edges_changed}",
            f"  Events: +{s.events_added} -{s.events_removed} ~{s.events_changed}",
            f"  Policy issues: +{s.policy_issues_added} -{s.policy_issues_removed}",
            f"  Risk increased: {s.risk_increased}",
            f"  HITL removed: {s.hitl_removed}",
            f"  Consensus changed: {s.consensus_changed}",
            f"  Paid call delta: {s.paid_call_delta:+d}",
            f"  Total changes: {s.total_changes}",
        ]
    )
    if report.first_divergence:
        fd = report.first_divergence
        lines.extend(["", f"First divergence ({fd.kind}):", f"  Reason: {fd.reason}"])
        if fd.node_id:
            lines.append(f"  Node:   {fd.node_id}")
    if report.graph_diff:
        gd = report.graph_diff
        if gd.nodes_changed:
            lines.extend(["", "Node changes:"])
            for nd in gd.nodes_changed[:10]:
                reg = " [REGRESSION]" if nd.is_semantic_regression else ""
                lines.append(f"  {nd.node_id}: {nd.change_type}{reg}")
                if nd.risk_delta:
                    lines.append(f"    Risk: {nd.risk_delta}")
                if nd.hitl_delta:
                    lines.append(f"    HITL: {nd.hitl_delta}")
                if nd.consensus_delta:
                    lines.append(f"    Consensus: {nd.consensus_delta}")
                if nd.paid_call_delta is True:
                    lines.append("    Paid call introduced")
    if report.policy_diff:
        pd = report.policy_diff
        if pd.issues_added:
            lines.extend(["", "Policy issues added:"])
            for issue in pd.issues_added[:5]:
                reg = " [REGRESSION]" if issue.is_regression else ""
                lines.append(f"  {issue.rule} ({issue.right_severity}){reg}")
        if pd.can_run_regression:
            lines.extend(["", "  POLICY REGRESSION: can_run changed from True to False"])
    if report.warnings:
        lines.extend(["", "Warnings:"] + [f"  {w}" for w in report.warnings])
    if report.errors:
        lines.extend(["", "Errors:"] + [f"  {e}" for e in report.errors])
    return "\n".join(lines)
