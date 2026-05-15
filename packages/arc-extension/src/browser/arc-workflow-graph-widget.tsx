/** ARC Workflow Graph Widget — ported shell from the legacy arc-workflows extension. */
import * as React from 'react';
import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcService, WorkflowInfo } from '../common/arc-protocol';

interface WorkflowNode {
    id: string;
    label: string;
    type?: string;
}

interface WorkflowEdge {
    id: string;
    from_node: string;
    to_node: string;
    label?: string;
    conditional?: boolean;
}

type GraphWorkflowInfo = WorkflowInfo & {
    id?: string;
    runtime?: string;
    nodes?: WorkflowNode[];
    edges?: WorkflowEdge[];
    metadata?: Record<string, unknown>;
};

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

    @postConstruct()
    protected init(): void {
        this.id = ArcWorkflowGraphWidget.ID;
        this.title.label = ArcWorkflowGraphWidget.LABEL;
        this.title.closable = true;
        this.title.caption = 'ARC Workflow Graph';
        this.loadWorkflows();
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
            <div style={{ flex: 1, overflow: 'auto', padding: '16px', backgroundColor: 'var(--theia-editor-background)' }}>
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
        return (
            <g key={edge.id}>
                <line x1={from.x + 60} y1={from.y + 20} x2={to.x + 60} y2={to.y + 20} stroke={edge.conditional ? '#ffb74d' : '#4fc3f7'} strokeWidth="2" markerEnd="url(#arc-workflow-arrowhead)" strokeDasharray={edge.conditional ? '5,3' : undefined} />
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
        return (
            <g key={node.id} style={{ cursor: 'pointer' }}>
                <rect x={pos.x} y={pos.y} width="120" height="40" rx="6" ry="6" fill={color.bg} stroke={color.border} strokeWidth="2" />
                <text x={pos.x + 60} y={pos.y + 24} fontSize="12" fill={color.text} textAnchor="middle" fontWeight="500">
                    {node.label.length > 14 ? `${node.label.substring(0, 14)}...` : node.label}
                </text>
            </g>
        );
    }

    protected renderEmpty(): React.ReactNode {
        return <div style={centerStyle}>No workflows detected</div>;
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
        switch (node.type) {
            case 'start': return { bg: '#1a472a', border: '#4caf50', text: '#fff' };
            case 'end': return { bg: '#4a1942', border: '#e040fb', text: '#fff' };
            case 'agent': return { bg: '#1a2d47', border: '#4fc3f7', text: '#fff' };
            case 'tool': return { bg: '#3d2b1a', border: '#ffb74d', text: '#fff' };
            case 'router': return { bg: '#2d2d00', border: '#fff176', text: '#fff' };
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
