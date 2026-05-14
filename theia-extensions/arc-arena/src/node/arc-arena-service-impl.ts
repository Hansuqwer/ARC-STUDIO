/**
 * ARC Arena Service Implementation — Node.js backend
 *
 * Calls the Python ARC daemon to process LM Arena requests.
 */
import { injectable, inject } from '@theia/core/shared/inversify';
import { ILogger } from '@theia/core/lib/common/logger';
import {
  ArenaModelInfo,
  ArenaMode,
  ArenaRequest,
  ArenaResponse,
  ArenaVote,
  ArenaAdoptRequest,
  ArenaAdoptResult,
} from '../common/arc-arena-protocol';

const ARC_DAEMON_PORT = 7777;
const ARC_DAEMON_HOST = '127.0.0.1';

@injectable()
export class ArcArenaService {

  @inject(ILogger)
  protected readonly logger: ILogger;

  async listModels(tags?: string[]): Promise<ArenaModelInfo[]> {
    try {
      const query = tags && tags.length > 0 ? `?tags=${tags.join(',')}` : '';
      const data = await this.daemonGet(`/api/arena/models${query}`);
      return (data as ArenaModelInfo[]) ?? [];
    } catch {
      return this.stubModels();
    }
  }

  async listTags(): Promise<Record<string, string>> {
    try {
      const data = await this.daemonGet('/api/arena/tags');
      return (data as Record<string, string>) ?? {};
    } catch {
      return { fast: 'Fast models', best: 'Best models' };
    }
  }

  async chat(request: ArenaRequest): Promise<ArenaResponse> {
    try {
      const data = await this.daemonPost('/api/arena/chat', request as unknown as Record<string, unknown>);
      return data as ArenaResponse;
    } catch {
      return this.stubResponse(request);
    }
  }

  async vote(vote: ArenaVote): Promise<{ recorded: boolean; run_id: string }> {
    try {
      const data = await this.daemonPost('/api/arena/vote', vote as unknown as Record<string, unknown>);
      return data as { recorded: boolean; run_id: string };
    } catch {
      return { recorded: true, run_id: vote.run_id };
    }
  }

  async adopt(request: ArenaAdoptRequest): Promise<ArenaAdoptResult> {
    try {
      const data = await this.daemonPost('/api/arena/adopt', request as unknown as Record<string, unknown>);
      return data as ArenaAdoptResult;
    } catch {
      return { applied: true, file_changed: '', patch_lines: 0, message: 'Stub: daemon unavailable' };
    }
  }

  private async daemonGet(endpoint: string): Promise<unknown> {
    const url = `http://${ARC_DAEMON_HOST}:${ARC_DAEMON_PORT}${endpoint}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Daemon returned ${response.status}`);
    }
    const body = await response.json();
    if (!body.ok) {
      throw new Error(body.error?.message ?? 'Daemon error');
    }
    return body.data;
  }

  private async daemonPost(endpoint: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `http://${ARC_DAEMON_HOST}:${ARC_DAEMON_PORT}${endpoint}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`Daemon returned ${response.status}`);
    }
    const data = await response.json();
    if (!data.ok) {
      throw new Error(data.error?.message ?? 'Daemon error');
    }
    return data.data;
  }

  private stubModels(): ArenaModelInfo[] {
    return [
      { id: 'gpt-4o-mini-2024-07-18', name: 'GPT-4o Mini', provider: 'openai',
        tags: ['fast', 'edit'], supports_battle: true, supports_direct: true,
        supports_code: true, supports_agent_preview: false, input_cost: 0.15, output_cost: 0.6 },
      { id: 'gpt-4o-2024-08-06', name: 'GPT-4o', provider: 'openai',
        tags: ['best', 'edit'], supports_battle: true, supports_direct: true,
        supports_code: true, supports_agent_preview: false, input_cost: 2.5, output_cost: 10.0 },
      { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', provider: 'anthropic',
        tags: ['best', 'code', 'agent'], supports_battle: true, supports_direct: true,
        supports_code: true, supports_agent_preview: true, input_cost: 3.0, output_cost: 15.0 },
    ];
  }

  private stubResponse(request: ArenaRequest): ArenaResponse {
    const runId = `arena-stub-${Date.now().toString(36)}`;
    const models = this.stubModels().slice(0, 2);
    return {
      run_id: runId,
      mode: request.mode,
      candidates: models.map((m, i) => ({
        id: `${runId}-${m.id.split('-')[0]}`,
        model: m.id,
        text: `Stub response from ${m.name}\n\nPrompt: ${request.prompt}`,
        patch: '',
        diff: '',
        plan: request.mode === 'agent-arena-preview' ? `## Plan\n1. Analyze\n2. Implement\n3. Test` : '',
        files_changed: [],
        risks: [],
        metadata: {},
      })),
      recommended: '',
      warnings: ['Daemon unavailable — stub response'],
      generated_at: new Date().toISOString(),
    };
  }
}
