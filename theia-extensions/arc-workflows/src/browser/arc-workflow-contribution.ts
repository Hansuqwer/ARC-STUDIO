import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { ArcWorkflowGraphWidget } from './arc-workflow-graph-widget';

export const OpenWorkflowGraphCommand: Command = {
  id: 'arc:open-workflow-graph',
  label: 'ARC: Open Workflow Graph',
  category: 'ARC',
};

@injectable()
export class ArcWorkflowContribution
  extends AbstractViewContribution<ArcWorkflowGraphWidget>
  implements FrontendApplicationContribution {

  constructor() {
    super({
      widgetId: ArcWorkflowGraphWidget.ID,
      widgetName: ArcWorkflowGraphWidget.LABEL,
      defaultWidgetOptions: { area: 'main' },
      toggleCommandId: OpenWorkflowGraphCommand.id,
    });
  }

  override registerCommands(registry: CommandRegistry): void {
    super.registerCommands(registry);
    registry.registerCommand(OpenWorkflowGraphCommand, {
      execute: () => this.openView({ activate: true }),
    });
  }
}
