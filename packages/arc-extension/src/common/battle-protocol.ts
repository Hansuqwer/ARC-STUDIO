/**
 * Battle Protocol Types
 *
 * TypeScript interfaces that mirror Python battle models for IDE integration.
 * These types match the JSON output from `arc battle` CLI commands.
 */

export interface BattleRun {
    id: string;
    prompt: string;
    workers: number;
    topology: 'flat';
    consensus_protocol: 'majority' | 'quorum';
    runtime_mode: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    created_at: string;
    started_at?: string;
    completed_at?: string;
    consensus_escrow: boolean;
    require_hitl: boolean;
    error_detail?: string;
    metadata?: Record<string, any>;
}

export interface BattleCandidate {
    id: string;
    battle_id: string;
    worker_id: string;
    model_id: string;
    output: string;
    created_at: string;
    metadata?: Record<string, any>;
}

export interface BattleVote {
    id: string;
    battle_id: string;
    candidate_id: string;
    voter: string;
    voter_type: 'human' | 'model';
    approved: boolean;
    reasoning?: string;
    created_at: string;
    commit_hash?: string;
    reveal_nonce?: string;
    metadata?: Record<string, any>;
}

export interface BattleOutcome {
    id: string;
    battle_id: string;
    winner_candidate_id?: string;
    consensus_reached: boolean;
    consensus_result: any;
    completed_at: string;
    metadata?: Record<string, any>;
}

export interface EloRating {
    model_id: string;
    rating: number;
    games_played: number;
    wins: number;
    losses: number;
    draws: number;
    last_updated: string;
    metadata?: Record<string, any>;
}

export interface BattleDetails {
    battle: BattleRun;
    candidates: BattleCandidate[];
    votes: BattleVote[];
    outcome?: BattleOutcome;
}

/**
 * Response from `arc battle list --json`
 */
export interface BattleListResponse {
    status: 'ok';
    data: BattleRun[];
}

/**
 * Response from `arc battle show <id> --json`
 */
export interface BattleShowResponse {
    status: 'ok';
    data: BattleDetails;
}

/**
 * Response from `arc battle leaderboard --json`
 */
export interface BattleLeaderboardResponse {
    status: 'ok';
    data: EloRating[];
}
