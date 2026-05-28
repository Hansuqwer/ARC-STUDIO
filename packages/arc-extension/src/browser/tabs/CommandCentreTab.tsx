/**
 * Command Centre Tab (Phase 76)
 *
 * Aggregates active/past sessions, runs, tasks, approvals, sandbox state,
 * provider health, and workspace context from existing producers.
 * Missing producers render explicit empty/degraded states — no fabricated data.
 */

import * as React from '@theia/core/shared/react';
import {
    ArcProfileInfo,
    ArcService,
    ChatSessionSummary,
    CiCheckStatus,
    ConfigStatus,
    HitlPromptInfo,
    IsolationProviderInfo,
    McpWorkbenchStatus,
    ProviderDiagnosticsInfo,
    TestbenchDetection,
    TraceFile,
    WorkspaceInventory,
} from '../../common/arc-protocol';

export interface CommandCentreTabProps {
    arcService: ArcService;
}

interface CommandCentreState {
    sessions: ChatSessionSummary[];
    sessionsLoaded: boolean;
    sessionsError: string | null;
    runs: TraceFile[];
    runsLoaded: boolean;
    runsError: string | null;
    hitlPrompts: HitlPromptInfo[];
    hitlLoaded: boolean;
    hitlError: string | null;
    isolationProviders: IsolationProviderInfo[];
    isolationLoaded: boolean;
    isolationError: string | null;
    profiles: ArcProfileInfo[];
    profilesLoaded: boolean;
    profilesError: string | null;
    providerDiagnostics?: ProviderDiagnosticsInfo;
    providerLoaded: boolean;
    providerError: string | null;
    workspaceStatus?: { frontendPath: string; backendPath: string; source: string };
    configStatus?: ConfigStatus;
    workspaceLoaded: boolean;
    workspaceError: string | null;
    mcpStatus?: McpWorkbenchStatus;
    mcpLoaded: boolean;
    mcpError: string | null;
    workspaceInventory?: WorkspaceInventory;
    invLoaded: boolean;
    invError: string | null;
    testbench?: TestbenchDetection;
    testbenchLoaded: boolean;
    testbenchError: string | null;
    ciStatus?: CiCheckStatus;
    ciLoaded: boolean;
    ciError: string | null;
}

export class CommandCentreTab extends React.Component<CommandCentreTabProps, CommandCentreState> {
    constructor(props: CommandCentreTabProps) {
        super(props);
        this.state = {
            sessions: [],
            sessionsLoaded: false,
            sessionsError: null,
            runs: [],
            runsLoaded: false,
            runsError: null,
            hitlPrompts: [],
            hitlLoaded: false,
            hitlError: null,
            isolationProviders: [],
            isolationLoaded: false,
            isolationError: null,
            profiles: [],
            profilesLoaded: false,
            profilesError: null,
            providerLoaded: false,
            providerError: null,
            workspaceLoaded: false,
            workspaceError: null,
            mcpLoaded: false,
            mcpError: null,
            invLoaded: false,
            invError: null,
            testbenchLoaded: false,
            testbenchError: null,
            ciLoaded: false,
            ciError: null,
        };
    }

    componentDidMount(): void {
        this.loadAll();
    }

    private async loadAll(): Promise<void> {
        await Promise.all([
            this.loadSessions(),
            this.loadRuns(),
            this.loadHitl(),
            this.loadIsolation(),
            this.loadProfiles(),
            this.loadProviderDiagnostics(),
            this.loadWorkspaceContext(),
            this.loadMcpStatus(),
            this.loadWorkspaceInventory(),
            this.loadTestbench(),
            this.loadCiStatus(),
        ]);
    }

    private async loadSessions(): Promise<void> {
        try {
            const sessions = await this.props.arcService.listChatSessions();
            this.setState({ sessions, sessionsLoaded: true });
        } catch (e: any) {
            this.setState({ sessionsError: e.message || 'Failed to load sessions', sessionsLoaded: true });
        }
    }

    private async loadRuns(): Promise<void> {
        try {
            const runs = await this.props.arcService.getTraces();
            this.setState({ runs, runsLoaded: true });
        } catch (e: any) {
            this.setState({ runsError: e.message || 'Failed to load runs', runsLoaded: true });
        }
    }

