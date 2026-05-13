/**
 * Backend Services Unit Tests
 *
 * Tests for the specialized backend service modules.
 */

import { WorkflowExecutor } from '../services/workflow-executor';
import { TraceParser } from '../services/trace-parser';
import { FileManager } from '../services/file-manager';
import { WorkflowDetector } from '../services/workflow-detector';
import { ArcError, ArcErrorCode } from '../../common/arc-protocol';
import * as fs from 'fs-extra';
import * as path from 'path';
import * as os from 'os';

describe('WorkflowExecutor', () => {
    let executor: WorkflowExecutor;

    beforeEach(() => {
        executor = new WorkflowExecutor();
    });

    describe('executeWorkflow validation', () => {
        it('should throw ArcError for empty prompt', async () => {
            await expect(executor.executeWorkflow('')).rejects.toThrow(ArcError);
            await expect(executor.executeWorkflow('')).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should throw ArcError for whitespace-only prompt', async () => {
            await expect(executor.executeWorkflow('   ')).rejects.toThrow(ArcError);
            await expect(executor.executeWorkflow('   ')).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should throw ArcError for overly long prompt', async () => {
            const longPrompt = 'a'.repeat(10001);
            await expect(executor.executeWorkflow(longPrompt)).rejects.toThrow(ArcError);
            await expect(executor.executeWorkflow(longPrompt)).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should throw ArcError for non-string prompt', async () => {
            await expect(executor.executeWorkflow(null as unknown as string)).rejects.toThrow(ArcError);
        });

        it('should return failed result when swarmgraph CLI is not found', async () => {
            const result = await executor.executeWorkflow('test prompt');
            expect(result.status).toBe('failed');
            expect(result.error).toContain('swarmgraph');
        });
    });

    describe('cancelWorkflow', () => {
        it('should return failure for unknown run ID', async () => {
            const result = await executor.cancelWorkflow('nonexistent-run-id');
            expect(result.success).toBe(false);
            expect(result.message).toContain('No running process');
        });
    });
});

describe('TraceParser', () => {
    let parser: TraceParser;
    let tempDir: string;

    beforeEach(async () => {
        parser = new TraceParser();
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-parse-test-'));
    });

    afterEach(async () => {
        await fs.remove(tempDir);
    });

    describe('parseJsonlContent', () => {
        it('should return null for empty content', () => {
            const result = parser.parseJsonlContent('');
            expect(result).toBeNull();
        });

        it('should return null for whitespace-only content', () => {
            const result = parser.parseJsonlContent('   \n  \n  ');
            expect(result).toBeNull();
        });

        it('should parse single JSON object', () => {
            const content = JSON.stringify({
                id: 'test-run',
                status: 'completed',
                events: [{ type: 'MESSAGE', timestamp: new Date().toISOString(), runId: 'test-run', sequence: 0, data: {} }]
            });
            const result = parser.parseJsonlContent(content);
            expect(result).not.toBeNull();
            expect(result!.id).toBe('test-run');
            expect(result!.status).toBe('completed');
        });

        it('should parse LangGraph-style JSONL (multi-line)', () => {
            const content = [
                JSON.stringify({ type: 'RUN_STARTED', timestamp: new Date().toISOString(), run_id: 'lg-run' }),
                JSON.stringify({ type: 'RUN_COMPLETED', timestamp: new Date().toISOString() }),
            ].join('\n');
            const result = parser.parseJsonlContent(content);
            expect(result).not.toBeNull();
            expect(result!.id).toBe('lg-run');
            expect(result!.events).toHaveLength(2);
            expect(result!.status).toBe('completed');
        });

        it('should handle malformed lines gracefully', () => {
            const content = [
                JSON.stringify({ type: 'EVENT', timestamp: new Date().toISOString() }),
                'not valid json',
                JSON.stringify({ type: 'RUN_COMPLETED', timestamp: new Date().toISOString() }),
            ].join('\n');
            const result = parser.parseJsonlContent(content);
            expect(result).not.toBeNull();
            expect(result!.events).toHaveLength(2);
        });

        it('should use fallbackId when no ID found', () => {
            const content = JSON.stringify({ status: 'completed' });
            const result = parser.parseJsonlContent(content, 'fallback-id');
            expect(result).not.toBeNull();
            expect(result!.id).toContain('fallback-id');
        });
    });

    describe('parseTrace', () => {
        it('should throw ArcError for missing file', async () => {
            await expect(parser.parseTrace(path.join(tempDir, 'nonexistent.jsonl')))
                .rejects.toThrow(ArcError);
        });
    });

    describe('normalizeStatus', () => {
        it('should normalize success variants', () => {
            expect(parser.normalizeStatus('completed')).toBe('completed');
            expect(parser.normalizeStatus('success')).toBe('completed');
            expect(parser.normalizeStatus('ok')).toBe('completed');
        });

        it('should normalize failure variants', () => {
            expect(parser.normalizeStatus('failed')).toBe('failed');
            expect(parser.normalizeStatus('error')).toBe('failed');
            expect(parser.normalizeStatus('failure')).toBe('failed');
        });

        it('should return unknown for unknown status', () => {
            expect(parser.normalizeStatus('running')).toBe('unknown');
            expect(parser.normalizeStatus('')).toBe('unknown');
            expect(parser.normalizeStatus(undefined as unknown as string)).toBe('unknown');
        });
    });

    describe('isValidEvent', () => {
        it('should validate proper event structure', () => {
            expect(parser.isValidEvent({ type: 'MESSAGE', timestamp: new Date().toISOString() })).toBe(true);
        });

        it('should reject invalid events', () => {
            expect(parser.isValidEvent(undefined)).toBeFalsy();
            expect(parser.isValidEvent({})).toBeFalsy();
            expect(parser.isValidEvent({ type: 'MESSAGE' })).toBeFalsy();
        });

        it('should treat null as falsy', () => {
            expect(parser.isValidEvent(null)).toBeFalsy();
        });
    });
});

