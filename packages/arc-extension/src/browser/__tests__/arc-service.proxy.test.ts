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
    TraceEvent,
    RuntimeCapabilitiesResponse,
    ProviderStatus,
    DoctorAction,
    RuntimeCapabilityReport,
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
                'detectWorkflows',
                'listRuntimeCapabilities',
                'getProviderStatus',
                'getWorkspaceStatus',
            ];

            const mockService: any = {
                executeWorkflow: async () => ({}),
                cancelWorkflow: async () => ({}),
                getTraces: async () => [],
                readTrace: async () => ({}),
                streamTrace: async () => ({}),
                validateTrace: async () => ({}),
                detectWorkflows: async () => [],
                listRuntimeCapabilities: async () => ({}),
                getProviderStatus: async () => ({}),
                getWorkspaceStatus: async () => ({}),
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

        it('listRuntimeCapabilities should return RuntimeCapabilitiesResponse', async () => {
            const mockService = {
                listRuntimeCapabilities: async (): Promise<RuntimeCapabilitiesResponse> => ({
                    workspace: '/test',
                    auto_priority: ['swarmgraph'],
                    runtimes: [
                        {
                            runtime_id: 'swarmgraph',
                            detected: true,
                            can_run: true,
                            availability: 'available',
                            detected_artifacts: [],
                            required_env: [],
                            requires_paid_calls: false,
                            doctor_actions: [],
                        },
                    ],
                }),
            };

            const result = await mockService.listRuntimeCapabilities();
            expect(result.workspace).toBe('/test');
            expect(result.runtimes.length).toBe(1);
            expect(result.runtimes[0].runtime_id).toBe('swarmgraph');
        });

        it('getProviderStatus should return ProviderStatus', async () => {
            const mockService = {
                getProviderStatus: async (provider: string): Promise<ProviderStatus> => ({
                    provider,
                    baseUrlConfigured: false,
                    apiKeyConfigured: true,
                    runtimeAvailable: true,
                    message: 'Provider configured',
                }),
            };

            const result = await mockService.getProviderStatus('openai');
            expect(result.provider).toBe('openai');
            expect(result.apiKeyConfigured).toBe(true);
        });

        it('getWorkspaceStatus should return workspace paths', async () => {
            const mockService = {
                getWorkspaceStatus: async (): Promise<{ frontendPath: string; backendPath: string; source: string }> => ({
                    frontendPath: '/workspace',
                    backendPath: '/workspace',
                    source: 'filesystem',
                }),
            };

            const result = await mockService.getWorkspaceStatus();
            expect(result.frontendPath).toBe('/workspace');
            expect(result.backendPath).toBe('/workspace');
        });

        it('RuntimeCapabilityReport should support doctor_actions', () => {
            const report: RuntimeCapabilityReport = {
                runtime_id: 'test',
                detected: true,
                can_run: false,
                availability: 'missing_deps',
                detected_artifacts: ['file.py'],
                required_env: ['API_KEY'],
                requires_paid_calls: true,
                doctor_actions: [
                    {
                        id: 'install-deps',
                        label: 'Install Dependencies',
                        description: 'Run pip install',
                        command: 'pip install -r requirements.txt',
                        safe_to_auto_run: true,
                    },
                ],
            };
            expect(report.doctor_actions.length).toBe(1);
            expect(report.doctor_actions[0].id).toBe('install-deps');
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
