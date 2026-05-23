/**
 * PolicyBypassBanner - Non-blocking banner for policy bypass warnings (Phase 22.1).
 * 
 * Displays when ≥1 POLICY_BYPASS_WARNING event is detected in a run.
 * Dismissible per-run (not per-session) - re-appears on fresh runs.
 */
import * as React from 'react';

export interface PolicyBypassBannerProps {
    runId: string;
    warningCount: number;
    onDismiss: () => void;
}

export const PolicyBypassBanner: React.FC<PolicyBypassBannerProps> = ({
    runId,
    warningCount,
    onDismiss,
}) => {
    return (
        <div
            style={{
                backgroundColor: '#fff3cd',
                border: '1px solid #ffc107',
                borderRadius: '4px',
                padding: '12px 16px',
                margin: '8px 0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '14px',
                color: '#856404',
            }}
            role="alert"
            aria-live="polite"
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '20px' }}>⚠️</span>
                <div>
                    <strong>Policy Bypass Warning</strong>
                    <div style={{ fontSize: '13px', marginTop: '4px' }}>
                        {warningCount} enforcement {warningCount === 1 ? 'gap' : 'gaps'} detected in run{' '}
                        <code style={{ 
                            backgroundColor: '#f8f9fa', 
                            padding: '2px 6px', 
                            borderRadius: '3px',
                            fontSize: '12px'
                        }}>
                            {runId.substring(0, 12)}...
                        </code>
                        . Some operations bypassed security gates. Check audit logs for details.
                    </div>
                </div>
            </div>
            <button
                onClick={onDismiss}
                style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: '#856404',
                    cursor: 'pointer',
                    fontSize: '20px',
                    padding: '4px 8px',
                    lineHeight: '1',
                }}
                aria-label="Dismiss warning"
                title="Dismiss (will re-appear on next run)"
            >
                ×
            </button>
        </div>
    );
};
