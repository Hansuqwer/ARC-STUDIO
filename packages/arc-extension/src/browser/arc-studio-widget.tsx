/**
 * ARC Studio Widget
 *
 * Single tabbed widget that replaces the 5 separate widgets.
 * Provides Chat, Runs, Workflows, and Config tabs with a status strip.
 */

import { injectable, postConstruct, inject } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { MessageService } from '@theia/core/lib/common/message-service';
import * as React from '@theia/core/shared/react';
import { ArcService, ConfigStatus, WorkflowInfo } from '../common/arc-protocol';
import { AssuranceTab, BattleTab, ChatTab, CommandCentreTab, ConfigTab, RunsTab, SwarmGraphInsightTab, WorkflowsTab } from './tabs';

type StudioTabId = 'chat' | 'runs' | 'workflows' | 'assurance' | 'swarmgraph-insight' | 'battle' | 'config' | 'command-centre';

interface ArcStudioWidgetState {
    activeTab: StudioTabId;
    workflows: WorkflowInfo[];
    isScanning: boolean;
    configStatus?: ConfigStatus;
    selectedRunId?: string | null;
}

@injectable()
export class ArcStudioWidget extends ReactWidget {

    static readonly ID = 'arc-studio-widget';
    static readonly LABEL = 'ARC Studio';

    @inject(MessageService)
    protected readonly messageService!: MessageService;

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    private state: ArcStudioWidgetState = {
        activeTab: 'chat',
        workflows: [],
        isScanning: false
    };

    @postConstruct()
    protected init(): void {
        this.id = ArcStudioWidget.ID;
        this.title.label = ArcStudioWidget.LABEL;
        this.title.caption = ArcStudioWidget.LABEL;
        this.title.closable = true;
        this.title.iconClass = 'fa fa-project-diagram';
        this.refreshConfigStatus();
        this.update();
    }

    private async refreshConfigStatus(): Promise<void> {
        try {
            const configStatus = await this.arcService.getConfigStatus();
            this.state = { ...this.state, configStatus };
        } catch {
            this.state = { ...this.state, configStatus: undefined };
        }
        this.update();
    }

    private setActiveTab(tab: StudioTabId): void {
        this.state = { ...this.state, activeTab: tab, selectedRunId: tab === 'runs' || tab === 'assurance' ? this.state.selectedRunId : null };
        this.update();
    }

    async handleScanWorkspace(): Promise<void> {
        if (this.state.isScanning) {
            return;
        }

        this.state = { ...this.state, isScanning: true };
        this.update();

        try {
            const workflows = await this.arcService.detectWorkflows();
            this.state = { ...this.state, isScanning: false, workflows };
            this.messageService.info(`Found ${workflows.length} workflow(s)`);
        } catch (error: any) {
            this.state = { ...this.state, isScanning: false };
            this.messageService.error(`Scan failed: ${error.message}`);
        }
        this.update();
    }

