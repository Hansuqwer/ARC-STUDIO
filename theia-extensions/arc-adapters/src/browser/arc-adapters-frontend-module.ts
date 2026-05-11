/** ARC Adapters — Frontend Module */
import { ContainerModule } from '@theia/core/shared/inversify';
import { WidgetFactory, bindViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { ArcAdaptersWidget } from './arc-adapters-widget';
import { ArcAdaptersContribution } from './arc-adapters-contribution';

export default new ContainerModule(bind => {
  bind(ArcAdaptersWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcAdaptersWidget.ID,
    createWidget: () => ctx.container.get(ArcAdaptersWidget),
  })).inSingletonScope();
  bindViewContribution(bind, ArcAdaptersContribution);
  bind(FrontendApplicationContribution).toService(ArcAdaptersContribution);
});
