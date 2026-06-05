"""ARC config loader — YAML loading with precedence (ADR-001).

Precedence order (highest wins):
1. CLI arguments (not resolved here — caller overrides)
2. Environment variables (``ARC_*`` prefixed)
3. Workspace config (``<workspace>/.arc/config.yaml``)
4. User config (``~/.arc/config.yaml``)
5. Built-in defaults (defined in ``model.py``)

Secrets policy: config files must never contain API keys.
All secret references use env var names.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from .model import ArcConfig

log = logging.getLogger(__name__)

ARC_CONFIG_VERSION = 2
DEFAULT_CONFIG_PATH = Path(".arc") / "config.yaml"
USER_CONFIG_PATH = Path.home() / ".arc" / "config.yaml"

# Environment variable -> config key mapping
ENV_TO_CONFIG: dict[str, str] = {
    "ARC_SWARMGRAPH_RUN_BACKEND": "swarmgraph.run_backend",
    "ARC_SWARMGRAPH_PROVIDER": "swarmgraph.provider",
    "ARC_OTEL_GENAI_EXPERIMENTAL": "telemetry.otel_genai_experimental",
}

# Env vars that are read directly by adapters (not stored in config model)
_IGNORED_ENV_KEYS = frozenset(
    {
        "ARC_HMAC_KEY",
        "ARC_DEBUG",
        "ARC_ALLOW_LIVE_ARENA",
        "ARC_SWARMGRAPH_CLI",
    }
)


def load_config(
    workspace: Optional[Path] = None,
    *,
    user_config_path: Path = USER_CONFIG_PATH,
) -> ArcConfig:
    """Load and merge ARC config with full precedence.

    1. Start with built-in defaults (``ArcConfig()``)
    2. Overlay user config (``~/.arc/config.yaml``)
    3. Overlay workspace config (``<workspace>/.arc/config.yaml``)
    4. Overlay environment variables (``ARC_*``)
    """
    config = ArcConfig()

    # Step 2: User config
    if user_config_path.exists():
        try:
            user_data = _load_yaml(user_config_path)
            config = _merge_dict_into_config(config, user_data)
        except Exception as e:
            log.warning("Failed to load user config %s: %s", user_config_path, e)

    # Step 3: Workspace config
    if workspace:
        ws_path = workspace / DEFAULT_CONFIG_PATH
        if ws_path.exists():
            try:
                ws_data = _load_yaml(ws_path)
                config = _merge_dict_into_config(config, ws_data)
            except Exception as e:
                log.warning("Failed to load workspace config %s: %s", ws_path, e)

    # Step 4: Environment variable overrides
    config = _apply_env_overrides(config)

    # Step 5: forward-compatible schema migrations
    config = _migrate_config(config)

    return config


def _migrate_config(config: ArcConfig) -> ArcConfig:
    """Apply forward-compatible schema migrations.

    v1 -> v2: ``execution.isolation`` was display-only and defaulted to
    ``"none"`` (the YAML template wrote it into every workspace) but was never
    wired to provider selection, so the effective behavior was always
    ``subprocess``. Upgrade a legacy ``"none"`` to ``"auto"`` so wiring the
    isolation selector does not silently disable isolation on already-
    initialized workspaces. A deliberate opt-out is re-set via ``arc isolation off``.
    """
    if config.version >= ARC_CONFIG_VERSION:
        return config
    data = config.model_dump()
    if config.version < 2 and data.get("execution", {}).get("isolation") == "none":
        data["execution"]["isolation"] = "auto"
    data["version"] = ARC_CONFIG_VERSION
    return ArcConfig.model_validate(data)


def init_config(workspace: Path) -> Path:
    """Generate a default ``.arc/config.yaml`` in the given workspace.

    Does not overwrite an existing config. Returns the path.
    """
    config_path = workspace / DEFAULT_CONFIG_PATH
    if config_path.exists():
        log.info("Config already exists: %s", config_path)
        return config_path
    config_path.parent.mkdir(parents=True, exist_ok=True)
    default = _generate_default_yaml()
    config_path.write_text(default, encoding="utf-8")
    log.info("Created default config: %s", config_path)
    return config_path


def set_isolation_backend(name: str, *, config_path: Path) -> Path:
    """Persist ``execution.isolation`` in ``config_path``, preserving other keys.

    Creates the file (stamped with the current schema version) when absent.
    Returns the path that was written.
    """
    data = _load_yaml(config_path) if config_path.exists() else {}
    data.setdefault("version", ARC_CONFIG_VERSION)
    execution = data.get("execution")
    if not isinstance(execution, dict):
        execution = {}
    execution["isolation"] = name
    data["execution"] = execution
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return config_path


def _load_yaml(path: Path) -> dict:
    """Load a YAML file, returning a dict."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return {}
    return data


def _merge_dict_into_config(config: ArcConfig, data: dict) -> ArcConfig:
    """Deep-merge a nested dict into an existing ArcConfig."""
    current = config.model_dump()
    _deep_merge(current, data)
    return ArcConfig.model_validate(current)


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override dict into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _apply_env_overrides(config: ArcConfig) -> ArcConfig:
    """Apply ARC_* environment variable overrides to config."""
    overrides: dict = {}
    for env_key, config_key in ENV_TO_CONFIG.items():
        if not config_key or env_key in _IGNORED_ENV_KEYS:
            continue
        value = os.environ.get(env_key)
        if value is not None:
            _set_nested(overrides, config_key, _coerce_value(value))
    if overrides:
        current = config.model_dump()
        _deep_merge(current, overrides)
        return ArcConfig.model_validate(current)
    return config


def _set_nested(d: dict, key: str, value: Any) -> None:
    """Set a dotted key (e.g. 'swarmgraph.run_backend') in a nested dict."""
    parts = key.split(".")
    current = d
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _coerce_value(value: str) -> Any:
    """Coerce string env value to bool/int if applicable."""
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    return value


_YAML_TEMPLATE = """# ARC Studio workspace configuration (ADR-001)
# Schema version for forward compatibility
version: 2

# Workspace identity
workspace:
  name: ""
  trust_level: auto

# Runtime selection
runtime:
  default: auto
  auto_detect: true
  fallback: stub

# Execution settings
execution:
  isolation: auto
  default_profile: local-safe
  timeout_seconds: 300
  allow_paid_calls: false
  background: false

# Provider routing (workspace-level overrides)
providers:
  default_provider: openai
  default_model: gpt-4.1-mini
  routing_mode: manual
  dry_run: true
  accounts: []

# SwarmGraph-specific
swarmgraph:
  provider: openai
  base_url: ""
  run_backend: stub
  cli_path: ""

# LangGraph-specific
langgraph:
  export: ""

# CrewAI-specific
crewai:
  export: ""

# Context providers
context:
  search_provider: brave
  context7_api_key_env: ""
  github_token_env: ""

# Telemetry
telemetry:
  otel_endpoint: ""
  otel_genai_experimental: false

# UI preferences (workspace-specific)
ui:
  show_mock_warnings: true
  compact_sidebar: false
  auto_open_sidebar: true

# Security
security:
  redact_secrets: true
  audit_enabled: false
  audit_secret_env: ""
  allowed_paths: []
  allowed_hosts: []
"""


def _generate_default_yaml() -> str:
    return _YAML_TEMPLATE
