/**
 * Evidence Chip Component
 *
 * Renders a small clickable chip for an evidence reference.
 * Shows an icon + truncated label based on evidence kind.
 * Emits structured EvidenceSelectionEvent on open for cross-surface linking.
 */

import * as React from '@theia/core/shared/react';
import type { EvidenceRef, EvidenceKind, EvidenceSelectionEvent } from '../../common/arc-protocol';

export interface EvidenceChipProps {
    evidenceRef: EvidenceRef;
    onOpen: (ref: EvidenceRef) => void;
    onSelect?: (event: EvidenceSelectionEvent) => void;
}

const KIND_ICONS: Record<EvidenceKind, string> = {
    file: '[F]',
    tool_output: '[T]',
    run: '[R]',
    node: '[N]',
    ledger: '[L]',
    receipt: '[RC]',
};

const KIND_LABELS: Record<EvidenceKind, string> = {
    file: 'File',
    tool_output: 'Tool',
    run: 'Run',
    node: 'Node',
    ledger: 'Ledger',
    receipt: 'Receipt',
};

function truncateTarget(target: string, max = 30): string {
    if (target.length <= max) return target;
    const parts = target.split('/');
    if (parts.length > 1) {
        const last = parts[parts.length - 1];
        return last.length <= max ? last : '…' + last.slice(-(max - 1));
    }
    return '…' + target.slice(-(max - 1));
}

export const EvidenceChip: React.FC<EvidenceChipProps> = ({ evidenceRef, onOpen, onSelect }) => {
    const { evidence_id, kind, target, label, redacted } = evidenceRef;

    const icon = KIND_ICONS[kind] || '?';
    const kindLabel = KIND_LABELS[kind] || kind;
    const safeTarget = redacted ? '[redacted]' : target;
    const displayLabel = redacted ? '[redacted]' : label || truncateTarget(target);

    const handleOpen = (source: EvidenceSelectionEvent['source']) => {
        onOpen(evidenceRef);
        if (onSelect) {
            const event: EvidenceSelectionEvent = {
                evidenceRef,
                source,
                timestamp: new Date().toISOString(),
            };
            onSelect(event);
        }
    };

    return (
        <button
            className='arc-evidence-chip'
            onClick={() => handleOpen('chip-click')}
            aria-label={`Evidence ${kindLabel}: ${displayLabel}${redacted ? ' (redacted)' : ''}`}
            title={`${kindLabel}: ${safeTarget}`}
        >
            <span className='arc-evidence-chip__icon' aria-hidden='true'>{icon}</span>
            <span className='arc-evidence-chip__label'>{displayLabel}</span>
            {redacted && (
                <span className='arc-evidence-chip__redacted' aria-label='Redacted'>[redacted]</span>
            )}
        </button>
    );
};
