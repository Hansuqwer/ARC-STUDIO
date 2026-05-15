/**
 * ARC Studio Frontend Module
 * 
 * This module provides the frontend contributions for ARC Studio,
 * including the SwarmGraph visualization widget and UI components.
 */

import { ContainerModule } from '@theia/core/shared/inversify';
import { WebSocketConnectionProvider, WidgetFactory, bindViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { ArcWidget } from './arc-widget';
import { ArcWidgetContribution } from './arc-widget-contribution';
import { ArcAdaptersWidget } from './arc-adapters-widget';
import { ArcAdaptersContribution } from './arc-adapters-contribution';
import { ArcWorkflowGraphWidget } from './arc-workflow-graph-widget';
import { ArcWorkflowContribution } from './arc-workflow-contribution';
import { ArcRunTimelineWidget } from './arc-run-timeline-widget';
import { ArcRunsContribution } from './arc-runs-contribution';
import { ArcEventStreamWidget } from './arc-event-stream-widget';
import { ArcEventStreamContribution } from './arc-event-stream-contribution';
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

    // Bind the ARC Adapters widget
    bind(ArcAdaptersWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcAdaptersWidget.ID,
        createWidget: () => ctx.container.get<ArcAdaptersWidget>(ArcAdaptersWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcAdaptersContribution);
    bind(FrontendApplicationContribution).toService(ArcAdaptersContribution);

    // Bind the ARC Workflow Graph widget
    bind(ArcWorkflowGraphWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcWorkflowGraphWidget.ID,
        createWidget: () => ctx.container.get<ArcWorkflowGraphWidget>(ArcWorkflowGraphWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcWorkflowContribution);
    bind(FrontendApplicationContribution).toService(ArcWorkflowContribution);

    // Bind the ARC Run Timeline widget
    bind(ArcRunTimelineWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcRunTimelineWidget.ID,
        createWidget: () => ctx.container.get<ArcRunTimelineWidget>(ArcRunTimelineWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcRunsContribution);
    bind(FrontendApplicationContribution).toService(ArcRunsContribution);

    // Bind the ARC Event Stream widget
    bind(ArcEventStreamWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcEventStreamWidget.ID,
        createWidget: () => ctx.container.get<ArcEventStreamWidget>(ArcEventStreamWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcEventStreamContribution);
    bind(FrontendApplicationContribution).toService(ArcEventStreamContribution);
});
