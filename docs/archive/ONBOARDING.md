# Developer Onboarding Guide

**Project:** ARC Studio  
**Version:** 0.6.0-alpha  
**Date:** 2026-05-13  

---

Welcome to ARC Studio! This guide will get you from zero to your first contribution in 3 days.

---

## Day 1: Setup

### Prerequisites Check

```bash
node --version    # >= 18.0.0
pnpm --version    # >= 8.0.0
python --version  # >= 3.11
git --version
which swarmgraph  # Should return path (optional for basic dev)
```

If any prerequisite is missing:
- **Node.js:** Install via nvm (`nvm install 18`)
- **pnpm:** `npm install -g pnpm`
- **Python:** Install via pyenv or system package manager
- **SwarmGraph:** https://github.com/Hansuqwer/SwarmGraph

### Clone and Install

```bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio
git checkout build/no-mockups-handoff

# Install all dependencies
pnpm install

# Build all packages
pnpm build
```

Expected build time: 2-5 minutes on first run.

### Start the Application

```bash
pnpm start:browser
```

Open http://localhost:3000 in your browser. You should see:
- Theia workbench with activity bar
- ARC Studio widget accessible via sidebar icon
- No console errors

### Verify Python Backend

```bash
cd python
uv sync --all-extras --dev
uv run arc --help
uv run arc inspect --json
```

### Run Tests

```bash
# Node.js tests
pnpm test

# Python tests
cd python && uv run pytest -v

# E2E tests (Playwright)
pnpm test:e2e
```

All tests should pass. If not, see `docs/TROUBLESHOOTING.md`.

### End of Day 1 Checklist

- [ ] Repository cloned and dependencies installed
- [ ] Build succeeds (`pnpm build`)
- [ ] Application starts on port 3000
- [ ] ARC widget visible in sidebar
- [ ] All tests pass
- [ ] Python CLI works (`arc --help`)

---

## Day 2: Codebase Tour

### Read These Documents (in order)

1. `README.md` — Project overview (10 min)
2. `docs/ARCHITECTURE.md` — System architecture (20 min)
3. `docs/DEVELOPMENT.md` — Development workflow (15 min)
4. `docs/IMPLEMENTATION_DECISIONS.md` — Why things are the way they are (15 min)
5. `docs/SECURITY.md` — Security model (10 min)

### Explore Key Files

#### Protocol Layer (start here)

```
packages/arc-extension/src/common/arc-protocol.ts
```

This defines the `ArcService` interface — the contract between frontend and backend. Read through:
- The 7 method signatures
- All type definitions (ExecutionOptions, ExecutionResult, TraceEvent, etc.)
- Error codes (ArcErrorCode enum)

#### Backend Service

```
packages/arc-extension/src/node/arc-backend-service.ts
```

Core business logic. Key sections:
- `executeWorkflow()` — How SwarmGraph CLI is spawned
- `getTraces()` / `readTrace()` — Trace file management
- `detectWorkflows()` — Workspace scanning logic
- Security utilities integration

#### Frontend Widget

```
packages/arc-extension/src/browser/arc-widget.tsx
```

Main UI component. Key sections:
- `render()` — Layout structure
- `executeWorkflow()` — User interaction flow
- `loadTraces()` — Trace list rendering
- Toast notifications

#### Security Layer

```
packages/arc-extension/src/node/security-utils.ts
```

Read through:
- `sanitizePrompt()` — Input validation
- `validateTraceId()` — Path traversal prevention
- `getSafeEnv()` — Environment allow-list

#### Python Backend

```
python/src/routes.py          # FastAPI endpoints
python/src/security_utils.py  # Python security utilities
python/src/daemon/            # Run management, SSE streaming
```

### Understand the Data Flow

Trace a complete workflow execution:

1. User clicks "Execute Workflow" in widget
2. `arc-widget.tsx` calls `this.arcService.executeWorkflow()`
3. JSON-RPC sends request to backend
4. `arc-backend-service.ts` validates input via `security-utils.ts`
5. Backend spawns `swarmgraph` subprocess with `shell: false`
6. SwarmGraph writes JSONL events to `.arc/traces/run-sg-{hash}.jsonl`
7. Backend parses output, returns `ExecutionResult`
8. Widget displays result and toast notification

### Run in Watch Mode

```bash
# Terminal 1: Watch mode (auto-rebuild on changes)
pnpm watch

# Terminal 2: Start application
pnpm start:browser
```

Make a small change (e.g., add a console.log) and verify it appears in the browser.

### End of Day 2 Checklist

- [ ] Read all core documentation
- [ ] Understand the protocol layer
- [ ] Can trace a workflow execution through the codebase
- [ ] Know where security validation happens
- [ ] Watch mode working for development
- [ ] Can run and debug both Node.js and Python code