    private async loadHitl(): Promise<void> {
        try {
            const hitlPrompts = await this.props.arcService.listPendingHitlPrompts();
            this.setState({ hitlPrompts, hitlLoaded: true });
        } catch (e: any) {
            this.setState({ hitlError: e.message || 'Failed to load HITL prompts', hitlLoaded: true });
        }
    }

    private async loadIsolation(): Promise<void> {
        try {
            const isolationProviders = await this.props.arcService.listIsolationProviders();
            this.setState({ isolationProviders, isolationLoaded: true });
        } catch (e: any) {
            this.setState({ isolationError: e.message || 'Failed to load isolation providers', isolationLoaded: true });
        }
    }

    private async loadProfiles(): Promise<void> {
        try {
            const profiles = await this.props.arcService.listProfiles();
            this.setState({ profiles, profilesLoaded: true });
        } catch (e: any) {
            this.setState({ profilesError: e.message || 'Failed to load profiles', profilesLoaded: true });
        }
    }

    private async loadProviderDiagnostics(): Promise<void> {
        try {
            const providerDiagnostics = await this.props.arcService.getProviderDiagnostics();
            this.setState({ providerDiagnostics, providerLoaded: true });
        } catch (e: any) {
            this.setState({ providerError: e.message || 'Failed to load provider diagnostics', providerLoaded: true });
        }
    }

    private async loadMcpStatus(): Promise<void> {
        try {
            const mcpStatus = await this.props.arcService.getMcpWorkbenchStatus();
            this.setState({ mcpStatus, mcpLoaded: true });
        } catch (e: any) {
            this.setState({ mcpError: e.message || 'Failed to load MCP status', mcpLoaded: true });
        }
    }

    private async loadWorkspaceInventory(): Promise<void> {
        try {
            const workspaceInventory = await this.props.arcService.getWorkspaceInventory({ maxEntries: 100 });
            this.setState({ workspaceInventory, invLoaded: true });
        } catch (e: any) {
            this.setState({ invError: e.message || 'Failed to load workspace inventory', invLoaded: true });
        }
    }

    private async loadTestbench(): Promise<void> {
        try {
            const testbench = await this.props.arcService.detectTestbench();
            this.setState({ testbench, testbenchLoaded: true });
        } catch (e: any) {
            this.setState({ testbenchError: e.message || 'Failed to detect testbench', testbenchLoaded: true });
        }
    }

    private async loadCiStatus(): Promise<void> {
        try {
            const ciStatus = await this.props.arcService.getCiCheckStatus();
            this.setState({ ciStatus, ciLoaded: true });
        } catch (e: any) {
            this.setState({ ciError: e.message || 'Failed to load CI status', ciLoaded: true });
        }
    }

    private async loadWorkspaceContext(): Promise<void> {
        try {
            const [workspaceStatus, configStatus] = await Promise.all([
                this.props.arcService.getWorkspaceStatus(),
                this.props.arcService.getConfigStatus(),
            ]);
            this.setState({ workspaceStatus, configStatus, workspaceLoaded: true });
        } catch (e: any) {
            this.setState({ workspaceError: e.message || 'Failed to load workspace context', workspaceLoaded: true });
        }
    }

