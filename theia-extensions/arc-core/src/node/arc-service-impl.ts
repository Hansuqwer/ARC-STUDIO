/**
 * ARC Service Implementation — Backend (Node.js)
 *
 * Calls the Python ARC daemon via:
 * 1. CLI mode: spawn `uv run arc <cmd> --json` (no daemon required)
 * 2. HTTP mode: call 127.0.0.1:7777 (daemon mode)
 *
 * Returns an error if neither daemon nor CLI is available. Fixture data lives
 * in tests/fixtures only, not the normal product path.
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
  ProviderDefinition,
  ProviderRoutingPolicy,
  RuntimeCapabilitiesResponse,
  StartRunRequest,
  GoldenTrace,
  EvalResult,
  ARC_PROTOCOL_VERSION,
} from '../common/arc-protocol';

const ARC_DAEMON_PORT = 7777;
const ARC_DAEMON_HOST = '127.0.0.1';
const ARC_CLI_TIMEOUT_MS = 30000;
const ARC_CLI_ENV_ALLOWLIST = ['PATH', 'HOME', 'LANG', 'LC_ALL', 'SHELL', 'TMPDIR', 'VIRTUAL_ENV'];
const ARC_CLI_DIAGNOSTIC_TAIL_BYTES = 2048;
const RUN_ID_RE = /^run-(sg|lg|ca|oa|ag2)-[a-f0-9]{6,64}$/;

export function validateRunId(runId: unknown): string {
  if (typeof runId !== 'string' || !RUN_ID_RE.test(runId)) {
    throw new Error('invalid run id');
  }
  return runId;
}

export function validateOtlpEndpoint(endpoint: unknown): string {
  if (typeof endpoint !== 'string' || endpoint.length === 0 || endpoint.length > 2048) {
    throw new Error('invalid otlp endpoint');
  }
  let url: URL;
  try {
    url = new URL(endpoint);
  } catch {
    throw new Error('invalid otlp endpoint');
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('otlp endpoint must be http(s)');
  }
  if (url.username || url.password) {
    throw new Error('otlp endpoint must not embed credentials');
  }
  const host = url.hostname.toLowerCase();
  const isPrivate = host === 'localhost'
    || host === '::1'
    || host.startsWith('127.')
    || host.startsWith('10.')
    || host.startsWith('192.168.')
    || /^172\.(1[6-9]|2\d|3[01])\./.test(host)
    || host.endsWith('.local')
    || host === '0.0.0.0';
  if (isPrivate && process.env.ARC_OTLP_ALLOW_PRIVATE !== 'true') {
    throw new Error('private/loopback otlp endpoint requires ARC_OTLP_ALLOW_PRIVATE=true');
  }
  return url.toString();
}

export function buildStartRunArgs(request: StartRunRequest): string[] {
  const runtime = Array.isArray(request.runtime) ? request.runtime.join(',') : request.runtime ?? 'auto';
  const args = ['run', request.workflow_id, '--runtime', runtime];
  if (request.profile_id) {
    args.push('--profile-id', request.profile_id);
  }
  if (request.allow_paid_calls === true) {
    args.push('--allow-paid-calls');
  }
  return args;
}

export function resolveWorkspaceRoot(raw: string | undefined): string {
  if (!raw || typeof raw !== 'string') {
    throw new Error('workspace path is not set');
  }
  const stripped = raw.startsWith('file://') ? new URL(raw).pathname : raw;
  const abs = path.resolve(stripped);
  if (!path.isAbsolute(abs)) {
    throw new Error('workspace path must be absolute');
  }
  if (abs.includes('\0')) {
    throw new Error('workspace path contains null byte');
  }
  try {
    if (!fs.statSync(abs).isDirectory()) {
      throw new Error('workspace path is not a directory');
    }
  } catch {
    throw new Error('workspace path is not accessible');
  }
  return abs;
}

export function safeJoinInsideWorkspace(workspaceRoot: string, ...segments: string[]): string {
  const root = resolveWorkspaceRoot(workspaceRoot);
  const joined = path.resolve(root, ...segments);
  const rel = path.relative(root, joined);
  if (rel.startsWith('..') || path.isAbsolute(rel)) {
    throw new Error('path escapes workspace');
  }
  return joined;
}

interface RedactedDiagnostics {
  readonly resolvedBinary: string;
  readonly cwd: string;
  readonly exitCode: number | null;
  readonly signal: NodeJS.Signals | null;
  readonly envKeysAllowed: readonly string[];
  readonly stderrTail: string;
  readonly stdoutTail: string;
}

class ArcCliError extends Error {
  constructor(
    message: string,
    readonly stderr = '',
    readonly stdout = '',
    readonly command = '',
    readonly diagnostics?: RedactedDiagnostics
  ) {
    super(message);
    this.name = 'ArcCliError';
  }
}

@injectable()
export class ArcServiceImpl implements ArcService {

  @inject(ILogger)
  protected readonly logger: ILogger;

  /** Tracks active CLI subprocesses for cancellation support. */
  private static readonly runningProcs: Map<string, cp.ChildProcess> = new Map();
  private static procCounter = 0;

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

  /** Return an Authorization header if ARC_DAEMON_TOKEN is set */
  private daemonAuthHeaders(): Record<string, string> {
    const token = process.env.ARC_DAEMON_TOKEN;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /** Call the daemon HTTP API */
  private async callDaemon<T>(endpoint: string, params?: Record<string, string>): Promise<ArcEnvelope<T>> {
    const queryStr = params ? '?' + new URLSearchParams(params).toString() : '';
    const url = `http://${ARC_DAEMON_HOST}:${ARC_DAEMON_PORT}${endpoint}${queryStr}`;

    return new Promise((resolve, reject) => {
      const req = http.get(url, { timeout: ARC_CLI_TIMEOUT_MS, headers: { ...this.daemonAuthHeaders() } }, res => {
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

  private async postDaemon<T>(endpoint: string, body: Record<string, unknown>): Promise<ArcEnvelope<T>> {
    const payload = JSON.stringify(body);
    const options: http.RequestOptions = {
      hostname: ARC_DAEMON_HOST,
      port: ARC_DAEMON_PORT,
      path: endpoint,
      method: 'POST',
      timeout: ARC_CLI_TIMEOUT_MS,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
        ...this.daemonAuthHeaders(),
      },
    };

    return new Promise((resolve, reject) => {
      const req = http.request(options, res => {
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
      req.write(payload);
      req.end();
    });
  }

  /** Spawn ARC CLI and parse JSON output */
  private async runCli<T>(args: string[], envOverrides: NodeJS.ProcessEnv = {}): Promise<ArcEnvelope<T>> {
    const procKey = `cli-${++ArcServiceImpl.procCounter}`;
    return new Promise((resolve, reject) => {
      const fullArgs = [...args, '--json'];
      const pythonDir = this.pythonProjectDir();
      const arcBin = path.join(pythonDir, '.venv', 'bin', 'arc');
      const command = fs.existsSync(arcBin) ? arcBin : 'uv';
      const commandArgs = fs.existsSync(arcBin) ? fullArgs : ['run', 'arc', ...fullArgs];
      const env = this.cliEnv({ ARC_JSON_OUTPUT: '1', ...envOverrides });
      this.logger.debug(`ARC CLI: ${command} ${commandArgs.join(' ')}`);

      const proc = cp.spawn(command, commandArgs, {
        cwd: pythonDir,
        timeout: ARC_CLI_TIMEOUT_MS,
        env,
      });

      ArcServiceImpl.runningProcs.set(procKey, proc);

      let stdout = '';
      let stderr = '';
      proc.stdout?.on('data', d => stdout += d);
      proc.stderr?.on('data', d => stderr += d);

      proc.on('close', code => {
        ArcServiceImpl.runningProcs.delete(procKey);
        if (code !== 0 && !stdout.trim()) {
          reject(new ArcCliError(
            `ARC CLI failed (exit ${code})`,
            stderr,
            stdout,
            `${command} ${commandArgs.join(' ')}`,
            this.cliDiagnostics(command, commandArgs, pythonDir, env, code, null, stdout, stderr)
          ));
          return;
        }
        try {
          resolve(JSON.parse(stdout));
        } catch (e) {
          reject(new ArcCliError(
            'ARC CLI returned invalid JSON',
            stderr,
            stdout,
            `${command} ${commandArgs.join(' ')}`,
            this.cliDiagnostics(command, commandArgs, pythonDir, env, code, null, stdout, stderr)
          ));
        }
      });

      proc.on('error', err => {
        ArcServiceImpl.runningProcs.delete(procKey);
        reject(new ArcCliError(
          `ARC CLI spawn failed: ${err.message}`,
          stderr,
          stdout,
          `${command} ${commandArgs.join(' ')}`,
          this.cliDiagnostics(command, commandArgs, pythonDir, env, null, null, stdout, stderr, err.message)
        ));
      });
    });
  }

  private cliDiagnostics(
    command: string,
    args: string[],
    cwd: string,
    env: NodeJS.ProcessEnv,
    exitCode: number | null,
    signal: NodeJS.Signals | null,
    stdout: string,
    stderr: string,
    spawnError?: string
  ): RedactedDiagnostics {
    return {
      resolvedBinary: command,
      cwd,
      envKeysAllowed: Object.keys(env).sort(),
      exitCode,
      signal,
      stdoutTail: this.redactDiagnosticText(this.tail(stdout)),
      stderrTail: this.redactDiagnosticText(this.tail(spawnError ? `${stderr}\n${spawnError}` : stderr)),
    };
  }

  private tail(value: string): string {
    return value.length <= ARC_CLI_DIAGNOSTIC_TAIL_BYTES
      ? value
      : value.slice(value.length - ARC_CLI_DIAGNOSTIC_TAIL_BYTES);
  }

  private redactDiagnosticText(value: string): string {
    let redacted = value.replace(/sk-[A-Za-z0-9_-]{6,}/g, 'sk-***redacted***');
    for (const fake of ['redacted', 'qwen-redacted', 'kimi-redacted', 'openai-redacted', 'anthropic-redacted'].map(suffix => `sk-test-${suffix}`)) {
      redacted = redacted.split(fake).join('sk-test-***redacted***');
    }
    return this.sanitize(redacted);
  }

  private pythonProjectDir(): string {
    const candidates = [
      process.env.ARC_PYTHON_DIR,
      path.resolve(process.cwd(), 'python'),
      path.resolve(process.cwd(), '..', '..', 'python'),
    ].filter((candidate): candidate is string => Boolean(candidate));
    return candidates.find(candidate => fs.existsSync(path.join(candidate, 'pyproject.toml'))) ?? process.cwd();
  }

  private cliEnv(overrides: NodeJS.ProcessEnv): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = {};
    for (const key of ARC_CLI_ENV_ALLOWLIST) {
      if (process.env[key]) {
        env[key] = process.env[key];
      }
    }
    for (const [key, value] of Object.entries(process.env)) {
      if (key.startsWith('ARC_') && value) {
        env[key] = value;
      }
    }
    if (process.env.PYTHONPATH) {
      env.PYTHONPATH = process.env.PYTHONPATH;
    }
    return { ...env, ...overrides };
  }

  private workspacePath(workspacePath: string): string {
    if (workspacePath) {
      return resolveWorkspaceRoot(workspacePath);
    }
    if (process.env.ARC_WORKSPACE_PATH) {
      return resolveWorkspaceRoot(process.env.ARC_WORKSPACE_PATH);
    }
    const rootDirIndex = process.argv.indexOf('--root-dir');
    if (rootDirIndex >= 0 && process.argv[rootDirIndex + 1]) {
      return resolveWorkspaceRoot(process.argv[rootDirIndex + 1]);
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
    const err = error instanceof Error ? error : new Error(String(error));
    const stderr = error instanceof ArcCliError ? this.sanitize(error.stderr).slice(-2000) : undefined;
    const stdout = error instanceof ArcCliError ? this.sanitize(error.stdout).slice(-2000) : undefined;
    const cliCommand = error instanceof ArcCliError ? this.sanitize(error.command) : undefined;
    const diagnostics = error instanceof ArcCliError ? error.diagnostics : undefined;
    const detail = stderr || stdout || cliCommand;
    const message = detail
      ? `ARC backend unavailable for ${command}: ${this.sanitize(err.message)}: ${detail}`
      : `ARC backend unavailable for ${command}: ${this.sanitize(err.message)}`;
    return {
      version: ARC_PROTOCOL_VERSION,
      ok: false,
      data: null,
      error: {
        code: 'BACKEND_UNAVAILABLE',
        message,
        details: {
          command,
          name: err.name,
          message: detail ? `${this.sanitize(err.message)}: ${detail}` : this.sanitize(err.message),
          ...(stderr ? { stderr } : {}),
          ...(stdout ? { stdout } : {}),
          ...(diagnostics ? { diagnostics } : {}),
        },
      },
      meta: {
        duration_ms: 1,
        timestamp: new Date().toISOString(),
      },
    };
  }

  private sanitize(value: string): string {
    return value
      .replace(/sk-[A-Za-z0-9_-]{8,}/g, 'sk-REDACTED')
      .replace(/(api[_-]?key\s*[=:]\s*)[^\s]+/ig, '$1REDACTED')
      .replace(/(authorization:\s*bearer\s+)[^\s]+/ig, '$1REDACTED');
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

  async listRuntimeCapabilities(workspacePath: string): Promise<ArcEnvelope<RuntimeCapabilitiesResponse>> {
    const workspace = this.workspacePath(workspacePath);
    try {
      if (await this.isDaemonRunning()) {
        return this.callDaemon('/api/runtimes/capabilities', { workspace });
      }
      return this.runCli(['runtimes', '--workspace', workspace, '--capabilities']);
    } catch (e) {
      return this.errorEnvelope('runtimes capabilities', e);
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

  async startRun(request: StartRunRequest): Promise<ArcEnvelope<RunRecord>> {
    try {
      if (process.env.ARC_SWARMGRAPH_RUN_BACKEND !== 'stub' && await this.isDaemonRunning()) {
        return this.postDaemon('/api/runs/start', request as unknown as Record<string, unknown>);
      }
      const args = buildStartRunArgs(request);
      const extraEnv = request.allow_paid_calls === true
        ? { ARC_SWARMGRAPH_ALLOW_COSTS: 'true' }
        : {};
      const requestedWorkspace = process.env.ARC_SWARMGRAPH_RUN_BACKEND === 'stub' && process.env.ARC_WORKSPACE_PATH
        ? process.env.ARC_WORKSPACE_PATH
        : typeof request.inputs?.workspacePath === 'string' ? request.inputs.workspacePath : '';
      const workspace = this.workspacePath(requestedWorkspace);
      if (workspace) args.push('--workspace', workspace);
      const prompt = typeof request.inputs?.prompt === 'string' ? request.inputs.prompt.trim() : '';
      if (prompt) args.push('--prompt', prompt);
      return this.runCli(args, extraEnv);
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
    const normalized = (provider || 'openai').trim();
    const envNames = this.providerApiKeyEnvNames(normalized);
    const apiKeySource = envNames.find(name => Boolean(process.env[name]));
    const baseUrlConfigured = Boolean(baseUrl?.trim() || process.env[`ARC_PROVIDER_${this.envProviderName(normalized)}_BASE_URL`]);
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
          ? `Provider credentials detected from environment. Live calls remain disabled unless ARC_ALLOW_LIVE_PROVIDER_TESTS=true.`
          : `Provider calls need one of: ${envNames.join(', ')}. Dry-run mode is active by default.`,
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

  async listProviders(): Promise<ArcEnvelope<ProviderDefinition[]>> {
    try {
      if (await this.isDaemonRunning()) {
        return this.callDaemon('/api/providers');
      }
    } catch (e) {
      return this.errorEnvelope('providers', e);
    }
    return {
      version: ARC_PROTOCOL_VERSION,
      ok: true,
      data: [
        { id: 'openai', display_name: 'OpenAI / ChatGPT', default_base_url: 'https://api.openai.com/v1', env_key_names: ['OPENAI_API_KEY'], auth_header: 'bearer', default_models: ['gpt-4.1', 'gpt-4.1-mini', 'o4-mini'], supports_streaming: true, supports_tools: true },
        { id: 'anthropic', display_name: 'Anthropic / Claude', default_base_url: 'https://api.anthropic.com', env_key_names: ['ANTHROPIC_API_KEY'], auth_header: 'x-api-key', default_models: ['claude-opus-4', 'claude-sonnet-4', 'claude-haiku-4'], supports_streaming: true, supports_tools: true },
        { id: 'openrouter', display_name: 'OpenRouter', default_base_url: 'https://openrouter.ai/api/v1', env_key_names: ['OPENROUTER_API_KEY'], auth_header: 'bearer', default_models: ['openai/gpt-4.1-mini', 'anthropic/claude-sonnet-4'], supports_streaming: true, supports_tools: true },
        { id: 'qwen', display_name: 'Qwen', default_base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', env_key_names: ['QWEN_API_KEY', 'DASHSCOPE_API_KEY'], auth_header: 'bearer', default_models: ['qwen-max', 'qwen-plus', 'qwen-turbo'], supports_streaming: true, supports_tools: true },
        { id: 'kimi', display_name: 'Kimi / Moonshot', default_base_url: 'https://api.moonshot.ai/v1', env_key_names: ['MOONSHOT_API_KEY', 'KIMI_API_KEY'], auth_header: 'bearer', default_models: ['kimi-k2', 'moonshot-v1-128k', 'moonshot-v1-32k'], supports_streaming: true, supports_tools: true },
        { id: 'g4f-groq', display_name: 'G4F: Groq (Free)', default_base_url: 'https://g4f.space/api/groq', env_key_names: [], auth_header: 'bearer', default_models: ['llama-3.1-8b-instant', 'llama-3.3-70b-versatile', 'qwen/qwen3-32b'], supports_streaming: true, supports_tools: true },
        { id: 'g4f-gemini', display_name: 'G4F: Gemini (Free)', default_base_url: 'https://g4f.space/api/gemini', env_key_names: [], auth_header: 'bearer', default_models: ['models/gemini-2.5-flash', 'models/gemini-3-flash-preview', 'models/gemini-flash-latest'], supports_streaming: true, supports_tools: true },
        { id: 'g4f-nvidia', display_name: 'G4F: Nvidia (Free)', default_base_url: 'https://g4f.space/api/nvidia', env_key_names: [], auth_header: 'bearer', default_models: ['deepseek-ai/deepseek-v4-pro', 'nvidia/nemotron-3-super-120b-a12b', 'meta/llama-3.3-70b-instruct'], supports_streaming: true, supports_tools: true },
        { id: 'g4f-pollinations', display_name: 'G4F: Pollinations (Free)', default_base_url: 'https://g4f.space/api/pollinations', env_key_names: [], auth_header: 'bearer', default_models: ['openai-fast', 'claude-fast', 'gemini-fast', 'mistral'], supports_streaming: true, supports_tools: true },
        { id: 'g4f-ollama', display_name: 'G4F: Ollama (Free)', default_base_url: 'https://g4f.space/api/ollama', env_key_names: [], auth_header: 'bearer', default_models: ['deepseek-v4-pro', 'glm-5.1', 'qwen3.5:397b', 'nemotron-3-super'], supports_streaming: true, supports_tools: true },
      ],
      error: null,
      meta: { timestamp: new Date().toISOString() },
    };
  }

  async listProviderStatuses(): Promise<ArcEnvelope<ProviderStatus[]>> {
    const providers = await this.listProviders();
    return {
      version: ARC_PROTOCOL_VERSION,
      ok: true,
      data: (providers.data ?? []).map(provider => {
        const source = provider.env_key_names.find(name => Boolean(process.env[name]));
        return {
          provider: provider.id,
          display_name: provider.display_name,
          enabled: true,
          dry_run: true,
          base_url_configured: true,
          api_key_configured: Boolean(source),
          api_key_source: source,
          runtimeAvailable: true,
          baseUrlConfigured: true,
          apiKeyConfigured: Boolean(source),
          apiKeySource: source,
          message: 'Dry-run provider definition loaded. Live calls require ARC_ALLOW_LIVE_PROVIDER_TESTS=true.',
        } as ProviderStatus;
      }),
      error: null,
      meta: { timestamp: new Date().toISOString() },
    };
  }

  async getProviderRouting(): Promise<ArcEnvelope<ProviderRoutingPolicy>> {
    return {
      version: ARC_PROTOCOL_VERSION,
      ok: true,
      data: { mode: 'manual', default_provider: 'openai', default_model: 'gpt-4.1-mini', dry_run: true, allow_paid_calls: false, max_retries: 1, timeout_ms: 30000 },
      error: null,
      meta: { timestamp: new Date().toISOString() },
    };
  }

  private providerApiKeyEnvNames(provider: string): string[] {
    if (provider.toLowerCase() === 'openai') {
      return ['OPENAI_API_KEY'];
    }
    if (provider.toLowerCase() === 'anthropic') {
      return ['ANTHROPIC_API_KEY'];
    }
    if (provider.toLowerCase() === 'openrouter') {
      return ['OPENROUTER_API_KEY'];
    }
    if (provider.toLowerCase() === 'qwen') {
      return ['QWEN_API_KEY', 'DASHSCOPE_API_KEY'];
    }
    if (provider.toLowerCase() === 'kimi') {
      return ['MOONSHOT_API_KEY', 'KIMI_API_KEY'];
    }
    // All G4F providers are free (no API key needed)
    if (provider.toLowerCase().startsWith('g4f-')) {
      return [];
    }
    return [`ARC_PROVIDER_${this.envProviderName(provider)}_API_KEY`];
  }

  private envProviderName(provider: string): string {
    return provider.toUpperCase().replace(/[^A-Z0-9]/g, '_');
  }

  async exportTraceToOTLP(runId: string, endpoint: string): Promise<ArcEnvelope<{ exported: boolean; warning?: string }>> {
    try {
      const safeRunId = validateRunId(runId);
      const safeEndpoint = validateOtlpEndpoint(endpoint);
      if (await this.isDaemonRunning()) {
        return this.postDaemon(`/api/telemetry/export/${safeRunId}`, { endpoint: safeEndpoint });
      }
      return this.errorEnvelope('export-trace', new Error('Daemon not running'));
    } catch (e) {
      return this.errorEnvelope('export-trace', e);
    }
  }

  async evalRun(runId: string, golden: GoldenTrace): Promise<ArcEnvelope<EvalResult>> {
    try {
      if (await this.isDaemonRunning()) {
        return this.postDaemon('/api/evals/run', { run_id: runId, golden });
      }
      return this.errorEnvelope('eval-run', new Error('Daemon not running'));
    } catch (e) {
      return this.errorEnvelope('eval-run', e);
    }
  }

  async cancelRun(_runId: string): Promise<ArcEnvelope<{ cancelled: boolean }>> {
    // The CLI subprocess tracking uses internal counters since the runId
    // is only known after the CLI exits. For cancellation we kill all
    // tracked running processes — coarse but sufficient for alpha.
    let cancelled = false;
    for (const [key, proc] of ArcServiceImpl.runningProcs.entries()) {
      if (proc.pid !== undefined && !proc.killed) {
        try {
          proc.kill('SIGTERM');
          cancelled = true;
        } catch {
          // process already exited
        }
      }
      ArcServiceImpl.runningProcs.delete(key);
    }
    return {
      version: ARC_PROTOCOL_VERSION,
      ok: true,
      data: { cancelled },
      error: null,
      meta: { duration_ms: 1, timestamp: new Date().toISOString() },
    };
  }
}
