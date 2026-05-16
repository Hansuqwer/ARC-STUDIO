"""Tests: Policy loader — PolicyConfig, ApprovalPolicy, load_policy(), compute_trust_diff()."""
from __future__ import annotations

import yaml
from pathlib import Path

from agent_runtime_cockpit.config.policy import (
    ApprovalRule,
    PolicyConfig,
    compute_trust_diff,
    load_policy,
)


def _write_policy(path: Path, policy: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(policy), encoding="utf-8")
    return path


# ─── Defaults ──────────────────────────────────────────────────────────────────


def test_policy_defaults():
    config = PolicyConfig()
    assert config.version == 1
    assert config.approvals.paid_calls == ApprovalRule.ASK
    assert config.approvals.destructive_writes == ApprovalRule.ASK
    assert config.approvals.trust_changes == ApprovalRule.DENY
    assert config.approvals.shell_exec == ApprovalRule.DENY
    assert config.approvals.phase_advance == ApprovalRule.ASK


# ─── User policy ───────────────────────────────────────────────────────────────


def test_load_user_policy_only(tmp_path):
    user_policy = _write_policy(
        tmp_path / "policy.yaml",
        {"approvals": {"shell_exec": "ask", "paid_calls": "deny"}},
    )
    config = load_policy(user_policy_path=user_policy)
    assert config.approvals.shell_exec == ApprovalRule.ASK
    assert config.approvals.paid_calls == ApprovalRule.DENY
    assert config.approvals.trust_changes == ApprovalRule.DENY


def test_user_policy_missing_returns_defaults(tmp_path):
    config = load_policy(
        user_policy_path=tmp_path / "nonexistent.yaml",
    )
    assert config.approvals.shell_exec == ApprovalRule.DENY
    assert config.approvals.paid_calls == ApprovalRule.ASK


