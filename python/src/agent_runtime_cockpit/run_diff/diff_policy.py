"""Policy report diff - compare two PolicyReport objects."""

from __future__ import annotations


from .models import (
    DiffSubject,
    DiffSubjectKind,
    FirstDivergence,
    PolicyDiff,
    PolicyIssueDiff,
    RunDiffReport,
)


def _issue_key(issue):
    return (issue.rule, issue.node_id)


def _is_new_regression(issue):
    return issue.severity == "error"


def _regression_type(issue, previous):
    if previous is None:
        return "blocker_introduced" if issue.severity == "error" else "warning_introduced"
    return "severity_escalated"


def _severity_worsened(left, right):
    order = {"info": 0, "warning": 1, "error": 2}
    return order.get(left, 0) < order.get(right, 0)


def _risk_level_worsened(left, right):
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return order.get(left, 0) < order.get(right, 0)


def diff_policy_reports(left, right):
    from .models import DiffSummary, RiskDiff

    left_map = {_issue_key(i): i for i in left.issues}
    right_map = {_issue_key(i): i for i in right.issues}
    issues_added = []
    issues_removed = []
    issues_changed = []
    for key, right_issue in right_map.items():
        if key not in left_map:
            diff = PolicyIssueDiff(
                rule=right_issue.rule,
                left_severity=None,
                right_severity=right_issue.severity,
                node_id=right_issue.node_id,
                left_present=False,
                right_present=True,
                is_regression=_is_new_regression(right_issue),
                regression_type=_regression_type(right_issue, None),
            )
            issues_added.append(diff)
        else:
            left_issue = left_map[key]
            if left_issue.severity != right_issue.severity:
                is_reg = _severity_worsened(left_issue.severity, right_issue.severity)
                issues_changed.append(
                    PolicyIssueDiff(
                        rule=right_issue.rule,
                        left_severity=left_issue.severity,
                        right_severity=right_issue.severity,
                        node_id=right_issue.node_id,
                        left_present=True,
                        right_present=True,
                        is_regression=is_reg,
                        regression_type="severity_escalated" if is_reg else None,
                    )
                )
    for key, left_issue in left_map.items():
        if key not in right_map:
            issues_removed.append(
                PolicyIssueDiff(
                    rule=left_issue.rule,
                    left_severity=left_issue.severity,
                    right_severity=None,
                    node_id=left_issue.node_id,
                    left_present=True,
                    right_present=False,
                    is_regression=False,
                    regression_type=None,
                )
            )
    can_run_regression = left.can_run and not right.can_run
    risk_regression = _risk_level_worsened(left.risk_level, right.risk_level)
    consensus_regression = (
        left.suggested_consensus != right.suggested_consensus
        and right.suggested_consensus is not None
        and left.suggested_consensus is not None
    )
    policy_diff = PolicyDiff(
        issues_added=issues_added,
        issues_removed=issues_removed,
        issues_changed=issues_changed,
        can_run_left=left.can_run,
        can_run_right=right.can_run,
        can_run_regression=can_run_regression,
        risk_level_left=left.risk_level,
        risk_level_right=right.risk_level,
        risk_regression=risk_regression,
        suggested_consensus_left=left.suggested_consensus,
        suggested_consensus_right=right.suggested_consensus,
        consensus_regression=consensus_regression,
        error_count_left=len(left.errors),
        error_count_right=len(right.errors),
        error_count_delta=len(right.errors) - len(left.errors),
        warning_count_left=len(left.warnings),
        warning_count_right=len(right.warnings),
        warning_count_delta=len(right.warnings) - len(left.warnings),
    )
    summary = DiffSummary()
    summary.policy_issues_added = len(issues_added)
    summary.policy_issues_removed = len(issues_removed)
    summary.policy_blockers_introduced = sum(1 for d in issues_added if d.right_severity == "error")
    summary.policy_errors_introduced = summary.policy_blockers_introduced
    if can_run_regression:
        summary.policy_issues_added += 1
    if risk_regression:
        summary.risk_increased = True
    summary.compute_total()
    first_div = None
    if issues_added:
        first = issues_added[0]
        first_div = FirstDivergence(
            kind="policy",
            policy_rule=first.rule,
            reason=f"Policy issue introduced: {first.rule} ({first.right_severity})",
            left_value={"issue": first.left_severity} if first.left_severity else None,
            right_value={"issue": first.right_severity, "node_id": first.node_id},
        )
    elif issues_changed:
        first = issues_changed[0]
        first_div = FirstDivergence(
            kind="policy",
            policy_rule=first.rule,
            reason=f"Policy issue severity changed: {first.rule} ({first.left_severity} -> {first.right_severity})",
            left_value={"severity": first.left_severity},
            right_value={"severity": first.right_severity},
        )
    elif can_run_regression:
        first_div = FirstDivergence(
            kind="policy",
            reason="can_run regressed from True to False",
            left_value={"can_run": True},
            right_value={"can_run": False},
        )
    risk_diff = RiskDiff(
        level_left=left.risk_level,
        level_right=right.risk_level,
        level_changed=left.risk_level != right.risk_level,
    )
    left_subject = DiffSubject(
        kind=DiffSubjectKind.POLICY_REPORT,
        id=left.workflow_id,
        metadata={
            "workflow_name": left.workflow_name,
            "runtime": left.runtime,
            "risk_level": left.risk_level,
            "can_run": left.can_run,
            "issue_count": len(left.issues),
        },
    )
    right_subject = DiffSubject(
        kind=DiffSubjectKind.POLICY_REPORT,
        id=right.workflow_id,
        metadata={
            "workflow_name": right.workflow_name,
            "runtime": right.runtime,
            "risk_level": right.risk_level,
            "can_run": right.can_run,
            "issue_count": len(right.issues),
        },
    )
    warnings = []
    if can_run_regression:
        warnings.append("POLICY REGRESSION: can_run changed from True to False")
    if risk_regression:
        warnings.append(f"RISK REGRESSION: {left.risk_level} -> {right.risk_level}")
    report = RunDiffReport(
        left=left_subject,
        right=right_subject,
        mode="policy_vs_policy",
        summary=summary,
        first_divergence=first_div,
        policy_diff=policy_diff,
        risk_diff=risk_diff,
        warnings=warnings,
    )
    return report.with_hash()


def diff_policy_from_paths(path_a, path_b):
    import json

    errors = []
    warnings = []
    left_report = None
    right_report = None
    for path, target in [(path_a, "left"), (path_b, "right")]:
        try:
            data = json.loads(open(path).read())
            from ..security.policy_linter import PolicyReport

            report = PolicyReport.model_validate(data)
            if target == "left":
                left_report = report
            else:
                right_report = report
        except FileNotFoundError:
            errors.append(f"Policy file not found: {path}")
        except json.JSONDecodeError:
            errors.append(f"Invalid JSON in {path}")
        except Exception as exc:
            errors.append(f"Failed to parse {path}: {exc}")
    if left_report is None or right_report is None:
        report = RunDiffReport(
            left=DiffSubject(kind=DiffSubjectKind.POLICY_REPORT, id=path_a, path=path_a),
            right=DiffSubject(kind=DiffSubjectKind.POLICY_REPORT, id=path_b, path=path_b),
            mode="policy_vs_policy",
            errors=errors,
        )
        return report.with_hash(), errors, warnings
    return diff_policy_reports(left_report, right_report), errors, warnings
