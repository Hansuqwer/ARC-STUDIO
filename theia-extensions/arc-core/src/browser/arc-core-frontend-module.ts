/**
 * ARC Core — Frontend Module
 *
 * Registers the ARC frontend service proxy, commands, and the main ARC widget.
 * Source: https://theia-ide.org/docs/extensions/
 */

import { ContainerModule } from '@theia/core/shared/inversify';
import { WebSocketConnectionProvider } from '@theia/core/lib/browser/messaging/ws-connection-provider';
import { CommandContribution, MenuContribution } from '@theia/core/lib/common';
import { WidgetFactory, bindViewContribution, FrontendApplicationContribution } from '@theia/core/lib/browser';
import { TabBarToolbarContribution } from '@theia/core/lib/browser/shell/tab-bar-toolbar';
import { ArcServiceSymbol, ARC_SERVICE_PATH } from '../common/arc-protocol';
import { ArcFrontendService } from './arc-frontend-service';
import { ArcMainWidget } from './arc-main-widget';
import { ArcMainWidgetContribution } from './arc-main-widget-contribution';
import { ArcCommandContribution } from './arc-command-contribution';

export default new ContainerModule(bind => {
  // Service proxy — connects to backend via WebSocket/JSON-RPC
  bind(ArcServiceSymbol).toDynamicValue(ctx => {
    const connection = ctx.container.get(WebSocketConnectionProvider);
    return connection.createProxy(ARC_SERVICE_PATH);
  }).inSingletonScope();

  // Frontend service wrapper
  bind(ArcFrontendService).toSelf().inSingletonScope();

  // Main widget
  bind(ArcMainWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcMainWidget.ID,
    createWidget: () => ctx.container.get(ArcMainWidget),
  })).inSingletonScope();

  // Widget contribution (registers in Activity Bar and View menu)
  bindViewContribution(bind, ArcMainWidgetContribution);
  bind(FrontendApplicationContribution).toService(ArcMainWidgetContribution);
  bind(TabBarToolbarContribution).toService(ArcMainWidgetContribution);

  // Commands
  bind(ArcCommandContribution).toSelf().inSingletonScope();
  bind(CommandContribution).toService(ArcCommandContribution);
  bind(MenuContribution).toService(ArcCommandContribution);
});
