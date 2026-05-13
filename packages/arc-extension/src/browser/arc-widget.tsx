/**
 * ARC Widget
 * 
 * Main UI widget for ARC Studio showing workflow execution,
 * trace visualization, and SwarmGraph controls.
 */

import { injectable, postConstruct, inject } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { MessageService } from '@theia/core/lib/common/message-service';
import * as React from '@theia/core/shared/react';
import { ArcService, ExecutionResult, TraceFile, WorkflowInfo } from '../common/arc-protocol';
import {
    ToastContainer,
    ToastNotification,
    ShortcutsModal,
    ProgressStep,
    WorkflowExecutionSection,
    TraceViewerSection,
    WorkflowDetectionSection,
    ErrorBanner
} from './components';

interface ArcWidgetState {
    isExecuting: boolean;
    executionStatus: 'idle' | 'running' | 'completed' | 'failed';
    executionProgress: number;
    executionSteps: ProgressStep[];
    executionResult?: ExecutionResult;
    executionTime?: number;
    prompt: string;

    isLoadingTraces: boolean;
    traceProgress: number;
    traces: TraceFile[];
    selectedTrace?: TraceFile;
    traceFilter: string;

    isScanning: boolean;
    scanProgress: number;
    workflows: WorkflowInfo[];

    error?: string;
    errorDetails?: string;

    toasts: ToastNotification[];

    isCollapsed: Record<string, boolean>;
    showShortcutsHelp: boolean;
}

@injectable()
export class ArcWidget extends ReactWidget {

    static readonly ID = 'arc-widget';
    static readonly LABEL = 'ARC Studio';

    @inject(MessageService)
    protected readonly messageService!: MessageService;

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    private keyboardHandler: ((e: KeyboardEvent) => void) | undefined;
    private toastTimeouts = new Map<string, NodeJS.Timeout>();
    private filterDebounceTimer: NodeJS.Timeout | undefined;
    private pendingFilterValue = '';

    private state: ArcWidgetState = {
        isExecuting: false,
        executionStatus: 'idle',
        executionProgress: 0,
        executionSteps: [],
        prompt: '',
        isLoadingTraces: false,
        traceProgress: 0,
        traces: [],
        traceFilter: '',
        isScanning: false,
        scanProgress: 0,
        workflows: [],
        toasts: [],
        isCollapsed: {
            'workflow-execution': false,
            'trace-viewer': false,
            'workflow-detection': false
        },
        showShortcutsHelp: false
    };

    @postConstruct()
    protected init(): void {
        const startTime = performance.now();

        this.id = ArcWidget.ID;
        this.title.label = ArcWidget.LABEL;
        this.title.caption = ArcWidget.LABEL;
        this.title.closable = true;
        this.title.iconClass = 'fa fa-project-diagram';
        
        this.setupKeyboardShortcuts();
        
        this.update();

        const duration = performance.now() - startTime;
        console.log(`[ARC Performance] Widget initialization: ${duration.toFixed(2)}ms`);
    }

    dispose(): void {
        if (this.keyboardHandler) {
            this.node.removeEventListener('keydown', this.keyboardHandler);
            this.keyboardHandler = undefined;
        }
        this.toastTimeouts.forEach((timeout) => clearTimeout(timeout));
        this.toastTimeouts.clear();
        if (this.filterDebounceTimer) {
            clearTimeout(this.filterDebounceTimer);
            this.filterDebounceTimer = undefined;
        }
        super.dispose();
    }

    protected setupKeyboardShortcuts(): void {
        this.keyboardHandler = (e: KeyboardEvent) => {
            const isModifierPressed = e.ctrlKey || e.metaKey;
            
            if (isModifierPressed) {
                switch (e.key.toLowerCase()) {
                    case 'e':
                        e.preventDefault();
                        this.handleExecuteWorkflow();
                        break;
                    case 'l':
                        e.preventDefault();
                        this.handleLoadTraces();
                        break;
                    case 's':
                        e.preventDefault();
                        this.handleScanWorkspace();
                        break;
                    case 'h':
                        e.preventDefault();
                        this.toggleShortcutsHelp();
                        break;
                    case '?':
                        e.preventDefault();
                        this.toggleShortcutsHelp();
                        break;
                }
            }
            
            if (e.key === 'Escape') {
                if (this.state.showShortcutsHelp) {
                    this.updateState({ showShortcutsHelp: false });
                } else if (this.state.error) {
                    this.handleRetry();
                }
            }
        };
        this.node.addEventListener('keydown', this.keyboardHandler);
    }

