/**
 * Test Bench Tab
 *
 * Standalone tab for testbench detection: lists detected test commands
 * with their source, confidence, runner, and cwd.
 * Previously rendered as a sub-panel in CommandCentreTab.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, TestbenchDetection, TestbenchRunResult } from '../../common/arc-protocol';
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

    const [runState, setRunState] = React.useState<
        Record<number, { running?: boolean; result?: TestbenchRunResult; error?: string }>
    >({});
    const runCommand = React.useCallback(async (i: number, command: string) => {
        if (!command) {
            return;
        }
        // Confirm gate: executing a command, even sandbox-policy-gated, is a mutating action.
        // eslint-disable-next-line no-alert
        if (!window.confirm(`Run "${command}" through the local-safe sandbox?\nNetwork and destructive operations are denied.`)) {
            return;
        }
        setRunState(s => ({ ...s, [i]: { running: true } }));
        try {
            const result = await arcService.runTestbench(command);
            setRunState(s => ({ ...s, [i]: { result } }));
        } catch (e) {
            setRunState(s => ({ ...s, [i]: { error: e instanceof Error ? e.message : String(e) } }));
        }
    }, [arcService]);

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
                        <div className='arc-testbench__card-actions'>
                            <button
                                className='arc-testbench__run'
                                disabled={!entry.command || runState[i]?.running}
                                aria-label={`Run ${entry.command || 'command'} in the local-safe sandbox`}
                                onClick={() => entry.command && runCommand(i, entry.command)}
                            >
                                {runState[i]?.running ? 'Running…' : 'Run (local-safe)'}
                            </button>
                            {runState[i]?.error && (
                                <span className='arc-testbench__run-error' role='alert'>
                                    Error: {runState[i]!.error}
                                </span>
                            )}
                            {runState[i]?.result && !runState[i]!.result!.allowed && (
                                <span className='arc-testbench__run-result arc-testbench__run-result--blocked'>
                                    Blocked by policy
                                </span>
                            )}
                            {runState[i]?.result && runState[i]!.result!.allowed && (
                                <span
                                    className={`arc-testbench__run-result arc-testbench__run-result--${runState[i]!.result!.exitCode === 0 ? 'pass' : 'fail'}`}
                                >
                                    Exit {runState[i]!.result!.exitCode ?? '?'}
                                    {runState[i]!.result!.exitCode === 0 ? ' ✓' : ''}
                                </span>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
