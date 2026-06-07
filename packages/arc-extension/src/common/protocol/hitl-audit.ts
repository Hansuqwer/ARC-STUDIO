/**
 * HITL (HitlPromptInfo, HitlRespondRequest) and Audit (AuditChainInfo) types.
 * Extracted from arc-protocol.ts (CR-027); re-exported via the barrel. Self-contained.
 */


/**
 * HITL prompt info for IDE display.
 */
export interface HitlPromptInfo {
    promptId: string;
    runId: string;
    prompt: string;
    createdAt: string;
    expiresAt?: string;
    promptType?: string;
    token?: string;
    status?: 'pending' | 'approved' | 'rejected' | 'modified' | 'expired' | 'used' | 'unknown';
    expired?: boolean;
    singleUse?: boolean;
    usedAt?: string;
}

/**
 * Request to respond to a HITL prompt.
 */
export interface HitlRespondRequest {
    promptId: string;
    decision: 'approve' | 'reject' | 'modify';
    response?: string;
    token: string;
}

// ========== Audit ==========

/**
 * Audit chain info for a run.
 */
export interface AuditChainInfo {
    runId: string;
    auditPath?: string;
    chainVerified: boolean;
    recordCount: number;
    state?: 'present' | 'missing' | 'degraded';
    reason?: string;
    signature?: string;
    hmacAlgo?: string;
    /** Verification mode used: sha256 or hmac */
    mode?: 'sha256' | 'hmac';
    /** Number of records actually checked by verifier */
    recordsChecked?: number;
    /** Verification duration in milliseconds */
    durationMs?: number;
    /** Audit chain file size in bytes */
    fileSizeBytes?: number;
    /** Peak memory usage during verification in MB */
    peakMemoryMb?: number;
}
