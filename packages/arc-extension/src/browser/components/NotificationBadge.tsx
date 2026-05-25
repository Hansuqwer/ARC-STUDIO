/**
 * NotificationBadge component — small count badge for IDE tab icons.
 *
 * Phase 32 / R25 — Slice 32.3.
 * Three states: 0 (hidden), 1-9 (number), 10+ (9+).
 */

import * as React from '@theia/core/shared/react';

export interface NotificationBadgeProps {
    count: number;
    variant?: 'hitl' | 'failure' | 'alert';
}

export function NotificationBadge({ count, variant = 'hitl' }: NotificationBadgeProps): React.ReactNode {
    if (count <= 0) {
        return null;
    }

    const display = count >= 10 ? '9+' : String(count);

    const colorMap: Record<string, string> = {
        hitl: '#e67e22',
        failure: '#e74c3c',
        alert: '#f39c12',
    };

    return (
        <span
            data-testid='notification-badge'
            className='arc-notification-badge'
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                minWidth: '18px',
                height: '18px',
                padding: '0 4px',
                borderRadius: '9px',
                backgroundColor: colorMap[variant] || '#e67e22',
                color: '#fff',
                fontSize: '11px',
                fontWeight: 700,
                lineHeight: 1,
                marginLeft: '4px',
            }}
            title={`${count} pending`}
        >
            {display}
        </span>
    );
}