    toggleShortcutsHelp(): void {
        this.updateState({ showShortcutsHelp: !this.state.showShortcutsHelp });
    }

    private addToast(type: ToastNotification['type'], message: string): void {
        const toast: ToastNotification = {
            id: `toast-${Date.now()}`,
            type,
            message,
            timestamp: Date.now()
        };
        
        this.updateState({ 
            toasts: [...this.state.toasts, toast] 
        });
        
        const timeout = setTimeout(() => {
            this.removeToast(toast.id);
        }, 5000);
        this.toastTimeouts.set(toast.id, timeout);
    }

    private removeToast(id: string): void {
        const timeout = this.toastTimeouts.get(id);
        if (timeout) {
            clearTimeout(timeout);
            this.toastTimeouts.delete(id);
        }
        this.updateState({
            toasts: this.state.toasts.filter(t => t.id !== id)
        });
    }

    private toggleSection(sectionId: string): void {
        this.updateState({
            isCollapsed: {
                ...this.state.isCollapsed,
                [sectionId]: !this.state.isCollapsed[sectionId]
            }
        });
    }

    private handleTraceFilterChange(value: string): void {
        this.pendingFilterValue = value;
        if (this.filterDebounceTimer) {
            clearTimeout(this.filterDebounceTimer);
        }
        this.filterDebounceTimer = setTimeout(() => {
            this.updateState({ traceFilter: this.pendingFilterValue });
            this.filterDebounceTimer = undefined;
        }, 300);
    }

    private clearTraceFilter(): void {
        if (this.filterDebounceTimer) {
            clearTimeout(this.filterDebounceTimer);
            this.filterDebounceTimer = undefined;
        }
        this.pendingFilterValue = '';
        this.updateState({ traceFilter: '' });
    }

    private updateExecutionStep(stepId: string, status: ProgressStep['status']): void {
        const steps = this.state.executionSteps.map(step => 
            step.id === stepId ? { ...step, status } : step
        );
        const completedCount = steps.filter(s => s.status === 'completed').length;
        const progress = Math.round((completedCount / steps.length) * 100);
        this.updateState({ executionSteps: steps, executionProgress: progress });
    }

    private updateState(updates: Partial<ArcWidgetState>): void {
        this.state = { ...this.state, ...updates };
        this.update();
    }

    async handleExecuteWorkflow(): Promise<void> {
        if (this.state.isExecuting || !this.state.prompt.trim()) {
            if (!this.state.prompt.trim()) {
                this.messageService.warn('Please enter a prompt for workflow execution');
                this.addToast('warning', 'Please enter a prompt for workflow execution');
            }
            return;
        }

        const perfStart = performance.now();

        const initialSteps: ProgressStep[] = [
            { id: 'parsing', label: 'Parsing prompt', status: 'in-progress' },
            { id: 'planning', label: 'Planning execution', status: 'pending' },
            { id: 'executing', label: 'Executing workflow', status: 'pending' },
            { id: 'recording', label: 'Recording trace', status: 'pending' },
            { id: 'finalizing', label: 'Finalizing results', status: 'pending' }
        ];

        this.updateState({ 
            isExecuting: true, 
            executionStatus: 'running',
            executionProgress: 0,
            executionSteps: initialSteps,
            error: undefined,
            errorDetails: undefined
        });

        const startTime = Date.now();

        try {
            this.updateExecutionStep('parsing', 'completed');
            this.updateState({ executionProgress: 20 });
            
            this.updateExecutionStep('planning', 'in-progress');
            this.updateState({ executionProgress: 30 });
            
            const result = await this.arcService.executeWorkflow(this.state.prompt.trim());
            
            this.updateExecutionStep('planning', 'completed');
            this.updateExecutionStep('executing', 'completed');
            this.updateState({ executionProgress: 60 });
            
            this.updateExecutionStep('recording', 'completed');
            this.updateState({ executionProgress: 80 });
            
            this.updateExecutionStep('finalizing', 'completed');
            
            const executionTime = Date.now() - startTime;

            if (result.status === 'failed') {
                this.updateState({
                    isExecuting: false,
                    executionStatus: 'failed',
                    error: 'Workflow execution failed',
                    errorDetails: result.error || 'Unknown error occurred',
                    executionProgress: 0,
                    executionResult: result,
                    executionTime
                });

                this.messageService.error(`Execution failed: ${result.error || 'Unknown error'}`);
                this.addToast('error', `Execution failed: ${result.error || 'Unknown error'}`);
                return;
            }

            this.updateState({
                isExecuting: false,
                executionStatus: 'completed',
                executionResult: result,
                executionTime,
                executionProgress: 100
            });

            this.messageService.info(`Workflow completed in ${(executionTime / 1000).toFixed(2)}s`);
            this.addToast('success', `Workflow completed in ${(executionTime / 1000).toFixed(2)}s`);

            const perfDuration = performance.now() - perfStart;
            console.log(`[ARC Performance] Workflow execution UI: ${perfDuration.toFixed(2)}ms`);
        } catch (error: any) {
            const currentStep = this.state.executionSteps.find(s => s.status === 'in-progress');
            if (currentStep) {
                this.updateExecutionStep(currentStep.id, 'failed');
            }
            
            this.updateState({
                isExecuting: false,
                executionStatus: 'failed',
                error: 'Workflow execution failed',
                errorDetails: error.message || 'Unknown error occurred',
                executionProgress: 0
            });

            this.messageService.error(`Execution failed: ${error.message}`);
            this.addToast('error', `Execution failed: ${error.message}`);

            const perfDuration = performance.now() - perfStart;
            console.log(`[ARC Performance] Workflow execution UI (failed): ${perfDuration.toFixed(2)}ms`);
        }
    }

