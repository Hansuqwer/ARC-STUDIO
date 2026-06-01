"""Tests for PR-D/E sandbox hardening + widened PR-B denylist.

PR-D: wrapper/compound normalisation (timeout/env/nohup/xargs/nice → inner cmd)
PR-E: wildcard CommandRule allow/deny/ask evaluated before classification
PR-B widened: extended credential/secret file denylist

No network, Docker, Lima, or Firecracker required.
"""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.security.sandbox import (
    CommandClassification,
    CommandRule,
    CommandRuleVerdict,
    SandboxPathViolation,
    SandboxPolicy,
    SandboxReasonCode,
    classify_command,
    decide,
    strip_command_wrappers,
    validate_command_paths,
)


# --------------------------------------------------------------------------- PR-D
class TestWrapperNormalisation:
    """timeout/env/nohup/nice/xargs/setsid wrappers are stripped before classification."""

    def test_timeout_curl_is_network(self):
        assert classify_command(["timeout", "30", "curl", "https://x"]) == (
            CommandClassification.NETWORK
        )

    def test_timeout_ls_is_read_only(self):
        assert classify_command(["timeout", "5", "ls", "-la"]) == (CommandClassification.READ_ONLY)

    def test_timeout_rm_is_destructive(self):
        assert classify_command(["timeout", "10", "rm", "-rf", "."]) == (
            CommandClassification.DESTRUCTIVE
        )

    def test_env_curl_is_network(self):
        assert classify_command(["env", "HTTPS_PROXY=x", "curl", "https://y"]) == (
            CommandClassification.NETWORK
        )

    def test_env_ls_is_read_only(self):
        assert classify_command(["env", "ls"]) == CommandClassification.READ_ONLY

    def test_nohup_pip_is_install(self):
        assert classify_command(["nohup", "pip", "install", "requests"]) == (
            CommandClassification.INSTALL
        )

    def test_nice_sudo_is_privileged(self):
        assert classify_command(["nice", "-n", "10", "sudo", "apt", "update"]) == (
            CommandClassification.PRIVILEGED
        )

    def test_setsid_wget_is_network(self):
        assert classify_command(["setsid", "wget", "https://x"]) == (CommandClassification.NETWORK)

    def test_xargs_rm_is_destructive(self):
        assert classify_command(["xargs", "rm"]) == CommandClassification.DESTRUCTIVE

    def test_nested_wrappers_peeled(self):
        # timeout 10 nohup curl → NETWORK
        assert classify_command(["timeout", "10", "nohup", "curl", "https://x"]) == (
            CommandClassification.NETWORK
        )

    def test_strip_command_wrappers_pure(self):
        assert strip_command_wrappers(["timeout", "30", "curl", "x"]) == ["curl", "x"]
        assert strip_command_wrappers(["nohup", "ls"]) == ["ls"]
        assert strip_command_wrappers(["ls", "-la"]) == ["ls", "-la"]

    def test_decide_respects_wrapper_normalised_class(self):
        d = decide(["timeout", "30", "curl", "https://x"], SandboxPolicy())
        assert d.allowed is False
        assert d.reason_code == SandboxReasonCode.NETWORK_DENIED
        assert d.classification == CommandClassification.NETWORK


# --------------------------------------------------------------------------- PR-E
class TestCommandRules:
    """Explicit allow/deny/ask rules evaluated before classification; first match wins."""

    def _policy(self, *rules, **kw):
        return SandboxPolicy(command_rules=rules, **kw)

    def test_explicit_allow_overrides_network_deny(self):
        rule = CommandRule(pattern="curl *", verdict=CommandRuleVerdict.ALLOW)
        d = decide(["curl", "https://internal.corp"], self._policy(rule))
        assert d.allowed is True
        assert d.reason_code == SandboxReasonCode.ALLOW_APPROVED

    def test_explicit_deny_overrides_read_only_allow(self):
        rule = CommandRule(pattern="ls *", verdict=CommandRuleVerdict.DENY)
        d = decide(["ls", "-la"], self._policy(rule))
        assert d.allowed is False

    def test_explicit_ask_sets_approval_required(self):
        rule = CommandRule(pattern="npm install *", verdict=CommandRuleVerdict.ASK)
        d = decide(["npm", "install", "react"], self._policy(rule))
        assert d.allowed is False
        assert d.approval_required is True

    def test_wildcard_star_matches_any(self):
        rule = CommandRule(pattern="*", verdict=CommandRuleVerdict.ALLOW)
        d = decide(["rm", "-rf", "/"], self._policy(rule))
        assert d.allowed is True  # explicit rule wins even over destructive

    def test_first_rule_wins(self):
        rules = (
            CommandRule(pattern="git *", verdict=CommandRuleVerdict.ALLOW),
            CommandRule(pattern="*", verdict=CommandRuleVerdict.DENY),
        )
        d = decide(["git", "status"], self._policy(*rules))
        assert d.allowed is True

    def test_no_match_falls_through_to_classifier(self):
        rule = CommandRule(pattern="docker *", verdict=CommandRuleVerdict.ALLOW)
        d = decide(["curl", "https://x"], self._policy(rule))
        # No rule matched → falls to classifier: curl → NETWORK_DENIED
        assert d.allowed is False
        assert d.reason_code == SandboxReasonCode.NETWORK_DENIED

    def test_empty_rules_unchanged_behavior(self):
        d = decide(["ls"], SandboxPolicy())
        assert d.allowed is True
        assert d.reason_code == SandboxReasonCode.ALLOW_READ_ONLY

    def test_exact_match_rule(self):
        rule = CommandRule(pattern="npm test", verdict=CommandRuleVerdict.ALLOW)
        assert decide(["npm", "test"], self._policy(rule)).allowed is True
        # npm install should not match
        d_install = decide(["npm", "install", "x"], self._policy(rule))
        assert d_install.allowed is False  # falls to classifier → INSTALL_DENIED


