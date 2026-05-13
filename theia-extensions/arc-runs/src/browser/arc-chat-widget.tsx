import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { CommandService } from '@theia/core/lib/common/command';
import { PreferenceService } from '@theia/core/lib/common/preferences/preference-service';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { RuntimeCapabilityReport, RuntimeId, RunRecord } from 'arc-core/lib/common/arc-protocol';

type ChatMessage = {
  role: 'user' | 'assistant' | 'system';
  text: string;
  runId?: string;
};

const ARENA_MODES = ['direct', 'battle', 'code', 'agent-arena-preview'] as const;
type ArenaMode = (typeof ARENA_MODES)[number];

const DEFAULT_ARENA_MODELS: Record<string, string> = {
  'gpt-4o-mini-2024-07-18': 'GPT-4o Mini',
  'gpt-4o-2024-08-06': 'GPT-4o',
  'claude-sonnet-4-20250514': 'Claude Sonnet 4',
  'codestral-2405': 'Codestral',
  'deepseek-coder-v2': 'DeepSeek Coder V2',
};

@injectable()
export class ArcChatWidget extends ReactWidget {
  static readonly ID = 'arc:chat';
  static readonly LABEL = 'ARC Chat';

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  @inject(CommandService)
  protected readonly commandService: CommandService;

  @inject(PreferenceService)
  protected readonly preferences: PreferenceService;

  protected prompt = '';
  protected loading = false;
  protected capabilities: RuntimeCapabilityReport[] = [];
  protected selectedRuntime: RuntimeId = 'auto';
  protected selectedRuntimes = new Set<RuntimeId>();
  protected allowPaidCalls = false;
  protected profileId = 'stub';
  protected lastError?: string;
  protected arenaMode: ArenaMode = 'direct';
  protected arenaModel = 'gpt-4o-mini-2024-07-18';
  protected messages: ChatMessage[] = [
    { role: 'system', text: 'Prompt local ARC runtimes. Select one runtime or multiple runtimes for combo mode.' },
  ];

  @postConstruct()
  protected init(): void {
    this.id = ArcChatWidget.ID;
    this.title.label = ArcChatWidget.LABEL;
    this.title.caption = 'ARC Chat';
    this.title.closable = true;
    this.title.iconClass = 'codicon codicon-comment-discussion';
    this.profileId = this.preferences.get<string>('arc.run.defaultProfile', 'stub');
    this.loadCapabilities();
  }

  protected async loadCapabilities(): Promise<void> {
    try {
      const result = await this.arcService.listRuntimeCapabilities();
      this.capabilities = result.data?.runtimes ?? [];
      this.lastError = result.error?.message;
    } catch (error) {
      this.lastError = String(error);
    } finally {
      this.update();
    }
  }

  protected render(): React.ReactNode {
    return (
      <div style={styles.root}>
        <div style={styles.messages}>{this.messages.map((message, index) => this.renderMessage(message, index))}</div>
        {this.renderRuntimeControls()}
        <textarea
          style={styles.prompt}
          rows={4}
          value={this.prompt}
          onChange={event => { this.prompt = event.currentTarget.value; this.update(); }}
          placeholder="Ask ARC to run a workflow prompt..."
        />
        <div style={styles.actions}>
          <button style={styles.primaryButton} disabled={this.loading || !this.prompt.trim()} onClick={() => this.submitPrompt()}>
            {this.loading ? 'Running...' : 'Send Prompt'}
          </button>
          <button style={styles.secondaryButton} disabled={this.loading} onClick={() => this.loadCapabilities()}>Refresh Runtimes</button>
        </div>
        {this.lastError && <pre style={styles.error}>{this.lastError}</pre>}
      </div>
    );
  }