    async handleLoadTraces(): Promise<void> {
        if (this.state.isLoadingTraces) {
            return;
        }

        const perfStart = performance.now();

        this.updateState({ 
            isLoadingTraces: true, 
            traceProgress: 0,
            error: undefined,
            errorDetails: undefined 
        });

        try {
            this.updateState({ traceProgress: 20 });
            await new Promise(resolve => setTimeout(resolve, 100));
            
            this.updateState({ traceProgress: 50 });
            
            const traces = await this.arcService.getTraces();
            
            this.updateState({ traceProgress: 80 });
            await new Promise(resolve => setTimeout(resolve, 100));

            this.updateState({
                isLoadingTraces: false,
                traces,
                traceProgress: 100
            });

            const perfDuration = performance.now() - perfStart;
            console.log(`[ARC Performance] Trace loading: ${perfDuration.toFixed(2)}ms for ${traces.length} traces`);

            this.messageService.info(`Loaded ${traces.length} trace(s)`);
            this.addToast('success', `Loaded ${traces.length} trace(s)`);
        } catch (error: any) {
            this.updateState({
                isLoadingTraces: false,
                error: 'Failed to load traces',
                errorDetails: error.message || 'Unknown error occurred',
                traceProgress: 0
            });

            this.messageService.error(`Failed to load traces: ${error.message}`);
            this.addToast('error', `Failed to load traces: ${error.message}`);

            const perfDuration = performance.now() - perfStart;
            console.log(`[ARC Performance] Trace loading (failed): ${perfDuration.toFixed(2)}ms`);
        }
    }

    async handleScanWorkspace(): Promise<void> {
        if (this.state.isScanning) {
            return;
        }

        const perfStart = performance.now();

        this.updateState({ 
            isScanning: true, 
            scanProgress: 0,
            error: undefined,
            errorDetails: undefined 
        });

        try {
            this.updateState({ scanProgress: 25 });
            await new Promise(resolve => setTimeout(resolve, 100));
            
            this.updateState({ scanProgress: 50 });
            
            const workflows = await this.arcService.detectWorkflows();
            
            this.updateState({ scanProgress: 75 });
            await new Promise(resolve => setTimeout(resolve, 100));

            this.updateState({
                isScanning: false,
                workflows,
                scanProgress: 100
            });

            const perfDuration = performance.now() - perfStart;
            console.log(`[ARC Performance] Workspace scan: ${perfDuration.toFixed(2)}ms`);

            this.messageService.info(`Found ${workflows.length} workflow(s)`);
            this.addToast('success', `Found ${workflows.length} workflow(s)`);
        } catch (error: any) {
            this.updateState({
                isScanning: false,
                error: 'Failed to scan workspace',
                errorDetails: error.message || 'Unknown error occurred',
                scanProgress: 0
            });

            this.messageService.error(`Scan failed: ${error.message}`);
            this.addToast('error', `Scan failed: ${error.message}`);

            const perfDuration = performance.now() - perfStart;
            console.log(`[ARC Performance] Workspace scan (failed): ${perfDuration.toFixed(2)}ms`);
        }
    }

