/**
 * ARC Studio Frontend Module
 * 
 * This module provides the frontend contributions for ARC Studio,
 * including the SwarmGraph visualization widget and UI components.
 */

import { ContainerModule } from '@theia/core/shared/inversify';
import { WebSocketConnectionProvider } from '@theia/core/lib/browser';
import { ArcWidget } from './arc-widget';
import { ArcWidgetContribution } from './arc-widget-contribution';
import { WidgetFactory } from '@theia/core/lib/browser';
import { bindViewContribution } from '@theia/core/lib/browser';
import { ArcServicePath, ArcService } from '../common/arc-protocol';
import type { ArcService as IArcService } from '../common/arc-protocol';
import './style/arc-widget.css';

export default new ContainerModule(bind => {
    // Bind the ARC service client (connects to backend via WebSocket)
    bind(ArcService).toDynamicValue(ctx => {
        const connection = ctx.container.get(WebSocketConnectionProvider);
        return connection.createProxy<IArcService>(ArcServicePath);
    }).inSingletonScope();

    // Bind the ARC widget
    bind(ArcWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcWidget.ID,
        createWidget: () => ctx.container.get<ArcWidget>(ArcWidget)
    })).inSingletonScope();

    // Bind the widget contribution
    bindViewContribution(bind, ArcWidgetContribution);
});
