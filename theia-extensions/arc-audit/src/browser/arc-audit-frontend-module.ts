/**
 * ARC Audit — Frontend Module
 * Registers the audit chain viewer widget.
 */
import { ContainerModule } from '@theia/core/shared/inversify';
import { WidgetFactory, bindViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { CommandContribution } from '@theia/core/lib/common';
import { ArcAuditWidget } from './arc-audit-widget';
import { ArcAuditContribution } from './arc-audit-contribution';

export default new ContainerModule(bind => {
  bind(ArcAuditWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcAuditWidget.ID,
    createWidget: () => ctx.container.get(ArcAuditWidget),
  })).inSingletonScope();
  bindViewContribution(bind, ArcAuditContribution);
  bind(FrontendApplicationContribution).toService(ArcAuditContribution);
  bind(CommandContribution).toService(ArcAuditContribution);
});
