/**
 * ARC Studio Frontend Module
 * 
 * This module provides the frontend contributions for ARC Studio,
 * including the SwarmGraph visualization widget and UI components.
 */

import { ContainerModule } from '@theia/core/shared/inversify';
import { ArcWidget } from './arc-widget';
import { ArcWidgetContribution } from './arc-widget-contribution';
import { WidgetFactory } from '@theia/core/lib/browser';
import { bindViewContribution } from '@theia/core/lib/browser';

export default new ContainerModule(bind => {
    // Bind the ARC widget
    bind(ArcWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcWidget.ID,
        createWidget: () => ctx.container.get<ArcWidget>(ArcWidget)
    })).inSingletonScope();

    // Bind the widget contribution
    bindViewContribution(bind, ArcWidgetContribution);
});
