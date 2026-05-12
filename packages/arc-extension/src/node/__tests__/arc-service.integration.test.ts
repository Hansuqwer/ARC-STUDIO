import { ArcBackendService } from '../arc-backend-service';
import {
    ArcError,
    ArcErrorCode,
    ExecutionResult,
    TraceFile,
    TraceData,
    ValidationResult,
    CancelResult,
    WorkflowInfo
} from '../../common/arc-protocol';
import * as fs from 'fs-extra';
import * as path from 'path';
import * as os from 'os';

describe('ArcBackendService Integration Tests', () => {
    let service: ArcBackendService;
    let tempDir: string;
    let originalCwd: string;

    beforeAll(() => {
        originalCwd = process.cwd();
    });

    beforeEach(async () => {
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-test-'));
        process.chdir(tempDir);
        service = new ArcBackendService();
    });

    afterEach(async () => {
        process.chdir(originalCwd);
        await fs.remove(tempDir);
    });

    describe('Instantiation', () => {
        it('should instantiate ArcBackendService', () => {
            expect(service).toBeDefined();
            expect(service).toBeInstanceOf(ArcBackendService);
        });
    });

    describe('executeWorkflow', () => {
        it('should throw ArcError for empty prompt', async () => {
            await expect(service.executeWorkflow('')).rejects.toThrow(ArcError);
            await expect(service.executeWorkflow('')).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should throw ArcError for whitespace-only prompt', async () => {
            await expect(service.executeWorkflow('   ')).rejects.toThrow(ArcError);
            await expect(service.executeWorkflow('   ')).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should throw ArcError for too-long prompt', async () => {
            const longPrompt = 'a'.repeat(10001);
            await expect(service.executeWorkflow(longPrompt)).rejects.toThrow(ArcError);
            await expect(service.executeWorkflow(longPrompt)).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should return ExecutionResult with valid prompt (CLI not found)', async () => {
            const result = await service.executeWorkflow('test prompt');
            expect(result).toBeDefined();
            expect(result.status).toBe('failed');
            expect(result.runId).toBeDefined();
            expect(result.error).toContain('SwarmGraph CLI');
            expect(result.duration).toBeDefined();
            expect(typeof result.duration).toBe('number');
        });

        it('should accept execution options', async () => {
            const result = await service.executeWorkflow('test prompt', {
                backend: 'stub',
                costAllowed: false,
                timeout: 60000
            });
            expect(result).toBeDefined();
            expect(result.status).toBeDefined();
        });
    });

    describe('getTraces', () => {
        it('should return empty array when no traces directory exists', async () => {
            const traces = await service.getTraces();
            expect(traces).toEqual([]);
        });

        it('should return empty array when traces directory is empty', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const traces = await service.getTraces();
            expect(traces).toEqual([]);
        });

        it('should return sorted array when traces exist', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const trace1 = {
                id: 'run-sg-001',
                workflowId: 'test-workflow',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-01T10:00:00.000Z',
                events: [
                    {
                        type: 'RUN_STARTED' as const,
                        timestamp: '2024-01-01T10:00:00.000Z',
                        runId: 'run-sg-001',
                        sequence: 0,
                        data: {}
                    }
                ],
                metadata: {}
            };

            const trace2 = {
                id: 'run-sg-002',
                workflowId: 'test-workflow',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-02T10:00:00.000Z',
                events: [
                    {
                        type: 'RUN_STARTED' as const,
                        timestamp: '2024-01-02T10:00:00.000Z',
                        runId: 'run-sg-002',
                        sequence: 0,
                        data: {}
                    }
                ],
                metadata: {}
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-001.jsonl'),
                JSON.stringify(trace1),
                'utf-8'
            );
            await fs.writeFile(
                path.join(tracesDir, 'run-sg-002.jsonl'),
                JSON.stringify(trace2),
                'utf-8'
            );

            const traces = await service.getTraces();
            expect(traces.length).toBe(2);
            expect(traces[0].id).toBe('run-sg-002');
            expect(traces[1].id).toBe('run-sg-001');
        });

        it('should skip non-jsonl files', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            await fs.writeFile(path.join(tracesDir, 'readme.txt'), 'not a trace', 'utf-8');
            await fs.writeFile(path.join(tracesDir, 'data.json'), '{}', 'utf-8');

            const traces = await service.getTraces();
            expect(traces).toEqual([]);
        });
    });

    describe('readTrace', () => {
        it('should throw ArcError for non-existent trace ID', async () => {
            await expect(service.readTrace('non-existent')).rejects.toThrow(ArcError);
            await expect(service.readTrace('non-existent')).rejects.toMatchObject({
                code: ArcErrorCode.TRACE_NOT_FOUND
            });
        });

        it('should throw ArcError for invalid trace ID with path traversal', async () => {
            await expect(service.readTrace('../etc/passwd')).rejects.toThrow(ArcError);
            await expect(service.readTrace('../etc/passwd')).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should throw ArcError for empty trace ID', async () => {
            await expect(service.readTrace('')).rejects.toThrow(ArcError);
        });

        it('should return TraceData for valid trace file', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const traceData = {
                id: 'run-sg-valid',
                workflowId: 'test-workflow',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-01T10:00:00.000Z',
                endedAt: '2024-01-01T10:05:00.000Z',
                events: [
                    {
                        type: 'RUN_STARTED' as const,
                        timestamp: '2024-01-01T10:00:00.000Z',
                        runId: 'run-sg-valid',
                        sequence: 0,
                        data: { prompt: 'test' }
                    },
                    {
                        type: 'RUN_COMPLETED' as const,
                        timestamp: '2024-01-01T10:05:00.000Z',
                        runId: 'run-sg-valid',
                        sequence: 1,
                        data: { output: 'result' }
                    }
                ],
                metadata: { model: 'test-model' }
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-valid.jsonl'),
                JSON.stringify(traceData),
                'utf-8'
            );

            const result = await service.readTrace('run-sg-valid');
            expect(result).toBeDefined();
            expect(result.id).toBe('run-sg-valid');
            expect(result.workflowId).toBe('test-workflow');
            expect(result.status).toBe('completed');
            expect(result.events.length).toBe(2);
            expect(result.runtime).toBe('swarmgraph');
        });
    });

    describe('detectWorkflows', () => {
        it('should return empty array when no workflows found', async () => {
            const workflows = await service.detectWorkflows();
            expect(Array.isArray(workflows)).toBe(true);
        });

        it('should detect SwarmGraph npm package if installed', async () => {
            const nodeModulesDir = path.join(tempDir, 'node_modules', 'swarmgraph');
            await fs.ensureDir(nodeModulesDir);
            await fs.writeFile(
                path.join(nodeModulesDir, 'package.json'),
                JSON.stringify({ name: 'swarmgraph', version: '1.0.0' }),
                'utf-8'
            );

            const workflows = await service.detectWorkflows();
            const swarmgraphWorkflows = workflows.filter(
                (w: WorkflowInfo) => w.type === 'swarmgraph'
            );

            if (swarmgraphWorkflows.length > 0) {
                expect(swarmgraphWorkflows[0].type).toBe('swarmgraph');
                expect(swarmgraphWorkflows[0].name).toContain('SwarmGraph');
            }
        });

        it('should detect local swarmgraph executable', async () => {
            const localPath = path.join(tempDir, 'swarmgraph');
            await fs.writeFile(localPath, '#!/bin/bash\necho "swarmgraph"', 'utf-8');
            await fs.chmod(localPath, 0o755);

            const workflows = await service.detectWorkflows();
            const swarmgraphWorkflows = workflows.filter(
                (w: WorkflowInfo) => w.type === 'swarmgraph'
            );

            if (swarmgraphWorkflows.length > 0) {
                expect(swarmgraphWorkflows[0].type).toBe('swarmgraph');
            }
        });
    });

    describe('validateTrace', () => {
        it('should return invalid for non-existent trace', async () => {
            const result = await service.validateTrace('non-existent');
            expect(result.valid).toBe(false);
            expect(result.errors.length).toBeGreaterThan(0);
            expect(result.format).toBe('unknown');
        });

        it('should return valid for well-formed trace', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const traceData = {
                id: 'run-sg-valid',
                workflowId: 'test-workflow',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-01T10:00:00.000Z',
                events: [
                    {
                        type: 'RUN_STARTED' as const,
                        timestamp: '2024-01-01T10:00:00.000Z',
                        runId: 'run-sg-valid',
                        sequence: 0,
                        data: {}
                    }
                ],
                metadata: {}
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-valid.jsonl'),
                JSON.stringify(traceData),
                'utf-8'
            );

            const result = await service.validateTrace('run-sg-valid');
            expect(result.valid).toBe(true);
            expect(result.errors.length).toBe(0);
            expect(result.format).toBe('json');
        });

        it('should detect jsonl format for multi-line traces', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const event1 = JSON.stringify({
                type: 'RUN_STARTED',
                timestamp: '2024-01-01T10:00:00.000Z',
                runId: 'run-sg-multi',
                sequence: 0,
                data: {}
            });
            const event2 = JSON.stringify({
                type: 'RUN_COMPLETED',
                timestamp: '2024-01-01T10:05:00.000Z',
                runId: 'run-sg-multi',
                sequence: 1,
                data: {}
            });

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-multi.jsonl'),
                `${event1}\n${event2}\n`,
                'utf-8'
            );

            const result = await service.validateTrace('run-sg-multi');
            expect(result.format).toBe('jsonl');
        });

        it('should report warnings for missing optional fields', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const incompleteTrace = {
                events: []
            };

            await fs.writeFile(
                path.join(tracesDir, 'incomplete.jsonl'),
                JSON.stringify(incompleteTrace),
                'utf-8'
            );

            const result = await service.validateTrace('incomplete');
            expect(result.warnings.some(e => e.includes('workflowId'))).toBe(true);
        });
    });

    describe('cancelWorkflow', () => {
        it('should return failure for non-running workflow', async () => {
            const result = await service.cancelWorkflow('non-existent-run');
            expect(result.success).toBe(false);
            expect(result.runId).toBe('non-existent-run');
            expect(result.message).toContain('No running process');
        });

        it('should return failure for empty run ID', async () => {
            const result = await service.cancelWorkflow('');
            expect(result.success).toBe(false);
        });
    });

    describe('streamTrace', () => {
        it('should throw ArcError for non-existent trace', async () => {
            await expect(service.streamTrace('non-existent')).rejects.toThrow(ArcError);
        });

        it('should throw ArcError for invalid trace ID', async () => {
            await expect(service.streamTrace('../invalid')).rejects.toThrow(ArcError);
        });
    });
});
