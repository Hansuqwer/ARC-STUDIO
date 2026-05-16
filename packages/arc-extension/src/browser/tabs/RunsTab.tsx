/**
 * Runs Tab
 *
 * Lists runs, allows selection, and renders receipt, failure autopsy,
 * and contract cards for the selected run. No trace viewer.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, TraceFile, RunReceipt, FailureAutopsy, RunContract, AuditChainInfo, HitlPromptInfo, ReplayEvent } from '../../common/arc-protocol';
import { RunReceiptCard } from '../components/RunReceiptCard';
import { FailureAutopsyCard } from '../components/FailureAutopsyCard';
import { RunContractCard } from '../components/RunContractCard';

export interface RunsTabProps {
    arcService: ArcService;
    initialRunId?: string | null;
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
    // Slice 7 additions
    auditInfo: AuditChainInfo | null;
    isVerifyingAudit: boolean;
    replayEvents: ReplayEvent[] | null;
    isReplaying: boolean;
    hitlPrompts: HitlPromptInfo[];
    isListHitl: boolean;
    hitlError: string | null;
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

export const RunsTab: React.FC<RunsTabProps> = ({ arcService, initialRunId }) => {
    const [state, setState] = React.useState<RunsTabState>({
        runs: [],
        selectedRunId: null,
        receipt: null,
        autopsy: null,
        contract: null,
        isLoadingRuns: false,
        isLoadingDetails: false,
        error: null,
        auditInfo: null,
        isVerifyingAudit: false,
        replayEvents: null,
        isReplaying: false,
        hitlPrompts: [],
        isListHitl: false,
        hitlError: null,
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

    const verifyAudit = React.useCallback(async (runId: string) => {
        if (!arcService.getAuditChainInfo) return;
        setState(prev => ({ ...prev, isVerifyingAudit: true, auditInfo: null }));
        try {
            const info = await arcService.getAuditChainInfo(runId);
            setState(prev => ({ ...prev, auditInfo: info, isVerifyingAudit: false }));
        } catch {
            setState(prev => ({ ...prev, isVerifyingAudit: false }));
        }
    }, [arcService]);

    const handleReplay = React.useCallback(async (runId: string) => {
        if (!arcService.replayRun) return;
        setState(prev => ({ ...prev, isReplaying: true, replayEvents: null }));
        try {
            const result = await arcService.replayRun(runId);
            setState(prev => ({ ...prev, replayEvents: result.events, isReplaying: false }));
        } catch {
            setState(prev => ({ ...prev, isReplaying: false }));
        }
    }, [arcService]);

    const listHitlPrompts = React.useCallback(async () => {
        if (!arcService.listPendingHitlPrompts) return;
        setState(prev => ({ ...prev, isListHitl: true, hitlError: null }));
        try {
            const prompts = await arcService.listPendingHitlPrompts();
            setState(prev => ({ ...prev, hitlPrompts: prompts, isListHitl: false }));
        } catch (err: any) {
            setState(prev => ({ ...prev, isListHitl: false, hitlError: err.message }));
        }
    }, [arcService]);

    const respondHitl = React.useCallback(async (prompt: HitlPromptInfo, decision: 'approve' | 'reject') => {
        if (!arcService.respondHitlPrompt) return;
        if (!prompt.token) {
            setState(prev => ({ ...prev, hitlError: `Missing HITL decision token for ${prompt.promptId}` }));
            return;
        }
        try {
            await arcService.respondHitlPrompt({ promptId: prompt.promptId, decision, token: prompt.token });
            // Refresh prompt list after response
            listHitlPrompts();
        } catch (err: any) {
            setState(prev => ({ ...prev, hitlError: err.message }));
        }
    }, [arcService, listHitlPrompts]);

    // Auto-select initialRunId when runs first load
    const initialAutoSelected = React.useRef(false);
    React.useEffect(() => {
        loadRuns();
    }, [loadRuns]);

    React.useEffect(() => {
        const currentRuns = state.runs;
        if (initialRunId && currentRuns.length > 0 && !initialAutoSelected.current) {
            const match = currentRuns.find(r => r.id === initialRunId);
            if (match) {
                initialAutoSelected.current = true;
                selectRun(initialRunId);
            }
        }
    }, [initialRunId, state.runs, selectRun]);

    const { runs, selectedRunId, receipt, autopsy, contract, isLoadingRuns, isLoadingDetails, error,
        auditInfo, isVerifyingAudit, replayEvents, isReplaying, hitlPrompts, isListHitl, hitlError } = state;

    return (
        <div className='arc-studio-runs' role='region' aria-label='Runs panel'>
            <div className='arc-studio-runs__header'>
                <h3>Runs</h3>
                <div className='arc-studio-runs__header-actions'>
                    <button
                        className='theia-button secondary'
                        onClick={listHitlPrompts}
                        disabled={isListHitl}
                        aria-label='List pending HITL prompts'
                    >
                        {isListHitl ? 'Loading…' : `HITL (${hitlPrompts.length})`}
                    </button>
                    <button
                        className='arc-studio-runs__refresh'
                        onClick={loadRuns}
                        disabled={isLoadingRuns}
                        aria-label='Refresh runs'
                    >
                        {isLoadingRuns ? 'Loading…' : 'Refresh'}
                    </button>
                </div>
            </div>

            {hitlError && (
                <div className='arc-studio-runs__error' role='alert'>
                    HITL error: {hitlError}
                </div>
            )}

            {hitlPrompts.length > 0 && (
                <div className='arc-studio-runs__hitl-prompts' aria-label='Pending HITL prompts'>
                    <h4>Pending HITL Prompts ({hitlPrompts.length})</h4>
                    {hitlPrompts.map(p => (
                        <div key={p.promptId} className='arc-studio-runs__hitl-item'>
                            <div className='arc-studio-runs__hitl-info'>
                                <span className='arc-studio-runs__hitl-id' title={p.promptId}>
                                    {p.promptId.slice(0, 12)}…
                                </span>
                                <span className='arc-studio-runs__hitl-run'>Run: {p.runId.slice(0, 12)}…</span>
                                <span className='arc-studio-runs__hitl-prompt'>{(p.prompt || '').slice(0, 80)}</span>
                            </div>
                            <div className='arc-studio-runs__hitl-actions'>
                                <button
                                    className='theia-button primary'
                                    onClick={() => respondHitl(p, 'approve')}
                                    aria-label='Approve HITL prompt'
                                >
                                    Approve
                                </button>
                                <button
                                    className='theia-button secondary'
                                    onClick={() => respondHitl(p, 'reject')}
                                    aria-label='Reject HITL prompt'
                                >
                                    Reject
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

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

                    {/* Slice 7: Audit chain info */}
                    {selectedRunId && !isLoadingDetails && (
                        <div className='arc-studio-runs__audit'>
                            <button
                                className='theia-button secondary'
                                onClick={() => verifyAudit(selectedRunId)}
                                disabled={isVerifyingAudit}
                                aria-label='Verify audit chain'
                            >
                                {isVerifyingAudit ? 'Verifying…' : 'Verify Audit'}
                            </button>
                            {auditInfo && (
                                <div className='arc-studio-runs__audit-info' aria-label='Audit chain status'>
                                    <p>
                                        <strong>Audit path:</strong> {auditInfo.auditPath}
                                    </p>
                                    <p>
                                        <strong>Chain verified:</strong>{' '}
                                        <span className={auditInfo.chainVerified ? 'arc-studio-runs__verified' : 'arc-studio-runs__unverified'}>
                                            {auditInfo.chainVerified ? 'Yes' : 'No'}
                                        </span>
                                    </p>
                                    <p><strong>Records:</strong> {auditInfo.recordCount}</p>
                                    {auditInfo.signature && (
                                        <p><strong>Signature:</strong> <code>{auditInfo.signature.slice(0, 16)}…</code></p>
                                    )}
                                    {auditInfo.hmacAlgo && (
                                        <p><strong>HMAC algo:</strong> {auditInfo.hmacAlgo}</p>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Slice 7: Replay */}
                    {selectedRunId && !isLoadingDetails && (
                        <div className='arc-studio-runs__replay'>
                            <button
                                className='theia-button secondary'
                                onClick={() => handleReplay(selectedRunId)}
                                disabled={isReplaying}
                                aria-label='Replay run events'
                            >
                                {isReplaying ? 'Replaying…' : 'Replay Events'}
                            </button>
                            {replayEvents && replayEvents.length > 0 && (
                                <div className='arc-studio-runs__replay-events'>
                                    <strong>{replayEvents.length} events replayed</strong>
                                    <pre className='arc-studio-runs__replay-list'>
                                        {replayEvents.map((ev, i) => (
                                            <div key={i} className='arc-studio-runs__replay-event'>
                                                <span className='arc-studio-runs__replay-seq'>#{ev.sequence}</span>
                                                <span className='arc-studio-runs__replay-type'>[{ev.type}]</span>
                                                <span className='arc-studio-runs__replay-data'>{JSON.stringify(ev.data).slice(0, 200)}</span>
                                            </div>
                                        ))}
                                    </pre>
                                </div>
                            )}
                            {replayEvents && replayEvents.length === 0 && (
                                <p className='arc-studio-runs__no-events'>No events found for this run.</p>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
