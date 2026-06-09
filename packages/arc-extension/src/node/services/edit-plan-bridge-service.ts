import {
    ArcError,
    ArcErrorCode,
    EditPlanApprovalResult,
    EditPlanApplyResult,
    EditPlanDiffResult,
    EditPlanInfo,
    EditPlanListResult,
} from '../../common/arc-protocol';
import { buildArcCliEnv, execArcCliAsync } from './arc-cli-utils';

interface ArcEnvelope {
    ok: boolean;
    data?: Record<string, unknown>;
    error?: { code?: string; message?: string };
}

const PLAN_ID_RE = /^[A-Za-z0-9_-]{1,96}$/;

export class EditPlanBridgeService {
    constructor(private readonly workspaceRoot: string) {}

    async listEditPlans(limit = 50): Promise<EditPlanListResult> {
        const safeLimit = Math.max(1, Math.min(Math.floor(limit || 50), 200));
        const data = await this.runArcJson(['edit', 'list', '--workspace', this.workspaceRoot, '--limit', String(safeLimit), '--json']);
        return {
            plans: Array.isArray(data.plans) ? (data.plans as Record<string, unknown>[]).map(plan => this.toPlan(plan)) : [],
            count: Number(data.count || 0),
        };
    }

    async showEditPlan(planId: string): Promise<EditPlanInfo> {
        this.validatePlanId(planId);
        return this.toPlan(await this.runArcJson(['edit', 'show', '--workspace', this.workspaceRoot, '--plan-id', planId, '--json']));
    }

    async approveEditPlan(planId: string, token: string): Promise<EditPlanApprovalResult> {
        this.validatePlanId(planId);
        if (!token || token.length > 512) {
            throw new ArcError(ArcErrorCode.INVALID_INPUT, 'invalid edit approval token');
        }
        const data = await this.runArcJson(['edit', 'approve', '--workspace', this.workspaceRoot, '--plan-id', planId, '--token', token, '--json']);
        return {
            version: Number(data.version || 1),
            approval_id: String(data.approval_id || ''),
            plan_id: String(data.plan_id || planId),
            token_hash: String(data.token_hash || ''),
            plan_hash: String(data.plan_hash || ''),
            approved_at: String(data.approved_at || ''),
        };
    }

    async diffEditPlan(planId: string, maxBytes = 131072): Promise<EditPlanDiffResult> {
        this.validatePlanId(planId);
        const safeMax = Math.max(1024, Math.min(Math.floor(maxBytes || 131072), 1024 * 1024));
        const data = await this.runArcJson(['edit', 'diff', '--workspace', this.workspaceRoot, '--plan-id', planId, '--max-bytes', String(safeMax), '--json']);
        const files = Array.isArray(data.files) ? data.files as Record<string, unknown>[] : [];
        return {
            plan_id: String(data.plan_id || planId),
            status: String(data.status || 'unknown'),
            diff: String(data.diff || ''),
            diff_truncated: Boolean(data.diff_truncated),
            binary: Boolean(data.binary),
            max_bytes: Number(data.max_bytes || safeMax),
            files: files.map(file => this.toFilePlan(file)),
        };
    }

    async applyEditPlan(planId: string, content: string, token: string): Promise<EditPlanApplyResult> {
        this.validatePlanId(planId);
        if (!token || token.length > 512) {
            throw new ArcError(ArcErrorCode.INVALID_INPUT, 'invalid edit approval token');
        }
        if (content.length > 1024 * 1024) {
            throw new ArcError(ArcErrorCode.INVALID_INPUT, 'edit content too large');
        }
        const data = await this.runArcJson(['edit', 'apply', '--workspace', this.workspaceRoot, '--plan-id', planId, '--content', content, '--approval-token', token, '--json']);
        return {
            applied: Boolean(data.applied),
            reason: String(data.reason || ''),
            transaction_id: data.transaction_id == null ? null : String(data.transaction_id),
            plan: data.plan && typeof data.plan === 'object' ? this.toPlan(data.plan as Record<string, unknown>) : undefined,
            audit_events: Array.isArray(data.audit_events) ? data.audit_events as Array<Record<string, unknown>> : [],
        };
    }

    private validatePlanId(planId: string): void {
        if (!PLAN_ID_RE.test(planId)) {
            throw new ArcError(ArcErrorCode.INVALID_INPUT, 'invalid edit plan id');
        }
    }

    private async runArcJson(args: string[]): Promise<Record<string, unknown>> {
        try {
            const output = await execArcCliAsync(args, {
                timeout: 10000,
            });
            const parsed: ArcEnvelope = JSON.parse(output);
            if (!parsed.ok || !parsed.data) {
                throw new ArcError(ArcErrorCode.RUN_FAILED, parsed?.error?.message || 'ARC edit CLI returned no data');
            }
            return parsed.data;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Edit plan bridge unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }

    private toPlan(raw: Record<string, unknown>): EditPlanInfo {
        const files = Array.isArray(raw.files) ? raw.files as Record<string, unknown>[] : [];
        return {
            version: Number(raw.version || 1),
            plan_id: String(raw.plan_id || ''),
            workspace_root: String(raw.workspace_root || this.workspaceRoot),
            policy: String(raw.policy || 'local-safe'),
            path: String(raw.path || ''),
            command: Array.isArray(raw.command) ? raw.command.map(String) : [],
            original_exists: Boolean(raw.original_exists),
            original_hash: String(raw.original_hash || ''),
            replacement_hash: String(raw.replacement_hash || ''),
            allowed: Boolean(raw.allowed),
            reason: String(raw.reason || ''),
            classification: String(raw.classification || 'unknown'),
            plan_path: raw.plan_path == null ? null : String(raw.plan_path),
            created_at: String(raw.created_at || ''),
            status: raw.status == null ? undefined : String(raw.status),
            files: files.map(file => this.toFilePlan(file)),
        };
    }

    private toFilePlan(file: Record<string, unknown>) {
        return {
            path: String(file.path || ''),
            command: Array.isArray(file.command) ? file.command.map(String) : [],
            original_exists: Boolean(file.original_exists),
            original_hash: String(file.original_hash || ''),
            replacement_hash: file.replacement_hash == null ? null : String(file.replacement_hash),
            patch_hash: file.patch_hash == null ? null : String(file.patch_hash),
            allowed: Boolean(file.allowed),
            reason: String(file.reason || ''),
            classification: String(file.classification || 'unknown'),
        };
    }
}
