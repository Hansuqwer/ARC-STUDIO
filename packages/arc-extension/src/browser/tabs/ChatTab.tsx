/**
 * Chat Tab
 *
 * Chat panel with runtime launch controls and local transcript.
 */

import * as React from '@theia/core/shared/react';
import { useState, useEffect } from '@theia/core/shared/react';
import { ArcService, ConfigStatus, RunPreflightResponse, RuntimeCapabilityReport } from '../../common/arc-protocol';

const FALLBACK_RUNTIMES: Record<string, { label: string }> = {
    'swarmgraph': { label: 'SwarmGraph standalone' },
    'crewai': { label: 'CrewAI standalone' },
    'crewai+swarmgraph': { label: 'CrewAI + SwarmGraph (fake/offline)' },
};

const FALLBACK_PROFILES = ['local-safe', 'local-paid'];
const FALLBACK_ISOLATION = ['subprocess', 'none'];

interface TranscriptMessage {
    id: number;
    role: 'user' | 'system';
    text: string;
}

export interface ChatTabProps {
    arcService?: ArcService;
    onSendMessage?: (message: string) => void;
    onNavigateToRuns?: (runId?: string) => void;
}

export const ChatTab: React.FC<ChatTabProps> = ({ arcService, onSendMessage, onNavigateToRuns }) => {
    const [input, setInput] = useState('');
    const [mode, setMode] = useState<'plan' | 'build' | 'auto'>('build');
    const [runtimeId, setRuntimeId] = useState('crewai+swarmgraph');
    const [profileId, setProfileId] = useState('local-safe');
    const [preflight, setPreflight] = useState<RunPreflightResponse | null>(null);
    const [preflightError, setPreflightError] = useState<string | null>(null);
    const [runMessage, setRunMessage] = useState<string | null>(null);
    const [lastRunId, setLastRunId] = useState<string | null>(null);
    const [lastTracePath, setLastTracePath] = useState<string | null>(null);
    const [capabilities, setCapabilities] = useState<RuntimeCapabilityReport[] | null>(null);
    const [configStatus, setConfigStatus] = useState<ConfigStatus | null>(null);
    const [isolationId, setIsolationId] = useState('subprocess');
    const [allowPaidCalls, setAllowPaidCalls] = useState(false);
    const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;
        if (onSendMessage) {
            onSendMessage(input.trim());
        }
        setTranscript(messages => [
            ...messages,
            { id: Date.now(), role: 'user', text: input.trim() },
        ]);
        setInput('');
    };

    const cycleMode = () => {
        const modes: Array<'plan' | 'build' | 'auto'> = ['plan', 'build', 'auto'];
        const idx = modes.indexOf(mode);
        setMode(modes[(idx + 1) % modes.length]);
    };

    const handlePreflight = async () => {
        if (!arcService?.preflightRun) return;
        setPreflightError(null);
        try {
            const result = await arcService.preflightRun({
                workflow: 'crew.py',
                prompt: input.trim() || undefined,
                runtimeId,
                profileId,
                allowPaidCalls,
                dryRun: true,
            });
            setPreflight(result);
            setTranscript(messages => [
                ...messages,
                { id: Date.now(), role: 'system', text: `Preflight ${result.runnable ? 'runnable' : 'blocked'} for ${result.runtime}` },
            ]);
        } catch (error) {
            setPreflightError(error instanceof Error ? error.message : 'Preflight failed');
        }
    };

    useEffect(() => {
        if (arcService?.listRuntimeCapabilities) {
            arcService.listRuntimeCapabilities()
                .then(resp => setCapabilities(resp.runtimes || []))
                .catch(() => setCapabilities(null));
        }
        if (arcService?.getConfigStatus) {
            arcService.getConfigStatus()
                .then(status => {
                    setConfigStatus(status);
                    setRuntimeId(status.runtime.defaultRuntime || runtimeId);
                    setIsolationId(status.runtime.isolation || isolationId);
                    setAllowPaidCalls(status.runtime.allowPaidCalls);
                })
                .catch(() => setConfigStatus(null));
        }
    }, [arcService]);

    const handleStartRun = async () => {
        if (!arcService?.startRun) return;
        setRunMessage(null);
        try {
            const result = await arcService.startRun({
                workflow: 'crew.py',
                prompt: input.trim() || undefined,
                runtimeId,
                profileId,
                allowPaidCalls,
            });
            setLastRunId(result.runId);
            setLastTracePath(result.tracePath || null);
            setRunMessage(`Run ${result.runId} completed`);
            setTranscript(messages => [
                ...messages,
                { id: Date.now(), role: 'system', text: `Run ${result.runId} completed` },
            ]);
        } catch (error) {
            setLastRunId(null);
            setLastTracePath(null);
            setRunMessage(`Run failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    };

    const runtimeOptions = capabilities?.length
        ? capabilities.map(cap => ({ value: cap.runtime_id, label: FALLBACK_RUNTIMES[cap.runtime_id]?.label || cap.runtime_id, cap }))
        : Object.entries(FALLBACK_RUNTIMES).map(([value, meta]) => ({ value, label: meta.label, cap: undefined }));
    const selectedCapability = capabilities?.find(cap => cap.runtime_id === runtimeId);
    const profileOptions = Array.from(new Set([
        ...(Array.isArray((configStatus as unknown as { profiles?: string[] } | null)?.profiles)
            ? (configStatus as unknown as { profiles: string[] }).profiles
            : []),
        ...FALLBACK_PROFILES,
    ]));
    const isolationOptions = Array.from(new Set([
        configStatus?.runtime.isolation,
        ...FALLBACK_ISOLATION,
    ].filter(Boolean) as string[]));
    const showPaidCallWarning = Boolean(
        selectedCapability?.requires_paid_calls || preflight?.paidCallRequired || allowPaidCalls,
    );

    return (
        <div className='arc-studio-chat' role='region' aria-label='Chat panel'>
            <div className='arc-studio-chat__header'>
                <span className='arc-studio-chat__mode' onClick={cycleMode} title='Click to cycle mode'>
                    Mode: {mode}
                </span>
            </div>

            <div className='arc-studio-chat__messages' aria-live='polite'>
                <div className='arc-studio-chat__placeholder'>
                    <p>Chat is ready. Type a message or use slash commands.</p>
                    <p className='arc-studio-chat__hint'>
                        Try: /help /config /runtime /status /workflows
                    </p>
                </div>
                <div className='arc-studio-chat__runtime-preflight'>
                    <label>
                        Runtime
                        <select className='arc-studio-chat__runtime-selector' value={runtimeId} onChange={e => setRuntimeId(e.currentTarget.value)}>
                            {runtimeOptions.map(({ value, label, cap }) => {
                                const disabled = cap !== undefined && !cap.can_run && value !== 'crewai+swarmgraph';
                                const reason = disabled ? (cap?.reason || 'not available') : '';
                                return (
                                    <option key={value} value={value} disabled={disabled} title={reason}>
                                        {label}{reason ? ` (${reason})` : ''}
                                    </option>
                                );
                            })}
                        </select>
                    </label>
                    <div className='arc-studio-chat__runtime-readiness' aria-live='polite'>
                        Readiness: {selectedCapability ? (selectedCapability.can_run ? 'ready' : 'blocked') : 'unknown'}
                        {selectedCapability?.availability && ` (${selectedCapability.availability})`}
                        {selectedCapability?.requires_paid_calls && ' - paid calls required'}
                        {selectedCapability?.reason && ` - ${selectedCapability.reason}`}
                    </div>
                    <label>
                        Profile
                        <select className='arc-studio-chat__profile-selector' value={profileId} onChange={e => setProfileId(e.currentTarget.value)}>
                            {profileOptions.map(profile => <option key={profile} value={profile}>{profile}</option>)}
                        </select>
                    </label>
                    <label>
                        Isolation
                        <select className='arc-studio-chat__isolation-selector' value={isolationId} onChange={e => setIsolationId(e.currentTarget.value)}>
                            {isolationOptions.map(isolation => <option key={isolation} value={isolation}>{isolation}</option>)}
                        </select>
                    </label>
                    <div className='arc-studio-chat__runtime-policy' aria-live='polite'>
                        Profile: {profileId} | Isolation: {isolationId} | Dry-run providerCall:false
                    </div>
                    {showPaidCallWarning && (
                        <div className='arc-studio-chat__paid-call-warning' role='alert'>
                            Paid provider calls require explicit opt-in. Dry-run preflight makes no provider calls (providerCall:false).
                            {selectedCapability?.requires_paid_calls && ' Selected runtime capability requires paid calls.'}
                            {preflight?.paidCallRequired && ' Preflight says paid calls are required.'}
                            {allowPaidCalls && ' Paid calls are currently enabled for the next explicit run action.'}
                        </div>
                    )}
                    <label className='arc-studio-chat__paid-calls'>
                        <input
                            type='checkbox'
                            checked={allowPaidCalls}
                            onChange={e => setAllowPaidCalls(e.currentTarget.checked)}
                        />
                        Allow paid calls
                    </label>
                    <button type='button' className='arc-studio-chat__dry-run' onClick={handlePreflight} disabled={!arcService?.preflightRun}>
                        Dry-run preflight
                    </button>
                    <button type='button' className='arc-studio-chat__run' onClick={handleStartRun} disabled={!arcService?.startRun || (!!preflight && !preflight.runnable)}>
                        Run fake/offline
                    </button>
                    {preflight && (
                        <div className='arc-studio-chat__preflight-result'>
                            <strong>{preflight.runtime}</strong>: {preflight.runnable ? 'Runnable' : 'Blocked'}
                            {preflight.blockers.length > 0 && (
                                <ul className='arc-studio-chat__blockers'>
                                    {preflight.blockers.map(blocker => <li key={blocker.code}>{blocker.code}: {blocker.message}</li>)}
                                </ul>
                            )}
                            {preflight.warnings.map(warning => <p key={warning} className='arc-studio-chat__warning'>{warning}</p>)}
                        </div>
                    )}
                    {preflightError && <p className='arc-studio-chat__preflight-error'>{preflightError}</p>}
                    {runMessage && (
                        <div className='arc-studio-chat__run-result'>
                            <p className='arc-studio-chat__run-message'>{runMessage}</p>
                            {lastRunId && (
                                <div className='arc-studio-chat__run-actions'>
                                    {lastTracePath && (
                                        <span className='arc-studio-chat__trace-path' title={lastTracePath}>
                                            Trace: {lastTracePath.split('/').pop()}
                                        </span>
                                    )}
                                    <button
                                        type='button'
                                        className='arc-studio-chat__view-runs'
                                        onClick={() => onNavigateToRuns?.(lastRunId)}
                                    >
                                        View in Runs
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                </div>
                {transcript.length > 0 && (
                    <div className='arc-studio-chat__transcript'>
                        {transcript.map(message => (
                            <p key={message.id} className={`arc-studio-chat__transcript-${message.role}`}>
                                {message.text}
                            </p>
                        ))}
                    </div>
                )}
            </div>

            <form className='arc-studio-chat__input' onSubmit={handleSubmit}>
                <input
                    type='text'
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder='Type a message or /command...'
                    aria-label='Chat input'
                    className='arc-studio-chat__input-field'
                />
                <button
                    type='submit'
                    className='arc-studio-chat__send'
                    disabled={!input.trim()}
                    aria-label='Send message'
                >
                    Send
                </button>
            </form>
        </div>
    );
};