def test_user_policy_corrupt_yaml_returns_defaults(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text("not: valid: yaml: [[[", encoding="utf-8")
    config = load_policy(user_policy_path=path)
    assert config.approvals.shell_exec == ApprovalRule.DENY  # safe defaults


def test_user_policy_stricter_than_defaults(tmp_path):
    user_policy = _write_policy(
        tmp_path / "policy.yaml",
        {"approvals": {"paid_calls": "deny", "destructive_writes": "deny"}},
    )
    config = load_policy(user_policy_path=user_policy)
    assert config.approvals.paid_calls == ApprovalRule.DENY  # user deny > default ask
    assert config.approvals.destructive_writes == ApprovalRule.DENY
    assert config.approvals.trust_changes == ApprovalRule.DENY


# ─── Project policy ────────────────────────────────────────────────────────────


def test_project_policy_overrides_user_on_unprotected(tmp_path):
    _write_policy(
        tmp_path / "user" / "policy.yaml",
        {"approvals": {"paid_calls": "deny"}},
    )
    _write_policy(
        tmp_path / "ws" / ".arc" / "policy.yaml",
        {"approvals": {"paid_calls": "ask"}},
    )
    config = load_policy(
        workspace=tmp_path / "ws",
        user_policy_path=tmp_path / "user" / "policy.yaml",
    )
    assert config.approvals.paid_calls == ApprovalRule.ASK  # project wins over user


def test_project_policy_cannot_weaken_shell_exec(tmp_path):
    _write_policy(
        tmp_path / "user" / "policy.yaml",
        {"approvals": {"shell_exec": "deny"}},
    )
    _write_policy(
        tmp_path / "ws" / ".arc" / "policy.yaml",
        {"approvals": {"shell_exec": "auto"}},
    )
    config = load_policy(
        workspace=tmp_path / "ws",
        user_policy_path=tmp_path / "user" / "policy.yaml",
    )
    assert config.approvals.shell_exec == ApprovalRule.DENY  # user deny protected


def test_project_policy_cannot_weaken_trust_changes(tmp_path):
    _write_policy(
        tmp_path / "user" / "policy.yaml",
        {"approvals": {"trust_changes": "deny"}},
    )
    _write_policy(
        tmp_path / "ws" / ".arc" / "policy.yaml",
        {"approvals": {"trust_changes": "ask"}},
    )
    config = load_policy(
        workspace=tmp_path / "ws",
        user_policy_path=tmp_path / "user" / "policy.yaml",
    )
    assert config.approvals.trust_changes == ApprovalRule.DENY  # user deny protected


def test_project_policy_can_strengthen_protected_fields(tmp_path):
    _write_policy(
        tmp_path / "user" / "policy.yaml",
        {"approvals": {"shell_exec": "ask"}},
    )
    _write_policy(
        tmp_path / "ws" / ".arc" / "policy.yaml",
        {"approvals": {"shell_exec": "deny"}},
    )
    config = load_policy(
        workspace=tmp_path / "ws",
        user_policy_path=tmp_path / "user" / "policy.yaml",
    )
    assert config.approvals.shell_exec == ApprovalRule.DENY  # project can strengthen


def test_project_policy_missing_no_error(tmp_path):
    config = load_policy(
        workspace=tmp_path / "nonexistent",
        user_policy_path=tmp_path / "user" / "policy.yaml",
    )
    assert config.approvals.paid_calls == ApprovalRule.ASK


def test_project_policy_injected_path(tmp_path):
    _write_policy(
        tmp_path / "custom-policy.yaml",
        {"approvals": {"destructive_writes": "deny"}},
    )
    config = load_policy(
        project_policy_path=tmp_path / "custom-policy.yaml",
        user_policy_path=tmp_path / "nonexistent.yaml",
    )
    assert config.approvals.destructive_writes == ApprovalRule.DENY


# ─── compute_trust_diff ────────────────────────────────────────────────────────


def test_compute_trust_diff_returns_diff_with_correct_reason(tmp_path):
    diff = compute_trust_diff(tmp_path)
    assert diff.diff_id.startswith("td_")
    assert diff.reason == "workspace_first_trust"
    assert diff.requires_confirmation is True


def test_compute_trust_diff_includes_added_capabilities(tmp_path):
    diff = compute_trust_diff(workspace=tmp_path)
    assert len(diff.added_capabilities) > 0
    assert "read_files" in diff.added_capabilities
    assert "browse_workspace" in diff.added_capabilities
    assert "no_shell_exec" in diff.before
    assert "run_commands" not in diff.before
    assert set(diff.added_capabilities).isdisjoint(diff.before)


def test_compute_trust_diff_with_restrictive_policy(tmp_path):
    policy = PolicyConfig()
    policy.approvals.shell_exec = ApprovalRule.DENY
    policy.approvals.paid_calls = ApprovalRule.DENY
    policy.approvals.destructive_writes = ApprovalRule.DENY
    policy.approvals.trust_changes = ApprovalRule.DENY

    diff = compute_trust_diff(workspace=tmp_path, policy=policy)
    assert "run_commands" not in diff.added_capabilities
    assert "call_paid_providers" not in diff.added_capabilities
    assert "write_files" not in diff.added_capabilities
    assert "modify_trust_settings" not in diff.added_capabilities
    assert "read_files" in diff.added_capabilities
    assert "browse_workspace" in diff.added_capabilities


def test_compute_trust_diff_with_permissive_policy(tmp_path):
    policy = PolicyConfig()
    policy.approvals.shell_exec = ApprovalRule.AUTO
    policy.approvals.paid_calls = ApprovalRule.AUTO
    policy.approvals.destructive_writes = ApprovalRule.AUTO
    policy.approvals.trust_changes = ApprovalRule.AUTO

    diff = compute_trust_diff(workspace=tmp_path, policy=policy)
    assert "run_commands" in diff.added_capabilities
    assert "call_paid_providers" in diff.added_capabilities
    assert "write_files" in diff.added_capabilities
    assert "modify_trust_settings" in diff.added_capabilities
    assert diff.before == ["read_only"]
    assert diff.removed_restrictions == [
        "no_shell_exec", "no_paid_calls", "no_destructive_writes", "no_trust_changes",
    ]


def test_compute_trust_diff_affected_runtimes(tmp_path):
    diff = compute_trust_diff(tmp_path)
    assert diff.affected_runtimes == ["*"]


def test_compute_trust_diff_has_workspace_path(tmp_path):
    diff = compute_trust_diff(tmp_path)
    assert diff.workspace_path == str(tmp_path.resolve())
