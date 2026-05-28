/**
 * CI Guardrails Tab
 *
 * Standalone tab for CI guardrails check status: overall pass/fail,
 * per-check results (sandbox_audit, policy, eval, receipt), and metadata.
 * Previously rendered as a sub-panel in CommandCentreTab.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, CiCheckStatus } from '../../common/arc-protocol';

export interface CiGuardrailsTabProps {
    arcService: ArcService;
}

export const CiGuardrailsTab: React.FC<CiGuardrailsTabProps> = ({ arcService }) => {
    const [status, setStatus] = React.useState<CiCheckStatus | null>(null);
    const [loading, setLoading] = React.useState<boolean>(true);
    const [error, setError] = React.useState<string | null>(null);

    const load = React.useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const s = await arcService.getCiCheckStatus();
            setStatus(s);
        } catch (err: any) {
            setError(err.message || 'Failed to load CI guardrails status');
        } finally {
            setLoading(false);
        }
    }, [arcService]);

    React.useEffect(() => {
        load();
    }, [load]);

    const overallPassed = status?.overall === 'pass';

    if (loading) {
        return (
            <div className='arc-ci-guardrails' role='region' aria-label='CI Guardrails'>
                <h3>CI Guardrails</h3>
                <p className='arc-ci-guardrails__loading'>Loading CI guardrails status...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className='arc-ci-guardrails' role='region' aria-label='CI Guardrails'>
                <h3>CI Guardrails</h3>
                <div className='arc-ci-guardrails__error' role='alert'>Error: {error}</div>
                <button className='arc-ci-guardrails__refresh' onClick={load}>Retry</button>
            </div>
        );
    }

    if (!status) {
        return (
            <div className='arc-ci-guardrails' role='region' aria-label='CI Guardrails'>
                <div className='arc-ci-guardrails__header'>
                    <h3>CI Guardrails</h3>
                    <button className='arc-ci-guardrails__refresh' onClick={load}>Refresh</button>
                </div>
                <p className='arc-ci-guardrails__empty'>CI guardrails status unavailable.</p>
            </div>
        );
    }

    const checkKeys = Object.keys(status.checks);

    return (
        <div className='arc-ci-guardrails' role='region' aria-label='CI Guardrails'>
            <div className='arc-ci-guardrails__header'>
                <h3>CI Guardrails</h3>
                <button className='arc-ci-guardrails__refresh' onClick={load}>Refresh</button>
            </div>

            <section className='arc-ci-guardrails__section'>
                <h4>Overall Status</h4>
                <div className='arc-ci-guardrails__field'>
                    <span className='arc-ci-guardrails__label'>Overall:</span>
                    <span className={`arc-ci-guardrails__badge ${overallPassed ? 'arc-ci-guardrails__badge--pass' : 'arc-ci-guardrails__badge--fail'}`}>
                        {overallPassed ? 'Pass' : 'Fail'}
                    </span>
                </div>
                <div className='arc-ci-guardrails__field'>
                    <span className='arc-ci-guardrails__label'>Private mode:</span>
                    <span>{status.private ? 'Yes' : 'No'}</span>
                </div>
                {status.checkedAt && (
                    <div className='arc-ci-guardrails__field'>
                        <span className='arc-ci-guardrails__label'>Checked at:</span>
                        <span>{status.checkedAt}</span>
                    </div>
                )}
            </section>

            <section className='arc-ci-guardrails__section'>
                <h4>Checks ({checkKeys.length})</h4>
                {checkKeys.length === 0 && (
                    <p className='arc-ci-guardrails__empty'>No checks recorded.</p>
                )}
                {checkKeys.length > 0 && (
                    <div className='arc-ci-guardrails__check-list'>
                        {checkKeys.map(key => {
                            const check = status.checks[key] ?? {};
                            const checkPassed = String(check.result ?? check.status ?? 'unknown') === 'pass';
                            return (
                                <div key={key} className='arc-ci-guardrails__check-card'>
                                    <div className='arc-ci-guardrails__check-header'>
                                        <strong>{key}</strong>
                                        <span className={`arc-ci-guardrails__check-badge ${checkPassed ? 'arc-ci-guardrails__badge--pass' : 'arc-ci-guardrails__badge--fail'}`}>
                                            {checkPassed ? 'Pass' : 'Fail'}
                                        </span>
                                    </div>
                                    {(check.message as string | undefined) && (
                                        <div className='arc-ci-guardrails__check-message'>{check.message as string}</div>
                                    )}
                                    {(check.reason as string | undefined) && (
                                        <div className='arc-ci-guardrails__check-reason'>{check.reason as string}</div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </section>
        </div>
    );
};
