import { RuntimeCapabilityReport } from '../../../common/arc-protocol';
import {
    buildRuntimeRemediationPlan,
    isSafeRemediationCommand,
    redactRemediationText,
} from '../runtime-remediation';

function capability(overrides: Partial<RuntimeCapabilityReport> = {}): RuntimeCapabilityReport {
    return {
        runtime_id: 'swarmgraph',
        detected: true,
        can_run: true,
        availability: 'available',
        detected_artifacts: [],
        required_env: [],
        requires_paid_calls: false,
        doctor_actions: [],
        ...overrides,
    };
}

describe('runtime remediation helpers', () => {
    it('builds runnable plan with status and profile guidance', () => {
        const plan = buildRuntimeRemediationPlan(capability());

        expect(plan.status).toBe('runnable');
        expect(plan.runtimeId).toBe('swarmgraph');
        expect(plan.steps[0]).toMatchObject({ id: 'runtime-status', kind: 'status' });
        expect(plan.steps.some(step => step.kind === 'profile')).toBe(true);
    });

    it('normalizes missing env vars without secret values', () => {
        const plan = buildRuntimeRemediationPlan(
            capability({
                can_run: false,
                availability: 'provider_gated',
                required_env: ['OPENAI_API_KEY', 'ARC_CONFIRM_PROVIDER_CALLS'],
                requires_paid_calls: true,
            })
        );

        const envStep = plan.steps.find(step => step.kind === 'env');
        expect(plan.status).toBe('gated');
        expect(envStep?.copyText).toBe('OPENAI_API_KEY\nARC_CONFIRM_PROVIDER_CALLS');
        expect(envStep?.description).toContain('env-var references only');
        expect(envStep?.description).not.toContain('sk-');
    });

    it('omits unsafe doctor action commands', () => {
        const plan = buildRuntimeRemediationPlan(
            capability({
                can_run: false,
                availability: 'missing_deps',
                doctor_actions: [
                    {
                        id: 'provider-login',
                        label: 'Provider login',
                        description: 'Run provider login manually',
                        command: 'provider login --token SECRET_TOKEN=abc123',
                        safe_to_auto_run: false,
                    },
                ],
            })
        );

        const action = plan.steps.find(step => step.id === 'doctor-provider-login');
        expect(action?.manual).toBe(true);
        expect(action?.command).toBeUndefined();
        expect(action?.copyText).toBeUndefined();
        expect(action?.description).toContain('command hidden');
    });

    it('keeps safe doctor action commands copyable', () => {
        const plan = buildRuntimeRemediationPlan(
            capability({
                can_run: false,
                availability: 'missing_deps',
                doctor_actions: [
                    {
                        id: 'install',
                        label: 'Install deps',
                        description: 'Install runtime dependencies',
                        command: 'pip install -r requirements.txt',
                        safe_to_auto_run: true,
                    },
                ],
            })
        );

        const action = plan.steps.find(step => step.id === 'doctor-install');
        expect(action?.manual).toBe(false);
        expect(action?.copyText).toBe('pip install -r requirements.txt');
    });

    it('redacts obvious secrets, tokens, passwords, api keys', () => {
        const text = redactRemediationText(
            'OPENAI_API_KEY=sk-test TOKEN=abc PASSWORD=hunter2 curl -H "Authorization: Bearer deadbeef" https://user:pass@example.com'
        );

        expect(text).toContain('OPENAI_API_KEY=<redacted>');
        expect(text).toContain('TOKEN=<redacted>');
        expect(text).toContain('PASSWORD=<redacted>');
        expect(text).toContain('Bearer <redacted>');
        expect(text).toContain('https://user:<redacted>@example.com');
        expect(text).not.toContain('sk-test');
        expect(text).not.toContain('hunter2');
        expect(isSafeRemediationCommand('OPENAI_API_KEY=sk-test arc run')).toBe(false);
    });
});
