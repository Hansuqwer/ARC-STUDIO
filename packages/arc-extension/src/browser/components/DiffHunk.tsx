/**
 * DiffHunk — accept/reject component for inline diff review (R89b).
 *
 * Renders a single unified diff hunk with Accept and Reject buttons.
 * Decision is reported via onAccept/onReject callbacks.
 * Accessible: keyboard-navigable buttons, ARIA roles.
 */

import * as React from '@theia/core/shared/react';

export interface DiffHunkProps {
    /** Hunk index (1-based) */
    index: number;
    /** Total number of hunks */
    total: number;
    /** Raw hunk text (unified diff) */
    hunk: string;
    /** Called when user accepts this hunk */
    onAccept: (index: number) => void;
    /** Called when user rejects this hunk */
    onReject: (index: number) => void;
    /** Whether this hunk has been decided */
    decision?: 'accepted' | 'rejected' | undefined;
}

export const DiffHunk: React.FC<DiffHunkProps> = ({
    index,
    total,
    hunk,
    onAccept,
    onReject,
    decision,
}) => {
    const decided = decision !== undefined;
    const lines = hunk.split('\n');

    return (
        <article
            className='arc-diff-hunk'
            aria-label={`Diff hunk ${index} of ${total}`}
            data-decision={decision ?? 'pending'}
        >
            <div className='arc-diff-hunk__header'>
                <span className='arc-diff-hunk__counter' aria-label={`Hunk ${index} of ${total}`}>
                    {index} / {total}
                </span>
                {decided && (
                    <span
                        className={`arc-diff-hunk__badge arc-diff-hunk__badge--${decision}`}
                        role='status'
                        aria-live='polite'
                    >
                        {decision === 'accepted' ? '✓ Accepted' : '✗ Rejected'}
                    </span>
                )}
            </div>

            <pre
                className='arc-diff-hunk__content'
                aria-label='Diff hunk content'
                tabIndex={0}
            >
                {lines.map((line, i) => {
                    const cls = line.startsWith('+')
                        ? 'arc-diff-hunk__line arc-diff-hunk__line--add'
                        : line.startsWith('-')
                        ? 'arc-diff-hunk__line arc-diff-hunk__line--del'
                        : line.startsWith('@@')
                        ? 'arc-diff-hunk__line arc-diff-hunk__line--meta'
                        : 'arc-diff-hunk__line';
                    return (
                        <span key={i} className={cls}>
                            {line}
                            {'\n'}
                        </span>
                    );
                })}
            </pre>

            {!decided && (
                <div className='arc-diff-hunk__actions' role='group' aria-label='Hunk decision'>
                    <button
                        type='button'
                        className='arc-diff-hunk__btn arc-diff-hunk__btn--accept'
                        onClick={() => onAccept(index)}
                        aria-label={`Accept hunk ${index}`}
                    >
                        ✓ Accept
                    </button>
                    <button
                        type='button'
                        className='arc-diff-hunk__btn arc-diff-hunk__btn--reject'
                        onClick={() => onReject(index)}
                        aria-label={`Reject hunk ${index}`}
                    >
                        ✗ Reject
                    </button>
                </div>
            )}
        </article>
    );
};

DiffHunk.displayName = 'DiffHunk';