    render(): React.ReactNode {
        const {
            sessions, sessionsLoaded, sessionsError,
            runs, runsLoaded, runsError,
            hitlPrompts, hitlLoaded, hitlError,
            isolationProviders, isolationLoaded, isolationError,
            profiles, profilesLoaded, profilesError,
            providerDiagnostics, providerLoaded, providerError,
            workspaceStatus, configStatus, workspaceLoaded, workspaceError,
            mcpStatus, mcpLoaded, mcpError,
            workspaceInventory, invLoaded, invError,
            testbench, testbenchLoaded, testbenchError,
            ciStatus, ciLoaded, ciError,
        } = this.state;

        const providerCount = providerDiagnostics?.providers?.length ?? 0;
        const providerWarnings = providerDiagnostics?.warnings ?? [];
        const localAttention = hitlPrompts.length > 0 || providerWarnings.length > 0 ? 'attention' : 'none detected';

        return (
            <div className='arc-command-centre' role='region' aria-label='Agent Command Centre'>
                <h3>Agent Command Centre</h3>
                <p className='arc-command-centre__subtitle'>
                    Supervisory view of active sessions, runs, approvals, and system state.
                </p>

                <div className='arc-command-centre__grid'>
                    {/* Sessions Panel */}
                    <section className='arc-command-centre__panel' aria-label='Sessions'>
                        <h4>Sessions</h4>
                        {!sessionsLoaded && <p className='arc-command-centre__loading'>Loading sessions...</p>}
                        {sessionsLoaded && sessionsError && (
                            <p className='arc-command-centre__error'>Error: {sessionsError}</p>
                        )}
                        {sessionsLoaded && !sessionsError && sessions.length === 0 && (
                            <p className='arc-command-centre__empty'>No active sessions.</p>
                        )}
                        {sessionsLoaded && !sessionsError && sessions.length > 0 && (
                            <ul className='arc-command-centre__list'>
                                {sessions.map((s, i) => (
                                    <li key={s.id || i}>
                                        <strong>{s.id}</strong>
                                        {s.mode && <span className='arc-command-centre__badge'>{s.mode}</span>}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>

                    {/* Runs Panel */}
                    <section className='arc-command-centre__panel' aria-label='Runs'>
                        <h4>Runs</h4>
                        {!runsLoaded && <p className='arc-command-centre__loading'>Loading runs...</p>}
                        {runsLoaded && runsError && (
                            <p className='arc-command-centre__error'>Error: {runsError}</p>
                        )}
                        {runsLoaded && !runsError && runs.length === 0 && (
                            <p className='arc-command-centre__empty'>No runs recorded.</p>
                        )}
                        {runsLoaded && !runsError && runs.length > 0 && (
                            <ul className='arc-command-centre__list'>
                                {runs.slice(0, 10).map((r, i) => (
                                    <li key={r.id || i}>
                                        <strong>{r.id}</strong>
                                        {r.status && <span className='arc-command-centre__badge'>{r.status}</span>}
                                    </li>
                                ))}
                                {runs.length > 10 && (
                                    <li className='arc-command-centre__more'>...and {runs.length - 10} more</li>
                                )}
                            </ul>
                        )}
                    </section>

                    {/* HITL Approvals Panel */}
                    <section className='arc-command-centre__panel' aria-label='Approvals'>
                        <h4>Pending Approvals</h4>
                        {!hitlLoaded && <p className='arc-command-centre__loading'>Loading approvals...</p>}
                        {hitlLoaded && hitlError && (
                            <p className='arc-command-centre__error'>Error: {hitlError}</p>
                        )}
                        {hitlLoaded && !hitlError && hitlPrompts.length === 0 && (
                            <p className='arc-command-centre__empty'>No pending approvals.</p>
                        )}
                        {hitlLoaded && !hitlError && hitlPrompts.length > 0 && (
                            <ul className='arc-command-centre__list'>
                                {hitlPrompts.map((p, i) => (
                                    <li key={p.promptId || i}>
                                        <strong>{p.promptId}</strong>
                                        <span className='arc-command-centre__badge arc-command-centre__badge--warning'>
                                            Pending
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>

                    {/* Sandbox/Isolation Panel */}
                    <section className='arc-command-centre__panel' aria-label='Sandbox'>
                        <h4>Sandbox &amp; Isolation</h4>
                        {!isolationLoaded && <p className='arc-command-centre__loading'>Loading isolation...</p>}
                        {isolationLoaded && isolationError && (
                            <p className='arc-command-centre__error'>Error: {isolationError}</p>
                        )}
                        {isolationLoaded && !isolationError && isolationProviders.length === 0 && (
                            <p className='arc-command-centre__empty'>No isolation providers available.</p>
                        )}
                        {isolationLoaded && !isolationError && isolationProviders.length > 0 && (
                            <ul className='arc-command-centre__list'>
                                {isolationProviders.map((p, i) => (
                                    <li key={p.id || i}>
                                        <strong>{p.id}</strong>
                                        <span className={`arc-command-centre__badge ${p.available ? 'arc-command-centre__badge--ok' : 'arc-command-centre__badge--warning'}`}>
                                            {p.available ? 'ready' : 'unavailable'}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>

                    {/* Profiles Panel */}
                    <section className='arc-command-centre__panel' aria-label='Profiles'>
                        <h4>Run Profiles</h4>
                        {!profilesLoaded && <p className='arc-command-centre__loading'>Loading profiles...</p>}
                        {profilesLoaded && profilesError && (
                            <p className='arc-command-centre__error'>Error: {profilesError}</p>
                        )}
                        {profilesLoaded && !profilesError && profiles.length === 0 && (
                            <p className='arc-command-centre__empty'>No profiles configured.</p>
                        )}
                        {profilesLoaded && !profilesError && profiles.length > 0 && (
                            <ul className='arc-command-centre__list'>
                                {profiles.map((p, i) => (
                                    <li key={p.id || i}>
                                        <strong>{p.name || p.id}</strong>
                                        {p.mode && <span className='arc-command-centre__badge'>{p.mode}</span>}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>

                    {/* Provider Health Panel */}
                    <section className='arc-command-centre__panel' aria-label='Provider Health'>
                        <h4>Provider Health</h4>
                        {!providerLoaded && <p className='arc-command-centre__loading'>Loading provider diagnostics...</p>}
                        {providerLoaded && providerError && (
                            <p className='arc-command-centre__error'>Error: {providerError}</p>
                        )}
                        {providerLoaded && !providerError && providerCount === 0 && (
                            <p className='arc-command-centre__empty'>No provider diagnostics available.</p>
                        )}
                        {providerLoaded && !providerError && providerCount > 0 && (
                            <p>{providerCount} provider diagnostic record(s) available.</p>
                        )}
                        {providerWarnings.length > 0 && (
                            <ul className='arc-command-centre__list'>
                                {providerWarnings.map((warning, i) => <li key={i}>{warning}</li>)}
                            </ul>
                        )}
                    </section>

                    {/* Workspace / Risk Panel */}
                    <section className='arc-command-centre__panel' aria-label='Workspace Risk'>
                        <h4>Workspace &amp; Risk</h4>
                        {!workspaceLoaded && <p className='arc-command-centre__loading'>Loading workspace context...</p>}
                        {workspaceLoaded && workspaceError && (
                            <p className='arc-command-centre__error'>Error: {workspaceError}</p>
                        )}
                        {workspaceLoaded && !workspaceError && workspaceStatus && configStatus && (
                            <ul className='arc-command-centre__list'>
                                <li><strong>Root:</strong> {workspaceStatus.backendPath}</li>
                                <li><strong>Trust:</strong> {configStatus.workspace.trustLevel}</li>
                                <li><strong>Local attention:</strong> {localAttention}</li>
                            </ul>
                        )}
                        {workspaceLoaded && !workspaceError && (!workspaceStatus || !configStatus) && (
                            <p className='arc-command-centre__empty'>Workspace context unavailable.</p>
                        )}
                    </section>

                    {/* Tasks Panel */}
                    <section className='arc-command-centre__panel' aria-label='Tasks'>
                        <h4>Tasks</h4>
                        <p className='arc-command-centre__empty'>Task producer not exposed; testbench detection available via the Testbench panel.</p>
                    </section>

                    {/* MCP Workbench Status Panel */}
                    <section className='arc-command-centre__panel' aria-label='MCP'>
                        <h4>MCP Workbench</h4>
                        {!mcpLoaded && <p className='arc-command-centre__loading'>Loading MCP status...</p>}
                        {mcpLoaded && mcpError && (
                            <p className='arc-command-centre__error'>Error: {mcpError}</p>
                        )}
                        {mcpLoaded && !mcpError && mcpStatus && (
                            <ul className='arc-command-centre__list'>
                                <li><strong>Server creatable:</strong> {mcpStatus.serverCreatable ? 'Yes' : 'No'}</li>
                                {mcpStatus.serverBlocker && <li><strong>Blocker:</strong> {mcpStatus.serverBlocker}</li>}
                                <li><strong>Tools:</strong> {mcpStatus.tools.length}</li>
                                <li><strong>Resources:</strong> {mcpStatus.resources.length}</li>
                                <li><strong>Trust:</strong> {mcpStatus.trust.level}</li>
                                <li><strong>Diagnostic:</strong> {mcpStatus.diagnostic}</li>
                            </ul>
                        )}
                        {mcpLoaded && !mcpError && !mcpStatus && (
                            <p className='arc-command-centre__empty'>MCP status unavailable.</p>
                        )}
                    </section>

                    {/* Workspace Inventory Panel */}
                    <section className='arc-command-centre__panel' aria-label='Workspace Inventory'>
                        <h4>Workspace Inventory</h4>
                        {!invLoaded && <p className='arc-command-centre__loading'>Loading inventory...</p>}
                        {invLoaded && invError && (
                            <p className='arc-command-centre__error'>Error: {invError}</p>
                        )}
                        {invLoaded && !invError && workspaceInventory && (
                            <ul className='arc-command-centre__list'>
                                <li><strong>Files:</strong> {workspaceInventory.files.count} ({workspaceInventory.files.totalSize} bytes)</li>
                                <li><strong>Git:</strong> {workspaceInventory.git.branch || 'unknown'} {workspaceInventory.git.dirty ? '(dirty)' : ''}</li>
                                <li><strong>Traces:</strong> {workspaceInventory.traces.count}</li>
                                <li><strong>MCP resources:</strong> {workspaceInventory.mcpResources.length}</li>
                                {workspaceInventory.symbols && <li><strong>Symbols:</strong> {workspaceInventory.symbols.count}</li>}
                            </ul>
                        )}
                        {invLoaded && !invError && !workspaceInventory && (
                            <p className='arc-command-centre__empty'>Workspace inventory unavailable.</p>
                        )}
                    </section>

                    {/* Testbench Panel */}
                    <section className='arc-command-centre__panel' aria-label='Testbench'>
                        <h4>Testbench</h4>
                        {!testbenchLoaded && <p className='arc-command-centre__loading'>Loading testbench...</p>}
                        {testbenchLoaded && testbenchError && (
                            <p className='arc-command-centre__error'>Error: {testbenchError}</p>
                        )}
                        {testbenchLoaded && !testbenchError && testbench && (
                            <>
                                <p><strong>Detected commands:</strong> {testbench.count}</p>
                                {testbench.detected.length > 0 && (
                                    <ul className='arc-command-centre__list'>
                                        {testbench.detected.slice(0, 5).map((d, i) => (
                                            <li key={i}>{d.command || d.runner || 'unknown'} ({d.source})</li>
                                        ))}
                                        {testbench.detected.length > 5 && (
                                            <li className='arc-command-centre__more'>...and {testbench.detected.length - 5} more</li>
                                        )}
                                    </ul>
                                )}
                            </>
                        )}
                        {testbenchLoaded && !testbenchError && (!testbench || testbench.count === 0) && (
                            <p className='arc-command-centre__empty'>No test commands detected.</p>
                        )}
                    </section>

                    {/* CI Guardrails Panel */}
                    <section className='arc-command-centre__panel' aria-label='CI Guardrails'>
                        <h4>CI Guardrails</h4>
                        {!ciLoaded && <p className='arc-command-centre__loading'>Loading CI status...</p>}
                        {ciLoaded && ciError && (
                            <p className='arc-command-centre__error'>Error: {ciError}</p>
                        )}
                        {ciLoaded && !ciError && ciStatus && (
                            <ul className='arc-command-centre__list'>
                                <li><strong>Overall:</strong> {ciStatus.overall}</li>
                                <li><strong>Private:</strong> {ciStatus.private ? 'Yes' : 'No'}</li>
                                <li><strong>Checks:</strong> {Object.keys(ciStatus.checks).length}</li>
                                {ciStatus.checkedAt && <li><strong>Checked at:</strong> {ciStatus.checkedAt}</li>}
                            </ul>
                        )}
                        {ciLoaded && !ciError && !ciStatus && (
                            <p className='arc-command-centre__empty'>CI status unavailable.</p>
                        )}
                    </section>
                </div>
            </div>
        );
    }
}
