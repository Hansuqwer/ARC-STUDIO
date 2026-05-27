/**
 * Phase 46 — Session Write Bridge TypeScript Tests
 *
 * Tests for SessionBridgeService write methods:
 * - importSession()
 * - deleteSession()
 * - updateSessionField()
 * - TS-side write mutex serialization
 */

import { SessionBridgeService } from '../services/session-bridge-service';
import { ArcError, ArcErrorCode, ChatSessionDetail } from '../../common/arc-protocol';

// Mock execFileSync so no real CLI calls are made
jest.mock('child_process', () => ({
    execFileSync: jest.fn(),
}));

const mockExecFileSync = jest.requireMock('child_process').execFileSync as jest.Mock;
const mockFetch = jest.fn();

/** Minimal ChatSessionDetail for tests */
function makePayload(overrides: Partial<ChatSessionDetail> = {}): ChatSessionDetail {
    return {
        id: 's-test123',
        mode: 'build',
        runtime_mode: 'fake',
        profile_id: 'default',
        isolation_id: 'none',
        created_at: '2026-05-26T00:00:00Z',
        updated_at: '2026-05-26T00:00:00Z',
        history: [{ role: 'user', content: 'hello' }],
        ...overrides,
    };
}

/** Helper: set up execFileSync to return a JSON ok envelope */
function mockCLIOk(data: Record<string, unknown> = {}): void {
    mockExecFileSync.mockReturnValue(
        JSON.stringify({ ok: true, data })
    );
}

/** Helper: set up execFileSync to return a JSON err envelope */
function mockCLIErr(code: string, message: string): void {
    mockExecFileSync.mockReturnValue(
        JSON.stringify({ ok: false, error: { code, message } })
    );
}

function mockDaemonOk(data: Record<string, unknown> = {}): void {
    mockFetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ ok: true, data }) });
}

function mockDaemonErr(status: number, code: string, message: string): void {
    mockFetch.mockResolvedValue({
        ok: false,
        status,
        json: async () => ({ ok: false, error: { code, message } }),
    });
}

