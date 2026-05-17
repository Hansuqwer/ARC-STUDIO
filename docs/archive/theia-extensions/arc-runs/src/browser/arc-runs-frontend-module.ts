/** ARC Runs — Frontend Module */
import { ContainerModule } from '@theia/core/shared/inversify';
import { WidgetFactory, bindViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { ArcRunTimelineWidget } from './arc-run-timeline-widget';
import { ArcChatWidget } from './arc-chat-widget';
import { ArcRunDiffWidget } from './arc-run-diff-widget';
import { ArcChatContribution, ArcRunsContribution, ArcRunDiffContribution } from './arc-runs-contribution';

export default new ContainerModule(bind => {
  bind(ArcRunTimelineWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcRunTimelineWidget.ID,
    createWidget: () => ctx.container.get(ArcRunTimelineWidget),
  })).inSingletonScope();

  bindViewContribution(bind, ArcRunsContribution);
  bind(FrontendApplicationContribution).toService(ArcRunsContribution);

  bind(ArcChatWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcChatWidget.ID,
    createWidget: () => ctx.container.get(ArcChatWidget),
  })).inSingletonScope();

  bindViewContribution(bind, ArcChatContribution);
  bind(FrontendApplicationContribution).toService(ArcChatContribution);

  bind(ArcRunDiffWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcRunDiffWidget.ID,
    createWidget: () => ctx.container.get(ArcRunDiffWidget),
  })).inSingletonScope();

  bindViewContribution(bind, ArcRunDiffContribution);
  bind(FrontendApplicationContribution).toService(ArcRunDiffContribution);
});
