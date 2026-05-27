/**
 * Phase 52 — SessionBridgeService SSE subscription tests.
 *
 * Tests:
 * 1. startSessionChangedSSE() uses SSE when daemon is available (mock EventSource).
 * 2. Falls back to CLI polling if SSE not available (daemon unavailable).
 * 3. onSessionChanged is called when session_changed event arrives via SSE.
 * 4. stopSessionChangedSSE() closes the event source.
 * 5. isSSEConnected reflects connection state.
 *
 * No WebSocket. No shared-server. No remote-sync. SSE is local daemon only.
 */

import { SessionBridgeService, IEventSourceFactory, IEventSource } from '../services/session-bridge-service';

// Mock child_process so no real CLI calls are made
jest.mock('child_process', () => ({
    execFileSync: jest.fn(),
}));

// --- Mock EventSource implementation ---

class MockEventSource implements IEventSource {
    onmessage: ((event: { data: string; lastEventId?: string }) => void) | null = null;
    onerror: ((event: unknown) => void) | null = null;

    private _listeners: Map<string, ((e: { data: string; lastEventId?: string }) => void)[]> = new Map();
    public closed = false;

    addEventListener(type: string, listener: (event: { data: string; lastEventId?: string }) => void): void {
        const existing = this._listeners.get(type) ?? [];
        this._listeners.set(type, [...existing, listener]);
    }

    close(): void {
        this.closed = true;
    }

    /** Test helper: simulate an event of a given type. */
    simulateEvent(type: string, data: Record<string, unknown>): void {
        const ev = { data: JSON.stringify(data), lastEventId: '' };
        const listeners = this._listeners.get(type) ?? [];
        listeners.forEach(l => l(ev));
        if (type === 'message') {
            this.onmessage?.(ev);
        }
    }

    /** Test helper: simulate an SSE error. */
    simulateError(err: unknown = new Error('SSE error')): void {
        this.onerror?.(err);
    }
}

class MockEventSourceFactory implements IEventSourceFactory {
    public lastCreatedSource?: MockEventSource;
    public createCallCount = 0;
    public shouldFail = false;

    create(_url: string): IEventSource {
        this.createCallCount++;
        if (this.shouldFail) {
            throw new Error('EventSource creation failed');
        }
        const source = new MockEventSource();
        this.lastCreatedSource = source;
        return source;
    }
}

// --- Helper ---

const mockFetch = jest.fn();
(global as unknown as Record<string, unknown>).fetch = mockFetch;

function makeSvc(daemonAvailable = true): { svc: SessionBridgeService; factory: MockEventSourceFactory } {
    const svc = new SessionBridgeService('/tmp/workspace');
    const factory = new MockEventSourceFactory();
    svc.eventSourceFactory = factory;

    if (daemonAvailable) {
        // Stub daemon availability
        mockFetch.mockResolvedValue({ ok: true, body: null });
        jest.spyOn(svc as unknown as { _daemonBaseUrl: () => Promise<string | undefined> }, '_daemonBaseUrl' as never)
            .mockResolvedValue('http://127.0.0.1:7777' as never);
    } else {
        jest.spyOn(svc as unknown as { _daemonBaseUrl: () => Promise<string | undefined> }, '_daemonBaseUrl' as never)
            .mockResolvedValue(undefined as never);
    }

    return { svc, factory };
}

// --- Tests ---

describe('SessionBridgeService — Phase 52 SSE', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('startSessionChangedSSE returns true when daemon is available', async () => {
        const { svc } = makeSvc(true);
        const result = await svc.startSessionChangedSSE();
        expect(result).toBe(true);
        expect(svc.isSSEConnected).toBe(true);
    });

    it('startSessionChangedSSE returns false when daemon is unavailable (CLI fallback)', async () => {
        const { svc } = makeSvc(false);
        const result = await svc.startSessionChangedSSE();
        expect(result).toBe(false);
        expect(svc.isSSEConnected).toBe(false);
    });

    it('onSessionChanged is called when session_changed SSE event arrives', async () => {
        const { svc, factory } = makeSvc(true);
        const received: Array<{ sessionId: string; operation: string }> = [];
        svc.onSessionChanged = (sessionId, operation) => {
            received.push({ sessionId, operation });
        };

        await svc.startSessionChangedSSE();
        const source = factory.lastCreatedSource!;
        expect(source).toBeDefined();

        // Simulate a session_changed event
        source.simulateEvent('session_changed', {
            session_id: 's-abc123',
            operation: 'write',
            workspace: '/tmp/workspace',
        });

        expect(received).toHaveLength(1);
        expect(received[0].sessionId).toBe('s-abc123');
        expect(received[0].operation).toBe('write');
    });

    it('onSessionChanged is NOT called for unknown event types', async () => {
        const { svc, factory } = makeSvc(true);
        const received: Array<unknown> = [];
        svc.onSessionChanged = () => received.push(true);

        await svc.startSessionChangedSSE();
        const source = factory.lastCreatedSource!;

        // run_completed is not session_changed
        source.simulateEvent('run_completed', { run_id: 'r1', workflow_id: 'wf1' });
        expect(received).toHaveLength(0);
    });

    it('stopSessionChangedSSE closes the event source', async () => {
        const { svc, factory } = makeSvc(true);
        await svc.startSessionChangedSSE();
        const source = factory.lastCreatedSource!;

        expect(svc.isSSEConnected).toBe(true);
        svc.stopSessionChangedSSE();

        expect(source.closed).toBe(true);
        expect(svc.isSSEConnected).toBe(false);
    });

    it('SSE error handler marks disconnected', async () => {
        const { svc, factory } = makeSvc(true);
        await svc.startSessionChangedSSE();
        const source = factory.lastCreatedSource!;

        expect(svc.isSSEConnected).toBe(true);
        source.simulateError();

        // After error, SSE is marked disconnected
        expect(svc.isSSEConnected).toBe(false);
    });

    it('startSessionChangedSSE is idempotent (does not double-connect)', async () => {
        const { svc, factory } = makeSvc(true);
        await svc.startSessionChangedSSE();
        await svc.startSessionChangedSSE();
        // Only one EventSource should be created
        expect(factory.createCallCount).toBe(1);
    });

    it('SSE uses no WebSocket — constraint documented', () => {
        // This is a documentation/constraint test.
        // The SSE implementation uses fetch-based streaming, not WebSocket.
        // No WebSocket. No shared-server. No remote-sync. Local daemon only.
        const { svc } = makeSvc(false);
        // The service should not have any WebSocket-related methods
        const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(svc));
        const wsMethod = methods.find(m => m.toLowerCase().includes('websocket'));
        expect(wsMethod).toBeUndefined();
    });
});
