/**
 * ARC Studio — Electron Daemon Manager (ADR-008)
 *
 * Manages the Python daemon lifecycle within the Electron app.
 * In dev mode, uses `uv run arc serve`. In production, uses
 * the bundled daemon binary/venv.
 *
 * This is the Phase 1 scaffold. Actual daemon bundling will be
 * decided after the packaging spike (scripts/electron-packaging-spike.sh).
 */
import { spawn, ChildProcess } from 'child_process';
import { app } from 'electron';
import * as path from 'path';
import * as crypto from 'crypto';
import * as http from 'http';

export interface DaemonManagerOptions {
  /** Port the daemon listens on (default: 7777) */
  port?: number;
  /** Timeout in ms for health check (default: 10000) */
  healthTimeout?: number;
  /** Auto-start daemon when created (default: false) */
  autoStart?: boolean;
}

export interface DaemonHealth {
  ok: boolean;
  version?: string;
  uptime?: number;
  error?: string;
}

export class DaemonManager {
  private process: ChildProcess | null = null;
  private readonly daemonPort: number;
  private readonly healthTimeout: number;
  private _token: string;
  private _started = false;

  constructor(options: DaemonManagerOptions = {}) {
    this.daemonPort = options.port ?? 7777;
    this.healthTimeout = options.healthTimeout ?? 10000;
    this._token = crypto.randomBytes(32).toString('hex');

    if (options.autoStart) {
      // defer to next tick so the constructor can return
      setImmediate(() => {
        this.start().catch((err) => {
          console.error('[DaemonManager] Auto-start failed:', err);
        });
      });
    }
  }

  get started(): boolean {
    return this._started;
  }

  get port(): number {
    return this.daemonPort;
  }

  get token(): string {
    return this._token;
  }

  async start(): Promise<void> {
    if (this.process) {
      console.warn('[DaemonManager] Daemon already running');
      return;
    }

    const daemonPath = this.getDaemonPath();
    const args = this.getDaemonArgs();

    console.log(`[DaemonManager] Starting daemon: ${daemonPath} ${args.join(' ')}`);

    this.process = spawn(daemonPath, args, {
      env: {
        ...process.env,
        ARC_DAEMON_TOKEN: this._token,
        ARC_WORKSPACE_PATH: this.getWorkspacePath(),
        ARC_DAEMON_PORT: String(this.daemonPort),
      },
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    this.process.stdout?.on('data', (data: Buffer) => {
      console.log(`[daemon] ${data.toString().trim()}`);
    });

    this.process.stderr?.on('data', (data: Buffer) => {
      console.error(`[daemon:err] ${data.toString().trim()}`);
    });

    this.process.on('exit', (code, signal) => {
      console.log(`[DaemonManager] Daemon exited (code=${code}, signal=${signal})`);
      this.process = null;
      this._started = false;
    });

    this.process.on('error', (err) => {
      console.error(`[DaemonManager] Daemon spawn error:`, err);
      this.process = null;
      this._started = false;
    });

    await this.waitForReady();
    this._started = true;
  }

  async stop(): Promise<void> {
    if (!this.process) {
      return;
    }

    console.log('[DaemonManager] Stopping daemon...');
    this.process.kill('SIGTERM');

    return new Promise<void>((resolve) => {
      const timeout = setTimeout(() => {
        console.warn('[DaemonManager] Daemon did not stop gracefully, sending SIGKILL');
        this.process?.kill('SIGKILL');
        resolve();
      }, 5000);

      this.process?.on('exit', () => {
        clearTimeout(timeout);
        this.process = null;
        this._started = false;
        resolve();
      });
    });
  }

  async health(): Promise<DaemonHealth> {
    try {
      const resp = await this.httpGet(`http://127.0.0.1:${this.daemonPort}/health`);
      const data = JSON.parse(resp);
      return {
        ok: true,
        version: data.version,
        uptime: data.uptime,
      };
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      return { ok: false, error: message };
    }
  }

  private getDaemonPath(): string {
    if (process.env.ARC_DEV_MODE || process.env.NODE_ENV === 'development') {
      return 'uv';
    }

    // Production: use bundled daemon
    const resourcesPath =
      process.resourcesPath || path.join(app.getAppPath(), 'resources');

    // Try binary first (PyInstaller), then script (embedded Python/uv)
    const binaryPath = path.join(resourcesPath, 'daemon', 'arc-daemon');
    const scriptPath = path.join(resourcesPath, 'daemon', 'arc-daemon.py');

    if (require('fs').existsSync(binaryPath)) {
      return binaryPath;
    }
    // Fall back to bundled Python
    const pythonBin = path.join(resourcesPath, 'python', 'bin', 'python3');
    if (require('fs').existsSync(pythonBin)) {
      return pythonBin;
    }
    // Fall back to uv bootstrap
    const uvBin = path.join(resourcesPath, 'bin', 'uv');
    if (require('fs').existsSync(uvBin)) {
      return uvBin;
    }

    // Absolute last resort
    return scriptPath;
  }

  private getDaemonArgs(): string[] {
    const daemonPath = this.getDaemonPath();
    const binaryName = path.basename(daemonPath);

    if (binaryName === 'uv') {
      return [
        'run',
        '--directory',
        path.join(this.getResourcesPath(), 'daemon'),
        'arc',
        'serve',
        '--port',
        String(this.daemonPort),
      ];
    }

    if (binaryName === 'python3' || binaryName === 'python') {
      return [
        path.join(this.getResourcesPath(), 'daemon', 'arc-daemon.py'),
        'serve',
        '--port',
        String(this.daemonPort),
      ];
    }

    // Binary (PyInstaller) or script
    return ['serve', '--port', String(this.daemonPort)];
  }

  private getResourcesPath(): string {
    return (
      process.resourcesPath || path.join(app.getAppPath(), 'resources')
    );
  }

  private getWorkspacePath(): string {
    // Default to user home; real logic should use Theia workspace
    return app.getPath('home');
  }

  private async waitForReady(): Promise<void> {
    const start = Date.now();

    while (Date.now() - start < this.healthTimeout) {
      try {
        const health = await this.health();
        if (health.ok) {
          console.log(`[DaemonManager] Daemon ready (version=${health.version})`);
          return;
        }
      } catch {
        // Not ready yet
      }
      await new Promise((r) => setTimeout(r, 200));
    }

    throw new Error(
      `Daemon failed to start within ${this.healthTimeout}ms on port ${this.daemonPort}`
    );
  }

  private httpGet(url: string): Promise<string> {
    return new Promise((resolve, reject) => {
      http
        .get(url, (res) => {
          let data = '';
          res.on('data', (chunk: string) => {
            data += chunk;
          });
          res.on('end', () => resolve(data));
        })
        .on('error', reject)
        .end();
    });
  }
}

export default DaemonManager;
