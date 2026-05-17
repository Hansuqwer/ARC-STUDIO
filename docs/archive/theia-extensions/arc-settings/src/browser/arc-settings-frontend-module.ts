/**
 * ARC Settings — Frontend Module
 * Registers ARC preferences: daemon path, Python env, port, provider API keys.
 * Source: https://theia-ide.org/docs/preferences/
 */
import { ContainerModule } from '@theia/core/shared/inversify';
import { PreferenceContribution } from '@theia/core/lib/common/preferences/preference-schema';
import { ArcPreferenceSchema } from './arc-preference-schema';

export default new ContainerModule(bind => {
  bind(PreferenceContribution).toConstantValue({ schema: ArcPreferenceSchema });
});
