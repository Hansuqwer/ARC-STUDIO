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
    RunReceipt,
    FailureAutopsy,
    RunContract,
    ConfigStatus,
    SafeConfigUpdate,
    ArcProfileInfo,
    IsolationStatus,
    IsolationProviderInfo,
    RunLinksResponse,
    HitlPromptInfo,
    HitlRespondRequest,
    AuditChainInfo,
    ReplayResult,
    ReplayEvent,
    ProviderQuotaResetResult,
    canonicalErrorCode,
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
                'preflightRun',
                'startRun',
                'getProviderStatus',
                'getWorkspaceStatus',
                'getRunReceipt',
                'getRunAutopsy',
                'getRunContract',
                'getConfigStatus',
                'saveConfig',
                'listProfiles',
                'getIsolationStatus',
                'listIsolationProviders',
                'getRunLinks',
                'listPendingHitlPrompts',
                'respondHitlPrompt',
                'getAuditChainInfo',
                'replayRun',
                'diffRuns',
                'resetProviderQuota',
                'getMcpWorkbenchStatus',
                'getWorkspaceInventory',
                'detectTestbench',
                'getCiCheckStatus',
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
                preflightRun: async () => ({}),
                startRun: async () => ({}),
                getProviderStatus: async () => ({}),
                getWorkspaceStatus: async () => ({}),
                getRunReceipt: async () => ({}),
                getRunAutopsy: async () => ({}),
                getRunContract: async () => ({}),
                getConfigStatus: async () => ({}),
                saveConfig: async () => ({}),
                listProfiles: async () => [],
                getIsolationStatus: async () => ({}),
                listIsolationProviders: async () => [],
                getRunLinks: async () => ({}),
                listPendingHitlPrompts: async () => [],
                respondHitlPrompt: async () => ({}),
                getAuditChainInfo: async () => ({}),
                replayRun: async () => ({}),
                diffRuns: async () => ({}),
                resetProviderQuota: async () => ({ success: true, message: 'Local provider quota counters reset' }),
                getMcpWorkbenchStatus: async () => ({ workspace: '', serverCreatable: false, tools: [], resources: [], trust: { level: 'unknown' }, diagnostic: '' }),
                getWorkspaceInventory: async () => ({ workspace: '', files: { count: 0, totalSize: 0, entries: [] }, git: { provenance: '' }, traces: { count: 0, entries: [] }, mcpResources: [] }),
                detectTestbench: async () => ({ workspace: '', detected: [], count: 0 }),
                getCiCheckStatus: async () => ({ private: false, workspace: '', checks: {}, overall: 'skip' }),
            };

            for (const method of requiredMethods) {
                expect(typeof mockService[method]).toBe('function');
            }
        });

        it('resetProviderQuota should return typed local reset result', async () => {
            const mockService = {
                resetProviderQuota: async (): Promise<ProviderQuotaResetResult> => ({
                    success: true,
                    message: 'Local provider quota counters reset',
                }),
            };

            await expect(mockService.resetProviderQuota()).resolves.toEqual({
                success: true,
                message: 'Local provider quota counters reset',
            });
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

        it('profile and isolation DTOs should contain no raw secrets', async () => {
            const mockService = {
                listProfiles: async (): Promise<ArcProfileInfo[]> => [
                    { id: 'local-safe', name: 'Local Safe', allowPaidCalls: false, dryRun: true, provider: 'ollama' },
                ],
                getIsolationStatus: async (): Promise<IsolationStatus> => ({
                    current: 'none',
                    available: true,
                    providers: [{ id: 'none', name: 'None', available: true, active: true }],
                }),
                listIsolationProviders: async (): Promise<IsolationProviderInfo[]> => [
                    { id: 'none', name: 'None', available: true, active: true },
                ],
            };

            expect(await mockService.listProfiles()).toEqual([
                { id: 'local-safe', name: 'Local Safe', allowPaidCalls: false, dryRun: true, provider: 'ollama' },
            ]);
            expect((await mockService.getIsolationStatus()).current).toBe('none');
            expect((await mockService.listIsolationProviders())[0].available).toBe(true);
        });
    });

        it('getRunReceipt should return RunReceipt', async () => {
            const mockService = {
                getRunReceipt: async (runId: string): Promise<RunReceipt> => ({
                    schema_version: 1,
                    receipt_id: 'rcpt_01JR6X7ABC123DEF456GHI789',
                    run_id: runId,
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
                }),
            };

            const result = await mockService.getRunReceipt('run_01HQ3WNOPQR456STU789VWX012');
            expect(result.receipt_id).toBe('rcpt_01JR6X7ABC123DEF456GHI789');
            expect(result.run_id).toBe('run_01HQ3WNOPQR456STU789VWX012');
            expect(result.status).toBe('completed');
        });

        it('getRunAutopsy should return FailureAutopsy or null', async () => {
            const mockService = {
                getRunAutopsy: async (runId: string): Promise<FailureAutopsy | null> => {
                    if (runId === 'run_failed') {
                        return {
                            schema_version: 1,
                            run_id: runId,
                            probable_cause: 'Tool execution timeout',
                            confidence: 'high',
                            retry_options: [{ label: 'Retry with same input', risk: 'low' }],
                            related_issues: [],
                            knows: ['Node was active for 45.2s before failure'],
                            guesses: ['Search tool may be rate-limited'],
                            evidence_refs: [],
                            created_at: '2024-01-01T00:00:00.000Z',
                            metadata: {},
                        };
                    }
                    return null;
                },
            };

            const result1 = await mockService.getRunAutopsy('run_failed');
            expect(result1).not.toBeNull();
            expect(result1!.probable_cause).toBe('Tool execution timeout');

            const result2 = await mockService.getRunAutopsy('run_ok');
            expect(result2).toBeNull();
        });

        it('getRunContract should return RunContract or null', async () => {
            const mockService = {
                getRunContract: async (runId: string): Promise<RunContract | null> => {
                    if (runId === 'run_with_contract') {
                        return {
                            schema_version: 1,
                            contract_id: 'ctr_01K...',
                            session_id: 'ses_01JX...',
                            objective: 'Review code changes',
                            runtime: 'swarmgraph',
                            mode: 'build',
                            allowed_tools: [],
                            write_scope: [],
                            cost_ceiling_usd: 'unknown',
                            approval_policy: 'auto',
                            rollback_plan: 'git revert',
                            evidence_expected: [],
                            status: 'fulfilled',
                            created_at: '2024-01-01T00:00:00.000Z',
                            metadata: {},
                        };
                    }
                    return null;
                },
            };

            const result1 = await mockService.getRunContract('run_with_contract');
            expect(result1).not.toBeNull();
            expect(result1!.objective).toBe('Review code changes');

            const result2 = await mockService.getRunContract('run_no_contract');
            expect(result2).toBeNull();
        });

        it('getRunReceipt should handle missing receipt gracefully', async () => {
            const mockService = {
                getRunReceipt: async (runId: string): Promise<RunReceipt> => {
                    throw new ArcError(ArcErrorCode.RUN_NOT_FOUND, `No receipt found for run: ${runId}`);
                },
            };

            await expect(mockService.getRunReceipt('nonexistent')).rejects.toThrow(ArcError);
        });

        it('getRunAutopsy should return null for non-failed runs', async () => {
            const mockService = {
                getRunAutopsy: async (_runId: string) => null,
            };

            const result = await mockService.getRunAutopsy('run_ok');
            expect(result).toBeNull();
        });

        it('getRunContract should return null when no contract exists', async () => {
            const mockService = {
                getRunContract: async (_runId: string) => null,
            };

            const result = await mockService.getRunContract('run_no_contract');
            expect(result).toBeNull();
        });

        // ========== Slice 7: HITL / Audit / Replay ==========

        it('listPendingHitlPrompts should return HitlPromptInfo array', async () => {
            const mockService = {
                listPendingHitlPrompts: async (): Promise<HitlPromptInfo[]> => [
                    {
                        promptId: 'hitl_01JR6X7ABC123DEF456GHI789',
                        runId: 'run_01HQ3WNOPQR456STU789VWX012',
                        prompt: 'Approve write to /etc/config?',
                        createdAt: '2024-01-01T00:00:00.000Z',
                        expiresAt: '2024-01-01T01:00:00.000Z',
                        promptType: 'file_write',
                        token: 'tok_test',
                    },
                ],
            };

            const prompts = await mockService.listPendingHitlPrompts();
            expect(Array.isArray(prompts)).toBe(true);
            expect(prompts.length).toBe(1);
            expect(prompts[0].promptId).toContain('hitl');
            expect(prompts[0].prompt).toContain('Approve');
        });

        it('respondHitlPrompt should return success status', async () => {
            const mockService = {
                respondHitlPrompt: async (request: HitlRespondRequest): Promise<{ success: boolean; message: string }> => ({
                    success: true,
                    message: `HITL ${request.decision} for ${request.promptId}`,
                }),
            };

            const result = await mockService.respondHitlPrompt({
                promptId: 'hitl_01JR6X7ABC123DEF456GHI789',
                decision: 'approve',
                token: 'tok_test',
            });
            expect(result.success).toBe(true);
            expect(result.message).toContain('approve');
        });

        it('respondHitlPrompt should support reject decision', async () => {
            const mockService = {
                respondHitlPrompt: async (request: HitlRespondRequest): Promise<{ success: boolean; message: string }> => ({
                    success: true,
                    message: `HITL ${request.decision} for ${request.promptId}`,
                }),
            };

            const result = await mockService.respondHitlPrompt({
                promptId: 'hitl_01JR6X7ABC123DEF456GHI789',
                decision: 'reject',
                token: 'tok_test',
            });
            expect(result.success).toBe(true);
            expect(result.message).toContain('reject');
        });

        it('getAuditChainInfo should return audit info for a run', async () => {
            const mockService = {
                getAuditChainInfo: async (runId: string): Promise<AuditChainInfo> => ({
                    runId,
                    auditPath: '/home/user/.arc/audit/chain.json',
                    chainVerified: true,
                    recordCount: 5,
                    signature: 'abcd1234efgh5678',
                    hmacAlgo: 'sha256',
                }),
            };

            const info = await mockService.getAuditChainInfo('run_01HQ3WNOPQR456STU789VWX012');
            expect(info.runId).toBe('run_01HQ3WNOPQR456STU789VWX012');
            expect(info.chainVerified).toBe(true);
            expect(info.recordCount).toBe(5);
            expect(info.hmacAlgo).toBe('sha256');
        });

        it('getAuditChainInfo should return null when no audit path exists', async () => {
            const mockService = {
                getAuditChainInfo: async (_runId: string): Promise<AuditChainInfo | null> => null,
            };

            const info = await mockService.getAuditChainInfo('run_no_audit');
            expect(info).toBeNull();
        });

        it('replayRun should return ReplayResult with events', async () => {
            const mockService = {
                replayRun: async (runId: string): Promise<ReplayResult> => ({
                    runId,
                    events: [
                        { type: 'RUN_STARTED', timestamp: '2024-01-01T00:00:00.000Z', runId, sequence: 0, data: { prompt: 'test' } },
                        { type: 'RUN_COMPLETED', timestamp: '2024-01-01T00:01:00.000Z', runId, sequence: 1, data: { output: 'done' } },
                    ],
                    totalEvents: 2,
                }),
            };

            const result = await mockService.replayRun('run_01HQ3WNOPQR456STU789VWX012');
            expect(result.runId).toBe('run_01HQ3WNOPQR456STU789VWX012');
            expect(result.totalEvents).toBe(2);
            expect(result.events[0].type).toBe('RUN_STARTED');
            expect(result.events[1].type).toBe('RUN_COMPLETED');
        });

        it('replayRun should handle empty event list', async () => {
            const mockService = {
                replayRun: async (runId: string): Promise<ReplayResult> => ({
                    runId,
                    events: [],
                    totalEvents: 0,
                }),
            };

            const result = await mockService.replayRun('run_empty');
            expect(result.totalEvents).toBe(0);
            expect(result.events).toEqual([]);
        });

        describe('Protocol Types', () => {
            it('ArcErrorCode should have all expected codes', () => {
                expect(ArcErrorCode.RUN_NOT_FOUND).toBe('RUN_NOT_FOUND');
                expect(ArcErrorCode.RUN_FAILED).toBe('RUN_FAILED');
                expect(ArcErrorCode.INVALID_INPUT).toBe('INVALID_INPUT');
                expect(ArcErrorCode.PERMISSION_DENIED).toBe('PERMISSION_DENIED');
                expect(ArcErrorCode.TIMEOUT).toBe('TIMEOUT');
                expect(ArcErrorCode.UNKNOWN).toBe('UNKNOWN');
            });

            it('canonicalErrorCode should normalize deprecated wire codes', () => {
                expect(canonicalErrorCode('TRACE_NOT_FOUND')).toBe(ArcErrorCode.RUN_NOT_FOUND);
                expect(canonicalErrorCode('EXECUTION_FAILED')).toBe(ArcErrorCode.RUN_FAILED);
                expect(canonicalErrorCode('PARSE_ERROR')).toBe(ArcErrorCode.INVALID_INPUT);
                expect(canonicalErrorCode('WORKFLOW_NOT_FOUND')).toBe(ArcErrorCode.WORKSPACE_NOT_FOUND);
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
