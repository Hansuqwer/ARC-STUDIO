"""Tests for policy report diff (Commit 3)."""

from __future__ import annotations

import sys

sys.path.insert(0, "/home/user/arc-theia-studio/python/src")


from agent_runtime_cockpit.run_diff.diff_policy import (
    _risk_level_worsened,
    _severity_worsened,
    diff_policy_reports,
)
from agent_runtime_cockpit.security.policy_linter import PolicyIssue, PolicyReport


def _make_report(wf_id, risk_level, can_run, issues, consensus=None):
    return PolicyReport(
        workflow_id=wf_id,
        workflow_name="Workflow " + wf_id,
        runtime="native",
        risk_level=risk_level,
        suggested_consensus=consensus,
        issues=issues,
        can_run=can_run,
    )


def _make_issue(rule, severity, node_id=None):
    return PolicyIssue(
        rule=rule,
        severity=severity,
        node_id=node_id,
        message="Issue: " + rule,
        remediation="Fix: " + rule,
    )


class TestDiffPolicyReports:
    def test_identical_reports_no_changes(self):
        issues = [_make_issue("missing_hitl", "warning")]
        left = _make_report("wf-1", "high", True, issues, "bft")
        right = _make_report("wf-1", "high", True, issues, "bft")
        report = diff_policy_reports(left, right)
        assert report.policy_diff is not None
        assert len(report.policy_diff.issues_added) == 0
        assert len(report.policy_diff.issues_removed) == 0
        assert report.policy_diff.can_run_regression is False

    def test_new_blocker_introduced(self):
        left_issues = [_make_issue("weak_consensus", "warning")]
        right_issues = [
            _make_issue("weak_consensus", "warning"),
            _make_issue("missing_hitl", "error"),
        ]
        left = _make_report("wf-1", "high", True, left_issues)
        right = _make_report("wf-1", "high", False, right_issues)
        report = diff_policy_reports(left, right)
        assert report.policy_diff.can_run_regression is True
        assert len(report.policy_diff.issues_added) == 1
        assert report.policy_diff.issues_added[0].is_regression is True

    def test_severity_escalated(self):
        left = _make_report("wf-1", "high", True, [_make_issue("weak_consensus", "info")])
        right = _make_report("wf-1", "high", True, [_make_issue("weak_consensus", "error")])
        report = diff_policy_reports(left, right)
        assert len(report.policy_diff.issues_changed) == 1
        assert report.policy_diff.issues_changed[0].is_regression is True

    def test_issue_removed(self):
        left = _make_report("wf-1", "high", True, [_make_issue("weak_consensus", "warning")])
        right = _make_report("wf-1", "high", True, [])
        report = diff_policy_reports(left, right)
        assert len(report.policy_diff.issues_removed) == 1

    def test_risk_level_increased(self):
        left = _make_report("wf-1", "medium", True, [])
        right = _make_report("wf-1", "high", True, [])
        report = diff_policy_reports(left, right)
        assert report.policy_diff.risk_regression is True

    def test_first_divergence_blocker(self):
        left = _make_report("wf-1", "high", True, [])
        right = _make_report("wf-1", "high", False, [_make_issue("missing_hitl", "error")])
        report = diff_policy_reports(left, right)
        assert report.first_divergence is not None
        assert report.first_divergence.kind == "policy"
        assert report.first_divergence.policy_rule == "missing_hitl"

    def test_report_has_hash(self):
        left = _make_report("wf-1", "low", True, [])
        right = _make_report("wf-1", "low", True, [])
        report = diff_policy_reports(left, right)
        assert report.diff_hash is not None
        assert len(report.diff_hash) == 64


class TestHelperFunctions:
    def test_severity_worsened_info_to_error(self):
        assert _severity_worsened("info", "error") is True

    def test_severity_worsened_same(self):
        assert _severity_worsened("error", "error") is False

    def test_risk_level_worsened_low_to_critical(self):
        assert _risk_level_worsened("low", "critical") is True

    def test_risk_level_worsened_downgrade(self):
        assert _risk_level_worsened("high", "low") is False


class TestNoNetworkPrimitives:
    def test_no_forbidden_primitives(self):
        import agent_runtime_cockpit.run_diff.diff_policy as mod

        content = open(mod.__file__).read()
        for f in ["subprocess", "socket", "aiohttp", "requests", "httpx", "Popen", "urlopen"]:
            assert f not in content, f"Found {f} in diff_policy.py"
