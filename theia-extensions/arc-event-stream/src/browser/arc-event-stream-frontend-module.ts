import { ContainerModule } from '@theia/core/shared/inversify';
import { FrontendApplicationContribution, WidgetFactory, bindViewContribution } from '@theia/core/lib/browser';
import { ArcEventStreamContribution } from './arc-event-stream-contribution';
import { ArcEventStreamWidget } from './arc-event-stream-widget';

export default new ContainerModule(bind => {
  bind(ArcEventStreamWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcEventStreamWidget.ID,
    createWidget: () => ctx.container.get(ArcEventStreamWidget),
  })).inSingletonScope();

  bindViewContribution(bind, ArcEventStreamContribution);
  bind(FrontendApplicationContribution).toService(ArcEventStreamContribution);
});
