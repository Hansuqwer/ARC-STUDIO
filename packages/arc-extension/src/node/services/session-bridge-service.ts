/**
 * SessionBridgeService — Read-Only Local Session Bridge (Phase 43)
 *
 * Provides read-only access to local ARC Studio chat sessions by shelling
 * out to `arc studio sessions --json` and `arc studio sessions show <id> --json`.
 *
 * CONSTRAINTS:
 * - Read-only: no import, write, or mutation methods.
 * - Uses argv-only execFileSync; shell option is never set to true.
 * - Only sanitised env vars are passed via buildArcCliEnv().
 * - IDE write/import bridge is explicitly deferred until advisory locking
 *   is fully verified across all platforms. See
 *   docs/research/cli-session-sharing-protocol.md.
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { execFileSync } from 'child_process';
import { ArcError, ArcErrorCode, ChatSessionSummary, ChatSessionDetail } from '../../common/arc-protocol';
import { buildArcCliEnv } from './arc-cli-utils';

@injectable()
export class SessionBridgeService {
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
}
