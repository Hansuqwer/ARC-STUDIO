# ADR-008: Python Daemon Bundling for Electron/Desktop

## Status
Proposed

## Context

ARC Studio's Python daemon (`agent-runtime-cockpit`) is currently:
- A standalone pip package (`agent-runtime-cockpit` v0.1.0a0)
- Built with hatchling, entry point: `arc = "agent_runtime_cockpit.cli:app"`
- Started manually via `uv run arc serve` or `arc serve`
- The Theia extension connects to it at `127.0.0.1:7777`
- **Not bundled** with the Electron app or Theia browser app
- Users must install Python, uv, and the ARC package separately

This creates friction:
- Multi-step setup (install Python → install uv → install ARC package → start daemon → open IDE)
- Version mismatch risk (daemon version != IDE version)
- No auto-start (daemon must be started manually)
- No auto-update (daemon and IDE updated independently)

For a polished desktop experience, the daemon should be bundled with the Electron app and auto-started.

## Decision

### Bundling Strategy: Embedded Python

Bundle a self-contained Python runtime with the Electron app:

```
ARC Studio.app/
├── Contents/
│   ├── MacOS/
│   │   └── arc-theia-studio        # Electron main process
│   ├── Resources/
│   │   ├── app/                     # Theia frontend
│   │   ├── python/                  # Embedded Python runtime
│   │   │   ├── bin/
│   │   │   │   └── python3          # Python interpreter
│   │   │   ├── lib/
│   │   │   │   └── python3.12/
│   │   │   └── site-packages/
│   │   │       └── agent_runtime_cockpit/  # ARC daemon package
│   │   └── daemon/
│   │       └── arc-daemon           # Daemon launcher script
```

### Implementation Options

#### Option A: PyInstaller (candidate for packaging spike)

Use PyInstaller to create a self-contained daemon binary:

```bash
# Build daemon binary
cd python
pyinstaller \
    --name arc-daemon \
    --onefile \
    --hidden-import aiohttp \
    --hidden-import aiofiles \
    --hidden-import pydantic \
    --hidden-import typer \
    --hidden-import rich \
    src/agent_runtime_cockpit/daemon.py
```

**Pros:**
- Single binary, no Python runtime needed
- Simple to bundle
- Works on macOS, Linux, Windows

**Cons:**
- Larger binary (~50-80MB with dependencies)
- Some dynamic imports may need `--hidden-import`
- Slower startup (extracts to temp dir)

#### Option B: Embedded Python + pip (Recommended for Phase 2)

Bundle a minimal Python runtime and install ARC package into it:

```bash
# Download embedded Python (macOS example)
PYTHON_VERSION=3.12.4
curl -L "https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-macos11.pkg" \
    -o python-installer.pkg

# Extract to Resources/python/
installer -pkg python-installer.pkg -target ./Resources/python-staging/

# Install ARC package
./Resources/python/bin/pip install \
    --target ./Resources/python/lib/python3.12/site-packages/ \
    ./python/
```

**Pros:**
- Full Python runtime (supports all features)
- Smaller ARC package (just the code, not the runtime)
- Easier to update (just replace site-packages)

**Cons:**
- More complex build process
- Larger total size (Python runtime + packages)
- Platform-specific Python builds needed

#### Option C: uv-based Bootstrap (Recommended for Phase 3)

Bundle `uv` binary and use it to bootstrap the daemon from a locked environment:

```bash
# Bundle uv binary
curl -LsSf https://astral.sh/uv/install.sh | sh
cp ~/.cargo/bin/uv ./Resources/

# Bundle uv.lock + pyproject.toml
cp python/pyproject.toml python/uv.lock ./Resources/daemon/

# At runtime: uv sync + uv run arc serve
./Resources/uv sync --directory ./Resources/daemon/
./Resources/uv run --directory ./Resources/daemon/ arc serve
```

**Pros:**
- Reproducible builds (uv.lock)
- Fast bootstrap (uv is very fast)
- Easy updates (update lock file)

**Cons:**
- Requires network for first bootstrap (or bundled cache)
- More runtime complexity

### Recommended Approach

**Phase 1 (P1): packaging spike**
- Compare PyInstaller, embedded Python, and uv-managed venv using a real daemon smoke test
- Decide only after startup time, size, signing/notarization, dependency, and update behavior are measured

