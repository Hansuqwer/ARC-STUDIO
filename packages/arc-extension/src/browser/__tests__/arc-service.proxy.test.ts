import {
    ArcServicePath,
    ArcService,
    ArcError,
    ArcErrorCode,
    ExecutionResult,
    TraceFile,
    TraceData,
    ValidationResult,
    CancelResult,
    WorkflowInfo,
    TraceEvent
} from '../../common/arc-protocol';

describe('ArcService Proxy Tests', () => {
    describe('ArcServicePath', () => {
        it('should be the correct path', () => {
            expect(ArcServicePath).toBe('/services/arc');
        });

        it('should be a valid URL path', () => {
            expect(ArcServicePath).toMatch(/^\/services\/\w+$/);
        });
    });

    describe('ArcService Symbol', () => {
        it('should be a Symbol', () => {
            expect(typeof ArcService).toBe('symbol');
        });

        it('should have correct description', () => {
            expect(ArcService.toString()).toBe('Symbol(ArcService)');
        });

        it('should be usable as object key', () => {
            const container: any = {};
            container[ArcService] = 'mock-service';
            expect(container[ArcService]).toBe('mock-service');
        });
    });

    describe('ArcService Interface', () => {
        it('should define all required methods', () => {
            const requiredMethods = [
                'executeWorkflow',
                'cancelWorkflow',
                'getTraces',
                'readTrace',
                'streamTrace',
                'validateTrace',
                'detectWorkflows'
            ];

            const mockService: any = {
                executeWorkflow: async () => ({}),
                cancelWorkflow: async () => ({}),
                getTraces: async () => [],
                readTrace: async () => ({}),
                streamTrace: async () => ({}),
                validateTrace: async () => ({}),
                detectWorkflows: async () => []
            };

            for (const method of requiredMethods) {
                expect(typeof mockService[method]).toBe('function');
            }
        });

        it('executeWorkflow should accept prompt and optional options', async () => {
            const mockService = {
                executeWorkflow: async (prompt: string, options?: any): Promise<ExecutionResult> => {
                    return {
                        runId: 'test-run',
                        status: 'completed' as const,
                        tracePath: '.arc/traces/test.jsonl'
                    };
                }
            };

            const result1 = await mockService.executeWorkflow('test');
            expect(result1.runId).toBe('test-run');

            const result2 = await mockService.executeWorkflow('test', { backend: 'stub' });
            expect(result2.runId).toBe('test-run');
        });

        it('getTraces should return TraceFile array', async () => {
            const mockService = {
                getTraces: async (): Promise<TraceFile[]> => [
                    {
                        id: 'run-1',
                        path: '/path/to/trace.jsonl',
                        timestamp: '2024-01-01T00:00:00.000Z',
                        status: 'completed'
                    }
                ]
            };

            const traces = await mockService.getTraces();
            expect(Array.isArray(traces)).toBe(true);
            expect(traces[0].id).toBe('run-1');
        });

        it('readTrace should return TraceData', async () => {
            const mockService = {
                readTrace: async (traceId: string): Promise<TraceData> => ({
                    id: traceId,
                    workflowId: 'test-workflow',
                    runtime: 'swarmgraph',
                    status: 'completed',
                    startedAt: '2024-01-01T00:00:00.000Z',
                    events: [],
                    metadata: {}
                })
            };

            const trace = await mockService.readTrace('test-id');
            expect(trace.id).toBe('test-id');
            expect(trace.events).toEqual([]);
        });

        it('validateTrace should return ValidationResult', async () => {
            const mockService = {
                validateTrace: async (traceId: string): Promise<ValidationResult> => ({
                    valid: true,
                    errors: [],
                    warnings: [],
                    format: 'jsonl'
                })
            };

            const result = await mockService.validateTrace('test-id');
            expect(result.valid).toBe(true);
            expect(result.format).toBe('jsonl');
        });

        it('cancelWorkflow should return CancelResult', async () => {
            const mockService = {
                cancelWorkflow: async (runId: string): Promise<CancelResult> => ({
                    success: true,
                    runId,
                    message: 'Cancelled'
                })
            };

            const result = await mockService.cancelWorkflow('run-1');
            expect(result.success).toBe(true);
            expect(result.runId).toBe('run-1');
        });

        it('detectWorkflows should return WorkflowInfo array', async () => {
            const mockService = {
                detectWorkflows: async (): Promise<WorkflowInfo[]> => [
                    {
                        type: 'swarmgraph',
                        path: '/usr/bin/swarmgraph',
                        name: 'SwarmGraph CLI'
                    }
                ]
            };

            const workflows = await mockService.detectWorkflows();
            expect(workflows.length).toBe(1);
            expect(workflows[0].type).toBe('swarmgraph');
        });
    });

    describe('Protocol Types', () => {
        it('ArcErrorCode should have all expected codes', () => {
            expect(ArcErrorCode.INVALID_INPUT).toBe('INVALID_INPUT');
            expect(ArcErrorCode.TRACE_NOT_FOUND).toBe('TRACE_NOT_FOUND');
            expect(ArcErrorCode.EXECUTION_FAILED).toBe('EXECUTION_FAILED');
            expect(ArcErrorCode.PARSE_ERROR).toBe('PARSE_ERROR');
            expect(ArcErrorCode.WORKFLOW_NOT_FOUND).toBe('WORKFLOW_NOT_FOUND');
            expect(ArcErrorCode.PERMISSION_DENIED).toBe('PERMISSION_DENIED');
            expect(ArcErrorCode.TIMEOUT).toBe('TIMEOUT');
            expect(ArcErrorCode.UNKNOWN).toBe('UNKNOWN');
        });

        it('ArcError should be instantiable', () => {
            const error = new ArcError(
                ArcErrorCode.INVALID_INPUT,
                'Test error',
                { detail: 'test' }
            );

            expect(error).toBeInstanceOf(Error);
            expect(error.name).toBe('ArcError');
            expect(error.code).toBe(ArcErrorCode.INVALID_INPUT);
            expect(error.message).toBe('Test error');
            expect(error.details).toEqual({ detail: 'test' });
        });

        it('ArcError should work with instanceof', () => {
            const error = new ArcError(ArcErrorCode.UNKNOWN, 'test');
            expect(error instanceof ArcError).toBe(true);
            expect(error instanceof Error).toBe(true);
        });

        it('ArcError should work without details', () => {
            const error = new ArcError(ArcErrorCode.TIMEOUT, 'timed out');
            expect(error.details).toBeUndefined();
        });
    });
});
