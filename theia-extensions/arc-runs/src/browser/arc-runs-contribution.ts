import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { ArcRunTimelineWidget } from './arc-run-timeline-widget';

export const OpenRunTimelineCommand: Command = {
  id: 'arc:open-run-timeline',
  label: 'ARC: Open Run Timeline',
  category: 'ARC',
};

@injectable()
export class ArcRunsContribution extends AbstractViewContribution<ArcRunTimelineWidget> {
  constructor() {
    super({
      widgetId: ArcRunTimelineWidget.ID,
      widgetName: ArcRunTimelineWidget.LABEL,
      defaultWidgetOptions: { area: 'main' },
      toggleCommandId: OpenRunTimelineCommand.id,
    });
  }

  override registerCommands(registry: CommandRegistry): void {
    super.registerCommands(registry);
    registry.registerCommand(OpenRunTimelineCommand, {
      execute: () => this.openView({ activate: true }),
    });
  }
}
