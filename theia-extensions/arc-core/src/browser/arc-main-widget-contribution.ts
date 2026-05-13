/**
 * ARC Main Widget Contribution
 *
 * Registers ARC in the Activity Bar (left sidebar),
 * adds keyboard shortcuts, and auto-opens on startup.
 * Source: https://theia-ide.org/docs/widgets/
 */

import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { TabBarToolbarContribution, TabBarToolbarRegistry } from '@theia/core/lib/browser/shell/tab-bar-toolbar';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { KeybindingRegistry } from '@theia/core/lib/browser/keybinding';
import { ArcMainWidget } from './arc-main-widget';

export const ArcOpenCommand: Command = {
  id: 'arc:open',
  label: 'ARC: Open Panel',
  iconClass: 'codicon codicon-circuit-board',
};

export const ArcRefreshCommand: Command = {
  id: 'arc:refresh',
  label: 'ARC: Refresh',
  iconClass: 'codicon codicon-refresh',
};

@injectable()
export class ArcMainWidgetContribution
  extends AbstractViewContribution<ArcMainWidget>
  implements FrontendApplicationContribution, TabBarToolbarContribution {

  constructor() {
    super({
      widgetId: ArcMainWidget.ID,
      widgetName: ArcMainWidget.LABEL,
      defaultWidgetOptions: {
        area: 'left',
        rank: 500,
      },
      toggleCommandId: ArcOpenCommand.id,
    });
  }

  override registerCommands(registry: CommandRegistry): void {
    super.registerCommands(registry);

    registry.registerCommand(ArcRefreshCommand, {
      isEnabled: () => true,
      execute: async () => {
        const widget = await this.openView({ activate: false });
        if (widget) {
          (widget as ArcMainWidget)['loadAll']();
        }
      },
    });
  }

  override registerKeybindings(keybindings: KeybindingRegistry): void {
    super.registerKeybindings(keybindings);

    // Cmd+Shift+R → Run Agent (open chat)
    keybindings.registerKeybinding({
      command: 'arc:run-agent',
      keybinding: 'ctrlcmd+shift+r',
    });

    // Cmd+Shift+M → Compare Models (open arena)
    keybindings.registerKeybinding({
      command: 'arc:compare-models',
      keybinding: 'ctrlcmd+shift+m',
    });
  }

  registerToolbarItems(registry: TabBarToolbarRegistry): void {
    registry.registerItem({
      id: ArcRefreshCommand.id,
      command: ArcRefreshCommand.id,
      tooltip: 'Refresh ARC',
    });
  }

  async initializeLayout(): Promise<void> {
    // Auto-open ARC sidebar on startup
    await this.openView({ activate: false });
  }
}