---

## Day 3: First Contribution

### Pick a Good First Issue

Look for issues labeled `good first issue` on GitHub:
https://github.com/Hansuqwer/arc-theia-studio/issues

Good starting areas:
- UI improvements (CSS, widget layout)
- Error message improvements
- Test additions
- Documentation updates

### Make Your Change

1. **Create a branch:**
   ```bash
   git checkout -b feature/my-first-contribution
   ```

2. **Make changes** in your editor

3. **Build and test:**
   ```bash
   pnpm build
   pnpm test
   pnpm start:browser  # Verify manually
   ```

4. **Run lint:**
   ```bash
   pnpm lint
   ```

5. **Commit:**
   ```bash
   git add .
   git commit -m "feat: describe your change"
   ```

### Submit a Pull Request

**Title format:** Use conventional commits
```
feat: add feature description
fix: describe bug fix
docs: update documentation
```

**PR description template:**
```markdown
## Summary
[What changed and why]

## Changes
- [List of changes]

## Testing
1. [Step 1 to test]
2. [Step 2 to test]

## Related Issues
Closes #[issue-number]
```

### Code Review

1. Address reviewer feedback
2. Push updates to the same branch
3. Wait for approval and merge

### End of Day 3 Checklist

- [ ] First PR submitted
- [ ] Build passes on PR
- [ ] Code follows project conventions
- [ ] Tests added/updated if applicable
- [ ] Documentation updated if needed

---

## Key Files to Know

### Must-Know Files

| File | What It Does | When You'll Touch It |
|------|-------------|---------------------|
| `packages/arc-extension/src/common/arc-protocol.ts` | API contracts, types, error codes | Adding new features, changing interfaces |
| `packages/arc-extension/src/node/arc-backend-service.ts` | Core business logic | Workflow execution, trace management |
| `packages/arc-extension/src/browser/arc-widget.tsx` | Main UI component | UI changes, user interactions |
| `packages/arc-extension/src/node/security-utils.ts` | Input validation, path security | Security-related changes |
| `packages/arc-extension/src/browser/arc-widget.css` | Styling and design system | Visual changes |

### Good-to-Know Files

| File | What It Does |
|------|-------------|
| `packages/arc-extension/src/browser/arc-keybinding-contribution.ts` | Keyboard shortcuts |
| `packages/arc-extension/src/browser/arc-widget-contribution.ts` | Widget registration |
| `packages/arc-browser-app/package.json` | Browser app configuration |
| `python/src/routes.py` | Python REST API |
| `python/src/daemon/` | Run management and SSE |
| `webpack.config.js` | Build configuration |

### Configuration Files

| File | Purpose |
|------|---------|
| `package.json` | Root monorepo configuration |
| `pnpm-workspace.yaml` | Workspace definitions |
| `tsconfig.base.json` | TypeScript base configuration |
| `python/pyproject.toml` | Python project configuration |

---

## Testing Approach

### Test Structure

```
packages/arc-extension/src/
├── __tests__/
│   ├── security-utils.test.ts          # 30 tests
│   ├── arc-service.integration.test.ts # 47 tests
│   └── arc-widget.integration.test.ts  # 66 tests

python/tests/
├── test_protocol.py        # 13 tests
├── test_adapters.py        # 26+ tests
├── test_agui_bridge.py     # 7 tests
├── test_context.py         # 16 tests
├── test_security.py        # 12 tests
└── test_storage.py         # 5 tests

tests/e2e/                  # Playwright E2E tests
tests/unit/                 # Node.js unit tests
```

### Running Tests

```bash
# All Node.js tests
pnpm test

# Specific test file
cd packages/arc-extension
npx jest __tests__/security-utils.test.ts

# All Python tests
cd python && uv run pytest

# Python with coverage
cd python && uv run pytest --cov

# Python specific test
cd python && uv run pytest -k adapter

# E2E tests
pnpm start:browser          # Terminal 1
pnpm test:e2e               # Terminal 2
```

### Writing Tests

**Node.js (Jest):**
```typescript
import { sanitizePrompt } from '../node/security-utils';

describe('sanitizePrompt', () => {
    it('should allow normal text', () => {
        const result = sanitizePrompt('Hello world');
        expect(result.sanitized).toBe('Hello world');
        expect(result.valid).toBe(true);
    });

    it('should reject shell metacharacters', () => {
        const result = sanitizePrompt('test; rm -rf /');
        expect(result.valid).toBe(false);
    });
});
```

