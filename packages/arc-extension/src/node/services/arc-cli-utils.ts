/**
 * Shared utilities for calling the ARC Python CLI
 * 
 * This module provides common constants and helper functions used across
 * ConfigService, RunLifecycleService, and AuditBridgeService when invoking
 * the Python CLI via execFileSync.
 */

/**
 * Environment variables allowed when calling the ARC CLI.
 * This allowlist ensures only safe, non-secret environment variables are passed.
 */
const ARC_CLI_ENV_ALLOWLIST = ['PATH', 'HOME', 'USER', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR'];

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
