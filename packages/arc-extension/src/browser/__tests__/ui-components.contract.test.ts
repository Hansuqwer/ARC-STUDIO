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

describe('ArcHealthWidget', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-health-widget.tsx'), 'utf-8');
    });

    it('should be an injectable ReactWidget', () => {
        expect(source).toMatch(/@injectable/);
        expect(source).toMatch(/extends ReactWidget/);
    });

    it('should inject ArcService', () => {
        expect(source).toMatch(/@inject\(ArcService\)/);
    });

    it('should use canonical ARC service health signals', () => {
        expect(source).toMatch(/getConfigStatus/);
        expect(source).toMatch(/listRuntimeCapabilities/);
    });

    it('should poll and clear health refresh timer', () => {
        expect(source).toMatch(/setInterval/);
        expect(source).toMatch(/clearInterval/);
    });
});

describe('ArcHealthContribution', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-health-contribution.ts'), 'utf-8');
    });

    it('should register health monitor command', () => {
        expect(source).toMatch(/arc:open-health-monitor/);
        expect(source).toMatch(/ARC: Show Health Monitor/);
    });

    it('should support arc-view deep link', () => {
        expect(source).toMatch(/health-monitor/);
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

    it('should import and use CrossLinkState', () => {
        expect(source).toMatch(/CrossLinkState/);
        expect(source).toMatch(/crossLinkState/);
    });

    it('should initialize CrossLinkState with null selection', () => {
        expect(source).toMatch(/selectedNodeId:\s*null/);
        expect(source).toMatch(/highlightedMessageIds:\s*\[\]/);
        expect(source).toMatch(/highlightedEvidenceIds:\s*\[\]/);
        expect(source).toMatch(/highlightedToolCallIds:\s*\[\]/);
        expect(source).toMatch(/highlightedRunIds:\s*\[\]/);
    });

    it('should update CrossLinkState on node select', () => {
        expect(source).toMatch(/handleNodeSelect/);
        expect(source).toMatch(/selectedNodeId/);
        expect(source).toMatch(/highlightedMessageIds/);
        expect(source).toMatch(/highlightedEvidenceIds/);
        expect(source).toMatch(/highlightedToolCallIds/);
    });

    it('should support onNodeSelect callback', () => {
        expect(source).toMatch(/onNodeSelectCallback/);
        expect(source).toMatch(/setOnNodeSelect/);
    });

    it('should emit GraphNodeSelectionEvent with linked IDs', () => {
        expect(source).toMatch(/GraphNodeSelectionEvent/);
        expect(source).toMatch(/linkedMessageIds/);
        expect(source).toMatch(/linkedEvidenceIds/);
        expect(source).toMatch(/linkedToolCallIds/);
    });

    it('should handle degraded cross-link state without crash', () => {
        expect(source).toMatch(/DegradationManifest/);
        expect(source).toMatch(/degradationManifest/);
        expect(source).toMatch(/isDegraded/);
    });

    it('should show degraded indicator when cross-linking unavailable', () => {
        expect(source).toMatch(/Cross-linking degraded/);
        expect(source).toMatch(/missing node IDs/);
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
        expect(source).toMatch(/Advanced Trace/);
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

        it('should export RunContractCard', () => {
            expect(source).toMatch(/export.*RunContractCard/);
        });

        it('should export FailureAutopsyCard', () => {
            expect(source).toMatch(/export.*FailureAutopsyCard/);
        });

        it('should export EvidenceChip', () => {
            expect(source).toMatch(/export.*EvidenceChip/);
        });

        it('should export RunReceiptCard', () => {
            expect(source).toMatch(/export.*RunReceiptCard/);
        });

        it('should export CapabilityDiffViewer', () => {
            expect(source).toMatch(/export.*CapabilityDiffViewer/);
        });
    });

    describe('RunContractCard', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'RunContractCard.tsx'), 'utf-8');
        });

        it('should export RunContractCardProps interface', () => {
            expect(source).toMatch(/export interface RunContractCardProps/);
        });

        it('should have contract, onAccept, onEdit, onCancel props', () => {
            expect(source).toMatch(/contract:\s*RunContract/);
            expect(source).toMatch(/onAccept\?:\s*\(\)\s*=>\s*void/);
            expect(source).toMatch(/onEdit\?:\s*\(\)\s*=>\s*void/);
            expect(source).toMatch(/onCancel\?:\s*\(\)\s*=>\s*void/);
        });

        it('should render contract card with role region', () => {
            expect(source).toMatch(/arc-contract-card/);
            expect(source).toMatch(/role='region'/);
        });

        it('should render status badge with all contract statuses', () => {
            expect(source).toMatch(/proposed:/);
            expect(source).toMatch(/accepted:/);
            expect(source).toMatch(/fulfilled:/);
            expect(source).toMatch(/violated:/);
        });

        it('should render objective, runtime, mode, cost ceiling, rollback', () => {
            expect(source).toMatch(/objective/);
            expect(source).toMatch(/runtime/);
            expect(source).toMatch(/mode/);
            expect(source).toMatch(/cost_ceiling_usd/);
            expect(source).toMatch(/rollback_plan/);
        });

        it('should render allowed tools and write scope lists', () => {
            expect(source).toMatch(/allowed_tools/);
            expect(source).toMatch(/write_scope/);
            expect(source).toMatch(/arc-contract-list/);
        });

        it('should render action buttons only for proposed status', () => {
            expect(source).toMatch(/status === 'proposed'/);
            expect(source).toMatch(/Accept/);
            expect(source).toMatch(/Edit/);
            expect(source).toMatch(/Cancel/);
        });

        it('should include accessibility labels', () => {
            expect(source).toMatch(/aria-label/);
        });
    });

    describe('FailureAutopsyCard', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'FailureAutopsyCard.tsx'), 'utf-8');
        });

        it('should export FailureAutopsyCardProps interface', () => {
            expect(source).toMatch(/export interface FailureAutopsyCardProps/);
        });

        it('should have autopsy, onRetry, onOpenDoctor, onOpenEvidence props', () => {
            expect(source).toMatch(/autopsy:\s*FailureAutopsy/);
            expect(source).toMatch(/onRetry\?:/);
            expect(source).toMatch(/onOpenDoctor\?:/);
            expect(source).toMatch(/onOpenEvidence\?:/);
        });

        it('should have onSelectEvidence prop for structured events', () => {
            expect(source).toMatch(/onSelectEvidence\?:/);
            expect(source).toMatch(/EvidenceSelectionEvent/);
        });

        it('should render autopsy card as polite region', () => {
            expect(source).toMatch(/arc-autopsy-card/);
            expect(source).toMatch(/role='region'/);
            expect(source).toMatch(/aria-live='polite'/);
        });

        it('should render probable cause and confidence', () => {
            expect(source).toMatch(/probable_cause/);
            expect(source).toMatch(/confidence/);
        });

        it('should render knows and guesses sections separately', () => {
            expect(source).toMatch(/knows/);
            expect(source).toMatch(/guesses/);
            expect(source).toMatch(/Known/);
            expect(source).toMatch(/Guesses/);
        });

        it('should render retry options with risk levels', () => {
            expect(source).toMatch(/retry_options/);
            expect(source).toMatch(/low:/);
            expect(source).toMatch(/medium:/);
            expect(source).toMatch(/high:/);
        });

        it('should render evidence chips', () => {
            expect(source).toMatch(/EvidenceChip/);
            expect(source).toMatch(/evidence_refs/);
        });

        it('should pass onSelectEvidence to EvidenceChip', () => {
            expect(source).toMatch(/onSelect=\{onSelectEvidence\}/);
        });

        it('should include accessibility labels', () => {
            expect(source).toMatch(/aria-label/);
            expect(source).toMatch(/role='status'/);
        });
    });

    describe('EvidenceChip', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'EvidenceChip.tsx'), 'utf-8');
        });

        it('should export EvidenceChipProps interface', () => {
            expect(source).toMatch(/export interface EvidenceChipProps/);
        });

        it('should have evidenceRef and onOpen props', () => {
            expect(source).toMatch(/evidenceRef:\s*EvidenceRef/);
            expect(source).not.toMatch(/^\s*ref:\s*EvidenceRef/m);
            expect(source).toMatch(/onOpen:\s*\(ref:\s*EvidenceRef\)\s*=>\s*void/);
        });

        it('should have optional onSelect callback for structured events', () => {
            expect(source).toMatch(/onSelect\?:\s*\(event:\s*EvidenceSelectionEvent\)\s*=>\s*void/);
        });

        it('should import EvidenceSelectionEvent type', () => {
            expect(source).toMatch(/EvidenceSelectionEvent/);
        });

        it('should render chip as clickable button', () => {
            expect(source).toMatch(/arc-evidence-chip/);
        });

        it('should support all evidence kinds', () => {
            expect(source).toMatch(/file:/);
            expect(source).toMatch(/tool_output:/);
            expect(source).toMatch(/run:/);
            expect(source).toMatch(/node:/);
            expect(source).toMatch(/ledger:/);
            expect(source).toMatch(/receipt:/);
        });

        it('should handle redacted evidence', () => {
            expect(source).toMatch(/redacted/);
            expect(source).toMatch(/safeTarget = redacted \? '\[redacted\]' : target/);
            expect(source).toMatch(/displayLabel = redacted \? '\[redacted\]'/);
        });

        it('should rely on native button activation', () => {
            expect(source).toMatch(/<button/);
            expect(source).toMatch(/onClick/);
            expect(source).not.toMatch(/onKeyDown/);
        });

        it('should use text evidence markers', () => {
            expect(source).toMatch(/'\[F\]'/);
            expect(source).toMatch(/'\[T\]'/);
            expect(source).toMatch(/'\[R\]'/);
            expect(source).toMatch(/'\[N\]'/);
            expect(source).toMatch(/'\[L\]'/);
            expect(source).toMatch(/'\[RC\]'/);
        });

        it('should include accessibility labels', () => {
            expect(source).toMatch(/aria-label/);
        });

        it('should emit structured selection event on open', () => {
            expect(source).toMatch(/handleOpen/);
            expect(source).toMatch(/EvidenceSelectionEvent/);
            expect(source).toMatch(/chip-click/);
            expect(source).toMatch(/timestamp/);
        });

        it('should pass evidenceRef in selection event', () => {
            expect(source).toMatch(/evidenceRef,/);
        });
    });

    describe('RunReceiptCard', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'RunReceiptCard.tsx'), 'utf-8');
        });

        it('should export RunReceiptCardProps interface', () => {
            expect(source).toMatch(/export interface RunReceiptCardProps/);
        });

        it('should have receipt, onExport, onVerify, onOpenEvidence props', () => {
            expect(source).toMatch(/receipt:\s*RunReceipt/);
            expect(source).toMatch(/onExport\?:\s*\(\)\s*=>\s*void/);
            expect(source).toMatch(/onVerify\?:\s*\(\)\s*=>\s*void/);
            expect(source).toMatch(/onOpenEvidence\?:/);
        });

        it('should have onSelectEvidence prop for structured events', () => {
            expect(source).toMatch(/onSelectEvidence\?:/);
            expect(source).toMatch(/EvidenceSelectionEvent/);
        });

        it('should render receipt card with role region', () => {
            expect(source).toMatch(/arc-receipt-card/);
            expect(source).toMatch(/role='region'/);
        });

        it('should render all receipt statuses', () => {
            expect(source).toMatch(/completed:/);
            expect(source).toMatch(/failed:/);
            expect(source).toMatch(/cancelled:/);
        });

        it('should render summary, cost, duration, signature', () => {
            expect(source).toMatch(/summary/);
            expect(source).toMatch(/cost_usd/);
            expect(source).toMatch(/duration_ms/);
            expect(source).toMatch(/signature/);
        });

        it('should render files changed with diff', () => {
            expect(source).toMatch(/files_changed/);
            expect(source).toMatch(/arc-receipt-file__added/);
            expect(source).toMatch(/arc-receipt-file__removed/);
        });

        it('should render evidence chips', () => {
            expect(source).toMatch(/EvidenceChip/);
            expect(source).toMatch(/evidence_refs/);
        });

        it('should pass onSelectEvidence to EvidenceChip', () => {
            expect(source).toMatch(/onSelect=\{onSelectEvidence\}/);
        });

        it('should render unresolved risks and trust boundaries', () => {
            expect(source).toMatch(/unresolved_risks/);
            expect(source).toMatch(/trust_boundaries_crossed/);
        });

        it('should include accessibility labels', () => {
            expect(source).toMatch(/aria-label/);
        });
    });

    describe('CapabilityDiffViewer', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(componentsDir, 'CapabilityDiffViewer.tsx'), 'utf-8');
        });

        it('should export CapabilityDiffViewerProps interface', () => {
            expect(source).toMatch(/export interface CapabilityDiffViewerProps/);
        });

        it('should have diffResponse, loading, error props', () => {
            expect(source).toMatch(/diffResponse:\s*CapabilityDiffResponse\s*\|\s*null/);
            expect(source).toMatch(/loading\??:\s*boolean/);
            expect(source).toMatch(/error\??:\s*string/);
        });

        it('should have onConfirm, onCancel, onCompare callbacks', () => {
            expect(source).toMatch(/onConfirm\?/);
            expect(source).toMatch(/onCancel\?/);
            expect(source).toMatch(/onCompare\?/);
        });

        it('should have availableRuntimes prop', () => {
            expect(source).toMatch(/availableRuntimes:\s*string\[\]/);
        });

        it('should render runtime selector dropdowns', () => {
            expect(source).toMatch(/<select/);
            expect(source).toMatch(/Source runtime/);
            expect(source).toMatch(/Target runtime/);
        });

        it('should render Compare button', () => {
            expect(source).toMatch(/Compare/);
        });

        it('should render added capabilities with green indicator', () => {
            expect(source).toMatch(/Added Capabilities/);
            expect(source).toMatch(/charts-green/);
        });

        it('should render removed capabilities with red indicator', () => {
            expect(source).toMatch(/Removed Capabilities/);
            expect(source).toMatch(/editorError-foreground/);
        });

        it('should render changed flags with before/after values', () => {
            expect(source).toMatch(/Changed Flags/);
            expect(source).toMatch(/val\.before/);
            expect(source).toMatch(/val\.after/);
        });

        it('should render unknown/degraded for null capability values', () => {
            expect(source).toMatch(/unknown/);
            expect(source).toMatch(/degraded/);
            expect(source).toMatch(/isUnknown/);
        });

        it('should render trust boundary warning when widened', () => {
            expect(source).toMatch(/Trust Boundary Widens/);
            expect(source).toMatch(/trustBoundaryWidened/);
            expect(source).toMatch(/role="alert"/);
        });

        it('should render trust-sensitive flag indicators', () => {
            expect(source).toMatch(/trust-sensitive/);
            expect(source).toMatch(/trustSensitiveChanges/);
        });

        it('should require explicit confirmation when trust boundary widens', () => {
            expect(source).toMatch(/Confirm Switch/);
            expect(source).toMatch(/handleConfirm/);
            expect(source).toMatch(/confirmed/);
        });

        it('should render Cancel button for confirmation', () => {
            expect(source).toMatch(/Cancel/);
            expect(source).toMatch(/handleCancel/);
        });

        it('should show confirmed state after confirmation', () => {
            expect(source).toMatch(/Confirmed/);
            expect(source).toMatch(/if\s*\(\s*confirmed\s*\)/);
        });

        it('should show loading state', () => {
            expect(source).toMatch(/Computing capability diff/);
            expect(source).toMatch(/if\s*\(\s*loading\s*\)/);
        });

        it('should show error state', () => {
            expect(source).toMatch(/Diff error/);
        });

        it('should show no differences message', () => {
            expect(source).toMatch(/No capability differences detected/);
        });

        it('should reset confirmed state when diffResponse changes', () => {
            expect(source).toMatch(/useEffect/);
            expect(source).toMatch(/setConfirmed\(false\)/);
        });

        it('should include accessibility attributes', () => {
            expect(source).toMatch(/aria-label/);
            expect(source).toMatch(/aria-live/);
            expect(source).toMatch(/role="alert"/);
        });
    });
});

