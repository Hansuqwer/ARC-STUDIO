/**
 * DaemonDiscoveryService — local Python daemon discovery (Phase 77).
 *
 * Owns local daemon URL resolution and loopback health probing so widgets and
 * bridge services do not duplicate discovery logic. Local daemon only; no
 * shared-server, remote sync, or background non-loopback probing.
 */

import { injectable } from '@theia/core/shared/inversify';
import type { PythonDaemonHealth } from '../../common/arc-protocol';

const ARC_PYTHON_DAEMON_URL_ENV = 'ARC_PYTHON_DAEMON_URL';
const DEFAULT_DAEMON_URL = 'http://127.0.0.1:7777';
const DAEMON_CACHE_TTL_MS = 30_000;

@injectable()
export class DaemonDiscoveryService {
    private _daemonCache?: { url?: string; expiresAt: number };

    getConfiguredUrl(): string | undefined {
        return this.localLoopbackBaseUrl(process.env[ARC_PYTHON_DAEMON_URL_ENV]?.trim());
    }

    private localLoopbackBaseUrl(rawUrl: string | undefined): string | undefined {
        if (!rawUrl) {
            return undefined;
        }
        try {
            const parsed = new URL(rawUrl);
            if (parsed.username || parsed.password) {
                return undefined;
            }
            if (!['127.0.0.1', 'localhost', '::1', '[::1]'].includes(parsed.hostname)) {
                return undefined;
            }
            if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
                return undefined;
            }
            parsed.pathname = parsed.pathname.replace(/\/$/, '');
            parsed.search = '';
            parsed.hash = '';
            return parsed.toString().replace(/\/$/, '');
        } catch {
            return undefined;
        }
    }

    async discoverDefaultUrl(): Promise<string | undefined> {
        try {
            const url = new URL('/health', DEFAULT_DAEMON_URL);
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 2_000);
            try {
                const response = await fetch(url, {
                    method: 'GET',
                    signal: controller.signal,
                });
                if (!response.ok) {
                    return undefined;
                }
                const body = await response.json().catch(() => undefined);
                return this.isPythonDaemonHealth(body) ? DEFAULT_DAEMON_URL : undefined;
            } finally {
                clearTimeout(timeout);
                controller.abort();
            }
        } catch {
            return undefined;
        }
    }

    private isPythonDaemonHealth(value: unknown): value is PythonDaemonHealth {
        if (!value || typeof value !== 'object') {
            return false;
        }
        const body = value as Record<string, unknown>;
        return body.status === 'healthy'
            && typeof body.version === 'string'
            && typeof body.uptime_seconds === 'number'
            && body.arc === true
            && !('active_runs' in body);
    }

    async resolveDaemonBaseUrl(): Promise<string | undefined> {
        const now = Date.now();
        if (this._daemonCache && this._daemonCache.expiresAt > now) {
            return this._daemonCache.url;
        }

        const configured = this.getConfiguredUrl();
        if (configured) {
            this._daemonCache = { url: configured.replace(/\/$/, ''), expiresAt: now + DAEMON_CACHE_TTL_MS };
            return this._daemonCache.url;
        }

        const discovered = await this.discoverDefaultUrl();
        this._daemonCache = { url: discovered, expiresAt: now + DAEMON_CACHE_TTL_MS };
        return discovered;
    }
}
