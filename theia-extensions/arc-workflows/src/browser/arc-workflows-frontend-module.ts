/**
 * ARC Workflows — Frontend Module
 * Registers the workflow graph widget.
 */
import { ContainerModule } from '@theia/core/shared/inversify';
import { WidgetFactory, bindViewContribution } from '@theia/core/lib/browser';
import { CommandContribution } from '@theia/core/lib/common';
import { ArcWorkflowGraphWidget } from './arc-workflow-graph-widget';
import { ArcWorkflowContribution } from './arc-workflow-contribution';

export default new ContainerModule(bind => {
  bind(ArcWorkflowGraphWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcWorkflowGraphWidget.ID,
    createWidget: () => ctx.container.get(ArcWorkflowGraphWidget),
  })).inSingletonScope();

  bindViewContribution(bind, ArcWorkflowContribution);
  bind(CommandContribution).toService(ArcWorkflowContribution);
});
