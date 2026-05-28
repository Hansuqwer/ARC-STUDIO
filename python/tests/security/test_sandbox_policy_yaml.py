"""Tests for Phase 35 YAML sandbox policy support."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.security.sandbox import (
    apply_sandbox_policy_yaml,
    default_workspace_policy_path,
    resolve_sandbox_policy,
    resolve_sandbox_policy_with_yaml,
    validate_sandbox_policy_yaml,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_YAML = """\
version: 1
name: dev-safe
allow_network: false
allow_install: false
allow_privileged: false
allow_unknown: false
"""

VALID_FULL_YAML = """\
version: 1
name: full-policy
allow_network: true
allow_install: false
allow_privileged: false
allow_unknown: true
timeout_seconds: 60
max_output_bytes: 32768
"""


def _write_yaml(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _payload(result):
    return json.loads(result.output)


# ---------------------------------------------------------------------------
# 1. validate_sandbox_policy_yaml — valid minimal YAML → ok=True
# ---------------------------------------------------------------------------


def test_validate_minimal_yaml_ok(tmp_path):
    p = _write_yaml(tmp_path / "policy.yaml", VALID_YAML)
    result = validate_sandbox_policy_yaml(p)
    assert result["ok"] is True
    assert result["policy_name"] == "dev-safe"
    assert result["errors"] == []


# ---------------------------------------------------------------------------
# 2. validate_sandbox_policy_yaml — missing name → ok=False
# ---------------------------------------------------------------------------


def test_validate_yaml_missing_name(tmp_path):
    content = "version: 1\nallow_network: false\n"
    p = _write_yaml(tmp_path / "policy.yaml", content)
    result = validate_sandbox_policy_yaml(p)
    assert result["ok"] is False
    assert any("missing" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# 3. validate_sandbox_policy_yaml — wrong version → ok=False
# ---------------------------------------------------------------------------


def test_validate_yaml_wrong_version(tmp_path):
    content = "version: 2\nname: bad\nallow_network: false\n"
    p = _write_yaml(tmp_path / "policy.yaml", content)
    result = validate_sandbox_policy_yaml(p)
    assert result["ok"] is False
    assert any("version" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# 4. validate_sandbox_policy_yaml — non-bool allow_network → ok=False
# ---------------------------------------------------------------------------


def test_validate_yaml_non_bool_allow_network(tmp_path):
    content = "version: 1\nname: bad\nallow_network: yes_please\n"
    p = _write_yaml(tmp_path / "policy.yaml", content)
    result = validate_sandbox_policy_yaml(p)
    assert result["ok"] is False
    assert any("allow_network" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# 5. validate_sandbox_policy_yaml — non-existent file → ok=False
# ---------------------------------------------------------------------------


def test_validate_yaml_nonexistent_file(tmp_path):
    p = tmp_path / "no-such-file.yaml"
    result = validate_sandbox_policy_yaml(p)
    assert result["ok"] is False
    assert result["errors"]


# ---------------------------------------------------------------------------
# 6. validate_sandbox_policy_yaml — valid full policy → ok=True, policy_name matches
# ---------------------------------------------------------------------------


def test_validate_full_yaml_ok(tmp_path):
    p = _write_yaml(tmp_path / "full.yaml", VALID_FULL_YAML)
    result = validate_sandbox_policy_yaml(p)
    assert result["ok"] is True
    assert result["policy_name"] == "full-policy"
    assert result["errors"] == []


# ---------------------------------------------------------------------------
# 7. apply_sandbox_policy_yaml — valid file → ok=True, file copied to target
# ---------------------------------------------------------------------------


def test_apply_yaml_valid_copies_file(tmp_path):
    src = _write_yaml(tmp_path / "src.yaml", VALID_YAML)
    ws = tmp_path / "workspace"
    ws.mkdir()
    result = apply_sandbox_policy_yaml(src, ws)
    assert result["ok"] is True
    target = Path(result["target"])
    assert target.exists()
    assert target.read_text(encoding="utf-8") == VALID_YAML
    assert result["policy_name"] == "dev-safe"
    assert result["errors"] == []


# ---------------------------------------------------------------------------
# 8. apply_sandbox_policy_yaml — invalid file → ok=False, not copied
# ---------------------------------------------------------------------------


def test_apply_yaml_invalid_not_copied(tmp_path):
    src = _write_yaml(tmp_path / "bad.yaml", "version: 1\nallow_network: false\n")  # no name
    ws = tmp_path / "workspace"
    ws.mkdir()
    default_target = default_workspace_policy_path(ws)
    result = apply_sandbox_policy_yaml(src, ws)
    assert result["ok"] is False
    assert not default_target.exists()


# ---------------------------------------------------------------------------
# 9. apply_sandbox_policy_yaml — creates parent dirs if missing
# ---------------------------------------------------------------------------


def test_apply_yaml_creates_parent_dirs(tmp_path):
    src = _write_yaml(tmp_path / "policy.yaml", VALID_YAML)
    ws = tmp_path / "deep" / "workspace"
    # ws does not exist yet; apply should create .arc/ under it
    target = ws / ".arc" / "sandbox-policy.yaml"
    result = apply_sandbox_policy_yaml(src, ws, target_path=target)
    assert result["ok"] is True
    assert target.exists()


# ---------------------------------------------------------------------------
# 10. resolve_sandbox_policy_with_yaml — finds policy by name from workspace YAML
# ---------------------------------------------------------------------------


def test_resolve_with_yaml_workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    arc_dir = ws / ".arc"
    arc_dir.mkdir()
    _write_yaml(arc_dir / "sandbox-policy.yaml", VALID_YAML)
    policy = resolve_sandbox_policy_with_yaml("dev-safe", ws)
    assert policy.name == "dev-safe"
    assert policy.allow_network is False


# ---------------------------------------------------------------------------
# 11. resolve_sandbox_policy_with_yaml — falls back to user YAML when workspace absent
# ---------------------------------------------------------------------------


def test_resolve_with_yaml_user_fallback(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    ws.mkdir()
    user_yaml = tmp_path / "user_home" / ".arc" / "sandbox-policy.yaml"
    user_yaml.parent.mkdir(parents=True)
    _write_yaml(user_yaml, VALID_YAML)
    # Patch default_user_sandbox_policy_path via monkeypatch on module level
    import agent_runtime_cockpit.security.sandbox as _mod

    monkeypatch.setattr(_mod, "default_user_sandbox_policy_path", lambda: user_yaml)
    policy = resolve_sandbox_policy_with_yaml("dev-safe", ws)
    assert policy.name == "dev-safe"


# ---------------------------------------------------------------------------
# 12. resolve_sandbox_policy_with_yaml — raises KeyError when not found anywhere
# ---------------------------------------------------------------------------


def test_resolve_with_yaml_not_found(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    with pytest.raises(KeyError, match="not found"):
        resolve_sandbox_policy_with_yaml("nonexistent-policy", ws)


# ---------------------------------------------------------------------------
# 13. resolve_sandbox_policy (modified) falls through to YAML lookup on KeyError
# ---------------------------------------------------------------------------


def test_resolve_sandbox_policy_fallthrough_to_yaml(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    arc_dir = ws / ".arc"
    arc_dir.mkdir()
    _write_yaml(arc_dir / "sandbox-policy.yaml", VALID_YAML)
    # JSON store does not exist → should fall through to workspace YAML
    policy = resolve_sandbox_policy("dev-safe", ws, path=tmp_path / "no-store.json")
    assert policy.name == "dev-safe"


# ---------------------------------------------------------------------------
# 14. CLI arc policy validate-yaml --file <valid_yaml> → ok=true JSON
# ---------------------------------------------------------------------------


def test_cli_validate_yaml_valid(tmp_path):
    p = _write_yaml(tmp_path / "policy.yaml", VALID_YAML)
    result = CliRunner().invoke(app, ["policy", "validate-yaml", "--json", "--file", str(p)])
    assert result.exit_code == 0, result.output
    data = _payload(result)
    assert data["ok"] is True
    assert data["data"]["ok"] is True
    assert data["data"]["policy_name"] == "dev-safe"


# ---------------------------------------------------------------------------
# 15. CLI arc policy validate-yaml --file <invalid_yaml> → ok=false, exit 1
# ---------------------------------------------------------------------------


def test_cli_validate_yaml_invalid(tmp_path):
    content = "version: 1\nallow_network: false\n"  # no name
    p = _write_yaml(tmp_path / "bad.yaml", content)
    result = CliRunner().invoke(app, ["policy", "validate-yaml", "--json", "--file", str(p)])
    assert result.exit_code == 1
    data = _payload(result)
    assert data["data"]["ok"] is False
    assert data["data"]["errors"]


# ---------------------------------------------------------------------------
# 16. CLI arc policy apply --file <valid_yaml> → ok=true, file copied
# ---------------------------------------------------------------------------


def test_cli_apply_yaml_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ws = tmp_path
    src = _write_yaml(tmp_path / "policy.yaml", VALID_YAML)
    target = tmp_path / "dest" / "sandbox-policy.yaml"
    result = CliRunner().invoke(
        app,
        [
            "policy",
            "apply",
            "--json",
            "--file",
            str(src),
            "--workspace",
            str(ws),
            "--target",
            str(target),
        ],
    )
    assert result.exit_code == 0, result.output
    data = _payload(result)
    assert data["data"]["ok"] is True
    assert target.exists()
