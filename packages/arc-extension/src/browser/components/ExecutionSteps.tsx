/**
 * Execution Steps Component
 * 
 * Displays workflow execution progress steps.
 */

import * as React from '@theia/core/shared/react';

export interface ProgressStep {
    id: string;
    label: string;
    status: 'pending' | 'in-progress' | 'completed' | 'failed';
}

export interface ExecutionStepsProps {
    steps: ProgressStep[];
}

export const ExecutionSteps: React.FC<ExecutionStepsProps> = ({ steps }) => {
    if (steps.length === 0) {
        return null;
    }

    return (
        <div className='arc-execution-steps' role='list' aria-label='Execution progress steps'>
            {steps.map((step: ProgressStep) => (
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
};