describe('SessionBridgeService — write bridge (Phase 46)', () => {
    let svc: SessionBridgeService;

    beforeEach(() => {
        svc = new SessionBridgeService('/workspace/test');
        jest.clearAllMocks();
        mockFetch.mockRejectedValue(new Error('daemon unavailable'));
        (global as unknown as { fetch: jest.Mock }).fetch = mockFetch;
        delete process.env.ARC_PYTHON_DAEMON_URL;
    });

    // ── importSession ──────────────────────────────────────────────────────────

    describe('importSession', () => {
        it('uses daemon when ARC_PYTHON_DAEMON_URL is configured', async () => {
            process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:7777';
            mockDaemonOk({ session_id: 's-test123' });
            const changed = jest.fn();
            svc.onSessionChanged = changed;
            const result = await svc.importSession(makePayload());
            expect(result.ok).toBe(true);
            expect(mockExecFileSync).not.toHaveBeenCalled();
            expect(mockFetch).toHaveBeenCalledWith(
                expect.objectContaining({ pathname: '/api/sessions/write' }),
                expect.objectContaining({ method: 'POST' })
            );
            expect(changed).toHaveBeenCalledWith('s-test123', 'write');
        });

        it('returns ok:true on successful import', async () => {
            mockCLIOk({ session_id: 's-test123', messages: 1 });
            const result = await svc.importSession(makePayload());
            expect(result.ok).toBe(true);
            expect(result.id).toBe('s-test123');
        });

        it('calls arc studio sessions write --json with stdin payload', async () => {
            mockCLIOk({ session_id: 's-test123' });
            await svc.importSession(makePayload());
            expect(mockExecFileSync).toHaveBeenCalledWith(
                'arc',
                ['studio', 'sessions', 'write', '--json'],
                expect.objectContaining({ input: expect.any(String) })
            );
            // Verify shell is not set
            const opts = mockExecFileSync.mock.calls[0][2] as Record<string, unknown>;
            expect(opts['shell']).toBeUndefined();
        });

        it('truncates history to 200 entries before sending', async () => {
            mockCLIOk({ session_id: 's-histcap' });
            const history = Array.from({ length: 250 }, (_, i) => ({
                role: 'user',
                content: `msg ${i}`,
            }));
            await svc.importSession(makePayload({ id: 's-histcap', history }));
            const sentInput = mockExecFileSync.mock.calls[0][2].input as string;
            const sentPayload = JSON.parse(sentInput) as { history: unknown[] };
            expect(sentPayload.history.length).toBeLessThanOrEqual(200);
        });

        it('throws INVALID_INPUT for unsafe session ID', async () => {
            await expect(
                svc.importSession(makePayload({ id: '../../etc/passwd' }))
            ).rejects.toMatchObject({ code: ArcErrorCode.INVALID_INPUT });
            expect(mockExecFileSync).not.toHaveBeenCalled();
        });

        it('throws INVALID_INPUT for empty session ID', async () => {
            await expect(
                svc.importSession(makePayload({ id: '' }))
            ).rejects.toMatchObject({ code: ArcErrorCode.INVALID_INPUT });
        });

        it('returns ok:false when CLI returns malformed output', async () => {
            mockExecFileSync.mockReturnValue('NOT JSON');
            const result = await svc.importSession(makePayload());
            expect(result.ok).toBe(false);
            expect(result.message).toContain('CLI error');
        });

        it('throws LOCK_CONTENTION when CLI returns LOCK_CONTENTION', async () => {
            mockCLIErr('LOCK_CONTENTION', 'advisory lock timeout');
            await expect(svc.importSession(makePayload())).rejects.toMatchObject({
                code: ArcErrorCode.LOCK_CONTENTION,
            });
        });

        it('does not fall back to CLI on daemon LOCK_CONTENTION', async () => {
            process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:7777';
            mockDaemonErr(429, 'LOCK_CONTENTION', 'daemon lock timeout');
            await expect(svc.importSession(makePayload())).rejects.toMatchObject({
                code: ArcErrorCode.LOCK_CONTENTION,
            });
            expect(mockExecFileSync).not.toHaveBeenCalled();
        });

        it('falls back to CLI when daemon returns 503', async () => {
            process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:7777';
            mockFetch.mockResolvedValue({ ok: false, status: 503, json: async () => ({ ok: false }) });
            mockCLIOk({ session_id: 's-test123' });
            const result = await svc.importSession(makePayload());
            expect(result.ok).toBe(true);
            expect(mockExecFileSync).toHaveBeenCalled();
        });

        it('throws PERMISSION_DENIED when CLI returns PERMISSION_DENIED', async () => {
            mockCLIErr('PERMISSION_DENIED', 'untrusted workspace');
            await expect(svc.importSession(makePayload())).rejects.toMatchObject({
                code: ArcErrorCode.PERMISSION_DENIED,
            });
        });

        it('returns ok:false on CLI process error', async () => {
            mockExecFileSync.mockImplementation(() => { throw new Error('arc not found'); });
            const result = await svc.importSession(makePayload());
            expect(result.ok).toBe(false);
            expect(result.message).toContain('arc not found');
        });
    });

    // ── deleteSession ──────────────────────────────────────────────────────────

    describe('deleteSession', () => {
        it('uses daemon for delete when configured', async () => {
            process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:7777';
            mockDaemonOk({ session_id: 's-del', deleted: true });
            const changed = jest.fn();
            svc.onSessionChanged = changed;
            const result = await svc.deleteSession('s-del');
            expect(result.ok).toBe(true);
            expect(mockExecFileSync).not.toHaveBeenCalled();
            expect(mockFetch).toHaveBeenCalledWith(
                expect.objectContaining({ pathname: '/api/sessions/s-del' }),
                expect.objectContaining({ method: 'DELETE' })
            );
            expect(changed).toHaveBeenCalledWith('s-del', 'delete');
        });

        it('returns ok:true on successful delete', async () => {
            mockCLIOk({ session_id: 's-del', deleted: true });
            const result = await svc.deleteSession('s-del');
            expect(result.ok).toBe(true);
        });

        it('calls arc studio sessions delete <id> --json', async () => {
            mockCLIOk({});
            await svc.deleteSession('s-del');
            expect(mockExecFileSync).toHaveBeenCalledWith(
                'arc',
                ['studio', 'sessions', 'delete', 's-del', '--json'],
                expect.objectContaining({ encoding: 'utf-8' })
            );
            const opts = mockExecFileSync.mock.calls[0][2] as Record<string, unknown>;
            expect(opts['shell']).toBeUndefined();
        });

        it('throws INVALID_INPUT for unsafe session ID before CLI call', async () => {
            await expect(svc.deleteSession('../../etc/passwd')).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT,
            });
            expect(mockExecFileSync).not.toHaveBeenCalled();
        });

        it('throws RUN_NOT_FOUND when CLI returns RUN_NOT_FOUND', async () => {
            mockCLIErr('RUN_NOT_FOUND', 'session not found');
            await expect(svc.deleteSession('s-ghost')).rejects.toMatchObject({
                code: ArcErrorCode.RUN_NOT_FOUND,
            });
        });

        it('throws PERMISSION_DENIED when CLI returns PERMISSION_DENIED', async () => {
            mockCLIErr('PERMISSION_DENIED', 'untrusted');
            await expect(svc.deleteSession('s-del')).rejects.toMatchObject({
                code: ArcErrorCode.PERMISSION_DENIED,
            });
        });

        it('throws LOCK_CONTENTION when CLI returns LOCK_CONTENTION', async () => {
            mockCLIErr('LOCK_CONTENTION', 'lock timeout');
            await expect(svc.deleteSession('s-del')).rejects.toMatchObject({
                code: ArcErrorCode.LOCK_CONTENTION,
            });
        });

        it('does not fall back to CLI on daemon RUN_NOT_FOUND', async () => {
            process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:7777';
            mockDaemonErr(404, 'RUN_NOT_FOUND', 'missing');
            await expect(svc.deleteSession('s-ghost')).rejects.toMatchObject({ code: ArcErrorCode.RUN_NOT_FOUND });
            expect(mockExecFileSync).not.toHaveBeenCalled();
        });
    });

    // ── updateSessionField ─────────────────────────────────────────────────────

    describe('updateSessionField', () => {
        it('uses daemon for update when configured', async () => {
            process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:7777';
            mockDaemonOk({ session_id: 's-upd', field: 'mode', updated: true });
            const changed = jest.fn();
            svc.onSessionChanged = changed;
            const result = await svc.updateSessionField('s-upd', 'mode', 'plan');
            expect(result.ok).toBe(true);
            expect(mockExecFileSync).not.toHaveBeenCalled();
            expect(mockFetch).toHaveBeenCalledWith(
                expect.objectContaining({ pathname: '/api/sessions/s-upd' }),
                expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ field: 'mode', value: 'plan' }) })
            );
            expect(changed).toHaveBeenCalledWith('s-upd', 'update');
        });

        it('returns ok:true on successful update', async () => {
            mockCLIOk({ session_id: 's-upd', field: 'mode', updated: true });
            const result = await svc.updateSessionField('s-upd', 'mode', 'plan');
            expect(result.ok).toBe(true);
        });

        it('calls arc studio sessions update with correct argv', async () => {
            mockCLIOk({});
            await svc.updateSessionField('s-upd', 'mode', 'plan');
            expect(mockExecFileSync).toHaveBeenCalledWith(
                'arc',
                ['studio', 'sessions', 'update', 's-upd', '--field', 'mode', '--value', 'plan', '--json'],
                expect.objectContaining({ encoding: 'utf-8' })
            );
            const opts = mockExecFileSync.mock.calls[0][2] as Record<string, unknown>;
            expect(opts['shell']).toBeUndefined();
        });

        it('throws INVALID_INPUT for disallowed field before CLI call', async () => {
            await expect(
                svc.updateSessionField('s-upd', 'history', '[]')
            ).rejects.toMatchObject({ code: ArcErrorCode.INVALID_INPUT });
            expect(mockExecFileSync).not.toHaveBeenCalled();
        });

        it('throws INVALID_INPUT for metadata field', async () => {
            await expect(
                svc.updateSessionField('s-upd', 'metadata', '{}')
            ).rejects.toMatchObject({ code: ArcErrorCode.INVALID_INPUT });
        });

        it('throws INVALID_INPUT for unsafe session ID', async () => {
            await expect(
                svc.updateSessionField('../evil', 'mode', 'plan')
            ).rejects.toMatchObject({ code: ArcErrorCode.INVALID_INPUT });
            expect(mockExecFileSync).not.toHaveBeenCalled();
        });

        it('allows all four safe fields', async () => {
            const fields = ['mode', 'runtime_mode', 'profile_id', 'isolation_id'];
            for (const field of fields) {
                mockCLIOk({});
                const result = await svc.updateSessionField('s-upd', field, 'value');
                expect(result.ok).toBe(true);
            }
        });

        it('throws RUN_NOT_FOUND when CLI returns RUN_NOT_FOUND', async () => {
            mockCLIErr('RUN_NOT_FOUND', 'not found');
            await expect(
                svc.updateSessionField('s-ghost', 'mode', 'plan')
            ).rejects.toMatchObject({ code: ArcErrorCode.RUN_NOT_FOUND });
        });

        it('does not fire onSessionChanged on CLI fallback', async () => {
            mockCLIOk({ session_id: 's-fallback' });
            const changed = jest.fn();
            svc.onSessionChanged = changed;
            const result = await svc.updateSessionField('s-fallback', 'mode', 'plan');
            expect(result.ok).toBe(true);
            expect(changed).not.toHaveBeenCalled();
        });

        it('daemon URL discovery caches result for 30s', async () => {
            mockFetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ arc: true }) });
            mockDaemonOk({ session_id: 's-cache' });
            await svc.updateSessionField('s-cache', 'mode', 'plan');
            await svc.updateSessionField('s-cache', 'mode', 'build');
            const healthCalls = mockFetch.mock.calls.filter(call => String(call[0]).includes('/health'));
            expect(healthCalls.length).toBeLessThanOrEqual(1);
        });
    });

    // ── TS-side write mutex ────────────────────────────────────────────────────

    describe('TS write mutex serialization', () => {
        it('sequential imports both succeed', async () => {
            // Two sequential imports both complete successfully
            mockExecFileSync
                .mockReturnValueOnce(JSON.stringify({ ok: true, data: { session_id: 's-seq1' } }))
                .mockReturnValueOnce(JSON.stringify({ ok: true, data: { session_id: 's-seq2' } }));

            const r1 = await svc.importSession(makePayload({ id: 's-seq1' }));
            const r2 = await svc.importSession(makePayload({ id: 's-seq2' }));
            expect(r1.ok).toBe(true);
            expect(r2.ok).toBe(true);
        });

        it('rejects with LOCK_CONTENTION when pendingWriteCount >= 1', async () => {
            // Build a deferred async task that holds the mutex
            let resolveTask!: () => void;
            const blockingPromise = new Promise<void>(res => { resolveTask = res; });

            mockExecFileSync.mockReturnValue(
                JSON.stringify({ ok: true, data: { session_id: 's-blocked' } })
            );

            // Manually increment pendingWriteCount to simulate "one already queued"
            // We do this by calling _serializedWrite with a task that doesn't resolve yet
            const internalFn = async () => {
                await blockingPromise;
                return { ok: true, id: 's-blocked', message: 'ok' };
            };
            // Access private method via type assertion for testing
            const pendingWrite = (svc as unknown as {
                _serializedWrite: <T>(fn: () => Promise<T>) => Promise<T>;
                _pendingWriteCount: number;
            })._serializedWrite(internalFn);

            // Now pendingWriteCount should be 1 — next call must be rejected
            await expect(
                svc.importSession(makePayload({ id: 's-rejected' }))
            ).rejects.toMatchObject({ code: ArcErrorCode.LOCK_CONTENTION });

            // Release the blocking promise to clean up
            resolveTask();
            await pendingWrite;
        });

        it('ArcErrorCode.LOCK_CONTENTION exists in the enum', () => {
            expect(ArcErrorCode.LOCK_CONTENTION).toBe('LOCK_CONTENTION');
        });
    });
});