describe('ArcAdaptersWidget Capability Diff Integration', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-adapters-widget.tsx'), 'utf-8');
    });

    it('should import CapabilityDiffViewer', () => {
        expect(source).toMatch(/CapabilityDiffViewer/);
    });

    it('should import CapabilityDiffResponse type', () => {
        expect(source).toMatch(/CapabilityDiffResponse/);
    });

    it('should have diff state in widget state', () => {
        expect(source).toMatch(/diffLoading/);
        expect(source).toMatch(/diffResponse/);
        expect(source).toMatch(/diffError/);
    });

    it('should render CapabilityDiffViewer in widget', () => {
        expect(source).toMatch(/<CapabilityDiffViewer/);
    });

    it('should handle compare action', () => {
        expect(source).toMatch(/handleCompare/);
        expect(source).toMatch(/getCapabilityDiff/);
    });

    it('should handle diff confirm action', () => {
        expect(source).toMatch(/handleDiffConfirm/);
    });

    it('should handle diff cancel action', () => {
        expect(source).toMatch(/handleDiffCancel/);
    });

    it('should pass available runtimes to diff viewer', () => {
        expect(source).toMatch(/availableRuntimes/);
        expect(source).toMatch(/runtimeIds/);
    });
});

describe('CapabilityDiff Protocol Type', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(__dirname, '..', '..', '..', 'src', 'common', 'arc-protocol.ts'), 'utf-8');
    });

    it('should define CapabilityDiffResponse interface', () => {
        expect(source).toMatch(/export interface CapabilityDiffResponse/);
    });

    it('should have diff, fromRuntime, toRuntime fields', () => {
        expect(source).toMatch(/diff:\s*CapabilityDiff/);
        expect(source).toMatch(/fromRuntime:\s*string/);
        expect(source).toMatch(/toRuntime:\s*string/);
    });

    it('should have trustBoundaryWidened and trustSensitiveChanges', () => {
        expect(source).toMatch(/trustBoundaryWidened:\s*boolean/);
        expect(source).toMatch(/trustSensitiveChanges:\s*string\[\]/);
    });

    it('should define getCapabilityDiff on ArcService', () => {
        expect(source).toMatch(/getCapabilityDiff\s*\(\s*fromRuntime:\s*string\s*,\s*toRuntime:\s*string\s*\)/);
    });
});

