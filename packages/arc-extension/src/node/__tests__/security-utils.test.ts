import {
    sanitizePrompt,
    validateTraceId,
    validateFilePath,
    validateBackend,
    sanitizeErrorMessage,
    validateWorkspaceRoot
} from '../security-utils';
import * as path from 'path';
import * as os from 'os';
import * as fs from 'fs-extra';

describe('security-utils', () => {
    describe('sanitizePrompt', () => {
        it('should throw on empty string', () => {
            expect(() => sanitizePrompt('')).toThrow('Invalid prompt: must be a non-empty string');
        });

        it('should throw on non-string input', () => {
            expect(() => sanitizePrompt(123 as any)).toThrow('Invalid prompt: must be a non-empty string');
            expect(() => sanitizePrompt(null as any)).toThrow('Invalid prompt: must be a non-empty string');
            expect(() => sanitizePrompt(undefined as any)).toThrow('Invalid prompt: must be a non-empty string');
        });

        it('should throw on prompt exceeding max length', () => {
            const longPrompt = 'a'.repeat(10001);
            expect(() => sanitizePrompt(longPrompt)).toThrow('Prompt exceeds maximum length of 10000 characters');
        });

        it('should remove control characters', () => {
            const promptWithControl = 'hello\x00\x01\x02world';
            const result = sanitizePrompt(promptWithControl);
            expect(result).toBe('helloworld');
            expect(result).not.toContain('\x00');
        });

        it('should throw on shell metacharacters', () => {
            expect(() => sanitizePrompt('hello; world')).toThrow('Prompt contains potentially dangerous characters');
            expect(() => sanitizePrompt('hello | world')).toThrow('Prompt contains potentially dangerous characters');
            expect(() => sanitizePrompt('hello & world')).toThrow('Prompt contains potentially dangerous characters');
            expect(() => sanitizePrompt('hello `world`')).toThrow('Prompt contains potentially dangerous characters');
            expect(() => sanitizePrompt('hello $(world)')).toThrow('Prompt contains potentially dangerous characters');
            expect(() => sanitizePrompt('hello < world')).toThrow('Prompt contains potentially dangerous characters');
            expect(() => sanitizePrompt('hello > world')).toThrow('Prompt contains potentially dangerous characters');
        });

        it('should return trimmed safe prompt', () => {
            expect(sanitizePrompt('  hello world  ')).toBe('hello world');
            expect(sanitizePrompt('run a workflow')).toBe('run a workflow');
            expect(sanitizePrompt('What is the weather today?')).toBe('What is the weather today?');
        });

        it('should accept prompt at exactly max length', () => {
            const maxPrompt = 'a'.repeat(10000);
            const result = sanitizePrompt(maxPrompt);
            expect(result).toBe(maxPrompt);
        });
    });

    describe('validateTraceId', () => {
        it('should throw on empty string', () => {
            expect(() => validateTraceId('')).toThrow('Invalid trace ID: must be a non-empty string');
        });

        it('should accept valid sg trace ID', () => {
            expect(validateTraceId('run-sg-abc123')).toBe('run-sg-abc123');
            expect(validateTraceId('run-sg-deadbeef')).toBe('run-sg-deadbeef');
        });

        it('should accept valid lg trace ID', () => {
            expect(validateTraceId('run-lg-abc123')).toBe('run-lg-abc123');
        });

        it('should accept valid ca trace ID', () => {
            expect(validateTraceId('run-ca-abc123')).toBe('run-ca-abc123');
        });

        it('should accept valid openai trace ID', () => {
            expect(validateTraceId('run-openai-abc123')).toBe('run-openai-abc123');
        });

        it('should throw on invalid formats', () => {
            expect(() => validateTraceId('invalid-id')).toThrow('Invalid trace ID format');
            expect(() => validateTraceId('run-unknown-abc123')).toThrow('Invalid trace ID format');
            expect(() => validateTraceId('run-sg-ABC123')).toThrow('Invalid trace ID format');
            expect(() => validateTraceId('run-sg-')).toThrow('Invalid trace ID format');
            expect(() => validateTraceId(123 as any)).toThrow('Invalid trace ID: must be a non-empty string');
        });

        it('should throw on path traversal attempts', () => {
            expect(() => validateTraceId('run-sg-abc/../etc')).toThrow('Invalid trace ID format');
            expect(() => validateTraceId('run-sg-abc/def')).toThrow('Invalid trace ID format');
            expect(() => validateTraceId('run-sg-abc\\def')).toThrow('Invalid trace ID format');
        });
    });

    describe('validateFilePath', () => {
        let tempDir: string;

        beforeEach(async () => {
            tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-fp-test-'));
        });

        afterEach(async () => {
            await fs.remove(tempDir);
        });

        it('should throw on empty path', () => {
            expect(() => validateFilePath('', '/workspace')).toThrow('Invalid file path: must be a non-empty string');
            expect(() => validateFilePath(null as any, '/workspace')).toThrow('Invalid file path: must be a non-empty string');
        });

        it('should return resolved path for valid file within workspace', () => {
            const result = validateFilePath('file.txt', tempDir);
            expect(result).toBe(path.join(tempDir, 'file.txt'));
        });

        it('should throw on path outside workspace', () => {
            expect(() => validateFilePath('../etc/passwd', tempDir)).toThrow('File path is outside workspace boundaries');
            expect(() => validateFilePath('../../outside', tempDir)).toThrow('File path is outside workspace boundaries');
        });

        it('should throw on null bytes in path', () => {
            expect(() => validateFilePath('file\x00.txt', tempDir)).toThrow('File path contains null bytes');
        });
    });

    describe('validateBackend', () => {
        it('should accept valid backends', () => {
            expect(validateBackend('stub')).toBe('stub');
            expect(validateBackend('local')).toBe('local');
            expect(validateBackend('gateway')).toBe('gateway');
        });

        it('should normalize to lowercase', () => {
            expect(validateBackend('STUB')).toBe('stub');
            expect(validateBackend('Gateway')).toBe('gateway');
            expect(validateBackend('LOCAL')).toBe('local');
        });

        it('should throw on invalid backend', () => {
            expect(() => validateBackend('invalid')).toThrow('Invalid backend: must be one of stub, local, gateway');
            expect(() => validateBackend('unknown')).toThrow('Invalid backend: must be one of stub, local, gateway');
        });

        it('should throw on empty or non-string', () => {
            expect(() => validateBackend('')).toThrow('Invalid backend: must be a non-empty string');
            expect(() => validateBackend(null as any)).toThrow('Invalid backend: must be a non-empty string');
            expect(() => validateBackend(undefined as any)).toThrow('Invalid backend: must be a non-empty string');
        });
    });

    describe('sanitizeErrorMessage', () => {
        it('should return "Resource not found" for ENOENT errors', () => {
            const error = new Error('ENOENT: no such file or directory');
            expect(sanitizeErrorMessage(error)).toBe('Resource not found');
        });

        it('should return "Permission denied" for EACCES errors', () => {
            const error = new Error('EACCES: permission denied');
            expect(sanitizeErrorMessage(error)).toBe('Permission denied');
        });

        it('should return "Operation timed out" for timeout errors', () => {
            const error = new Error('operation timeout after 5000ms');
            expect(sanitizeErrorMessage(error)).toBe('Operation timed out');
            const error2 = new Error('ETIMEDOUT');
            expect(sanitizeErrorMessage(error2)).toBe('Operation timed out');
        });

        it('should return "Failed to execute command" for spawn errors', () => {
            const error = new Error('spawn EAGAIN');
            expect(sanitizeErrorMessage(error)).toBe('Failed to execute command');
            const error2 = new Error('ENOEXEC: exec format error');
            expect(sanitizeErrorMessage(error2)).toBe('Failed to execute command');
        });

        it('should return validation error messages as-is', () => {
            const error = new Error('Invalid prompt: must be a non-empty string');
            expect(sanitizeErrorMessage(error)).toBe('Invalid prompt: must be a non-empty string');
            const error2 = new Error('Prompt exceeds maximum length of 10000 characters');
            expect(sanitizeErrorMessage(error2)).toBe('Prompt exceeds maximum length of 10000 characters');
        });

        it('should return generic message for unknown errors', () => {
            const error = new Error('Some random unexpected error');
            expect(sanitizeErrorMessage(error)).toBe('An error occurred while processing your request');
            expect(sanitizeErrorMessage('not an error' as any)).toBe('An error occurred while processing your request');
            expect(sanitizeErrorMessage(null as any)).toBe('An error occurred while processing your request');
        });
    });

    describe('validateWorkspaceRoot', () => {
        it('should throw on empty or non-string', () => {
            expect(() => validateWorkspaceRoot('')).toThrow('Invalid workspace root');
            expect(() => validateWorkspaceRoot(null as any)).toThrow('Invalid workspace root');
            expect(() => validateWorkspaceRoot(undefined as any)).toThrow('Invalid workspace root');
        });

        it('should return normalized absolute path for valid workspace', () => {
            const result = validateWorkspaceRoot('/tmp');
            expect(result).toBe('/tmp');
            expect(path.isAbsolute(result)).toBe(true);
        });
    });
});
