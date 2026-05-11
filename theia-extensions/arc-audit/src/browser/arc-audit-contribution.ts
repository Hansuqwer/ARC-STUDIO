import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { ArcAuditWidget } from './arc-audit-widget';

export const OpenAuditViewerCommand: Command = { id: 'arc:open-audit-viewer', label: 'ARC: Open Audit Viewer', category: 'ARC' };

@injectable()
export class ArcAuditContribution extends AbstractViewContribution<ArcAuditWidget> {
  constructor() {
    super({ widgetId: ArcAuditWidget.ID, widgetName: ArcAuditWidget.LABEL, defaultWidgetOptions: { area: 'main' }, toggleCommandId: OpenAuditViewerCommand.id });
  }
  override registerCommands(r: CommandRegistry): void {
    super.registerCommands(r);
    r.registerCommand(OpenAuditViewerCommand, { execute: () => this.openView({ activate: true }) });
  }
}
