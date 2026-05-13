/**
 * Workflow Execution Section Component
 * 
 * UI section for executing workflows.
 */

import * as React from '@theia/core/shared/react';
import { ExecutionResult } from '../../common/arc-protocol';
import { ProgressBar } from './ProgressBar';
import { ExecutionSteps, ProgressStep } from './ExecutionSteps';

export interface WorkflowExecutionSectionProps {
    isCollapsed: boolean;
    onToggle: () => void;
    prompt: string;
    onPromptChange: (value: string) => void;
    isExecuting: boolean;
    executionStatus: 'idle' | 'running' | 'completed' | 'failed';
    executionProgress: number;
    executionSteps: ProgressStep[];
    executionResult?: ExecutionResult;
    executionTime?: number;
    onExecute: () => void;
}

export const WorkflowExecutionSection: React.FC<WorkflowExecutionSectionProps> = ({
    isCollapsed,
    onToggle,
    prompt,
    onPromptChange,
    isExecuting,
    executionStatus,
    executionProgress,
    executionSteps,
    executionResult,
    executionTime,
    onExecute
}) => {
    return (
        <section className={`arc-section ${isCollapsed ? 'arc-section-collapsed' : ''}`} aria-labelledby='workflow-execution-heading'>
            <button 
                className='arc-section-header'
                onClick={onToggle}
                aria-expanded={!isCollapsed}
                aria-controls='workflow-execution-content'
            >
                <h3 id='workflow-execution-heading'>Workflow Execution</h3>
                <div className='arc-section-header-right'>
                    {isCollapsed && executionStatus !== 'idle' && (
                        <span className='arc-section-badge' aria-label={`Status: ${executionStatus}`}>
                            {executionStatus === 'running' ? '⟳' : executionStatus === 'completed' ? '✓' : '✗'}
                        </span>
                    )}
                    <span className='arc-section-toggle' aria-hidden='true'>
                        {isCollapsed ? '▸' : '▾'}
                    </span>
                </div>
            </button>
            
            <div id='workflow-execution-content' className='arc-section-content'>
                {!isCollapsed && (
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
                                onChange={(e) => onPromptChange(e.target.value)}
                                onKeyDown={(e) => {
                                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                                        onExecute();
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
                            onClick={onExecute}
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

                        {isExecuting && <ProgressBar value={executionProgress} label={`${executionProgress}% complete`} />}
                        <ExecutionSteps steps={executionSteps} />

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
    );
};
