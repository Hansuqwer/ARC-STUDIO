/**
 * ARC Arena Widget — LM Arena integration for battle, direct, code, and agent-arena-preview.
 *
 * Primary interaction point for /models lmarena.
 */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { PreferenceService } from '@theia/core/lib/common/preferences/preference-service';
import { MessageService } from '@theia/core/lib/common/message-service';
import { CommandService } from '@theia/core/lib/common/command';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { ArcArenaService } from '../node/arc-arena-service-impl';
import {
  ArenaMode,
  ArenaModelInfo,
  ArenaCandidate,
  ArenaResponse,
  ArenaRequest,
  ArenaVote,
  PrivacyLevel,
} from '../common/arc-arena-protocol';

interface ChatMessage {
  role: 'user' | 'assistant' | 'arena';
  text: string;
  mode?: ArenaMode;
  candidates?: ArenaCandidate[];
  runId?: string;
}

@injectable()
export class ArcArenaWidget extends ReactWidget {
  static readonly ID = 'arc:arena';
  static readonly LABEL = 'ARC Arena';

  @inject(ArcArenaService)
  protected readonly arenaService: ArcArenaService;

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  @inject(PreferenceService)
  protected readonly preferences: PreferenceService;

  @inject(MessageService)
  protected readonly messages: MessageService;

  @inject(CommandService)
  protected readonly commandService: CommandService;

  // ─── State ──────────────────────────────────────────────────────────────
  protected mode: ArenaMode = 'direct';
  protected models: ArenaModelInfo[] = [];
  protected selectedModel = '';
  protected selectedTags: string[] = [];
  protected prompt = '';
  protected loading = false;
  protected privacy: PrivacyLevel = 'Private';
  protected profileId = 'local-safe';
  protected allowPaidCalls = false;
  protected arenaResponse: ArenaResponse | null = null;
  protected lastError = '';
  protected selectedCandidateIdx = 0;
  protected chatHistory: ChatMessage[] = [];

  @postConstruct()
  protected init(): void {
    this.id = ArcArenaWidget.ID;
    this.title.label = ArcArenaWidget.LABEL;
    this.title.caption = 'ARC Arena — LM Arena Integration';
    this.title.closable = true;
    this.title.iconClass = 'codicon codicon-rocket';
    this.loadPreferences();
    this.loadModels();
    this.addWelcomeMessage();
  }

  protected addWelcomeMessage(): void {
    this.chatHistory.push({
      role: 'assistant',
      text: 'Welcome to ARC Arena.\n\nUse /models to see available models.\nPick a mode: battle, direct, code, or agent-arena-preview.\nThen enter your prompt.',
    });
  }

  protected loadPreferences(): void {
    this.mode = this.preferences.get<ArenaMode>('arc.arena.defaultMode', 'direct');
    this.privacy = this.preferences.get<PrivacyLevel>('arc.arena.privacy', 'Private');
    this.selectedTags = this.preferences.get<string[]>('arc.arena.defaultModelTags', ['fast']);
    this.profileId = this.preferences.get<string>('arc.run.defaultProfile', 'local-safe');
    this.allowPaidCalls = this.profileId === 'local-paid' || this.profileId === 'gateway';
  }

  protected async loadModels(): Promise<void> {
    try {
      this.models = await this.arenaService.listModels(this.selectedTags);
      if (this.models.length > 0 && !this.selectedModel) {
        this.selectedModel = this.models[0].id;
      }
      this.update();
    } catch {
      this.models = [];
    }
  }

  // ─── Public methods (called from commands) ──────────────────────────────

  adoptSelected(): void {
    if (!this.arenaResponse || this.arenaResponse.candidates.length === 0) return;
    const candidate = this.arenaResponse.candidates[this.selectedCandidateIdx];
    if (!candidate) return;
    this.arenaService.adopt({
      run_id: this.arenaResponse.run_id,
      candidate_id: candidate.id,
    }).then(result => {
      this.messages.info(`Adopted: ${result.file_changed} (${result.patch_lines} lines)`);
    }).catch(err => {
      this.messages.error(`Adopt failed: ${err}`);
    });
  }

