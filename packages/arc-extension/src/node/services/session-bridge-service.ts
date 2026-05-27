/**
 * SessionBridgeService — Read/Write Local Session Bridge (Phase 43 + Phase 46)
 *
 * Provides read-only access to local ARC Studio chat sessions by shelling
 * out to `arc studio sessions --json` and `arc studio sessions show <id> --json`.
 *
 * Phase 46 adds write methods: importSession(), deleteSession(), updateSessionField().
 *
 * CONSTRAINTS:
 * - Uses argv-only execFileSync / execFileSyncWithStdin; shell option is NEVER set to true.
 * - Only sanitised env vars are passed via buildArcCliEnv().
 * - Write methods are serialized via a per-instance Promise-chain mutex.
 *   This is a second-layer defense to reduce contention against the authoritative
 *   Python-side advisory lock (fcntl.flock in storage/advisory_lock.py).
 * - Daemon write protocol is deliberately deferred.
 *   TODO(Phase 47): upgrade to daemon IPC/WebSocket write protocol once
 *   the daemon wire format and session-change events are designed and tested.
 *   See docs/research/cli-session-sharing-protocol.md.
 *
 * Allowed fields for updateSessionField(): mode, runtime_mode, profile_id, isolation_id.
 * History mutation from the IDE is intentionally blocked.
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { execFileSync } from 'child_process';
import { ArcError, ArcErrorCode, ChatSessionSummary, ChatSessionDetail } from '../../common/arc-protocol';
import { buildArcCliEnv } from './arc-cli-utils';

/** Safe session ID pattern — must match Python SESSION_ID_RE and TypeScript getChatSession() */
const SESSION_ID_RE = /^[A-Za-z0-9_-]{1,80}$/;

/** Fields the IDE is allowed to update via `arc studio sessions update`. */
const ALLOWED_UPDATE_FIELDS = new Set(['mode', 'runtime_mode', 'profile_id', 'isolation_id']);

/** Maximum history entries forwarded to the Python write bridge. */
const MAX_HISTORY_ENTRIES = 200;
const ARC_PYTHON_DAEMON_URL_ENV = 'ARC_PYTHON_DAEMON_URL';
const DEFAULT_DAEMON_URL = 'http://127.0.0.1:7777';
const DAEMON_CACHE_TTL_MS = 30_000;
const DAEMON_WRITE_TIMEOUT_MS = 10_000;

type SessionOperation = 'write' | 'delete' | 'update';

class DaemonUnavailableError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'DaemonUnavailableError';
    }
}

function canonicalDaemonErrorCode(code: string): ArcErrorCode {
    if (code === 'LOCK_CONTENTION') return ArcErrorCode.LOCK_CONTENTION;
    if (code === 'PERMISSION_DENIED') return ArcErrorCode.PERMISSION_DENIED;
    if (code === 'RUN_NOT_FOUND') return ArcErrorCode.RUN_NOT_FOUND;
    if (code === 'INVALID_INPUT') return ArcErrorCode.INVALID_INPUT;
    if (code === 'TIMEOUT') return ArcErrorCode.TIMEOUT;
    return ArcErrorCode.UNKNOWN;
}

@injectable()
export class SessionBridgeService {
    /**
     * Serializes write operations to avoid concurrent advisory lock contention.
     * One write at a time; additional writes queue behind the current one.
     * This is second-layer defense only; Python-side fcntl.flock is authoritative.
     */
    private _writeMutex: Promise<void> = Promise.resolve();
    private _daemonCache?: { url?: string; expiresAt: number };
    onSessionChanged?: (sessionId: string, operation: SessionOperation) => void;

    constructor(
        @inject('WorkspaceRoot') private readonly workspaceRoot: string
    ) {}

