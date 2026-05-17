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
import { PreferenceContribution } from '@theia/core/lib/common/preferences/preference-schema';
import { ArcServiceSymbol, ARC_SERVICE_PATH } from '../common/arc-protocol';
import { ArcFrontendService } from './arc-frontend-service';
import { ArcMainWidget } from './arc-main-widget';
import { ArcMainWidgetContribution } from './arc-main-widget-contribution';
import { ArcCommandContribution } from './arc-command-contribution';
import { ArcStatusBarContribution } from './arc-status-bar-contribution';
import { ArcWelcomeWidget } from './arc-welcome-widget';
import { ArcWelcomeContribution } from './arc-welcome-contribution';
import { ArcUIPreferenceSchema } from './arc-ui-preferences';

// Inject global ARC focus styles
function injectArcFocusStyles(): void {
  const style = document.createElement('style');
  style.textContent = `
    .arc-main-widget button:focus-visible,
    .arc-main-widget select:focus-visible,
    .arc-main-widget input[type="checkbox"]:focus-visible,
    .arc-main-widget textarea:focus-visible,
    [class*="arc-"] button:focus-visible,
    [class*="arc-"] select:focus-visible,
    [class*="arc-"] input:focus-visible,
    [class*="arc-"] textarea:focus-visible {
      outline: 2px solid var(--theia-focusBorder);
      outline-offset: 2px;
    }
  `;
  document.head.appendChild(style);
}
injectArcFocusStyles();

export default new ContainerModule(bind => {
  // Service proxy — connects to backend via WebSocket/JSON-RPC
  bind(ArcServiceSymbol).toDynamicValue(ctx => {
    const connection = ctx.container.get(WebSocketConnectionProvider);
    return connection.createProxy(ARC_SERVICE_PATH);
  }).inSingletonScope();

  // Frontend service wrapper
  bind(ArcFrontendService).toSelf().inSingletonScope();

  // UI Preferences
  bind(PreferenceContribution).toConstantValue({
    schema: ArcUIPreferenceSchema,
  });

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

  // Status bar
  bind(ArcStatusBarContribution).toSelf().inSingletonScope();
  bind(FrontendApplicationContribution).toService(ArcStatusBarContribution);

  // Welcome widget
  bind(ArcWelcomeWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcWelcomeWidget.ID,
    createWidget: () => ctx.container.get(ArcWelcomeWidget),
  })).inSingletonScope();
  bindViewContribution(bind, ArcWelcomeContribution);
  bind(FrontendApplicationContribution).toService(ArcWelcomeContribution);
});
