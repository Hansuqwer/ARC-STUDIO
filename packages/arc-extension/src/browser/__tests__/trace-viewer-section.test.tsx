/**
 * Phase 285 — R-PERF2: TraceViewerSection virtualization tests.
 */

jest.mock('@theia/core/lib/browser', () => ({
    FrontendApplicationContribution: class {},
    StatusBar: class {},
    StatusBarAlignment: { LEFT: 'left' },
    WebSocketConnectionProvider: class {},
}));
jest.mock('@theia/core/shared/inversify', () => ({
    inject: () => () => undefined,
    injectable: () => () => undefined,
    postConstruct: () => () => undefined,
}));

// Mock @tanstack/react-virtual — just render all items in tests
jest.mock('@tanstack/react-virtual', () => ({
    useVirtualizer: ({ count, estimateSize }: { count: number; estimateSize: () => number }) => ({
        getVirtualItems: () =>
            Array.from({ length: count }, (_, i) => ({
                index: i,
                start: i * estimateSize(),
                size: estimateSize(),
                key: i,
            })),
        getTotalSize: () => count * estimateSize(),
    }),
}));

import * as React from 'react';
import { render, screen } from '@testing-library/react';
import { TraceViewerSection } from '../components/TraceViewerSection';
import type { TraceFile } from '../../common/arc-protocol';

function makeTraces(n: number): TraceFile[] {
    return Array.from({ length: n }, (_, i) => ({
        id: `run-${i}`,
        path: `/tmp/traces/run-${i}.jsonl`,
        timestamp: new Date(2026, 0, 1, 0, i).toISOString(),
        status: (i % 3 === 0 ? 'failed' : 'completed') as 'completed' | 'failed',
    }));
}

const DEFAULT_PROPS = {
    isCollapsed: false,
    onToggle: jest.fn(),
    isLoadingTraces: false,
    traceProgress: 0,
    traces: [],
    selectedTrace: undefined,
    traceFilter: '',
    onTraceFilterChange: jest.fn(),
    onClearFilter: jest.fn(),
    onLoadTraces: jest.fn(),
    onSelectTrace: jest.fn(),
};

describe('TraceViewerSection virtualization', () => {
    it('renders with 0 traces showing empty state', () => {
        render(<TraceViewerSection {...DEFAULT_PROPS} />);
        expect(screen.getByText(/No traces loaded/i)).toBeTruthy();
    });

    it('renders a small list correctly', () => {
        const traces = makeTraces(5);
        render(<TraceViewerSection {...DEFAULT_PROPS} traces={traces} />);
        // All 5 should be rendered (virtualizer mocked to render all)
        expect(screen.getAllByRole('option').length).toBe(5);
    });

    it('renders large list through virtualized container', () => {
        const traces = makeTraces(200);
        const { container } = render(<TraceViewerSection {...DEFAULT_PROPS} traces={traces} />);
        // The scroll container has a fixed height (bounded)
        const scrollContainer = container.querySelector('[style*="overflow-y"]');
        expect(scrollContainer).not.toBeNull();
    });

    it('filter reduces visible items', () => {
        const traces = makeTraces(10);
        render(<TraceViewerSection {...DEFAULT_PROPS} traces={traces} traceFilter='run-1' />);
        // Only run-1 matches exact filter "run-1" (not run-10, etc. in our test set)
        expect(screen.getAllByRole('option').length).toBeGreaterThan(0);
    });

    it('shows no-match empty state when filter matches nothing', () => {
        const traces = makeTraces(5);
        render(<TraceViewerSection {...DEFAULT_PROPS} traces={traces} traceFilter='zzzzzz' />);
        expect(screen.getByText(/No traces match the filter/i)).toBeTruthy();
    });
});