**Phase 2 (P2): selected bundling implementation**
- Better for long-term maintenance
- Supports full Python ecosystem
- Needed for adapter plugins (LangGraph, CrewAI, etc.)

**Phase 3 (P3): update/bootstrap refinement**
- Best developer experience
- Reproducible builds
- Easy version management

### Electron Integration

The Electron main process manages the daemon lifecycle:

```typescript
// electron/main/daemon-manager.ts
import { spawn, ChildProcess } from 'child_process';
import { app } from 'electron';
import * as path from 'path';

class DaemonManager {
    private process: ChildProcess | null = null;
    private daemonPort = 7777;
    
    async start(): Promise<void> {
        const daemonPath = this.getDaemonPath();
        
        this.process = spawn(daemonPath, ['serve', '--port', String(this.daemonPort)], {
            env: {
                ...process.env,
                ARC_DAEMON_TOKEN: this.generateToken(),
                ARC_WORKSPACE_PATH: this.getWorkspacePath(),
            },
            stdio: ['pipe', 'pipe', 'pipe'],
        });
        
        // Wait for health check
        await this.waitForReady();
    }
    
    async stop(): Promise<void> {
        if (this.process) {
            this.process.kill('SIGTERM');
            await new Promise<void>((resolve) => {
                this.process!.on('exit', () => resolve());
            });
            this.process = null;
        }
    }
    
    private getDaemonPath(): string {
        if (process.env.ARC_DEV_MODE) {
            return 'uv'; // Dev mode: use uv run arc serve
        }
        
        // Production: bundled daemon
        const resourcesPath = process.resourcesPath || path.join(app.getAppPath(), 'resources');
        return path.join(resourcesPath, 'daemon', 'arc-daemon');
    }
    
    private generateToken(): string {
        return require('crypto').randomBytes(32).toString('hex');
    }
    
    private async waitForReady(timeout = 10000): Promise<void> {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            try {
                const resp = await fetch(`http://127.0.0.1:${this.daemonPort}/health`);
                if (resp.ok) return;
            } catch {
                // Not ready yet
            }
            await new Promise(r => setTimeout(r, 200));
        }
        throw new Error('Daemon failed to start');
    }
}
```

### Auto-Start Configuration

Theia preference controls auto-start:

```typescript
// Already exists: arc.daemon.autoStart (default: false)
// In bundled mode, default changes to true
'arc.daemon.autoStart': {
    type: 'boolean',
    default: IS_BUNDLED ? true : false,
    description: 'Auto-start Python daemon when IDE opens',
}
```

### Version Management

The daemon and IDE versions must be compatible:

```typescript
// On startup, verify daemon version matches expected
async function verifyDaemonVersion(): Promise<void> {
    const resp = await fetch('http://127.0.0.1:7777/health');
    const health = await resp.json();
    
    const expectedVersion = require('../package.json').daemonVersion;
    if (health.version !== expectedVersion) {
        throw new Error(
            `Daemon version mismatch: expected ${expectedVersion}, got ${health.version}`
        );
    }
}
```

### Update Strategy

When the Electron app updates:
1. New app bundle includes new daemon binary
2. On first launch, old daemon is stopped, new daemon is started
3. No separate daemon update mechanism needed
4. Daemon version is tied to app version

## Consequences

### Positive
- Single install (user downloads one .dmg/.AppImage/.exe)
- Auto-start daemon (no manual setup)
- Version-locked (no mismatch risk)
- Auto-update (daemon updates with app)
- Better user experience

### Negative
- Larger app bundle (+50-100MB for Python runtime)
- Platform-specific builds needed (macOS, Linux, Windows)
- More complex build pipeline
- Harder to debug daemon issues (embedded runtime)

### Neutral
- Dev mode still uses `uv run arc serve` (not bundled)
- Daemon port remains 7777 (no change)
- Daemon token auto-generated per session (more secure)

## References
- Current daemon: `python/src/agent_runtime_cockpit/web/server.py`
- Current packaging: `python/pyproject.toml`
- Theia daemon preference: `theia-extensions/arc-settings/src/common/arc-preference-schema.ts`
- Theia daemon connection: `theia-extensions/arc-core/src/node/arc-service-impl.ts:172-176`