    /**
     * List saved local chat sessions.
     * Calls `arc studio sessions --json`; returns the ok.data array.
     * Returns an empty array if no sessions exist or the CLI is unavailable.
     */
    async listChatSessions(): Promise<ChatSessionSummary[]> {
        try {
            const output = execFileSync('arc', ['studio', 'sessions', '--json'], {
                timeout: 10_000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok || !Array.isArray(parsed.data)) {
                return [];
            }
            return (parsed.data as Array<Record<string, unknown>>).map(s => ({
                id: String(s['id'] ?? ''),
                mode: String(s['mode'] ?? ''),
                runtime_mode: String(s['runtime_mode'] ?? ''),
                updated_at: String(s['updated_at'] ?? ''),
                message_count: Array.isArray(s['history']) ? (s['history'] as unknown[]).length : 0,
            }));
        } catch {
            return [];
        }
    }

    /**
     * Get a single chat session by ID (redacted).
     * Calls `arc studio sessions show <id> --json`.
     * Throws ArcError(RUN_NOT_FOUND) if the session does not exist.
     */
    async getChatSession(sessionId: string): Promise<ChatSessionDetail> {
        // Input validation: only allow safe session ID characters
        if (!/^[A-Za-z0-9_-]{1,80}$/.test(sessionId)) {
            throw new ArcError(ArcErrorCode.INVALID_INPUT, `Invalid session ID: ${sessionId}`);
        }
        let output: string;
        try {
            output = execFileSync('arc', ['studio', 'sessions', 'show', sessionId, '--json'], {
                timeout: 10_000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err);
            throw new ArcError(ArcErrorCode.RUN_NOT_FOUND, `Session not found: ${sessionId} (${msg})`);
        }
        const parsed = JSON.parse(output);
        if (!parsed.ok || !parsed.data) {
            throw new ArcError(ArcErrorCode.RUN_NOT_FOUND, `Session not found: ${sessionId}`);
        }
        const d = parsed.data as Record<string, unknown>;
        return {
            id: String(d['id'] ?? ''),
            mode: String(d['mode'] ?? ''),
            runtime_mode: String(d['runtime_mode'] ?? ''),
            profile_id: String(d['profile_id'] ?? ''),
            isolation_id: String(d['isolation_id'] ?? ''),
            created_at: String(d['created_at'] ?? ''),
            updated_at: String(d['updated_at'] ?? ''),
            history: Array.isArray(d['history']) ? d['history'] as Array<Record<string, string>> : [],
        };
    }

    // ── Write bridge (Phase 46) ────────────────────────────────────────────────

    /**
     * Import (create or overwrite) a session from the IDE.
     *
     * Serialized via _writeMutex to prevent concurrent advisory lock contention.
     * The Python-side advisory lock (fcntl.flock) remains the authoritative guard.
     */
    async importSession(payload: ChatSessionDetail): Promise<{ ok: boolean; id: string; message: string }> {
        // Input validation
        if (!SESSION_ID_RE.test(payload.id)) {
            throw new ArcError(ArcErrorCode.INVALID_INPUT, `Invalid session ID: ${payload.id}`);
        }
        // Cap history
        const capped: ChatSessionDetail = {
            ...payload,
            history: Array.isArray(payload.history)
                ? payload.history.slice(-MAX_HISTORY_ENTRIES)
                : [],
        };

        return this._serializedWrite(async () => {
            try {
                const parsed = await this._writeToDaemon('POST', '/api/sessions/write', capped);
                const id = String((parsed.data as Record<string, unknown> | undefined)?.session_id ?? payload.id);
                this.onSessionChanged?.(id, 'write');
                return { ok: true, id, message: 'imported' };
            } catch (err: unknown) {
                if (!this._isDaemonUnavailable(err)) {
                    throw err;
                }
                return this._importSessionViaCli(capped);
            }
        });
    }

    /**
     * Delete a session by ID from the IDE.
     */
    async deleteSession(sessionId: string): Promise<{ ok: boolean; message: string }> {
        if (!SESSION_ID_RE.test(sessionId)) {
            throw new ArcError(ArcErrorCode.INVALID_INPUT, `Invalid session ID: ${sessionId}`);
        }
        return this._serializedWrite(async () => {
            try {
                await this._writeToDaemon('DELETE', `/api/sessions/${encodeURIComponent(sessionId)}`);
                this.onSessionChanged?.(sessionId, 'delete');
                return { ok: true, message: 'deleted' };
            } catch (err: unknown) {
                if (!this._isDaemonUnavailable(err)) {
                    throw err;
                }
                return this._deleteSessionViaCli(sessionId);
            }
        });
    }

    /**
     * Update a single safe field on a session.
     * Allowed fields: mode, runtime_mode, profile_id, isolation_id.
     */
    async updateSessionField(sessionId: string, field: string, value: string): Promise<{ ok: boolean; message: string }> {
        if (!SESSION_ID_RE.test(sessionId)) {
            throw new ArcError(ArcErrorCode.INVALID_INPUT, `Invalid session ID: ${sessionId}`);
        }
        if (!ALLOWED_UPDATE_FIELDS.has(field)) {
            throw new ArcError(
                ArcErrorCode.INVALID_INPUT,
                `Field '${field}' is not updatable via IDE bridge; allowed: ${[...ALLOWED_UPDATE_FIELDS].sort().join(', ')}`
            );
        }
        return this._serializedWrite(async () => {
            try {
                await this._writeToDaemon('PATCH', `/api/sessions/${encodeURIComponent(sessionId)}`, { field, value });
                this.onSessionChanged?.(sessionId, 'update');
                return { ok: true, message: 'updated' };
            } catch (err: unknown) {
                if (!this._isDaemonUnavailable(err)) {
                    throw err;
                }
                return this._updateSessionFieldViaCli(sessionId, field, value);
            }
        });
    }

    private async _daemonBaseUrl(): Promise<string | undefined> {
        const now = Date.now();
        if (this._daemonCache && this._daemonCache.expiresAt > now) {
            return this._daemonCache.url;
        }
        const configured = process.env[ARC_PYTHON_DAEMON_URL_ENV]?.trim();
        if (configured) {
            this._daemonCache = { url: configured.replace(/\/$/, ''), expiresAt: now + DAEMON_CACHE_TTL_MS };
            return this._daemonCache.url;
        }
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 2_000);
            const response = await fetch(new URL('/health', DEFAULT_DAEMON_URL), { signal: controller.signal });
            clearTimeout(timeout);
            if (response.ok) {
                this._daemonCache = { url: DEFAULT_DAEMON_URL, expiresAt: now + DAEMON_CACHE_TTL_MS };
                return DEFAULT_DAEMON_URL;
            }
        } catch {
            // loopback probe unavailable; use CLI fallback
        }
        this._daemonCache = { url: undefined, expiresAt: now + DAEMON_CACHE_TTL_MS };
        return undefined;
    }

