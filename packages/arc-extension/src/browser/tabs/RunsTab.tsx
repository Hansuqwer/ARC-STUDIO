/**
 * Runs Tab
 *
 * Lists runs, allows selection, and renders receipt, failure autopsy,
 * and contract cards for the selected run. No trace viewer.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, TraceFile, RunReceipt, FailureAutopsy, RunContract, RetryOption } from '../../common/arc-protocol';
import { RunReceiptCard } from '../components/RunReceiptCard';
import { FailureAutopsyCard } from '../components/FailureAutopsyCard';
import { RunContractCard } from '../components/RunContractCard';

export interface RunsTabProps {
    arcService: ArcService;
}

interface RunsTabState {
    runs: TraceFile[];
    selectedRunId: string | null;
    receipt: RunReceipt | null;
    autopsy: FailureAutopsy | null;
    contract: RunContract | null;
    isLoadingRuns: boolean;
    isLoadingDetails: boolean;
    error: string | null;
}

function truncateId(id: string, max = 12): string {
    return id.length > max ? id.slice(0, max) + '…' : id;
}

function formatTimestamp(ts: string): string {
    try {
        const d = new Date(ts);
        return d.toLocaleString();
    } catch {
        return ts;
    }
}

export const RunsTab: React.FC<RunsTabProps> = ({ arcService }) => {
    const [state, setState] = React.useState<RunsTabState>({
        runs: [],
        selectedRunId: null,
        receipt: null,
        autopsy: null,
        contract: null,
        isLoadingRuns: false,
        isLoadingDetails: false,
        error: null,
    });

    const loadRuns = React.useCallback(async () => {
        setState(prev => ({ ...prev, isLoadingRuns: true, error: null }));
        try {
            const runs = await arcService.getTraces();
            setState(prev => ({ ...prev, runs, isLoadingRuns: false }));
        } catch (err: any) {
            setState(prev => ({
                ...prev,
                isLoadingRuns: false,
                error: `Failed to load runs: ${err.message}`,
            }));
        }
    }, [arcService]);

    const selectRun = React.useCallback(async (runId: string) => {
        setState(prev => ({
            ...prev,
            selectedRunId: runId,
            receipt: null,
            autopsy: null,
            contract: null,
            isLoadingDetails: true,
            error: null,
        }));
        try {
            const [receipt, autopsy, contract] = await Promise.all([
                arcService.getRunReceipt(runId).catch(() => null),
                arcService.getRunAutopsy(runId).catch(() => null),
                arcService.getRunContract(runId).catch(() => null),
            ]);
            setState(prev => ({
                ...prev,
                receipt,
                autopsy,
                contract,
                isLoadingDetails: false,
            }));
        } catch (err: any) {
            setState(prev => ({
                ...prev,
                isLoadingDetails: false,
                error: `Failed to load run details: ${err.message}`,
            }));
        }
    }, [arcService]);

    React.useEffect(() => {
        loadRuns();
    }, [loadRuns]);

    const { runs, selectedRunId, receipt, autopsy, contract, isLoadingRuns, isLoadingDetails, error } = state;

    return (
        <div className='arc-studio-runs' role='region' aria-label='Runs panel'>
            <div className='arc-studio-runs__header'>
                <h3>Runs</h3>
                <button
                    className='arc-studio-runs__refresh'
                    onClick={loadRuns}
                    disabled={isLoadingRuns}
                    aria-label='Refresh runs'
                >
                    {isLoadingRuns ? 'Loading…' : 'Refresh'}
                </button>
            </div>

            {error && (
                <div className='arc-studio-runs__error' role='alert'>
                    {error}
                </div>
            )}

            <div className='arc-studio-runs__layout'>
                <div className='arc-studio-runs__list'>
                    {isLoadingRuns && runs.length === 0 && (
                        <div className='arc-studio-runs__placeholder'>
                            <p>Loading runs…</p>
                        </div>
                    )}

                    {!isLoadingRuns && runs.length === 0 && (
                        <div className='arc-studio-runs__placeholder'>
                            <p>No runs yet.</p>
                            <p className='arc-studio-runs__hint'>
                                Run a workflow from the Chat or Workflows tab to see results here.
                            </p>
                        </div>
                    )}

                    {runs.map(run => (
                        <button
                            key={run.id}
                            className={`arc-studio-runs__item ${selectedRunId === run.id ? 'arc-studio-runs__item--selected' : ''}`}
                            onClick={() => selectRun(run.id)}
                            aria-label={`Run ${truncateId(run.id)} — ${run.status}`}
                            aria-current={selectedRunId === run.id ? 'true' : undefined}
                        >
                            <span className={`arc-studio-runs__item-status arc-studio-runs__item-status--${run.status}`}>
                                {run.status === 'completed' ? '[OK]' : run.status === 'failed' ? '[!]' : '[?]'}
                            </span>
                            <span className='arc-studio-runs__item-id' title={run.id}>
                                {truncateId(run.id)}
                            </span>
                            <span className='arc-studio-runs__item-time'>
                                {formatTimestamp(run.timestamp)}
                            </span>
                            {run.eventCount !== undefined && (
                                <span className='arc-studio-runs__item-events'>
                                    {run.eventCount} events
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                <div className='arc-studio-runs__detail'>
                    {!selectedRunId && !isLoadingDetails && (
                        <div className='arc-studio-runs__detail-placeholder'>
                            <p>Select a run to view details.</p>
                        </div>
                    )}

                    {isLoadingDetails && (
                        <div className='arc-studio-runs__detail-placeholder'>
                            <p>Loading run details…</p>
                        </div>
                    )}

                    {selectedRunId && !isLoadingDetails && !receipt && !autopsy && (
                        <div className='arc-studio-runs__detail-placeholder'>
                            <p>No details available for this run.</p>
                        </div>
                    )}

                    {selectedRunId && !isLoadingDetails && receipt && (
                        <RunReceiptCard receipt={receipt} />
                    )}

                    {selectedRunId && !isLoadingDetails && autopsy && (
                        <FailureAutopsyCard
                            autopsy={autopsy}
                        />
                    )}

                    {selectedRunId && !isLoadingDetails && contract && (
                        <RunContractCard contract={contract} />
                    )}
                </div>
            </div>
        </div>
    );
};
