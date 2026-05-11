/**
 * ARC Service Implementation — Backend (Node.js)
 *
 * Calls the Python ARC daemon via:
 * 1. CLI mode: spawn `uv run arc <cmd> --json` (no daemon required)
 * 2. HTTP mode: call localhost:7777 (daemon mode)
 *
 * Returns an error if neither daemon nor CLI is available. Mock data is kept
 * in the test fixture package only, not the normal product path.
 *
 * MOCK_REASON: Python daemon may not be installed in all environments
 * REAL_IMPLEMENTATION_PATH: python/src/agent_runtime_cockpit/daemon.py
 * LOCAL_FIX_STEPS: Run `uv sync && uv run arc serve` in the python/ directory
 * OWNER: Python ARC Core Agent
 * REMOVE_BEFORE: already removed from normal product path
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { ILogger } from '@theia/core/lib/common/logger';
import * as cp from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as http from 'http';
import {
  ArcService,
  ArcEnvelope,
  WorkspaceInfo,
  RuntimeInfo,
  WorkflowInfo,
  SchemaInfo,
  RunRecord,
  ContextPackEntry,
  ProviderStatus,
  ARC_PROTOCOL_VERSION,
} from '../common/arc-protocol';

const ARC_DAEMON_PORT = 7777;
const ARC_DAEMON_HOST = 'localhost';
const ARC_CLI_TIMEOUT_MS = 30000;

@injectable()
export class ArcServiceImpl implements ArcService {

  @inject(ILogger)
  protected readonly logger: ILogger;

  /** Check if the ARC daemon is running */
  private async isDaemonRunning(): Promise<boolean> {
    return new Promise(resolve => {
      const req = http.get(
        `http://${ARC_DAEMON_HOST}:${ARC_DAEMON_PORT}/health`,
        { timeout: 2000 },
        res => resolve(res.statusCode === 200)
      );
      req.on('error', () => resolve(false));
      req.on('timeout', () => { req.destroy(); resolve(false); });
    });
  }

  /** Call the daemon HTTP API */
  private async callDaemon<T>(endpoint: string, params?: Record<string, string>): Promise<ArcEnvelope<T>> {
    const queryStr = params ? '?' + new URLSearchParams(params).toString() : '';
    const url = `http://${ARC_DAEMON_HOST}:${ARC_DAEMON_PORT}${endpoint}${queryStr}`;

    return new Promise((resolve, reject) => {
      const req = http.get(url, { timeout: ARC_CLI_TIMEOUT_MS }, res => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            reject(new Error(`Invalid JSON from daemon: ${data.substring(0, 200)}`));
          }
        });
      });
      req.on('error', reject);
      req.on('timeout', () => { req.destroy(); reject(new Error('Daemon request timed out')); });
    });
  }

  /** Spawn ARC CLI and parse JSON output */
  private async runCli<T>(args: string[]): Promise<ArcEnvelope<T>> {
    return new Promise((resolve, reject) => {
      const fullArgs = [...args, '--json'];
      this.logger.debug(`ARC CLI: uv run arc ${fullArgs.join(' ')}`);

      // Try uv first, then python -m
      const proc = cp.spawn('uv', ['run', 'arc', ...fullArgs], {
        cwd: this.pythonProjectDir(),
        timeout: ARC_CLI_TIMEOUT_MS,
        env: { ...process.env, ARC_JSON_OUTPUT: '1' },
      });

      let stdout = '';
      let stderr = '';
      proc.stdout?.on('data', d => stdout += d);
      proc.stderr?.on('data', d => stderr += d);

      proc.on('close', code => {
        if (code !== 0 && !stdout.trim()) {
          reject(new Error(`ARC CLI failed (exit ${code}): ${stderr.substring(0, 500)}`));
          return;
        }
        try {
          resolve(JSON.parse(stdout));
        } catch (e) {
          reject(new Error(`ARC CLI returned invalid JSON: ${stdout.substring(0, 200)}`));
        }
      });

      proc.on('error', err => {
        reject(new Error(`ARC CLI spawn failed: ${err.message}`));
      });
    });
  }

  private pythonProjectDir(): string {
    const candidates = [
      process.env.ARC_PYTHON_DIR,
      path.resolve(process.cwd(), 'python'),
      path.resolve(process.cwd(), '..', '..', 'python'),
      '/Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio/python',
    ].filter((candidate): candidate is string => Boolean(candidate));
    return candidates.find(candidate => fs.existsSync(path.join(candidate, 'pyproject.toml'))) ?? process.cwd();
  }

  private workspacePath(workspacePath: string): string {
    if (workspacePath) {
      return workspacePath;
    }
    if (process.env.ARC_WORKSPACE_PATH) {
      return process.env.ARC_WORKSPACE_PATH;
    }
    const rootDirIndex = process.argv.indexOf('--root-dir');
    if (rootDirIndex >= 0 && process.argv[rootDirIndex + 1]) {
      return process.argv[rootDirIndex + 1];
    }
    return workspacePath;
  }

  private workspaceSource(workspacePath: string): string {
    if (workspacePath) {
      return 'frontend';
    }
    if (process.env.ARC_WORKSPACE_PATH) {
      return 'ARC_WORKSPACE_PATH';
    }
    if (process.argv.includes('--root-dir')) {
      return '--root-dir';
    }
    return 'unset';
  }

  /** Error envelope — never fake successful product data. */
  private errorEnvelope<T>(command: string, error: unknown): ArcEnvelope<T> {
    return {
      version: ARC_PROTOCOL_VERSION,
      ok: false,
      data: null,
      error: {
        code: 'BACKEND_UNAVAILABLE',
        message: `ARC backend unavailable for ${command}: ${error}`,
      },
      meta: {
        duration_ms: 1,
        timestamp: new Date().toISOString(),
      },
    };
  }

  async inspectWorkspace(workspacePath: string): Promise<ArcEnvelope<WorkspaceInfo>> {
    const workspace = this.workspacePath(workspacePath);
    try {
      if (await this.isDaemonRunning()) {
        return this.callDaemon('/api/inspect', { workspace });
      }
      return this.runCli(['inspect', '--workspace', workspace]);
    } catch (e) {
      this.logger.warn(`inspectWorkspace failed: ${e}`);
      return this.errorEnvelope('inspect', e);
    }
  }

  async listRuntimes(workspacePath: string): Promise<ArcEnvelope<RuntimeInfo[]>> {
    const workspace = this.workspacePath(workspacePath);
    try {
      if (await this.isDaemonRunning()) {
        return this.callDaemon('/api/runtimes', { workspace });
      }
      return this.runCli(['runtimes', '--workspace', workspace]);
    } catch (e) {
      return this.errorEnvelope('runtimes', e);
    }
  }

  async listWorkflows(workspacePath: string, runtimeId?: string): Promise<ArcEnvelope<WorkflowInfo[]>> {
    const workspace = this.workspacePath(workspacePath);
    try {
      const args = ['workflows', '--workspace', workspace];
      if (runtimeId) args.push('--runtime', runtimeId);
      if (await this.isDaemonRunning()) {
        return this.callDaemon('/api/workflows', { workspace, runtime: runtimeId ?? '' });
      }
      return this.runCli(args);
    } catch (e) {
      return this.errorEnvelope('workflows', e);
    }
  }

  async listSchemas(workspacePath: string, runtimeId?: string): Promise<ArcEnvelope<SchemaInfo[]>> {
    const workspace = this.workspacePath(workspacePath);
    try {
      const args = ['schemas', '--workspace', workspace];
      if (runtimeId) args.push('--runtime', runtimeId);
      if (await this.isDaemonRunning()) {
        return this.callDaemon('/api/schemas', { workspace, runtime: runtimeId ?? '' });
      }
      return this.runCli(args);
    } catch (e) {
      return this.errorEnvelope('schemas', e);
    }
  }

  async startRun(workflowId: string, inputs?: Record<string, unknown>): Promise<ArcEnvelope<RunRecord>> {
    try {
      if (await this.isDaemonRunning()) {
        return this.callDaemon('/api/runs/start', { workflow_id: workflowId });
      }
      const args = ['run', workflowId];
      const workspace = this.workspacePath('');
      if (workspace) args.push('--workspace', workspace);
      return this.runCli(args);
    } catch (e) {
      return this.errorEnvelope('run', e);
    }
  }

  async getRun(runId: string): Promise<ArcEnvelope<RunRecord>> {
    try {
      if (await this.isDaemonRunning()) {
        return this.callDaemon(`/api/runs/${runId}`);
      }
      return this.runCli(['run', 'get', '--id', runId]);
    } catch (e) {
      return this.errorEnvelope('run', e);
    }
  }

  async listRuns(workspacePath: string): Promise<ArcEnvelope<RunRecord[]>> {
    const workspace = this.workspacePath(workspacePath);
    try {
      if (await this.isDaemonRunning()) {
        return this.callDaemon('/api/runs', { workspace });
      }
      return this.runCli(['runs', '--workspace', workspace]);
    } catch (e) {
      return this.errorEnvelope('runs', e);
    }
  }

  async generateContextPack(task: string, workspacePath?: string): Promise<ArcEnvelope<ContextPackEntry[]>> {
    try {
      const workspace = workspacePath ? this.workspacePath(workspacePath) : '';
      const args = ['context', 'pack', '--task', task];
      if (workspace) args.push('--workspace', workspace);
      if (await this.isDaemonRunning()) {
        return this.callDaemon('/api/context/pack', { task, workspace });
      }
      return this.runCli(args);
    } catch (e) {
      return this.errorEnvelope('context', e);
    }
  }

  async getDaemonStatus(): Promise<ArcEnvelope<{ running: boolean; version: string; pid?: number }>> {
    const running = await this.isDaemonRunning();
    return {
      version: ARC_PROTOCOL_VERSION,
      ok: true,
      data: { running, version: running ? 'unknown' : 'not-running' },
      error: null,
      meta: { timestamp: new Date().toISOString() },
    };
  }

  async getProviderStatus(provider: string, baseUrl?: string): Promise<ArcEnvelope<ProviderStatus>> {
    const normalized = (provider || '9router').trim();
    const envNames = this.providerApiKeyEnvNames(normalized);
    const apiKeySource = envNames.find(name => Boolean(process.env[name]));
    const baseUrlConfigured = Boolean(baseUrl?.trim() || process.env[`AI_PROVIDER_GATEWAY_${this.envProviderName(normalized)}_BASE_URL`]);
    return {
      version: ARC_PROTOCOL_VERSION,
      ok: true,
      data: {
        provider: normalized,
        baseUrlConfigured,
        apiKeyConfigured: Boolean(apiKeySource),
        apiKeySource,
        runtimeAvailable: true,
        message: apiKeySource
          ? `Provider credentials detected from environment. Local SwarmGraph run bridge is available; backend=${process.env.ARC_SWARMGRAPH_RUN_BACKEND ?? 'stub'}.`
          : `Local SwarmGraph run bridge is available with backend=${process.env.ARC_SWARMGRAPH_RUN_BACKEND ?? 'stub'}. Provider calls need one of: ${envNames.join(', ')}`,
      },
      error: null,
      meta: { timestamp: new Date().toISOString() },
    };
  }

  async getWorkspaceStatus(workspacePath: string): Promise<ArcEnvelope<{ frontendPath: string; backendPath: string; source: string }>> {
    return {
      version: ARC_PROTOCOL_VERSION,
      ok: true,
      data: {
        frontendPath: workspacePath,
        backendPath: this.workspacePath(workspacePath),
        source: this.workspaceSource(workspacePath),
      },
      error: null,
      meta: { timestamp: new Date().toISOString() },
    };
  }

  private providerApiKeyEnvNames(provider: string): string[] {
    if (provider.toLowerCase() === '9router') {
      return ['AI_PROVIDER_GATEWAY_9ROUTER_API_KEY', 'ROUTER_API_KEY', 'NINEROUTER_API_KEY', 'KILO_CODE_API_KEY'];
    }
    return [`AI_PROVIDER_GATEWAY_${this.envProviderName(provider)}_API_KEY`];
  }

  private envProviderName(provider: string): string {
    return provider.toUpperCase().replace(/[^A-Z0-9]/g, '_');
  }
}
