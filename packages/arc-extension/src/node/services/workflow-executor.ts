/**
 * Workflow Executor Service
 *
 * Handles SwarmGraph workflow execution, process management,
 * command execution with security, and workflow cancellation.
 */

import { spawn, ChildProcess } from 'child_process';
import { injectable } from '@theia/core/shared/inversify';
import {
    ExecutionOptions,
    ExecutionResult,
    CancelResult,
    ArcError,
    ArcErrorCode
} from '../../common/arc-protocol';
import {
    sanitizePrompt as strictSanitizePrompt,
    validateBackend as strictValidateBackend,
    sanitizeErrorMessage as strictSanitizeErrorMessage,
} from '../security-utils';
import * as fs from 'fs-extra';
import * as path from 'path';

/**
 * Allow-list of environment variables passed to child processes.
 * Prevents unbounded environment inheritance (P1 security fix).
 */
const SUBPROCESS_ENV_ALLOWLIST = [
    'PATH', 'HOME', 'USER', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR',
    'ARC_SWARMGRAPH_CLI',
    'ARC_SWARMGRAPH_RUN_BACKEND',
    'ARC_SWARMGRAPH_ALLOW_COSTS',
    'ARC_SWARMGRAPH_GATEWAY_URL',
];

function buildChildEnv(): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = {};
    for (const key of SUBPROCESS_ENV_ALLOWLIST) {
        const value = process.env[key];
        if (value !== undefined) env[key] = value;
    }
    return env;
}

@injectable()
export class WorkflowExecutor {
    private runningProcesses = new Map<string, ChildProcess>();

    /**
     * Execute a SwarmGraph workflow with enhanced validation and error handling.
     */
    async executeWorkflow(
        prompt: string,
        options?: ExecutionOptions
    ): Promise<ExecutionResult> {
        const startTime = Date.now();

        try {
            // Input validation
            this.validatePrompt(prompt);

            // Validate and sanitize options
            const backend = strictValidateBackend(options?.backend || 'gateway');
            const costAllowed = options?.costAllowed !== false;
            const timeout = options?.timeout || 300000;
            const workspaceRoot = options?.workspaceRoot || process.cwd();

            // Check SwarmGraph CLI availability
            const cliPath = await this.findExecutable('swarmgraph', workspaceRoot);
            if (!cliPath) {
                throw new ArcError(
                    ArcErrorCode.RUN_FAILED,
                    'SwarmGraph CLI (swarmgraph) not found. Please install SwarmGraph first.',
                    { command: 'swarmgraph' }
                );
            }

            // Sanitize prompt for safe command execution
            const sanitizedPrompt = strictSanitizePrompt(prompt);

            // Build command arguments
            const args = this.buildSwarmArgs(sanitizedPrompt, backend, costAllowed);

            // Generate tentative run ID for tracking
            const tentativeRunId = `run-sg-${Date.now().toString(16)}`;
            this.runningProcesses.set(tentativeRunId, null!);

            // Execute command with streaming support
            const result = await this.executeCommandWithTimeout(
                cliPath,
                args,
                timeout,
                workspaceRoot,
                tentativeRunId
            );

            // Always compute a trace path (even on failure, may have partial trace)
            const tracePath = `.arc/traces/${tentativeRunId}.jsonl`;

            // Parse output to extract definitive run ID
            const runId = this.extractRunId(result.stdout) || tentativeRunId;

            // Determine execution status
            const status = this.determineExecutionStatus(result);

            // Build result
            const duration = Date.now() - startTime;

            if (status === 'failed') {
                return {
                    runId,
                    status: 'failed',
                    error: this.formatErrorMessage(result),
                    tracePath,
                    duration
                };
            }

            return {
                runId,
                status,
                output: this.extractOutput(result.stdout),
                tracePath,
                duration
            };
        } catch (error: any) {
            const duration = Date.now() - startTime;

            if (error instanceof ArcError) {
                if (error.code === ArcErrorCode.INVALID_INPUT) {
                    throw error;
                }
                return {
                    runId: 'failed',
                    status: 'failed',
                    error: error.message,
                    tracePath: '',
                    duration
                };
            }

            return {
                runId: 'failed',
                status: 'failed',
                error: strictSanitizeErrorMessage(error),
                tracePath: '',
                duration
            };
        }
    }

