import * as React from '@theia/core/shared/react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { TraceEvent } from '../../common/arc-protocol';

interface VirtualizedEventListProps {
    events: TraceEvent[];
    estimateSize?: number;
    overscan?: number;
    renderEvent: (event: TraceEvent) => React.ReactNode;
}

const EVENT_COLORS: Record<string, string> = {
    RUN_STARTED: '#4caf50',
    RUN_COMPLETED: '#4caf50',
    RUN_FAILED: '#f44336',
    HITL_PROMPT: '#ff9800',
    HITL_RESPONSE: '#4caf50',
    HITL_TIMEOUT: '#f44336',
    MESSAGE: '#9c27b0',
    RAW: '#757575',
    CUSTOM: '#607d8b',
};

function eventColor(type: string): string {
    return EVENT_COLORS[type] ?? (type.includes('ERROR') || type.includes('FAILED') ? '#f44336' : '#4fc3f7');
}

const EventRow: React.FC<{ event: TraceEvent; style: React.CSSProperties; onClick: () => void }> = React.memo(({ event, style, onClick }) => (
    <div
        style={{
            ...style,
            borderLeft: `4px solid ${eventColor(event.type)}`,
            backgroundColor: 'var(--theia-editor-background)',
            borderRadius: '4px',
            padding: '8px',
            cursor: 'pointer',
            marginBottom: '4px',
        }}
        onClick={onClick}
    >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
            <strong>{event.type}</strong>
            <span style={{ color: 'var(--theia-descriptionForeground)', fontSize: '11px' }}>#{event.sequence}</span>
        </div>
        <div style={{ color: 'var(--theia-descriptionForeground)', fontSize: '11px' }}>{event.timestamp}</div>
    </div>
));

EventRow.displayName = 'EventRow';

export const VirtualizedEventList: React.FC<VirtualizedEventListProps> = ({
    events,
    estimateSize = 64,
    overscan = 5,
    renderEvent,
}) => {
    const parentRef = React.useRef<HTMLDivElement>(null);

    const virtualizer = useVirtualizer({
        count: events.length,
        getScrollElement: () => parentRef.current,
        estimateSize: () => estimateSize,
        overscan,
    });

    if (events.length === 0) {
        return (
            <div
                style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--theia-descriptionForeground)',
                }}
            >
                No events match current filters
            </div>
        );
    }

    return (
        <div ref={parentRef} style={{ flex: 1, overflow: 'auto' }}>
            <div
                style={{
                    height: `${virtualizer.getTotalSize()}px`,
                    width: '100%',
                    position: 'relative',
                }}
            >
                {virtualizer.getVirtualItems().map((virtualItem) => {
                    const event = events[virtualItem.index];
                    return (
                        <div
                            key={virtualItem.key}
                            style={{
                                position: 'absolute',
                                top: 0,
                                left: 0,
                                width: '100%',
                                transform: `translateY(${virtualItem.start}px)`,
                            }}
                        >
                            {renderEvent(event)}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
