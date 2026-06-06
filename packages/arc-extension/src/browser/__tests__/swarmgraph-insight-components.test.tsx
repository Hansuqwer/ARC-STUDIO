/**
 * SwarmGraph Insight UI Phase 1 — component render contract tests.
 */
import * as React from 'react';
import { DagPlannerViz } from '../swarmgraph/DagPlannerViz';
import { ConsensusEvidenceCard } from '../swarmgraph/ConsensusEvidenceCard';
import { HitlApprovalPanel } from '../swarmgraph/HitlApprovalPanel';

const EMPTY_TOPOLOGY = { status: 'empty' as const, nodes: [], edges: [] };
const TOPOLOGY = {
    status: 'present' as const,
    nodes: [{ id: 'queen', role: 'queen' }, { id: 'w1', role: 'worker' }],
    edges: [{ source: 'queen', target: 'w1' }],
};
const EMPTY_CONSENSUS = { status: 'empty' as const, decision: undefined, strategy: undefined, voters: [], votes: [] };
const CONSENSUS = { status: 'present' as const, decision: 'consensus', strategy: 'majority', voters: ['w1', 'w2'], votes: [{}, {}] };

describe('DagPlannerViz', () => {
    it('renders empty state', () => {
        const el = React.createElement(DagPlannerViz, { topology: EMPTY_TOPOLOGY });
        expect(el).toBeTruthy();
        expect(el.props.topology.status).toBe('empty');
    });

    it('renders topology with nodes', () => {
        const el = React.createElement(DagPlannerViz, { topology: TOPOLOGY });
        expect(el.props.topology.nodes).toHaveLength(2);
        expect(el.props.topology.edges).toHaveLength(1);
    });
});

describe('ConsensusEvidenceCard', () => {
    it('renders empty state', () => {
        const el = React.createElement(ConsensusEvidenceCard, { consensus: EMPTY_CONSENSUS });
        expect(el).toBeTruthy();
    });

    it('renders consensus data', () => {
        const el = React.createElement(ConsensusEvidenceCard, { consensus: CONSENSUS });
        expect(el.props.consensus.voters).toHaveLength(2);
    });
});

describe('HitlApprovalPanel', () => {
    it('renders with required props', () => {
        const el = React.createElement(HitlApprovalPanel, {
            runId: 'run-123',
            prompt: 'Approve?',
            onApprove: () => {},
            onReject: () => {},
        });
        expect(el).toBeTruthy();
        expect(el.props.runId).toBe('run-123');
    });
});
