# ADR-001: Configuration Model and Precedence

## Status
Proposed

## Context

ARC Studio currently has configuration scattered across:
- CLI arguments (Typer flags)
- Environment variables (~40+ `ARC_*` vars)
- Runtime-generated JSON files (`~/.arc/providers.json`, `~/.arc/provider-routing.json`, `~/.arc/provider-quota.json`)
- Theia preferences (`arc-settings`, `arc-core` UI preferences)
- Run profiles (`security/profiles.py`)
- No unified `.arc/config` file exists at workspace level

This creates confusion about precedence, makes workspace-specific configuration difficult, and prevents declarative project-level ARC setup.

## Decision

### Workspace Config File: `.arc/config.yaml`

Create a workspace-level configuration file at `<workspace>/.arc/config.yaml` with the following schema:

```yaml
# .arc/config.yaml - ARC Studio workspace configuration
# Schema version for forward compatibility
version: 1

# Workspace identity
workspace:
  name: string              # Optional human-readable name
  trust_level: auto | trusted | partial | untrusted  # Default: auto

# Runtime selection
runtime:
  default: string           # Default runtime: swarmgraph, langgraph, crewai, etc.
  auto_detect: true         # Auto-detect runtime from workflow files
  fallback: stub            # Fallback when detection fails

# Execution settings
execution:
  isolation: none | subprocess | docker | orbstack | firecracker
  default_profile: stub | local-safe | local-paid | gateway
  timeout_seconds: 300
  allow_paid_calls: false
  background: false         # Default to foreground execution

# Provider routing (workspace-level overrides)
providers:
  default_provider: openai
  default_model: gpt-4.1-mini
  routing_mode: manual | priority | fallback
  dry_run: true
  accounts: []              # References to env vars, never inline keys

# SwarmGraph-specific
swarmgraph:
  provider: openai
  base_url: ""              # Optional gateway URL
  run_backend: stub | local | gateway
  cli_path: ""              # Optional explicit CLI path

# LangGraph-specific
langgraph:
  export: ""                # module:function export target

# CrewAI-specific
crewai:
  export: ""                # module:attribute export target

# Context providers
context:
  search_provider: brave
  context7_api_key_env: ""  # Env var name, not value
  github_token_env: ""      # Env var name, not value

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
  audit_enabled: false      # Enable HMAC audit chain
  audit_secret_env: ""      # Env var name for HMAC secret
  allowed_paths: []         # Filesystem path allowlist (future)
  allowed_hosts: []         # Network host allowlist (future)
```

### Config File Locations and Precedence

Configuration is resolved in the following precedence order (highest to lowest):

1. **CLI arguments** — explicit flags always win
2. **Environment variables** — `ARC_*` prefixed vars override config files
3. **Workspace config** — `<workspace>/.arc/config.yaml` (project-specific)
4. **User config** — `~/.arc/config.yaml` (user-level defaults)
5. **Built-in defaults** — stub backend, dry-run, localhost-only

### Environment Variable Mapping

Environment variables map to config keys using a deterministic convention:
- `ARC_DAEMON_PORT` → `daemon.port`
- `ARC_SWARMGRAPH_RUN_BACKEND` → `swarmgraph.run_backend`
- `ARC_SWARMGRAPH_ALLOW_COSTS` → `execution.allow_paid_calls` (dual-gate)
- `ARC_OTEL_GENAI_EXPERIMENTAL` → `telemetry.otel_genai_experimental`

All existing env vars remain supported for backward compatibility.

### Secrets Policy

- **Never** store API keys or secrets in `.arc/config.yaml`
- All secret references use env var names (e.g., `api_key_env: OPENAI_API_KEY`)
- The config loader resolves env vars at runtime
- `.arc/` is already in `.gitignore` but config should be safe to commit (no secrets)

### Config Loading API

```python
# Python
from agent_runtime_cockpit.config import load_config, Config

config = load_config(workspace_path="/path/to/workspace")
# Returns merged Config with full precedence applied
config.swarmgraph.run_backend  # resolved value
config.execution.allow_paid_calls  # resolved value
```

```typescript
// TypeScript
import { loadArcConfig } from '@arc/config';

const config = await loadArcConfig(workspacePath);
// Returns merged config with full precedence applied
```

### Migration Path

- Phase 1: Create config schema and loader (read-only, no behavior change)
- Phase 2: Wire config loader into daemon and CLI (env vars still override)
- Phase 3: Add `arc config init` CLI command to generate `.arc/config.yaml`
- Phase 4: Deprecate redundant env vars in favor of config file
- Phase 5: Add `arc config show` and `arc config set` for CLI-driven config management

## Consequences

### Positive
- Single source of truth for workspace-level ARC configuration
- Declarative, version-controllable project setup
- Clear precedence rules eliminate configuration confusion
- Enables workspace-specific provider/runtime settings
- Safe to commit to git (no secrets)

### Negative
- Adds a new config file to manage
- Requires migration code to maintain backward compatibility with env vars
- Two config formats (YAML for workspace, JSON for `~/.arc/` runtime state)

### Neutral
- Theia preferences remain separate (IDE-specific, not workspace-specific)
- Runtime state files (`providers.json`, `provider-quota.json`) remain JSON (frequent writes)
- Config is read once at startup, not watched for changes

## References
- Current env vars: `python/src/agent_runtime_cockpit/providers.py:89-180`
- Current profiles: `python/src/agent_runtime_cockpit/security/profiles.py:9-42`
- Theia preferences: `theia-extensions/arc-settings/src/common/arc-preference-schema.ts`
- CLI arguments: `python/src/agent_runtime_cockpit/cli.py`
