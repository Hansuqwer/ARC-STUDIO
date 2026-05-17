/**
 * ARC Welcome Contribution
 *
 * Registers the welcome widget and opens it on first launch.
 * Controlled by the `arc.ui.showOnboarding` preference.
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { AbstractViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { PreferenceService } from '@theia/core/lib/common/preferences/preference-service';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { ArcWelcomeWidget } from './arc-welcome-widget';

export const OpenWelcomeCommand: Command = {
  id: 'arc:open-welcome',
  label: 'ARC: Open Welcome',
  iconClass: 'codicon codicon-star',
};

@injectable()
export class ArcWelcomeContribution
  extends AbstractViewContribution<ArcWelcomeWidget>
  implements FrontendApplicationContribution {

  @inject(PreferenceService)
  protected readonly preferences: PreferenceService;

  constructor() {
    super({
      widgetId: ArcWelcomeWidget.ID,
      widgetName: ArcWelcomeWidget.LABEL,
      defaultWidgetOptions: {
        area: 'main',
        rank: 100,
      },
      toggleCommandId: OpenWelcomeCommand.id,
    });
  }

  override registerCommands(registry: CommandRegistry): void {
    super.registerCommands(registry);
    registry.registerCommand(OpenWelcomeCommand, {
      execute: () => this.openView({ activate: true }),
    });
  }

  async initializeLayout(): Promise<void> {
    // Show welcome widget on first launch (controlled by preference)
    const showOnboarding = this.preferences.get<boolean>('arc.ui.showOnboarding', true);
    if (showOnboarding) {
      await this.openView({ activate: true });
      // Disable onboarding after first view
      await this.preferences.set('arc.ui.showOnboarding', false);
    }
  }
}
