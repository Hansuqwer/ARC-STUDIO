/**
 * ARC Status Bar Contribution
 *
 * Shows daemon status, profile indicator, and run status in the status bar.
 * Source: https://theia-ide.org/docs/extensions/#status-bar
 */

import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { StatusBar, StatusBarAlignment, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { PreferenceService } from '@theia/core/lib/common/preferences/preference-service';
import { CommandService } from '@theia/core/lib/common/command';
import { ArcFrontendService } from './arc-frontend-service';

const DAEMON_STATUS_ID = 'arc-daemon-status';
const PROFILE_STATUS_ID = 'arc-profile-status';
const RUN_STATUS_ID = 'arc-run-status';

@injectable()
export class ArcStatusBarContribution implements FrontendApplicationContribution {

  @inject(StatusBar)
  protected readonly statusBar: StatusBar;

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  @inject(PreferenceService)
  protected readonly preferences: PreferenceService;

  @inject(CommandService)
  protected readonly commandService: CommandService;

  protected pollTimer: ReturnType<typeof setInterval> | undefined;

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
    await Promise.all([
      this.updateDaemonStatus(),
      this.updateProfileStatus(),
      this.updateRunStatus(),
    ]);
  }

  protected async updateDaemonStatus(): Promise<void> {
    try {
      const result = await this.arcService.getDaemonStatus();
      const running = result.data?.running ?? false;
      this.statusBar.setElement(DAEMON_STATUS_ID, {
        text: running ? '$(circle-large-filled) ARC' : '$(circle-large-outline) ARC',
        tooltip: running
          ? `ARC daemon running (v${result.data?.version ?? '?'})`
          : 'ARC daemon not running. Start with `uv run arc serve`',
        alignment: StatusBarAlignment.LEFT,
        priority: 10,
        command: 'arc:open',
      });
    } catch {
      this.statusBar.setElement(DAEMON_STATUS_ID, {
        text: '$(circle-large-outline) ARC',
        tooltip: 'ARC daemon unavailable',
        alignment: StatusBarAlignment.LEFT,
        priority: 10,
        command: 'arc:open',
      });
    }
  }

  protected async updateProfileStatus(): Promise<void> {
    const profileId = this.preferences.get<string>('arc.run.defaultProfile', 'stub');
    this.statusBar.setElement(PROFILE_STATUS_ID, {
      text: `$(shield) Profile: ${profileId}`,
      tooltip: 'Click to change security profile',
      alignment: StatusBarAlignment.LEFT,
      priority: 9,
      command: 'arc:open-chat',
    });
  }

  protected async updateRunStatus(): Promise<void> {
    try {
      const result = await this.arcService.listRuns();
      const activeRuns = (result.data ?? []).filter(run => run.status === 'running' || run.status === 'pending');
      if (activeRuns.length > 0) {
        const latest = activeRuns[0];
        this.statusBar.setElement(RUN_STATUS_ID, {
          text: `$(play) Running (${latest.id.substring(0, 12)})`,
          tooltip: 'Click to open run timeline',
          alignment: StatusBarAlignment.LEFT,
          priority: 8,
          command: 'arc:open-run-timeline',
        });
      } else {
        this.statusBar.setElement(RUN_STATUS_ID, {
          text: '$(check) Ready',
          tooltip: 'No active runs',
          alignment: StatusBarAlignment.LEFT,
          priority: 8,
        });
      }
    } catch {
      this.statusBar.setElement(RUN_STATUS_ID, {
        text: '',
        alignment: StatusBarAlignment.LEFT,
        priority: 8,
      });
    }
  }
}
