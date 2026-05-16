/**
 * Workflows Tab
 *
 * Workflow detection and list shell. Reuses detection pattern from existing WorkflowDetectionSection.
 */

import * as React from '@theia/core/shared/react';
import { WorkflowInfo } from '../../common/arc-protocol';

export interface WorkflowsTabProps {
    workflows: WorkflowInfo[];
    isScanning: boolean;
    onScanWorkspace: () => void;
}

export const WorkflowsTab: React.FC<WorkflowsTabProps> = ({ workflows, isScanning, onScanWorkspace }) => {
    return (
        <div className='arc-studio-workflows' role='region' aria-label='Workflows panel'>
            <div className='arc-studio-workflows__header'>
                <h3>Workflows</h3>
                <button
                    className='arc-studio-workflows__scan'
                    onClick={onScanWorkspace}
                    disabled={isScanning}
                    aria-label='Scan workspace for workflows'
                >
                    {isScanning ? 'Scanning...' : 'Scan'}
                </button>
            </div>

            <div className='arc-studio-workflows__list'>
                {workflows.length === 0 && !isScanning && (
                    <div className='arc-studio-workflows__placeholder'>
                        <p>No workflows detected.</p>
                        <p className='arc-studio-workflows__hint'>
                            Click Scan to detect SwarmGraph or LangGraph workflows in this workspace.
                        </p>
                    </div>
                )}

                {workflows.map((wf, idx) => (
                    <div key={idx} className='arc-studio-workflows__card'>
                        <div className='arc-studio-workflows__card-title'>{wf.name || `workflow-${idx}`}</div>
                        <div className='arc-studio-workflows__card-meta'>
                            {wf.type && <span className='arc-studio-workflows__badge'>{wf.type}</span>}
                            {wf.path && <span className='arc-studio-workflows__file'>{wf.path}</span>}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
