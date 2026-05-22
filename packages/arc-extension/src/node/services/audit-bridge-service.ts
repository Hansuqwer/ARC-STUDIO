/**
 * AuditBridgeService - Audit chain and run metadata access
 * 
 * Handles:
 * - Run links (evidence references)
 * - Run receipts (cost/usage summaries)
 * - Failure autopsies (post-mortem analysis)
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { execFileSync } from 'child_process';
import * as path from 'path';
import {
    RunLinksResponse,
    RunReceipt,
    FailureAutopsy,
    ArcError,
    ArcErrorCode,
} from '../../common/arc-protocol';
import { buildArcCliEnv } from './arc-cli-utils';
import { validateRunId } from '../security-utils';

@injectable()
export class AuditBridgeService {
    constructor(
        @inject('WorkspaceRoot') private readonly workspaceRoot: string
    ) {}

    async getRunLinks(runId: string, filter?: string, stableId?: string): Promise<RunLinksResponse> {
        try {
            const args = ['runs', 'links', runId, '--json'];
            if (filter) {
                args.push('--filter', filter);
            }
            if (stableId) {
                args.push('--stable-id', stableId);
            }

            const output = execFileSync('arc', args, {
                timeout: 15000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && parsed.data) {
                const data = parsed.data;
                return {
                    nodeChains: data.node_chains || {},
                    messageChains: data.message_chains || {},
                    toolCallChains: data.tool_call_chains || {},
                    evidenceChains: data.evidence_chains || {},
                    hasStableIds: !!data.has_stable_ids,
                    stableIdCount: data.stable_id_count || 0,
                };
            }
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                parsed?.error?.message || 'CLI returned no data for run links',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to get run links: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    async getRunReceipt(runId: string): Promise<RunReceipt> {
        try {
            validateRunId(runId);
            const receiptPath = path.join(this.workspaceRoot, '.arc', 'receipts', `${runId}.json`);
            const fs = await import('fs-extra');
            if (!await fs.pathExists(receiptPath)) {
                throw new ArcError(ArcErrorCode.RUN_NOT_FOUND, `No receipt found for run: ${runId}`, { runId });
            }
            const content = await fs.readFile(receiptPath, 'utf-8');
            return JSON.parse(content) as RunReceipt;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to read receipt: ${error instanceof Error ? error.message : 'Unknown error'}`,
                { runId }
            );
        }
    }

    async getRunAutopsy(runId: string): Promise<FailureAutopsy | null> {
        try {
            validateRunId(runId);
            const autopsyPath = path.join(this.workspaceRoot, '.arc', 'autopsies', `${runId}.json`);
            const fs = await import('fs-extra');
            if (!await fs.pathExists(autopsyPath)) {
                return null;
            }
            const content = await fs.readFile(autopsyPath, 'utf-8');
            return JSON.parse(content) as FailureAutopsy;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to read autopsy: ${error instanceof Error ? error.message : 'Unknown error'}`,
                { runId }
            );
        }
    }
}
