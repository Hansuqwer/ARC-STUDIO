/**
 * Run Receipt Card Component
 *
 * Displays a completed/failed run receipt with summary, cost,
 * files changed, evidence refs, and signature status.
 */

import * as React from '@theia/core/shared/react';
import type { RunReceipt, FileChange, EvidenceSelectionEvent } from '../../common/arc-protocol';
import { EvidenceChip } from './EvidenceChip';
import type { EvidenceChipProps } from './EvidenceChip';
import { BudgetGauge } from './BudgetGauge';
import { BudgetVector } from '../../common/arc-protocol';

export interface RunReceiptCardProps {
    receipt: RunReceipt;
    onExport?: () => void;
    onVerify?: () => void;
    onOpenEvidence?: EvidenceChipProps['onOpen'];
    onSelectEvidence?: (event: EvidenceSelectionEvent) => void;
}

const STATUS_TONE: Record<string, string> = {
    completed: 'arc-receipt-status--completed',
    failed: 'arc-receipt-status--failed',
    cancelled: 'arc-receipt-status--cancelled',
};

const STATUS_LABELS: Record<string, string> = {
    completed: '[OK] Completed',
    failed: '[!] Failed',
    cancelled: '[-] Cancelled',
};

function truncateId(id: string, max = 12): string {
    return id.length > max ? id.slice(0, max) + '…' : id;
}

function formatCost(cost?: number | 'unknown'): string {
    if (cost === undefined || cost === 'unknown' || !Number.isFinite(cost)) return 'unknown';
    return cost === 0 ? '$0.00' : `$${cost.toFixed(2)}`;
}

function formatDuration(ms?: number): string {
    if (ms === undefined || !Number.isFinite(ms) || ms < 0) return 'unknown';
    if (ms < 1000) return `${ms}ms`;
    const s = ms / 1000;
    if (s < 60) return `${s.toFixed(1)}s`;
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}m ${sec}s`;
}

export const RunReceiptCard: React.FC<RunReceiptCardProps> = ({
    receipt,
    onExport,
    onVerify,
    onOpenEvidence,
    onSelectEvidence,
}) => {
    const {
        receipt_id,
        run_id,
        status,
        summary,
        cost_usd,
        duration_ms,
        files_changed,
        evidence_refs,
        signature,
        rollback_command,
        unresolved_risks,
        trust_boundaries_crossed,
    } = receipt;

    return (
        <div className='arc-receipt-card' role='region' aria-label={`Run receipt ${truncateId(receipt_id)}`}>
            <div className='arc-receipt-card__header'>
                <span className={`arc-receipt-status ${STATUS_TONE[status]}`} aria-label={`Status: ${STATUS_LABELS[status]}`}>
                    {STATUS_LABELS[status]}
                </span>
                <span className='arc-receipt-id' title={receipt_id}>
                    {truncateId(receipt_id)}
                </span>
            </div>

            <div className='arc-receipt-card__body'>
                <p className='arc-receipt-summary'>
                    <strong>Run ID:</strong> <code title={run_id}>{truncateId(run_id)}</code>
                    <button
                        className='arc-inline-copy'
                        type='button'
                        onClick={() => navigator.clipboard?.writeText(run_id)}
                        aria-label='Copy run ID'
                    >
                        Copy
                    </button>
                </p>

                <p className='arc-receipt-summary'>
                    <strong>Summary:</strong> {summary}
                </p>

                <div className='arc-receipt-section'>
                    <strong>Budget Usage</strong>
                    <BudgetGauge
                        usage={{ tokens: null, cost_usd: cost_usd === 'unknown' ? undefined : cost_usd, latency_ms: duration_ms }}
                        limit={(receipt as any).budget_limit}
                    />
                </div>

                <dl className='arc-receipt-meta'>
                    <dt>Cost</dt>
                    <dd>{formatCost(cost_usd)}</dd>

                    <dt>Duration</dt>
                    <dd>{formatDuration(duration_ms)}</dd>

                    <dt>Signature</dt>
                    <dd className={signature ? 'arc-receipt-signed' : 'arc-receipt-unsigned'}>
                        {signature ? `${signature.slice(0, 8)}…` : 'unsigned'}
                    </dd>
                </dl>

                {rollback_command && (
                    <div className='arc-receipt-section'>
                        <strong>Rollback command</strong>
                        <code className='arc-receipt-command'>{rollback_command}</code>
                    </div>
                )}

                {files_changed.length > 0 && (
                    <div className='arc-receipt-section'>
                        <strong>Files changed ({files_changed.length})</strong>
                        <ul className='arc-receipt-list' aria-label='Files changed'>
                            {files_changed.map((fc: FileChange) => (
                                <li key={fc.path} className='arc-receipt-file'>
                                    <code>{fc.path}</code>
                                    <span className='arc-receipt-file__diff'>
                                        <span className='arc-receipt-file__added'>+{fc.added}</span>
                                        <span className='arc-receipt-file__removed'>-{fc.removed}</span>
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {evidence_refs.length > 0 && onOpenEvidence && (
                    <div className='arc-receipt-evidence' aria-label='Evidence references'>
                        {evidence_refs.map(ref => (
                            <EvidenceChip key={ref.evidence_id} evidenceRef={ref} onOpen={onOpenEvidence} onSelect={onSelectEvidence} />
                        ))}
                    </div>
                )}

                {unresolved_risks.length > 0 && (
                    <div className='arc-receipt-risks' role='alert' aria-label='Unresolved risks'>
                        <strong>[!] Unresolved risks ({unresolved_risks.length})</strong>
                        <ul className='arc-receipt-list'>
                            {unresolved_risks.map((risk, i) => (
                                <li key={i}>{risk}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {trust_boundaries_crossed.length > 0 && (
                    <div className='arc-receipt-trust' aria-label='Trust boundaries crossed'>
                        <strong>Trust boundaries crossed ({trust_boundaries_crossed.length})</strong>
                        <ul className='arc-receipt-list'>
                            {trust_boundaries_crossed.map((boundary, i) => (
                                <li key={i}>{boundary}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>

            {(onExport || onVerify) && (
                <div className='arc-receipt-card__actions'>
                    {onExport && (
                        <button
                            className='theia-button secondary'
                            onClick={onExport}
                            aria-label='Export receipt'
                        >
                            Export receipt
                        </button>
                    )}
                    {onVerify && (
                        <button
                            className='theia-button secondary'
                            onClick={onVerify}
                            aria-label='Verify receipt signature'
                        >
                            Verify
                        </button>
                    )}
                </div>
            )}
        </div>
    );
};