  rejectAll(): void {
    this.arenaResponse = null;
    this.chatHistory.push({ role: 'arena', text: 'All candidates rejected.', runId: '' });
    this.update();
  }

  voteA(): void {
    if (!this.arenaResponse || this.arenaResponse.candidates.length < 2) return;
    this.recordVote(this.arenaResponse.candidates[0].id, this.arenaResponse.candidates[1].id);
  }

  voteB(): void {
    if (!this.arenaResponse || this.arenaResponse.candidates.length < 2) return;
    this.recordVote(this.arenaResponse.candidates[1].id, this.arenaResponse.candidates[0].id);
  }

  protected recordVote(winnerId: string, loserId: string): void {
    if (!this.arenaResponse) return;
    const vote: ArenaVote = {
      run_id: this.arenaResponse.run_id,
      winner_candidate_id: winnerId,
      loser_candidate_id: loserId,
      profile_id: this.profileId,
    };
    this.arenaService.vote(vote).catch(() => {});
    this.chatHistory.push({
      role: 'arena',
      text: `Vote recorded for candidate ${winnerId.substring(0, 8)}`,
      runId: this.arenaResponse.run_id,
    });
    this.arenaResponse = null;
    this.update();
  }

  // ─── Submission ─────────────────────────────────────────────────────────

  protected async submitPrompt(): Promise<void> {
    const text = this.prompt.trim();
    if (!text || this.loading) return;
    this.loading = true;
    this.lastError = '';
    this.arenaResponse = null;
    this.chatHistory.push({ role: 'user', text, mode: this.mode });
    this.prompt = '';
    this.update();

    try {
      const request: ArenaRequest = {
        mode: this.mode,
        prompt: text,
        model: this.selectedModel,
        model_tags: this.selectedTags,
        privacy: this.privacy,
        allow_paid_calls: this.allowPaidCalls,
        profile_id: this.profileId,
      };
      const response = await this.arenaService.chat(request);
      this.arenaResponse = response;
      this.chatHistory.push({
        role: 'arena',
        text: this.formatResponseSummary(response),
        mode: response.mode,
        candidates: response.candidates,
        runId: response.run_id,
      });
    } catch (err) {
      this.lastError = String(err);
      this.chatHistory.push({ role: 'assistant', text: `Error: ${this.lastError}` });
    } finally {
      this.loading = false;
      this.update();
    }
  }

  protected formatResponseSummary(response: ArenaResponse): string {
    const counts = response.candidates.map(c => c.model || '?').join(', ');
    let summary = `**${response.mode.toUpperCase()}** — ${response.candidates.length} candidate(s): ${counts}`;
    if (response.warnings.length > 0) {
      summary += `\n\n⚠ ${response.warnings.join('; ')}`;
    }
    return summary;
  }

  // ─── Rendering ──────────────────────────────────────────────────────────

  protected render(): React.ReactNode {
    return (
      <div style={containerStyle}>
        {this.renderHeader()}
        {this.renderControls()}
        {this.renderChatHistory()}
        {this.renderBattleView()}
        {this.renderInput()}
      </div>
    );
  }

  protected renderHeader(): React.ReactNode {
    return (
      <div style={headerStyle}>
        <h2 style={{ margin: 0, fontSize: 14 }}>ARC Arena</h2>
        <span style={{ fontSize: 11, opacity: 0.7 }}>
          {this.models.length} models · {this.privacy}
        </span>
      </div>
    );
  }

