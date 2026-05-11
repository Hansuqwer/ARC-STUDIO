/** ARC Context — Frontend Module */
import { ContainerModule } from '@theia/core/shared/inversify';
import { WidgetFactory, bindViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { CommandContribution } from '@theia/core/lib/common';
import { ArcContextPackWidget } from './arc-context-pack-widget';
import { ArcContextContribution } from './arc-context-contribution';

export default new ContainerModule(bind => {
  bind(ArcContextPackWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcContextPackWidget.ID,
    createWidget: () => ctx.container.get(ArcContextPackWidget),
  })).inSingletonScope();
  bindViewContribution(bind, ArcContextContribution);
  bind(FrontendApplicationContribution).toService(ArcContextContribution);
  bind(CommandContribution).toService(ArcContextContribution);
});
