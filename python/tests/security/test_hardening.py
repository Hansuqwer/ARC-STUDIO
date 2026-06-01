"""Hardening regression tests (findings H1–H9).

These lock in the security-hardening changes:

- H1 validate_workspace_path resolves instead of substring-rejecting `..`
- H2 single-source env allowlist (providers and SandboxPolicy never diverge)
- H3 unified secret redaction (frontend Redactor == subprocess redact_output)
- H4 NoneIsolationProvider runs the resolved (not symlinked) cwd
- H5 python -c is only READ_ONLY when statically proven side-effect free
- H7 git global options (-c/-C/--git-dir) are stripped before classification
- H8 oversized argv is treated as UNKNOWN (deny-default)
- H9 audit persistence failure never fail-opens a denial

No network, Docker, Lima, or Firecracker required.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from agent_runtime_cockpit.isolation.none import NoneIsolationProvider
from agent_runtime_cockpit.isolation.subprocess import (
    DEFAULT_SAFE_ENV_KEYS,
    redact_output,
)
from agent_runtime_cockpit.security.redaction import Redactor, redact_secrets
from agent_runtime_cockpit.security.sandbox import (
    MAX_ARGV_COUNT,
    CommandClassification,
    SandboxPolicy,
    classify_command,
)
from agent_runtime_cockpit.security.validation import (
    SAFE_ENV_KEYS,
    validate_workspace_path,
)


# --------------------------------------------------------------------------- H1
class TestValidateWorkspacePathHardening:
    def test_dotdot_is_resolved_not_rejected(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        target = tmp_path / "sub" / ".." / "sub"
        assert validate_workspace_path(str(target)) == sub.resolve()

    def test_legitimate_path_with_dotdot_substring_allowed(self, tmp_path):
        weird = tmp_path / "my..app"
        weird.mkdir()
        assert validate_workspace_path(str(weird)) == weird.resolve()

    def test_nul_byte_rejected(self):
        with pytest.raises(ValueError, match="NUL"):
            validate_workspace_path("/tmp/x\x00y")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            validate_workspace_path("")


# --------------------------------------------------------------------------- H2
class TestEnvAllowlistSingleSource:
    def test_policy_and_provider_allowlists_match(self):
        assert DEFAULT_SAFE_ENV_KEYS == frozenset(SAFE_ENV_KEYS)
        assert frozenset(SandboxPolicy().env_allowlist) == DEFAULT_SAFE_ENV_KEYS

    def test_shell_excluded_everywhere(self):
        assert "SHELL" not in SAFE_ENV_KEYS
        assert "SHELL" not in DEFAULT_SAFE_ENV_KEYS
        assert "SHELL" not in SandboxPolicy().env_allowlist

    def test_secret_env_stripped(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
        monkeypatch.setenv("PATH", os.environ.get("PATH", "/usr/bin"))
        provider = NoneIsolationProvider()
        filtered = provider.filter_env()
        assert "OPENAI_API_KEY" not in filtered
        assert "PATH" in filtered


# --------------------------------------------------------------------------- H3
class TestRedactionParity:
    SECRETS = [
        "sk-" + "a" * 24,  # openai (>=20)
        "sk-ant-" + "b" * 20,  # anthropic
        "AKIA" + "A" * 16,  # aws
        "ghp_" + "c" * 36,  # github
        "Authorization: Bearer " + "d" * 30,  # bearer
        "postgres://user:hunter2@db.example.com/app",  # url password
        "-----BEGIN RSA PRIVATE KEY-----",  # pem
    ]

    @pytest.mark.parametrize("secret", SECRETS)
    def test_subprocess_and_frontend_agree(self, secret):
        frontend = Redactor().redact_string(secret)
        subproc = redact_output(secret)
        shared = redact_secrets(secret)
        assert "[REDACTED]" in frontend, f"frontend leaked: {secret}"
        assert "[REDACTED]" in subproc, f"subprocess leaked: {secret}"
        assert frontend == subproc == shared

    def test_url_password_preserves_host(self):
        out = redact_output("postgres://user:hunter2@db.example.com/app")
        assert "hunter2" not in out
        assert "db.example.com" in out


# --------------------------------------------------------------------------- H4
class TestNoneProviderResolvedCwd:
    def test_symlinked_cwd_rejected(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        link = ws / "link"
        os.symlink(outside, link)
        provider = NoneIsolationProvider(workspace_root=ws)
        with pytest.raises(ValueError, match="escapes workspace"):
            asyncio.run(provider.execute(["true"], cwd=link))

    def test_real_subdir_cwd_allowed(self, tmp_path):
        ws = tmp_path / "ws"
        sub = ws / "sub"
        sub.mkdir(parents=True)
        provider = NoneIsolationProvider(workspace_root=ws)
        result = asyncio.run(provider.execute(["pwd"], cwd=sub))
        assert result.exit_code == 0
        assert str(sub.resolve()) in result.stdout


# --------------------------------------------------------------------------- H5
class TestPythonDashCClassification:
    def test_plain_print_literal_is_read_only(self):
        assert (
            classify_command(["python", "-c", "print('hello')"]) == CommandClassification.READ_ONLY
        )

    def test_attribute_call_is_not_read_only(self):
        # os.getcwd() reaches an attribute call -> not provably safe -> UNKNOWN
        assert (
            classify_command(["python", "-c", "print(__import__('os').getcwd())"])
            != CommandClassification.READ_ONLY
        )

    def test_dunder_import_not_read_only(self):
        assert (
            classify_command(["python", "-c", "__import__('socket')"])
            != CommandClassification.READ_ONLY
        )

    def test_eval_not_read_only(self):
        assert classify_command(["python", "-c", "eval('1+1')"]) != CommandClassification.READ_ONLY

    def test_known_network_hint_still_network(self):
        assert classify_command(["python", "-c", "import socket"]) == CommandClassification.NETWORK


# --------------------------------------------------------------------------- H7
class TestGitGlobalOptionStripping:
    def test_git_dash_c_fetch_is_network(self):
        cmd = ["git", "-c", "protocol.ext.allow=always", "fetch", "origin"]
        assert classify_command(cmd) == CommandClassification.NETWORK

    def test_git_dash_capital_c_clean_is_destructive(self):
        cmd = ["git", "-C", "/some/dir", "clean", "-fd"]
        assert classify_command(cmd) == CommandClassification.DESTRUCTIVE

    def test_git_git_dir_inline_status_is_read_only(self):
        cmd = ["git", "--git-dir=.git", "status"]
        assert classify_command(cmd) == CommandClassification.READ_ONLY

    def test_plain_git_status_still_read_only(self):
        assert classify_command(["git", "status"]) == CommandClassification.READ_ONLY


# --------------------------------------------------------------------------- H8
class TestArgvBounds:
    def test_oversized_argv_count_is_unknown(self):
        cmd = ["ls", *(["x"] * (MAX_ARGV_COUNT + 1))]
        assert classify_command(cmd) == CommandClassification.UNKNOWN

    def test_oversized_argv_bytes_is_unknown(self):
        cmd = ["ls", "y" * (1_048_576 + 10)]
        assert classify_command(cmd) == CommandClassification.UNKNOWN

    def test_normal_argv_classifies_normally(self):
        assert classify_command(["ls", "-la"]) == CommandClassification.READ_ONLY


# --------------------------------------------------------------------------- H9
class TestAuditPersistenceNeverFailOpen:
    def test_persist_failure_marks_event_without_raising(self, monkeypatch):
        from agent_runtime_cockpit.cli import sandbox as sandbox_cli

        def boom(_audit):
            raise OSError("disk full")

        monkeypatch.setattr(sandbox_cli, "persist_sandbox_audit_event", boom)
        audit = {"command": ["rm", "-rf", "."], "decision": {"allowed": False}}
        result = sandbox_cli._persist_audit_safely(audit)
        # Decision is untouched; persistence flagged as failed; no exception.
        assert result["audit_path"] is None
        assert result["audit_persisted"] is False
        assert result["decision"]["allowed"] is False