  protected renderControls(): React.ReactNode {
    return (
      <div style={controlsStyle}>
        {/* Mode selector */}
        <label style={labelStyle}>
          Mode:
          <select
            style={selectStyle}
            value={this.mode}
            onChange={e => { this.mode = e.currentTarget.value as ArenaMode; this.update(); }}
          >
            <option value="battle">⚔ Battle</option>
            <option value="direct">💬 Direct</option>
            <option value="code">🔧 Code</option>
            <option value="agent-arena-preview">🤖 Agent Preview</option>
          </select>
        </label>

        {/* Model selector */}
        <label style={labelStyle}>
          Model:
          <select
            style={selectStyle}
            value={this.selectedModel}
            onChange={e => { this.selectedModel = e.currentTarget.value; this.update(); }}
          >
            {this.models.filter(m => this.modeSupports(m)).map(m => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.provider})
              </option>
            ))}
          </select>
        </label>

        {/* Profile */}
        <label style={labelStyle}>
          Profile:
          <select
            style={selectStyle}
            value={this.profileId}
            onChange={e => { this.profileId = e.currentTarget.value; this.update(); }}
          >
            <option value="stub">Stub</option>
            <option value="local-safe">Local Safe</option>
            <option value="local-paid">Local Paid</option>
            <option value="gateway">Gateway</option>
          </select>
        </label>
      </div>
    );
  }

  protected modeSupports(m: ArenaModelInfo): boolean {
    switch (this.mode) {
      case 'battle': return m.supports_battle;
      case 'direct': return m.supports_direct;
      case 'code': return m.supports_code;
      case 'agent-arena-preview': return m.supports_agent_preview;
      default: return true;
    }
  }

  protected renderChatHistory(): React.ReactNode {
    return (
      <div style={chatHistoryStyle}>
        {this.chatHistory.map((msg, i) => (
          <div key={i} style={{
            ...messageStyle,
            backgroundColor: msg.role === 'user' ? 'var(--theia-editor-selectionBackground)' : 'transparent',
          }}>
            <div style={{ fontSize: 10, fontWeight: 600, marginBottom: 4, opacity: 0.6 }}>
              {msg.role.toUpperCase()}{msg.mode ? ` · ${msg.mode}` : ''}{msg.runId ? ` · ${msg.runId.substring(0, 12)}` : ''}
            </div>
            <div style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{msg.text}</div>
            {msg.candidates && msg.candidates.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {msg.candidates.map((c, ci) => (
                  <div
                    key={c.id}
                    style={{
                      ...candidateCardStyle,
                      borderColor: ci === this.selectedCandidateIdx ? 'var(--theia-textLink-foreground)' : 'var(--theia-widget-border)',
                    }}
                    onClick={() => { this.selectedCandidateIdx = ci; this.update(); }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 11 }}>{c.model || `Candidate ${ci + 1}`}</div>
                    <div style={{ fontSize: 10, opacity: 0.7, maxHeight: 80, overflow: 'hidden' }}>
                      {c.text.substring(0, 200)}
                    </div>
                    {c.plan && <div style={{ fontSize: 10, color: 'var(--theia-textLink-foreground)' }}>Has plan</div>}
                    {c.patch && <div style={{ fontSize: 10, color: 'var(--theia-charts-green)' }}>Has patch</div>}
                    {c.risks.length > 0 && <div style={{ fontSize: 10, color: 'var(--theia-editorWarning-foreground)' }}>{c.risks.length} risk(s)</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {this.loading && <div style={{ padding: 8, textAlign: 'center', opacity: 0.5 }}>Generating...</div>}
      </div>
    );
  }

  protected renderBattleView(): React.ReactNode {
    if (!this.arenaResponse || this.arenaResponse.mode !== 'battle' || this.arenaResponse.candidates.length < 2) {
      return null;
    }
    const [a, b] = this.arenaResponse.candidates;
    return (
      <div style={battleContainerStyle}>
        <div style={{ ...battlePanelStyle, borderRight: '1px solid var(--theia-widget-border)' }}>
          <div style={battleHeaderStyle}>A: {a.model}</div>
          <pre style={battleContentStyle}>{a.text}</pre>
          <button style={voteBtnStyle} onClick={() => this.voteA()} aria-label="Vote for candidate A">Vote A (Ctrl+Shift+1)</button>
        </div>
        <div style={battlePanelStyle}>
          <div style={battleHeaderStyle}>B: {b.model}</div>
          <pre style={battleContentStyle}>{b.text}</pre>
          <button style={voteBtnStyle} onClick={() => this.voteB()} aria-label="Vote for candidate B">Vote B (Ctrl+Shift+2)</button>
        </div>
      </div>
    );
  }

  protected renderInput(): React.ReactNode {
    return (
      <div style={inputContainerStyle}>
        <textarea
          style={inputStyle}
          rows={3}
          value={this.prompt}
          onChange={e => { this.prompt = e.currentTarget.value; this.update(); }}
          onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) this.submitPrompt(); }}
          placeholder={`Enter prompt for ${this.mode} mode... (Cmd+Enter to send)`}
        />
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={primaryBtnStyle} onClick={() => this.submitPrompt()} disabled={this.loading} aria-label="Send prompt">
            {this.loading ? 'Generating...' : 'Send'}
          </button>
          {this.arenaResponse && this.arenaResponse.mode !== 'battle' && (
            <>
              <button style={secondaryBtnStyle} onClick={() => this.adoptSelected()} aria-label="Adopt selected candidate">Adopt (Ctrl+1)</button>
              <button style={secondaryBtnStyle} onClick={() => this.rejectAll()} aria-label="Reject all candidates">Reject (Ctrl+3)</button>
            </>
          )}
        </div>
      </div>
    );
  }
}

// ─── Styles ─────────────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  fontFamily: 'var(--theia-ui-font-family)',
  color: 'var(--theia-foreground)',
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '8px 12px',
  borderBottom: '1px solid var(--theia-widget-border)',
};

const controlsStyle: React.CSSProperties = {
  display: 'flex',
  gap: 12,
  padding: '8px 12px',
  borderBottom: '1px solid var(--theia-widget-border)',
  flexWrap: 'wrap',
  fontSize: 12,
};

const labelStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  fontSize: 11,
};

const selectStyle: React.CSSProperties = {
  color: 'var(--theia-dropdown-foreground)',
  backgroundColor: 'var(--theia-dropdown-background)',
  border: '1px solid var(--theia-dropdown-border)',
  borderRadius: 4,
  padding: '4px 6px',
  fontSize: 11,
};

const chatHistoryStyle: React.CSSProperties = {
  flex: 1,
  overflow: 'auto',
  padding: 12,
};

const messageStyle: React.CSSProperties = {
  padding: '8px 10px',
  border: '1px solid var(--theia-widget-border)',
  borderRadius: 6,
  marginBottom: 8,
};

const candidateCardStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 200,
  padding: 8,
  border: '1px solid',
  borderRadius: 6,
  cursor: 'pointer',
  backgroundColor: 'var(--theia-editor-background)',
};

