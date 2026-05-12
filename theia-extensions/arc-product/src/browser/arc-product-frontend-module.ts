/**
 * ARC Studio — Product Frontend Module
 *
 * Registers product branding: welcome page override, about dialog customization.
 * Source: https://theia-ide.org/docs/blueprint_documentation/
 * Source: https://github.com/eclipse-theia/theia-ide (theia-blueprint-product)
 */

import { ContainerModule } from '@theia/core/shared/inversify';
import { GettingStartedWidget } from '@theia/getting-started/lib/browser/getting-started-widget';
import { WidgetFactory } from '@theia/core/lib/browser/widget-manager';
import { ArcGettingStartedWidget } from './arc-getting-started-widget';

export default new ContainerModule((bind, unbind, isBound, rebind) => {
  // Override the default Getting Started (welcome page) with ARC Studio's
  rebind(GettingStartedWidget).to(ArcGettingStartedWidget).inSingletonScope();

  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: GettingStartedWidget.ID,
    createWidget: () => ctx.container.get<ArcGettingStartedWidget>(ArcGettingStartedWidget)
  })).inSingletonScope();
});
