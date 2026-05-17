/**
 * Assurance Tab
 *
 * Dedicated HITL inbox, audit-chain viewer, and replay stepper.
 */

import * as React from '@theia/core/shared/react';
import type {
    ArcService,
    AuditChainInfo,
    HitlPromptInfo,
    ReplayEvent,
} from '../../common/arc-protocol';

export interface AssuranceTabProps {
    arcService: ArcService;
    initialRunId?: string | null;
}

type HitlDecision = 'approve' | 'reject' | 'modify';
type AuditState = 'present' | 'missing' | 'degraded';

interface HitlDrafts {
    [promptId: string]: string;
}

function formatTime(value?: string): string {
    if (!value) {
        return 'not provided';
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function isExpired(value?: string): boolean {
    if (!value) {
        return false;
    }
    const time = new Date(value).getTime();
    return !Number.isNaN(time) && time <= Date.now();
}

function hitlBlocked(prompt: HitlPromptInfo): boolean {
    return !prompt.token || isExpired(prompt.expiresAt);
}

function auditState(info: AuditChainInfo | null): AuditState {
    if (!info || !info.auditPath || info.recordCount <= 0) {
        return 'missing';
    }
    return info.chainVerified ? 'present' : 'degraded';
}

function eventText(event: ReplayEvent): string {
    return `${event.type} ${JSON.stringify(event.data ?? {})}`.toUpperCase();
}

function eventAnnotations(event: ReplayEvent): string[] {
    const text = eventText(event);
    return ['HITL', 'AUDIT', 'APPROVAL', 'REPLAY'].filter(marker => text.includes(marker));
}

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

export const AssuranceTab: React.FC<AssuranceTabProps> = ({ arcService, initialRunId }) => {
    const [hitlPrompts, setHitlPrompts] = React.useState<HitlPromptInfo[]>([]);
    const [hitlDrafts, setHitlDrafts] = React.useState<HitlDrafts>({});
    const [hitlLoading, setHitlLoading] = React.useState(false);
    const [hitlRespondingId, setHitlRespondingId] = React.useState<string | null>(null);
    const [hitlError, setHitlError] = React.useState<string | null>(null);

    const [runId, setRunId] = React.useState(initialRunId ?? '');
    const [auditInfo, setAuditInfo] = React.useState<AuditChainInfo | null>(null);
    const [auditLoading, setAuditLoading] = React.useState(false);
    const [auditError, setAuditError] = React.useState<string | null>(null);

    const [replayEvents, setReplayEvents] = React.useState<ReplayEvent[]>([]);
    const [replayTotal, setReplayTotal] = React.useState(0);
    const [activeStep, setActiveStep] = React.useState(0);
    const [replayLoading, setReplayLoading] = React.useState(false);
    const [replayError, setReplayError] = React.useState<string | null>(null);

    const loadHitlPrompts = React.useCallback(async () => {
        setHitlLoading(true);
        setHitlError(null);
        try {
            setHitlPrompts(await arcService.listPendingHitlPrompts());
        } catch (error) {
            setHitlError(errorMessage(error));
        } finally {
            setHitlLoading(false);
        }
    }, [arcService]);

    const respondHitl = React.useCallback(async (prompt: HitlPromptInfo, decision: HitlDecision) => {
        if (hitlBlocked(prompt)) {
            setHitlError(`Prompt ${prompt.promptId} has missing or expired token.`);
            return;
        }
        setHitlRespondingId(prompt.promptId);
        setHitlError(null);
        try {
            await arcService.respondHitlPrompt({
                promptId: prompt.promptId,
                decision,
                response: decision === 'modify' ? hitlDrafts[prompt.promptId] ?? '' : undefined,
                token: prompt.token!,
            });
            await loadHitlPrompts();
        } catch (error) {
            setHitlError(errorMessage(error));
        } finally {
            setHitlRespondingId(null);
        }
    }, [arcService, hitlDrafts, loadHitlPrompts]);

    const verifyAudit = React.useCallback(async () => {
        const trimmedRunId = runId.trim();
        if (!trimmedRunId) {
            setAuditError('Run id required.');
            return;
        }
        setAuditLoading(true);
        setAuditError(null);
        setAuditInfo(null);
        try {
            setAuditInfo(await arcService.getAuditChainInfo(trimmedRunId));
        } catch (error) {
            setAuditError(errorMessage(error));
        } finally {
            setAuditLoading(false);
        }
    }, [arcService, runId]);

    const loadReplay = React.useCallback(async () => {
        const trimmedRunId = runId.trim();
        if (!trimmedRunId) {
            setReplayError('Run id required.');
            return;
        }
        setReplayLoading(true);
        setReplayError(null);
        setReplayEvents([]);
        setReplayTotal(0);
        setActiveStep(0);
        try {
            const result = await arcService.replayRun(trimmedRunId);
            setReplayEvents(result.events ?? []);
            setReplayTotal(result.totalEvents ?? result.events?.length ?? 0);
        } catch (error) {
            setReplayError(errorMessage(error));
        } finally {
            setReplayLoading(false);
        }
    }, [arcService, runId]);

    React.useEffect(() => {
        loadHitlPrompts();
    }, [loadHitlPrompts]);

    const activeEvent = replayEvents[activeStep] ?? null;
    const activeAnnotations = activeEvent ? eventAnnotations(activeEvent) : [];
    const state = auditState(auditInfo);

    return (
        <div className='arc-studio-assurance' role='region' aria-label='Assurance panel'>
            <section className='arc-studio-assurance__section arc-studio-assurance__hitl'>
                <div className='arc-studio-assurance__section-header'>
                    <h3>HITL Inbox</h3>
                    <button
                        className='arc-studio-assurance__button'
                        onClick={loadHitlPrompts}
                        disabled={hitlLoading}
                    >
                        {hitlLoading ? 'Loading...' : 'Refresh'}
                    </button>
                </div>

                {hitlError && <div className='arc-studio-assurance__error' role='alert'>{hitlError}</div>}
                {!hitlLoading && hitlPrompts.length === 0 && (
                    <div className='arc-studio-assurance__empty'>No pending HITL prompts.</div>
                )}

                <div className='arc-studio-assurance__hitl-list'>
                    {hitlPrompts.map(prompt => {
                        const expired = isExpired(prompt.expiresAt);
                        const blocked = hitlBlocked(prompt);
                        const responding = hitlRespondingId === prompt.promptId;
                        return (
                            <article className='arc-studio-assurance__hitl-card' key={prompt.promptId}>
                                <div className='arc-studio-assurance__hitl-meta'>
                                    <strong>{prompt.promptId}</strong>
                                    <span>run {prompt.runId}</span>
                                    <span>created {formatTime(prompt.createdAt)}</span>
                                    <span>expires {formatTime(prompt.expiresAt)}</span>
                                    {!prompt.token && <span className='arc-studio-assurance__status'>token missing</span>}
                                    {expired && <span className='arc-studio-assurance__status'>token expired</span>}
                                </div>
                                <div className='arc-studio-assurance__hitl-prompt'>{prompt.prompt}</div>
                                <textarea
                                    className='arc-studio-assurance__textarea'
                                    value={hitlDrafts[prompt.promptId] ?? ''}
                                    onChange={event => setHitlDrafts(prev => ({
                                        ...prev,
                                        [prompt.promptId]: event.currentTarget.value,
                                    }))}
                                    placeholder='Optional modified response'
                                    disabled={blocked || responding}
                                />
                                <div className='arc-studio-assurance__actions'>
                                    <button onClick={() => respondHitl(prompt, 'approve')} disabled={blocked || responding}>Approve</button>
                                    <button onClick={() => respondHitl(prompt, 'reject')} disabled={blocked || responding}>Reject</button>
                                    <button onClick={() => respondHitl(prompt, 'modify')} disabled={blocked || responding}>Respond</button>
                                </div>
                            </article>
                        );
                    })}
                </div>
            </section>

            <section className='arc-studio-assurance__section arc-studio-assurance__audit'>
                <h3>Audit Chain Viewer</h3>
                <div className='arc-studio-assurance__run-controls'>
                    <input
                        className='arc-studio-assurance__input'
                        value={runId}
                        onChange={event => setRunId(event.currentTarget.value)}
                        placeholder='Run id'
                    />
                    <button className='arc-studio-assurance__button' onClick={verifyAudit} disabled={auditLoading}>
                        {auditLoading ? 'Verifying...' : 'Verify'}
                    </button>
                </div>
                <p className='arc-studio-assurance__note'>No adapter-wide keyed audit/HMAC claim. This view reports available run audit material only.</p>
                {auditError && <div className='arc-studio-assurance__error' role='alert'>{auditError}</div>}
                <div className='arc-studio-assurance__audit-state'>state: {state}</div>
                {auditInfo && (
                    <dl className='arc-studio-assurance__details'>
                        <dt>run</dt><dd>{auditInfo.runId}</dd>
                        <dt>path</dt><dd>{auditInfo.auditPath || 'missing'}</dd>
                        <dt>records</dt><dd>{auditInfo.recordCount}</dd>
                        <dt>verified</dt><dd>{auditInfo.chainVerified ? 'yes' : 'no'}</dd>
                        <dt>signature</dt><dd>{auditInfo.signature || 'not provided'}</dd>
                        <dt>hmac</dt><dd>{auditInfo.hmacAlgo || 'not provided'}</dd>
                    </dl>
                )}
            </section>

            <section className='arc-studio-assurance__section arc-studio-assurance__replay'>
                <h3>Replay Stepper</h3>
                <div className='arc-studio-assurance__run-controls'>
                    <button className='arc-studio-assurance__button' onClick={loadReplay} disabled={replayLoading}>
                        {replayLoading ? 'Loading replay...' : 'Load Replay'}
                    </button>
                    <button onClick={() => setActiveStep(step => Math.max(0, step - 1))} disabled={activeStep <= 0}>Prev</button>
                    <button onClick={() => setActiveStep(step => Math.min(replayEvents.length - 1, step + 1))} disabled={activeStep >= replayEvents.length - 1}>Next</button>
                </div>
                {replayError && <div className='arc-studio-assurance__error' role='alert'>{replayError}</div>}
                {!replayLoading && replayEvents.length === 0 && (
                    <div className='arc-studio-assurance__empty'>No replay events loaded.</div>
                )}
                {activeEvent && (
                    <article className='arc-studio-assurance__replay-card'>
                        <div className='arc-studio-assurance__replay-progress'>
                            step {activeStep + 1} / {replayEvents.length} ({replayTotal} total)
                        </div>
                        <div className='arc-studio-assurance__replay-meta'>
                            <strong>{activeEvent.type}</strong>
                            <span>{formatTime(activeEvent.timestamp)}</span>
                            <span>sequence {activeEvent.sequence}</span>
                        </div>
                        {activeAnnotations.length > 0 && (
                            <div className='arc-studio-assurance__annotations'>
                                {activeAnnotations.map(annotation => (
                                    <span className='arc-studio-assurance__annotation' key={annotation}>{annotation}</span>
                                ))}
                            </div>
                        )}
                        <pre className='arc-studio-assurance__event-data'>
                            {JSON.stringify(activeEvent.data, null, 2)}
                        </pre>
                    </article>
                )}
            </section>
        </div>
    );
};
