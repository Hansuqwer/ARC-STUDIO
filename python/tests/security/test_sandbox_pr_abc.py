"""Tests for PR-A/B/C sandbox hardening.

PR-A: per-command exit-code semantics (grep/diff/test nonzero != error)
PR-B: secret/credential read-exfil paths denied
PR-C: stable denial reason codes on SandboxDecision / audit events

No network, Docker, Lima, or Firecracker required.
"""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.security.sandbox import (
    CommandClassification,
    SandboxPathViolation,
    SandboxPolicy,
    SandboxReasonCode,
    build_audit_event,
    decide,
    interpret_exit_code,
    utc_now,
    validate_command_paths,
)


# --------------------------------------------------------------------------- PR-A
class TestExitCodeSemantics:
    def test_grep_no_match_not_error(self):
        is_error, note = interpret_exit_code(["grep", "x", "f"], 1)
        assert is_error is False
        assert note == "no matches found"

    def test_grep_real_error(self):
        is_error, note = interpret_exit_code(["grep", "x", "f"], 2)
        assert is_error is True
        assert note is None

    def test_rg_no_match_not_error(self):
        assert interpret_exit_code(["rg", "x"], 1) == (False, "no matches found")

    def test_diff_differ_not_error(self):
        is_error, note = interpret_exit_code(["diff", "a", "b"], 1)
        assert is_error is False
        assert note == "files differ"

    def test_test_condition_false_not_error(self):
        assert interpret_exit_code(["test", "-f", "x"], 1) == (False, "condition is false")

    def test_default_nonzero_is_error(self):
        assert interpret_exit_code(["ls"], 1) == (True, None)

    def test_zero_is_success(self):
        assert interpret_exit_code(["grep", "x"], 0) == (False, None)

    def test_none_exit_is_error(self):
        assert interpret_exit_code(["grep", "x"], None) == (True, None)

    def test_empty_command_default(self):
        assert interpret_exit_code([], 1) == (True, None)


# --------------------------------------------------------------------------- PR-B
class TestSecretReadDeny:
    def _policy(self, tmp_path):
        return SandboxPolicy(workspace_root=tmp_path)

    @pytest.mark.parametrize(
        "command",
        [
            ["cat", "/proc/self/environ"],
            ["cat", "/proc/1234/environ"],
            ["cat", ".env"],
            ["cat", ".env.production"],
            ["cat", "config/.env.local"],
            ["cat", "~/.ssh/id_rsa"],
            ["cat", "~/.aws/credentials"],
            ["cat", ".netrc"],
            ["cat", ".git-credentials"],
            ["cat", ".npmrc"],
        ],
    )
    def test_secret_paths_denied(self, tmp_path, command):
        with pytest.raises(SandboxPathViolation) as exc:
            validate_command_paths(command, self._policy(tmp_path))
        assert exc.value.reason_code == SandboxReasonCode.SECRET_READ_DENIED

    def test_normal_workspace_read_allowed(self, tmp_path):
        (tmp_path / "notes.txt").write_text("hi", encoding="utf-8")
        # Should not raise.
        validate_command_paths(["cat", "notes.txt"], self._policy(tmp_path))

    def test_non_secret_env_named_file_in_path_segment_allowed(self, tmp_path):
        # A file literally named "environment.txt" must not trip the /proc rule.
        (tmp_path / "environment.txt").write_text("x", encoding="utf-8")
        validate_command_paths(["cat", "environment.txt"], self._policy(tmp_path))


# --------------------------------------------------------------------------- PR-C
class TestReasonCodes:
    def _policy(self, **kw):
        return SandboxPolicy(**kw)

    def test_read_only_code(self):
        assert decide(["ls", "-la"], self._policy()).reason_code == (
            SandboxReasonCode.ALLOW_READ_ONLY
        )

    def test_network_denied_code(self):
        d = decide(["curl", "https://example.com"], self._policy())
        assert d.allowed is False
        assert d.reason_code == SandboxReasonCode.NETWORK_DENIED

    def test_network_allowed_code(self):
        d = decide(["curl", "https://example.com"], self._policy(allow_network=True))
        assert d.allowed is True
        assert d.reason_code == SandboxReasonCode.ALLOW_NETWORK

    def test_destructive_denied_code(self):
        d = decide(["rm", "-rf", "."], self._policy())
        assert d.reason_code == SandboxReasonCode.DESTRUCTIVE_DENIED

    def test_privileged_denied_code(self):
        d = decide(["sudo", "ls"], self._policy())
        assert d.reason_code == SandboxReasonCode.PRIVILEGED_DENIED

    def test_install_denied_code(self):
        d = decide(["pip", "install", "requests"], self._policy())
        assert d.reason_code == SandboxReasonCode.INSTALL_DENIED

    def test_unknown_denied_code(self):
        d = decide(["frobnicate", "--wat"], self._policy())
        assert d.reason_code == SandboxReasonCode.UNKNOWN_DENIED

    def test_argv_oversized_code(self):
        cmd = ["ls", *(["x"] * 5000)]
        d = decide(cmd, self._policy())
        assert d.allowed is False
        assert d.reason_code == SandboxReasonCode.ARGV_OVERSIZED

    def test_audit_event_includes_reason_code(self):
        d = decide(["curl", "https://x"], self._policy())
        audit = build_audit_event(
            command=["curl", "https://x"],
            cwd=__import__("pathlib").Path("/tmp"),
            decision=d,
            provider="subprocess",
            started_at=utc_now(),
            ended_at=utc_now(),
            exit_code=None,
            stdout_truncated=False,
            stderr_truncated=False,
            redaction_applied=False,
        )
        assert audit["reason_code"] == SandboxReasonCode.NETWORK_DENIED.value

    def test_reason_text_preserved_alongside_code(self):
        d = decide(["rm", "-rf", "."], self._policy())
        assert d.reason  # human-readable reason still present
        assert d.reason_code is not None

    def test_classification_unaffected_by_reason_code(self):
        d = decide(["ls"], self._policy())
        assert d.classification == CommandClassification.READ_ONLY
