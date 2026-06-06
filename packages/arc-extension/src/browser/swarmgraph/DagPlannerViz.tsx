import * as React from 'react';
import type { SwarmGraphTopologyInsight } from '../tabs/swarmgraph-insight-model';

interface DagPlannerVizProps {
    topology: SwarmGraphTopologyInsight;
}

/** Renders DAG topology as a plain node/edge list. No D3 in Phase 1. Uses --arc-color-* tokens. */
export const DagPlannerViz: React.FC<DagPlannerVizProps> = ({ topology }) => {
    if (topology.status === 'empty') {
        return <div className="arc-dag-viz" aria-label="DAG Planner — no data">No topology data.</div>;
    }
    return (
        <div className="arc-dag-viz" aria-label="DAG Planner — topology">
            <h4 style={{ color: 'var(--arc-color-primary, #3794ff)', margin: '0 0 8px' }}>Nodes</h4>
            <ul role="list" aria-label="DAG nodes">
                {topology.nodes.map(n => (
                    <li key={n.id} role="listitem" style={{ marginBottom: 4 }}>
                        <strong>{n.id}</strong>{n.role ? ` (${n.role})` : ''}{n.label && n.label !== n.id ? ` — ${n.label}` : ''}
                    </li>
                ))}
            </ul>
            <h4 style={{ color: 'var(--arc-color-primary, #3794ff)', margin: '8px 0' }}>Edges</h4>
            <ul role="list" aria-label="DAG edges">
                {topology.edges.map((e, i) => (
                    <li key={i} role="listitem" style={{ marginBottom: 2 }}>
                        {e.source} → {e.target}{e.label ? ` (${e.label})` : ''}
                    </li>
                ))}
            </ul>
        </div>
    );
};
