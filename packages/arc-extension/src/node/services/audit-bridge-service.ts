/**
 * AuditBridgeService - Audit chain and run metadata access
 * 
 * Handles:
 * - Run links (evidence references)
 * - Run receipts (cost/usage summaries)
 * - Failure autopsies (post-mortem analysis)
 */

import { injectable } from '@theia/core/shared/inversify';
import {
    RunLinksResponse,
    RunReceipt,
    FailureAutopsy,
} from '../../common/arc-protocol';

@injectable()
export class AuditBridgeService {
    // Methods will be moved from ArcBackendService in subsequent commits

    async getRunLinks(runId: string, filter?: string, stableId?: string): Promise<RunLinksResponse> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async getRunReceipt(runId: string): Promise<RunReceipt> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async getRunAutopsy(runId: string): Promise<FailureAutopsy | null> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }
}
