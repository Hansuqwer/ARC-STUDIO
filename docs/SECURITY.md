# Security

ARC Studio is an alpha Theia IDE and Python daemon. Treat unknown workspaces as untrusted.

## Trust Boundaries

- Theia frontend talks to the Theia backend over Theia JSON-RPC.
- Theia backend shells out to the ARC Python CLI with argv arrays, not shell strings.
- The Python daemon exposes local HTTP routes for IDE integration.
- Runtime adapters may invoke local runtime CLIs such as SwarmGraph.
- Provider APIs are external trust boundaries and must remain opt-in for live calls.

## Workspace Trust

Workspace trust is enabled in browser and Electron app preferences (`security.workspace.trust.enabled=true`). Do not disable it to work around extension bugs.

## Local Daemon

The daemon binds to `127.0.0.1` by default, and Theia backend daemon calls use `127.0.0.1` rather than `localhost` to avoid host resolution drift. CORS defaults to `http://127.0.0.1:3000` and can be overridden with `ARC_CORS_ORIGIN` for local development only.

## Secrets

Provider keys must not be written to traces, logs, screenshots, or test artifacts. Current provider support is dry-run metadata only; secure key storage is not implemented yet. Live provider smoke tests require `ARC_ALLOW_LIVE_PROVIDER_TESTS=true`.

## Subprocesses

Subprocess calls must pass arguments as arrays and must not use shell interpolation for workspace paths, prompts, or provider config.

## Electron

Unsigned smoke builds are local-only. Release packaging uses `electron-builder.release.yml` and requires signing credentials. Do not distribute smoke artifacts.

## Plugins, MCP, Tools

Only install plugins and MCP/tool servers from trusted sources. MCP servers and local tools can execute code or access workspace files.

## Disclosure

Use private repository security advisories or contact the maintainer before publishing security issues.
