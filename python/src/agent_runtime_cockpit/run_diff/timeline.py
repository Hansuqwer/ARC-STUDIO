"""Timeline generation for Run Diff / Time Travel."""

from __future__ import annotations

import hashlib

from .models import ChangeType, TimelineFrame


def _frame_id(prefix, sequence):
    return hashlib.sha256(f"{prefix}:{sequence}".encode()).hexdigest()[:16]


def build_timeline_from_run_events(events, subject="run", run_id=None):
    frames = []
    for i, event in enumerate(events):
        frame = TimelineFrame(
            frame_id=_frame_id(subject, i),
            sequence=event.sequence,
            timestamp=event.timestamp,
            subject=subject,
            event_type=event.type,
            summary=f"{event.type} @ seq={event.sequence}",
            left_label=None,
            right_label=None,
            change_type=ChangeType.UNCHANGED,
            left_value=event.model_dump(mode="json") if event else None,
            right_value=None,
            redacted=False,
            redacted_fields=[],
        )
        frames.append(frame)
    return frames


def build_timeline_from_report(report):
    frames = []
    frame_idx = 0
    if report.first_divergence:
        div = report.first_divergence
        frames.append(
            TimelineFrame(
                frame_id=_frame_id("divergence", 0),
                sequence=div.sequence or 0,
                subject="divergence",
                event_type=div.kind,
                node_id=div.node_id,
                summary=f"FIRST DIVERGENCE: {div.reason}",
                left_label="left",
                right_label="right",
                change_type=ChangeType.CHANGED,
                left_value={"value": div.left_value},
                right_value={"value": div.right_value},
                redacted=False,
            )
        )
        frame_idx += 1
    if report.graph_diff:
        gd = report.graph_diff
        for node_id in gd.nodes_removed:
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("node", frame_idx),
                    sequence=frame_idx,
                    subject="ir",
                    node_id=node_id,
                    summary=f"Node removed: {node_id}",
                    change_type=ChangeType.REMOVED,
                    left_label="left",
                    right_label=None,
                    redacted=False,
                )
            )
            frame_idx += 1
        for node_id in gd.nodes_added:
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("node", frame_idx),
                    sequence=frame_idx,
                    subject="ir",
                    node_id=node_id,
                    summary=f"Node added: {node_id}",
                    change_type=ChangeType.ADDED,
                    left_label=None,
                    right_label="right",
                    redacted=False,
                )
            )
            frame_idx += 1
        for node_diff in gd.nodes_changed:
            reg = " [REGRESSION]" if node_diff.is_semantic_regression else ""
            parts = [f"Node changed: {node_diff.node_id}"]
            if node_diff.risk_delta:
                parts.append(f"Risk: {node_diff.risk_delta}")
            if node_diff.hitl_delta:
                parts.append(f"HITL: {node_diff.hitl_delta}")
            if node_diff.consensus_delta:
                parts.append(f"Consensus: {node_diff.consensus_delta}")
            if node_diff.paid_call_delta is True:
                parts.append("Paid call introduced")
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("node", frame_idx),
                    sequence=frame_idx,
                    subject="ir",
                    node_id=node_diff.node_id,
                    summary="; ".join(parts) + reg,
                    left_label="left",
                    right_label="right",
                    change_type=ChangeType.CHANGED,
                    left_value={"node_id": node_diff.node_id, "risk_delta": node_diff.risk_delta},
                    right_value={"node_id": node_diff.node_id},
                    redacted=False,
                    redacted_fields=[],
                )
            )
            frame_idx += 1
        for edge_id in gd.edges_removed:
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("edge", frame_idx),
                    sequence=frame_idx,
                    subject="ir",
                    summary=f"Edge removed: {edge_id}",
                    change_type=ChangeType.REMOVED,
                    left_label="left",
                    right_label=None,
                    redacted=False,
                )
            )
            frame_idx += 1
        for edge_id in gd.edges_added:
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("edge", frame_idx),
                    sequence=frame_idx,
                    subject="ir",
                    summary=f"Edge added: {edge_id}",
                    change_type=ChangeType.ADDED,
                    left_label=None,
                    right_label="right",
                    redacted=False,
                )
            )
            frame_idx += 1
    if report.event_diff:
        ed = report.event_diff
        for entry in ed.events_removed:
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("event", frame_idx),
                    sequence=entry.sequence or frame_idx,
                    timestamp=entry.timestamp,
                    subject="run",
                    event_type=entry.event_type,
                    summary=f"Event removed: {entry.event_type}",
                    change_type=ChangeType.REMOVED,
                    left_label="left",
                    right_label=None,
                    redacted=False,
                )
            )
            frame_idx += 1
        for entry in ed.events_added:
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("event", frame_idx),
                    sequence=entry.sequence or frame_idx,
                    timestamp=entry.timestamp,
                    subject="run",
                    event_type=entry.event_type,
                    summary=f"Event added: {entry.event_type}",
                    change_type=ChangeType.ADDED,
                    left_label=None,
                    right_label="right",
                    redacted=False,
                )
            )
            frame_idx += 1
        for change in ed.events_changed:
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("event", frame_idx),
                    sequence=change.get("sequence", frame_idx),
                    subject="run",
                    event_type=f"{change.get('left_type', '?')} -> {change.get('right_type', '?')}",
                    summary=f"Event changed: {change.get('left_type', '?')} -> {change.get('right_type', '?')}",
                    change_type=ChangeType.CHANGED,
                    left_label="left",
                    right_label="right",
                    redacted=False,
                )
            )
            frame_idx += 1
    if report.policy_diff:
        pd = report.policy_diff
        for issue in pd.issues_added:
            reg = " [REGRESSION]" if issue.is_regression else ""
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("policy", frame_idx),
                    sequence=frame_idx,
                    subject="policy",
                    node_id=issue.node_id,
                    summary=f"Policy issue added: {issue.rule} ({issue.right_severity}){reg}",
                    change_type=ChangeType.ADDED,
                    left_label=None,
                    right_label="right",
                    right_value={"rule": issue.rule, "severity": issue.right_severity},
                    redacted=False,
                )
            )
            frame_idx += 1
        for issue in pd.issues_removed:
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("policy", frame_idx),
                    sequence=frame_idx,
                    subject="policy",
                    node_id=issue.node_id,
                    summary=f"Policy issue removed: {issue.rule} ({issue.left_severity})",
                    change_type=ChangeType.REMOVED,
                    left_label="left",
                    right_label=None,
                    left_value={"rule": issue.rule, "severity": issue.left_severity},
                    redacted=False,
                )
            )
            frame_idx += 1
        for issue in pd.issues_changed:
            frames.append(
                TimelineFrame(
                    frame_id=_frame_id("policy", frame_idx),
                    sequence=frame_idx,
                    subject="policy",
                    node_id=issue.node_id,
                    summary=f"Policy severity changed: {issue.rule} ({issue.left_severity} -> {issue.right_severity})",
                    change_type=ChangeType.CHANGED,
                    left_label="left",
                    right_label="right",
                    left_value={"severity": issue.left_severity},
                    right_value={"severity": issue.right_severity},
                    redacted=False,
                )
            )
            frame_idx += 1
    return frames


class TimeTravelCursor:
    def __init__(self, frames):
        self._frames = frames
        self._index = 0

    @property
    def current(self):
        if 0 <= self._index < len(self._frames):
            return self._frames[self._index]
        return None

    @property
    def frame_id(self):
        return self.current.frame_id if self.current else None

    @property
    def sequence(self):
        return self.current.sequence if self.current else None

    @property
    def can_step_back(self):
        return self._index > 0

    @property
    def can_step_forward(self):
        return self._index < len(self._frames) - 1

    def step_back(self):
        if self.can_step_back:
            self._index -= 1
        return self.current

    def step_forward(self):
        if self.can_step_forward:
            self._index += 1
        return self.current

    def seek_to(self, frame_id):
        for i, f in enumerate(self._frames):
            if f.frame_id == frame_id:
                self._index = i
                return f
        return None

    def context(self, before=2, after=2):
        start = max(0, self._index - before)
        end = min(len(self._frames), self._index + after + 1)
        return self._frames[start:end]

    def as_dict(self):
        return {
            "frame_id": self.frame_id,
            "sequence": self.sequence,
            "can_step_back": self.can_step_back,
            "can_step_forward": self.can_step_forward,
            "context": [f.model_dump() for f in self.context()],
        }
