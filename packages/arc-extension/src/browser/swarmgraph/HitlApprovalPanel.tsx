import * as React from 'react';

interface HitlApprovalPanelProps {
    runId: string;
    prompt: string;
    onApprove: (reason: string) => void;
    onReject: (reason: string) => void;
}

/** Renders HITL Approve/Reject panel. Accepts props; no live wiring in Phase 1. */
export const HitlApprovalPanel: React.FC<HitlApprovalPanelProps> = ({ runId, prompt, onApprove, onReject }) => {
    const [reason, setReason] = React.useState('');

    return (
        <div className="arc-hitl-panel" role="region" aria-label="HITL Approval"
            style={{ border: '1px solid var(--arc-color-warning, #cca700)', padding: 12, borderRadius: 4 }}>
            <h4 style={{ margin: '0 0 8px', color: 'var(--arc-color-warning, #cca700)' }}>Approval Required</h4>
            <div style={{ marginBottom: 8 }}><strong>Run:</strong> {runId}</div>
            <div style={{ marginBottom: 8 }}>{prompt}</div>
            <textarea
                aria-label="Approval reason"
                value={reason}
                onChange={e => setReason(e.target.value)}
                placeholder="Reason (optional)"
                rows={3}
                style={{ width: '100%', marginBottom: 8, boxSizing: 'border-box' }}
            />
            <div style={{ display: 'flex', gap: 8 }}>
                <button
                    aria-label="Approve run"
                    onClick={() => onApprove(reason)}
                    style={{ color: 'var(--arc-color-success, #73c991)' }}
                >
                    Approve
                </button>
                <button
                    aria-label="Reject run"
                    onClick={() => onReject(reason)}
                    style={{ color: 'var(--arc-color-error, #f14c4c)' }}
                >
                    Reject
                </button>
            </div>
        </div>
    );
};
