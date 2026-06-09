/**
 * Phase 277 — R87c: ArcStatusBarContribution SSE subscription tests.
 *
 * All Theia browser / lumino imports are mocked so this runs cleanly
 * in jsdom without a real browser environment.
 */

// Mock Theia imports before any module loads them
jest.mock('@theia/core/lib/browser', () => ({
    FrontendApplicationContribution: class {},
    StatusBar: class {},
    StatusBarAlignment: { LEFT: 'left' },
    WebSocketConnectionProvider: class {},
}));
jest.mock('@theia/core/lib/common/preferences/preference-service', () => ({
    PreferenceService: class {},
}));
jest.mock('@theia/core/shared/inversify', () => ({
    inject: () => () => undefined,
    injectable: () => () => undefined,
    postConstruct: () => () => undefined,
}));
jest.mock('../../common/arc-protocol', () => ({
    ArcServicePath: '/arc-service',
}));

// Now safe to import
import { ArcStatusBarContribution } from '../arc-status-bar-contribution';

// Minimal EventSource stub
class MockEventSource {
    static instances: MockEventSource[] = [];
    url: string;
    listeners: Record<string, Array<() => void>> = {};
    closed = false;
    onerror: (() => void) | undefined;

    constructor(url: string) {
        this.url = url;
        MockEventSource.instances.push(this);
    }
    addEventListener(type: string, handler: () => void): void {
        if (!this.listeners[type]) this.listeners[type] = [];
        this.listeners[type].push(handler);
    }
    dispatchEvent(type: string): void {
        (this.listeners[type] ?? []).forEach(h => h());
    }
    close(): void { this.closed = true; }
}

function makeContrib(): ArcStatusBarContribution {
    const c = new (ArcStatusBarContribution as any)();
    c.statusBar = { setElement: jest.fn(), removeElement: jest.fn().mockResolvedValue(undefined) };
    c.connectionProvider = {
        createProxy: jest.fn().mockReturnValue({ getConfigStatus: jest.fn().mockResolvedValue(undefined) }),
    };
    c.preferences = { get: jest.fn().mockReturnValue(true) };
    return c;
}

describe('ArcStatusBarContribution SSE', () => {
    let origEventSource: unknown;

    beforeEach(() => {
        MockEventSource.instances = [];
        origEventSource = (global as any).EventSource;
        (global as any).EventSource = MockEventSource;
    });

    afterEach(() => {
        (global as any).EventSource = origEventSource;
    });

    it('opens EventSource to the global SSE endpoint', () => {
        const c = makeContrib();
        c['_connectSse']();
        expect(MockEventSource.instances.length).toBe(1);
        expect(MockEventSource.instances[0].url).toBe('http://127.0.0.1:7777/api/global/events/stream');
    });

    it('registers listeners for all 4 terminal event types', () => {
        const c = makeContrib();
        c['_connectSse']();
        const sse = MockEventSource.instances[0];
        for (const t of ['RUN_STARTED', 'RUN_COMPLETED', 'RUN_FAILED', 'RUN_CANCELLED']) {
            expect(sse.listeners[t]?.length).toBeGreaterThan(0);
        }
    });

    it('calls updateStatusBar when RUN_COMPLETED fires', async () => {
        const c = makeContrib();
        const spy = jest.spyOn(c as any, 'updateStatusBar').mockResolvedValue(undefined);
        c['_connectSse']();
        MockEventSource.instances[0].dispatchEvent('RUN_COMPLETED');
        await Promise.resolve();
        expect(spy).toHaveBeenCalled();
    });

    it('closes and clears sseSource on onerror', () => {
        const c = makeContrib();
        c['_connectSse']();
        const sse = MockEventSource.instances[0];
        sse.onerror!();
        expect(sse.closed).toBe(true);
        expect(c['sseSource']).toBeUndefined();
    });

    it('closes SSE source on onStop', async () => {
        const c = makeContrib();
        c['_connectSse']();
        await c.onStop();
        expect(MockEventSource.instances[0].closed).toBe(true);
    });

    it('does not throw when EventSource is unavailable', () => {
        (global as any).EventSource = undefined;
        const c = makeContrib();
        expect(() => c['_connectSse']()).not.toThrow();
    });

    it('fallback poll uses 60s interval, not 10s', () => {
        const c = makeContrib();
        const spy = jest.spyOn(global, 'setInterval').mockReturnValue(42 as any);
        c['updateStatusBar'] = jest.fn().mockResolvedValue(undefined);
        c['_connectSse'] = jest.fn();
        c['init']();
        const intervals = spy.mock.calls.map(call => call[1]);
        expect(intervals).toContain(60000);
        expect(intervals).not.toContain(10000);
        spy.mockRestore();
    });
});