**Python (pytest):**
```python
from src.security_utils import sanitize_input

def test_sanitize_normal_text():
    result = sanitize_input("Hello world")
    assert result["valid"] is True

def test_sanitize_shell_chars():
    result = sanitize_input("test; rm -rf /")
    assert result["valid"] is False
```

### Coverage Targets

| Scope | Target | Current |
|-------|--------|---------|
| Overall | ≥70% | 63.86% |
| Backend service | ≥80% | 67.74% |
| Security utils | ≥95% | 96.61% |
| Widget | ≥60% | 0% (needs jsdom) |

---

## Code Style Guidelines

### TypeScript

- **Indentation:** 4 spaces
- **Quotes:** Single quotes for strings
- **Types:** Explicit types, avoid `any`
- **JSDoc:** Required for public APIs
- **Naming:** camelCase for variables/functions, PascalCase for classes/interfaces
- **Imports:** Group by external/internal, alphabetize

```typescript
/**
 * Execute a workflow with the given prompt.
 *
 * @param prompt - The user prompt to execute
 * @param options - Execution configuration
 * @returns Promise resolving to execution result
 * @throws ArcError if input is invalid or execution fails
 */
async executeWorkflow(
    prompt: string,
    options?: ExecutionOptions
): Promise<ExecutionResult> {
    // Implementation
}
```

### Python

- **Style:** PEP 8
- **Indentation:** 4 spaces
- **Quotes:** Double quotes for strings
- **Type hints:** Required for all functions
- **Docstrings:** Google style
- **Line length:** 100 characters (ruff config)

```python
def execute_workflow(prompt: str, backend: str = "gateway") -> ExecutionResponse:
    """
    Execute a workflow with the given prompt.

    Args:
        prompt: The user prompt to execute
        backend: Backend type ('gateway' or 'stub')

    Returns:
        ExecutionResponse with run ID and trace path

    Raises:
        ValueError: If prompt is empty or invalid
    """
    # Implementation
```

### CSS

- **Variables:** Use Theia CSS custom properties (`--theia-*`)
- **Naming:** BEM-like convention with kebab-case
- **Organization:** Group by component, then state
- **Comments:** Section headers for major components

```css
.arc-widget {
    display: flex;
    flex-direction: column;
    padding: var(--theia-ui-padding);
    background: var(--theia-editor-background);
}

.arc-widget__header {
    font-size: var(--theia-ui-font-size1);
    font-weight: 600;
}

.arc-widget--loading {
    opacity: 0.7;
    pointer-events: none;
}
```

### Git Commits

Use conventional commits:

```
feat: add trace filtering by date range
fix: handle missing trace files gracefully
docs: update API documentation for streamTrace
refactor: extract workspace scanning into separate module
test: add security-utils path traversal tests
chore: update dependencies
```

### Security Rules (Never Violate)

1. **Never use `shell: true`** in subprocess execution
2. **Never pass user input directly** to shell commands
3. **Always validate paths** are within workspace boundaries
4. **Never log secrets** or sensitive data
5. **Always sanitize error messages** before displaying to users
6. **Use environment allow-list** for subprocess spawning

---

## Debugging Tips

### Frontend Debugging

1. Open browser DevTools (F12)
2. Console tab for logs
3. Sources tab for breakpoints
4. Network tab for JSON-RPC calls

### Backend Debugging

```bash
# Start with Node.js inspector
NODE_OPTIONS='--inspect' pnpm start:browser

# Attach VS Code debugger
# Use .vscode/launch.json with port 9229
```

### Python Debugging

```python
import pdb; pdb.set_trace()  # Breakpoint
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Build fails | `pnpm clean && pnpm install && pnpm build` |
| Port 3000 in use | `lsof -i :3000` then kill process |
| Changes not appearing | Hard refresh (Cmd+Shift+R), rebuild |
| SwarmGraph not found | `which swarmgraph`, check PATH |
| Python tests fail | `cd python && uv sync --all-extras --dev` |

See `docs/TROUBLESHOOTING.md` for detailed solutions.

---

## Getting Help

1. **Check documentation** — Most answers are in `docs/`
2. **Search issues** — https://github.com/Hansuqwer/arc-theia-studio/issues
3. **Create an issue** — Include environment, steps to reproduce, expected/actual behavior
4. **Join discussions** — https://github.com/Hansuqwer/arc-theia-studio/discussions

---

## Next Steps After Onboarding

1. **Pick a second issue** — Build momentum with another contribution
2. **Read the roadmap** — `docs/ROADMAP.md` for upcoming features
3. **Explore adapters** — Understand SwarmGraph and LangGraph integration
4. **Contribute to docs** — Fix typos, add examples, improve clarity
5. **Review PRs** — Learn from other developers' contributions
