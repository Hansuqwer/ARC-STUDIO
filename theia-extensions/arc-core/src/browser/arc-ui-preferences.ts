/**
 * ARC UI Preferences Schema
 */
import { PreferenceSchema } from '@theia/core/lib/common/preferences/preference-schema';

export const ArcUIPreferenceSchema: PreferenceSchema = {
  properties: {
    'arc.ui.showOnboarding': {
      type: 'boolean',
      default: true,
      description: 'Show welcome widget on first launch.',
    },
    'arc.ui.autoOpenSidebar': {
      type: 'boolean',
      default: true,
      description: 'Auto-open ARC sidebar on startup.',
    },
    'arc.ui.showStatusBar': {
      type: 'boolean',
      default: true,
      description: 'Show ARC status bar items.',
    },
    'arc.ui.compactSidebar': {
      type: 'boolean',
      default: false,
      description: 'Use compact sidebar layout.',
    },
  },
};
