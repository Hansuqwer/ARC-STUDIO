/**
 * Test Bench Tab
 *
 * Standalone tab for testbench detection: lists detected test commands
 * with their source, confidence, runner, and cwd.
 * Previously rendered as a sub-panel in CommandCentreTab.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, TestbenchDetection } from '../../common/arc-protocol';
import { useAsyncState } from '../hooks/useAsyncState';

export interface TestBenchTabProps {
    arcService: ArcService;
}

export const TestBenchTab: React.FC<TestBenchTabProps> = ({ arcService }) => {
    const { data: detection, loading, error, reload: load } = useAsyncState<TestbenchDetection>(
        () => arcService.detectTestbench(),
        [arcService],
        { errorMessage: 'Failed to detect testbench' },
    );

    if (loading) {
        return (
            <div className='arc-testbench' role='region' aria-label='Test Bench'>
                <h3>Test Bench</h3>
                <p className='arc-testbench__loading'>Detecting test commands...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className='arc-testbench' role='region' aria-label='Test Bench'>
                <h3>Test Bench</h3>
                <div className='arc-testbench__error' role='alert'>Error: {error}</div>
                <button className='arc-testbench__refresh' onClick={load}>Retry</button>
            </div>
        );
    }

    if (!detection || detection.count === 0) {
        return (
            <div className='arc-testbench' role='region' aria-label='Test Bench'>
                <div className='arc-testbench__header'>
                    <h3>Test Bench</h3>
                    <button className='arc-testbench__refresh' onClick={load}>Refresh</button>
                </div>
                <p className='arc-testbench__empty'>No test commands detected.</p>
            </div>
        );
    }

    return (
        <div className='arc-testbench' role='region' aria-label='Test Bench'>
            <div className='arc-testbench__header'>
                <h3>Test Bench</h3>
                <button className='arc-testbench__refresh' onClick={load}>Refresh</button>
            </div>

            <p className='arc-testbench__summary'>
                Detected <strong>{detection.count}</strong> test command{detection.count !== 1 ? 's' : ''}
            </p>

            <div className='arc-testbench__list'>
                {detection.detected.map((entry, i) => (
                    <div key={i} className='arc-testbench__card'>
                        <div className='arc-testbench__card-command'>
                            {entry.command || entry.runner || 'unknown'}
                        </div>
                        <div className='arc-testbench__card-meta'>
                            {entry.source && (
                                <span className='arc-testbench__badge'>Source: {entry.source}</span>
                            )}
                            {entry.confidence && (
                                <span className='arc-testbench__badge'>Confidence: {entry.confidence}</span>
                            )}
                            {entry.runner && (
                                <span className='arc-testbench__badge'>Runner: {entry.runner}</span>
                            )}
                        </div>
                        {entry.cwd && (
                            <div className='arc-testbench__card-cwd'>cwd: {entry.cwd}</div>
                        )}
                        {entry.script && (
                            <div className='arc-testbench__card-script'>Script: {entry.script}</div>
                        )}
                        {entry.reason && (
                            <div className='arc-testbench__card-reason'>{entry.reason}</div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};
