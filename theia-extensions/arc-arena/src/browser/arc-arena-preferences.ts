/**
 * ARC Arena Preferences Schema
 */
import { PreferenceSchema } from '@theia/core/lib/common/preferences/preference-schema';

export const ArcArenaPreferenceSchema: PreferenceSchema = {
  type: 'object',
  properties: {
    'arc.arena.defaultMode': {
      type: 'string',
      default: 'direct',
      enum: ['battle', 'direct', 'code', 'agent-arena-preview'],
      description: 'Default Arena interaction mode.',
    },
    'arc.arena.serverUrl': {
      type: 'string',
      default: '',
      description: 'Override Arena server URL (empty = use ARC daemon).',
    },
    'arc.arena.privacy': {
      type: 'string',
      default: 'Private',
      enum: ['Private', 'Debug', 'Research'],
      description: 'Privacy level for code sent to Arena providers.',
    },
    'arc.arena.defaultModelTags': {
      type: 'array',
      items: { type: 'string' },
      default: ['fast'],
      description: 'Default model tags to filter Arena models.',
    },
    'arc.arena.maxOutputLines': {
      type: 'number',
      default: 100,
      minimum: 1,
      description: 'Maximum lines in Arena output.',
    },
  },
};