    protected render(): React.ReactNode {
        const { activeTab, workflows, isScanning, configStatus } = this.state;
        const runtime = configStatus?.runtime.defaultRuntime || 'unknown';
        const mode = configStatus?.mode || 'unknown';
        const workspaceTrust = configStatus?.workspace.trustLevel || 'unknown';

        const tabs: { id: StudioTabId; label: string }[] = [
            { id: 'chat', label: 'Chat' },
            { id: 'runs', label: 'Runs' },
            { id: 'workflows', label: 'Workflows' },
            { id: 'assurance', label: 'Assurance' },
            { id: 'swarmgraph-insight', label: 'SwarmGraph Insight' },
            { id: 'battle', label: 'Battle' },
            { id: 'command-centre', label: 'Command Centre' },
            { id: 'config', label: 'Config' }
        ];

        return (
            <div className='arc-studio-widget-container' role='main' aria-label='ARC Studio'>
                <div className='arc-studio-header'>
                    <h2>ARC Studio</h2>
                    <p>Agent Runtime Cockpit</p>
                </div>

                <div className='arc-studio-tabs' role='tablist'>
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            id={`arc-studio-tab-${tab.id}`}
                            role='tab'
                            aria-selected={activeTab === tab.id}
                            aria-controls={`arc-studio-panel-${tab.id}`}
                            className={`arc-studio-tab ${activeTab === tab.id ? 'arc-studio-tab--active' : ''}`}
                            onClick={() => this.setActiveTab(tab.id)}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                <div className='arc-studio-content'>
                    <div
                        id={`arc-studio-panel-chat`}
                        role='tabpanel'
                        aria-labelledby='arc-studio-tab-chat'
                        hidden={activeTab !== 'chat'}
                    >
                        {activeTab === 'chat' && (
                            <ChatTab
                                arcService={this.arcService}
                                onNavigateToRuns={(runId) => {
                                    this.state = { ...this.state, selectedRunId: runId ?? null };
                                    this.setActiveTab('runs');
                                }}
                            />
                        )}
                    </div>
                    <div
                        id={`arc-studio-panel-runs`}
                        role='tabpanel'
                        aria-labelledby='arc-studio-tab-runs'
                        hidden={activeTab !== 'runs'}
                    >
                        {activeTab === 'runs' && (
                            <RunsTab
                                arcService={this.arcService}
                                initialRunId={this.state.selectedRunId}
                            />
                        )}
                    </div>
                    <div
                        id={`arc-studio-panel-workflows`}
                        role='tabpanel'
                        aria-labelledby='arc-studio-tab-workflows'
                        hidden={activeTab !== 'workflows'}
                    >
                        {activeTab === 'workflows' && (
                            <WorkflowsTab
                                workflows={workflows}
                                isScanning={isScanning}
                                onScanWorkspace={() => this.handleScanWorkspace()}
                            />
                        )}
                    </div>
                    <div
                        id={`arc-studio-panel-assurance`}
                        role='tabpanel'
                        aria-labelledby='arc-studio-tab-assurance'
                        hidden={activeTab !== 'assurance'}
                    >
                        {activeTab === 'assurance' && (
                            <AssuranceTab
                                arcService={this.arcService}
                                initialRunId={this.state.selectedRunId}
                            />
                        )}
                    </div>
                    <div
                        id={`arc-studio-panel-battle`}
                        role='tabpanel'
                        aria-labelledby='arc-studio-tab-battle'
                        hidden={activeTab !== 'battle'}
                    >
                        {activeTab === 'battle' && <BattleTab arcService={this.arcService} />}
                    </div>
                    <div
                        id={`arc-studio-panel-command-centre`}
                        role='tabpanel'
                        aria-labelledby='arc-studio-tab-command-centre'
                        hidden={activeTab !== 'command-centre'}
                    >
                        {activeTab === 'command-centre' && <CommandCentreTab arcService={this.arcService} />}
                    </div>
                    <div
                        id={`arc-studio-panel-config`}
                        role='tabpanel'
                        aria-labelledby='arc-studio-tab-config'
                        hidden={activeTab !== 'config'}
                    >
                        {activeTab === 'config' && <ConfigTab arcService={this.arcService} />}
                    </div>
                    <div
                        id={`arc-studio-panel-swarmgraph-insight`}
                        role='tabpanel'
                        aria-labelledby='arc-studio-tab-swarmgraph-insight'
                        hidden={activeTab !== 'swarmgraph-insight'}
                    >
                        {activeTab === 'swarmgraph-insight' && <SwarmGraphInsightTab arcService={this.arcService} />}
                    </div>
                </div>

                <div className='arc-studio-status' role='status' aria-live='polite'>
                    <span className='arc-studio-status__segment'>Runtime: {runtime}</span>
                    <span className='arc-studio-status__segment'>Model: unset</span>
                    <span className='arc-studio-status__segment'>Mode: {mode}</span>
                    <span className='arc-studio-status__segment'>Workspace: {workspaceTrust}</span>
                </div>
            </div>
        );
    }
}
