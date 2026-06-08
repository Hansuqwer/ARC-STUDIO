/**
 * Config Tab — v0.1 minimal config UI.
 *
 * Displays runtime, mode, workspace trust state, and provider key status.
 * Secrets are shown only as source/status — never raw values.
 * Gracefully handles unavailable backend.
 */

import * as React from '@theia/core/shared/react';
import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcService, SafeConfigUpdate, ProviderCatalogEntry } from '../../common/arc-protocol';
import {
    MODE_OPTIONS,
    PROVIDER_DISPLAY,
    formatMetadataKeys,
    providerSourceBadge,
    providerSourceColor,
} from './config-tab-helpers';
import { useConfigTabState } from './useConfigTabState';

export interface ConfigTabProps {
    arcService?: ArcService;
    onSave?: (update: SafeConfigUpdate) => void;
}

export const ConfigTab: React.FC<ConfigTabProps> = ({ arcService, onSave }) => {
    const {
        config,
        loading,
        saving,
        saveMessage,
        selectedRuntime,
        setSelectedRuntime,
        selectedMode,
        setSelectedMode,
        providerCatalog,
        selectedProvider,
        setSelectedProvider,
        providerEnvVar,
        setProviderEnvVar,
        selectedIsolation,
        setSelectedIsolation,
        selectedProfile,
        setSelectedProfile,
        dryRun,
        setDryRun,
        allowPaidCalls,
        setAllowPaidCalls,
        capabilities,
        capabilitiesLoading,
        profiles,
        isolationStatus,
        isolationProviders,
        exportText,
        setExportText,
        quotaProviderFilter,
        setQuotaProviderFilter,
        quotaResetting,
        quotaResetConfirmOpen,
        setQuotaResetConfirmOpen,
        quotaResetPhrase,
        setQuotaResetPhrase,
        liveProviderConfirmPhrase,
        setLiveProviderConfirmPhrase,
        providerActionLaunching,
        providerActionResult,
        providerTestResults,
        providerModels,
        testingProviders,
        expandedProviders,
        loadConfig,
        buildSafeExport,
        handleSave,
        testAllProviders,
        toggleProviderExpanded,
        runtimeOptionsWithCaps,
        diagnostics,
        quotaCounters,
        providerQuotaOptions,
        currentProfile,
        costPolicySummary,
        providerActionAvailable,
        providerTelemetryUnavailable,
        providerTelemetryError,
        providerTelemetryEmpty,
        quotaResetAvailable,
        quotaResetConfirmation,
        quotaResetRequiredPhrase,
        quotaResetConfirmed,
        selectedRuntimeCapability,
        runtimeRemediationPlan,
        exportTargetValidation,
        exportTargetCopyText,
        liveProviderGate,
        providerActionProvider,
        providerActionModel,
        liveProviderActionDisabled,
        handleProviderAction,
        handleResetQuota,
        handleSaveKeyRef,
    } = useConfigTabState({ arcService });

    if (loading) {
        return (
            <div className='arc-studio-config' role='region' aria-label='Config panel'>
                <div className='arc-studio-config__loading' style={{ padding: '16px', color: 'var(--theia-foreground)', textAlign: 'center' }}>
                    Loading configuration...
                </div>
            </div>
        );
    }

    if (!config || !config.backendAvailable) {
        return (
            <div className='arc-studio-config' role='region' aria-label='Config panel'>
                <div className='arc-studio-config__unavailable' style={{ padding: '16px' }}>
                    <h3>Config</h3>
                    <p style={{ color: 'var(--theia-errorForeground)', fontSize: '13px' }}>
                        Backend unavailable. {config?.backendMessage || 'Start the ARC daemon to manage configuration.'}
                    </p>
                    <button
                        className='arc-studio-config__retry'
                        onClick={loadConfig}
                        style={{ marginTop: '8px', padding: '4px 12px' }}
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className='arc-studio-config' role='region' aria-label='Config panel'>
            <div className='arc-studio-config__header' style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600 }}>Config</h3>
                <button
                    className='arc-studio-config__save'
                    onClick={handleSave}
                    disabled={saving}
                    aria-label='Save configuration'
                    style={{ padding: '4px 12px', fontSize: '12px' }}
                >
                    {saving ? 'Saving...' : 'Save'}
                </button>
                <button
                    className='arc-studio-config__export-safe'
                    onClick={() => setExportText(buildSafeExport())}
                    aria-label='Export safe configuration snapshot'
                    style={{ padding: '4px 12px', fontSize: '12px', marginLeft: '8px' }}
                >
                    Export safe snapshot
                </button>
            </div>

            {saveMessage && (
                <div className='arc-studio-config__message' style={{ padding: '6px 16px', fontSize: '12px', color: 'var(--theia-descriptionForeground)', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                    {saveMessage}
                </div>
            )}

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Runtime</h4>
                <div className='arc-studio-config__radio-group' style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {runtimeOptionsWithCaps.map(opt => {
                        const disabled = !opt.canRun;
                        return (
                            <label key={opt.value} style={{
                                display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px',
                                cursor: disabled ? 'not-allowed' : 'pointer',
                                opacity: disabled ? 0.55 : 1,
                            }}
                            title={disabled ? opt.description : ''}
                            >
                                <input
                                    type='radio'
                                    name='runtime'
                                    value={opt.value}
                                    checked={selectedRuntime === opt.value}
                                    onChange={() => !disabled && setSelectedRuntime(opt.value)}
                                    disabled={disabled}
                                />
                                <span style={{
                                    display: 'inline-block',
                                    padding: '1px 6px',
                                    borderRadius: '3px',
                                    fontSize: '10px',
                                    fontFamily: 'monospace',
                                    backgroundColor: disabled ? 'var(--theia-badge-background)' : 'var(--theia-badge-background)',
                                    color: disabled ? 'var(--theia-descriptionForeground)' : 'var(--theia-badge-foreground)',
                                    minWidth: '20px',
                                    textAlign: 'center',
                                }}>{opt.badge}</span>
                                <span>{opt.label}</span>
                                <span style={{
                                    fontSize: '11px',
                                    color: disabled ? 'var(--theia-editorWarning-foreground)' : 'var(--theia-descriptionForeground)',
                                }}>
                                    {disabled ? `⛔ ${opt.description}` : opt.description}
                                </span>
                            </label>
                        );
                    })}
                </div>
            </div>

            <div className='arc-studio-config__section arc-studio-config__runtime-setup-wizard' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Runtime Setup Wizard</h4>
                <p style={{ margin: '0 0 6px', fontSize: '12px', color: 'var(--theia-descriptionForeground)' }}>
                    {runtimeRemediationPlan.summary}
                </p>
                <p style={{ margin: '0 0 6px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    No raw secrets are captured or displayed. Env var names only; values stay in your shell/keychain.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px', fontSize: '11px' }}>
                    <span style={{ fontFamily: 'monospace' }}>runtime: {selectedRuntime}</span>
                    <span style={{ fontFamily: 'monospace' }}>status: {runtimeRemediationPlan.status}</span>
                    <span style={{ fontFamily: 'monospace' }}>setup: {selectedRuntimeCapability?.can_run ? 'detected' : 'needs setup'}</span>
                    {capabilitiesLoading && <span>refreshing...</span>}
                </div>
                {selectedRuntimeCapability && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px', marginBottom: '8px', fontSize: '11px' }}>
                        <div>
                            <strong>Metadata keys</strong>
                            <div style={{ marginTop: '4px', fontFamily: 'monospace', color: 'var(--theia-descriptionForeground)' }}>
                                {formatMetadataKeys(selectedRuntimeCapability.metadata)}
                            </div>
                        </div>
                        <div>
                            <strong>Trace metadata keys</strong>
                            <div style={{ marginTop: '4px', fontFamily: 'monospace', color: 'var(--theia-descriptionForeground)' }}>
                                {formatMetadataKeys(selectedRuntimeCapability.traceMetadata)}
                            </div>
                        </div>
                        <div>
                            <strong>Runtime gates</strong>
                            <div style={{ marginTop: '4px', fontFamily: 'monospace', color: 'var(--theia-descriptionForeground)' }}>
                                realRuntime={String(Boolean(selectedRuntimeCapability.realRuntimeGate))}; providerBacked={String(Boolean(selectedRuntimeCapability.providerBacked))}
                            </div>
                        </div>
                        <div>
                            <strong>Required env names</strong>
                            <div style={{ marginTop: '4px', fontFamily: 'monospace', color: 'var(--theia-descriptionForeground)' }}>
                                {(selectedRuntimeCapability.requiredEnv || selectedRuntimeCapability.required_env).length > 0 ? (selectedRuntimeCapability.requiredEnv || selectedRuntimeCapability.required_env).join(', ') : 'none'}
                            </div>
                        </div>
                        <div>
                            <strong>Detected artifacts</strong>
                            <div style={{ marginTop: '4px', fontFamily: 'monospace', color: 'var(--theia-descriptionForeground)' }}>
                                {runtimeRemediationPlan.artifacts.length > 0 ? runtimeRemediationPlan.artifacts.join(', ') : 'none'}
                            </div>
                        </div>
                        <div>
                            <strong>Doctor actions</strong>
                            <div style={{ marginTop: '4px', fontFamily: 'monospace', color: 'var(--theia-descriptionForeground)' }}>
                                {(selectedRuntimeCapability.doctorActions || selectedRuntimeCapability.doctor_actions).length > 0 ? `${(selectedRuntimeCapability.doctorActions || selectedRuntimeCapability.doctor_actions).length} available` : 'none'}
                            </div>
                        </div>
                    </div>
                )}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {exportTargetValidation.envName && (
                        <div className='arc-studio-config__export-target-guidance' style={{ padding: '8px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '4px', backgroundColor: 'var(--theia-editor-background)', fontSize: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'flex-start' }}>
                                <div>
                                    <strong>Export target env-ref</strong>
                                    <span className='arc-studio-config__export-target-status' style={{ marginLeft: '6px', fontSize: '10px', color: 'var(--theia-descriptionForeground)', fontFamily: 'monospace' }}>
                                        {exportTargetValidation.status}
                                    </span>
                                </div>
                                <button
                                    className='arc-studio-config__export-target-copy'
                                    onClick={() => navigator.clipboard?.writeText(exportTargetCopyText)}
                                    style={{ fontSize: '11px' }}
                                >
                                    Copy env-ref
                                </button>
                            </div>
                            <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>
                                {exportTargetValidation.message} Configure the shell/env only; ARC does not save export target values.
                            </p>
                            <div className='arc-studio-config__export-target-env' style={{ marginTop: '4px', fontSize: '11px' }}>
                                Env ref: <span style={{ fontFamily: 'monospace' }}>{exportTargetValidation.envName}</span>
                            </div>
                            <code className='arc-studio-config__export-target-module' style={{ display: 'block', marginTop: '4px', padding: '4px 6px', fontSize: '11px', whiteSpace: 'pre-wrap', backgroundColor: 'var(--theia-input-background)' }}>
                                {exportTargetCopyText}
                            </code>
                            <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>
                                {exportTargetValidation.remediation}
                            </p>
                        </div>
                    )}
                    {runtimeRemediationPlan.steps.length > 0 ? runtimeRemediationPlan.steps.map(step => {
                        const copyText = step.copyText || step.command || '';
                        const canCopy = Boolean(step.copyText || step.command);
                        return (
                            <div key={step.id} className='arc-studio-config__runtime-remediation-step' style={{ padding: '8px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '4px', backgroundColor: 'var(--theia-editor-background)', fontSize: '12px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'flex-start' }}>
                                    <div>
                                        <strong>{step.title}</strong>
                                        <span style={{ marginLeft: '6px', fontSize: '10px', color: 'var(--theia-descriptionForeground)', fontFamily: 'monospace' }}>{step.kind}</span>
                                    </div>
                                    {canCopy && (
                                        <button
                                            className='arc-studio-config__runtime-remediation-copy'
                                            onClick={() => navigator.clipboard?.writeText(copyText)}
                                            style={{ fontSize: '11px' }}
                                        >
                                            Copy
                                        </button>
                                    )}
                                </div>
                                <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>{step.description}</p>
                                {step.envVars && step.envVars.length > 0 && (
                                    <div style={{ marginTop: '4px', fontSize: '11px' }}>
                                        Env refs: <span style={{ fontFamily: 'monospace' }}>{step.envVars.join(', ')}</span>
                                    </div>
                                )}
                                {step.command && (
                                    <code className='arc-studio-config__runtime-remediation-command' style={{ display: 'block', marginTop: '4px', padding: '4px 6px', fontSize: '11px', whiteSpace: 'pre-wrap', backgroundColor: 'var(--theia-input-background)' }}>
                                        {step.command}
                                    </code>
                                )}
                            </div>
                        );
                    }) : (
                        <div className='arc-studio-config__runtime-remediation-step' style={{ fontSize: '12px', color: 'var(--theia-descriptionForeground)' }}>
                            No remediation steps available. Refresh runtime capabilities after installing dependencies.
                        </div>
                    )}
                </div>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Mode</h4>
                <div className='arc-studio-config__radio-group' style={{ display: 'flex', gap: '8px' }}>
                    {MODE_OPTIONS.map(opt => (
                        <label key={opt.value} style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '13px',
                            cursor: 'pointer',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            backgroundColor: selectedMode === opt.value ? 'var(--theia-list-activeSelectionBackground)' : 'transparent',
                            color: selectedMode === opt.value ? 'var(--theia-list-activeSelectionForeground)' : 'var(--theia-foreground)',
                        }}>
                            <input
                                type='radio'
                                name='mode'
                                value={opt.value}
                                checked={selectedMode === opt.value}
                                onChange={() => setSelectedMode(opt.value)}
                            />
                            <span>{opt.label}</span>
                            <span style={{ fontSize: '11px', opacity: 0.7 }}>({opt.description})</span>
                        </label>
                    ))}
                </div>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Workspace Trust</h4>
                <p className={config.workspace.trusted ? 'arc-studio-config__trusted' : 'arc-studio-config__untrusted'} style={{
                    margin: 0,
                    fontSize: '13px',
                    color: config.workspace.trusted ? 'var(--theia-terminal-ansiGreen)' : 'var(--theia-errorForeground)',
                }}>
                    {config.workspace.trusted ? '✓' : '✗'} Workspace {config.workspace.trusted ? 'trusted' : 'not trusted'}
                </p>
                <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)', fontFamily: 'monospace' }}>
                    {config.workspace.workspacePath}
                </p>
                <p style={{ margin: '2px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Trust level: {config.workspace.trustLevel}
                </p>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Run Policy</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px', fontSize: '12px' }}>
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        Isolation
                        <select
                            className='arc-studio-config__isolation-select'
                            value={selectedIsolation}
                            onChange={e => setSelectedIsolation(e.currentTarget.value)}
                        >
                            {isolationProviders.map(provider => (
                                <option key={provider.id} value={provider.id} disabled={!provider.available}>
                                    {provider.name || provider.id}{provider.available ? '' : ` — ${provider.reason || 'unavailable'}`}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        Profile
                        <select
                            className='arc-studio-config__profile-select'
                            value={selectedProfile}
                            onChange={e => setSelectedProfile(e.currentTarget.value)}
                        >
                            {profiles.map(profile => (
                                <option key={profile.id} value={profile.id}>
                                    {profile.name || profile.id}{profile.dryRun ? ' — dry-run' : ''}{profile.allowPaidCalls ? ' — paid allowed' : ''}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className='arc-studio-config__dry-run-toggle' style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <input
                            type='checkbox'
                            checked={dryRun}
                            onChange={e => {
                                const next = e.currentTarget.checked;
                                setDryRun(next);
                                if (next) setAllowPaidCalls(false);
                            }}
                        />
                        Dry run (providerCall:false)
                    </label>
                    <label className='arc-studio-config__paid-calls-toggle' style={{ display: 'flex', alignItems: 'center', gap: '6px', opacity: dryRun ? 0.6 : 1 }}>
                        <input
                            type='checkbox'
                            checked={!dryRun && allowPaidCalls}
                            disabled={dryRun}
                            onChange={e => setAllowPaidCalls(e.currentTarget.checked)}
                        />
                        Request backend paid-call opt-in (no provider call here)
                    </label>
                </div>
                <p className='arc-studio-config__run-policy-note' style={{ margin: '8px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    YAML-backed safe config save persists runtime, mode, isolation, dry-run, paid-call opt-in, and selected profile. Dry-run saves force paid calls off; provider auth remains env-var references only.
                </p>
                <p className='arc-studio-config__safe-fields-summary' style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Safe fields only: defaultRuntime={selectedRuntime}, mode={selectedMode}, isolation={selectedIsolation}, selectedProfile={selectedProfile}; no raw secrets or provider calls.
                </p>
                <p className='arc-studio-config__cost-policy-summary' style={{ margin: '4px 0 0', fontSize: '11px', color: dryRun || !allowPaidCalls ? 'var(--theia-descriptionForeground)' : 'var(--theia-editorWarning-foreground)' }}>
                    Local cost preview: {costPolicySummary.label}. Dry-run blocks paid calls; current profile dryRun={String(Boolean(currentProfile?.dryRun))}, allowPaidCalls={String(Boolean(currentProfile?.allowPaidCalls))}; effective allowPaidCalls={String(costPolicySummary.paidCallsAllowed)}. backend-enforced opt-in gates; this UI does not enable provider execution.
                </p>
                {isolationStatus?.message && (
                    <p className='arc-studio-config__isolation-message' style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                        Isolation status: {isolationStatus.message}
                    </p>
                )}
            </div>

            <div className='arc-studio-config__section arc-studio-config__provider-cost' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                    <h4 style={{ margin: 0, fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Provider Diagnostics & Local Quota Preview</h4>
                    <button
                        className='arc-studio-config__provider-refresh'
                        onClick={loadConfig}
                        disabled={loading}
                    >
                        Refresh provider status
                    </button>
                </div>
                <p className='arc-studio-config__paid-call-warning' style={{ margin: '8px 0', fontSize: '11px', color: 'var(--theia-editorWarning-foreground)' }}>
                    Provider diagnostics, proxy, gate, quota, and cost controls are preview-only in this UI. provider execution is not implemented here. This panel makes no provider network calls and does not enable real provider execution. Quota/cost display and reset use ARC local counters only, not provider remote quota.
                </p>
                <p className='arc-studio-config__provider-telemetry-state' style={{ margin: '0 0 8px', fontSize: '11px', color: providerTelemetryError ? 'var(--theia-editorWarning-foreground)' : 'var(--theia-descriptionForeground)' }}>
                    Provider telemetry state: {providerTelemetryUnavailable ? 'unavailable/degraded - backend method not wired; no provider call attempted' : providerTelemetryError ? 'error/degraded - local telemetry read failed; provider execution still disabled' : loading ? 'loading local telemetry...' : 'loaded from local ARC telemetry only'}.
                </p>
                <div className='arc-studio-config__live-provider-gate' style={{ margin: '8px 0', padding: '8px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '4px', fontSize: '11px', backgroundColor: 'var(--theia-editor-background)' }}>
                    <strong>Narrow provider action gate: {liveProviderGate.label || liveProviderGate.state || liveProviderGate.status || (dryRun || !allowPaidCalls ? 'blocked/gated' : 'preview-only')}</strong>
                    <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>
                        Default remains dry-run/offline. Live calls require backend gates: ARC_ALLOW_LIVE_PROVIDER_TESTS=true, paid-call opt-in, exact confirmation, env-ref key only. This is one narrow provider action, not provider-backed adoption or runtime support. Future live provider paths remain backend-gated and not launched from this panel.
                    </p>
                    <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>
                        {liveProviderGate.message || 'State derives from dry-run, paid-call opt-in, diagnostics metadata, and local cost policy only.'} Enforcement: {liveProviderGate.enforcement || 'backend-enforced opt-in; UI remains preview/offline and never enables provider execution.'}
                    </p>
                    <p className='arc-studio-config__provider-action-warning' style={{ margin: '6px 0 0', color: 'var(--theia-editorWarning-foreground)' }}>
                        {liveProviderGate.costWarning || 'Paid/live provider-backed action requires explicit confirmation; dry-run/offline remains default.'}
                    </p>
                    <p className='arc-studio-config__provider-accounting-label' style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>
                        {liveProviderGate.accountingLabel || 'Local accounting display uses ARC local counters only; no raw secrets, no remote quota, no billing read.'}
                    </p>
                    <div style={{ marginTop: '6px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                            Action target: <span style={{ fontFamily: 'monospace' }}>{providerActionProvider}</span> / <span style={{ fontFamily: 'monospace' }}>{providerActionModel}</span>; prompt is fixed smoke text; raw keys are never displayed. Local accounting only; no provider call attempted unless all backend gates pass.
                    </div>
                    <label className='arc-studio-config__provider-action-confirm' style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '6px' }}>
                        Paid-call confirmation phrase
                        <input
                            className='arc-studio-config__provider-action-confirm-input'
                            value={liveProviderConfirmPhrase}
                            onChange={e => setLiveProviderConfirmPhrase(e.currentTarget.value)}
                            placeholder={liveProviderGate.requiredPhrase || 'I UNDERSTAND THIS MAY COST MONEY'}
                            aria-label='Provider action paid-call confirmation phrase'
                        />
                    </label>
                    <button
                        className='arc-studio-config__provider-action-guarded'
                        disabled={liveProviderActionDisabled}
                        onClick={handleProviderAction}
                        style={{ marginTop: '6px', fontSize: '12px' }}
                    >
                        {providerActionLaunching ? 'Running gated provider action...' : providerActionAvailable ? 'Run one backend-gated provider action' : 'Backend action unavailable - fail closed'}
                    </button>
                    {providerActionResult && (
                        <div className='arc-studio-config__provider-action-result' style={{ marginTop: '6px', fontSize: '11px', color: providerActionResult.success ? 'var(--theia-descriptionForeground)' : 'var(--theia-editorWarning-foreground)' }}>
                            Result: success={String(providerActionResult.success)} blocked={String(providerActionResult.blocked)} dryRun={String(providerActionResult.dryRun)} providerCall={String(providerActionResult.providerCall)} provider={providerActionResult.provider || providerActionProvider} model={providerActionResult.model || providerActionModel}. {providerActionResult.message}
                        </div>
                    )}
                </div>
                <div className='arc-studio-config__provider-diagnostics' style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px', fontSize: '12px' }}>
                    <span>Backend live-test config (UI makes no calls): <span style={{ fontFamily: 'monospace' }}>{diagnostics.liveTestsEnabled ? 'configured for separate gated backend use' : 'disabled/gated'}</span></span>
                    <span>Routing default: <span style={{ fontFamily: 'monospace' }}>{diagnostics.routingDefault || 'unset'}</span></span>
                    <span>Configured providers: <span style={{ fontFamily: 'monospace' }}>{diagnostics.configuredProvidersCount}</span></span>
                    <span>Configured accounts: <span style={{ fontFamily: 'monospace' }}>{diagnostics.configuredAccountsCount}</span></span>
                </div>
                <p className='arc-studio-config__provider-paths-note' style={{ margin: '6px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Path legend: dry-run/offline = local preview only; local quota reset = ARC storage counters only; provider remote quota is not read or reset; narrow provider action = explicit backend-gated one-shot only.
                </p>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px', fontSize: '12px', maxWidth: '260px' }}>
                    Quota provider filter
                    <select
                        className='arc-studio-config__quota-provider-filter'
                        value={quotaProviderFilter}
                        onChange={e => setQuotaProviderFilter(e.currentTarget.value)}
                    >
                        <option value='all'>All providers</option>
                        {providerQuotaOptions.map(p => (
                            <option key={p.id} value={p.id}>{p.displayName || p.display_name || p.id}</option>
                        ))}
                    </select>
                </label>
                <div className='arc-studio-config__provider-quota' style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px', fontSize: '11px' }}>
                    {quotaCounters.length > 0 ? quotaCounters.map(row => (
                        <span key={row.key} className='arc-studio-config__quota-row' style={{ display: 'inline-flex', gap: '6px', padding: '2px 6px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '3px', fontFamily: 'monospace' }}>
                            <span className='arc-studio-config__quota-bucket'>{row.bucket}</span>
                            <span className='arc-studio-config__quota-scope'>{row.scope}</span>
                            <span>{row.id}</span>
                            <strong>{row.count}</strong>
                        </span>
                    )) : <span className='arc-studio-config__quota-empty' style={{ color: 'var(--theia-descriptionForeground)' }}>{providerTelemetryEmpty ? 'No local quota counters recorded yet. Run dry-run/offline flows to produce event-backed counters.' : 'Quota counters unavailable/degraded; no provider calls attempted.'}</span>}
                </div>
                {!quotaResetAvailable && (
                    <p className='arc-studio-config__quota-reset-disabled' style={{ margin: '6px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                        Local ARC quota reset disabled until local counters exist and the reset method is available. Provider remote quota is never changed here.
                    </p>
                )}
                {quotaResetAvailable && (
                    <div className='arc-studio-config__quota-reset-confirm' style={{ marginTop: '8px', padding: '8px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '4px', fontSize: '12px' }}>
                        <button
                            className='arc-studio-config__quota-reset-open'
                            onClick={() => setQuotaResetConfirmOpen(true)}
                            disabled={quotaResetting}
                        >
                            Local quota-counter reset
                        </button>
                        {quotaResetConfirmOpen && (
                            <div className='arc-studio-config__quota-reset-modal' role='dialog' aria-label='Confirm local quota-counter reset' style={{ marginTop: '8px' }}>
                                <p style={{ margin: '0 0 6px', color: 'var(--theia-editorWarning-foreground)' }}>
                                    Local ARC quota-counter reset only. No provider network, no provider remote quota change, no live API, no billing action.
                                </p>
                                <p style={{ margin: '0 0 6px', color: 'var(--theia-descriptionForeground)' }}>
                                    Type exact phrase <code>{quotaResetRequiredPhrase}</code> to enable reset. {quotaResetConfirmation.warning || quotaResetConfirmation.description || ''}
                                </p>
                                <input
                                    className='arc-studio-config__quota-reset-phrase'
                                    value={quotaResetPhrase}
                                    onChange={e => setQuotaResetPhrase(e.currentTarget.value)}
                                    placeholder={quotaResetRequiredPhrase}
                                    aria-label='Quota reset confirmation phrase'
                                />
                                <button
                                    className='arc-studio-config__quota-reset-local'
                                    onClick={handleResetQuota}
                                    disabled={quotaResetting || !quotaResetConfirmed}
                                    style={{ marginLeft: '8px', fontSize: '12px' }}
                                >
                                    {quotaResetting ? 'Resetting local quota counters...' : 'Confirm local reset'}
                                </button>
                                <button
                                    className='arc-studio-config__quota-reset-cancel'
                                    onClick={() => { setQuotaResetConfirmOpen(false); setQuotaResetPhrase(''); }}
                                    disabled={quotaResetting}
                                    style={{ marginLeft: '6px', fontSize: '12px' }}
                                >
                                    Cancel
                                </button>
                            </div>
                        )}
                    </div>
                )}
                <p className='arc-studio-config__quota-reset-note' style={{ margin: '6px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Local quota-counter reset calls ARC CLI local storage only; no provider network calls, no provider remote quota changes, no live API calls, no billing action.
                </p>
            </div>

            {exportText && (
                <div className='arc-studio-config__section arc-studio-config__safe-export' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                    <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Safe Config Snapshot</h4>
                    <p style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                        Copy-safe JSON. Contains status/source metadata only; no raw credentials.
                    </p>
                    <pre className='arc-studio-config__safe-export-json' style={{ maxHeight: '220px', overflow: 'auto', fontSize: '11px' }}>{exportText}</pre>
                </div>
            )}

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Provider Key Reference</h4>
                <p style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Save an environment variable name only. ARC does not capture raw key material.
                </p>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px', marginBottom: '8px' }}>
                    Provider
                    <select
                        className='arc-studio-config__provider-dropdown'
                        value={selectedProvider}
                        onChange={e => {
                            const next = e.currentTarget.value;
                            const entry = providerCatalog.find(p => p.id === next);
                            setSelectedProvider(next);
                            setProviderEnvVar(entry?.envKeyNames?.[0] || entry?.env_key_names?.[0] || '');
                        }}
                    >
                        {(providerCatalog.length ? providerCatalog : [{ id: 'openai', displayName: 'OpenAI', display_name: 'OpenAI' } as ProviderCatalogEntry]).map(p => (
                            <option key={p.id} value={p.id}>{p.displayName || p.display_name || p.id}</option>
                        ))}
                    </select>
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px', marginBottom: '8px' }}>
                    API key via env var
                    <input
                        className='arc-studio-config__provider-env-input'
                        value={providerEnvVar}
                        onChange={e => setProviderEnvVar(e.currentTarget.value)}
                        placeholder='OPENAI_API_KEY'
                    />
                </label>
                <button
                    className='arc-studio-config__save-key-ref'
                    onClick={handleSaveKeyRef}
                    disabled={saving || !providerEnvVar.trim()}
                >
                    Save key reference
                </button>
                <p className='arc-studio-config__web-auth-warning' style={{ margin: '8px 0 0', fontSize: '11px', color: 'var(--theia-editorWarning-foreground)' }}>
                    Web session auth is research-only. ARC does not capture browser cookies or passphrases. Use official API/OAuth where available.
                </p>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <h4 style={{ margin: 0, fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Providers</h4>
                    <button
                        onClick={testAllProviders}
                        disabled={testingProviders || !arcService}
                        style={{
                            padding: '4px 8px',
                            fontSize: '11px',
                            borderRadius: '3px',
                            border: '1px solid var(--theia-button-border)',
                            backgroundColor: 'var(--theia-button-background)',
                            color: 'var(--theia-button-foreground)',
                            cursor: testingProviders ? 'wait' : 'pointer',
                            opacity: testingProviders ? 0.6 : 1,
                        }}
                    >
                        {testingProviders ? 'Testing...' : 'Test All'}
                    </button>
                </div>
                <p style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Keys shown as source/status only — raw values are never displayed.
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {config.providers.map(p => {
                        const testResult = providerTestResults.get(p.provider);
                        const models = providerModels.get(p.provider) || [];
                        const isExpanded = expandedProviders.has(p.provider);
                        
                        // Determine status color
                        let statusColor = '#999'; // default/unset
                        let statusIcon = '○';
                        
                        if (testResult) {
                            if (testResult.status === 'success') {
                                statusColor = '#66bb6a'; // green
                                statusIcon = '✓';
                            } else if (testResult.status === 'warning') {
                                statusColor = '#ffb74d'; // yellow
                                statusIcon = '⚠';
                            } else if (testResult.status === 'error') {
                                statusColor = '#f44336'; // red
                                statusIcon = '✗';
                            }
                        } else if (p.configured) {
                            statusColor = providerSourceColor(p.source);
                            statusIcon = '✓';
                        } else {
                            statusIcon = '✗';
                        }
                        
                        return (
                            <div key={p.provider} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                <div className='arc-studio-config__provider' style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    padding: '6px 8px',
                                    borderRadius: '4px',
                                    backgroundColor: 'var(--theia-editor-background)',
                                    fontSize: '12px',
                                    cursor: models.length > 0 ? 'pointer' : 'default',
                                }}
                                onClick={() => models.length > 0 && toggleProviderExpanded(p.provider)}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{ 
                                            fontWeight: 500,
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '6px',
                                        }}>
                                            <span style={{ color: statusColor, fontSize: '14px' }}>{statusIcon}</span>
                                            {PROVIDER_DISPLAY[p.provider] || p.displayName || p.provider}
                                        </span>
                                        <span style={{
                                            display: 'inline-block',
                                            padding: '1px 6px',
                                            borderRadius: '3px',
                                            fontSize: '10px',
                                            fontFamily: 'monospace',
                                            color: providerSourceColor(p.source),
                                            border: `1px solid ${providerSourceColor(p.source)}40`,
                                        }}>
                                            {providerSourceBadge(p.source)}
                                        </span>
                                        {models.length > 0 && (
                                            <span style={{
                                                fontSize: '10px',
                                                color: 'var(--theia-descriptionForeground)',
                                                fontFamily: 'monospace',
                                            }}>
                                                {models.length} model{models.length !== 1 ? 's' : ''}
                                            </span>
                                        )}
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                                        {testResult && (
                                            <span style={{ 
                                                fontSize: '10px',
                                                color: statusColor,
                                                maxWidth: '200px',
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap',
                                            }}>
                                                {testResult.message}
                                            </span>
                                        )}
                                        {p.defaultModel && <span>model: {p.defaultModel}</span>}
                                        {p.envOverride && (
                                            <span className='arc-studio-config__env-override' style={{ fontFamily: 'monospace', opacity: 0.8 }}>
                                                env: {p.envOverride}
                                            </span>
                                        )}
                                        {models.length > 0 && (
                                            <span style={{ fontSize: '10px' }}>
                                                {isExpanded ? '▼' : '▶'}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                
                                {/* Expanded model list */}
                                {isExpanded && models.length > 0 && (
                                    <div style={{
                                        marginLeft: '16px',
                                        padding: '8px',
                                        borderRadius: '4px',
                                        backgroundColor: 'var(--theia-editor-background)',
                                        fontSize: '11px',
                                    }}>
                                        <div style={{ 
                                            fontWeight: 600, 
                                            marginBottom: '6px',
                                            color: 'var(--theia-descriptionForeground)',
                                            fontSize: '10px',
                                            textTransform: 'uppercase',
                                        }}>
                                            Available Models
                                        </div>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                            {models.slice(0, 10).map((model, idx) => (
                                                <div key={idx} style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'space-between',
                                                    padding: '4px 6px',
                                                    borderRadius: '3px',
                                                    backgroundColor: 'var(--theia-input-background)',
                                                }}>
                                                    <span style={{ fontFamily: 'monospace', fontSize: '10px' }}>
                                                        {model.model}
                                                    </span>
                                                    <div style={{ display: 'flex', gap: '6px', fontSize: '9px', color: 'var(--theia-descriptionForeground)' }}>
                                                        {model.capabilities?.supportsChat && <span title="Supports chat">💬</span>}
                                                        {model.capabilities?.supportsTools && <span title="Supports tools">🔧</span>}
                                                        {model.capabilities?.supportsStreaming && <span title="Supports streaming">⚡</span>}
                                                    </div>
                                                </div>
                                            ))}
                                            {models.length > 10 && (
                                                <div style={{ 
                                                    fontSize: '10px', 
                                                    color: 'var(--theia-descriptionForeground)',
                                                    fontStyle: 'italic',
                                                    padding: '4px 6px',
                                                }}>
                                                    ... and {models.length - 10} more
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Routing</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px' }}>
                    <span>Mode: <span style={{ fontFamily: 'monospace' }}>{config.runtime.routingMode}</span></span>
                    <span>Dry run: <span style={{ fontFamily: 'monospace' }}>{config.runtime.dryRun ? 'yes' : 'no'}</span></span>
                    <span>Isolation: <span style={{ fontFamily: 'monospace' }}>{config.runtime.isolation}</span></span>
                    <span>Profile: <span style={{ fontFamily: 'monospace' }}>{selectedProfile}</span></span>
                    <span>Paid calls: <span style={{ fontFamily: 'monospace', color: config.runtime.allowPaidCalls ? 'var(--theia-terminal-ansiYellow)' : 'var(--theia-descriptionForeground)' }}>{config.runtime.allowPaidCalls ? 'allowed' : 'blocked'}</span></span>
                </div>
            </div>
        </div>
    );
};

export class ConfigTabWidget extends ReactWidget {
    static readonly ID = 'arc:config-tab';
    static readonly LABEL = 'ARC Config';

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    @postConstruct()
    protected init(): void {
        this.id = ConfigTabWidget.ID;
        this.title.label = ConfigTabWidget.LABEL;
        this.title.closable = true;
        this.title.caption = 'ARC Studio Configuration';
        this.update();
    }

    protected render(): React.ReactNode {
        return <ConfigTab arcService={this.arcService} />;
    }
}
