/**
 * ARC Workflow Graph Widget — Wave 5: runtime/graph linkage foundation.
 *
 * Stable IDs, evidence/link refs, read-only menu reservation,
 * and minimal graph/chat selection contract.
 */
import * as React from 'react';
import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import {
    ArcService,
    WorkflowInfo,
    GraphNodeData,
    GraphEdgeData,
    CrossLinkState,
    EvidenceRef,
    GraphNodeSelectionEvent,
    DegradationManifest,
} from '../common/arc-protocol';

interface WorkflowNode {
    id: string;
    label: string;
    type?: string;
    messageId?: string;
    toolCallId?: string;
    decisionId?: string;
    approvalId?: string;
    evidenceRefs?: EvidenceRef[];
    eventCount?: number;
    state?: 'idle' | 'running' | 'waiting' | 'done' | 'failed';
    runtime?: string;
    lastEventAt?: string;
    durationMs?: number;
}

interface WorkflowEdge {
    id: string;
    from_node: string;
    to_node: string;
    label?: string;
    conditional?: boolean;
    messageVolume?: number;
    active?: boolean;
}

type GraphWorkflowInfo = WorkflowInfo & {
    id?: string;
    runtime?: string;
    nodes?: WorkflowNode[];
    edges?: WorkflowEdge[];
    metadata?: Record<string, unknown>;
};

type OnNodeSelect = (event: GraphNodeSelectionEvent) => void;

@injectable()
export class ArcWorkflowGraphWidget extends ReactWidget {
    static readonly ID = 'arc:workflow-graph';
    static readonly LABEL = 'ARC Workflow Graph';

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    protected workflows: GraphWorkflowInfo[] = [];
    protected selectedWorkflow: GraphWorkflowInfo | null = null;
    protected loading = false;
    protected error = '';

    protected crossLinkState: CrossLinkState = {
        selectedNodeId: null,
        highlightedMessageIds: [],
        highlightedEvidenceIds: [],
        highlightedToolCallIds: [],
        highlightedRunIds: [],
    };

    protected onNodeSelectCallback: OnNodeSelect | null = null;

    protected degradationManifest: DegradationManifest = {
        totalEvents: 0,
        missingNodeIds: 0,
        missingMessageIds: 0,
        missingToolCallIds: 0,
        missingEvidenceRefs: 0,
        isDegraded: false,
        crossLinkingAvailable: true,
    };

    protected selectedNodeForMenu: WorkflowNode | null = null;
    protected showNodeMenu = false;

    @postConstruct()
    protected init(): void {
        this.id = ArcWorkflowGraphWidget.ID;
        this.title.label = ArcWorkflowGraphWidget.LABEL;
        this.title.closable = true;
        this.title.caption = 'ARC Workflow Graph';
        this.loadWorkflows();
    }

    setOnNodeSelect(callback: OnNodeSelect | null): void {
        this.onNodeSelectCallback = callback;
    }

    updateCrossLinkState(state: Partial<CrossLinkState>): void {
        this.crossLinkState = { ...this.crossLinkState, ...state };
        this.update();
    }

    updateDegradationManifest(manifest: Partial<DegradationManifest>): void {
        this.degradationManifest = { ...this.degradationManifest, ...manifest };
        this.update();
    }

    protected async loadWorkflows(): Promise<void> {
        this.loading = true;
        this.error = '';
        this.update();
        try {
            this.workflows = (await this.arcService.detectWorkflows()) as GraphWorkflowInfo[];
            this.selectedWorkflow = this.workflows[0] ?? null;
        } catch (error) {
            this.error = error instanceof Error ? error.message : String(error);
        } finally {
            this.loading = false;
            this.update();
        }
    }

