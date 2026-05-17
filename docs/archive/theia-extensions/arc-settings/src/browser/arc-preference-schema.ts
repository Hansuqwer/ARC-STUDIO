/**
 * ARC Preference Schema
 * All ARC Studio user preferences.
 */
import { PreferenceSchema } from '@theia/core/lib/common/preferences/preference-schema';

export const ArcPreferenceSchema: PreferenceSchema = {
  properties: {
    'arc.daemon.port': {
      type: 'number',
      default: 7777,
      description: 'Port for the ARC Python daemon HTTP server.',
    },
    'arc.daemon.host': {
      type: 'string',
      default: '127.0.0.1',
      description: 'Host for the ARC Python daemon.',
    },
    'arc.daemon.autoStart': {
      type: 'boolean',
      default: false,
      description: 'Automatically start the ARC daemon when the IDE opens.',
    },
    'arc.python.executable': {
      type: 'string',
      default: 'uv',
      description: 'Python launcher executable (uv, python3, or full path).',
    },
    'arc.python.projectDir': {
      type: 'string',
      default: '',
      description: 'Path to the ARC Python project directory (containing pyproject.toml).',
    },
    'arc.context.context7ApiKey': {
      type: 'string',
      default: '',
      description: 'Context7 API key for documentation retrieval.',
    },
    'arc.context.githubToken': {
      type: 'string',
      default: '',
      description: 'GitHub token for code search API.',
    },
    'arc.extensions.enableFlutter': {
      type: 'boolean',
      default: false,
      description: 'Enable the experimental Flutter project extension.',
    },
    'arc.extensions.enableA2UI': {
      type: 'boolean',
      default: false,
      description: 'Enable the experimental A2UI declarative UI extension.',
    },
    'arc.ui.showMockWarnings': {
      type: 'boolean',
      default: true,
      description: 'Show warnings when ARC is using fixture/mock data.',
    },
    'arc.swarmgraph.provider': {
      type: 'string',
      default: 'openai',
      description: 'Default provider id for ARC runs. This is non-secret; API keys must come from environment or future secure storage.',
    },
    'arc.swarmgraph.baseUrl': {
      type: 'string',
      default: '',
      description: 'Optional SwarmGraph provider base URL override. Leave empty for provider default.',
    },
    'arc.run.defaultProfile': {
      type: 'string',
      default: 'stub',
      enum: ['stub', 'local-safe', 'local-paid', 'gateway'],
      description: 'Default run profile: stub (safe), local-safe (network), local-paid (network+paid), gateway (full access).',
    },
    'arc.telemetry.otlpEndpoint': {
      type: 'string',
      default: '',
      description: 'OTLP endpoint for trace export (e.g., http://localhost:4317). Leave empty to disable telemetry export.',
    },
  },
};