const battleContainerStyle: React.CSSProperties = {
  display: 'flex',
  borderTop: '1px solid var(--theia-widget-border)',
  height: 300,
};

const battlePanelStyle: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  overflow: 'auto',
};

const battleHeaderStyle: React.CSSProperties = {
  padding: '6px 8px',
  fontWeight: 600,
  fontSize: 11,
  borderBottom: '1px solid var(--theia-widget-border)',
  backgroundColor: 'var(--theia-editor-background)',
};

const battleContentStyle: React.CSSProperties = {
  flex: 1,
  margin: 0,
  padding: 8,
  fontSize: 11,
  whiteSpace: 'pre-wrap',
  overflow: 'auto',
};

const voteBtnStyle: React.CSSProperties = {
  backgroundColor: 'var(--theia-button-background)',
  color: 'var(--theia-button-foreground)',
  border: 'none',
  borderRadius: 4,
  padding: '4px 8px',
  cursor: 'pointer',
  fontSize: 11,
  margin: 4,
};

const inputContainerStyle: React.CSSProperties = {
  padding: '8px 12px',
  borderTop: '1px solid var(--theia-widget-border)',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  color: 'var(--theia-input-foreground)',
  backgroundColor: 'var(--theia-input-background)',
  border: '1px solid var(--theia-input-border)',
  borderRadius: 4,
  padding: '6px 8px',
  resize: 'vertical',
  fontSize: 12,
  fontFamily: 'var(--theia-ui-font-family)',
};

const primaryBtnStyle: React.CSSProperties = {
  backgroundColor: 'var(--theia-button-background)',
  color: 'var(--theia-button-foreground)',
  border: 'none',
  borderRadius: 4,
  padding: '6px 12px',
  cursor: 'pointer',
  fontSize: 12,
};

const secondaryBtnStyle: React.CSSProperties = {
  ...primaryBtnStyle,
  backgroundColor: 'var(--theia-secondaryButton-background)',
  color: 'var(--theia-secondaryButton-foreground)',
};
