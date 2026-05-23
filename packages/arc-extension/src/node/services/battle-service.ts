/**
 * Battle Service
 *
 * Backend service that bridges to Python CLI battle commands.
 * Provides methods to list battles, get battle details, and fetch leaderboard.
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { execFileSync } from 'child_process';
import type {
    BattleRun,
    BattleDetails,
    EloRating,
    BattleListResponse,
    BattleShowResponse,
    BattleLeaderboardResponse
} from '../../common/battle-protocol';

@injectable()
export class BattleService {

    @inject('WorkspaceRoot')
    protected readonly workspaceRoot!: string;

    /**
     * List battle runs with optional filtering.
     */
    async listBattles(options?: { status?: string; limit?: number }): Promise<BattleRun[]> {
        try {
            const args = ['battle', 'list', '--json'];
            
            if (options?.status) {
                args.push('--status', options.status);
            }
            
            if (options?.limit) {
                args.push('--limit', options.limit.toString());
            }

            const output = execFileSync('arc', args, {
                cwd: this.workspaceRoot,
                encoding: 'utf-8',
                maxBuffer: 10 * 1024 * 1024, // 10MB
                timeout: 30000 // 30 seconds
            });

            const response: BattleListResponse = JSON.parse(output);
            
            if (response.status === 'ok') {
                return response.data;
            }
            
            throw new Error('Failed to list battles');
        } catch (error: any) {
            console.error('Failed to list battles:', error);
            throw new Error(`Failed to list battles: ${error.message}`);
        }
    }

    /**
     * Get detailed information about a specific battle.
     */
    async getBattleDetails(battleId: string): Promise<BattleDetails> {
        try {
            const output = execFileSync('arc', ['battle', 'show', battleId, '--json'], {
                cwd: this.workspaceRoot,
                encoding: 'utf-8',
                maxBuffer: 10 * 1024 * 1024, // 10MB
                timeout: 30000 // 30 seconds
            });

            const response: BattleShowResponse = JSON.parse(output);
            
            if (response.status === 'ok') {
                return response.data;
            }
            
            throw new Error('Failed to get battle details');
        } catch (error: any) {
            console.error('Failed to get battle details:', error);
            throw new Error(`Failed to get battle details: ${error.message}`);
        }
    }

    /**
     * Get ELO leaderboard rankings.
     */
    async getLeaderboard(limit?: number): Promise<EloRating[]> {
        try {
            const args = ['battle', 'leaderboard', '--json'];
            
            if (limit) {
                args.push('--limit', limit.toString());
            }

            const output = execFileSync('arc', args, {
                cwd: this.workspaceRoot,
                encoding: 'utf-8',
                maxBuffer: 10 * 1024 * 1024, // 10MB
                timeout: 30000 // 30 seconds
            });

            const response: BattleLeaderboardResponse = JSON.parse(output);
            
            if (response.status === 'ok') {
                return response.data;
            }
            
            throw new Error('Failed to get leaderboard');
        } catch (error: any) {
            console.error('Failed to get leaderboard:', error);
            throw new Error(`Failed to get leaderboard: ${error.message}`);
        }
    }
}
