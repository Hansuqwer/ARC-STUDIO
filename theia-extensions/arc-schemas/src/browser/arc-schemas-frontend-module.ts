/** ARC Schemas — Frontend Module */
import { ContainerModule } from '@theia/core/shared/inversify';
import { WidgetFactory, bindViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { CommandContribution } from '@theia/core/lib/common';
import { ArcSchemaInspectorWidget } from './arc-schema-inspector-widget';
import { ArcSchemasContribution } from './arc-schemas-contribution';

export default new ContainerModule(bind => {
  bind(ArcSchemaInspectorWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcSchemaInspectorWidget.ID,
    createWidget: () => ctx.container.get(ArcSchemaInspectorWidget),
  })).inSingletonScope();

  bindViewContribution(bind, ArcSchemasContribution);
  bind(FrontendApplicationContribution).toService(ArcSchemasContribution);
  bind(CommandContribution).toService(ArcSchemasContribution);
});
