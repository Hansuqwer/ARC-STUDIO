/**
 * Notification service — polls CLI for event counts used by IDE badges.
 *
 * Phase 32 / R25 — Slice 32.3.
 */

import { injectable } from '@theia/core/shared/inversify';
import type { NotificationCounts } from '../../common/notification-protocol';

@injectable()
export class NotificationBackendService implements NotificationCounts {
    hitl: number = 0;
    runFailures: number = 0;
    auditAlerts: number = 0;

    async getCounts(): Promise<NotificationCounts> {
        try {
            const [hitlResult, runsResult] = await Promise.allSettled([
                this.#execCli(['hitl', 'pending', '--json']),
                this.#execCli(['runs', 'list', '--json']),
            ]);

            const hitl = hitlResult.status === 'fulfilled'
                ? this.#countHitlPending(hitlResult.value)
                : 0;

            const runFailures = runsResult.status === 'fulfilled'
                ? this.#countRunFailures(runsResult.value)
                : 0;

            const auditAlerts = 0; // TODO: wire audit alert detection when event bus query is available

            return { hitl, runFailures, auditAlerts };
        } catch {
            return { hitl: 0, runFailures: 0, auditAlerts: 0 };
        }
    }

    async #execCli(args: string[]): Promise<string> {
        const { exec } = require('child_process');
        return new Promise<string>((resolve, reject) => {
            exec(`arc ${args.join(' ')}`, {
                timeout: 5000,
                maxBuffer: 1024 * 64,
            }, (err: Error | null, stdout: string) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(stdout);
                }
            });
        });
    }

    #countHitlPending(output: string): number {
        try {
            const parsed = JSON.parse(output);
            if (Array.isArray(parsed)) {
                return parsed.length;
            }
            if (parsed.data && Array.isArray(parsed.data)) {
                return parsed.data.length;
            }
            return 0;
        } catch {
            return 0;
        }
    }

    #countRunFailures(output: string): number {
        try {
            const parsed = JSON.parse(output);
            const runs = Array.isArray(parsed) ? parsed : (parsed.data || []);
            return runs.filter((r: any) => r?.status === 'failed').length;
        } catch {
            return 0;
        }
    }
}
