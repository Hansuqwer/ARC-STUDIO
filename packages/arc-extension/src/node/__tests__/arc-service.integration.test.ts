import { ArcBackendService } from '../arc-backend-service';
import {
    ArcError,
    ArcErrorCode,
    ExecutionResult,
    TraceFile,
    TraceData,
    ValidationResult,
    CancelResult,
    WorkflowInfo,
    RunReceipt,
    FailureAutopsy,
    RunContract,
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
            await expect(service.readTrace('run-sg-ff00')).rejects.toThrow(ArcError);
            await expect(service.readTrace('run-sg-ff00')).rejects.toMatchObject({
                code: ArcErrorCode.TRACE_NOT_FOUND
            });
        });

        it('should throw ArcError for invalid trace ID with path traversal', async () => {
            await expect(service.readTrace('../etc/passwd')).rejects.toThrow(ArcError);
        });

        it('should throw ArcError for empty trace ID', async () => {
            await expect(service.readTrace('')).rejects.toThrow(ArcError);
        });

        it('should return TraceData for valid trace file', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const traceData = {
                id: 'run-sg-ab08',
                workflowId: 'test-workflow',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-01T10:00:00.000Z',
                endedAt: '2024-01-01T10:05:00.000Z',
                events: [
                    {
                        type: 'RUN_STARTED' as const,
                        timestamp: '2024-01-01T10:00:00.000Z',
                        runId: 'run-sg-ab08',
                        sequence: 0,
                        data: { prompt: 'test' }
                    },
                    {
                        type: 'RUN_COMPLETED' as const,
                        timestamp: '2024-01-01T10:05:00.000Z',
                        runId: 'run-sg-ab08',
                        sequence: 1,
                        data: { output: 'result' }
                    }
                ],
                metadata: { model: 'test-model' }
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-ab08.jsonl'),
                JSON.stringify(traceData),
                'utf-8'
            );

            const result = await service.readTrace('run-sg-ab08');
            expect(result).toBeDefined();
            expect(result.id).toBe('run-sg-ab08');
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
                id: 'run-sg-ab06',
                workflowId: 'test-workflow',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-01T10:00:00.000Z',
                events: [
                    {
                        type: 'RUN_STARTED' as const,
                        timestamp: '2024-01-01T10:00:00.000Z',
                        runId: 'run-sg-ab06',
                        sequence: 0,
                        data: {}
                    }
                ],
                metadata: {}
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-ab06.jsonl'),
                JSON.stringify(traceData),
                'utf-8'
            );

            const result = await service.validateTrace('run-sg-ab06');
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
                runId: 'run-sg-ab07',
                sequence: 0,
                data: {}
            });
            const event2 = JSON.stringify({
                type: 'RUN_COMPLETED',
                timestamp: '2024-01-01T10:05:00.000Z',
                runId: 'run-sg-ab07',
                sequence: 1,
                data: {}
            });

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-ab07.jsonl'),
                `${event1}\n${event2}\n`,
                'utf-8'
            );

            const result = await service.validateTrace('run-sg-ab07');
            expect(result.format).toBe('jsonl');
        });

        it('should report warnings for missing optional fields', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const incompleteTrace = {
                events: []
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa00.jsonl'),
                JSON.stringify(incompleteTrace),
                'utf-8'
            );

            const result = await service.validateTrace('run-sg-aa00');
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
            await expect(service.streamTrace('run-sg-ff01')).rejects.toThrow(ArcError);
        });

        it('should throw ArcError for invalid trace ID', async () => {
            await expect(service.streamTrace('../invalid')).rejects.toThrow(Error);
        });

        it('should return async iterable for valid trace', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const event1 = JSON.stringify({
                type: 'RUN_STARTED',
                timestamp: '2024-01-01T10:00:00.000Z',
                runId: 'run-sg-abcd',
                sequence: 0,
                data: { prompt: 'test' }
            });
            const event2 = JSON.stringify({
                type: 'RUN_COMPLETED',
                timestamp: '2024-01-01T10:05:00.000Z',
                runId: 'run-sg-abcd',
                sequence: 1,
                data: { output: 'result' }
            });

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-abcd.jsonl'),
                `${event1}\n${event2}\n`,
                'utf-8'
            );

            const iterable = await service.streamTrace('run-sg-abcd');
            const events: any[] = [];
            for await (const event of iterable) {
                events.push(event);
            }
            expect(events.length).toBe(2);
            expect(events[0].type).toBe('RUN_STARTED');
            expect(events[1].type).toBe('RUN_COMPLETED');
        });

        it('should handle empty trace file', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa99.jsonl'),
                '',
                'utf-8'
            );

            const iterable = await service.streamTrace('run-sg-aa99');
            const events: any[] = [];
            for await (const event of iterable) {
                events.push(event);
            }
            expect(events.length).toBe(0);
        });

        it('should skip malformed lines in stream', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const content = [
                JSON.stringify({ type: 'RUN_STARTED', timestamp: '2024-01-01T10:00:00.000Z', runId: 'run-sg-aa88', sequence: 0, data: {} }),
                'this is not valid json',
                JSON.stringify({ type: 'RUN_COMPLETED', timestamp: '2024-01-01T10:05:00.000Z', runId: 'run-sg-aa88', sequence: 1, data: {} }),
            ].join('\n');

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa88.jsonl'),
                content,
                'utf-8'
            );

            const iterable = await service.streamTrace('run-sg-aa88');
            const events: any[] = [];
            for await (const event of iterable) {
                events.push(event);
            }
            expect(events.length).toBe(2);
        });
    });

    describe('streamActiveTrace', () => {
        it('should stream replay chunks with explicit terminal end', async () => {
            jest.spyOn(service, 'replayRun').mockResolvedValue({
                runId: 'run-sg-ac01',
                events: [
                    {
                        type: 'RUN_STARTED',
                        timestamp: '2024-01-01T10:00:00.000Z',
                        runId: 'run-sg-ac01',
                        sequence: 0,
                        data: {}
                    },
                    {
                        type: 'RUN_COMPLETED',
                        timestamp: '2024-01-01T10:00:01.000Z',
                        runId: 'run-sg-ac01',
                        sequence: 1,
                        data: {}
                    }
                ],
                totalEvents: 2
            });

            const iterable = await service.streamActiveTrace({ runId: 'run-sg-ac01', mode: 'replay' });
            const chunks: any[] = [];
            for await (const chunk of iterable) {
                chunks.push(chunk);
            }

            expect(chunks[0].status.state).toBe('replaying');
            expect(chunks[1].event.type).toBe('RUN_STARTED');
            expect(chunks[2].terminal).toBe('RUN_COMPLETED');
            expect(chunks[3].terminal).toBe('STREAM_END');
            expect(chunks[3].done).toBe(true);
        });

        it('should expose live disconnected terminal without provider calls', async () => {
            const replaySpy = jest.spyOn(service, 'replayRun');

            const iterable = await service.streamActiveTrace({ runId: 'run-sg-ac02', mode: 'live' });
            const chunks: any[] = [];
            for await (const chunk of iterable) {
                chunks.push(chunk);
            }

            expect(replaySpy).not.toHaveBeenCalled();
            expect(chunks[0].status.state).toBe('connecting');
            expect(chunks[1].status.state).toBe('disconnected');
            expect(chunks[1].terminal).toBe('STREAM_END');
            expect(chunks[1].done).toBe(true);
        });

        it('should cancel an active stream proxy before replay emits events', async () => {
            jest.spyOn(service, 'replayRun').mockResolvedValue({
                runId: 'run-sg-ac03',
                events: [],
                totalEvents: 0
            });

            const iterable = await service.streamActiveTrace({ runId: 'run-sg-ac03', mode: 'replay' });
            const cancelResult = await service.cancelActiveTraceStream('run-sg-ac03');
            const chunks: any[] = [];
            for await (const chunk of iterable) {
                chunks.push(chunk);
            }

            expect(cancelResult.success).toBe(true);
            expect(chunks[0].status.state).toBe('replaying');
            expect(chunks[1].terminal).toBe('RUN_CANCELLED');
            expect(chunks[1].status.state).toBe('cancelled');
        });

        it('should reject invalid active stream run IDs and modes', async () => {
            await expect(service.streamActiveTrace({ runId: '../bad', mode: 'replay' })).rejects.toThrow(Error);
            await expect(service.streamActiveTrace({ runId: 'run-sg-ac04', mode: 'bad' as any })).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });
    });

    describe('parseJsonlTrace (via readTrace)', () => {
        it('should parse single-line JSON trace', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const traceData = {
                id: 'run-sg-ab01',
                workflowId: 'test',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-01T10:00:00.000Z',
                events: [{ type: 'RUN_STARTED', timestamp: '2024-01-01T10:00:00.000Z', runId: 'run-sg-ab01', sequence: 0, data: {} }],
                metadata: {}
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-ab01.jsonl'),
                JSON.stringify(traceData),
                'utf-8'
            );

            const result = await service.readTrace('run-sg-ab01');
            expect(result.id).toBe('run-sg-ab01');
            expect(result.events.length).toBe(1);
        });

        it('should parse multi-line JSONL trace', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const event1 = JSON.stringify({ type: 'RUN_STARTED', timestamp: '2024-01-01T10:00:00.000Z', runId: 'run-sg-ab02', sequence: 0, data: {} });
            const event2 = JSON.stringify({ type: 'RUN_COMPLETED', timestamp: '2024-01-01T10:05:00.000Z', runId: 'run-sg-ab02', sequence: 1, data: {} });

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-ab02.jsonl'),
                `${event1}\n${event2}\n`,
                'utf-8'
            );

            const result = await service.readTrace('run-sg-ab02');
            expect(result.events.length).toBe(2);
            expect(result.runtime).toBe('langgraph');
        });

        it('should handle malformed lines gracefully', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const content = [
                JSON.stringify({ type: 'RUN_STARTED', timestamp: '2024-01-01T10:00:00.000Z', runId: 'run-sg-ab03', sequence: 0, data: {} }),
                'not json at all',
                JSON.stringify({ type: 'RUN_COMPLETED', timestamp: '2024-01-01T10:05:00.000Z', runId: 'run-sg-ab03', sequence: 1, data: {} }),
            ].join('\n');

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-ab03.jsonl'),
                content,
                'utf-8'
            );

            const result = await service.readTrace('run-sg-ab03');
            expect(result.events.length).toBe(2);
        });

        it('should normalize snake_case fields', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const snakeCaseTrace = {
                id: 'run-sg-ab04',
                workflow_id: 'my-workflow',
                runtime: 'swarmgraph',
                status: 'completed',
                started_at: '2024-01-01T10:00:00.000Z',
                ended_at: '2024-01-01T10:05:00.000Z',
                events: [
                    { type: 'RUN_STARTED', timestamp: '2024-01-01T10:00:00.000Z', run_id: 'run-sg-ab04', sequence: 0, data: {} }
                ],
                metadata: {}
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-ab04.jsonl'),
                JSON.stringify(snakeCaseTrace),
                'utf-8'
            );

            const result = await service.readTrace('run-sg-ab04');
            expect(result.workflowId).toBe('my-workflow');
            expect(result.startedAt).toBe('2024-01-01T10:00:00.000Z');
            expect(result.endedAt).toBe('2024-01-01T10:05:00.000Z');
            expect(result.events[0].runId).toBe('run-sg-ab04');
        });

        it('should return error for empty trace content', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-ab05.jsonl'),
                '',
                'utf-8'
            );

            await expect(service.readTrace('run-sg-ab05')).rejects.toThrow(ArcError);
        });
    });

    describe('detectWorkflows - LangGraph', () => {
        it('should detect LangGraph Python files with StateGraph', async () => {
            const pyDir = path.join(tempDir, 'workflows');
            await fs.ensureDir(pyDir);

            const pyContent = `
from langgraph.graph import StateGraph

workflow = StateGraph()
compiled = workflow.compile()
`;
            await fs.writeFile(path.join(pyDir, 'my_workflow.py'), pyContent, 'utf-8');

            const workflows = await service.detectWorkflows();
            const langgraphWorkflows = workflows.filter((w: WorkflowInfo) => w.type === 'langgraph');

            expect(langgraphWorkflows.length).toBeGreaterThan(0);
            expect(langgraphWorkflows[0].name).toBe('workflow');
            expect(langgraphWorkflows[0].description).toContain('LangGraph StateGraph workflow');
        });

        it('should ignore LangGraph files in excluded directories', async () => {
            const excludedDirs = ['node_modules', '.git', '__pycache__', '.venv', 'venv', '.arc', 'docs', 'scripts'];

            for (const dir of excludedDirs) {
                const pyDir = path.join(tempDir, dir);
                await fs.ensureDir(pyDir);
                await fs.writeFile(
                    path.join(pyDir, 'workflow.py'),
                    'from langgraph.graph import StateGraph\nworkflow = StateGraph()',
                    'utf-8'
                );
            }

            const workflows = await service.detectWorkflows();
            const langgraphWorkflows = workflows.filter((w: WorkflowInfo) => w.type === 'langgraph');
            expect(langgraphWorkflows.length).toBe(0);
        });

        it('should detect LangGraph workflow with persistence', async () => {
            const pyDir = path.join(tempDir, 'agents');
            await fs.ensureDir(pyDir);

            const pyContent = `
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

builder = StateGraph()
graph = builder.compile(checkpointer=MemorySaver())
`;
            await fs.writeFile(path.join(pyDir, 'persistent_agent.py'), pyContent, 'utf-8');

            const workflows = await service.detectWorkflows();
            const langgraphWorkflows = workflows.filter((w: WorkflowInfo) => w.type === 'langgraph');

            expect(langgraphWorkflows.length).toBeGreaterThan(0);
            expect(langgraphWorkflows[0].description).toContain('persistence');
        });

        it('should skip Python files without langgraph import', async () => {
            const pyDir = path.join(tempDir, 'scripts');
            await fs.ensureDir(pyDir);

            await fs.writeFile(
                path.join(pyDir, 'utils.py'),
                'import os\nprint("hello")',
                'utf-8'
            );

            const workflows = await service.detectWorkflows();
            const langgraphWorkflows = workflows.filter((w: WorkflowInfo) => w.type === 'langgraph');
            expect(langgraphWorkflows.length).toBe(0);
        });
    });

    describe('validateTrace - additional coverage', () => {
        it('should validate trace with normalized defaults', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const minimalTrace = {
                events: [
                    { data: {} }
                ]
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa11.jsonl'),
                JSON.stringify(minimalTrace),
                'utf-8'
            );

            const result = await service.validateTrace('run-sg-aa11');
            expect(result).toBeDefined();
            expect(result.format).toBe('json');
        });

        it('should validate trace with events having normalized defaults', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const traceWithBadEvents = {
                id: 'run-sg-bad0',
                workflowId: 'test',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-01T10:00:00.000Z',
                events: [
                    { sequence: 0, data: {} },
                    { type: 'RUN_COMPLETED', runId: 'run-sg-bad0', sequence: 1, data: {} }
                ],
                metadata: {}
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-bad0.jsonl'),
                JSON.stringify(traceWithBadEvents),
                'utf-8'
            );

            const result = await service.validateTrace('run-sg-bad0');
            expect(result).toBeDefined();
            expect(result.valid).toBe(true);
        });

        it('should validate trace with events missing sequence', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const traceWithNoSeq = {
                id: 'run-sg-aa22',
                workflowId: 'test',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-01T10:00:00.000Z',
                events: [
                    { type: 'RUN_STARTED', timestamp: '2024-01-01T10:00:00.000Z', runId: 'run-sg-aa22', data: {} }
                ],
                metadata: {}
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa22.jsonl'),
                JSON.stringify(traceWithNoSeq),
                'utf-8'
            );

            const result = await service.validateTrace('run-sg-aa22');
            expect(result).toBeDefined();
            expect(result.valid).toBe(true);
        });

        it('should handle invalid JSON content', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa33.jsonl'),
                'this is not json at all',
                'utf-8'
            );

            const result = await service.validateTrace('run-sg-aa33');
            expect(result.valid).toBe(false);
            expect(result.errors.length).toBeGreaterThan(0);
        });

        it('should handle invalid trace ID format', async () => {
            const result = await service.validateTrace('invalid-id-format');
            expect(result.valid).toBe(false);
            expect(result.errors.length).toBeGreaterThan(0);
        });
    });

    describe('cancelWorkflow - additional coverage', () => {
        it('should handle cancellation of killed process', async () => {
            const result = await service.cancelWorkflow('run-sg-nonexistent');
            expect(result.success).toBe(false);
            expect(result.message).toContain('No running process');
        });
    });

    describe('readTrace - additional coverage', () => {
        it('should handle trace with snake_case event fields', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const traceData = {
                id: 'run-sg-aa44',
                workflow_id: 'test-wf',
                runtime: 'swarmgraph',
                status: 'completed',
                started_at: '2024-01-01T10:00:00.000Z',
                events: [
                    { type: 'RUN_STARTED', timestamp: '2024-01-01T10:00:00.000Z', run_id: 'run-sg-aa44', sequence: 0, data: { prompt: 'test' } }
                ],
                metadata: {}
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa44.jsonl'),
                JSON.stringify(traceData),
                'utf-8'
            );

            const result = await service.readTrace('run-sg-aa44');
            expect(result.events[0].runId).toBe('run-sg-aa44');
        });

        it('should handle trace with traces field instead of events', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            const traceData = {
                id: 'run-sg-aa55',
                workflowId: 'test',
                runtime: 'swarmgraph',
                status: 'completed',
                startedAt: '2024-01-01T10:00:00.000Z',
                traces: [
                    { type: 'RUN_STARTED', timestamp: '2024-01-01T10:00:00.000Z', runId: 'run-sg-aa55', sequence: 0, data: {} }
                ],
                metadata: {}
            };

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa55.jsonl'),
                JSON.stringify(traceData),
                'utf-8'
            );

            const result = await service.readTrace('run-sg-aa55');
            expect(result.events.length).toBe(1);
        });

        it('should handle malformed JSON trace file', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa66.jsonl'),
                '{invalid json content',
                'utf-8'
            );

            await expect(service.readTrace('run-sg-aa66')).rejects.toThrow(ArcError);
        });
    });

    describe('getTraces - additional coverage', () => {
        it('should handle trace files with malformed content gracefully', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);

            await fs.writeFile(
                path.join(tracesDir, 'run-sg-aa77.jsonl'),
                'not valid json',
                'utf-8'
            );

            const traces = await service.getTraces();
            expect(traces.length).toBe(1);
            expect(traces[0].id).toBe('run-sg-aa77');
            expect(traces[0].status).toBe('unknown');
        });
    });

    describe('getRunReceipt', () => {
        it('should throw ArcError when receipt file does not exist', async () => {
            await expect(service.getRunReceipt('run_01HQ3WNOPQR456STU789VWX012')).rejects.toThrow(ArcError);
        });

        it('should throw ArcError for invalid run ID', async () => {
            await expect(service.getRunReceipt('bad')).rejects.toThrow(ArcError);
        });

        it('should return parsed receipt when file exists', async () => {
            const receiptsDir = path.join(tempDir, '.arc', 'receipts');
            await fs.ensureDir(receiptsDir);

            const receipt: RunReceipt = {
                schema_version: 1,
                receipt_id: 'rcpt_01JR6X7ABC123DEF456GHI789',
                run_id: 'run_01HQ3WNOPQR456STU789VWX012',
                session_id: 'ses_01JX8YABC123DEF456GHI789JK',
                status: 'completed',
                summary: 'Workflow completed successfully',
                cost_usd: 0.04,
                duration_ms: 48200,
                files_changed: [],
                approvals: [],
                evidence_refs: [],
                trust_boundaries_crossed: [],
                unresolved_risks: [],
                created_at: '2024-01-01T00:00:00.000Z',
            };

            await fs.writeFile(
                path.join(receiptsDir, 'run_01HQ3WNOPQR456STU789VWX012.json'),
                JSON.stringify(receipt),
                'utf-8'
            );

            const result = await service.getRunReceipt('run_01HQ3WNOPQR456STU789VWX012');
            expect(result.receipt_id).toBe('rcpt_01JR6X7ABC123DEF456GHI789');
            expect(result.status).toBe('completed');
            expect(result.cost_usd).toBe(0.04);
        });
    });

    describe('getRunAutopsy', () => {
        it('should return null when autopsy file does not exist', async () => {
            const result = await service.getRunAutopsy('run_01HQ3WNOPQR456STU789VWX012');
            expect(result).toBeNull();
        });

        it('should throw ArcError for invalid run ID', async () => {
            await expect(service.getRunAutopsy('bad')).rejects.toThrow(ArcError);
        });

        it('should return parsed autopsy when file exists', async () => {
            const autopsiesDir = path.join(tempDir, '.arc', 'autopsies');
            await fs.ensureDir(autopsiesDir);

            const autopsy: FailureAutopsy = {
                schema_version: 1,
                run_id: 'run_failed',
                probable_cause: 'Tool execution timeout at node reviewer',
                confidence: 'high',
                failed_node: 'reviewer',
                last_safe_state: "worker 'writer' completed at T+12.4s",
                retry_options: [{ label: 'Retry with same input', risk: 'low' }],
                related_issues: [],
                knows: ["Node 'reviewer' was active for 45.2s before failure"],
                guesses: ['Search tool may be rate-limited'],
                evidence_refs: [],
                created_at: '2024-01-01T00:00:00.000Z',
                metadata: {},
            };

            await fs.writeFile(
                path.join(autopsiesDir, 'run_failed.json'),
                JSON.stringify(autopsy),
                'utf-8'
            );

            const result = await service.getRunAutopsy('run_failed');
            expect(result).not.toBeNull();
            expect(result!.probable_cause).toContain('Tool execution timeout');
            expect(result!.confidence).toBe('high');
        });
    });

    describe('getRunContract', () => {
        it('should return null when contract file does not exist', async () => {
            const result = await service.getRunContract('run_01HQ3WNOPQR456STU789VWX012');
            expect(result).toBeNull();
        });

        it('should throw ArcError for invalid run ID', async () => {
            await expect(service.getRunContract('bad')).rejects.toThrow(ArcError);
        });

        it('should return parsed contract when file exists', async () => {
            const contractsDir = path.join(tempDir, '.arc', 'contracts');
            await fs.ensureDir(contractsDir);

            const contract: RunContract = {
                schema_version: 1,
                contract_id: 'ctr_01K...',
                session_id: 'ses_01JX...',
                objective: 'Review code changes',
                runtime: 'swarmgraph',
                mode: 'build',
                allowed_tools: ['search', 'read'],
                write_scope: ['src/'],
                cost_ceiling_usd: 'unknown',
                approval_policy: 'auto',
                rollback_plan: 'git revert --no-edit HEAD',
                evidence_expected: [],
                status: 'fulfilled',
                created_at: '2024-01-01T00:00:00.000Z',
                metadata: {},
            };

            await fs.writeFile(
                path.join(contractsDir, 'run_with_contract.json'),
                JSON.stringify(contract),
                'utf-8'
            );

            const result = await service.getRunContract('run_with_contract');
            expect(result).not.toBeNull();
            expect(result!.objective).toBe('Review code changes');
            expect(result!.runtime).toBe('swarmgraph');
        });
    });
});