    /**
     * Cancel a running workflow execution.
     */
    async cancelWorkflow(runId: string): Promise<CancelResult> {
        try {
            const process = this.runningProcesses.get(runId);

            if (!process || (process as any).killed) {
                return {
                    success: false,
                    runId,
                    message: 'No running process found for this run ID'
                };
            }

            process.kill('SIGTERM');
            this.runningProcesses.delete(runId);

            return {
                success: true,
                runId,
                message: 'Workflow execution cancelled'
            };
        } catch (error) {
            return {
                success: false,
                runId,
                message: strictSanitizeErrorMessage(error)
            };
        }
    }

    // ========== Command Execution ==========

    /**
     * Build swarmgraph CLI arguments.
     */
    private buildSwarmArgs(prompt: string, backend: string, costAllowed: boolean): string[] {
        return [
            'swarm',
            '--json',
            prompt,
            ...(backend !== 'gateway' ? ['--backend', backend] : []),
            ...(costAllowed ? ['--cost-allowed'] : ['--no-cost'])
        ];
    }

    /**
     * Execute a command with timeout and streaming support.
     */
    private executeCommandWithTimeout(
        command: string,
        args: string[],
        timeout: number,
        cwd: string,
        runId: string
    ): Promise<{ stdout: string; stderr: string; exitCode: number; timedOut: boolean }> {
        return new Promise((resolve, reject) => {
            const child = spawn(command, args, {
                cwd,
                shell: false,
                env: buildChildEnv(),
                detached: process.platform !== 'win32',
                stdio: ['ignore', 'pipe', 'pipe']
            });

            this.runningProcesses.set(runId, child);

            let stdout = '';
            let stderr = '';
            let killed = false;
            let timeoutHandle: NodeJS.Timeout;

            child.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            child.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            child.on('close', (code) => {
                clearTimeout(timeoutHandle);
                this.runningProcesses.delete(runId);

                if (killed) {
                    resolve({
                        stdout,
                        stderr,
                        exitCode: 124,
                        timedOut: true
                    });
                } else {
                    resolve({
                        stdout,
                        stderr,
                        exitCode: code ?? 0,
                        timedOut: false
                    });
                }
            });

            child.on('error', (error) => {
                clearTimeout(timeoutHandle);
                this.runningProcesses.delete(runId);
                reject(new ArcError(
                    ArcErrorCode.RUN_FAILED,
                    `Failed to execute command: ${command} ${args.join(' ')}`,
                    { error: error.message, command, args }
                ));
            });

            timeoutHandle = setTimeout(() => {
                killed = true;
                this.killProcessTree(child, 'SIGTERM');

                setTimeout(() => {
                    if (!child.killed) {
                        this.killProcessTree(child, 'SIGKILL');
                    }
                }, 5000);

                reject(new ArcError(
                    ArcErrorCode.TIMEOUT,
                    `Command execution timed out after ${timeout}ms`,
                    { command, args, timeout }
                ));
            }, timeout);
        });
    }

    private killProcessTree(child: ChildProcess, signal: NodeJS.Signals): void {
        if (child.pid && process.platform !== 'win32') {
            try {
                process.kill(-child.pid, signal);
                return;
            } catch {
                // Fall back to direct kill if the process group is already gone.
            }
        }
        child.kill(signal);
    }

    // ========== Validation ==========

    /**
     * Validate prompt input.
     */
    private validatePrompt(prompt: string): void {
        if (!prompt || typeof prompt !== 'string' || prompt.trim().length === 0) {
            throw new ArcError(
                ArcErrorCode.INVALID_INPUT,
                'Prompt must be a non-empty string',
                { prompt: typeof prompt === 'string' ? prompt.substring(0, 100) : prompt }
            );
        }

        if (prompt.length > 10000) {
            throw new ArcError(
                ArcErrorCode.INVALID_INPUT,
                'Prompt exceeds maximum length of 10000 characters',
                { length: prompt.length, max: 10000 }
            );
        }
    }

    // ========== Output Processing ==========

