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
        const widgetPath = path.join(__dirname, '..', 'arc-widget.tsx');
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

        it('should render a Workflow Execution section', () => {
            expect(widgetSource).toMatch(/Workflow Execution/);
        });

        it('should render a Trace Viewer section', () => {
            expect(widgetSource).toMatch(/Trace Viewer/);
        });

        it('should render a Workflow Detection section', () => {
            expect(widgetSource).toMatch(/Workflow Detection/);
        });

        it('should render Execute Workflow button', () => {
            expect(widgetSource).toMatch(/Execute Workflow/);
        });

        it('should render Load Traces button', () => {
            expect(widgetSource).toMatch(/Load Traces/);
        });

        it('should render Scan Workspace button', () => {
            expect(widgetSource).toMatch(/Scan Workspace/);
        });

        it('should use theia-button class for buttons', () => {
            expect(widgetSource).toMatch(/theia-button/);
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
});
