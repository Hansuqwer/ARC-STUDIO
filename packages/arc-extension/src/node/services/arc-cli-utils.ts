/**
 * Shared utilities for calling the ARC Python CLI
 * 
 * This module provides common constants and helper functions used across
 * ConfigService, RunLifecycleService, and AuditBridgeService when invoking
 * the Python CLI via execFileSync.
 */

import { execFile } from 'child_process';
import { promisify } from 'util';

/**
 * Environment variables allowed when calling the ARC CLI.
 * This allowlist ensures only safe, non-secret environment variables are passed.
 */
const ARC_CLI_ENV_ALLOWLIST = [
    'PATH',
    'HOME',
    'USER',
    'LANG',
    'LC_ALL',
    'TZ',
    'TMPDIR',
    'VIRTUAL_ENV',
    'VIRTUAL_ENV_PROMPT',
    'PYTHONPATH',
    'PIP_REQUIRE_VIRTUALENV',
];

/**
 * Build a sanitized environment object for ARC CLI calls.
 * Only includes variables from the allowlist.
 */
export function buildArcCliEnv(): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = {};
    for (const key of ARC_CLI_ENV_ALLOWLIST) {
        const value = process.env[key];
        if (value !== undefined) {
            env[key] = value;
        }
    }
    return env;
}

let _execFileAsync: ReturnType<typeof promisify> | undefined;

/**
 * Non-blocking ARC CLI invocation.
 *
 * Use this on hot backend paths (startRun, getConfigStatus, saveConfig) so a
 * slow CLI call never blocks the single-threaded Node event loop the way
 * execFileSync does. argv-only (no shell), sanitised env, timeout, and a
 * bounded output buffer.
 *
 * ``promisify(execFile)`` is created lazily so importing this module never
 * fails in tests that mock ``child_process`` without an ``execFile`` member.
 */
export async function execArcCliAsync(
    args: string[],
    opts: { timeout?: number; maxBuffer?: number } = {},
): Promise<string> {
    if (!_execFileAsync) {
        _execFileAsync = promisify(execFile);
    }
    const { stdout } = (await _execFileAsync('arc', args, {
        timeout: opts.timeout ?? 10000,
        maxBuffer: opts.maxBuffer ?? 1024 * 1024,
        windowsHide: true,
        encoding: 'utf-8',
        env: buildArcCliEnv(),
    })) as { stdout: string | Buffer };
    return typeof stdout === 'string' ? stdout : Buffer.from(stdout).toString('utf-8');
}

/**
 * Safe configuration keys that can be updated via the config API.
 * These keys do not contain secret values.
 */
export const SAFE_CONFIG_KEYS = [
    'defaultRuntime',
    'mode',
    'isolation',
    'allowPaidCalls',
    'dryRun',
    'routingMode',
    'selectedProfile'
];

/**
 * Pattern to detect unsafe configuration keys that might contain secrets.
 * Used to reject config updates that attempt to set secret values.
 */
export const UNSAFE_CONFIG_KEY_PATTERN = /(secret|token|password|api[_-]?key|raw.*key|credential)/i;

/**
 * Trust-sensitive flags used in workspace trust evaluation.
 * These flags indicate capabilities that require workspace trust.
 */
export const TRUST_SENSITIVE_FLAGS = [
    'can_run',
    'requires_paid_calls',
    'requires_shell',
    'requires_secrets',
    'requires_network',
];
