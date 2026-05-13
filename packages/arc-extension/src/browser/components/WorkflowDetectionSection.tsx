/**
 * Workflow Detection Section Component
 * 
 * UI section for detecting workflows in workspace.
 */

import * as React from '@theia/core/shared/react';
import { WorkflowInfo } from '../../common/arc-protocol';
import { ProgressBar } from './ProgressBar';

export interface WorkflowDetectionSectionProps {
    isCollapsed: boolean;
    onToggle: () => void;
    isScanning: boolean;
    scanProgress: number;
    workflows: WorkflowInfo[];
    onScanWorkspace: () => void;
}

export const WorkflowDetectionSection: React.FC<WorkflowDetectionSectionProps> = ({
    isCollapsed,
    onToggle,
    isScanning,
    scanProgress,
    workflows,
    onScanWorkspace
}) => {
    return (
        <section className={`arc-section ${isCollapsed ? 'arc-section-collapsed' : ''}`} aria-labelledby='workflow-detection-heading'>
            <button 
                className='arc-section-header'
                onClick={onToggle}
                aria-expanded={!isCollapsed}
                aria-controls='workflow-detection-content'
            >
                <h3 id='workflow-detection-heading'>Workflow Detection</h3>
                <div className='arc-section-header-right'>
                    {isCollapsed && workflows.length > 0 && (
                        <span className='arc-section-badge' aria-label={`${workflows.length} workflow(s)`}>
                            {workflows.length}
                        </span>
                    )}
                    <span className='arc-section-toggle' aria-hidden='true'>
                        {isCollapsed ? '▸' : '▾'}
                    </span>
                </div>
            </button>
            
            <div id='workflow-detection-content' className='arc-section-content'>
                {!isCollapsed && (
                    <>
                        <p className='arc-section-description'>Detect workflows in workspace</p>
                        
                        <button 
                            className={`theia-button ${isScanning ? 'arc-button-loading' : ''}`}
                            onClick={onScanWorkspace}
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

                        {isScanning && <ProgressBar value={scanProgress} label='Scanning workspace...' />}

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
    );
};
