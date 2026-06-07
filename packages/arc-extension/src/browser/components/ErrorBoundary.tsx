/**
 * ErrorBoundary
 *
 * Reusable React error boundary so a throw inside one ARC Studio tab renders a
 * recoverable fallback instead of blanking the entire widget. A class component
 * is required here: React error boundaries rely on getDerivedStateFromError /
 * componentDidCatch, which have no hooks equivalent.
 */

import * as React from '@theia/core/shared/react';

export interface ErrorBoundaryProps {
    /** Human-readable name of the guarded surface (e.g. the active tab label). */
    surface?: string;
    children: React.ReactNode;
}

interface ErrorBoundaryState {
    error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { error };
    }

    componentDidCatch(error: Error, info: React.ErrorInfo): void {
        // eslint-disable-next-line no-console
        console.error(`ARC Studio surface "${this.props.surface ?? 'unknown'}" crashed:`, error, info);
    }

    private readonly handleRetry = (): void => {
        this.setState({ error: null });
    };

    render(): React.ReactNode {
        const { error } = this.state;
        if (error) {
            const surface = this.props.surface ?? 'panel';
            return (
                <div className='arc-error arc-error-boundary' role='alert' aria-live='assertive'>
                    <div className='arc-error-content'>
                        <span className='arc-error-icon' aria-hidden='true'>⚠</span>
                        <div className='arc-error-text'>
                            <strong className='arc-error-title'>The {surface} view hit an error.</strong>
                            <p className='arc-error-details'>{error.message || String(error)}</p>
                        </div>
                    </div>
                    <div className='arc-error-actions'>
                        <button
                            className='theia-button secondary'
                            onClick={this.handleRetry}
                            aria-label={`Retry ${surface} view`}
                        >
                            Retry
                        </button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
