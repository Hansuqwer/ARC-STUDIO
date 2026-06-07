import { ContainerModule } from '@theia/core/shared/inversify';
import { WebSocketConnectionProvider, WidgetFactory, bindViewContribution, FrontendApplicationContribution, KeybindingContribution } from '@theia/core/lib/browser';
import { CommandContribution } from '@theia/core/lib/common';
import { PreferenceContribution } from '@theia/core/lib/common/preferences/preference-schema';
import { ArcWidget } from './arc-widget';
import { ArcWidgetContribution } from './arc-widget-contribution';
import { ArcAdaptersWidget } from './arc-adapters-widget';
import { ArcAdaptersContribution } from './arc-adapters-contribution';
import { ArcMobileWidget } from './arc-mobile-widget';
import { ArcMobileContribution } from './arc-mobile-contribution';
import { ArcWorkflowGraphWidget } from './arc-workflow-graph-widget';
import { ArcWorkflowContribution } from './arc-workflow-contribution';
import { ArcRunTimelineWidget } from './arc-run-timeline-widget';
import { ArcRunsContribution } from './arc-runs-contribution';
import { ArcEventStreamWidget } from './arc-event-stream-widget';
import { ArcEventStreamContribution } from './arc-event-stream-contribution';
import { ArcHealthWidget } from './arc-health-widget';
import { ArcHealthContribution } from './arc-health-contribution';
import { ArcSimulationWidget } from './arc-simulation-widget';
import { ArcSimulationContribution } from './arc-simulation-contribution';
import { ArcStatusBarContribution } from './arc-status-bar-contribution';
import { ArcWelcomeWidget } from './arc-welcome-widget';
import { ArcWelcomeContribution } from './arc-welcome-contribution';
import { ArcStudioWidget } from './arc-studio-widget';
import { ArcStudioWidgetContribution } from './arc-studio-widget-contribution';
import { ArcKeybindingContribution } from './arc-keybinding-contribution';
import { ArcPreferenceSchema } from './arc-preference-schema';
import { ArenaContribution } from './arena/arena-contribution';
import { ArenaInlineCompletionProvider } from './arena/arena-inline-completion-provider';
import { ArenaService } from './arena/arena-service';
import { ArcServicePath, ArcService } from '../common/arc-protocol';
import type { ArcService as IArcService } from '../common/arc-protocol';
import './style/arc-widget.css';
import './style/arc-studio-widget.css';
import { ArcContextDrawer } from './arc-context-drawer';

export default new ContainerModule(bind => {
    bind(PreferenceContribution).toConstantValue({ schema: ArcPreferenceSchema });
    bind(FrontendApplicationContribution).to(ArcStatusBarContribution).inSingletonScope();

    // Bind the ARC service client (connects to backend via WebSocket)
    bind(ArcService).toDynamicValue(ctx => {
        const connection = ctx.container.get(WebSocketConnectionProvider);
        return connection.createProxy<IArcService>(ArcServicePath);
    }).inSingletonScope();

    // Bind the ARC keybinding and command contribution
    bind(ArcKeybindingContribution).toSelf().inSingletonScope();
    bind(CommandContribution).toService(ArcKeybindingContribution);
    bind(KeybindingContribution).toService(ArcKeybindingContribution);

    // Bind Copilot Arena inline completion integration. It remains preference-gated.
    bind(ArenaService).toSelf().inSingletonScope();
    bind(ArenaInlineCompletionProvider).toSelf().inSingletonScope();
    bind(ArenaContribution).toSelf().inSingletonScope();
    bind(FrontendApplicationContribution).toService(ArenaContribution);
    bind(CommandContribution).toService(ArenaContribution);
    bind(KeybindingContribution).toService(ArenaContribution);

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

    // Mobile Runtime widget (R79 slice 110.6 — simulator/mock only)
    bind(ArcMobileWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcMobileWidget.ID,
        createWidget: () => ctx.container.get<ArcMobileWidget>(ArcMobileWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcMobileContribution);
    bind(FrontendApplicationContribution).toService(ArcMobileContribution);

    // Bind the ARC Workflow Graph widget
    bind(ArcWorkflowGraphWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcWorkflowGraphWidget.ID,
        createWidget: () => ctx.container.get<ArcWorkflowGraphWidget>(ArcWorkflowGraphWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcWorkflowContribution);
    bind(FrontendApplicationContribution).toService(ArcWorkflowContribution);

    // Bind the ARC Run Timeline widget (advanced trace)
    bind(ArcRunTimelineWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcRunTimelineWidget.ID,
        createWidget: () => ctx.container.get<ArcRunTimelineWidget>(ArcRunTimelineWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcRunsContribution);
    bind(FrontendApplicationContribution).toService(ArcRunsContribution);

    // Bind the ARC Event Stream widget (advanced trace)
    bind(ArcEventStreamWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcEventStreamWidget.ID,
        createWidget: () => ctx.container.get<ArcEventStreamWidget>(ArcEventStreamWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcEventStreamContribution);
    bind(FrontendApplicationContribution).toService(ArcEventStreamContribution);

    // Bind the ARC Health Monitor widget
    bind(ArcHealthWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcHealthWidget.ID,
        createWidget: () => ctx.container.get<ArcHealthWidget>(ArcHealthWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcHealthContribution);
    bind(FrontendApplicationContribution).toService(ArcHealthContribution);

    // Bind the ARC IR Simulation Panel widget
    bind(ArcSimulationWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcSimulationWidget.ID,
        createWidget: () => ctx.container.get<ArcSimulationWidget>(ArcSimulationWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcSimulationContribution);
    bind(FrontendApplicationContribution).toService(ArcSimulationContribution);

    // Bind the ARC Welcome widget (manual command; startup controlled by pref)
    bind(ArcWelcomeWidget).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcWelcomeWidget.ID,
        createWidget: () => ctx.container.get<ArcWelcomeWidget>(ArcWelcomeWidget),
    })).inSingletonScope();
    bindViewContribution(bind, ArcWelcomeContribution);
    bind(FrontendApplicationContribution).toService(ArcWelcomeContribution);

    // Bind the ARC Context Drawer (shows AGENTS.md capability cards)
    bind(ArcContextDrawer).toSelf();
    bind(WidgetFactory).toDynamicValue(ctx => ({
        id: ArcContextDrawer.ID,
        createWidget: () => ctx.container.get<ArcContextDrawer>(ArcContextDrawer),
    })).inSingletonScope();
});
