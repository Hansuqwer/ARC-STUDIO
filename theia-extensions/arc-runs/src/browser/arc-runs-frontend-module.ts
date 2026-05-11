/** ARC Runs — Frontend Module */
import { ContainerModule } from '@theia/core/shared/inversify';
import { WidgetFactory, bindViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { CommandContribution } from '@theia/core/lib/common';
import { ArcRunTimelineWidget } from './arc-run-timeline-widget';
import { ArcRunsContribution } from './arc-runs-contribution';

export default new ContainerModule(bind => {
  bind(ArcRunTimelineWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcRunTimelineWidget.ID,
    createWidget: () => ctx.container.get(ArcRunTimelineWidget),
  })).inSingletonScope();

  bindViewContribution(bind, ArcRunsContribution);
  bind(FrontendApplicationContribution).toService(ArcRunsContribution);
  bind(CommandContribution).toService(ArcRunsContribution);
});
