import { injectable, inject } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command, CommandContribution, CommandRegistry } from '@theia/core/lib/common/command';
import { MessageService } from '@theia/core/lib/common/message-service';
import { ArcHealthWidget } from './arc-health-widget';

export const OpenHealthMonitorCommand: Command = {
  id: 'arc:open-health-monitor',
  label: 'ARC: Show Health Monitor',
  category: 'ARC',
};

export const RestartDaemonCommand: Command = {
  id: 'arc:restart-daemon',
  label: 'ARC: Restart Daemon',
  category: 'ARC',
};

@injectable()
export class ArcHealthContribution extends AbstractViewContribution<ArcHealthWidget> implements CommandContribution {
  @inject(MessageService)
  protected readonly messages: MessageService;

  constructor() {
    super({
      widgetId: ArcHealthWidget.ID,
      widgetName: ArcHealthWidget.LABEL,
      defaultWidgetOptions: { area: 'main' },
      toggleCommandId: OpenHealthMonitorCommand.id,
    });
  }

  registerCommands(commands: CommandRegistry): void {
    super.registerCommands(commands);
    commands.registerCommand(RestartDaemonCommand, {
      execute: async () => {
        const answer = await this.messages.warn(
          'Restart local ARC daemon? This only affects the loopback daemon used by this workspace.',
          'Restart',
          'Cancel',
        );
        if (answer === 'Restart') {
          await this.messages.info('Daemon restart is not wired yet. Stop and start `uv run arc serve` manually.');
        }
      },
    });
  }

  async initializeLayout(): Promise<void> {
    const params = new URLSearchParams(window.location.search);
    if (params.get('arc-view') === 'health-monitor') {
      await this.openView({ activate: true });
    }
  }
}
