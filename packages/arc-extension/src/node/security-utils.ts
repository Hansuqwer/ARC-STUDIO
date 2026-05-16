/**
 * Security Utilities
 * 
 * Provides input validation, sanitization, and security checks
 * for the ARC Backend Service.
 */

import * as path from 'path';

/**
 * Validates and sanitizes user prompts to prevent command injection
 */
export function sanitizePrompt(prompt: string): string {
    if (!prompt || typeof prompt !== 'string') {
        throw new Error('Invalid prompt: must be a non-empty string');
    }

    // Limit prompt length to prevent DoS
    const MAX_PROMPT_LENGTH = 10000;
    if (prompt.length > MAX_PROMPT_LENGTH) {
        throw new Error(`Prompt exceeds maximum length of ${MAX_PROMPT_LENGTH} characters`);
    }

    // Remove null bytes and other control characters that could be used for injection
    const sanitized = prompt.replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '');

    // Check for shell metacharacters that could enable command injection
    const dangerousPatterns = [
        /[;&|`$(){}[\]<>]/,  // Shell metacharacters
        /\$\(/,               // Command substitution
        /`/,                  // Backtick command substitution
    ];

    for (const pattern of dangerousPatterns) {
        if (pattern.test(sanitized)) {
            throw new Error('Prompt contains potentially dangerous characters');
        }
    }

    return sanitized.trim();
}

/**
 * Validates trace ID to prevent path traversal attacks
 * Supports multiple runtime prefixes: sg (SwarmGraph), lg (LangGraph), 
 * ca (Claude), openai
 */
export function validateTraceId(traceId: string): string {
    if (!traceId || typeof traceId !== 'string') {
        throw new Error('Invalid trace ID: must be a non-empty string');
    }

    // Trace IDs should match the pattern: run-[prefix]-[hexadecimal]
    const traceIdPattern = /^run-(sg|lg|ca|openai)-[a-f0-9]+$/;
    if (!traceIdPattern.test(traceId)) {
        throw new Error('Invalid trace ID format');
    }

    // Additional check: ensure no path traversal characters
    if (traceId.includes('..') || traceId.includes('/') || traceId.includes('\\')) {
        throw new Error('Trace ID contains invalid path characters');
    }

    return traceId;
}

/**
 * Validates and normalizes file paths to prevent directory traversal
 */
export function validateFilePath(filePath: string, workspaceRoot: string): string {
    if (!filePath || typeof filePath !== 'string') {
        throw new Error('Invalid file path: must be a non-empty string');
    }

    // Resolve the absolute path
    const absolutePath = path.resolve(workspaceRoot, filePath);
    const normalizedWorkspace = path.resolve(workspaceRoot);

    // Ensure the resolved path is within the workspace
    if (!absolutePath.startsWith(normalizedWorkspace)) {
        throw new Error('File path is outside workspace boundaries');
    }

    // Check for null bytes
    if (absolutePath.includes('\0')) {
        throw new Error('File path contains null bytes');
    }

    return absolutePath;
}

/**
 * Validates backend option
 * Canonical set: stub | local | gateway
 */
export function validateBackend(backend: string): string {
    const allowedBackends = ['stub', 'local', 'gateway'];
    
    if (!backend || typeof backend !== 'string') {
        throw new Error('Invalid backend: must be a non-empty string');
    }

    if (!allowedBackends.includes(backend.toLowerCase())) {
        throw new Error(`Invalid backend: must be one of ${allowedBackends.join(', ')}`);
    }

    return backend.toLowerCase();
}

/**
 * Sanitizes error messages to prevent information leakage
 */
export function sanitizeErrorMessage(error: any): string {
    // Don't expose internal error details, stack traces, or file paths
    if (error instanceof Error) {
        // Map specific errors to safe messages
        if (error.message.includes('ENOENT')) {
            return 'Resource not found';
        }
        if (error.message.includes('EACCES') || error.message.includes('EPERM')) {
            return 'Permission denied';
        }
        if (error.message.includes('timeout') || error.message.includes('ETIMEDOUT')) {
            return 'Operation timed out';
        }
        if (error.message.includes('spawn') || error.message.includes('ENOEXEC')) {
            return 'Failed to execute command';
        }
        
        // For validation errors, we can expose the message as it's user-facing
        if (error.message.includes('Invalid') || error.message.includes('exceeds maximum')) {
            return error.message;
        }
    }

    // Generic error message for everything else
    return 'An error occurred while processing your request';
}

/**
 * Validates run ID to prevent path traversal attacks
 * Supports standard run ID format: run_<prefix>_<hash>
 */
export function validateRunId(runId: string): string {
    if (!runId || typeof runId !== 'string') {
        throw new Error('Invalid run ID: must be a non-empty string');
    }

    const runIdPattern = /^run[-_][a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*$/;
    if (!runIdPattern.test(runId)) {
        throw new Error('Invalid run ID format');
    }

    if (runId.includes('..') || runId.includes('/') || runId.includes('\\')) {
        throw new Error('Run ID contains invalid path characters');
    }

    return runId;
}

/**
 * Validates workspace root directory
 */
export function validateWorkspaceRoot(workspaceRoot: string): string {
    if (!workspaceRoot || typeof workspaceRoot !== 'string') {
        throw new Error('Invalid workspace root');
    }

    const normalized = path.resolve(workspaceRoot);
    
    // Ensure it's an absolute path
    if (!path.isAbsolute(normalized)) {
        throw new Error('Workspace root must be an absolute path');
    }

    return normalized;
}
