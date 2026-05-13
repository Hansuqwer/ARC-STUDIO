/**
 * Progress Bar Component
 * 
 * Displays a progress bar with optional label.
 */

import * as React from '@theia/core/shared/react';

export interface ProgressBarProps {
    value: number;
    label?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ value, label }) => {
    return (
        <div className='arc-progress-container' role='progressbar' aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
            <div className='arc-progress-bar'>
                <div className='arc-progress-fill' style={{ width: `${value}%` }}></div>
            </div>
            {label && <span className='arc-progress-label'>{label}</span>}
        </div>
    );
};
