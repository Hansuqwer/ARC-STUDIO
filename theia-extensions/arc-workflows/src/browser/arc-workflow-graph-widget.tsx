/**
 * ARC Workflow Graph Widget
 *
 * Renders workflow topology as an SVG graph.
 * Uses a simple force-directed layout for the alpha.
 *
 * NOTE: Production implementation should use a proper graph library
 * (e.g., @eclipse-glsp/client or reactflow).
 * MOCK_REASON: No graph rendering library bundled yet
 * REAL_IMPLEMENTATION_PATH: Integrate @eclipse-glsp/client or reactflow
 * LOCAL_FIX_STEPS: pnpm add reactflow && replace SVG renderer
 * OWNER: Workflow Graph Agent
 * REMOVE_BEFORE: Beta
 */

import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { WorkflowInfo, WorkflowNode, WorkflowEdge } from 'arc-core/lib/common/arc-protocol';

@injectable()
export class ArcWorkflowGraphWidget extends ReactWidget {
  static readonly ID = 'arc:workflow-graph';
  static readonly LABEL = 'ARC Workflow Graph';

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  protected workflows: WorkflowInfo[] = [];
  protected selectedWorkflow: WorkflowInfo | null = null;
  protected loading = false;

  @postConstruct()
  protected override init(): void {
    super.init();
    this.id = ArcWorkflowGraphWidget.ID;
    this.title.label = ArcWorkflowGraphWidget.LABEL;
    this.title.closable = true;
    this.title.caption = 'ARC Workflow Graph';
    this.loadWorkflows();
  }

  protected async loadWorkflows(): Promise<void> {
    this.loading = true;
    this.update();
    try {
      const result = await this.arcService.listWorkflows();
      this.workflows = result.data ?? [];
      if (this.workflows.length > 0) {
        this.selectedWorkflow = this.workflows[0];
      }
    } finally {
      this.loading = false;
      this.update();
    }
  }

  protected render(): React.ReactNode {
    if (this.loading) {
      return <div style={{ padding: '24px', textAlign: 'center' }}>Loading workflows…</div>;
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
          onChange={e => {
            this.selectedWorkflow = this.workflows.find(w => w.id === e.target.value) ?? null;
            this.update();
          }}
        >
          {this.workflows.map(w => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
        <button style={btnStyle} onClick={() => this.loadWorkflows()}>↻</button>
      </div>
    );
  }

  protected renderGraph(workflow: WorkflowInfo): React.ReactNode {
    // Simple SVG layout — nodes in a grid, edges as lines
    const nodePositions = this.computeLayout(workflow.nodes, workflow.edges);
    const svgWidth = 800;
    const svgHeight = 500;

    return (
      <div style={{ flex: 1, overflow: 'auto', padding: '16px', backgroundColor: 'var(--theia-editor-background)' }}>
        <svg width={svgWidth} height={svgHeight} style={{ fontFamily: 'var(--theia-ui-font-family)' }}>
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#4fc3f7" />
            </marker>
          </defs>

          {/* Edges */}
          {workflow.edges.map(edge => {
            const from = nodePositions[edge.from_node];
            const to = nodePositions[edge.to_node];
            if (!from || !to) return null;
            return (
              <g key={edge.id}>
                <line
                  x1={from.x + 60} y1={from.y + 20}
                  x2={to.x + 60} y2={to.y + 20}
                  stroke={edge.conditional ? '#ffb74d' : '#4fc3f7'}
                  strokeWidth="2"
                  markerEnd="url(#arrowhead)"
                  strokeDasharray={edge.conditional ? '5,3' : undefined}
                />
                {edge.label && (
                  <text
                    x={(from.x + to.x) / 2 + 60}
                    y={(from.y + to.y) / 2 + 20}
                    fontSize="10"
                    fill="#999"
                    textAnchor="middle"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {workflow.nodes.map(node => {
            const pos = nodePositions[node.id];
            if (!pos) return null;
            const nodeColor = this.nodeColor(node);
            return (
              <g key={node.id} style={{ cursor: 'pointer' }}>
                <rect
                  x={pos.x} y={pos.y}
                  width="120" height="40"
                  rx="6" ry="6"
                  fill={nodeColor.bg}
                  stroke={nodeColor.border}
                  strokeWidth="2"
                />
                <text
                  x={pos.x + 60} y={pos.y + 24}
                  fontSize="12"
                  fill={nodeColor.text}
                  textAnchor="middle"
                  fontWeight="500"
                >
                  {node.label.length > 14 ? node.label.substring(0, 14) + '…' : node.label}
                </text>
              </g>
            );
          })}
        </svg>
        <div style={{ fontSize: '11px', color: 'var(--theia-descriptionForeground)', marginTop: '8px' }}>
          {workflow.nodes.length} nodes · {workflow.edges.length} edges · Runtime: {workflow.runtime}
          {workflow.metadata?.['_mock'] && ' · [MOCK fixture]'}
        </div>
      </div>
    );
  }

  protected renderEmpty(): React.ReactNode {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '12px', color: 'var(--theia-descriptionForeground)' }}>
        <span style={{ fontSize: '32px' }}>⎘</span>
        <span>No workflows detected</span>
      </div>
    );
  }

  protected computeLayout(nodes: WorkflowNode[], edges: WorkflowEdge[]): Record<string, { x: number; y: number }> {
    // Simple layered layout for DAG
    const positions: Record<string, { x: number; y: number }> = {};
    const layers: string[][] = [];

    // Find entry nodes (start nodes or nodes with no incoming edges)
    const hasIncoming = new Set(edges.map(e => e.to_node));
    const startNodes = nodes.filter(n => !hasIncoming.has(n.id) || n.type === 'start').map(n => n.id);

    // BFS layering
    const visited = new Set<string>();
    let currentLayer = startNodes;
    while (currentLayer.length > 0) {
      layers.push(currentLayer);
      currentLayer.forEach(id => visited.add(id));
      const nextLayer = edges
        .filter(e => currentLayer.includes(e.from_node) && !visited.has(e.to_node))
        .map(e => e.to_node)
        .filter((id, i, arr) => arr.indexOf(id) === i);
      currentLayer = nextLayer;
    }

    // Any remaining unvisited nodes
    const remaining = nodes.filter(n => !visited.has(n.id)).map(n => n.id);
    if (remaining.length > 0) layers.push(remaining);

    // Assign positions
    const layerSpacing = 160;
    const nodeSpacing = 80;
    layers.forEach((layer, li) => {
      const totalHeight = (layer.length - 1) * nodeSpacing;
      const startY = (500 - totalHeight) / 2;
      layer.forEach((nodeId, ni) => {
        positions[nodeId] = {
          x: 40 + li * layerSpacing,
          y: startY + ni * nodeSpacing,
        };
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
}

const btnStyle: React.CSSProperties = {
  padding: '4px 8px',
  background: 'none',
  border: '1px solid var(--theia-widget-border)',
  borderRadius: '4px',
  cursor: 'pointer',
  color: 'var(--theia-foreground)',
};
