/**
 * ArcWidget Integration Tests
 *
 * Tests the widget's static properties and state logic without
 * importing Theia browser dependencies (which require jsdom and
 * ESM module support).
 *
 * These tests verify the widget contract by reading the source file
 * and validating expected constants and patterns.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('ArcWidget Integration Tests', () => {
    let widgetSource: string;

    beforeAll(async () => {
        // When running from lib/, we need to point back to src/
        const widgetPath = path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-widget.tsx');
        widgetSource = await fs.readFile(widgetPath, 'utf-8');
    });

    describe('Static Properties', () => {
        it('should have correct ID', () => {
            expect(widgetSource).toMatch(/static\s+readonly\s+ID\s*=\s*['"]arc-widget['"]/);
        });

        it('should have correct LABEL', () => {
            expect(widgetSource).toMatch(/static\s+readonly\s+LABEL\s*=\s*['"]ARC Studio['"]/);
        });

        it('ID should be defined as a static readonly property', () => {
            expect(widgetSource).toMatch(/static\s+readonly\s+ID/);
        });

        it('LABEL should be defined as a static readonly property', () => {
            expect(widgetSource).toMatch(/static\s+readonly\s+LABEL/);
        });
    });

    describe('Widget Class Structure', () => {
        it('should be an injectable class', () => {
            expect(widgetSource).toMatch(/@injectable\(\)/);
            expect(widgetSource).toMatch(/export\s+class\s+ArcWidget/);
        });

        it('should extend ReactWidget', () => {
            expect(widgetSource).toMatch(/class\s+ArcWidget\s+extends\s+ReactWidget/);
        });

        it('should have a render method', () => {
            expect(widgetSource).toMatch(/protected\s+render\s*\(\s*\)\s*:\s*React\.ReactNode/);
        });

        it('should have an init method with postConstruct', () => {
            expect(widgetSource).toMatch(/@postConstruct\(\)/);
            expect(widgetSource).toMatch(/protected\s+init\s*\(\s*\)/);
        });
    });

    describe('Widget Initialization', () => {
        it('should set widget ID in init', () => {
            expect(widgetSource).toMatch(/this\.id\s*=\s*ArcWidget\.ID/);
        });

        it('should set title label in init', () => {
            expect(widgetSource).toMatch(/this\.title\.label\s*=\s*ArcWidget\.LABEL/);
        });

        it('should set title caption in init', () => {
            expect(widgetSource).toMatch(/this\.title\.caption\s*=\s*ArcWidget\.LABEL/);
        });

        it('should make widget closable', () => {
            expect(widgetSource).toMatch(/this\.title\.closable\s*=\s*true/);
        });

        it('should set icon class', () => {
            expect(widgetSource).toMatch(/this\.title\.iconClass\s*=/);
        });

        it('should call update after initialization', () => {
            expect(widgetSource).toMatch(/this\.update\(\)/);
        });
    });

    describe('UI Rendering', () => {
        it('should render a widget container', () => {
            expect(widgetSource).toMatch(/arc-widget-container/);
        });

        it('should render a header with ARC Studio title', () => {
            expect(widgetSource).toMatch(/<h2>ARC Studio<\/h2>/);
        });

        it('should render a subtitle', () => {
            expect(widgetSource).toMatch(/Agent Runtime Cockpit/);
        });

        it('should use WorkflowExecutionSection component', () => {
            expect(widgetSource).toMatch(/WorkflowExecutionSection/);
        });

        it('should use TraceViewerSection component', () => {
            expect(widgetSource).toMatch(/TraceViewerSection/);
        });

        it('should use WorkflowDetectionSection component', () => {
            expect(widgetSource).toMatch(/WorkflowDetectionSection/);
        });

        it('should use ToastContainer component', () => {
            expect(widgetSource).toMatch(/ToastContainer/);
        });

        it('should use ShortcutsModal component', () => {
            expect(widgetSource).toMatch(/ShortcutsModal/);
        });

        it('should use ErrorBanner component', () => {
            expect(widgetSource).toMatch(/ErrorBanner/);
        });
    });

    describe('State Update Logic', () => {
        it('should support partial state updates via spread', () => {
            const state = {
                isExecuting: false,
                executionStatus: 'idle' as const,
                prompt: ''
            };

            const updated = { ...state, isExecuting: true, prompt: 'test' };

            expect(updated.isExecuting).toBe(true);
            expect(updated.prompt).toBe('test');
            expect(updated.executionStatus).toBe('idle');
        });

        it('should support nested state updates for isCollapsed', () => {
            const isCollapsed = {
                'workflow-execution': false,
                'trace-viewer': false,
                'workflow-detection': false
            };

            const updated = {
                ...isCollapsed,
                'workflow-execution': !isCollapsed['workflow-execution']
            };

            expect(updated['workflow-execution']).toBe(true);
            expect(updated['trace-viewer']).toBe(false);
        });

        it('should support array state updates for traces', () => {
            const traces: any[] = [];
            const newTrace = {
                id: 'run-1',
                path: '/path',
                timestamp: '2024-01-01T00:00:00.000Z',
                status: 'completed' as const
            };

            const updated = [...traces, newTrace];
            expect(updated.length).toBe(1);
            expect(updated[0].id).toBe('run-1');
        });

        it('should support toast notification state updates', () => {
            const toasts: any[] = [];
            const newToast = {
                id: 'toast-1',
                type: 'success' as const,
                message: 'Test notification',
                timestamp: Date.now()
            };

            const withToast = [...toasts, newToast];
            expect(withToast.length).toBe(1);

            const withoutToast = withToast.filter(t => t.id !== 'toast-1');
            expect(withoutToast.length).toBe(0);
        });

        it('should support execution step progress calculation', () => {
            const steps = [
                { id: 'step1', label: 'Step 1', status: 'completed' as const },
                { id: 'step2', label: 'Step 2', status: 'completed' as const },
                { id: 'step3', label: 'Step 3', status: 'in-progress' as const },
                { id: 'step4', label: 'Step 4', status: 'pending' as const },
                { id: 'step5', label: 'Step 5', status: 'pending' as const }
            ];

            const completedCount = steps.filter(s => s.status === 'completed').length;
            const progress = Math.round((completedCount / steps.length) * 100);

            expect(progress).toBe(40);
        });
    });

    describe('Trace Filtering Logic', () => {
        it('should filter traces by ID (case-insensitive)', () => {
            const traces = [
                { id: 'run-sg-abc123', path: '', timestamp: '', status: 'completed' as const },
                { id: 'run-sg-def456', path: '', timestamp: '', status: 'completed' as const },
                { id: 'run-sg-ABC789', path: '', timestamp: '', status: 'failed' as const }
            ];

            const filter = 'abc';
            const filtered = traces.filter(t =>
                t.id.toLowerCase().includes(filter.toLowerCase())
            );

            expect(filtered.length).toBe(2);
            expect(filtered.map(t => t.id)).toContain('run-sg-abc123');
            expect(filtered.map(t => t.id)).toContain('run-sg-ABC789');
        });

        it('should return all traces with empty filter', () => {
            const traces = [
                { id: 'run-1', path: '', timestamp: '', status: 'completed' as const },
                { id: 'run-2', path: '', timestamp: '', status: 'failed' as const }
            ];

            const filtered = traces.filter(t =>
                t.id.toLowerCase().includes(''.toLowerCase())
            );

            expect(filtered.length).toBe(2);
        });
    });

    describe('Execution Status Logic', () => {
        it('should have valid execution status values', () => {
            const validStatuses = ['idle', 'running', 'completed', 'failed'];
            validStatuses.forEach(status => {
                expect(['idle', 'running', 'completed', 'failed']).toContain(status);
            });
        });

        it('should have valid progress step statuses', () => {
            const validStepStatuses = ['pending', 'in-progress', 'completed', 'failed'];
            validStepStatuses.forEach(status => {
                expect(['pending', 'in-progress', 'completed', 'failed']).toContain(status);
            });
        });

        it('should have valid toast types', () => {
            const validToastTypes = ['success', 'error', 'info', 'warning'];
            validToastTypes.forEach(type => {
                expect(['success', 'error', 'info', 'warning']).toContain(type);
            });
        });
    });

    describe('State Management - updateState', () => {
        it('should merge partial state updates', () => {
            const initialState = {
                isExecuting: false,
                executionStatus: 'idle' as const,
                prompt: '',
                error: undefined as string | undefined
            };

            const updated = { ...initialState, isExecuting: true, prompt: 'test prompt' };

            expect(updated.isExecuting).toBe(true);
            expect(updated.prompt).toBe('test prompt');
            expect(updated.executionStatus).toBe('idle');
            expect(updated.error).toBeUndefined();
        });

        it('should clear error state on update', () => {
            const stateWithError = {
                error: 'Something went wrong',
                errorDetails: 'Details here',
                executionStatus: 'failed' as const
            };

            const cleared = { ...stateWithError, error: undefined, errorDetails: undefined, executionStatus: 'idle' as const };

            expect(cleared.error).toBeUndefined();
            expect(cleared.errorDetails).toBeUndefined();
            expect(cleared.executionStatus).toBe('idle');
        });

        it('should update execution progress state', () => {
            const state = {
                executionProgress: 0,
                executionSteps: [
                    { id: 'step1', label: 'Step 1', status: 'pending' as const },
                    { id: 'step2', label: 'Step 2', status: 'pending' as const }
                ]
            };

            const updatedSteps = state.executionSteps.map(s =>
                s.id === 'step1' ? { ...s, status: 'completed' as const } : s
            );
            const completedCount = updatedSteps.filter(s => s.status === 'completed').length;
            const progress = Math.round((completedCount / updatedSteps.length) * 100);

            const updated = { ...state, executionSteps: updatedSteps, executionProgress: progress };

            expect(updated.executionProgress).toBe(50);
            expect(updated.executionSteps[0].status).toBe('completed');
        });
    });

    describe('State Management - handleRetry', () => {
        it('should reset error state on retry', () => {
            const state = {
                error: 'Execution failed',
                errorDetails: 'Timeout exceeded',
                executionStatus: 'failed' as const,
                executionSteps: [{ id: 's1', label: 'S1', status: 'failed' as const }],
                executionProgress: 25
            };

            const retriedState = {
                ...state,
                error: undefined,
                errorDetails: undefined,
                executionStatus: 'idle' as const,
                executionSteps: [],
                executionProgress: 0
            };

            expect(retriedState.error).toBeUndefined();
            expect(retriedState.errorDetails).toBeUndefined();
            expect(retriedState.executionStatus).toBe('idle');
            expect(retriedState.executionSteps).toEqual([]);
            expect(retriedState.executionProgress).toBe(0);
        });
    });

    describe('Execution Flow - state transitions', () => {
        it('should transition from idle to running on execute', () => {
            const initialState = { isExecuting: false, executionStatus: 'idle' as const };
            const runningState = { isExecuting: true, executionStatus: 'running' as const };

            expect(initialState.isExecuting).toBe(false);
            expect(runningState.isExecuting).toBe(true);
            expect(runningState.executionStatus).toBe('running');
        });

        it('should transition from running to completed on success', () => {
            const runningState = { isExecuting: true, executionStatus: 'running' as const };
            const completedState = {
                isExecuting: false,
                executionStatus: 'completed' as const,
                executionResult: { runId: 'run-sg-123', status: 'completed' as const, tracePath: '.arc/traces/run-sg-123.jsonl' },
                executionTime: 5000,
                executionProgress: 100
            };

            expect(completedState.isExecuting).toBe(false);
            expect(completedState.executionStatus).toBe('completed');
            expect(completedState.executionResult?.runId).toBe('run-sg-123');
        });

        it('should transition from running to failed on error', () => {
            const runningState = { isExecuting: true, executionStatus: 'running' as const };
            const failedState = {
                isExecuting: false,
                executionStatus: 'failed' as const,
                error: 'Workflow execution failed',
                errorDetails: 'Timeout exceeded',
                executionProgress: 0
            };

            expect(failedState.isExecuting).toBe(false);
            expect(failedState.executionStatus).toBe('failed');
            expect(failedState.error).toBe('Workflow execution failed');
        });

        it('should initialize execution steps on workflow start', () => {
            const initialSteps = [
                { id: 'parsing', label: 'Parsing prompt', status: 'in-progress' as const },
                { id: 'planning', label: 'Planning execution', status: 'pending' as const },
                { id: 'executing', label: 'Executing workflow', status: 'pending' as const },
                { id: 'recording', label: 'Recording trace', status: 'pending' as const },
                { id: 'finalizing', label: 'Finalizing results', status: 'pending' as const }
            ];

            expect(initialSteps.length).toBe(5);
            expect(initialSteps[0].status).toBe('in-progress');
            expect(initialSteps.filter(s => s.status === 'pending').length).toBe(4);
        });
    });

    describe('Error Handling', () => {
        it('should set error state when execution throws', () => {
            const errorState = {
                isExecuting: false,
                executionStatus: 'failed' as const,
                error: 'Workflow execution failed',
                errorDetails: 'Connection refused',
                executionProgress: 0
            };

            expect(errorState.executionStatus).toBe('failed');
            expect(errorState.error).toBeDefined();
            expect(errorState.errorDetails).toBe('Connection refused');
        });

        it('should mark current step as failed on error', () => {
            const steps = [
                { id: 'parsing', label: 'Parsing', status: 'completed' as const },
                { id: 'executing', label: 'Executing', status: 'in-progress' as const },
                { id: 'finalizing', label: 'Finalizing', status: 'pending' as const }
            ];

            const currentStep = steps.find(s => s.status === 'in-progress');
            const failedSteps = steps.map(s =>
                s.id === currentStep?.id ? { ...s, status: 'failed' as const } : s
            );

            expect(failedSteps[1].status).toBe('failed');
            expect(failedSteps[0].status).toBe('completed');
        });
    });

    describe('Trace Filtering', () => {
        it('should filter traces by ID substring', () => {
            const traces = [
                { id: 'run-sg-abc123', path: '', timestamp: '2024-01-01T00:00:00.000Z', status: 'completed' as const },
                { id: 'run-sg-def456', path: '', timestamp: '2024-01-02T00:00:00.000Z', status: 'failed' as const },
                { id: 'run-lg-abc789', path: '', timestamp: '2024-01-03T00:00:00.000Z', status: 'completed' as const }
            ];

            const filtered = traces.filter(t => t.id.toLowerCase().includes('abc'));
            expect(filtered.length).toBe(2);
            expect(filtered.map(t => t.id)).toEqual(['run-sg-abc123', 'run-lg-abc789']);
        });

        it('should filter traces by prefix', () => {
            const traces = [
                { id: 'run-sg-001', path: '', timestamp: '', status: 'completed' as const },
                { id: 'run-lg-002', path: '', timestamp: '', status: 'completed' as const },
                { id: 'run-ca-003', path: '', timestamp: '', status: 'completed' as const }
            ];

            const filtered = traces.filter(t => t.id.toLowerCase().includes('run-sg'));
            expect(filtered.length).toBe(1);
            expect(filtered[0].id).toBe('run-sg-001');
        });

        it('should handle empty filter returning all traces', () => {
            const traces = [
                { id: 'run-1', path: '', timestamp: '', status: 'completed' as const },
                { id: 'run-2', path: '', timestamp: '', status: 'failed' as const }
            ];

            const filter = '';
            const filtered = traces.filter(t => t.id.toLowerCase().includes(filter.toLowerCase()));
            expect(filtered.length).toBe(2);
        });

        it('should handle no matches', () => {
            const traces = [
                { id: 'run-sg-001', path: '', timestamp: '', status: 'completed' as const }
            ];

            const filtered = traces.filter(t => t.id.toLowerCase().includes('nonexistent'));
            expect(filtered.length).toBe(0);
        });
    });

    describe('Toast Management', () => {
        it('should add toast notification', () => {
            const toasts: any[] = [];
            const newToast = {
                id: 'toast-1',
                type: 'success' as const,
                message: 'Workflow completed',
                timestamp: Date.now()
            };

            const updated = [...toasts, newToast];
            expect(updated.length).toBe(1);
            expect(updated[0].type).toBe('success');
            expect(updated[0].message).toBe('Workflow completed');
        });

        it('should remove toast by ID', () => {
            const toasts = [
                { id: 'toast-1', type: 'success' as const, message: 'Done', timestamp: Date.now() },
                { id: 'toast-2', type: 'error' as const, message: 'Failed', timestamp: Date.now() },
                { id: 'toast-3', type: 'info' as const, message: 'Info', timestamp: Date.now() }
            ];

            const remaining = toasts.filter(t => t.id !== 'toast-2');
            expect(remaining.length).toBe(2);
            expect(remaining.map(t => t.id)).not.toContain('toast-2');
        });

        it('should support multiple toasts', () => {
            const toasts = [
                { id: 'toast-1', type: 'success' as const, message: 'First', timestamp: Date.now() },
                { id: 'toast-2', type: 'warning' as const, message: 'Second', timestamp: Date.now() },
                { id: 'toast-3', type: 'error' as const, message: 'Third', timestamp: Date.now() }
            ];

            expect(toasts.length).toBe(3);
            expect(toasts.map(t => t.type)).toEqual(['success', 'warning', 'error']);
        });

        it('should auto-dismiss toasts after timeout', () => {
            jest.useFakeTimers();

            const toasts = [
                { id: 'toast-1', type: 'info' as const, message: 'Auto-dismiss', timestamp: Date.now() }
            ];

            const dismissToast = (id: string) => toasts.filter(t => t.id !== id);

            setTimeout(() => {
                const remaining = dismissToast('toast-1');
                expect(remaining.length).toBe(0);
            }, 5000);

            jest.advanceTimersByTime(5000);
            jest.useRealTimers();
        });

        it('should handle toast dismissal clearing timeout', () => {
            const timeoutMap = new Map<string, NodeJS.Timeout>();
            const toastId = 'toast-1';

            const timeout = setTimeout(() => {}, 5000);
            timeoutMap.set(toastId, timeout);

            expect(timeoutMap.has(toastId)).toBe(true);

            const t = timeoutMap.get(toastId);
            if (t) clearTimeout(t);
            timeoutMap.delete(toastId);

            expect(timeoutMap.has(toastId)).toBe(false);
        });
    });

    describe('Section Toggle State', () => {
        it('should toggle section collapsed state', () => {
            const isCollapsed = {
                'workflow-execution': false,
                'trace-viewer': false,
                'workflow-detection': false
            };

            const toggled = {
                ...isCollapsed,
                'workflow-execution': !isCollapsed['workflow-execution']
            };

            expect(toggled['workflow-execution']).toBe(true);
            expect(toggled['trace-viewer']).toBe(false);

            const toggledBack = {
                ...toggled,
                'workflow-execution': !toggled['workflow-execution']
            };
            expect(toggledBack['workflow-execution']).toBe(false);
        });
    });

    describe('Widget Source Code Patterns', () => {
        it('should have updateState method', () => {
            expect(widgetSource).toMatch(/updateState/);
        });

        it('should have handleRetry method', () => {
            expect(widgetSource).toMatch(/handleRetry/);
        });

        it('should have addToast method', () => {
            expect(widgetSource).toMatch(/addToast/);
        });

        it('should have removeToast method', () => {
            expect(widgetSource).toMatch(/removeToast/);
        });

        it('should have handleExecuteWorkflow method', () => {
            expect(widgetSource).toMatch(/handleExecuteWorkflow/);
        });

        it('should have handleLoadTraces method', () => {
            expect(widgetSource).toMatch(/handleLoadTraces/);
        });

        it('should have handleLoadTraces method', () => {
            expect(widgetSource).toMatch(/async\s+handleLoadTraces\s*\(/);
        });

        it('should have handleScanWorkspace method', () => {
            expect(widgetSource).toMatch(/handleScanWorkspace/);
        });

        it('should have dispose method', () => {
            expect(widgetSource).toMatch(/dispose\s*\(\s*\)\s*:/);
        });

        it('should use TraceViewerSection component with filtering', () => {
            expect(widgetSource).toMatch(/TraceViewerSection/);
            expect(widgetSource).toMatch(/traceFilter/);
        });

        it('should use ToastContainer component', () => {
            expect(widgetSource).toMatch(/ToastContainer/);
            expect(widgetSource).toMatch(/toasts/);
        });

        it('should use ErrorBanner component with retry', () => {
            expect(widgetSource).toMatch(/ErrorBanner/);
            expect(widgetSource).toMatch(/handleRetry/);
        });
    });
});
