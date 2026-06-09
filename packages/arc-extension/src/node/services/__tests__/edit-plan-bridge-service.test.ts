/**
 * Phase 284 R-PERF4: EditPlanBridgeService async (non-blocking) tests.
 * All methods now use execArcCliAsync instead of execFileSync.
 */
import { ArcErrorCode } from '../../../common/arc-protocol';
import { EditPlanBridgeService } from '../edit-plan-bridge-service';

// Mock the arc-cli-utils module so execArcCliAsync is controllable
jest.mock('../arc-cli-utils', () => ({
    execArcCliAsync: jest.fn(),
    buildArcCliEnv: jest.fn().mockReturnValue({}),
}));

import { execArcCliAsync } from '../arc-cli-utils';
const mockExecArcCliAsync = execArcCliAsync as jest.Mock;

function ok(data: Record<string, unknown>): string {
    return JSON.stringify({ ok: true, data });
}

describe('EditPlanBridgeService (async)', () => {
    let service: EditPlanBridgeService;

    beforeEach(() => {
        jest.clearAllMocks();
        service = new EditPlanBridgeService('/workspace/test');
    });

    it('listEditPlans is async and uses execArcCliAsync', async () => {
        mockExecArcCliAsync.mockResolvedValue(ok({ plans: [], count: 0 }));
        const result = await service.listEditPlans(25);
        expect(result.count).toBe(0);
        expect(mockExecArcCliAsync).toHaveBeenCalledWith(
            ['edit', 'list', '--workspace', '/workspace/test', '--limit', '25', '--json'],
            expect.any(Object)
        );
        // Verify it does NOT use shell (no shell: true in options)
        const opts = mockExecArcCliAsync.mock.calls[0][1] as Record<string, unknown>;
        expect(opts.shell).toBeUndefined();
    });

    it('showEditPlan is async and returns EditPlanInfo', async () => {
        mockExecArcCliAsync.mockResolvedValue(ok({
            version: 1, plan_id: 'edit-abc', workspace_root: '/workspace/test',
            policy: 'local-safe', path: 'a.txt', command: ['python'],
            original_exists: true, original_hash: 'h1', replacement_hash: 'h2',
            allowed: true, reason: 'allowed', classification: 'writes_workspace',
            created_at: 'now', status: 'present',
            files: [{ path: 'a.txt', command: ['python'], original_exists: true,
                original_hash: 'h1', replacement_hash: 'h2', allowed: true,
                reason: 'allowed', classification: 'writes_workspace' }],
        }));
        const plan = await service.showEditPlan('edit-abc');
        expect(plan.plan_id).toBe('edit-abc');
        expect(plan.files[0].path).toBe('a.txt');
        expect(JSON.stringify(plan)).not.toContain('replacement content');
    });

    it('rejects unsafe plan ids before invoking CLI', async () => {
        await expect(service.showEditPlan('../x')).rejects.toMatchObject({ code: ArcErrorCode.INVALID_INPUT });
        expect(mockExecArcCliAsync).not.toHaveBeenCalled();
    });

    it('approveEditPlan is async', async () => {
        mockExecArcCliAsync.mockResolvedValue(ok({
            version: 1, approval_id: 'ap-1', plan_id: 'edit-abc',
            token_hash: 'th', plan_hash: 'ph', approved_at: 'now'
        }));
        const result = await service.approveEditPlan('edit-abc', 'tok');
        expect(result.approval_id).toBe('ap-1');
        expect(mockExecArcCliAsync).toHaveBeenCalledWith(
            ['edit', 'approve', '--workspace', '/workspace/test', '--plan-id', 'edit-abc', '--token', 'tok', '--json'],
            expect.any(Object)
        );
    });

    it('diffEditPlan is async and returns diff content', async () => {
        mockExecArcCliAsync.mockResolvedValue(ok({
            plan_id: 'edit-abc', status: 'present', diff: '-old\n+new\n',
            diff_truncated: false, binary: false, max_bytes: 131072, files: []
        }));
        const result = await service.diffEditPlan('edit-abc');
        expect(result.diff).toContain('+new');
    });

    it('applyEditPlan is async', async () => {
        mockExecArcCliAsync.mockResolvedValue(ok({
            applied: true, reason: 'applied', transaction_id: 'txn-abc', audit_events: []
        }));
        const result = await service.applyEditPlan('edit-abc', 'new\n', 'tok');
        expect(result.transaction_id).toBe('txn-abc');
    });
});
