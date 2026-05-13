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

interface ProgressStep {
    id: string;
    label: string;
    status: 'pending' | 'in-progress' | 'completed' | 'failed';
}

interface ToastNotification {
    id: string;
    type: 'success' | 'error' | 'info' | 'warning';
    message: string;
    timestamp: number;
}

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

    isCollapsed: { [key: string]: boolean };
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
    private toastTimeouts: Map<string, NodeJS.Timeout> = new Map();
    private filterDebounceTimer: NodeJS.Timeout | undefined;
    private pendingFilterValue: string = '';

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

    private renderProgressBar(value: number, label?: string): React.ReactNode {
        return (
            <div className='arc-progress-container' role='progressbar' aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
                <div className='arc-progress-bar'>
                    <div className='arc-progress-fill' style={{ width: `${value}%` }}></div>
                </div>
                {label && <span className='arc-progress-label'>{label}</span>}
            </div>
        );
    }

    private renderToastContainer(): React.ReactNode {
        return (
            <div className='arc-toast-container' role='region' aria-label='Notifications' aria-live='polite'>
                {this.state.toasts.map((toast: ToastNotification) => (
                    <div 
                        key={toast.id} 
                        className={`arc-toast arc-toast-${toast.type}`}
                        role='alert'
                        aria-atomic='true'
                    >
                        <span className='arc-toast-icon' aria-hidden='true'>
                            {toast.type === 'success' && '✓'}
                            {toast.type === 'error' && '✗'}
                            {toast.type === 'info' && 'ℹ'}
                            {toast.type === 'warning' && '⚠'}
                        </span>
                        <span className='arc-toast-message'>{toast.message}</span>
                        <button 
                            className='arc-toast-dismiss'
                            onClick={() => this.removeToast(toast.id)}
                            aria-label='Dismiss notification'
                        >
                            ×
                        </button>
                    </div>
                ))}
            </div>
        );
    }

    private renderShortcutsModal(): React.ReactNode {
        if (!this.state.showShortcutsHelp) {
            return null;
        }

        return (
            <div 
                className='arc-modal-overlay' 
                role='dialog' 
                aria-modal='true' 
                aria-labelledby='shortcuts-title'
                onClick={(e) => {
                    if (e.target === e.currentTarget) {
                        this.toggleShortcutsHelp();
                    }
                }}
            >
                <div className='arc-modal'>
                    <div className='arc-modal-header'>
                        <h3 id='shortcuts-title'>Keyboard Shortcuts</h3>
                        <button 
                            className='arc-modal-close'
                            onClick={() => this.toggleShortcutsHelp()}
                            aria-label='Close shortcuts help'
                        >
                            ×
                        </button>
                    </div>
                    <div className='arc-modal-content'>
                        <table className='arc-shortcuts-table'>
                            <thead>
                                <tr>
                                    <th>Action</th>
                                    <th>Windows/Linux</th>
                                    <th>Mac</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Execute Workflow</td>
                                    <td><kbd>Ctrl+E</kbd></td>
                                    <td><kbd>⌘+E</kbd></td>
                                </tr>
                                <tr>
                                    <td>Load Traces</td>
                                    <td><kbd>Ctrl+L</kbd></td>
                                    <td><kbd>⌘+L</kbd></td>
                                </tr>
                                <tr>
                                    <td>Scan Workspace</td>
                                    <td><kbd>Ctrl+S</kbd></td>
                                    <td><kbd>⌘+S</kbd></td>
                                </tr>
                                <tr>
                                    <td>Show Shortcuts</td>
                                    <td><kbd>Ctrl+H</kbd></td>
                                    <td><kbd>⌘+H</kbd></td>
                                </tr>
                                <tr>
                                    <td>Close Modal</td>
                                    <td><kbd>Esc</kbd></td>
                                    <td><kbd>Esc</kbd></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        );
    }

    private renderExecutionSteps(): React.ReactNode {
        const { executionSteps } = this.state;
        
        if (executionSteps.length === 0) {
            return null;
        }

        return (
            <div className='arc-execution-steps' role='list' aria-label='Execution progress steps'>
                {executionSteps.map((step: ProgressStep) => (
                    <div 
                        key={step.id} 
                        className={`arc-step arc-step-${step.status}`}
                        role='listitem'
                        aria-current={step.status === 'in-progress' ? 'step' : undefined}
                    >
                        <span className='arc-step-indicator' aria-hidden='true'>
                            {step.status === 'completed' && '✓'}
                            {step.status === 'in-progress' && '⟳'}
                            {step.status === 'pending' && '○'}
                            {step.status === 'failed' && '✗'}
                        </span>
                        <span className='arc-step-label'>{step.label}</span>
                    </div>
                ))}
            </div>
        );
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
            isCollapsed
        } = this.state;

        const filteredTraces = traces.filter((t: TraceFile) => 
            t.id.toLowerCase().includes(traceFilter.toLowerCase())
        );

        const result = (
            <div className='arc-widget-container' role='main' aria-label='ARC Studio'>
                {this.renderToastContainer()}
                {this.renderShortcutsModal()}
                
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

                {error && (
                    <div className='arc-error' role='alert' aria-live='assertive'>
                        <div className='arc-error-content'>
                            <span className='arc-error-icon' aria-hidden='true'>⚠</span>
                            <div className='arc-error-text'>
                                <strong className='arc-error-title'>{error}</strong>
                                {errorDetails && (
                                    <p className='arc-error-details'>{errorDetails}</p>
                                )}
                            </div>
                        </div>
                        <div className='arc-error-actions'>
                            <button 
                                className='theia-button secondary'
                                onClick={() => this.handleRetry()}
                                aria-label='Try again'
                            >
                                Try Again
                            </button>
                            <button 
                                className='arc-error-dismiss'
                                onClick={() => this.handleRetry()}
                                aria-label='Dismiss error'
                            >
                                ×
                            </button>
                        </div>
                    </div>
                )}

                <div className='arc-content'>
                    <section className={`arc-section ${isCollapsed['workflow-execution'] ? 'arc-section-collapsed' : ''}`} aria-labelledby='workflow-execution-heading'>
                        <button 
                            className='arc-section-header'
                            onClick={() => this.toggleSection('workflow-execution')}
                            aria-expanded={!isCollapsed['workflow-execution']}
                            aria-controls='workflow-execution-content'
                        >
                            <h3 id='workflow-execution-heading'>Workflow Execution</h3>
                            <div className='arc-section-header-right'>
                                {isCollapsed['workflow-execution'] && executionStatus !== 'idle' && (
                                    <span className='arc-section-badge' aria-label={`Status: ${executionStatus}`}>
                                        {executionStatus === 'running' ? '⟳' : executionStatus === 'completed' ? '✓' : '✗'}
                                    </span>
                                )}
                                <span className='arc-section-toggle' aria-hidden='true'>
                                    {isCollapsed['workflow-execution'] ? '▸' : '▾'}
                                </span>
                            </div>
                        </button>
                        
                        <div id='workflow-execution-content' className='arc-section-content'>
                            {!isCollapsed['workflow-execution'] && (
                                <>
                                    <p className='arc-section-description'>Execute SwarmGraph and LangGraph workflows</p>
                                    
                                    <div className='arc-input-group'>
                                        <label htmlFor='prompt-input'>Prompt:</label>
                                        <input
                                            id='prompt-input'
                                            type='text'
                                            className='theia-input'
                                            placeholder='Enter workflow prompt...'
                                            value={prompt}
                                            onChange={(e) => this.updateState({ prompt: e.target.value })}
                                            onKeyDown={(e) => {
                                                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                                                    this.handleExecuteWorkflow();
                                                }
                                            }}
                                            disabled={isExecuting}
                                            aria-required='true'
                                            aria-describedby='prompt-help'
                                        />
                                        <small id='prompt-help' className='arc-help-text'>
                                            Press <kbd>Ctrl+Enter</kbd> to execute or <kbd>Ctrl+E</kbd>
                                        </small>
                                    </div>

                                    <button 
                                        className={`theia-button primary ${isExecuting ? 'arc-button-loading' : ''}`}
                                        onClick={() => this.handleExecuteWorkflow()}
                                        disabled={isExecuting || !prompt.trim()}
                                        aria-busy={isExecuting}
                                        aria-label='Execute workflow'
                                    >
                                        {isExecuting ? (
                                            <>
                                                <span className='arc-spinner' aria-hidden='true'></span>
                                                <span className='arc-button-text'>Executing...</span>
                                            </>
                                        ) : (
                                            'Execute Workflow'
                                        )}
                                    </button>

                                    {isExecuting && this.renderProgressBar(executionProgress, `${executionProgress}% complete`)}
                                    {this.renderExecutionSteps()}

                                    {executionStatus !== 'idle' && (
                                        <div className={`arc-status arc-status-${executionStatus}`} role='status' aria-live='polite'>
                                            <span className='arc-status-icon' aria-hidden='true'>
                                                {executionStatus === 'running' && '⏳'}
                                                {executionStatus === 'completed' && '✓'}
                                                {executionStatus === 'failed' && '✗'}
                                            </span>
                                            <span className='arc-status-text'>
                                                {executionStatus === 'running' && 'Workflow is running...'}
                                                {executionStatus === 'completed' && executionTime !== undefined && `Completed in ${(executionTime / 1000).toFixed(2)}s`}
                                                {executionStatus === 'completed' && executionTime === undefined && 'Completed'}
                                                {executionStatus === 'failed' && 'Execution failed'}
                                            </span>
                                        </div>
                                    )}

                                    {executionResult && executionStatus === 'completed' && (
                                        <div className='arc-result'>
                                            <h4>Execution Result</h4>
                                            <dl className='arc-result-list'>
                                                <dt>Run ID:</dt>
                                                <dd><code>{executionResult.runId}</code></dd>
                                                <dt>Trace:</dt>
                                                <dd><code>{executionResult.tracePath}</code></dd>
                                                <dt>Status:</dt>
                                                <dd><span className='arc-status-badge arc-status-badge-success'>Completed</span></dd>
                                            </dl>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    </section>

                    <section className={`arc-section ${isCollapsed['trace-viewer'] ? 'arc-section-collapsed' : ''}`} aria-labelledby='trace-viewer-heading'>
                        <button 
                            className='arc-section-header'
                            onClick={() => this.toggleSection('trace-viewer')}
                            aria-expanded={!isCollapsed['trace-viewer']}
                            aria-controls='trace-viewer-content'
                        >
                            <h3 id='trace-viewer-heading'>Trace Viewer</h3>
                            <div className='arc-section-header-right'>
                                {isCollapsed['trace-viewer'] && filteredTraces.length > 0 && (
                                    <span className='arc-section-badge' aria-label={`${filteredTraces.length} trace(s)`}>
                                        {filteredTraces.length}
                                    </span>
                                )}
                                <span className='arc-section-toggle' aria-hidden='true'>
                                    {isCollapsed['trace-viewer'] ? '▸' : '▾'}
                                </span>
                            </div>
                        </button>
                        
                        <div id='trace-viewer-content' className='arc-section-content'>
                            {!isCollapsed['trace-viewer'] && (
                                <>
                                    <p className='arc-section-description'>View execution traces from .arc/traces/</p>
                                    
                                    <div className='arc-input-group'>
                                        <label htmlFor='trace-filter'>Filter traces:</label>
                                        <div className='arc-filter-input-wrapper'>
                                            <input
                                                id='trace-filter'
                                                type='text'
                                                className='theia-input'
                                                placeholder='Filter by ID...'
                                                value={traceFilter}
                                                onChange={(e) => this.handleTraceFilterChange(e.target.value)}
                                                aria-label='Filter traces by ID'
                                            />
                                            {traceFilter && (
                                                <button
                                                    className='arc-filter-clear'
                                                    onClick={() => this.clearTraceFilter()}
                                                    aria-label='Clear filter'
                                                    title='Clear filter'
                                                >
                                                    ×
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    <button 
                                        className={`theia-button ${isLoadingTraces ? 'arc-button-loading' : ''}`}
                                        onClick={() => this.handleLoadTraces()}
                                        disabled={isLoadingTraces}
                                        aria-busy={isLoadingTraces}
                                        aria-label='Load traces'
                                    >
                                        {isLoadingTraces ? (
                                            <>
                                                <span className='arc-spinner' aria-hidden='true'></span>
                                                <span className='arc-button-text'>Loading...</span>
                                            </>
                                        ) : (
                                            'Load Traces'
                                        )}
                                    </button>

                                    {isLoadingTraces && this.renderProgressBar(traceProgress, 'Loading traces...')}

                                    {traces.length > 0 && (
                                        <div className='arc-trace-list' role='listbox' aria-label='Trace files'>
                                            <div className='arc-trace-list-header'>
                                                <span>Status</span>
                                                <span>Run ID</span>
                                                <span>Timestamp</span>
                                            </div>
                                            {filteredTraces.map((trace: TraceFile) => (
                                                <div 
                                                    key={trace.id} 
                                                    className={`arc-trace-item ${selectedTrace?.id === trace.id ? 'arc-trace-item-selected' : ''}`}
                                                    role='option'
                                                    onClick={() => this.updateState({ selectedTrace: trace })}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter' || e.key === ' ') {
                                                            this.updateState({ selectedTrace: trace });
                                                        }
                                                    }}
                                                    tabIndex={0}
                                                    aria-selected={selectedTrace?.id === trace.id}
                                                >
                                                    <span className={`arc-trace-status arc-trace-status-${trace.status}`} aria-label={`Status: ${trace.status}`}>
                                                        {trace.status === 'completed' ? '✓' : '✗'}
                                                    </span>
                                                    <span className='arc-trace-id'>{trace.id}</span>
                                                    <span className='arc-trace-time'>{new Date(trace.timestamp).toLocaleString()}</span>
                                                </div>
                                            ))}
                                            {filteredTraces.length === 0 && (
                                                <p className='arc-empty-state'>No traces match the filter</p>
                                            )}
                                        </div>
                                    )}

                                    {traces.length === 0 && !isLoadingTraces && (
                                        <p className='arc-empty-state'>No traces loaded. Click "Load Traces" to view traces.</p>
                                    )}
                                </>
                            )}
                        </div>
                    </section>

                    <section className={`arc-section ${isCollapsed['workflow-detection'] ? 'arc-section-collapsed' : ''}`} aria-labelledby='workflow-detection-heading'>
                        <button 
                            className='arc-section-header'
                            onClick={() => this.toggleSection('workflow-detection')}
                            aria-expanded={!isCollapsed['workflow-detection']}
                            aria-controls='workflow-detection-content'
                        >
                            <h3 id='workflow-detection-heading'>Workflow Detection</h3>
                            <div className='arc-section-header-right'>
                                {isCollapsed['workflow-detection'] && workflows.length > 0 && (
                                    <span className='arc-section-badge' aria-label={`${workflows.length} workflow(s)`}>
                                        {workflows.length}
                                    </span>
                                )}
                                <span className='arc-section-toggle' aria-hidden='true'>
                                    {isCollapsed['workflow-detection'] ? '▸' : '▾'}
                                </span>
                            </div>
                        </button>
                        
                        <div id='workflow-detection-content' className='arc-section-content'>
                            {!isCollapsed['workflow-detection'] && (
                                <>
                                    <p className='arc-section-description'>Detect workflows in workspace</p>
                                    
                                    <button 
                                        className={`theia-button ${isScanning ? 'arc-button-loading' : ''}`}
                                        onClick={() => this.handleScanWorkspace()}
                                        disabled={isScanning}
                                        aria-busy={isScanning}
                                        aria-label='Scan workspace for workflows'
                                    >
                                        {isScanning ? (
                                            <>
                                                <span className='arc-spinner' aria-hidden='true'></span>
                                                <span className='arc-button-text'>Scanning...</span>
                                            </>
                                        ) : (
                                            'Scan Workspace'
                                        )}
                                    </button>

                                    {isScanning && this.renderProgressBar(scanProgress, 'Scanning workspace...')}

                                    {workflows.length > 0 && (
                                        <div className='arc-workflow-list' role='list' aria-label='Detected workflows'>
                                            <div className='arc-workflow-list-header'>
                                                <span>Type</span>
                                                <span>Name</span>
                                                <span>Path</span>
                                            </div>
                                            {workflows.map((workflow: WorkflowInfo, idx: number) => (
                                                <div key={idx} className='arc-workflow-item' role='listitem'>
                                                    <span className='arc-workflow-type' aria-label={`Type: ${workflow.type}`}>
                                                        {workflow.type}
                                                    </span>
                                                    <span className='arc-workflow-name'>{workflow.name}</span>
                                                    <span className='arc-workflow-path'>{workflow.path}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {workflows.length === 0 && !isScanning && (
                                        <p className='arc-empty-state'>No workflows detected. Click "Scan Workspace" to detect workflows.</p>
                                    )}
                                </>
                            )}
                        </div>
                    </section>
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
