/**
 * Edit Plans Tab
 *
 * Review surface for saved ARC edit plans. Replacement content is not persisted;
 * real unified diff content is loaded through the Python bridge with caps.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, EditPlanInfo } from '../../common/arc-protocol';
import { useAsyncState } from '../hooks/useAsyncState';

export interface EditPlansTabProps {
    arcService: ArcService;
}

export const EditPlansTab: React.FC<EditPlansTabProps> = ({ arcService }) => {
    const { data: plansResult, loading, error, reload: load } = useAsyncState(
        () => arcService.listEditPlans(50),
        [arcService],
    );
    const plans = plansResult?.plans ?? [];
    const [selected, setSelected] = React.useState<EditPlanInfo | null>(null);
    const [token, setToken] = React.useState('');
    const [content, setContent] = React.useState('');
    const [diff, setDiff] = React.useState<string | null>(null);
    const [message, setMessage] = React.useState<string | null>(null);
    const [mutationError, setMutationError] = React.useState<string | null>(null);

    const showPlan = async (planId: string) => {
        setMutationError(null);
        setMessage(null);
        try {
            const plan = await arcService.showEditPlan(planId);
            setSelected(plan);
            const diffResult = await arcService.diffEditPlan(planId, 131072);
            setDiff(diffResult.binary ? 'Binary diff blocked.' : diffResult.diff + (diffResult.diff_truncated ? '\n[diff truncated]' : ''));
        } catch (err: any) {
            setMutationError(err.message || 'Failed to show edit plan');
        }
    };

    const apply = async () => {
        if (!selected || !token.trim()) {
            setMutationError('Approval token required.');
            return;
        }
        setMutationError(null);
        try {
            const result = await arcService.applyEditPlan(selected.plan_id, content, token.trim());
            setMessage(result.applied ? `Applied ${selected.plan_id} transaction ${result.transaction_id || 'n/a'}.` : `Not applied: ${result.reason}`);
            load();
        } catch (err: any) {
            setMutationError(err.message || 'Failed to apply edit plan');
        }
    };

    const approve = async () => {
        if (!selected || !token.trim()) {
            setMutationError('Approval token required.');
            return;
        }
        setMutationError(null);
        try {
            const result = await arcService.approveEditPlan(selected.plan_id, token.trim());
            setMessage(`Approved ${result.plan_id}. Apply still uses existing CLI hash/staleness checks.`);
            setToken('');
        } catch (err: any) {
            setMutationError(err.message || 'Failed to approve edit plan');
        }
    };

    return (
        <div className='arc-edit-plans' role='region' aria-label='Edit Plans'>
            <div className='arc-edit-plans__header'>
                <h3>Edit Plans</h3>
                <button className='arc-edit-plans__refresh' onClick={load}>Refresh</button>
            </div>
            <p className='arc-edit-plans__scope'>
                Local review of saved edit plans. Replacement content is not persisted; diff/apply use the Python sandbox and ARC transaction gates.
            </p>
            {loading && <p className='arc-edit-plans__loading'>Loading saved edit plans...</p>}
            {error && <div className='arc-edit-plans__error' role='alert'>Error: {error}</div>}
            {mutationError && <div className='arc-edit-plans__error' role='alert'>Error: {mutationError}</div>}
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
                            <pre className='arc-edit-plans__diff' aria-label='Edit plan diff'>
                                {diff || 'Select a plan to load diff content.'}
                            </pre>
                            <label className='arc-edit-plans__approval'>
                                Approval token
                                <input value={token} onChange={event => setToken(event.currentTarget.value)} />
                            </label>
                            <label className='arc-edit-plans__content'>
                                Replacement content for apply
                                <textarea value={content} onChange={event => setContent(event.currentTarget.value)} />
                            </label>
                            <button
                                className='arc-edit-plans__approve'
                                onClick={approve}
                                disabled={!selected.allowed || selected.status === 'stale'}
                            >
                                Approve Saved Plan
                            </button>
                            <button
                                className='arc-edit-plans__apply'
                                onClick={apply}
                                disabled={!selected.allowed || selected.status === 'stale'}
                            >
                                Apply Through Gates
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
