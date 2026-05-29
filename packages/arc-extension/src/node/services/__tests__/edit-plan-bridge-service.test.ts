import { execFileSync } from 'child_process';
import { ArcErrorCode } from '../../../common/arc-protocol';
import { EditPlanBridgeService } from '../edit-plan-bridge-service';

jest.mock('child_process', () => ({
    execFileSync: jest.fn(),
}));

const mockExecFileSync = execFileSync as jest.Mock;

function ok(data: Record<string, unknown>): string {
    return JSON.stringify({ ok: true, data });
}

describe('EditPlanBridgeService', () => {
    let service: EditPlanBridgeService;

    beforeEach(() => {
        jest.clearAllMocks();
        service = new EditPlanBridgeService('/workspace/test');
    });

    it('lists edit plans through argv-only ARC CLI', () => {
        mockExecFileSync.mockReturnValue(ok({ plans: [], count: 0 }));
        const result = service.listEditPlans(25);
        expect(result.count).toBe(0);
        expect(mockExecFileSync).toHaveBeenCalledWith(
            'arc',
            ['edit', 'list', '--workspace', '/workspace/test', '--limit', '25', '--json'],
            expect.objectContaining({ windowsHide: true })
        );
        const opts = mockExecFileSync.mock.calls[0][2] as Record<string, unknown>;
        expect(opts.shell).toBeUndefined();
    });

    it('shows one metadata-only edit plan', () => {
        mockExecFileSync.mockReturnValue(ok({
            version: 1,
            plan_id: 'edit-abc',
            workspace_root: '/workspace/test',
            policy: 'local-safe',
            path: 'a.txt',
            command: ['python'],
            original_exists: true,
            original_hash: 'h1',
            replacement_hash: 'h2',
            allowed: true,
            reason: 'all files allowed',
            classification: 'writes_workspace',
            created_at: 'now',
            status: 'present',
            files: [{ path: 'a.txt', command: ['python'], original_exists: true, original_hash: 'h1', replacement_hash: 'h2', allowed: true, reason: 'allowed', classification: 'writes_workspace' }],
        }));
        const plan = service.showEditPlan('edit-abc');
        expect(plan.plan_id).toBe('edit-abc');
        expect(plan.files[0].path).toBe('a.txt');
        expect(JSON.stringify(plan)).not.toContain('replacement content');
    });

    it('rejects unsafe plan ids before invoking CLI', () => {
        expect(() => service.showEditPlan('../x')).toThrow(expect.objectContaining({ code: ArcErrorCode.INVALID_INPUT }));
        expect(mockExecFileSync).not.toHaveBeenCalled();
    });

    it('approves a plan through scoped token CLI command', () => {
        mockExecFileSync.mockReturnValue(ok({ version: 1, approval_id: 'ap-1', plan_id: 'edit-abc', token_hash: 'th', plan_hash: 'ph', approved_at: 'now' }));
        const result = service.approveEditPlan('edit-abc', 'tok');
        expect(result.approval_id).toBe('ap-1');
        expect(mockExecFileSync).toHaveBeenCalledWith(
            'arc',
            ['edit', 'approve', '--workspace', '/workspace/test', '--plan-id', 'edit-abc', '--token', 'tok', '--json'],
            expect.any(Object)
        );
    });
});
