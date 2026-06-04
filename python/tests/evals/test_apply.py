"""Tests for evals/apply.py — Eval-to-Policy auto-apply loop."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.evals.apply import (
    ACTION_MAP,
    ProfileApplyResult,
    apply_mutations,
    apply_to_profile,
    compute_mutations,
)
from agent_runtime_cockpit.evals.policy_recommend import (
    PolicyRecommendation,
    PolicyRecommendationReport,
    apply_to_profile as recommend_apply_to_profile,
)
from agent_runtime_cockpit.security.profiles import (
    BUILTIN_PROFILES,
    PROFILE_SCHEMA_VERSION,
    RunProfile,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    return tmp_path


def _make_report(actions: list[str]) -> PolicyRecommendationReport:
    recs = [
        PolicyRecommendation(
            id=f"rec-{i:03d}",
            confidence=0.8,
            category="test",
            title="Test",
            description="Test recommendation",
            action=action,
        )
        for i, action in enumerate(actions, 1)
    ]
    return PolicyRecommendationReport(
        total_runs=10,
        failed_runs=5,
        failure_rate=0.5,
        recommendations=recs,
    )


# ─── Schema Version ─────────────────────────────────────────────────────────


def test_profile_schema_version_is_2():
    assert PROFILE_SCHEMA_VERSION == 2


# ─── RunProfile extra field ──────────────────────────────────────────────────


def test_runprofile_extra_defaults_empty():
    p = RunProfile(id="test", name="Test")
    assert p.extra == {}


def test_runprofile_extra_custom():
    p = RunProfile(id="test", name="Test", extra={"foo": "bar"})
    assert p.extra == {"foo": "bar"}


def test_builtin_profiles_have_empty_extra():
    for profile in BUILTIN_PROFILES.values():
        assert profile.extra == {}


# ─── Mutation computation ────────────────────────────────────────────────────


def test_compute_mutations_consensus():
    m = compute_mutations(["add_consensus_check=majority_voting"])
    assert m == {"extra": {"consensus": "majority"}}


def test_compute_mutations_hitl():
    m = compute_mutations(["add_hitl_checkpoint=before_completion"])
    assert m == {"extra": {"require_hitl": "True"}}


def test_compute_mutations_tool_approval():
    m = compute_mutations(["require_tool_approval=side_effect_tools"])
    assert m == {"allow_shell": False, "extra": {"require_tool_approval": "True"}}


def test_compute_mutations_paid_call_gate():
    m = compute_mutations(["review_paid_call_gate=enabled"])
    assert m == {"allow_paid_calls": False, "extra": {"review_required": "True"}}


def test_compute_mutations_multiple_merges_extra():
    m = compute_mutations(
        [
            "add_consensus_check=majority_voting",
            "add_hitl_checkpoint=before_completion",
        ]
    )
    assert m == {"extra": {"consensus": "majority", "require_hitl": "True"}}


def test_compute_mutations_unknown_action_ignored():
    m = compute_mutations(["unknown_action=foo"])
    assert m == {}


# ─── apply_mutations ─────────────────────────────────────────────────────────


def test_apply_mutations_sets_shell_false():
    profile = RunProfile(id="test", name="Test", allow_shell=True)
    mutations = {"allow_shell": False, "extra": {"require_tool_approval": "True"}}
    new_profile, extra = apply_mutations(profile, mutations)
    assert new_profile.allow_shell is False
    assert extra == {"require_tool_approval": "True"}


# ─── apply_to_profile ────────────────────────────────────────────────────────


def test_apply_dry_run_does_not_write(workspace: Path):
    result = apply_to_profile(
        "local-safe",
        ["add_consensus_check=majority_voting"],
        workspace=workspace,
        dry_run=True,
    )
    assert result.dry_run is True
    assert not Path(result.new_path).exists()
    assert result.correlation_id
    assert result.profile_id == "local-safe"


def test_apply_writes_versioned_file(workspace: Path):
    result = apply_to_profile(
        "local-safe",
        ["add_consensus_check=majority_voting"],
        workspace=workspace,
        dry_run=False,
    )
    assert result.dry_run is False
    assert result.version == 1
    path = Path(result.new_path)
    assert path.exists()
    assert "local-safe.v1.yaml" in path.name


def test_apply_idempotent(workspace: Path):
    r1 = apply_to_profile(
        "local-safe",
        ["add_consensus_check=majority_voting"],
        workspace=workspace,
        dry_run=False,
    )
    r2 = apply_to_profile(
        "local-safe",
        ["add_consensus_check=majority_voting"],
        workspace=workspace,
        dry_run=False,
    )
    # Idempotent: same version, same path
    assert r1.version == r2.version
    assert r1.new_path == r2.new_path
    assert "already applied" in r2.diff_summary


def test_apply_increments_version_on_different_mutations(workspace: Path):
    apply_to_profile(
        "local-safe",
        ["add_consensus_check=majority_voting"],
        workspace=workspace,
        dry_run=False,
    )
    r2 = apply_to_profile(
        "local-safe",
        ["add_hitl_checkpoint=before_completion"],
        workspace=workspace,
        dry_run=False,
    )
    assert r2.version == 2


def test_apply_never_overwrites_builtin():
    """Builtins are forked, never mutated."""
    assert "local-safe" in BUILTIN_PROFILES
    result = apply_to_profile(
        "local-safe",
        ["require_tool_approval=side_effect_tools"],
        workspace=Path("/tmp/arc-test-never-run"),
        dry_run=True,
    )
    # The builtin itself is unchanged
    assert BUILTIN_PROFILES["local-safe"].allow_shell is False
    assert result.diff_summary  # should have changes


def test_apply_diff_summary_includes_changes(workspace: Path):
    result = apply_to_profile(
        "local-safe",
        ["review_paid_call_gate=enabled"],
        workspace=workspace,
        dry_run=True,
    )
    assert "review_required" in result.diff_summary


def test_apply_correlation_id_stable():
    """Same profile + actions → same correlation_id."""
    r1 = apply_to_profile(
        "local-safe",
        ["add_consensus_check=majority_voting"],
        workspace=Path("/tmp/arc-test-never-run"),
        dry_run=True,
    )
    r2 = apply_to_profile(
        "local-safe",
        ["add_consensus_check=majority_voting"],
        workspace=Path("/tmp/arc-test-never-run2"),
        dry_run=True,
    )
    assert r1.correlation_id == r2.correlation_id


# ─── recommend_apply_to_profile (public method on policy_recommend) ──────────


def test_recommend_apply_to_profile_delegates(workspace: Path):
    report = _make_report(["add_consensus_check=majority_voting"])
    result = recommend_apply_to_profile(report, "local-safe", workspace=workspace, dry_run=True)
    assert isinstance(result, ProfileApplyResult)
    assert result.profile_id == "local-safe"
    assert result.dry_run is True


def test_recommend_apply_multiple_actions(workspace: Path):
    report = _make_report(
        [
            "require_tool_approval=side_effect_tools",
            "review_paid_call_gate=enabled",
        ]
    )
    result = recommend_apply_to_profile(report, "local-safe", workspace=workspace, dry_run=False)
    assert result.dry_run is False
    path = Path(result.new_path)
    assert path.exists()
    content = path.read_text()
    assert "require_tool_approval" in content
    assert "review_required" in content


# ─── ProfileApplyResult JSON stability ───────────────────────────────────────


def test_profile_apply_result_json_stable():
    r = ProfileApplyResult(
        new_path="/tmp/test.v1.yaml",
        diff_summary="allow_shell: True → False",
        correlation_id="abc123",
        dry_run=False,
        profile_id="local-safe",
        version=1,
    )
    d = r.model_dump()
    assert d["new_path"] == "/tmp/test.v1.yaml"
    assert d["correlation_id"] == "abc123"
    assert d["version"] == 1
    assert d["dry_run"] is False


# ─── ACTION_MAP coverage ─────────────────────────────────────────────────────


def test_action_map_has_all_required_actions():
    required = {
        "add_consensus_check=majority_voting",
        "set_consensus=majority_plus_hitl",
        "add_hitl_checkpoint=before_completion",
        "require_tool_approval=side_effect_tools",
        "review_paid_call_gate=enabled",
    }
    assert required.issubset(set(ACTION_MAP.keys()))
