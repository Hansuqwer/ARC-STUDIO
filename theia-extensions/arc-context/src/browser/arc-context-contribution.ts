import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { ArcContextPackWidget } from './arc-context-pack-widget';

export const OpenContextPackCommand: Command = { id: 'arc:open-context-pack', label: 'ARC: Open Context Pack Viewer', category: 'ARC' };

@injectable()
export class ArcContextContribution extends AbstractViewContribution<ArcContextPackWidget> {
  constructor() {
    super({ widgetId: ArcContextPackWidget.ID, widgetName: ArcContextPackWidget.LABEL, defaultWidgetOptions: { area: 'main' }, toggleCommandId: OpenContextPackCommand.id });
  }
  override registerCommands(r: CommandRegistry): void {
    super.registerCommands(r);
    r.registerCommand(OpenContextPackCommand, { execute: () => this.openView({ activate: true }) });
  }
}