    protected handleNodeSelect(node: WorkflowNode): void {
        const nodeId = node.id;
        const evidenceIds = (node.evidenceRefs ?? []).map(ref => ref.evidence_id);
        const toolCallIds = node.toolCallId ? [node.toolCallId] : [];
        const messageIds = node.messageId ? [node.messageId] : [];

        this.crossLinkState = {
            ...this.crossLinkState,
            selectedNodeId: nodeId,
            highlightedMessageIds: messageIds,
            highlightedEvidenceIds: evidenceIds,
            highlightedToolCallIds: toolCallIds,
        };

        if (this.onNodeSelectCallback) {
            const nodeData: GraphNodeData = {
                id: nodeId,
                label: node.label,
                type: (node.type as GraphNodeData['type']) ?? 'agent',
                runtime: (node.runtime ?? this.selectedWorkflow?.type ?? 'swarmgraph') as GraphNodeData['runtime'],
                state: node.state ?? 'idle',
                messageId: node.messageId,
                toolCallId: node.toolCallId,
                decisionId: node.decisionId,
                approvalId: node.approvalId,
                evidenceRefs: node.evidenceRefs,
                eventCount: node.eventCount,
            };

            this.onNodeSelectCallback({
                nodeId,
                nodeData,
                linkedMessageIds: messageIds,
                linkedEvidenceIds: evidenceIds,
                linkedToolCallIds: toolCallIds,
            });
        }

        this.update();
    }

    protected handleNodeContextMenu(node: WorkflowNode, event: React.MouseEvent): void {
        event.preventDefault();
        this.selectedNodeForMenu = node;
        this.showNodeMenu = true;
        this.update();
    }

    protected closeNodeMenu(): void {
        this.showNodeMenu = false;
        this.selectedNodeForMenu = null;
        this.update();
    }

    protected handleCopyNodeId(): void {
        if (this.selectedNodeForMenu) {
            navigator.clipboard?.writeText(this.selectedNodeForMenu.id);
        }
        this.closeNodeMenu();
    }

    protected handleShowEvidence(): void {
        this.closeNodeMenu();
    }

    protected handleOpenReceipt(): void {
        this.closeNodeMenu();
    }

    protected handleExplainEdge(): void {
        this.closeNodeMenu();
    }

