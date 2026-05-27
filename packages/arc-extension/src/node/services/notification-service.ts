/**
 * Notification service — polls CLI for event counts used by IDE badges.
 *
 * Phase 32 / R25 — Slice 32.3.
 */

import { injectable } from '@theia/core/shared/inversify';
import { spawn } from 'child_process';
import type { NotificationCounts } from '../../common/notification-protocol';

@injectable()
export class NotificationBackendService implements NotificationCounts {
    hitl: number = 0;
    runFailures: number = 0;
    auditAlerts: number = 0;

    async getCounts(): Promise<NotificationCounts> {
        try {
            const output = await this.#execCli(['events', 'summary', '--json']);
            return this.#parseSummary(output);
        } catch {
            return { hitl: 0, runFailures: 0, auditAlerts: 0, source: 'cli_fallback', degraded: true };
        }
    }

    async #execCli(args: string[]): Promise<string> {
        return new Promise<string>((resolve, reject) => {
            const child = spawn('arc', args, { shell: false });
            const chunks: Buffer[] = [];
            const timer = setTimeout(() => {
                child.kill('SIGTERM');
                reject(new Error('arc events summary timed out'));
            }, 5000);
            child.stdout.on('data', chunk => {
                chunks.push(Buffer.from(chunk));
            });
            child.on('error', err => {
                clearTimeout(timer);
                reject(err);
            });
            child.on('close', code => {
                clearTimeout(timer);
                const output = Buffer.concat(chunks).toString('utf8').slice(0, 64 * 1024);
                code === 0 ? resolve(output) : reject(new Error(`arc exited ${code}`));
            });
        });
    }

    #parseSummary(output: string): NotificationCounts {
        try {
            const parsed = JSON.parse(output);
            const data = parsed.data || parsed;
            return {
                hitl: Number(data.hitl || 0),
                runFailures: Number(data.runFailures || 0),
                auditAlerts: Number(data.auditAlerts || 0),
                taskFailures: Number(data.taskFailures || 0),
                evalFailures: Number(data.evalFailures || 0),
                protocol: data.protocol === 'sse' ? 'sse' : undefined,
                source: data.source === 'local_event_log_recent' ? 'local_event_log_recent' : 'cli_fallback',
                degraded: Boolean(data.degraded),
            };
        } catch {
            return { hitl: 0, runFailures: 0, auditAlerts: 0, source: 'cli_fallback', degraded: true };
        }
    }
}
