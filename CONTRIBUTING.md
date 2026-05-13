# Contributing to ARC Studio

## Setup

```bash
cd python
uv sync --all-extras --dev
.venv/bin/python -m pytest

cd ..
pnpm install
pnpm build
```

## Development Workflow

1. Create a feature branch from `build/no-mockups-handoff`
2. Make changes following the architectural decisions in `docs/IMPLEMENTATION_DECISIONS.md`
3. Add or update tests
4. Run all checks: `bash scripts/check.sh`
5. Update documentation if needed
6. Submit a pull request

## Test Commands

```bash
# Python tests
cd python
.venv/bin/python -m pytest
.venv/bin/arc inspect --json
.venv/bin/arc adapter test swarmgraph --json
.venv/bin/arc adapter test langgraph --json

# Node.js tests
cd ..
node tests/unit/arc-protocol.test.js
node packages/arc-test-fixtures/src/index.js
pnpm -r test

# All checks
bash scripts/check.sh
```

## Code Style

### TypeScript
- Follow Theia conventions
- Use 4-space indentation
- Add JSDoc comments for public APIs
- Use explicit types (avoid `any`)

### Python
- Follow PEP 8 with type hints
- Use 4-space indentation
- Add docstrings for functions

### Commit Messages
Use conventional commits:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code refactoring
- `test:` — Adding tests
- `chore:` — Build/tooling changes

## Mock Policy

- Normal product paths must not silently return mock success.
- Test fixtures and demo helpers are allowed only when clearly named and marked.
- Runtime capabilities must describe real product behavior, not fixture behavior.
- If a dependency, daemon, or runtime is unavailable, return an explicit error.

## Definition Of Done

- Tests added or updated.
- Python tests pass (`cd python && .venv/bin/python -m pytest`).
- Node/Theia build checked (`pnpm build`).
- Docs updated with verified command output.
- No venvs, caches, node modules, generated build output, or secrets committed.

## Pull Request Guidelines

**PR Title:** Use conventional commit format
```
feat: add trace visualization component
fix: handle missing trace files
docs: update API documentation
```

**PR Description:** Include:
- What changed and why
- How to test the changes
- Screenshots (for UI changes)
- Related issues

## Getting Help

- Read `docs/DEVELOPMENT.md` for setup and debugging
- Check `docs/TROUBLESHOOTING.md` for common issues
- Search [GitHub Issues](https://github.com/Hansuqwer/arc-theia-studio/issues)
- Create an issue with environment details, steps to reproduce, and logs
