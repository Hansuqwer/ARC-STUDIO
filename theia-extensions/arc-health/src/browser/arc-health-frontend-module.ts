import { ContainerModule } from '@theia/core/shared/inversify';
import { FrontendApplicationContribution, WidgetFactory, bindViewContribution } from '@theia/core/lib/browser';
import { ArcHealthContribution } from './arc-health-contribution';
import { ArcHealthWidget } from './arc-health-widget';

export default new ContainerModule(bind => {
  bind(ArcHealthWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcHealthWidget.ID,
    createWidget: () => ctx.container.get(ArcHealthWidget),
  })).inSingletonScope();

  bindViewContribution(bind, ArcHealthContribution);
  bind(FrontendApplicationContribution).toService(ArcHealthContribution);
});
