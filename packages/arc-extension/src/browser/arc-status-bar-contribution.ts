import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { FrontendApplicationContribution, StatusBar, StatusBarAlignment, WebSocketConnectionProvider } from '@theia/core/lib/browser';
import { PreferenceService } from '@theia/core/lib/common/preferences/preference-service';
import { ArcServicePath } from '../common/arc-protocol';
import type { ArcService } from '../common/arc-protocol';

const BACKEND_STATUS_ID = 'arc-backend-status';
const MODE_STATUS_ID = 'arc-mode-status';
const TRUST_STATUS_ID = 'arc-trust-status';
const RUNTIME_STATUS_ID = 'arc-runtime-status';
const PROFILE_STATUS_ID = 'arc-profile-status';
const ALL_STATUS_IDS = [
    BACKEND_STATUS_ID,
    MODE_STATUS_ID,
    TRUST_STATUS_ID,
    RUNTIME_STATUS_ID,
    PROFILE_STATUS_ID,
];

@injectable()
export class ArcStatusBarContribution implements FrontendApplicationContribution {
    @inject(StatusBar)
    protected readonly statusBar!: StatusBar;

    @inject(WebSocketConnectionProvider)
    protected readonly connectionProvider!: WebSocketConnectionProvider;

    @inject(PreferenceService)
    protected readonly preferences!: PreferenceService;

    protected pollTimer: ReturnType<typeof setInterval> | undefined;
    protected arcService: ArcService | undefined;
    protected sseSource: EventSource | undefined;

    @postConstruct()
    protected init(): void {
        this.updateStatusBar();
        this._connectSse();
        // Fallback poll (60s) catches daemon restarts when SSE is unavailable.
        this.pollTimer = setInterval(() => this.updateStatusBar(), 60000);
    }

    /** Connect to the GlobalEventBroker SSE feed; refresh status on terminal events. */
    protected _connectSse(): void {
        if (typeof EventSource === 'undefined') {
            return; // SSE not available in this environment
        }
        const sse = new EventSource('http://127.0.0.1:7777/api/global/events/stream');
        this.sseSource = sse;
        const refresh = (): void => { void this.updateStatusBar(); };
        for (const t of ['RUN_STARTED', 'RUN_COMPLETED', 'RUN_FAILED', 'RUN_CANCELLED']) {
            sse.addEventListener(t, refresh);
        }
        sse.onerror = (): void => {
            // On error, close and let the fallback poll handle it.
            sse.close();
            this.sseSource = undefined;
        };
    }

    async onStop(): Promise<void> {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
        }
        if (this.sseSource) {
            this.sseSource.close();
            this.sseSource = undefined;
        }
    }

    protected async updateStatusBar(): Promise<void> {
        if (!this.preferences.get<boolean>('arc.ui.showStatusBar', true)) {
            await Promise.all(ALL_STATUS_IDS.map(id => this.statusBar.removeElement(id)));
            return;
        }
        await this.updateFromConfig();
    }

    /** Single source for the status rail: mode · trust · runtime · daemon · profile. Degrades to
     * 'unknown'/offline when the daemon is unreachable rather than disappearing (producer-truth). */
    protected async updateFromConfig(): Promise<void> {
        if (!this.arcService) {
            this.arcService = this.connectionProvider.createProxy<ArcService>(ArcServicePath);
        }
        let config: Awaited<ReturnType<ArcService['getConfigStatus']>> | undefined;
        try {
            config = await this.arcService.getConfigStatus();
        } catch {
            config = undefined;
        }

        const online = config?.backendAvailable ?? false;
        this.setEntry(BACKEND_STATUS_ID, {
            text: online ? '$(circle-large-filled) ARC' : '$(circle-large-outline) ARC',
            tooltip: online ? 'ARC daemon reachable' : (config?.backendMessage || 'ARC daemon unavailable'),
            label: online ? 'ARC daemon online' : 'ARC daemon offline',
            priority: 10,
        });

        const mode = config?.mode ?? 'unknown';
        this.setEntry(MODE_STATUS_ID, {
            text: `$(symbol-event) ${mode}`,
            tooltip: config ? `Run mode: ${mode}` : 'Run mode unavailable (daemon offline)',
            label: `Run mode ${mode}`,
            priority: 9,
        });

        const trust = config?.workspace?.trustLevel ?? 'unknown';
        const trustIcon = trust === 'trusted' ? '$(shield)' : trust === 'untrusted' ? '$(warning)' : '$(question)';
        this.setEntry(TRUST_STATUS_ID, {
            text: `${trustIcon} ${trust}`,
            tooltip: config?.workspace?.reason
                ? `Workspace trust: ${trust} — ${config.workspace.reason}`
                : `Workspace trust: ${trust}`,
            label: `Workspace trust ${trust}`,
            priority: 8,
        });

        const runtime = config?.runtime?.defaultRuntime ?? 'unknown';
        this.setEntry(RUNTIME_STATUS_ID, {
            text: `$(server-process) ${runtime}`,
            tooltip: config
                ? `Default runtime: ${runtime} (isolation: ${config.runtime.isolation})`
                : 'Runtime unavailable (daemon offline)',
            label: `Default runtime ${runtime}`,
            priority: 7,
        });

        const profile = config?.selectedProfile
            ?? this.preferences.get<string>('arc.run.defaultProfile', 'stub');
        this.setEntry(PROFILE_STATUS_ID, {
            text: `$(person) ${profile}`,
            tooltip: `Default ARC run profile: ${profile}`,
            label: `Default run profile ${profile}`,
            priority: 6,
        });
    }

    private setEntry(
        id: string,
        e: { text: string; tooltip: string; label: string; priority: number },
    ): void {
        this.statusBar.setElement(id, {
            text: e.text,
            tooltip: e.tooltip,
            alignment: StatusBarAlignment.LEFT,
            priority: e.priority,
            command: 'arc-studio:open',
            accessibilityInformation: { label: e.label, role: 'status' },
        });
    }
}
