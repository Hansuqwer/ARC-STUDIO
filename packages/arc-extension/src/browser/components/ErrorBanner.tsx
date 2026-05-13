/**
 * Error Banner Component
 * 
 * Displays error messages with retry action.
 */

import * as React from '@theia/core/shared/react';

export interface ErrorBannerProps {
    error?: string;
    errorDetails?: string;
    onRetry: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ error, errorDetails, onRetry }) => {
    if (!error) {
        return null;
    }

    return (
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
                    onClick={onRetry}
                    aria-label='Try again'
                >
                    Try Again
                </button>
                <button 
                    className='arc-error-dismiss'
                    onClick={onRetry}
                    aria-label='Dismiss error'
                >
                    ×
                </button>
            </div>
        </div>
    );
};