    /**
     * Determine execution status from command result.
     */
    private determineExecutionStatus(result: { stdout: string; stderr: string; exitCode: number }): 'completed' | 'failed' | 'running' {
        if (result.exitCode !== 0) {
            return 'failed';
        }

        try {
            const lines = result.stdout.split('\n').filter(line => line.trim());
            for (const line of lines) {
                if (line.startsWith('{')) {
                    const jsonData = JSON.parse(line);
                    if (jsonData.status === 'failed' || jsonData.status === 'error') {
                        return 'failed';
                    }
                    if (jsonData.error || jsonData.exception) {
                        return 'failed';
                    }
                }
            }
        } catch {
            // JSON parse errors are non-fatal
        }

        return 'completed';
    }

    /**
     * Extract meaningful output from stdout.
     */
    private extractOutput(stdout: string): string {
        const lines = stdout.split('\n').filter(line => line.trim());
        const outputLines: string[] = [];

        for (const line of lines) {
            if (line.startsWith('{')) {
                try {
                    const json = JSON.parse(line);
                    if (json.output) {
                        outputLines.push(json.output);
                    }
                    if (json.result) {
                        outputLines.push(json.result);
                    }
                    if (json.message) {
                        outputLines.push(json.message);
                    }
                    if (json.final_output) {
                        outputLines.push(json.final_output);
                    }
                } catch {
                    outputLines.push(line);
                }
            } else {
                outputLines.push(line);
            }
        }

        return outputLines.join('\n').trim() || stdout.trim();
    }

    /**
     * Format error message from execution result.
     */
    private formatErrorMessage(result: { stdout: string; stderr: string; exitCode: number }): string {
        try {
            const lines = result.stdout.split('\n').filter(line => line.trim());
            for (const line of lines) {
                if (line.startsWith('{')) {
                    const json = JSON.parse(line);
                    if (json.error) {
                        return String(json.error);
                    }
                    if (json.exception) {
                        return String(json.exception);
                    }
                    if (json.message && json.status === 'failed') {
                        return String(json.message);
                    }
                }
            }
        } catch {
            // Fall through to stderr
        }

        const stderr = result.stderr.trim();
        if (stderr && !stderr.includes('DEBUG') && !stderr.includes('INFO')) {
            return stderr;
        }

        return `Workflow execution failed with exit code ${result.exitCode}`;
    }

    // ========== Utilities ==========

    /**
     * Extract run ID from command output.
     */
    private extractRunId(output: string): string | null {
        try {
            const lines = output.split('\n').filter(line => line.trim());
            for (const line of lines) {
                if (line.startsWith('{')) {
                    const jsonData = JSON.parse(line);
                    if (jsonData.id) return String(jsonData.id);
                    if (jsonData.run_id) return String(jsonData.run_id);
                    if (jsonData.runId) return String(jsonData.runId);
                }
            }
        } catch {
            // Fall through to regex
        }

        const runIdMatch = output.match(/run-sg-([a-f0-9]+)/);
        if (runIdMatch) {
            return `run-sg-${runIdMatch[1]}`;
        }

        return null;
    }

    /**
     * Find executable in workspace or PATH.
     */
    private async findExecutable(name: string, workspaceRoot: string): Promise<string | null> {
        const configured = process.env.ARC_SWARMGRAPH_CLI;
        if (configured && await fs.pathExists(configured)) {
            return configured;
        }

        const systemPath = await this.whichExecutable(name);
        if (systemPath) return systemPath;

        if (process.env.ARC_TRUST_WORKSPACE_LAUNCHER === '1') {
            const localPath = path.join(workspaceRoot, name);
            if (await fs.pathExists(localPath)) {
                return localPath;
            }
        }

        return null;
    }

    /**
     * Find an executable in PATH.
     */
    private async whichExecutable(name: string): Promise<string | null> {
        try {
            const opId = `which-${name}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
            const { stdout } = await this.executeCommandWithTimeout(
                'which',
                [name],
                5000,
                process.cwd(),
                opId
            );
            const execPath = stdout.trim();
            if (execPath && await fs.pathExists(execPath)) {
                return execPath;
            }
        } catch {
            // Not found
        }
        return null;
    }
}
