/**
 * Run Contract Card Component
 *
 * Displays a pre-run contract with objective, runtime, mode, tools,
 * write scope, cost ceiling, and rollback plan. Renders status badge
 * and action buttons for accept/edit/cancel.
 */

import * as React from '@theia/core/shared/react';
import type { RunContract, ContractStatus } from '../../common/arc-protocol';

export interface RunContractCardProps {
    contract: RunContract;
    onAccept?: () => void;
    onEdit?: () => void;
    onCancel?: () => void;
}

const STATUS_LABELS: Record<ContractStatus, string> = {
    proposed: '[?] Proposed',
    accepted: '[OK] Accepted',
    fulfilled: '[OK] Fulfilled',
    violated: '[!] Violated',
};

const STATUS_TONE: Record<ContractStatus, string> = {
    proposed: 'arc-contract-status--proposed',
    accepted: 'arc-contract-status--accepted',
    fulfilled: 'arc-contract-status--fulfilled',
    violated: 'arc-contract-status--violated',
};

function truncateId(id: string, max = 12): string {
    return id.length > max ? id.slice(0, max) + '…' : id;
}

function formatCost(cost?: number | 'unknown'): string {
    if (cost === undefined || cost === 'unknown' || !Number.isFinite(cost)) return 'unknown';
    return cost === 0 ? '$0.00' : `$${cost.toFixed(2)}`;
}

export const RunContractCard: React.FC<RunContractCardProps> = ({
    contract,
    onAccept,
    onEdit,
    onCancel,
}) => {
    const {
        contract_id,
        objective,
        runtime,
        mode,
        allowed_tools,
        write_scope,
        cost_ceiling_usd,
        rollback_plan,
        status,
    } = contract;

    return (
        <div className='arc-contract-card' role='region' aria-label={`Run contract ${truncateId(contract_id)}`}>
            <div className='arc-contract-card__header'>
                <span className={`arc-contract-status ${STATUS_TONE[status]}`} aria-label={`Status: ${STATUS_LABELS[status]}`}>
                    {STATUS_LABELS[status]}
                </span>
                <span className='arc-contract-id' title={contract_id}>
                    {truncateId(contract_id)}
                </span>
            </div>

            <div className='arc-contract-card__body'>
                <p className='arc-contract-objective'>
                    <strong>Objective:</strong> {objective}
                </p>

                <dl className='arc-contract-meta'>
                    <dt>Runtime</dt>
                    <dd>{runtime}</dd>

                    <dt>Mode</dt>
                    <dd>{mode}</dd>

                    <dt>Cost ceiling</dt>
                    <dd>{formatCost(cost_ceiling_usd)}</dd>

                    <dt>Rollback</dt>
                    <dd>{rollback_plan}</dd>
                </dl>

                {allowed_tools.length > 0 && (
                    <div className='arc-contract-section'>
                        <strong>Allowed tools ({allowed_tools.length})</strong>
                        <ul className='arc-contract-list' aria-label='Allowed tools'>
                            {allowed_tools.map(tool => (
                                <li key={tool}><code>{tool}</code></li>
                            ))}
                        </ul>
                    </div>
                )}

                {write_scope.length > 0 && (
                    <div className='arc-contract-section'>
                        <strong>Write scope</strong>
                        <ul className='arc-contract-list' aria-label='Write scope'>
                            {write_scope.map(scope => (
                                <li key={scope}><code>{scope}</code></li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>

            {status === 'proposed' && (onAccept || onEdit || onCancel) && (
                <div className='arc-contract-card__actions'>
                    {onAccept && (
                        <button
                            className='theia-button primary'
                            onClick={onAccept}
                            aria-label='Accept contract'
                        >
                            Accept
                        </button>
                    )}
                    {onEdit && (
                        <button
                            className='theia-button secondary'
                            onClick={onEdit}
                            aria-label='Edit contract'
                        >
                            Edit
                        </button>
                    )}
                    {onCancel && (
                        <button
                            className='theia-button secondary'
                            onClick={onCancel}
                            aria-label='Cancel contract'
                        >
                            Cancel
                        </button>
                    )}
                </div>
            )}
        </div>
    );
};