    protected render(): React.ReactNode {
        if (this.loading) {
            return <div style={centerStyle}>Loading workflows...</div>;
        }
        if (this.error) {
            return <div style={centerStyle}>Workflow detection failed: {this.error}</div>;
        }
        return (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: 'var(--theia-ui-font-family)' }}>
                {this.renderToolbar()}
                {this.selectedWorkflow ? this.renderGraph(this.selectedWorkflow) : this.renderEmpty()}
            </div>
        );
    }

    protected renderToolbar(): React.ReactNode {
        return (
            <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--theia-widget-border)', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontWeight: 600 }}>Workflow:</span>
                <select
                    style={{ flex: 1, padding: '4px', backgroundColor: 'var(--theia-input-background)', color: 'var(--theia-input-foreground)', border: '1px solid var(--theia-input-border)', borderRadius: '4px' }}
                    value={this.workflowKey(this.selectedWorkflow)}
                    onChange={event => {
                        this.selectedWorkflow = this.workflows.find(workflow => this.workflowKey(workflow) === event.target.value) ?? null;
                        this.update();
                    }}
                >
                    {this.workflows.map(workflow => <option key={this.workflowKey(workflow)} value={this.workflowKey(workflow)}>{workflow.name}</option>)}
                </select>
                <button style={buttonStyle} onClick={() => this.loadWorkflows()}>Refresh</button>
            </div>
        );
    }

    protected renderGraph(workflow: GraphWorkflowInfo): React.ReactNode {
        const nodes = workflow.nodes ?? [];
        const edges = workflow.edges ?? [];
        if (nodes.length === 0) {
            return (
                <div style={centerStyle}>
                    <strong>{workflow.name}</strong>
                    <span>Detected {workflow.type} workflow at {workflow.path}</span>
                    <span>Topology metadata is not available yet.</span>
                </div>
            );
        }
        const nodePositions = this.computeLayout(nodes, edges);
        return (
            <div style={{ flex: 1, overflow: 'auto', padding: '16px', backgroundColor: 'var(--theia-editor-background)', position: 'relative' }} onClick={() => this.closeNodeMenu()}>
                {this.renderDegradationIndicator()}
                {this.renderNodeMenu()}
                <svg width="800" height="500" style={{ fontFamily: 'var(--theia-ui-font-family)' }}>
                    <defs>
                        <marker id="arc-workflow-arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                            <polygon points="0 0, 10 3.5, 0 7" fill="#4fc3f7" />
                        </marker>
                    </defs>
                    {edges.map(edge => this.renderEdge(edge, nodePositions))}
                    {nodes.map(node => this.renderNode(node, nodePositions))}
                </svg>
                <div style={{ fontSize: '11px', color: 'var(--theia-descriptionForeground)', marginTop: '8px' }}>
                    {nodes.length} nodes / {edges.length} edges / Runtime: {workflow.runtime ?? workflow.type}
                    {this.crossLinkState.selectedNodeId && ` · Selected: ${this.crossLinkState.selectedNodeId}`}
                    {this.degradationManifest.isDegraded && ' · ⚠ Cross-linking degraded'}
                </div>
            </div>
        );
    }

    protected renderEdge(edge: WorkflowEdge, positions: Record<string, { x: number; y: number }>): React.ReactNode {
        const from = positions[edge.from_node];
        const to = positions[edge.to_node];
        if (!from || !to) {
            return null;
        }
        const strokeWidth = edge.messageVolume ? Math.min(edge.messageVolume, 3) : 2;
        const strokeColor = edge.active ? '#fff176' : edge.conditional ? '#ffb74d' : '#4fc3f7';
        return (
            <g key={edge.id}>
                <line
                    x1={from.x + 60}
                    y1={from.y + 20}
                    x2={to.x + 60}
                    y2={to.y + 20}
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    markerEnd="url(#arc-workflow-arrowhead)"
                    strokeDasharray={edge.conditional ? '5,3' : undefined}
                    style={edge.active ? { animation: 'arc-edge-flow 420ms linear infinite' } : undefined}
                />
                {edge.label && <text x={(from.x + to.x) / 2 + 60} y={(from.y + to.y) / 2 + 20} fontSize="10" fill="#999" textAnchor="middle">{edge.label}</text>}
            </g>
        );
    }

    protected renderNode(node: WorkflowNode, positions: Record<string, { x: number; y: number }>): React.ReactNode {
        const pos = positions[node.id];
        if (!pos) {
            return null;
        }
        const color = this.nodeColor(node);
        const isSelected = this.crossLinkState.selectedNodeId === node.id;
        const hasEvidence = (node.evidenceRefs?.length ?? 0) > 0;
        const hasStableIds = !!node.messageId || !!node.toolCallId || !!node.decisionId;
        const stateIndicator = node.state === 'running' ? '●' : node.state === 'done' ? '✓' : node.state === 'failed' ? '✗' : '';

        return (
            <g
                key={node.id}
                style={{ cursor: 'pointer' }}
                onClick={() => this.handleNodeSelect(node)}
                onContextMenu={(e) => this.handleNodeContextMenu(node, e)}
                role="button"
                aria-label={`${node.label}, ${node.type ?? 'agent'}, ${node.runtime ?? this.selectedWorkflow?.type ?? 'swarmgraph'}, ${node.state ?? 'idle'}, ${node.eventCount ?? 0} events`}
            >
                <rect
                    x={pos.x}
                    y={pos.y}
                    width="120"
                    height="40"
                    rx="6"
                    ry="6"
                    fill={color.bg}
                    stroke={isSelected ? '#fff176' : color.border}
                    strokeWidth={isSelected ? 3 : 2}
                />
                <text x={pos.x + 60} y={pos.y + 20} fontSize="12" fill={color.text} textAnchor="middle" fontWeight="500">
                    {node.label.length > 14 ? `${node.label.substring(0, 14)}...` : node.label}
                </text>
                {stateIndicator && (
                    <text x={pos.x + 108} y={pos.y + 14} fontSize="10" fill={node.state === 'failed' ? '#ef5350' : node.state === 'done' ? '#66bb6a' : '#4fc3f7'}>
                        {stateIndicator}
                    </text>
                )}
                {hasEvidence && (
                    <circle cx={pos.x + 8} cy={pos.y + 34} r="4" fill="#ffb74d" />
                )}
                {hasStableIds && (
                    <circle cx={pos.x + 18} cy={pos.y + 34} r="3" fill="#4fc3f7" />
                )}
                {node.eventCount && (
                    <text x={pos.x + 60} y={pos.y + 36} fontSize="9" fill={color.text} textAnchor="middle" opacity={0.7}>
                        {node.eventCount} events
                    </text>
                )}
            </g>
        );
    }

    protected renderEmpty(): React.ReactNode {
        return <div style={centerStyle}>No workflows detected</div>;
    }

    protected renderNodeMenu(): React.ReactNode {
        if (!this.showNodeMenu || !this.selectedNodeForMenu) {
            return null;
        }

        return (
            <div
                style={{
                    position: 'absolute',
                    top: '50%',
                    right: '16px',
                    zIndex: 1000,
                    backgroundColor: 'var(--theia-menu-background)',
                    border: '1px solid var(--theia-menu-border)',
                    borderRadius: '4px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                    padding: '4px 0',
                    minWidth: '180px',
                    fontFamily: 'var(--theia-ui-font-family)',
                    fontSize: '13px',
                }}
            >
                <div style={{ padding: '4px 12px', fontWeight: 600, borderBottom: '1px solid var(--theia-menu-border)', color: 'var(--theia-foreground)' }}>
                    {this.selectedNodeForMenu.label}
                </div>
                <div
                    style={{ padding: '6px 12px', cursor: 'pointer', color: 'var(--theia-foreground)' }}
                    onClick={() => this.handleCopyNodeId()}
                    onMouseEnter={e => { (e.target as HTMLElement).style.backgroundColor = 'var(--theia-list-hoverBackground)'; }}
                    onMouseLeave={e => { (e.target as HTMLElement).style.backgroundColor = 'transparent'; }}
                >
                    Copy node ID
                </div>
                <div
                    style={{ padding: '6px 12px', cursor: 'pointer', color: 'var(--theia-descriptionForeground)', opacity: 0.6 }}
                    onClick={() => this.handleShowEvidence()}
                    title="Reserved for v0.2"
                >
                    Show evidence
                </div>
                <div
                    style={{ padding: '6px 12px', cursor: 'pointer', color: 'var(--theia-descriptionForeground)', opacity: 0.6 }}
                    onClick={() => this.handleOpenReceipt()}
                    title="Reserved for v0.2"
                >
                    Open receipt
                </div>
                <div
                    style={{ padding: '6px 12px', cursor: 'pointer', color: 'var(--theia-descriptionForeground)', opacity: 0.6 }}
                    onClick={() => this.handleExplainEdge()}
                    title="Reserved for v0.2"
                >
                    Explain edge
                </div>
                <div style={{ borderTop: '1px solid var(--theia-menu-border)', marginTop: '4px', paddingTop: '4px', padding: '4px 12px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Read-only · Mutating commands reserved
                </div>
            </div>
        );
    }

    protected renderDegradationIndicator(): React.ReactNode {
        if (!this.degradationManifest.isDegraded) {
            return null;
        }

        return (
            <div style={{
                padding: '6px 12px',
                backgroundColor: 'rgba(255, 183, 77, 0.15)',
                borderBottom: '1px solid rgba(255, 183, 77, 0.3)',
                color: '#ffb74d',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
            }}>
                <span>⚠</span>
                <span>Cross-linking degraded: {this.degradationManifest.missingNodeIds} missing node IDs, {this.degradationManifest.missingMessageIds} missing message IDs</span>
            </div>
        );
    }

    protected computeLayout(nodes: WorkflowNode[], edges: WorkflowEdge[]): Record<string, { x: number; y: number }> {
        const positions: Record<string, { x: number; y: number }> = {};
        const layers: string[][] = [];
        const hasIncoming = new Set(edges.map(edge => edge.to_node));
        const startNodes = nodes.filter(node => !hasIncoming.has(node.id) || node.type === 'start').map(node => node.id);
        const visited = new Set<string>();
        let currentLayer = startNodes;
        while (currentLayer.length > 0) {
            layers.push(currentLayer);
            currentLayer.forEach(id => visited.add(id));
            currentLayer = edges.filter(edge => currentLayer.includes(edge.from_node) && !visited.has(edge.to_node)).map(edge => edge.to_node).filter((id, index, array) => array.indexOf(id) === index);
        }
        const remaining = nodes.filter(node => !visited.has(node.id)).map(node => node.id);
        if (remaining.length > 0) {
            layers.push(remaining);
        }
        layers.forEach((layer, layerIndex) => {
            const startY = (500 - ((layer.length - 1) * 80)) / 2;
            layer.forEach((nodeId, nodeIndex) => {
                positions[nodeId] = { x: 40 + layerIndex * 160, y: startY + nodeIndex * 80 };
            });
        });
        return positions;
    }

    protected nodeColor(node: WorkflowNode): { bg: string; border: string; text: string } {
        const state = node.state;
        if (state === 'running') {
            return { bg: '#1a3d47', border: '#4fc3f7', text: '#fff' };
        }
        if (state === 'failed') {
            return { bg: '#4a1a1a', border: '#ef5350', text: '#fff' };
        }
        if (state === 'done') {
            return { bg: '#1a472a', border: '#66bb6a', text: '#fff' };
        }
        switch (node.type) {
            case 'start': return { bg: '#1a472a', border: '#4caf50', text: '#fff' };
            case 'end': return { bg: '#4a1942', border: '#e040fb', text: '#fff' };
            case 'queen': return { bg: '#2d1a47', border: '#ab47bc', text: '#fff' };
            case 'worker':
            case 'agent': return { bg: '#1a2d47', border: '#4fc3f7', text: '#fff' };
            case 'tool': return { bg: '#3d2b1a', border: '#ffb74d', text: '#fff' };
            case 'resource': return { bg: '#1a3d32', border: '#66bb6a', text: '#fff' };
            case 'prompt': return { bg: '#2d1a47', border: '#ba68c8', text: '#fff' };
            case 'decision':
            case 'router': return { bg: '#2d2d00', border: '#fff176', text: '#fff' };
            case 'hitl': return { bg: '#1a2d3d', border: '#4dd0e1', text: '#fff' };
            case 'terminal': return { bg: '#4a1942', border: '#e040fb', text: '#fff' };
            default: return { bg: '#2d2d2d', border: '#666', text: '#fff' };
        }
    }

    protected workflowKey(workflow: GraphWorkflowInfo | null): string {
        return workflow?.id ?? workflow?.path ?? '';
    }
}

const centerStyle: React.CSSProperties = {
    alignItems: 'center',
    color: 'var(--theia-descriptionForeground)',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    height: '100%',
    justifyContent: 'center',
    padding: '24px',
    textAlign: 'center',
};

const buttonStyle: React.CSSProperties = {
    background: 'none',
    border: '1px solid var(--theia-widget-border)',
    borderRadius: '4px',
    color: 'var(--theia-foreground)',
    cursor: 'pointer',
    padding: '4px 8px',
};
