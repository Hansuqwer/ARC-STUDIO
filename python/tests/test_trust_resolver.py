"""
Tests: Workspace trust resolver — ADR-006 P1a advisory mode (PR 22).

Tests the external trust database, CLI commands, and the security
guarantee that a committed .arc/trusted file does not self-authorize.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.security.trust import (
    resolve_trust,
    trust_workspace,
    untrust_workspace,
    list_trusted,
    TrustLevel,
    TRUST_DB,
)
from agent_runtime_cockpit.cli import app


class TestTrustResolver:
    """Core trust resolution logic."""

    def test_untrusted_by_default(self, tmp_path):
        resolution = resolve_trust(tmp_path, trust_db=tmp_path / "trust-db.json")
        assert resolution.level == TrustLevel.UNTRUSTED
        assert "not found" in resolution.reason
        assert resolution.warning is not None

    def test_trust_workspace(self, tmp_path):
        trust_db = tmp_path / "trust-db.json"
        resolution = trust_workspace(tmp_path, note="my workspace", trust_db=trust_db)
        assert resolution.level == TrustLevel.TRUSTED
        assert "added" in resolution.reason

        # Verify persistence
        assert trust_db.exists()
        data = json.loads(trust_db.read_text())
        assert data[str(tmp_path.resolve())]["trusted"] is True
        assert data[str(tmp_path.resolve())]["note"] == "my workspace"

    def test_trust_then_resolve(self, tmp_path):
        trust_db = tmp_path / "trust-db.json"
        trust_workspace(tmp_path, trust_db=trust_db)
        resolution = resolve_trust(tmp_path, trust_db=trust_db)
        assert resolution.level == TrustLevel.TRUSTED

    def test_untrust_workspace(self, tmp_path):
        trust_db = tmp_path / "trust-db.json"
        trust_workspace(tmp_path, trust_db=trust_db)
        resolution = untrust_workspace(tmp_path, trust_db=trust_db)
        assert resolution.level == TrustLevel.UNTRUSTED
        assert "removed" in resolution.reason

        # Verify it's gone
        resolution2 = resolve_trust(tmp_path, trust_db=trust_db)
        assert resolution2.level == TrustLevel.UNTRUSTED

    def test_list_trusted(self, tmp_path):
        trust_db = tmp_path / "trust-db.json"
        assert list_trusted(trust_db=trust_db) == {}
        trust_workspace(tmp_path, trust_db=trust_db)
        trusted = list_trusted(trust_db=trust_db)
        assert str(tmp_path.resolve()) in trusted

    def test_missing_trust_db_returns_empty(self, tmp_path):
        trust_db = tmp_path / "nonexistent" / "db.json"
        assert list_trusted(trust_db=trust_db) == {}
        resolution = resolve_trust(tmp_path, trust_db=trust_db)
        assert resolution.level == TrustLevel.UNTRUSTED


class TestTrustCLI:
    """CLI commands for trust management."""

    def test_trust_status_untrusted(self, tmp_path):
        result = CliRunner().invoke(app, [
            "workspace", "trust-status",
            "--workspace", str(tmp_path),
            "--json",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)["data"]
        assert data["level"] == "untrusted"

    def test_trust_then_status(self, tmp_path):
        # Mark as trusted
        trust_result = CliRunner().invoke(app, [
            "workspace", "trust",
            "--workspace", str(tmp_path),
            "--note", "test workspace",
            "--json",
        ])
        assert trust_result.exit_code == 0, trust_result.output
        assert json.loads(trust_result.output)["data"]["level"] == "trusted"

        # Check status
        status_result = CliRunner().invoke(app, [
            "workspace", "trust-status",
            "--workspace", str(tmp_path),
            "--json",
        ])
        assert status_result.exit_code == 0, status_result.output
        assert json.loads(status_result.output)["data"]["level"] == "trusted"

    def test_untrust(self, tmp_path):
        # Trust first
        CliRunner().invoke(app, [
            "workspace", "trust",
            "--workspace", str(tmp_path),
            "--json",
        ])
        # Then untrust
        untrust_result = CliRunner().invoke(app, [
            "workspace", "untrust",
            "--workspace", str(tmp_path),
            "--json",
        ])
        assert untrust_result.exit_code == 0, untrust_result.output
        assert json.loads(untrust_result.output)["data"]["level"] == "untrusted"

        # Verify untrusted
        status_result = CliRunner().invoke(app, [
            "workspace", "trust-status",
            "--workspace", str(tmp_path),
            "--json",
        ])
        assert json.loads(status_result.output)["data"]["level"] == "untrusted"
