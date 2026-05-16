/**
 * Failure Autopsy Card Component
 *
 * Displays structured diagnosis for a failed run: probable cause,
 * confidence, known facts vs guesses, retry options, and evidence refs.
 */

import * as React from '@theia/core/shared/react';
import type { FailureAutopsy, RetryOption, EvidenceSelectionEvent } from '../../common/arc-protocol';
import { EvidenceChip } from './EvidenceChip';
import type { EvidenceChipProps } from './EvidenceChip';

export interface FailureAutopsyCardProps {
    autopsy: FailureAutopsy;
    onRetry?: (option: RetryOption) => void;
    onOpenDoctor?: () => void;
    onOpenEvidence?: EvidenceChipProps['onOpen'];
    onSelectEvidence?: (event: EvidenceSelectionEvent) => void;
}

const CONFIDENCE_LABELS: Record<string, string> = {
    high: 'High confidence',
    medium: 'Medium confidence',
    low: 'Low confidence',
    unknown: 'Unknown confidence',
};

const RISK_TONE: Record<string, string> = {
    low: 'arc-retry-risk--low',
    medium: 'arc-retry-risk--medium',
    high: 'arc-retry-risk--high',
};

const RISK_LABEL: Record<string, string> = {
    low: '[L]',
    medium: '[M]',
    high: '[H]',
};

function truncateId(id: string, max = 12): string {
    return id.length > max ? id.slice(0, max) + '…' : id;
}

export const FailureAutopsyCard: React.FC<FailureAutopsyCardProps> = ({
    autopsy,
    onRetry,
    onOpenDoctor,
    onOpenEvidence,
    onSelectEvidence,
}) => {
    const {
        run_id,
        probable_cause,
        confidence,
        error_category,
        failed_node,
        last_safe_state,
        retry_options,
        knows,
        guesses,
        evidence_refs,
    } = autopsy;

    return (
        <div className='arc-autopsy-card' role='region' aria-live='polite' aria-label={`Failure autopsy for ${truncateId(run_id)}`}>
            <span className='arc-sr-only' role='status'>Run failed: {probable_cause}</span>
            <div className='arc-autopsy-card__header'>
                <h3 className='arc-autopsy-title'>
                    Run failed
                    {failed_node && <span className='arc-autopsy-node'> at <code>{failed_node}</code></span>}
                </h3>
                <span className={`arc-autopsy-confidence arc-autopsy-confidence--${confidence}`} aria-label={CONFIDENCE_LABELS[confidence]}>
                    {CONFIDENCE_LABELS[confidence]}
                </span>
            </div>

            <div className='arc-autopsy-card__body'>
                {error_category && (
                    <p className='arc-autopsy-safe-state'>
                        <strong>Error category:</strong> <code>{error_category}</code>
                    </p>
                )}

                <p className='arc-autopsy-cause'>
                    <strong>Probable cause:</strong> {probable_cause}
                </p>

                {last_safe_state && (
                    <p className='arc-autopsy-safe-state'>
                        <strong>Last safe state:</strong> {last_safe_state}
                    </p>
                )}

                {knows.length > 0 && (
                    <div className='arc-autopsy-section'>
                        <strong className='arc-autopsy-section-title'>Known</strong>
                        <ul className='arc-autopsy-list arc-autopsy-list--knows' aria-label='Known facts'>
                            {knows.map((item, i) => (
                                <li key={i} className='arc-autopsy-item'>
                                    <span className='arc-autopsy-icon' aria-hidden='true'>✓</span>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {guesses.length > 0 && (
                    <div className='arc-autopsy-section'>
                        <strong className='arc-autopsy-section-title'>Guesses</strong>
                        <ul className='arc-autopsy-list arc-autopsy-list--guesses' aria-label='Hypotheses'>
                            {guesses.map((item, i) => (
                                <li key={i} className='arc-autopsy-item'>
                                    <span className='arc-autopsy-icon' aria-hidden='true'>?</span>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {evidence_refs.length > 0 && onOpenEvidence && (
                    <div className='arc-autopsy-evidence' aria-label='Evidence references'>
                        {evidence_refs.map(ref => (
                            <EvidenceChip key={ref.evidence_id} evidenceRef={ref} onOpen={onOpenEvidence} onSelect={onSelectEvidence} />
                        ))}
                    </div>
                )}
            </div>

            {(retry_options.length > 0 || onOpenDoctor) && (
                <div className='arc-autopsy-card__actions'>
                    {retry_options.map((option, i) => (
                        <button
                            key={i}
                            className={`theia-button secondary ${RISK_TONE[option.risk] || ''}`}
                            onClick={() => onRetry?.(option)}
                            disabled={!onRetry}
                            aria-label={`Retry: ${option.label} (${option.risk} risk)`}
                            title={option.command || option.label}
                        >
                            {RISK_LABEL[option.risk] || '[?]'} {option.label}
                        </button>
                    ))}
                    {onOpenDoctor && (
                        <button
                            className='theia-button secondary'
                            onClick={onOpenDoctor}
                            aria-label='Run arc doctor'
                        >
                            Run arc doctor
                        </button>
                    )}
                </div>
            )}
        </div>
    );
};
