"""Approval policy loader — PolicyConfig, ApprovalPolicy, load_policy().

Policy files control what runtime actions require user confirmation.
Precedence: Project > User > Built-in defaults.

Project policy CANNOT weaken user policy for ``shell_exec`` or ``trust_changes``.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import yaml
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..protocol.trust_diff import TrustDiff

DEFAULT_USER_POLICY_PATH = Path.home() / ".config" / "arc-studio" / "policy.yaml"
DEFAULT_PROJECT_POLICY_PATH = Path(".arc") / "policy.yaml"


class ApprovalRule(str, Enum):
    ASK = "ask"
    AUTO = "auto"
    DENY = "deny"


_ORDER = {ApprovalRule.DENY: 3, ApprovalRule.ASK: 2, ApprovalRule.AUTO: 1}


def _stricter(a: ApprovalRule, b: ApprovalRule) -> ApprovalRule:
    return a if _ORDER[a] >= _ORDER[b] else b


class ApprovalPolicy(BaseModel):
    paid_calls: ApprovalRule = ApprovalRule.ASK
    destructive_writes: ApprovalRule = ApprovalRule.ASK
    trust_changes: ApprovalRule = ApprovalRule.DENY
    shell_exec: ApprovalRule = ApprovalRule.DENY
    phase_advance: ApprovalRule = ApprovalRule.ASK


class PolicyConfig(BaseModel):
    version: int = 1
    approvals: ApprovalPolicy = Field(default_factory=ApprovalPolicy)


def load_policy(
    workspace: Optional[Path] = None,
    user_policy_path: Path = DEFAULT_USER_POLICY_PATH,
    project_policy_path: Optional[Path] = None,
) -> PolicyConfig:
    """Load and merge policy files with precedence and safety constraints.

    1. Built-in defaults
    2. User policy overlays defaults
    3. Project policy overlays user policy, but cannot weaken user policy
       for ``shell_exec`` or ``trust_changes``.
    """
    merged = PolicyConfig()

    user_policy = _load_policy_file(user_policy_path)
    if user_policy is not None:
        merged = _merge_user_over_defaults(user_policy, merged)

    if project_policy_path is None and workspace is not None:
        project_policy_path = workspace / DEFAULT_PROJECT_POLICY_PATH

    if project_policy_path is not None and project_policy_path.exists():
        project_policy = _load_policy_file(project_policy_path)
        if project_policy is not None:
            merged = _merge_project_over_user(merged, project_policy)

    return merged


def compute_trust_diff(
    workspace: Path,
    policy: Optional[PolicyConfig] = None,
) -> TrustDiff:
    """Compute a TrustDiff for the UNTRUSTED -> TRUSTED transition.

    Lists the capabilities and restrictions that change when a workspace
    goes from untrusted (read-only, no network, no paid calls) to trusted.
    """
    from ..protocol.trust_diff import TrustDiff

    if policy is None:
        policy = load_policy(workspace=workspace)

    added: list[str] = []
    removed: list[str] = []

    exec_policy = policy.approvals
    if exec_policy.shell_exec != ApprovalRule.DENY:
        added.append("run_commands")
        removed.append("no_shell_exec")
    if exec_policy.paid_calls != ApprovalRule.DENY:
        added.append("call_paid_providers")
        removed.append("no_paid_calls")
    if exec_policy.destructive_writes != ApprovalRule.DENY:
        added.append("write_files")
        removed.append("no_destructive_writes")
    if exec_policy.trust_changes != ApprovalRule.DENY:
        added.append("modify_trust_settings")
        removed.append("no_trust_changes")

    added.append("read_files")
    added.append("browse_workspace")

    baseline = [
        "read_only",
        "no_shell_exec",
        "no_paid_calls",
        "no_destructive_writes",
        "no_trust_changes",
    ]
    before = [cap for cap in baseline if cap not in removed]
    after = ["read_files", "browse_workspace"] + [cap for cap in added if cap not in {"read_files", "browse_workspace"}]

    return TrustDiff(
        diff_id="td_" + secrets.token_urlsafe(16),
        workspace_path=str(workspace.resolve()),
        before=before,
        after=after,
        added_capabilities=added,
        removed_restrictions=removed,
        affected_runtimes=["*"],
        reason="workspace_first_trust",
        requires_confirmation=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _load_policy_file(path: Path) -> Optional[PolicyConfig]:
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return PolicyConfig.model_validate(data)
    except Exception as exc:
        log.warning("Failed to load policy file %s: %s", path, exc)
        return None


def _merge_user_over_defaults(
    user: PolicyConfig, defaults: PolicyConfig,
) -> PolicyConfig:
    merged = PolicyConfig()
    merged.version = max(user.version, defaults.version)
    for field_name in ApprovalPolicy.model_fields:
        user_val = getattr(user.approvals, field_name)
        setattr(merged.approvals, field_name, user_val)
    return merged


def _merge_project_over_user(
    user_policy: PolicyConfig, project_policy: PolicyConfig,
) -> PolicyConfig:
    """Merge project policy over user policy with safety constraints.

    Project wins for all fields EXCEPT ``shell_exec`` and ``trust_changes``,
    where the stricter (more restrictive) value is kept.
    """
    protected = {"shell_exec", "trust_changes"}
    merged = PolicyConfig()
    merged.version = max(user_policy.version, project_policy.version)
    for field_name in ApprovalPolicy.model_fields:
        user_val = getattr(user_policy.approvals, field_name)
        project_val = getattr(project_policy.approvals, field_name)
        if field_name in protected:
            setattr(merged.approvals, field_name, _stricter(user_val, project_val))
        else:
            setattr(merged.approvals, field_name, project_val)
    return merged
