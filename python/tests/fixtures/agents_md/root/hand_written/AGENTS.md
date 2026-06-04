# AGENTS.md — arc-theia-studio hand-written instructions

This file is hand-written for the arc-theia-studio project. It uses
project-specific terminology and has no excessive emoji or repetitive
phrasing.

## arc-theia-studio Workspace Rules

The CapabilityCard system uses SHA-256 hashing for integrity.
EnforcementContext gates all operations.
SwarmGraph IR is compiled from workflow definitions.

## Coding Patterns

- Typer subapps in `_subapps.py`
- Pydantic models with `extra="ignore"`
- Dataclass for immutable state
- ArcEnvelope for all CLI output

## Module Map

python/src/agent_runtime_cockpit/
  cli/          → command handlers
  security/     → sandbox, enforcement
  isolation/    → subprocess, container, microvm
  capabilities/ → typed cards

## Test Conventions

- pytest with tmp_path fixtures
- monkeypatch for OS/env stubs
- CliRunner for CLI integration
- No live network in CI
