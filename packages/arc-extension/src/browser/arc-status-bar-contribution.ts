import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { FrontendApplicationContribution, StatusBar, StatusBarAlignment, WebSocketConnectionProvider } from '@theia/core/lib/browser';
import { PreferenceService } from '@theia/core/lib/common/preferences/preference-service';
import { ArcServicePath } from '../common/arc-protocol';
import type { ArcService } from '../common/arc-protocol';

const BACKEND_STATUS_ID = 'arc-backend-status';
const PROFILE_STATUS_ID = 'arc-profile-status';

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

    @postConstruct()
    protected init(): void {
        this.updateStatusBar();
        this.pollTimer = setInterval(() => this.updateStatusBar(), 10000);
    }

    async onStop(): Promise<void> {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
        }
    }

    protected async updateStatusBar(): Promise<void> {
        if (!this.preferences.get<boolean>('arc.ui.showStatusBar', true)) {
            await Promise.all([
                this.statusBar.removeElement(BACKEND_STATUS_ID),
                this.statusBar.removeElement(PROFILE_STATUS_ID),
            ]);
            return;
        }

        await Promise.all([
            this.updateBackendStatus(),
            this.updateProfileStatus(),
        ]);
    }

    protected async updateBackendStatus(): Promise<void> {
        try {
            if (!this.arcService) {
                this.arcService = this.connectionProvider.createProxy<ArcService>(ArcServicePath);
            }
            const config = await this.arcService.getConfigStatus();
            this.statusBar.setElement(BACKEND_STATUS_ID, {
                text: config.backendAvailable ? '$(circle-large-filled) ARC' : '$(circle-large-outline) ARC',
                tooltip: config.backendAvailable ? 'ARC backend reachable' : config.backendMessage || 'ARC backend unavailable',
                alignment: StatusBarAlignment.LEFT,
                priority: 10,
                command: 'arc-studio:open',
            });
        } catch {
            this.statusBar.setElement(BACKEND_STATUS_ID, {
                text: '$(circle-large-outline) ARC',
                tooltip: 'ARC backend unavailable',
                alignment: StatusBarAlignment.LEFT,
                priority: 10,
                command: 'arc-studio:open',
            });
        }
    }

    protected async updateProfileStatus(): Promise<void> {
        const profileId = this.preferences.get<string>('arc.run.defaultProfile', 'stub');
        this.statusBar.setElement(PROFILE_STATUS_ID, {
            text: `$(shield) Profile: ${profileId}`,
            tooltip: 'Default ARC run profile',
            alignment: StatusBarAlignment.LEFT,
            priority: 9,
            command: 'arc-studio:open',
        });
    }
}
