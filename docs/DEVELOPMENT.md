# ARC Studio Development Guide

**Version:** 0.1.0  
**Last Updated:** 2026-05-13  
**Status:** Phase 6 - Alpha Acceptance

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Project Structure](#project-structure)
4. [Building and Running](#building-and-running)
5. [Development Workflow](#development-workflow)
6. [Debugging](#debugging)
7. [Testing](#testing)
8. [Common Issues](#common-issues)
9. [Contributing](#contributing)

---

## Getting Started

### Prerequisites

Ensure you have the following installed:

- **Node.js** >= 18.0.0
- **pnpm** >= 8.0.0
- **Python** >= 3.11
- **Git**
- **SwarmGraph CLI** (for workflow execution)

### Verify Installation

```bash
# Check Node.js version
node --version  # Should be >= 18.0.0

# Check pnpm version
pnpm --version  # Should be >= 8.0.0

# Check Python version
python --version  # Should be >= 3.11

# Check SwarmGraph installation
which swarmgraph  # Should return path to executable
```

### Clone Repository

```bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio
git checkout build/no-mockups-handoff
```

### Initial Setup

```bash
# Install all dependencies
pnpm install

# Build all packages
pnpm build

# Verify build succeeded
echo $?  # Should output 0
```

**Note:** If build fails, see [Common Issues](#common-issues) for solutions.

---

## Development Environment

### Recommended IDE

**Visual Studio Code** with extensions:
- ESLint
- Prettier
- TypeScript and JavaScript Language Features
- Python
- GitLens

### Editor Configuration

Create `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.tsdk": "node_modules/typescript/lib",
  "files.exclude": {
    "**/node_modules": true,
    "**/lib": true,
    "**/.DS_Store": true
  }
}
```

### Environment Variables

Create `.env` file in project root (optional):

```bash
# Python API configuration
PYTHON_API_PORT=8000
PYTHON_API_HOST=0.0.0.0

# SwarmGraph configuration
SWARMGRAPH_BACKEND=gateway
SWARMGRAPH_COST_ALLOWED=true

# Development mode
NODE_ENV=development
```

---

## Project Structure

```
arc-theia-studio/
├── packages/                   # Monorepo packages
│   ├── arc-extension/          # Main Theia extension
│   │   ├── src/
│   │   │   ├── browser/        # Frontend (React)
│   │   │   ├── node/           # Backend (Node.js)
│   │   │   └── common/         # Shared protocol
│   │   ├── lib/                # Compiled output
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── arc-browser-app/        # Browser application
│   │   ├── src-gen/            # Generated Theia app
│   │   ├── package.json
│   │   └── webpack.config.js
│   ├── arc-electron-app/       # Electron app (TODO)
│   └── arc-test-fixtures/      # Test utilities (TODO)
├── python/                     # Python backend
│   ├── src/
│   │   ├── routes.py           # REST API
│   │   └── security_utils.py   # Security
│   ├── tests/                  # Python tests
│   └── pyproject.toml
├── docs/                       # Documentation
├── scripts/                    # Build scripts
├── .arc/                       # Runtime data
│   └── traces/                 # Trace files
├── package.json                # Root package.json
├── pnpm-workspace.yaml         # Workspace config
└── README.md
```

### Key Files

| File | Purpose |
|------|---------|
| `packages/arc-extension/src/common/arc-protocol.ts` | Protocol definitions |
| `packages/arc-extension/src/node/arc-backend-service.ts` | Backend service |
| `packages/arc-extension/src/browser/arc-widget.tsx` | Main UI widget |
| `python/src/routes.py` | REST API endpoints |
| `docs/IMPLEMENTATION_DECISIONS.md` | Architectural decisions |

---

## Building and Running

### Build Commands

```bash
# Build all packages
pnpm build

# Build specific package
pnpm --filter arc-extension build

# Watch mode (auto-rebuild on changes)
pnpm watch

# Clean build artifacts
pnpm clean
```

### Running the Application

#### Browser Mode

```bash
# Start browser application on port 3000
pnpm start:browser

# Open in browser
open http://localhost:3000
```

#### Electron Mode (TODO)

```bash
# Start Electron application
pnpm start:electron
```

### Running Python API

```bash
# Navigate to python directory
cd python

# Install dependencies (first time only)
pip install -e .

# Start API server
uvicorn src.routes:app --host 0.0.0.0 --port 8000 --reload

# Test API
curl http://localhost:8000/
```

---

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes to code**
   - Edit TypeScript files in `packages/arc-extension/src/`
   - Edit Python files in `python/src/`

3. **Build and test**
   ```bash
   pnpm build
   pnpm start:browser
   ```

4. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: add my feature"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   # Create PR on GitHub
   ```

### Code Style

#### TypeScript

Follow Theia conventions:
- Use 4-space indentation
- Use single quotes for strings
- Add JSDoc comments for public APIs
- Use explicit types (avoid `any`)

Example:
```typescript
/**
 * Execute a workflow with the given prompt.
 * 
 * @param prompt - The user prompt
 * @param options - Execution options
 * @returns Promise resolving to execution result
 */
async executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult> {
    // Implementation
}
```

#### Python

Follow PEP 8:
- Use 4-space indentation
- Use double quotes for strings
- Add docstrings for functions
- Use type hints

Example:
```python
def execute_workflow(prompt: str, backend: str = "gateway") -> ExecutionResponse:
    """
    Execute a workflow with the given prompt.
    
    Args:
        prompt: The user prompt
        backend: Backend type ('gateway' or 'stub')
    
    Returns:
        ExecutionResponse with run ID and trace path
    """
    # Implementation
```

### Commit Messages

Follow conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Build/tooling changes

Examples:
```bash
git commit -m "feat: add trace visualization widget"
git commit -m "fix: handle missing trace files gracefully"
git commit -m "docs: update API documentation"
```

---

## Debugging

### Debugging Frontend (Browser)

1. **Start application in watch mode**
   ```bash
   pnpm watch
   ```

2. **Start browser app**
   ```bash
   pnpm start:browser
   ```

3. **Open browser DevTools**
   - Press F12 or Cmd+Option+I
   - Go to Sources tab
   - Set breakpoints in TypeScript files

4. **View console logs**
   ```typescript
   console.log('Debug message:', data);
   ```

### Debugging Backend (Node.js)

1. **Add debug configuration** (`.vscode/launch.json`):
   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "type": "node",
         "request": "attach",
         "name": "Attach to Backend",
         "port": 9229,
         "restart": true
       }
     ]
   }
   ```

2. **Start with debugging enabled**
   ```bash
   NODE_OPTIONS='--inspect' pnpm start:browser
   ```

3. **Attach debugger in VS Code**
   - Press F5
   - Set breakpoints in backend files

### Debugging Python API

1. **Add debug prints**
   ```python
   print(f"Debug: {variable}")
   ```

2. **Use Python debugger**
   ```python
   import pdb; pdb.set_trace()
   ```

3. **Run with debugger**
   ```bash
   python -m pdb -m uvicorn src.routes:app
   ```

### Viewing Logs

**Browser Console:**
- Frontend logs appear in browser DevTools console

**Terminal Output:**
- Backend logs appear in terminal where `pnpm start:browser` is running

**Trace Files:**
- Execution traces stored in `.arc/traces/*.jsonl`
- View with: `cat .arc/traces/run-sg-*.jsonl | jq`

---

## Testing

### Current State (Phase 6)

✅ **Automated tests available** — 82 Python tests + 8 Node.js unit tests + E2E smoke tests

### Running Tests

```bash
# Python tests
cd python
uv run pytest              # all tests
uv run pytest -v           # verbose
uv run pytest -k adapter   # filter by keyword
uv run pytest --cov        # with coverage

# Node.js unit tests
node tests/unit/arc-protocol.test.js
node packages/arc-test-fixtures/src/index.js

# All checks
pnpm -r test
bash scripts/check.sh

# E2E tests (Playwright)
pnpm start:browser         # in terminal 1
cd tests/e2e && pnpm install:browsers  # first time only
pnpm test:e2e              # from root
```

### Conformance Tests

```bash
uv run arc adapter test swarmgraph  # 8/8 pass
uv run arc adapter test langgraph   # 9/9 pass
```

### Manual Testing

#### Test Workflow Execution

1. Start application: `pnpm start:browser`
2. Open ARC Studio widget (View → ARC Studio)
3. Click "Execute Workflow" button
4. Enter prompt: "What is 2+2?"
5. Verify execution completes
6. Check trace file created in `.arc/traces/`

#### Test Trace Loading

1. Execute a workflow (see above)
2. Click "Load Traces" button
3. Verify trace list appears
4. Click on a trace
5. Verify trace details display

#### Test API Endpoints

```bash
# Start Python API
cd python && uvicorn src.routes:app --reload

# Test health check
curl http://localhost:8000/

# Test workflow execution
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "backend": "stub"}'

# Test trace listing
curl http://localhost:8000/api/traces
```

### Test Files

| File | Tests | Coverage |
|------|-------|---------|
| `python/test_protocol.py` | 13 | Envelope, error codes, domain models |
| `python/test_adapters.py` | 26+ | SwarmGraph, LangGraph, registry, conformance |
| `python/test_agui_bridge.py` | 7 | AG-UI event mapping, roundtrip |
| `python/test_context.py` | 16 | All 5 providers, cache, ranker, engine |
| `python/test_security.py` | 12 | Redaction, path validation |
| `python/test_storage.py` | 5 | JSONL save/load/list |
| `tests/unit/arc-protocol.test.js` | 8 | Bootstrap protocol tests |

---

## Common Issues

### Build Errors

#### Issue: TypeScript compilation fails

**Solution:**
1. Clean and reinstall: `pnpm clean && pnpm install && pnpm build`
2. Check for missing dependencies: `pnpm install`
3. Verify Node.js >= 18.0.0: `node --version`
4. Check interface in `packages/arc-extension/src/common/arc-protocol.ts`
5. Ensure all methods implemented in `packages/arc-extension/src/node/arc-backend-service.ts`

#### Issue: Module not found errors

```
Cannot find module '@theia/core'
```

**Solution:**
```bash
# Clean and reinstall
pnpm clean
rm -rf node_modules
pnpm install
pnpm build
```

### Runtime Errors

#### Issue: SwarmGraph command not found

```
Error: Command failed: swarmgraph swarm --json "prompt"
```

**Solution:**
1. Install SwarmGraph: https://github.com/Hansuqwer/SwarmGraph
2. Verify installation: `which swarmgraph`
3. Add to PATH if needed

#### Issue: Port 3000 already in use

```
Error: listen EADDRINUSE: address already in use :::3000
```

**Solution:**
```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or use different port
PORT=3001 pnpm start:browser
```

#### Issue: Trace files not found

```
Error: Trace file not found: run-sg-abc123
```

**Solution:**
1. Verify `.arc/traces/` directory exists
2. Check trace file exists: `ls .arc/traces/`
3. Verify file permissions: `ls -la .arc/traces/`

### Development Issues

#### Issue: Changes not reflected in browser

**Solution:**
1. Stop the application (Ctrl+C)
2. Rebuild: `pnpm build`
3. Restart: `pnpm start:browser`
4. Hard refresh browser (Cmd+Shift+R)

#### Issue: Watch mode not working

**Solution:**
```bash
# Stop watch mode
# Kill all node processes
pkill -f "tsc -w"

# Restart watch mode
pnpm watch
```

---

## Contributing

### Before You Start

1. Read [Implementation Decisions](IMPLEMENTATION_DECISIONS.md)
2. Check [GitHub Issues](https://github.com/Hansuqwer/arc-theia-studio/issues)
3. Discuss major changes in an issue first

### Development Process

1. **Fork and clone** the repository
2. **Create a branch** for your feature
3. **Make changes** following code style
4. **Test manually** (automated tests coming in Phase 5)
5. **Update documentation** if needed
6. **Commit with conventional commits**
7. **Push and create PR**

### Pull Request Guidelines

**PR Title:** Use conventional commit format
```
feat: add trace visualization component
fix: handle missing trace files
docs: update development guide
```

**PR Description:** Include:
- What changed and why
- How to test the changes
- Screenshots (for UI changes)
- Related issues

**Example:**
```markdown
## Summary
Adds trace visualization component to display execution events.

## Changes
- Created TraceVisualization component
- Added event timeline rendering
- Integrated with ArcWidget

## Testing
1. Start app: `pnpm start:browser`
2. Execute a workflow
3. Click "Load Traces"
4. Verify timeline displays

## Screenshots
[Screenshot of trace visualization]

Closes #42
```

### Code Review Process

1. **Automated checks** must pass (when CI is set up)
2. **Manual review** by maintainer
3. **Address feedback** and update PR
4. **Merge** when approved

---

## Useful Commands

### Package Management

```bash
# Install dependencies
pnpm install

# Add dependency to specific package
pnpm --filter arc-extension add <package>

# Update dependencies
pnpm update

# Check for outdated packages
pnpm outdated
```

### Build and Clean

```bash
# Build all packages
pnpm build

# Build specific package
pnpm --filter arc-extension build

# Clean build artifacts
pnpm clean

# Clean and rebuild
pnpm clean && pnpm build
```

### Development

```bash
# Watch mode (auto-rebuild)
pnpm watch

# Start browser app
pnpm start:browser

# Start Electron app (TODO)
pnpm start:electron

# Lint code
pnpm lint
```

### Python

```bash
# Install Python dependencies
cd python && pip install -e .

# Run Python API
uvicorn src.routes:app --reload

# Run Python tests (TODO)
pytest

# Lint Python code
ruff check src tests

# Type check Python code
mypy src tests
```

### Git

```bash
# Create feature branch
git checkout -b feature/my-feature

# Commit changes
git add .
git commit -m "feat: add feature"

# Push branch
git push origin feature/my-feature

# Update from main
git fetch origin
git rebase origin/build/no-mockups-handoff
```

---

## Resources

### Documentation

- [README](../README.md) - Project overview
- [API Documentation](API.md) - API reference
- [Architecture](ARCHITECTURE.md) - System architecture
- [Implementation Decisions](IMPLEMENTATION_DECISIONS.md) - Design decisions
- [Research Notes](RESEARCH_NOTES.md) - Technology research

### External Resources

- [Eclipse Theia Documentation](https://theia-ide.org/docs/)
- [Theia Extension Development](https://theia-ide.org/docs/composing_applications/)
- [SwarmGraph Repository](https://github.com/Hansuqwer/SwarmGraph)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

### Community

- [GitHub Issues](https://github.com/Hansuqwer/arc-theia-studio/issues)
- [GitHub Discussions](https://github.com/Hansuqwer/arc-theia-studio/discussions)

---

## Getting Help

### Debugging Steps

1. **Check logs** - Browser console and terminal output
2. **Verify environment** - Node, pnpm, Python versions
3. **Clean rebuild** - `pnpm clean && pnpm build`
4. **Check documentation** - README, API docs, this guide
5. **Search issues** - GitHub issues for similar problems
6. **Ask for help** - Create a GitHub issue

### Creating an Issue

Include:
- **Environment:** OS, Node version, pnpm version
- **Steps to reproduce:** Exact commands run
- **Expected behavior:** What should happen
- **Actual behavior:** What actually happens
- **Logs:** Relevant error messages
- **Screenshots:** If applicable

---

## Next Steps

After setting up your development environment:

1. **Explore the codebase** - Read through key files
2. **Run the application** - Start browser app and test features
3. **Make a small change** - Fix a typo or add a comment
4. **Read architectural docs** - Understand system design
5. **Pick an issue** - Find a good first issue on GitHub
6. **Start contributing!**

Happy coding! 🚀
