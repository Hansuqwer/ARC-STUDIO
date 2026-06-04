# AGENTS.md — arc-theia-studio

This file describes the agent instructions for the arc-theia-studio workspace.
It should be used by AI agents working in this repository to understand the
project structure, conventions, and boundaries.

## Project Structure

The arc-theia-studio monorepo contains:
- `python/` — Python CLI, TUI, and daemon (agent_runtime_cockpit)
- `packages/` — TypeScript packages for the Eclipse Theia IDE extension
- `applications/` — Theia browser application
- `docs/` — Architecture decisions, research, and roadmap
- `protocol/` — Cross-language protocol fixtures

## Development Conventions

- Python code uses ruff for linting, pytest for testing
- TypeScript uses ESLint and Jest
- All CLI commands emit JSON envelopes via `ok()` / `err()` helpers
- Tests must not depend on live network or external services
- Security-sensitive code requires audit annotations

## File Organization

When adding new Python modules:
- Source goes in `python/src/agent_runtime_cockpit/<module>/`
- Tests go in `python/tests/<module>/`
- CLI commands register in `cli/_subapps.py` then `cli/_app.py`

When adding TypeScript:
- Extension code in `packages/arc-extension/src/`
- Widget contributions follow Theia DI patterns

## Security Boundaries

- Sandbox policy enforced on all subprocess execution
- Paid calls gated behind `--allow-paid` flag
- Workspace trust required for file operations outside workspace
- Secrets never logged or included in JSON output

## Testing Requirements

- New features require unit tests
- CLI commands require integration tests with typer.testing.CliRunner
- No mocking of security boundaries in tests (test real enforcement)
- Fixtures in `python/tests/fixtures/`

## Agent Behavior Guidelines

When working in this repo:
- Read existing code before writing new code
- Match existing patterns (Typer subapps, Pydantic models, dataclasses)
- Use the protocol envelope for all CLI output
- Register new CLI commands properly through _subapps.py
- Keep changes small and reviewable
- Run `cd python && uv run ruff check src tests` before committing
- Run `cd python && uv run pytest tests/ -q` to verify

## Workspace Metadata

- Primary language: Python 3.11+
- Package manager: uv (Python), pnpm (Node)
- CI: GitHub Actions
- Release: v0.1.0-alpha

## Do Not

- Do not execute workflows without explicit user request
- Do not make network calls in tests
- Do not bypass security enforcement
- Do not create files outside the workspace tree
- Do not use shell=True in subprocess calls
- Do not log secrets or API keys

## arc-theia-studio Specific Patterns

The following identifiers are project-specific and should be recognized:
- `ArcEnvelope`, `EnforcementContext`, `CapabilityCard`
- `SwarmGraph`, `RuntimeAdapter`, `IsolationProvider`
- `EventBroker`, `JobSupervisor`, `ChatSession`
- `arc sandbox`, `arc policy`, `arc providers`

## Context Retrieval

This workspace uses a context retrieval engine with providers:
- Local repo search
- Context7 documentation
- GitHub code search
- Web search (gated)

Agents should use `arc context` commands to retrieve relevant information
before making changes to unfamiliar code.