    private handleRetry(): void {
        this.updateState({ 
            error: undefined, 
            errorDetails: undefined,
            executionStatus: 'idle',
            executionSteps: [],
            executionProgress: 0
        });
    }

    protected render(): React.ReactNode {
        const renderStart = performance.now();

        const { 
            isExecuting, 
            executionStatus, 
            executionProgress,
            executionResult, 
            executionTime,
            prompt,
            isLoadingTraces, 
            traceProgress,
            traces, 
            selectedTrace,
            traceFilter,
            isScanning, 
            scanProgress,
            workflows,
            error,
            errorDetails,
            isCollapsed,
            toasts,
            showShortcutsHelp,
            executionSteps
        } = this.state;

        const result = (
            <div className='arc-widget-container' role='main' aria-label='ARC Studio'>
                <ToastContainer toasts={toasts} onDismiss={(id) => this.removeToast(id)} />
                <ShortcutsModal isOpen={showShortcutsHelp} onClose={() => this.toggleShortcutsHelp()} />
                
                <div className='arc-header'>
                    <h2>ARC Studio</h2>
                    <p>Agent Runtime Cockpit</p>
                    <button 
                        className='arc-header-help'
                        onClick={() => this.toggleShortcutsHelp()}
                        aria-label='Show keyboard shortcuts'
                        title='Show keyboard shortcuts (Ctrl+H)'
                    >
                        ?
                    </button>
                </div>

                <ErrorBanner error={error} errorDetails={errorDetails} onRetry={() => this.handleRetry()} />

                <div className='arc-content'>
                    <WorkflowExecutionSection
                        isCollapsed={isCollapsed['workflow-execution']}
                        onToggle={() => this.toggleSection('workflow-execution')}
                        prompt={prompt}
                        onPromptChange={(value) => this.updateState({ prompt: value })}
                        isExecuting={isExecuting}
                        executionStatus={executionStatus}
                        executionProgress={executionProgress}
                        executionSteps={executionSteps}
                        executionResult={executionResult}
                        executionTime={executionTime}
                        onExecute={() => this.handleExecuteWorkflow()}
                    />

                    <TraceViewerSection
                        isCollapsed={isCollapsed['trace-viewer']}
                        onToggle={() => this.toggleSection('trace-viewer')}
                        isLoadingTraces={isLoadingTraces}
                        traceProgress={traceProgress}
                        traces={traces}
                        selectedTrace={selectedTrace}
                        traceFilter={traceFilter}
                        onTraceFilterChange={(value) => this.handleTraceFilterChange(value)}
                        onClearFilter={() => this.clearTraceFilter()}
                        onLoadTraces={() => this.handleLoadTraces()}
                        onSelectTrace={(trace) => this.updateState({ selectedTrace: trace })}
                    />

                    <WorkflowDetectionSection
                        isCollapsed={isCollapsed['workflow-detection']}
                        onToggle={() => this.toggleSection('workflow-detection')}
                        isScanning={isScanning}
                        scanProgress={scanProgress}
                        workflows={workflows}
                        onScanWorkspace={() => this.handleScanWorkspace()}
                    />
                </div>

                <div className='arc-footer' role='contentinfo'>
                    <small>
                        <kbd>Ctrl+H</kbd> Show shortcuts | <kbd>Ctrl+E</kbd> Execute | <kbd>Ctrl+L</kbd> Load Traces | <kbd>Ctrl+S</kbd> Scan | <kbd>Esc</kbd> Close
                    </small>
                </div>
            </div>
        );

        const renderDuration = performance.now() - renderStart;
        if (renderDuration > 16) {
            console.warn(`[ARC Performance] Slow widget render: ${renderDuration.toFixed(2)}ms (>${16}ms threshold)`);
        }

        return result;
    }
}
