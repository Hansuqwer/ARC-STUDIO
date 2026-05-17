/**
 * ARC Welcome Widget — onboarding screen shown on first launch.
 *
 * Guides new users through getting started with ARC Studio.
 * Source: https://theia-ide.org/docs/widgets/#react-based-widget
 */

import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { CommandService } from '@theia/core/lib/common/command';
import { WorkspaceService } from '@theia/workspace/lib/browser/workspace-service';

@injectable()
export class ArcWelcomeWidget extends ReactWidget {
  static readonly ID = 'arc:welcome';
  static readonly LABEL = 'Welcome to ARC Studio';

  @inject(CommandService)
  protected readonly commandService: CommandService;

  @inject(WorkspaceService)
  protected readonly workspaceService: WorkspaceService;

  @postConstruct()
  protected init(): void {
    this.id = ArcWelcomeWidget.ID;
    this.title.label = ArcWelcomeWidget.LABEL;
    this.title.caption = 'Welcome to ARC Studio';
    this.title.closable = true;
    this.title.iconClass = 'codicon codicon-star';
    this.node.classList.add('arc-welcome-widget');
  }

  protected render(): React.ReactNode {
    const hasWorkspace = this.workspaceService.tryGetRoots().length > 0;

    return (
      <div style={styles.container}>
        <div style={styles.logo}>⬡</div>
        <h1 style={styles.title}>Welcome to ARC Studio</h1>
        <p style={styles.subtitle}>
          Agent Runtime Cockpit — inspect, run, and compare AI agents.
        </p>

        <div style={styles.steps}>
          <div style={styles.step}>
            <div style={styles.stepNumber}>1</div>
            <div style={styles.stepContent}>
              <strong>Open a workspace</strong>
              <p>Open a folder containing an agent project (SwarmGraph, LangGraph, CrewAI, OpenAI Agents).</p>
            </div>
          </div>
          <div style={styles.step}>
            <div style={styles.stepNumber}>2</div>
            <div style={styles.stepContent}>
              <strong>Check runtime readiness</strong>
              <p>Runtimes are detected automatically. Look for ✓ icons in the sidebar.</p>
            </div>
          </div>
          <div style={styles.step}>
            <div style={styles.stepNumber}>3</div>
            <div style={styles.stepContent}>
              <strong>Run your first agent</strong>
              <p>Click "Run Agent" in the sidebar or press <kbd>Cmd+Shift+R</kbd>.</p>
            </div>
          </div>
        </div>

        <div style={styles.actions}>
          {!hasWorkspace && (
            <button style={styles.primaryBtn} onClick={() => this.commandService.executeCommand('workspace:open')}>
              Open Workspace
            </button>
          )}
          <button style={styles.secondaryBtn} onClick={() => this.commandService.executeCommand('arc:open-chat')}>
            Run Agent
          </button>
          <button style={styles.secondaryBtn} onClick={() => this.closeWelcome()}>
            Get Started
          </button>
        </div>
      </div>
    );
  }

  protected async closeWelcome(): Promise<void> {
    this.close();
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '40px 24px',
    height: '100%',
    overflow: 'auto',
    fontFamily: 'var(--theia-ui-font-family)',
    color: 'var(--theia-foreground)',
    textAlign: 'center',
  },
  logo: {
    fontSize: '48px',
    color: 'var(--theia-textLink-foreground)',
    marginBottom: '16px',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
    margin: '0 0 8px 0',
  },
  subtitle: {
    fontSize: '14px',
    color: 'var(--theia-descriptionForeground)',
    margin: '0 0 32px 0',
    maxWidth: '400px',
  },
  steps: {
    display: 'flex',
    flexDirection: 'column' as any,
    gap: '16px',
    maxWidth: '440px',
    width: '100%',
    marginBottom: '32px',
  },
  step: {
    display: 'flex',
    gap: '14px',
    alignItems: 'flex-start',
    textAlign: 'left' as any,
  },
  stepNumber: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    backgroundColor: 'var(--theia-button-background)',
    color: 'var(--theia-button-foreground)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '13px',
    fontWeight: 700,
    flexShrink: 0,
  },
  stepContent: {
    fontSize: '13px',
    lineHeight: 1.4,
  },
  actions: {
    display: 'flex',
    gap: '10px',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  primaryBtn: {
    padding: '8px 18px',
    backgroundColor: 'var(--theia-button-background)',
    color: 'var(--theia-button-foreground)',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
  },
  secondaryBtn: {
    padding: '8px 18px',
    backgroundColor: 'var(--theia-secondaryButton-background)',
    color: 'var(--theia-secondaryButton-foreground)',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
  },
};
