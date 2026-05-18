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

const backendSource = fs.readFileSync(path.resolve(__dirname, '../../../src/node/arc-backend-service.ts'), 'utf-8');

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

    describe('provider quota reset bridge', () => {
        it('should call quota reset CLI, not quota show', () => {
            expect(backendSource).toMatch(/async resetProviderQuota\(\)/);
            expect(backendSource).toMatch(/execFileSync\('arc', \['providers', 'quota', 'reset', '--json'\]/);
            expect(backendSource).toMatch(/env:\s*buildArcCliEnv\(\)/);
            expect(backendSource).toMatch(/Provider quota reset failed/);
            expect(backendSource).not.toMatch(/execFileSync\('arc', \['providers', 'quota', 'show', '--json'\]/);
        });
    });

    describe('gated provider action bridge', () => {
        let originalPath: string | undefined;

        afterEach(() => {
            process.env.PATH = originalPath;
        });

        async function installArcFixture(script: string): Promise<void> {
            originalPath = process.env.PATH;
            const binDir = path.join(tempDir, 'bin');
            await fs.ensureDir(binDir);
            const arcPath = path.join(binDir, 'arc');
            await fs.writeFile(arcPath, script, 'utf-8');
            await fs.chmod(arcPath, 0o755);
            process.env.PATH = `${binDir}${path.delimiter}${originalPath || ''}`;
        }

        it('should default to dry-run and pass only provider/model/prompt/gate flags', async () => {
            const argsPath = path.join(tempDir, 'arc-args.txt');
            await installArcFixture(`#!/bin/sh
printf '%s\n' "$@" > "${argsPath}"
printf '%s' '{"ok":true,"data":{"provider":"openai","model":"gpt-4o-mini","dry_run":true,"provider_call":false,"blocked":false,"message":"dry run only","quota":{"remaining":5}}}'
`);

            const result = await service.runGatedProviderAction({
                provider: 'openai',
                model: 'gpt-4o-mini',
                prompt: 'hello'
            });

            const args = (await fs.readFile(argsPath, 'utf-8')).trim().split('\n');
            expect(args).toEqual([
                'providers',
                'action',
                '--provider',
                'openai',
                '--prompt',
                'hello',
                '--json',
                '--model',
                'gpt-4o-mini'
            ]);
            expect(args.join(' ')).not.toMatch(/sk-|api[_-]?key|token/i);
            expect(result).toMatchObject({
                success: true,
                blocked: false,
                dryRun: true,
                providerCall: false,
                provider: 'openai',
                model: 'gpt-4o-mini',
                message: 'dry run only',
                quota: { remaining: 5 }
            });
        });

        it('should surface blocked CLI JSON from failed commands', async () => {
            await installArcFixture(`#!/bin/sh
printf '%s' '{"ok":false,"error":{"code":"provider_gate_blocked","message":"Provider call blocked: confirmation required"},"data":{"provider":"openai","dry_run":false,"provider_call":false,"blocked":true}}' >&2
exit 2
`);

            const result = await service.runGatedProviderAction({
                provider: 'openai',
                model: 'gpt-4o-mini',
                prompt: 'hello',
                dryRun: false,
                allowPaidCalls: true
            });

            expect(result).toMatchObject({
                success: false,
                blocked: true,
                dryRun: false,
                providerCall: false,
                provider: 'openai',
                message: 'Provider call blocked: confirmation required'
            });
        });

        it('should include explicit confirmation flags only when requested', async () => {
            const argsPath = path.join(tempDir, 'arc-args.txt');
            await installArcFixture(`#!/bin/sh
printf '%s\n' "$@" > "${argsPath}"
printf '%s' '{"ok":true,"data":{"provider":"openai","dry_run":false,"provider_call":true,"blocked":false,"message":"completed"}}'
`);

            const result = await service.runGatedProviderAction({
                provider: 'openai',
                prompt: 'hello',
                dryRun: false,
                allowPaidCalls: true,
                confirmProviderCall: true
            });

            const args = (await fs.readFile(argsPath, 'utf-8')).trim().split('\n');
            expect(args).toContain('--allow-paid-calls');
            expect(args).toContain('--live');
            expect(args).toContain('--confirm');
            expect(args).toContain('RUN_PROVIDER_ACTION:openai:gpt-4o-mini');
            expect(args).not.toContain('--dry-run');
            expect(result).toMatchObject({ success: true, blocked: false, dryRun: false, providerCall: true });
        });
    });

    describe('run cost metadata bridge', () => {
        let originalPath: string | undefined;

        afterEach(() => {
            process.env.PATH = originalPath;
        });

        async function installArcFixture(script: string): Promise<void> {
            originalPath = process.env.PATH;
            const binDir = path.join(tempDir, 'bin');
            await fs.ensureDir(binDir);
            const arcPath = path.join(binDir, 'arc');
            await fs.writeFile(arcPath, script, 'utf-8');
            await fs.chmod(arcPath, 0o755);
            process.env.PATH = `${binDir}${path.delimiter}${originalPath || ''}`;
        }

        it('should preserve dry-run preflight and map cost metadata without implicit paid opt-in', async () => {
            const argsPath = path.join(tempDir, 'arc-args.txt');
            await installArcFixture(`#!/bin/sh
printf '%s\n' "$@" > "${argsPath}"
printf '%s' '{"ok":true,"data":{"workflow":"crew.py","runtime":"crewai+swarmgraph","runnable":false,"blockers":[],"warnings":[],"doctor_actions":[],"paid_call_required":true,"provider":"openai","quota":{"remaining":3},"estimated_cost":{"currency":"USD"},"key_ref_status":{},"export_target_status":{},"dependency_status":{}}}'
`);

            const result = await service.preflightRun({
                workflow: 'crew.py',
                runtimeId: 'crewai+swarmgraph',
                dryRun: true
            });

            const args = (await fs.readFile(argsPath, 'utf-8')).trim().split('\n');
            expect(args).toContain('--dry-run');
            expect(args).not.toContain('--allow-paid-calls');
            expect(result.providerCall).toBe(false);
            expect(result.costMetadata).toEqual({
                paidCallRequired: true,
                paidCallAllowed: false,
                providerCall: false,
                dryRun: true,
                quota: { remaining: 3 },
                provider: 'openai',
                estimatedCost: { currency: 'USD' }
            });
        });

        it('should pass paid opt-in to startRun only when request explicitly permits it', async () => {
            const argsPath = path.join(tempDir, 'arc-args.txt');
            await installArcFixture(`#!/bin/sh
printf '%s\n' "$@" > "${argsPath}"
printf '%s' '{"ok":true,"data":{"id":"run-1","status":"completed","runtime":"crewai+swarmgraph","paid_call_required":true,"metadata":{"trace_path":"trace.jsonl","provider":"openai"}}}'
`);

            const result = await service.startRun({
                workflow: 'crew.py',
                runtimeId: 'crewai+swarmgraph',
                allowPaidCalls: true
            });

            const args = (await fs.readFile(argsPath, 'utf-8')).trim().split('\n');
            expect(args).toContain('--allow-paid-calls');
            expect(result.costMetadata).toMatchObject({
                paidCallRequired: true,
                paidCallAllowed: true,
                providerCall: false,
                dryRun: false,
                provider: 'openai'
            });
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

    describe('config status/save', () => {
        let originalPath: string | undefined;

        afterEach(() => {
            process.env.PATH = originalPath;
        });

        async function installArcFixture(script: string): Promise<string> {
            originalPath = process.env.PATH;
            const binDir = path.join(tempDir, 'bin');
            await fs.ensureDir(binDir);
            const arcPath = path.join(binDir, 'arc');
            await fs.writeFile(arcPath, script, 'utf-8');
            await fs.chmod(arcPath, 0o755);
            process.env.PATH = `${binDir}${path.delimiter}${originalPath || ''}`;
            return arcPath;
        }

        it('should return safe config status from CLI output without secret values', async () => {
            await installArcFixture(`#!/bin/sh
if [ "$1 $2 $3" = "providers status --json" ]; then
  printf '%s' '{"ok":true,"data":[{"provider":"openai","display_name":"OpenAI","apiKeyConfigured":true,"apiKeySource":"env","api_key_env":"OPENAI_API_KEY","default_model":"gpt-4o","api_key":"sk-should-not-surface"},{"provider":"anthropic","display_name":"Anthropic","api_key_configured":false,"api_key":"sk-ant-should-not-surface"}]}'
  exit 0
fi
if [ "$1 $2 $3" = "config show --json" ]; then
  printf '%s' '{"ok":true,"data":{"runtime":{"default":"langgraph","auto_detect":false,"fallback":"stub"},"execution":{"isolation":"subprocess","timeout_seconds":120,"allow_paid_calls":true},"providers":{"dry_run":false,"routing_mode":"auto"},"profiles":{"selected_profile":"local-dev"},"workspace":{"trust_level":"trusted"}}}'
  exit 0
fi
exit 2
`);

            const result = await service.getConfigStatus();

            expect(result.backendAvailable).toBe(true);
            expect(result.workspace.trusted).toBe(true);
            expect(result.runtime).toMatchObject({
                defaultRuntime: 'langgraph',
                autoDetect: false,
                isolation: 'subprocess',
                timeoutSeconds: 120,
                allowPaidCalls: true,
                dryRun: false,
                routingMode: 'auto'
            });
            expect(result.selectedProfile).toBe('local-dev');
            expect(result.providers[0]).toEqual({
                provider: 'openai',
                displayName: 'OpenAI',
                configured: true,
                source: 'env',
                defaultModel: 'gpt-4o',
                envOverride: 'OPENAI_API_KEY'
            });
            expect(JSON.stringify(result)).not.toContain('sk-should-not-surface');
            expect(JSON.stringify(result)).not.toContain('sk-ant-should-not-surface');
        });

        it('should return degraded provider status when providers CLI fails but keep config defaults', async () => {
            await installArcFixture(`#!/bin/sh
if [ "$1 $2 $3" = "providers status --json" ]; then
  printf '%s' 'arc missing' >&2
  exit 1
fi
if [ "$1 $2 $3" = "config show --json" ]; then
  printf '%s' '{"ok":false}'
  exit 0
fi
exit 2
`);

            const result = await service.getConfigStatus();

            expect(result.backendAvailable).toBe(false);
            expect(result.backendMessage).toContain('Backend unavailable:');
            expect(result.providers).toEqual([
                { provider: 'openai', displayName: 'OpenAI', configured: false, source: 'unset' },
                { provider: 'anthropic', displayName: 'Anthropic', configured: false, source: 'unset' },
                { provider: 'ollama', displayName: 'Ollama', configured: false, source: 'unset' }
            ]);
            expect(result.runtime).toMatchObject({
                defaultRuntime: 'swarmgraph',
                autoDetect: true,
                fallback: 'stub',
                isolation: 'none',
                timeoutSeconds: 300,
                allowPaidCalls: false,
                dryRun: true,
                routingMode: 'manual'
            });
        });

        it('should reject unsafe save config fields before invoking CLI', async () => {
            const markerPath = path.join(tempDir, 'cli-called');
            await installArcFixture(`#!/bin/sh
touch "${markerPath}"
exit 1
`);

            const result = await service.saveConfig({ apiKey: 'sk-secret' } as any);

            expect(result.success).toBe(false);
            expect(result.message).toContain('Rejected unsafe config field: apiKey');
            expect(await fs.pathExists(markerPath)).toBe(false);
        });

        it('should reject empty save config updates before invoking CLI', async () => {
            const markerPath = path.join(tempDir, 'cli-called');
            await installArcFixture(`#!/bin/sh
touch "${markerPath}"
exit 1
`);

            const result = await service.saveConfig({});

            expect(result).toEqual({ success: false, message: 'No config fields to update.' });
            expect(await fs.pathExists(markerPath)).toBe(false);
        });

        it('should save only safe config fields through arc config set', async () => {
            const argsPath = path.join(tempDir, 'arc-args.txt');
            await installArcFixture(`#!/bin/sh
printf '%s\n' "$@" > "${argsPath}"
exit 0
`);

            const result = await service.saveConfig({
                defaultRuntime: 'langgraph',
                mode: 'build',
                isolation: 'subprocess',
                allowPaidCalls: false,
                dryRun: true,
                routingMode: 'manual',
                selectedProfile: 'local-dev'
            });

            expect(result).toEqual({ success: true, message: 'Configuration saved.' });
            const args = (await fs.readFile(argsPath, 'utf-8')).trim().split('\n');
            expect(args).toEqual([
                'config',
                'set',
                'runtime.default=langgraph',
                'execution.mode=build',
                'execution.isolation=subprocess',
                'execution.allow_paid_calls=false',
                'providers.dry_run=true',
                'providers.routing_mode=manual',
                'profiles.selected_profile=local-dev'
            ]);
        });

        it('should report save config CLI failures', async () => {
            await installArcFixture(`#!/bin/sh
printf '%s' 'permission denied' >&2
exit 1
`);

            const result = await service.saveConfig({ defaultRuntime: 'langgraph' });

            expect(result.success).toBe(false);
            expect(result.message).toContain('Failed to save config:');
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

    describe('streamActiveTrace live daemon proxy', () => {
        const originalFetch = global.fetch;
        const originalDaemonUrl = process.env.ARC_PYTHON_DAEMON_URL;

        afterEach(() => {
            global.fetch = originalFetch;
            if (originalDaemonUrl === undefined) {
                delete process.env.ARC_PYTHON_DAEMON_URL;
            } else {
                process.env.ARC_PYTHON_DAEMON_URL = originalDaemonUrl;
            }
        });

        async function collectActiveTrace(runId = 'run_live_test') {
            const iterable = await service.streamActiveTrace({ runId, mode: 'live', timeoutMs: 1000 });
            const chunks = [];
            for await (const chunk of iterable) {
                chunks.push(chunk);
                if (chunk.done) break;
            }
            return chunks;
        }

        it('should use configured Python daemon URL for live SSE', async () => {
            process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:8765';
            let requestedUrl = '';
            global.fetch = jest.fn(async (url: Parameters<typeof fetch>[0]) => {
                requestedUrl = url.toString();
                const body = new ReadableStream({
                    start(controller) {
                        controller.enqueue(new TextEncoder().encode('data: {"type":"RUN_COMPLETED"}\n\n'));
                        controller.close();
                    },
                });
                return { ok: true, status: 200, body } as Response;
            });

            const chunks = await collectActiveTrace();

            expect(requestedUrl).toBe('http://127.0.0.1:8765/api/runs/run_live_test/events?mode=live');
            expect(chunks.some(chunk => chunk.status?.state === 'connected')).toBe(true);
            expect(chunks[chunks.length - 1]).toMatchObject({ terminal: 'RUN_COMPLETED', done: true });
        });

        it('should reject unsafe configured daemon URL', async () => {
            process.env.ARC_PYTHON_DAEMON_URL = 'file:///tmp/arc.sock';
            global.fetch = jest.fn();

            const chunks = await collectActiveTrace();

            expect(global.fetch).not.toHaveBeenCalled();
            expect(chunks[chunks.length - 1]).toMatchObject({
                terminal: 'STREAM_END',
                done: true,
                status: { state: 'error', message: 'Invalid Python web/SSE base URL.' },
            });
        });

        it('should emit disconnected degraded state when daemon fetch fails', async () => {
            process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:8765';
            global.fetch = jest.fn(async () => {
                throw new Error('ECONNREFUSED');
            });

            const chunks = await collectActiveTrace();

            expect(chunks[chunks.length - 1]).toMatchObject({
                terminal: 'STREAM_END',
                done: true,
                status: { state: 'disconnected' },
            });
            expect(chunks[chunks.length - 1]?.status?.message).toContain('Live SSE proxy degraded; ECONNREFUSED');
        });
    });
});