    private async _writeToDaemon(method: string, path: string, body?: unknown): Promise<Record<string, unknown>> {
        const baseUrl = await this._daemonBaseUrl();
        if (!baseUrl) {
            throw new DaemonUnavailableError('daemon unavailable');
        }
        const url = new URL(path, baseUrl);
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), DAEMON_WRITE_TIMEOUT_MS);
        let response: Response;
        try {
            response = await fetch(url, {
                method,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'X-ARC-Workspace': this.workspaceRoot,
                },
                body: body === undefined ? undefined : JSON.stringify(body),
            });
        } catch (err: unknown) {
            throw new DaemonUnavailableError(err instanceof Error ? err.message : String(err));
        } finally {
            clearTimeout(timeout);
        }
        let parsed: Record<string, unknown>;
        try {
            parsed = await response.json() as Record<string, unknown>;
        } catch {
            if (response.status === 503 || response.status === 504) {
                throw new DaemonUnavailableError(`daemon HTTP ${response.status}`);
            }
            throw new ArcError(ArcErrorCode.INTERNAL_ERROR, `Daemon returned HTTP ${response.status}`);
        }
        if (response.status === 503 || response.status === 504) {
            throw new DaemonUnavailableError(`daemon HTTP ${response.status}`);
        }
        if (!response.ok || parsed.ok === false) {
            const error = parsed.error as Record<string, unknown> | undefined;
            const code = String(error?.code ?? 'UNKNOWN');
            const message = String(error?.message ?? `Daemon returned HTTP ${response.status}`);
            throw new ArcError(canonicalDaemonErrorCode(code), message);
        }
        return parsed;
    }

    private _isDaemonUnavailable(err: unknown): boolean {
        return err instanceof DaemonUnavailableError;
    }

    private _importSessionViaCli(payload: ChatSessionDetail): { ok: boolean; id: string; message: string } {
        try {
            const output = execFileSync('arc', ['studio', 'sessions', 'write', '--json'], {
                input: JSON.stringify(payload),
                timeout: 15_000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok) {
                return { ok: true, id: String(parsed.data?.session_id ?? payload.id), message: 'imported' };
            }
            return this._cliImportFailure(parsed, payload.id);
        } catch (err: unknown) {
            if (err instanceof ArcError) throw err;
            const msg = err instanceof Error ? err.message : String(err);
            return { ok: false, id: payload.id, message: `CLI error: ${msg}` };
        }
    }

    private _deleteSessionViaCli(sessionId: string): { ok: boolean; message: string } {
        try {
            const output = execFileSync('arc', ['studio', 'sessions', 'delete', sessionId, '--json'], {
                timeout: 10_000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            return this._cliMutationResult(output, 'deleted');
        } catch (err: unknown) {
            if (err instanceof ArcError) throw err;
            const msg = err instanceof Error ? err.message : String(err);
            return { ok: false, message: `CLI error: ${msg}` };
        }
    }

    private _updateSessionFieldViaCli(sessionId: string, field: string, value: string): { ok: boolean; message: string } {
        try {
            const output = execFileSync('arc', ['studio', 'sessions', 'update', sessionId, '--field', field, '--value', value, '--json'], {
                timeout: 10_000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            return this._cliMutationResult(output, 'updated');
        } catch (err: unknown) {
            if (err instanceof ArcError) throw err;
            const msg = err instanceof Error ? err.message : String(err);
            return { ok: false, message: `CLI error: ${msg}` };
        }
    }

    private _cliMutationResult(output: string, successMessage: string): { ok: boolean; message: string } {
        try {
            const parsed = JSON.parse(output);
            if (parsed.ok) {
                return { ok: true, message: successMessage };
            }
            const code = String(parsed.error?.code ?? 'UNKNOWN');
            if (['LOCK_CONTENTION', 'PERMISSION_DENIED', 'RUN_NOT_FOUND'].includes(code)) {
                throw new ArcError(canonicalDaemonErrorCode(code), parsed.error?.message ?? code);
            }
            return { ok: false, message: parsed.error?.message ?? `${successMessage} failed` };
        } catch (e: unknown) {
            if (e instanceof ArcError) throw e;
            return { ok: false, message: `parse error: ${e}` };
        }
    }

    private _cliImportFailure(parsed: Record<string, any>, fallbackId: string): { ok: boolean; id: string; message: string } {
        const code = String(parsed.error?.code ?? 'UNKNOWN');
        if (['LOCK_CONTENTION', 'PERMISSION_DENIED'].includes(code)) {
            throw new ArcError(canonicalDaemonErrorCode(code), parsed.error?.message ?? code);
        }
        return { ok: false, id: fallbackId, message: parsed.error?.message ?? 'import failed' };
    }

    /**
     * Internal: queue an async write operation through the mutex.
     * Rejects with LOCK_CONTENTION if the queue already has 1 pending operation
     * (i.e. a current + 1 queued = 2 pending is the practical limit for the
     * single-writer IDE assumption; more than 1 queued indicates a UX error).
     *
     * NOTE: This is a second-layer defense only. The Python advisory lock
     * (storage/advisory_lock.py) is the authoritative data-safety guard.
     */
    private _pendingWriteCount = 0;
    private _serializedWrite<T>(fn: () => Promise<T>): Promise<T> {
        if (this._pendingWriteCount >= 1) {
            return Promise.reject(
                new ArcError(ArcErrorCode.LOCK_CONTENTION, 'A session write is already queued; retry after it completes')
            );
        }
        this._pendingWriteCount++;
        const next = this._writeMutex.then(fn).finally(() => {
            this._pendingWriteCount--;
        });
        this._writeMutex = next.then(() => undefined, () => undefined);
        return next;
    }
}
