/**
 * ARC Arena Frontend Module — DI wiring for the Arena extension.
 */
import { ContainerModule } from '@theia/core/shared/inversify';
import {
  WidgetFactory,
  bindViewContribution,
  FrontendApplicationContribution,
} from '@theia/core/lib/browser';
import { CommandContribution, MenuContribution } from '@theia/core/lib/common';
import { KeybindingContribution } from '@theia/core/lib/common/keybinding';
import { PreferenceContribution } from '@theia/core/lib/common/preferences/preference-contribution';
import { ArcArenaWidget } from './arc-arena-widget';
import { ArcArenaContribution } from './arc-arena-contribution';
import { ArcArenaService } from '../node/arc-arena-service-impl';
import { ArcArenaPreferenceSchema } from './arc-arena-preferences';

export default new ContainerModule(bind => {
  // Service
  bind(ArcArenaService).toSelf().inSingletonScope();

  // Widget
  bind(ArcArenaWidget).toSelf();
  bind(WidgetFactory).toDynamicValue(ctx => ({
    id: ArcArenaWidget.ID,
    createWidget: () => ctx.container.get(ArcArenaWidget),
  })).inSingletonScope();

  // View contribution (activity bar + toggle command)
  bindViewContribution(bind, ArcArenaContribution);
  bind(FrontendApplicationContribution).toService(ArcArenaContribution);
  bind(CommandContribution).toService(ArcArenaContribution);
  bind(MenuContribution).toService(ArcArenaContribution);
  bind(KeybindingContribution).toService(ArcArenaContribution);

  // Preferences
  bind(PreferenceContribution).toConstantValue({
    schema: ArcArenaPreferenceSchema,
  });
});
