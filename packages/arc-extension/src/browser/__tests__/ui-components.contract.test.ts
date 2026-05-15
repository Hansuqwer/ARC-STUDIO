/**
 * UI Components Contract Tests
 *
 * Tests for the reusable UI component modules.
 * Follows the same source-pattern approach as arc-widget.integration.test.ts.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('UI Components Contracts', () => {
    // Reads TSX source directly; update this if src/ or the compiled outDir changes.
    const componentsDir = path.join(__dirname, '..', '..', '..', 'src', 'browser', 'components');

    describe('ProgressBar', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'ProgressBar.tsx'), 'utf-8');
        });

        it('should export ProgressBarProps interface', () => {
            expect(source).toMatch(/export interface ProgressBarProps/);
        });

        it('should have value and optional label props', () => {
            expect(source).toMatch(/value:\s*number/);
            expect(source).toMatch(/label\??:\s*string/);
        });

        it('should render a progress container with role', () => {
            expect(source).toMatch(/arc-progress-container/);
            expect(source).toMatch(/role='progressbar'/);
        });

        it('should show label conditionally', () => {
            expect(source).toMatch(/label &&/);
            expect(source).toMatch(/arc-progress-label/);
        });
    });

    describe('ToastContainer', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'ToastContainer.tsx'), 'utf-8');
        });

        it('should export ToastNotification interface', () => {
            expect(source).toMatch(/export interface ToastNotification/);
        });

        it('should export ToastContainerProps interface', () => {
            expect(source).toMatch(/export interface ToastContainerProps/);
        });

        it('should render toast container region', () => {
            expect(source).toMatch(/arc-toast-container/);
            expect(source).toMatch(/role='region'/);
        });

        it('should support dismiss callback', () => {
            expect(source).toMatch(/onDismiss/);
        });

        it('should support multiple toast types', () => {
            expect(source).toMatch(/'success'/);
            expect(source).toMatch(/'error'/);
            expect(source).toMatch(/'warning'/);
            expect(source).toMatch(/'info'/);
        });
    });

    describe('ShortcutsModal', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'ShortcutsModal.tsx'), 'utf-8');
        });

        it('should export ShortcutsModalProps interface', () => {
            expect(source).toMatch(/export interface ShortcutsModalProps/);
        });

        it('should have isOpen and onClose props', () => {
            expect(source).toMatch(/isOpen:\s*boolean/);
            expect(source).toMatch(/onClose:\s*\(\)\s*=>\s*void/);
        });

        it('should render as modal dialog when open', () => {
            expect(source).toMatch(/role='dialog'/);
            expect(source).toMatch(/aria-modal='true'/);
        });

        it('should render keyboard shortcuts table', () => {
            expect(source).toMatch(/Keyboard Shortcuts/);
            expect(source).toMatch(/Ctrl\+E/);
            expect(source).toMatch(/⌘\+E/);
        });

        it('should return null when not open', () => {
            expect(source).toMatch(/if\s*\(!isOpen\)/);
            expect(source).toMatch(/return null/);
        });

        it('should close on overlay click', () => {
            expect(source).toMatch(/e\.target === e\.currentTarget/);
            expect(source).toMatch(/onClose/);
        });
    });

    describe('ExecutionSteps', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'ExecutionSteps.tsx'), 'utf-8');
        });

        it('should export ProgressStep interface', () => {
            expect(source).toMatch(/export interface ProgressStep/);
        });

        it('should support all step statuses', () => {
            expect(source).toMatch(/'pending'/);
            expect(source).toMatch(/'in-progress'/);
            expect(source).toMatch(/'completed'/);
            expect(source).toMatch(/'failed'/);
        });

        it('should render nothing for empty steps', () => {
            expect(source).toMatch(/steps\.length === 0/);
            expect(source).toMatch(/return null/);
        });

        it('should render steps with status classes', () => {
            expect(source).toMatch(/arc-step /);
            expect(source).toMatch(/arc-step-\$\{step\.status\}/);
        });

        it('should indicate current step', () => {
            expect(source).toMatch(/aria-current/);
        });
    });

    describe('ErrorBanner', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'ErrorBanner.tsx'), 'utf-8');
        });

        it('should export ErrorBannerProps interface', () => {
            expect(source).toMatch(/export interface ErrorBannerProps/);
        });

        it('should have error, errorDetails, onRetry props', () => {
            expect(source).toMatch(/error\??:\s*string/);
            expect(source).toMatch(/errorDetails\??:\s*string/);
            expect(source).toMatch(/onRetry:\s*\(\)\s*=>\s*void/);
        });

        it('should return null when no error', () => {
            expect(source).toMatch(/if\s*\(!error\)/);
            expect(source).toMatch(/return null/);
        });

        it('should render error with retry button', () => {
            expect(source).toMatch(/arc-error/);
            expect(source).toMatch(/Try Again/);
        });
    });

    describe('WorkflowExecutionSection', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'WorkflowExecutionSection.tsx'), 'utf-8');
        });

        it('should export WorkflowExecutionSectionProps interface', () => {
            expect(source).toMatch(/export interface WorkflowExecutionSectionProps/);
        });

        it('should have execution-related props', () => {
            expect(source).toMatch(/isExecuting/);
            expect(source).toMatch(/executionStatus/);
            expect(source).toMatch(/onExecute/);
        });

        it('should render execution section heading', () => {
            expect(source).toMatch(/Workflow Execution/);
        });

        it('should render prompt input', () => {
            expect(source).toMatch(/prompt-input/);
            expect(source).toMatch(/Enter workflow prompt/);
        });

        it('should render execute button', () => {
            expect(source).toMatch(/Execute Workflow/);
            expect(source).toMatch(/theia-button primary/);
        });
    });

    describe('TraceViewerSection', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'TraceViewerSection.tsx'), 'utf-8');
        });

        it('should export TraceViewerSectionProps interface', () => {
            expect(source).toMatch(/export interface TraceViewerSectionProps/);
        });

        it('should have trace-related props', () => {
            expect(source).toMatch(/isLoadingTraces/);
            expect(source).toMatch(/selectedTrace/);
            expect(source).toMatch(/onLoadTraces/);
        });

        it('should render trace viewer section heading', () => {
            expect(source).toMatch(/Trace Viewer/);
        });

        it('should render filter input', () => {
            expect(source).toMatch(/trace-filter/);
            expect(source).toMatch(/Filter by ID/);
        });

        it('should render load traces button', () => {
            expect(source).toMatch(/Load Traces/);
        });
    });

    describe('WorkflowDetectionSection', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'WorkflowDetectionSection.tsx'), 'utf-8');
        });

        it('should export WorkflowDetectionSectionProps interface', () => {
            expect(source).toMatch(/export interface WorkflowDetectionSectionProps/);
        });

        it('should have scan-related props', () => {
            expect(source).toMatch(/isScanning/);
            expect(source).toMatch(/scanProgress/);
            expect(source).toMatch(/onScanWorkspace/);
        });

        it('should render workflow detection section heading', () => {
            expect(source).toMatch(/Workflow Detection/);
        });

        it('should render scan button', () => {
            expect(source).toMatch(/Scan Workspace/);
        });
    });

    describe('ArcAdaptersWidget', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-adapters-widget.tsx'), 'utf-8');
    });

    it('should be an injectable ReactWidget', () => {
        expect(source).toMatch(/@injectable/);
        expect(source).toMatch(/extends ReactWidget/);
    });

    it('should have static ID and LABEL', () => {
        expect(source).toMatch(/static readonly ID/);
        expect(source).toMatch(/static readonly LABEL/);
    });

    it('should inject ArcService', () => {
        expect(source).toMatch(/@inject\(ArcService\)/);
    });

    it('should render runtime readiness heading', () => {
        expect(source).toMatch(/Runtime Readiness/);
    });

    it('should render Refresh button', () => {
        expect(source).toMatch(/Refresh/);
    });

    it('should render capability cards', () => {
        expect(source).toMatch(/renderCard/);
        expect(source).toMatch(/runtime_id/);
    });

    it('should render doctor action buttons', () => {
        expect(source).toMatch(/doctor_actions/);
        expect(source).toMatch(/runDoctorAction/);
    });

    it('should render confirm dialog for unsafe actions', () => {
        expect(source).toMatch(/confirmAction/);
        expect(source).toMatch(/renderConfirmDialog/);
    });
});

describe('ArcAdaptersContribution', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-adapters-contribution.ts'), 'utf-8');
    });

    it('should be injectable', () => {
        expect(source).toMatch(/@injectable/);
    });

    it('should extend AbstractViewContribution', () => {
        expect(source).toMatch(/extends AbstractViewContribution/);
    });

    it('should have open adapters command', () => {
        expect(source).toMatch(/arc:open-adapters/);
    });
});

describe('ArcWorkflowGraphWidget', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-workflow-graph-widget.tsx'), 'utf-8');
    });

    it('should be an injectable ReactWidget', () => {
        expect(source).toMatch(/@injectable/);
        expect(source).toMatch(/extends ReactWidget/);
    });

    it('should inject ArcService', () => {
        expect(source).toMatch(/@inject\(ArcService\)/);
    });

    it('should use existing workflow detection RPC', () => {
        expect(source).toMatch(/detectWorkflows/);
    });

    it('should render unavailable topology honestly', () => {
        expect(source).toMatch(/Topology metadata is not available yet/);
    });

    it('should include graph layout helpers', () => {
        expect(source).toMatch(/computeLayout/);
        expect(source).toMatch(/nodeColor/);
    });
});

describe('ArcWorkflowContribution', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-workflow-contribution.ts'), 'utf-8');
    });

    it('should register workflow graph command', () => {
        expect(source).toMatch(/arc:open-workflow-graph/);
        expect(source).toMatch(/ArcWorkflowGraphWidget\.ID/);
    });
});

describe('ArcRunTimelineWidget', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-run-timeline-widget.tsx'), 'utf-8');
    });

    it('should be an injectable ReactWidget', () => {
        expect(source).toMatch(/@injectable/);
        expect(source).toMatch(/extends ReactWidget/);
    });

    it('should use trace-backed RPC methods', () => {
        expect(source).toMatch(/getTraces/);
        expect(source).toMatch(/readTrace/);
    });

    it('should render HITL event markers', () => {
        expect(source).toMatch(/HITL_PROMPT/);
        expect(source).toMatch(/HITL_RESPONSE/);
        expect(source).toMatch(/HITL_TIMEOUT/);
    });

    it('should support event filtering and selected event details', () => {
        expect(source).toMatch(/eventFilter/);
        expect(source).toMatch(/selectedEvent/);
        expect(source).toMatch(/filteredEvents/);
    });
});

describe('ArcRunsContribution', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-runs-contribution.ts'), 'utf-8');
    });

    it('should register run timeline command', () => {
        expect(source).toMatch(/arc:open-run-timeline/);
        expect(source).toMatch(/ArcRunTimelineWidget\.ID/);
    });
});

describe('ArcEventStreamWidget', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-event-stream-widget.tsx'), 'utf-8');
    });

    it('should be an injectable ReactWidget', () => {
        expect(source).toMatch(/@injectable/);
        expect(source).toMatch(/extends ReactWidget/);
    });

    it('should render trace-backed events without claiming live SSE', () => {
        expect(source).toMatch(/getTraces/);
        expect(source).toMatch(/readTrace/);
        expect(source).toMatch(/trace-backed renderer/);
    });

    it('should support event type chips and text filtering', () => {
        expect(source).toMatch(/selectedEventTypes/);
        expect(source).toMatch(/getFilteredEvents/);
        expect(source).toMatch(/Filter text or event type/);
    });

    it('should render event details panel', () => {
        expect(source).toMatch(/renderDetails/);
        expect(source).toMatch(/selectedEvent/);
    });
});

describe('ArcEventStreamContribution', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-event-stream-contribution.ts'), 'utf-8');
    });

    it('should register event stream command', () => {
        expect(source).toMatch(/arc:open-event-stream/);
        expect(source).toMatch(/ArcEventStreamWidget\.ID/);
    });
});

describe('index exports', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'index.ts'), 'utf-8');
        });

        it('should export ProgressBar', () => {
            expect(source).toMatch(/export.*ProgressBar/);
        });

        it('should export ToastContainer', () => {
            expect(source).toMatch(/export.*ToastContainer/);
        });

        it('should export ShortcutsModal', () => {
            expect(source).toMatch(/export.*ShortcutsModal/);
        });

        it('should export ExecutionSteps', () => {
            expect(source).toMatch(/export.*ExecutionSteps/);
        });

        it('should export ErrorBanner', () => {
            expect(source).toMatch(/export.*ErrorBanner/);
        });

        it('should export WorkflowExecutionSection', () => {
            expect(source).toMatch(/export.*WorkflowExecutionSection/);
        });

        it('should export TraceViewerSection', () => {
            expect(source).toMatch(/export.*TraceViewerSection/);
        });

        it('should export WorkflowDetectionSection', () => {
            expect(source).toMatch(/export.*WorkflowDetectionSection/);
        });
    });
});
