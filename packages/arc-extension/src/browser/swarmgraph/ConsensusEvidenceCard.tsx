import * as React from 'react';
import type { SwarmGraphConsensusInsight } from '../tabs/swarmgraph-insight-model';

interface ConsensusEvidenceCardProps {
    consensus: SwarmGraphConsensusInsight;
}

/** Renders consensus score, vote count, and evidence summary. Static props only in Phase 1. */
export const ConsensusEvidenceCard: React.FC<ConsensusEvidenceCardProps> = ({ consensus }) => {
    if (consensus.status === 'empty') {
        return <div className="arc-consensus-card" aria-label="Consensus Evidence — no data">No consensus data.</div>;
    }
    return (
        <div className="arc-consensus-card" role="region" aria-label="Consensus Evidence"
            style={{ border: '1px solid var(--arc-color-border, #454545)', padding: 12, borderRadius: 4 }}>
            <h4 style={{ margin: '0 0 8px', color: 'var(--arc-color-primary, #3794ff)' }}>Consensus Evidence</h4>
            {consensus.decision && (
                <div><strong>Decision:</strong> {consensus.decision}</div>
            )}
            {consensus.strategy && (
                <div><strong>Strategy:</strong> {consensus.strategy}</div>
            )}
            <div><strong>Voters:</strong> {consensus.voters.length > 0 ? consensus.voters.join(', ') : '—'}</div>
            <div><strong>Votes:</strong> {consensus.votes.length}</div>
        </div>
    );
};
