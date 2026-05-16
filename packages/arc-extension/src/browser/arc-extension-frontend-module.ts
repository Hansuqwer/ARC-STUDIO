import { ContainerModule } from '@theia/core/shared/inversify';
import { WebSocketConnectionProvider, WidgetFactory, bindViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { PreferenceContribution } from '@theia/core/lib/common/preferences/preference-schema';
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
import { ArcHealthWidget } from './arc-health-widget';
import { ArcHealthContribution } from './arc-health-contribution';
import { ArcStudioWidget } from './arc-studio-widget';
import { ArcStudioWidgetContribution } from './arc-studio-widget-contribution';
import { ArcPreferenceSchema } from './arc-preference-schema';
import { ArcServicePath, ArcService } from '../common/arc-protocol';
import type { ArcService as IArcService } from '../common/arc-protocol';
import './style/arc-widget.css';
import './style/arc-studio-widget.css';

export default new ContainerModule(bind => {
    bind(PreferenceContribution).toConstantValue({ schema: ArcPreferenceSchema });

    // Bind the ARC service client (connects to backend via WebSocket)
    bind(ArcService).toDynamicValue(ctx => {
        const connection = ctx.container.get(WebSocketConnectionProvider);
        return connection.createProxy<IArcService>(ArcServicePath);
    }).inSingletonScope();

    // Bind the ARC Studio widget (primary/default)
    bind(ArcStudioWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcStudioWidget.ID,
        createWidget: () => ctx.container.get<ArcStudioWidget>(ArcStudioWidget)
    })).inSingletonScope();
    bindViewContribution(bind, ArcStudioWidgetContribution);
    bind(FrontendApplicationContribution).toService(ArcStudioWidgetContribution);

    // Bind the legacy ARC widget (kept for backward compatibility)
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

    // Bind the ARC Run Timeline widget (advanced trace — available via command, not default-opened)
    bind(ArcRunTimelineWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcRunTimelineWidget.ID,
        createWidget: () => ctx.container.get<ArcRunTimelineWidget>(ArcRunTimelineWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcRunsContribution);

    // Bind the ARC Event Stream widget (advanced trace — available via command, not default-opened)
    bind(ArcEventStreamWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcEventStreamWidget.ID,
        createWidget: () => ctx.container.get<ArcEventStreamWidget>(ArcEventStreamWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcEventStreamContribution);

    // Bind the ARC Health Monitor widget
    bind(ArcHealthWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcHealthWidget.ID,
        createWidget: () => ctx.container.get<ArcHealthWidget>(ArcHealthWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcHealthContribution);
    bind(FrontendApplicationContribution).toService(ArcHealthContribution);
});