describe('Advanced Trace Widgets (v0.1: not default-promoted, available via command)', () => {
    const browserDir = path.join(__dirname, '..', '..', '..', 'src', 'browser');

    describe('ArcRunTimelineWidget', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(browserDir, 'arc-run-timeline-widget.tsx'), 'utf-8');
        });

        it('should still export the widget class', () => {
            expect(source).toMatch(/export\s+class\s+ArcRunTimelineWidget/);
        });

        it('should have Advanced Trace label', () => {
            expect(source).toMatch(/Advanced Trace/);
        });

        it('should still be an injectable ReactWidget', () => {
            expect(source).toMatch(/@injectable/);
            expect(source).toMatch(/extends ReactWidget/);
        });
    });

    describe('ArcEventStreamWidget', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(browserDir, 'arc-event-stream-widget.tsx'), 'utf-8');
        });

        it('should still export the widget class', () => {
            expect(source).toMatch(/export\s+class\s+ArcEventStreamWidget/);
        });

        it('should have Advanced Trace label', () => {
            expect(source).toMatch(/Advanced Trace/);
        });

        it('should still be an injectable ReactWidget', () => {
            expect(source).toMatch(/@injectable/);
            expect(source).toMatch(/extends ReactWidget/);
        });
    });

    describe('ArcRunsContribution', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(browserDir, 'arc-runs-contribution.ts'), 'utf-8');
        });

        it('should have Advanced Trace in command label', () => {
            expect(source).toMatch(/Advanced Trace/);
        });
    });

    describe('ArcEventStreamContribution', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(browserDir, 'arc-event-stream-contribution.ts'), 'utf-8');
        });

        it('should have Advanced Trace in command label', () => {
            expect(source).toMatch(/Advanced Trace/);
        });
    });

    describe('Frontend Module does not default-promote trace widgets', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(browserDir, 'arc-extension-frontend-module.ts'), 'utf-8');
        });

        it('should NOT bind FrontendApplicationContribution for ArcRunsContribution', () => {
            const runsContributionSection = source.match(/ArcRunsContribution[\s\S]*?(?=ArcEventStreamContribution|$)/);
            expect(runsContributionSection).not.toBeNull();
            expect(runsContributionSection![0]).not.toMatch(/FrontendApplicationContribution.*ArcRunsContribution/);
        });

        it('should NOT bind FrontendApplicationContribution for ArcEventStreamContribution', () => {
            const eventStreamSection = source.match(/ArcEventStreamContribution[\s\S]*?(?=\}\);|$)/);
            expect(eventStreamSection).not.toBeNull();
            expect(eventStreamSection![0]).not.toMatch(/FrontendApplicationContribution.*ArcEventStreamContribution/);
        });

        it('should still bind ArcRunTimelineWidget factory', () => {
            expect(source).toMatch(/bind\(ArcRunTimelineWidget\)/);
            expect(source).toMatch(/id:\s*ArcRunTimelineWidget\.ID/);
        });

        it('should still bind ArcEventStreamWidget factory', () => {
            expect(source).toMatch(/bind\(ArcEventStreamWidget\)/);
            expect(source).toMatch(/id:\s*ArcEventStreamWidget\.ID/);
        });

        it('should still bind view contributions for trace widgets', () => {
            expect(source).toMatch(/bindViewContribution\(bind,\s*ArcRunsContribution\)/);
            expect(source).toMatch(/bindViewContribution\(bind,\s*ArcEventStreamContribution\)/);
        });
    });
});