describe('FileManager', () => {
    let fileManager: FileManager;
    let tempDir: string;

    beforeEach(async () => {
        fileManager = new FileManager();
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-fm-test-'));
    });

    afterEach(async () => {
        await fs.remove(tempDir);
    });

    describe('getTraceFiles', () => {
        it('should return empty array when traces directory does not exist', async () => {
            const result = await fileManager.getTraceFiles(tempDir);
            expect(result).toEqual([]);
        });

        it('should list trace files in .arc/traces', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);
            await fs.writeFile(
                path.join(tracesDir, 'run-1.jsonl'),
                JSON.stringify({ id: 'run-1', status: 'completed' })
            );
            const result = await fileManager.getTraceFiles(tempDir);
            expect(result).toHaveLength(1);
            expect(result[0].id).toBe('run-1');
        });

        it('should only include .jsonl files', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);
            await fs.writeFile(path.join(tracesDir, 'run-1.jsonl'), JSON.stringify({ id: 'run-1' }));
            await fs.writeFile(path.join(tracesDir, 'readme.txt'), 'not a trace');
            const result = await fileManager.getTraceFiles(tempDir);
            expect(result).toHaveLength(1);
        });
    });

    describe('getTracePath', () => {
        it('should return correct path for trace ID', () => {
            const result = fileManager.getTracePath(tempDir, 'run-sg-abc123');
            expect(result).toContain('.arc/traces/run-sg-abc123.jsonl');
        });

        it('should throw on invalid trace ID', () => {
            expect(() => fileManager.getTracePath(tempDir, '../evil')).toThrow();
        });
    });

    describe('ensureTracesDir', () => {
        it('should create traces directory', async () => {
            await fileManager.ensureTracesDir(tempDir);
            const exists = await fs.pathExists(path.join(tempDir, '.arc', 'traces'));
            expect(exists).toBe(true);
        });
    });
});

describe('WorkflowDetector', () => {
    let detector: WorkflowDetector;
    let tempDir: string;

    beforeEach(async () => {
        detector = new WorkflowDetector();
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-wd-test-'));
    });

    afterEach(async () => {
        await fs.remove(tempDir);
    });

    describe('detectWorkflows', () => {
        it('should return empty array for empty workspace', async () => {
            const result = await detector.detectWorkflows(tempDir);
            expect(Array.isArray(result)).toBe(true);
        });

        it('should detect local swarmgraph executable', async () => {
            const swarmgraphPath = path.join(tempDir, 'swarmgraph');
            await fs.writeFile(swarmgraphPath, '#!/bin/bash\necho "swarmgraph"');
            await fs.chmod(swarmgraphPath, 0o755);
            const result = await detector.detectWorkflows(tempDir);
            expect(result.length).toBeGreaterThanOrEqual(1);
            expect(result.some(w => w.type === 'swarmgraph')).toBe(true);
        });

        it('should detect LangGraph Python files', async () => {
            const pyDir = path.join(tempDir, 'workflows');
            await fs.ensureDir(pyDir);
            await fs.writeFile(
                path.join(pyDir, 'agent.py'),
                'from langgraph.graph import StateGraph\n' +
                'graph = StateGraph(state_schema)\n' +
                'graph.compile()\n'
            );
            const result = await detector.detectWorkflows(tempDir);
            expect(result.length).toBeGreaterThanOrEqual(1);
            expect(result.some(w => w.type === 'langgraph')).toBe(true);
        });

        it('should skip Python files without langgraph', async () => {
            await fs.writeFile(path.join(tempDir, 'hello.py'), 'print("hello")');
            const result = await detector.detectWorkflows(tempDir);
            expect(result.every(w => w.type !== 'langgraph')).toBe(true);
        });
    });
});
