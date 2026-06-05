"""Tests for the isolation backend selector + v1->v2 isolation migration (ADR-006)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.config.loader import load_config
from agent_runtime_cockpit.config.model import ArcConfig
from agent_runtime_cockpit.isolation import (
    build_isolation_provider,
    resolve_isolation_backend,
)
from agent_runtime_cockpit.isolation.base import IsolationProvider
from agent_runtime_cockpit.isolation.none import NoneIsolationProvider
from agent_runtime_cockpit.isolation.subprocess import SubprocessIsolationProvider


def test_default_config_resolves_to_subprocess() -> None:
    """Default config (isolation=auto) resolves to the hardened subprocess backend."""
    cfg = ArcConfig()
    assert cfg.execution.isolation == "auto"
    assert resolve_isolation_backend(cfg) == "subprocess"


def test_no_config_resolves_to_subprocess() -> None:
    assert resolve_isolation_backend(None) == "subprocess"


@pytest.mark.parametrize("backend", ["none", "subprocess", "docker", "microvm"])
def test_concrete_config_passthrough(backend: str) -> None:
    cfg = ArcConfig()
    cfg.execution.isolation = backend
    assert resolve_isolation_backend(cfg) == backend


def test_override_wins_over_config() -> None:
    cfg = ArcConfig()
    cfg.execution.isolation = "none"
    assert resolve_isolation_backend(cfg, override="microvm") == "microvm"


def test_override_auto_defers_to_config() -> None:
    cfg = ArcConfig()
    cfg.execution.isolation = "docker"
    assert resolve_isolation_backend(cfg, override="auto") == "docker"


def test_unknown_configured_value_fails_safe_to_subprocess() -> None:
    cfg = ArcConfig()
    cfg.execution.isolation = "bogus"
    assert resolve_isolation_backend(cfg) == "subprocess"


def test_unknown_override_raises() -> None:
    with pytest.raises(ValueError):
        resolve_isolation_backend(ArcConfig(), override="bogus")


def test_factory_builds_expected_providers(tmp_path: Path) -> None:
    assert isinstance(build_isolation_provider("none"), NoneIsolationProvider)
    assert isinstance(
        build_isolation_provider("subprocess", workspace_root=tmp_path),
        SubprocessIsolationProvider,
    )
    # docker + microvm construct even when their runtimes are absent; availability
    # is reported via status()/health_check(), not the constructor.
    for name in ("docker", "microvm"):
        assert isinstance(build_isolation_provider(name), IsolationProvider)


def test_factory_unknown_raises() -> None:
    with pytest.raises(ValueError):
        build_isolation_provider("bogus")


def test_v1_none_config_migrates_to_auto(tmp_path: Path) -> None:
    """A legacy v1 config with isolation=none upgrades to auto (preserves real behavior)."""
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("version: 1\nexecution:\n  isolation: none\n", encoding="utf-8")
    cfg = load_config(user_config_path=cfg_path)
    assert cfg.version == 2
    assert cfg.execution.isolation == "auto"
    assert resolve_isolation_backend(cfg) == "subprocess"


def test_v2_none_config_is_preserved(tmp_path: Path) -> None:
    """An explicit v2 opt-out (isolation=none) is NOT migrated away."""
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("version: 2\nexecution:\n  isolation: none\n", encoding="utf-8")
    cfg = load_config(user_config_path=cfg_path)
    assert cfg.version == 2
    assert cfg.execution.isolation == "none"
    assert resolve_isolation_backend(cfg) == "none"


def test_build_execution_provider_maps_backends_with_policy(tmp_path: Path) -> None:
    """The policy-aware builder used by every execution path maps each backend name."""
    from agent_runtime_cockpit.isolation.none import NoneIsolationProvider
    from agent_runtime_cockpit.isolation.selector import build_execution_provider
    from agent_runtime_cockpit.isolation.subprocess import SubprocessIsolationProvider

    sub = build_execution_provider(
        "subprocess",
        workspace_root=tmp_path,
        env_allowlist=frozenset({"PATH"}),
        max_output_bytes=1024,
    )
    assert isinstance(sub, SubprocessIsolationProvider)
    none = build_execution_provider(
        "none", workspace_root=tmp_path, env_allowlist=frozenset(), max_output_bytes=1024
    )
    assert isinstance(none, NoneIsolationProvider)
    for name in ("docker", "microvm"):
        prov = build_execution_provider(
            name, workspace_root=tmp_path, env_allowlist=frozenset(), max_output_bytes=1024
        )
        assert isinstance(prov, IsolationProvider)