# --------------------------------------------------------------------------- PR-B widened
class TestSecretDenylistWidened:
    def _policy(self, tmp_path):
        return SandboxPolicy(workspace_root=tmp_path)

    @pytest.mark.parametrize(
        "command",
        [
            # Extended basenames
            ["cat", ".my.cnf"],
            ["cat", ".vault-token"],
            ["cat", ".bash_history"],
            ["cat", ".zsh_history"],
            # Extended suffixes
            ["cat", "~/.azure/accessTokens.json"],
            # Extended segments
            ["cat", "~/.config/gcloud/credentials.db"],
            ["cat", "~/.kube/config"],
            ["cat", "~/.config/helm/repositories.yaml"],
            ["cat", "/etc/shadow"],
            ["cat", "/etc/gshadow"],
            ["cat", "/var/run/secrets/kubernetes.io/serviceaccount/token"],
            # Regex patterns
            ["cat", "/proc/1/mem"],
            ["cat", ".terraformrc"],
            ["cat", "terraform.tfvars"],
            ["cat", "prod.tfvars.json"],
        ],
    )
    def test_widened_secret_paths_denied(self, tmp_path, command):
        with pytest.raises(SandboxPathViolation) as exc:
            validate_command_paths(command, self._policy(tmp_path))
        assert exc.value.reason_code == SandboxReasonCode.SECRET_READ_DENIED

    @pytest.mark.parametrize(
        "command",
        [
            # CLI credential stores (corpus sweep: awslabs/git-secrets + OWASP)
            ["cat", "~/.config/gh/hosts.yml"],  # GitHub CLI
            ["cat", "~/.config/hub"],  # hub CLI
            ["cat", "~/.config/glab-cli/config.toml"],  # GitLab CLI
            ["cat", "~/.config/netlify/config.json"],  # Netlify CLI
            ["cat", "~/.config/heroku/netrc"],  # Heroku CLI
            ["cat", "~/.config/doctl/config.yaml"],  # DigitalOcean CLI
            ["cat", "~/.config/fly/config.yml"],  # Fly.io CLI
            ["cat", "~/.config/stripe/config.toml"],  # Stripe CLI
            ["cat", "~/.config/vercel/creds.json"],  # Vercel CLI
            ["cat", "~/.config/op/config"],  # 1Password CLI
            ["cat", "~/.1password/agent.sock"],  # 1Password agent
            ["cat", "~/.password-store/email.gpg"],  # pass manager
            ["cat", "~/.dbt/profiles.yml"],  # dbt (db creds)
        ],
    )
    def test_corpus_sweep_cli_credential_dirs_denied(self, tmp_path, command):
        with pytest.raises(SandboxPathViolation) as exc:
            validate_command_paths(command, self._policy(tmp_path))
        assert exc.value.reason_code == SandboxReasonCode.SECRET_READ_DENIED

    def test_runuser_is_unknown_deny_default(self):
        """runuser -l USER --command 'CMD' uses a shell string, not argv sublist.
        Cannot safely classify → UNKNOWN → deny-default. Intentional non-wrapper."""
        d = decide(["runuser", "-l", "agent", "--command", "curl https://x"], SandboxPolicy())
        assert d.allowed is False  # deny-default on UNKNOWN

    def test_normal_file_still_allowed(self, tmp_path):
        # Non-secret names that superficially resemble secret names
        (tmp_path / "env_config.txt").write_text("ok", encoding="utf-8")
        validate_command_paths(["cat", "env_config.txt"], self._policy(tmp_path))

    def test_file_named_like_history_but_different(self, tmp_path):
        # .bash_profile is not a secret sink (doesn't contain credentials)
        # Only the exact match set triggers denial
        (tmp_path / ".bash_profile").write_text("ok", encoding="utf-8")
        validate_command_paths(["cat", ".bash_profile"], self._policy(tmp_path))
