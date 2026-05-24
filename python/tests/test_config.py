"""Tests: ARC config model and loader (ADR-001)."""

from __future__ import annotations

from pathlib import Path

from agent_runtime_cockpit.config import ArcConfig, init_config, load_config
from agent_runtime_cockpit.config.model import (
    ExecutionConfig,
    WorkspaceConfig,
)


class TestArcConfigModel:
    """Pydantic config model defaults and round-trip."""

    def test_default_config(self):
        config = ArcConfig()
        assert config.version == 1
        assert config.workspace.trust_level == "auto"
        assert config.runtime.default == "auto"
        assert config.execution.isolation == "none"
        assert config.execution.default_profile == "local-safe"
        assert config.providers.default_provider == "openai"
        assert config.swarmgraph.run_backend == "stub"
        assert config.security.redact_secrets is True

    def test_config_json_roundtrip(self):
        config = ArcConfig()
        json_str = config.model_dump_json()
        restored = ArcConfig.model_validate_json(json_str)
        assert restored == config

    def test_flatten(self):
        config = ArcConfig(
            workspace=WorkspaceConfig(name="test-ws"),
            execution=ExecutionConfig(timeout_seconds=600),
        )
        flat = config.flatten()
        assert flat["workspace.name"] == "test-ws"
        assert flat["execution.timeout_seconds"] == 600
        assert flat["version"] == 1


class TestLoadConfig:
    """Config loading with precedence."""

    def test_load_defaults_with_no_files(self, tmp_path: Path):
        config = load_config(tmp_path)
        assert config.version == 1
        assert config.runtime.default == "auto"

    def test_load_workspace_config(self, tmp_path: Path):
        ws = tmp_path / "workspace"
        ws.mkdir(parents=True)
        config_dir = ws / ".arc"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("""
version: 1
runtime:
  default: langgraph
execution:
  isolation: subprocess
  timeout_seconds: 600
swarmgraph:
  run_backend: local
""")
        config = load_config(ws)
        assert config.runtime.default == "langgraph"
        assert config.execution.isolation == "subprocess"
        assert config.execution.timeout_seconds == 600
        assert config.swarmgraph.run_backend == "local"
        # Verify other defaults are preserved
        assert config.workspace.trust_level == "auto"

    def test_load_user_config_overrides(self, tmp_path: Path):
        user_config = tmp_path / "user_config.yaml"
        user_config.write_text("""
version: 1
execution:
  allow_paid_calls: true
providers:
  default_provider: anthropic
""")
        config = load_config(tmp_path, user_config_path=user_config)
        assert config.execution.allow_paid_calls is True
        assert config.providers.default_provider == "anthropic"

    def test_workspace_overrides_user(self, tmp_path: Path):
        user_config = tmp_path / "user_config.yaml"
        user_config.write_text("execution:\n  timeout_seconds: 100")
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".arc").mkdir(parents=True)
        (ws / ".arc" / "config.yaml").write_text("execution:\n  timeout_seconds: 999")

        config = load_config(ws, user_config_path=user_config)
        # Workspace config should win over user config
        assert config.execution.timeout_seconds == 999

    def test_env_var_overrides(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "gateway")
        monkeypatch.setenv("ARC_SWARMGRAPH_PROVIDER", "anthropic")
        config = load_config(tmp_path)
        assert config.swarmgraph.run_backend == "gateway"
        assert config.swarmgraph.provider == "anthropic"

    def test_env_var_boolean_coercion(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("ARC_OTEL_GENAI_EXPERIMENTAL", "true")
        config = load_config(tmp_path)
        assert config.telemetry.otel_genai_experimental is True

    def test_invalid_yaml_does_not_crash(self, tmp_path: Path):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".arc").mkdir(parents=True)
        (ws / ".arc" / "config.yaml").write_text("{{invalid yaml")
        # Should not raise — falls back to defaults with warning
        config = load_config(ws)
        assert config.version == 1


class TestInitConfig:
    """Config file generation."""

    def test_init_creates_file(self, tmp_path: Path):
        ws = tmp_path / "ws"
        ws.mkdir()
        config_path = init_config(ws)
        assert config_path.exists()
        content = config_path.read_text()
        assert "version: 1" in content
        assert "execution:" in content
        assert "swarmgraph:" in content

    def test_init_does_not_overwrite(self, tmp_path: Path):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".arc").mkdir(parents=True)
        existing = ws / ".arc" / "config.yaml"
        existing.write_text("custom: content")
        init_config(ws)
        assert existing.read_text() == "custom: content"


class TestCLIConfig:
    """CLI contract tests for arc config commands."""

    def test_config_init(self, tmp_path: Path):
        from typer.testing import CliRunner

        from agent_runtime_cockpit.cli import app

        ws = tmp_path / "ws"
        ws.mkdir()
        result = CliRunner().invoke(app, ["config", "init", "--workspace", str(ws), "--json"])
        assert result.exit_code == 0, result.output
        import json

        data = json.loads(result.output)["data"]
        assert data["version"] == 1
        assert (ws / ".arc" / "config.yaml").exists()

    def test_config_show(self, tmp_path: Path):
        from typer.testing import CliRunner

        from agent_runtime_cockpit.cli import app

        ws = tmp_path / "ws"
        ws.mkdir(parents=True)
        result = CliRunner().invoke(app, ["config", "show", "--workspace", str(ws), "--json"])
        assert result.exit_code == 0, result.output
        import json

        data = json.loads(result.output)["data"]
        assert data["version"] == 1
        assert data["runtime.default"] == "auto"
