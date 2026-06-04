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

const AUTO_REFRESH_INTERVAL_MS = 10_000;
const REPLAY_CATEGORIES = ['lifecycle', 'message', 'tool', 'error', 'hitl', 'audit', 'unknown'] as const;
type ReplayCategory = typeof REPLAY_CATEGORIES[number];

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

function auditMaterialExists(info: AuditChainInfo | null): boolean {
    return Boolean(info?.auditPath && info.recordCount > 0);
}

function auditStateCopy(state: AuditState): { variant: 'info' | 'success' | 'warning'; title: string; detail: string } {
    if (state === 'present') {
        return {
            variant: 'success',
            title: 'Run audit material verified',
            detail: 'This confirms only the audit chain available for this run, not adapter-wide keyed audit coverage.',
        };
    }
    if (state === 'degraded') {
        return {
            variant: 'warning',
            title: 'Audit material is degraded',
            detail: 'Run audit records exist, but chain verification failed or returned incomplete material.',
        };
    }
    return {
        variant: 'info',
        title: 'No run audit material found',
        detail: 'Verify/export is limited to runs that produced audit material on their execution path.',
    };
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

function downloadJson(data: unknown, filename: string): void {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
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

    const [autoRefreshEnabled, setAutoRefreshEnabled] = React.useState(true);
    const [lastRefreshedAt, setLastRefreshedAt] = React.useState<Date | null>(null);
    const [categoryFilters, setCategoryFilters] = React.useState<Set<ReplayCategory>>(new Set(REPLAY_CATEGORIES));

    const loadHitlPrompts = React.useCallback(async () => {
        setHitlLoading(true);
        setHitlError(null);
        try {
            setHitlPrompts(await arcService.listPendingHitlPrompts());
            setLastRefreshedAt(new Date());
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

    React.useEffect(() => {
        if (!autoRefreshEnabled) {
            return;
        }
        const intervalId = setInterval(() => {
            if (hitlRespondingId === null) {
                loadHitlPrompts();
            }
        }, AUTO_REFRESH_INTERVAL_MS);
        return () => clearInterval(intervalId);
    }, [autoRefreshEnabled, hitlRespondingId, loadHitlPrompts]);

    const filteredReplayEvents = React.useMemo(() => {
        if (categoryFilters.size === REPLAY_CATEGORIES.length) {
            return replayEvents;
        }
        return replayEvents.filter(evt => categoryFilters.has((evt.category ?? 'unknown') as ReplayCategory));
    }, [replayEvents, categoryFilters]);

    React.useEffect(() => {
        if (activeStep >= filteredReplayEvents.length && filteredReplayEvents.length > 0) {
            setActiveStep(filteredReplayEvents.length - 1);
        } else if (filteredReplayEvents.length === 0) {
            setActiveStep(0);
        }
    }, [filteredReplayEvents.length, activeStep]);

    const activeEvent = filteredReplayEvents[activeStep] ?? null;
    const filtersActive = categoryFilters.size < REPLAY_CATEGORIES.length;
    const filteredCount = replayEvents.length - filteredReplayEvents.length;
    const activeAnnotations = activeEvent ? eventAnnotations(activeEvent) : [];
    const state = auditState(auditInfo);
    const auditCopy = auditStateCopy(state);
    const canExportAudit = auditMaterialExists(auditInfo);

    return (
        <div className='arc-studio-assurance' role='region' aria-label='Assurance panel'>
            <section className='arc-studio-assurance__section arc-studio-assurance__hitl'>
                <div className='arc-studio-assurance__section-header'>
                    <h3>
                        HITL Inbox
                        {autoRefreshEnabled && (
                            <span className='arc-studio-assurance__live-badge' title='Auto-refreshing every 10s'><span className='arc-studio-assurance__live-dot' />LIVE</span>
                        )}
                    </h3>
                    <div className='arc-studio-assurance__section-actions'>
                        {lastRefreshedAt && (
                            <span className='arc-studio-assurance__timestamp'>
                                updated {lastRefreshedAt.toLocaleTimeString()}
                            </span>
                        )}
                        <button
                            className='arc-studio-assurance__button arc-studio-assurance__button--secondary'
                            onClick={() => {
                                downloadJson(hitlPrompts, `hitl-prompts-${Date.now()}.json`);
                            }}
                            disabled={hitlPrompts.length === 0}
                        >
                            Export HITL as JSON
                        </button>
                        <button
                            className='arc-studio-assurance__button'
                            onClick={loadHitlPrompts}
                            disabled={hitlLoading}
                        >
                            {hitlLoading ? 'Loading...' : 'Refresh'}
                        </button>
                    </div>
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
                <div className='arc-studio-assurance__section-header'>
                    <h3>Audit Chain Viewer</h3>
                    {canExportAudit && auditInfo && (
                        <button
                            className='arc-studio-assurance__button arc-studio-assurance__button--secondary'
                            onClick={() => {
                                downloadJson(auditInfo, `audit-chain-${auditInfo.runId}-${Date.now()}.json`);
                            }}
                        >
                            Export audit as JSON
                        </button>
                    )}
                </div>
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
                <div className={`arc-studio-assurance__state-banner arc-studio-assurance__state-banner--${auditCopy.variant}`}>
                    <span className='arc-studio-assurance__state-icon' aria-hidden='true'>{state === 'present' ? 'OK' : state === 'degraded' ? '!' : 'i'}</span>
                    <div className='arc-studio-assurance__state-body'>
                        <div className='arc-studio-assurance__state-title'>state: {state} — {auditCopy.title}</div>
                        <div className='arc-studio-assurance__state-detail'>{auditCopy.detail}</div>
                    </div>
                </div>
                {auditInfo && (
                    <dl className='arc-studio-assurance__details'>
                        <dt>run</dt><dd>{auditInfo.runId}</dd>
                        <dt>path</dt><dd>{auditInfo.auditPath || 'missing'}</dd>
                        <dt>records</dt><dd>{auditInfo.recordCount}</dd>
                        <dt>verified</dt><dd>{auditInfo.chainVerified ? 'yes' : 'no'}</dd>
                        {auditInfo.mode && <><dt>mode</dt><dd>{auditInfo.mode}</dd></>}
                        {auditInfo.recordsChecked != null && <><dt>records checked</dt><dd>{auditInfo.recordsChecked}</dd></>}
                        {auditInfo.durationMs != null && <><dt>duration</dt><dd>{auditInfo.durationMs} ms</dd></>}
                        {auditInfo.fileSizeBytes != null && <><dt>file size</dt><dd>{(auditInfo.fileSizeBytes / 1024).toFixed(1)} KB</dd></>}
                        {auditInfo.peakMemoryMb != null && <><dt>peak memory</dt><dd>{auditInfo.peakMemoryMb.toFixed(2)} MB</dd></>}
                        <dt>signature</dt><dd>{auditInfo.signature || 'not provided'}</dd>
                        <dt>hmac</dt><dd>{auditInfo.hmacAlgo || 'not provided'}</dd>
                    </dl>
                )}
            </section>

            <section className='arc-studio-assurance__section arc-studio-assurance__replay'>
                <div className='arc-studio-assurance__section-header'>
                    <h3>Replay Stepper</h3>
                    {replayEvents.length > 0 && (
                        <button
                            className='arc-studio-assurance__button arc-studio-assurance__button--secondary'
                            onClick={() => {
                                downloadJson(replayEvents, `replay-events-${Date.now()}.json`);
                            }}
                        >
                            Export events as JSON
                        </button>
                    )}
                </div>
                <div className='arc-studio-assurance__run-controls'>
                    <button className='arc-studio-assurance__button' onClick={loadReplay} disabled={replayLoading}>
                        {replayLoading ? 'Loading replay...' : 'Load Replay'}
                    </button>
                    <button onClick={() => setActiveStep(step => Math.max(0, step - 1))} disabled={activeStep <= 0}>Prev</button>
                    <button onClick={() => setActiveStep(step => Math.min(replayEvents.length - 1, step + 1))} disabled={activeStep >= filteredReplayEvents.length - 1}>Next</button>
                </div>
                {replayEvents.length > 0 && (
                    <div className='arc-studio-assurance__filter-bar'>
                        {REPLAY_CATEGORIES.map(category => (
                            <label className='arc-studio-assurance__filter-label' key={category}>
                                <input
                                    type='checkbox'
                                    className='arc-studio-assurance__filter-checkbox'
                                    checked={categoryFilters.has(category)}
                                    onChange={() => {
                                        setCategoryFilters(prev => {
                                            const next = new Set(prev);
                                            if (next.has(category)) {
                                                next.delete(category);
                                            } else {
                                                next.add(category);
                                            }
                                            return next;
                                        });
                                        setActiveStep(0);
                                    }}
                                />
                                {category}
                            </label>
                        ))}
                        {filtersActive && (
                            <button
                                className='arc-studio-assurance__filter-clear'
                                onClick={() => {
                                    setCategoryFilters(new Set(REPLAY_CATEGORIES));
                                    setActiveStep(0);
                                }}
                            >
                                Clear filters
                            </button>
                        )}
                    </div>
                )}
                {replayError && <div className='arc-studio-assurance__error' role='alert'>{replayError}</div>}
                {!replayLoading && replayEvents.length === 0 && (
                    <div className='arc-studio-assurance__empty'>No replay events loaded.</div>
                )}
                {!replayLoading && replayEvents.length > 0 && filteredReplayEvents.length === 0 && (
                    <div className='arc-studio-assurance__empty'>No events match the current filters.</div>
                )}
                {activeEvent && (
                    <article className='arc-studio-assurance__replay-card'>
                        <div className='arc-studio-assurance__replay-progress'>
                            step {activeStep + 1} / {filteredReplayEvents.length} ({replayTotal} total)
                            {filtersActive && <span className='arc-studio-assurance__filtered-count'> ({filteredCount} filtered)</span>}
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