  protected renderMessage(message: ChatMessage, index: number): React.ReactNode {
    return (
      <div key={index} style={{ ...styles.message, ...(message.role === 'user' ? styles.userMessage : {}) }}>
        <strong>{message.role}</strong>
        <div style={styles.messageText}>{message.text}</div>
        {message.runId && (
          <div style={{ marginTop: 6, display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={styles.runId}>Run: {message.runId}</span>
            <button style={styles.secondaryButton} onClick={() => this.openTimeline(message.runId!)}>Open in Timeline</button>
          </div>
        )}
      </div>
    );
  }

  protected renderRuntimeControls(): React.ReactNode {
    const runnable = this.capabilities.filter(runtime => runtime.runtime_id !== 'auto');
    return (
      <div style={styles.runtimeBox}>
        <label>
          Runtime:{' '}
          <select
            style={styles.select}
            value={this.selectedRuntime}
            onChange={event => { this.selectedRuntime = event.currentTarget.value as RuntimeId; this.update(); }}
          >
            <option value="auto">Auto</option>
            {runnable.map(runtime => (
              <option key={runtime.runtime_id} value={runtime.runtime_id as RuntimeId} disabled={!runtime.can_run}>
                {this.runtimeLabel(runtime)}
              </option>
            ))}
          </select>
        </label>
        <div style={styles.comboList}>
          <strong>Combo:</strong>
          {runnable.map(runtime => (
            <label key={runtime.runtime_id} style={styles.checkboxLabel} title={runtime.reason ?? ''}>
              <input
                type="checkbox"
                disabled={!runtime.can_run}
                checked={this.selectedRuntimes.has(runtime.runtime_id as RuntimeId)}
                onChange={event => this.toggleComboRuntime(runtime.runtime_id as RuntimeId, event.currentTarget.checked)}
              />
              {this.runtimeLabel(runtime)}
            </label>
          ))}
        </div>
        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={this.allowPaidCalls}
            onChange={event => { this.allowPaidCalls = event.currentTarget.checked; this.update(); }}
          />
          Allow paid/provider calls
        </label>
        <label style={styles.checkboxLabel}>
          Profile:{' '}
          <select
            style={styles.select}
            value={this.profileId}
            onChange={event => { this.profileId = event.currentTarget.value; this.update(); }}
          >
            <option value="stub">Stub (Safe)</option>
            <option value="local-safe">Local Safe</option>
            <option value="local-paid">Local Paid</option>
            <option value="gateway">Gateway (Full Access)</option>
          </select>
        </label>
        {this.selectedRuntime === 'lmarena' && this.renderArenaControls()}
        {this.renderReadiness()}
      </div>
    );
  }

  protected renderArenaControls(): React.ReactNode {
    return (
      <div style={{ ...styles.runtimeBox, marginTop: 4 }}>
        <label>
          Arena Mode:{' '}
          <select
            style={styles.select}
            value={this.arenaMode}
            onChange={event => { this.arenaMode = event.currentTarget.value as ArenaMode; this.update(); }}
          >
            {ARENA_MODES.map(mode => (
              <option key={mode} value={mode}>{mode}</option>
            ))}
          </select>
        </label>
        <label>
          Arena Model:{' '}
          <select
            style={styles.select}
            value={this.arenaModel}
            onChange={event => { this.arenaModel = event.currentTarget.value; this.update(); }}
          >
            {Object.entries(DEFAULT_ARENA_MODELS).map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
        </label>
      </div>
    );
  }

  protected renderReadiness(): React.ReactNode {
    const missing = this.capabilities.filter(runtime => !runtime.can_run);
    if (missing.length === 0) {
      return null;
    }
    return (
      <div style={styles.readiness}>
        {missing.map(runtime => (
          <div key={runtime.runtime_id}>
            <strong>{runtime.runtime_id}</strong>: {runtime.reason || runtime.availability}
            {runtime.required_env.length > 0 && ` Set ${runtime.required_env.join(', ')}.`}
          </div>
        ))}
      </div>
    );
  }

  protected toggleComboRuntime(runtime: RuntimeId, checked: boolean): void {
    if (checked) {
      this.selectedRuntimes.add(runtime);
    } else {
      this.selectedRuntimes.delete(runtime);
    }
    this.update();
  }

  protected runtimeLabel(runtime: RuntimeCapabilityReport): string {
    const status = runtime.can_run ? 'run' : runtime.availability.replace(/_/g, ' ');
    const paid = runtime.requires_paid_calls ? ', paid' : '';
    return `${runtime.runtime_id} (${status}${paid})`;
  }

  protected runtimeSelection(): RuntimeId | RuntimeId[] {
    const combo = Array.from(this.selectedRuntimes);
    return combo.length > 1 ? combo : this.selectedRuntime;
  }

  protected async openTimeline(runId: string): Promise<void> {
    await this.commandService.executeCommand('arc:open-run-timeline');
  }

  protected async submitPrompt(): Promise<void> {
    const prompt = this.prompt.trim();
    if (!prompt) {
      return;
    }
    this.loading = true;
    this.lastError = undefined;
    this.prompt = '';
    this.messages.push({ role: 'user', text: prompt });
    this.update();
    try {
      const runtime = this.runtimeSelection();
      const inputs: Record<string, unknown> = { prompt };
      let workflowId = 'wf-swarmgraph-001';

      // When lmarena is selected, route through the Arena adapter
      if (runtime === 'lmarena') {
        workflowId = `arena-${this.arenaMode}`;
        inputs.arena_mode = this.arenaMode;
        inputs.arena_model = this.arenaModel;
      }

      const result = await this.arcService.startRun(workflowId, inputs, runtime, this.allowPaidCalls ? true : undefined);
      if (result.data) {
        this.messages.push(this.messageFromRun(result.data));
      } else {
        this.lastError = result.error?.message ?? 'Run failed.';
        this.messages.push({ role: 'assistant', text: this.lastError });
      }
    } catch (error) {
      this.lastError = String(error);
      this.messages.push({ role: 'assistant', text: this.lastError });
    } finally {
      this.loading = false;
      this.update();
    }
  }

  protected messageFromRun(run: RunRecord): ChatMessage {
    const isArena = run.runtime === 'lmarena' || run.workflow_id.startsWith('arena-');
    if (isArena) {
      const mode = run.metadata?.arena_mode ?? run.workflow_id.replace('arena-', '');
      const model = run.metadata?.arena_model ?? '';
      const warnings = Array.isArray(run.metadata?.warnings) ? (run.metadata.warnings as string[]).join('; ') : '';
      const output = this.finalOutput(run) || `Arena ${mode} completed (${model || 'stub'}).`;
      return { role: 'assistant', text: `${output}${warnings ? `\n\n⚠ ${warnings}` : ''}`, runId: run.id };
    }
    const output = this.finalOutput(run) || `Run ${run.status}. Runtime: ${run.runtime}.`;
    return { role: 'assistant', text: output, runId: run.id };
  }

  protected finalOutput(run: RunRecord): string | undefined {
    for (let i = run.events.length - 1; i >= 0; i--) {
      const event = run.events[i];
      const value = event.data.final_output ?? event.data.output ?? event.data.message;
      if (typeof value === 'string' && value.length > 0) {
        return value;
      }
    }
    return undefined;
  }
}

const styles: Record<string, React.CSSProperties> = {
  root: { display: 'flex', flexDirection: 'column', gap: '10px', height: '100%', padding: '14px', color: 'var(--theia-foreground)', fontFamily: 'var(--theia-ui-font-family)' },
  messages: { flex: 1, overflow: 'auto', display: 'grid', alignContent: 'start', gap: '8px' },
  message: { border: '1px solid var(--theia-widget-border)', borderRadius: 6, padding: '8px 10px', backgroundColor: 'var(--theia-editor-background)' },
  userMessage: { backgroundColor: 'var(--theia-list-activeSelectionBackground)' },
  messageText: { marginTop: 4, whiteSpace: 'pre-wrap', fontSize: 12 },
  runId: { marginTop: 6, fontSize: 11, color: 'var(--theia-descriptionForeground)' },
  runtimeBox: { display: 'grid', gap: 8, padding: 10, border: '1px solid var(--theia-widget-border)', borderRadius: 6 },
  comboList: { display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', fontSize: 12 },
  checkboxLabel: { display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 },
  readiness: { display: 'grid', gap: 4, color: '#ffb74d', fontSize: 11 },
  prompt: { resize: 'vertical', color: 'var(--theia-input-foreground)', backgroundColor: 'var(--theia-input-background)', border: '1px solid var(--theia-input-border)', borderRadius: 4, padding: 8, fontFamily: 'inherit' },
  select: { color: 'var(--theia-input-foreground)', backgroundColor: 'var(--theia-input-background)', border: '1px solid var(--theia-input-border)', borderRadius: 4, padding: '4px 6px' },
  actions: { display: 'flex', gap: 8 },
  primaryButton: { padding: '6px 12px', color: 'var(--theia-button-foreground)', backgroundColor: 'var(--theia-button-background)', border: 'none', borderRadius: 4 },
  secondaryButton: { padding: '6px 12px', color: 'var(--theia-secondaryButton-foreground)', backgroundColor: 'var(--theia-secondaryButton-background)', border: 'none', borderRadius: 4 },
  error: { color: '#ef9a9a', border: '1px solid #ef5350', borderRadius: 4, padding: 8, whiteSpace: 'pre-wrap' },
};
