/**
 * Battle Tab
 *
 * Displays battle runs, candidates, votes, outcomes, and ELO leaderboard.
 * Phase 34.2 - IDE Battle Tab implementation.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, BattleRun, BattleDetails, EloRating } from '../../common/arc-protocol';

export interface BattleTabProps {
    arcService: ArcService;
}

interface BattleTabState {
    battles: BattleRun[];
    selectedBattleId: string | null;
    battleDetails: BattleDetails | null;
    leaderboard: EloRating[];
    isLoadingBattles: boolean;
    isLoadingDetails: boolean;
    isLoadingLeaderboard: boolean;
    error: string | null;
}

function formatTimestamp(ts: string): string {
    try {
        const d = new Date(ts);
        return d.toLocaleString();
    } catch {
        return ts;
    }
}

function truncateId(id: string, max = 12): string {
    return id.length > max ? id.slice(0, max) + '…' : id;
}

export const BattleTab: React.FC<BattleTabProps> = ({ arcService }) => {
    const [state, setState] = React.useState<BattleTabState>({
        battles: [],
        selectedBattleId: null,
        battleDetails: null,
        leaderboard: [],
        isLoadingBattles: false,
        isLoadingDetails: false,
        isLoadingLeaderboard: false,
        error: null,
    });

    const loadBattles = React.useCallback(async () => {
        setState(prev => ({ ...prev, isLoadingBattles: true, error: null }));
        try {
            const battles = await arcService.listBattles({ limit: 50 });
            setState(prev => ({ ...prev, battles, isLoadingBattles: false }));
        } catch (err: any) {
            setState(prev => ({
                ...prev,
                isLoadingBattles: false,
                error: `Failed to load battles: ${err.message}`,
            }));
        }
    }, [arcService]);

    const loadLeaderboard = React.useCallback(async () => {
        setState(prev => ({ ...prev, isLoadingLeaderboard: true }));
        try {
            const leaderboard = await arcService.getLeaderboard(10);
            setState(prev => ({ ...prev, leaderboard, isLoadingLeaderboard: false }));
        } catch (err: any) {
            setState(prev => ({ ...prev, isLoadingLeaderboard: false }));
        }
    }, [arcService]);

    const selectBattle = React.useCallback(async (battleId: string) => {
        setState(prev => ({
            ...prev,
            selectedBattleId: battleId,
            battleDetails: null,
            isLoadingDetails: true,
            error: null,
        }));
        try {
            const details = await arcService.getBattleDetails(battleId);
            setState(prev => ({ ...prev, battleDetails: details, isLoadingDetails: false }));
        } catch (err: any) {
            setState(prev => ({
                ...prev,
                isLoadingDetails: false,
                error: `Failed to load battle details: ${err.message}`,
            }));
        }
    }, [arcService]);

    React.useEffect(() => {
        loadBattles();
        loadLeaderboard();
    }, [loadBattles, loadLeaderboard]);

    const { battles, selectedBattleId, battleDetails, leaderboard, isLoadingBattles, isLoadingDetails, isLoadingLeaderboard, error } = state;

    // Empty state
    if (battles.length === 0 && !isLoadingBattles) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <p style={{ color: 'var(--theia-descriptionForeground)' }}>
                    No battles found. Run <code>arc battle run "your prompt"</code> to create a battle.
                </p>
                <button
                    onClick={loadBattles}
                    style={{
                        marginTop: '1rem',
                        padding: '0.5rem 1rem',
                        cursor: 'pointer',
                    }}
                >
                    Refresh
                </button>
            </div>
        );
    }

    return (
        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 300px', gap: '1rem', height: '100%', padding: '1rem' }}>
            {/* Battle List */}
            <div style={{ overflowY: 'auto', borderRight: '1px solid var(--theia-panel-border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={{ margin: 0 }}>Battles ({battles.length})</h3>
                    <button onClick={loadBattles} disabled={isLoadingBattles} style={{ cursor: 'pointer' }}>
                        {isLoadingBattles ? '...' : '↻'}
                    </button>
                </div>
                {error && <div style={{ color: 'var(--theia-errorForeground)', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {battles.map(battle => (
                        <div
                            key={battle.id}
                            onClick={() => selectBattle(battle.id)}
                            style={{
                                padding: '0.75rem',
                                cursor: 'pointer',
                                backgroundColor: selectedBattleId === battle.id ? 'var(--theia-list-activeSelectionBackground)' : 'transparent',
                                border: '1px solid var(--theia-panel-border)',
                                borderRadius: '4px',
                            }}
                        >
                            <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>{truncateId(battle.id)}</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--theia-descriptionForeground)' }}>
                                <div>Status: <span style={{ color: battle.status === 'completed' ? 'var(--theia-testing-iconPassed)' : 'var(--theia-testing-iconFailed)' }}>{battle.status}</span></div>
                                <div>Workers: {battle.workers} | {battle.consensus_protocol}</div>
                                <div>{formatTimestamp(battle.created_at)}</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Battle Details */}
            <div style={{ overflowY: 'auto', padding: '0 1rem' }}>
                {isLoadingDetails && <div>Loading battle details...</div>}
                {!selectedBattleId && !isLoadingDetails && (
                    <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--theia-descriptionForeground)' }}>
                        Select a battle to view details
                    </div>
                )}
                {battleDetails && !isLoadingDetails && (
                    <div>
                        <h3>Battle: {truncateId(battleDetails.battle.id)}</h3>
                        <div style={{ marginBottom: '1.5rem' }}>
                            <div><strong>Prompt:</strong> {battleDetails.battle.prompt}</div>
                            <div><strong>Workers:</strong> {battleDetails.battle.workers}</div>
                            <div><strong>Topology:</strong> {battleDetails.battle.topology}</div>
                            <div><strong>Consensus:</strong> {battleDetails.battle.consensus_protocol}</div>
                            <div><strong>Status:</strong> {battleDetails.battle.status}</div>
                        </div>

                        <h4>Candidates ({battleDetails.candidates.length})</h4>
                        <div style={{ marginBottom: '1.5rem' }}>
                            {battleDetails.candidates.map(candidate => (
                                <div key={candidate.id} style={{ marginBottom: '1rem', padding: '0.75rem', border: '1px solid var(--theia-panel-border)', borderRadius: '4px' }}>
                                    <div><strong>{candidate.worker_id}</strong> ({candidate.model_id})</div>
                                    <div style={{ fontSize: '0.9rem', marginTop: '0.5rem', color: 'var(--theia-descriptionForeground)' }}>
                                        {candidate.output.substring(0, 200)}{candidate.output.length > 200 ? '...' : ''}
                                    </div>
                                </div>
                            ))}
                        </div>

                        <h4>Votes ({battleDetails.votes.length})</h4>
                        <div style={{ marginBottom: '1.5rem' }}>
                            {battleDetails.votes.map(vote => (
                                <div key={vote.id} style={{ marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                                    <span style={{ color: vote.approved ? 'var(--theia-testing-iconPassed)' : 'var(--theia-testing-iconFailed)' }}>
                                        {vote.approved ? '✓' : '✗'}
                                    </span>
                                    {' '}{vote.voter} → {truncateId(vote.candidate_id)}
                                </div>
                            ))}
                        </div>

                        {battleDetails.outcome && (
                            <>
                                <h4>Outcome</h4>
                                <div>
                                    <div><strong>Consensus Reached:</strong> {battleDetails.outcome.consensus_reached ? 'Yes' : 'No'}</div>
                                    {battleDetails.outcome.winner_candidate_id && (
                                        <div><strong>Winner:</strong> {truncateId(battleDetails.outcome.winner_candidate_id)}</div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                )}
            </div>

            {/* Leaderboard */}
            <div style={{ overflowY: 'auto', borderLeft: '1px solid var(--theia-panel-border)', paddingLeft: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={{ margin: 0 }}>Leaderboard</h3>
                    <button onClick={loadLeaderboard} disabled={isLoadingLeaderboard} style={{ cursor: 'pointer' }}>
                        {isLoadingLeaderboard ? '...' : '↻'}
                    </button>
                </div>
                {leaderboard.length === 0 && !isLoadingLeaderboard && (
                    <div style={{ color: 'var(--theia-descriptionForeground)', fontSize: '0.9rem' }}>
                        No ELO ratings yet
                    </div>
                )}
                <div style={{ fontSize: '0.85rem' }}>
                    {leaderboard.map((rating, index) => (
                        <div key={rating.model_id} style={{ marginBottom: '0.75rem', padding: '0.5rem', border: '1px solid var(--theia-panel-border)', borderRadius: '4px' }}>
                            <div style={{ fontWeight: 'bold' }}>#{index + 1} {rating.model_id}</div>
                            <div style={{ color: 'var(--theia-descriptionForeground)' }}>
                                <div>Rating: {rating.rating.toFixed(1)}</div>
                                <div>Games: {rating.games_played}</div>
                                <div>W-L-D: {rating.wins}-{rating.losses}-{rating.draws}</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
