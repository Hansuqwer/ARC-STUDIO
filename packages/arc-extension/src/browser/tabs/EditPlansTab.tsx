/**
 * Edit Plans Tab
 *
 * Metadata-only review surface for saved ARC edit plans. Replacement content
 * and full diffs are intentionally absent from saved plan records.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, EditPlanInfo } from '../../common/arc-protocol';

export interface EditPlansTabProps {
    arcService: ArcService;
}

export const EditPlansTab: React.FC<EditPlansTabProps> = ({ arcService }) => {
    const [plans, setPlans] = React.useState<EditPlanInfo[]>([]);
    const [selected, setSelected] = React.useState<EditPlanInfo | null>(null);
    const [token, setToken] = React.useState('');
    const [loading, setLoading] = React.useState(true);
    const [message, setMessage] = React.useState<string | null>(null);
    const [error, setError] = React.useState<string | null>(null);

    const load = React.useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await arcService.listEditPlans(50);
            setPlans(result.plans);
            if (result.plans.length && !selected) {
                setSelected(result.plans[0]);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to load edit plans');
        } finally {
            setLoading(false);
        }
    }, [arcService, selected]);

    React.useEffect(() => {
        load();
    }, [load]);

    const showPlan = async (planId: string) => {
        setError(null);
        setMessage(null);
        try {
            setSelected(await arcService.showEditPlan(planId));
        } catch (err: any) {
            setError(err.message || 'Failed to show edit plan');
        }
    };

    const approve = async () => {
        if (!selected || !token.trim()) {
            setError('Approval token required.');
            return;
        }
        setError(null);
        try {
            const result = await arcService.approveEditPlan(selected.plan_id, token.trim());
            setMessage(`Approved ${result.plan_id}. Apply still uses existing CLI hash/staleness checks.`);
            setToken('');
        } catch (err: any) {
            setError(err.message || 'Failed to approve edit plan');
        }
    };

    return (
        <div className='arc-edit-plans' role='region' aria-label='Edit Plans'>
            <div className='arc-edit-plans__header'>
                <h3>Edit Plans</h3>
                <button className='arc-edit-plans__refresh' onClick={load}>Refresh</button>
            </div>
            <p className='arc-edit-plans__scope'>
                Local metadata-only review of saved edit plans. Replacement content and full diffs are not persisted here.
            </p>
            {loading && <p className='arc-edit-plans__loading'>Loading saved edit plans...</p>}
            {error && <div className='arc-edit-plans__error' role='alert'>Error: {error}</div>}
            {message && <div className='arc-edit-plans__message' role='status'>{message}</div>}
            {!loading && plans.length === 0 && <p className='arc-edit-plans__empty'>No saved edit plans.</p>}
            {!loading && plans.length > 0 && (
                <div className='arc-edit-plans__layout'>
                    <div className='arc-edit-plans__list' aria-label='Saved edit plans'>
                        {plans.map(plan => (
                            <button
                                key={plan.plan_id}
                                className='arc-edit-plans__item'
                                onClick={() => showPlan(plan.plan_id)}
                            >
                                <span>{plan.plan_id}</span>
                                <span>{plan.status || 'unknown'}</span>
                            </button>
                        ))}
                    </div>
                    {selected && (
                        <div className='arc-edit-plans__detail' aria-label='Selected edit plan'>
                            <h4>{selected.plan_id}</h4>
                            <p>Status: {selected.status || 'unknown'}</p>
                            <p>Decision: {selected.allowed ? 'allow' : 'deny'}</p>
                            <p>Reason: {selected.reason}</p>
                            <p>Policy: {selected.policy}</p>
                            <div className='arc-edit-plans__files'>
                                <h5>Files</h5>
                                {selected.files.map(file => (
                                    <div key={file.path} className='arc-edit-plans__file'>
                                        <strong>{file.path}</strong>
                                        <span>{file.classification}</span>
                                        <span>original {file.original_hash.slice(0, 12)}</span>
                                        {file.replacement_hash && <span>replacement {file.replacement_hash.slice(0, 12)}</span>}
                                        {file.patch_hash && <span>patch {file.patch_hash.slice(0, 12)}</span>}
                                    </div>
                                ))}
                            </div>
                            <label className='arc-edit-plans__approval'>
                                Approval token
                                <input value={token} onChange={event => setToken(event.currentTarget.value)} />
                            </label>
                            <button
                                className='arc-edit-plans__approve'
                                onClick={approve}
                                disabled={!selected.allowed || selected.status === 'stale'}
                            >
                                Approve Saved Plan
                            </button>
                            <p className='arc-edit-plans__handoff'>
                                Apply handoff: use `arc edit apply --plan-id {selected.plan_id} --content &lt;text&gt; --approval-token &lt;token&gt;`.
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};
