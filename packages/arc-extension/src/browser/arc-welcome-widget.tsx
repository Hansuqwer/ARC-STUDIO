import * as React from 'react';
import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { CommandService } from '@theia/core/lib/common/command';
import { WorkspaceService } from '@theia/workspace/lib/browser/workspace-service';

@injectable()
export class ArcWelcomeWidget extends ReactWidget {
    static readonly ID = 'arc:welcome';
    static readonly LABEL = 'Welcome to ARC Studio';

    @inject(CommandService)
    protected readonly commandService!: CommandService;

    @inject(WorkspaceService)
    protected readonly workspaceService!: WorkspaceService;

    @postConstruct()
    protected init(): void {
        this.id = ArcWelcomeWidget.ID;
        this.title.label = ArcWelcomeWidget.LABEL;
        this.title.caption = 'Welcome to ARC Studio';
        this.title.closable = true;
        this.title.iconClass = 'codicon codicon-star';
    }

    protected render(): React.ReactNode {
        const hasWorkspace = this.workspaceService.tryGetRoots().length > 0;
        return (
            <div style={styles.container} data-testid="arc-welcome-widget">
                <div style={styles.logo}>ARC</div>
                <h1 style={styles.title}>Welcome to ARC Studio</h1>
                <p style={styles.subtitle}>Inspect, run, trace, audit, and compare agent workflows.</p>
                <div style={styles.steps}>
                    {this.renderStep('1', 'Open a workspace', 'Use a folder containing an agent project.')}
                    {this.renderStep('2', 'Check runtime readiness', 'Open adapters or config to inspect available runtimes.')}
                    {this.renderStep('3', 'Run your first agent', 'Open ARC Studio and launch from the Chat tab.')}
                </div>
                <div style={styles.actions}>
                    {!hasWorkspace && <button style={styles.primaryBtn} onClick={() => this.commandService.executeCommand('workspace:open')}>Open Workspace</button>}
                    <button style={styles.secondaryBtn} onClick={() => this.commandService.executeCommand('arc-studio:open')}>Open ARC Studio</button>
                    <button style={styles.secondaryBtn} onClick={() => this.close()}>Get Started</button>
                </div>
            </div>
        );
    }

    protected renderStep(number: string, title: string, body: string): React.ReactNode {
        return (
            <div style={styles.step}>
                <div style={styles.stepNumber}>{number}</div>
                <div style={styles.stepContent}><strong>{title}</strong><p>{body}</p></div>
            </div>
        );
    }
}

const styles: Record<string, React.CSSProperties> = {
    container: { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 24px', height: '100%', overflow: 'auto', fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)', textAlign: 'center' },
    logo: { fontSize: '18px', fontWeight: 700, color: 'var(--theia-textLink-foreground)', marginBottom: '16px', letterSpacing: '0.18em' },
    title: { fontSize: '22px', fontWeight: 700, margin: '0 0 8px 0' },
    subtitle: { fontSize: '14px', color: 'var(--theia-descriptionForeground)', margin: '0 0 32px 0', maxWidth: '440px' },
    steps: { display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '480px', width: '100%', marginBottom: '32px' },
    step: { display: 'flex', gap: '14px', alignItems: 'flex-start', textAlign: 'left' },
    stepNumber: { width: '28px', height: '28px', borderRadius: '50%', backgroundColor: 'var(--theia-button-background)', color: 'var(--theia-button-foreground)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 700, flexShrink: 0 },
    stepContent: { fontSize: '13px', lineHeight: 1.4 },
    actions: { display: 'flex', gap: '10px', flexWrap: 'wrap', justifyContent: 'center' },
    primaryBtn: { padding: '8px 18px', backgroundColor: 'var(--theia-button-background)', color: 'var(--theia-button-foreground)', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: 600 },
    secondaryBtn: { padding: '8px 18px', backgroundColor: 'var(--theia-secondaryButton-background)', color: 'var(--theia-secondaryButton-foreground)', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' },
};
