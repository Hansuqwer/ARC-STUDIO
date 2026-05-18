/**
 * ConfigTab runtime remediation contract tests.
 * Static source checks only; no Theia/jsdom runtime required.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('ConfigTab runtime remediation contract', () => {
    let source: string;
    let helperSource: string;
    let wizardSource: string;

    beforeAll(async () => {
        source = await fs.readFile(
            path.join(__dirname, '..', '..', '..', 'src', 'browser', 'tabs', 'ConfigTab.tsx'),
            'utf-8'
        );
        helperSource = await fs.readFile(
            path.join(__dirname, '..', '..', '..', 'src', 'browser', 'tabs', 'runtime-remediation.ts'),
            'utf-8'
        );
        const wizardStart = source.indexOf('arc-studio-config__runtime-setup-wizard');
        const wizardEnd = source.indexOf("<div className='arc-studio-config__section'", wizardStart + 1);
        wizardSource = source.slice(wizardStart, wizardEnd);
    });

    it('imports and uses the runtime remediation planner', () => {
        expect(source).toMatch(/buildRuntimeRemediationPlan/);
        expect(source).toMatch(/from '\.\/runtime-remediation'/);
        expect(source).toMatch(/buildRuntimeRemediationPlan\(/);
    });

    it('renders the runtime setup wizard with exact safety copy and classes', () => {
        expect(source).toMatch(/arc-studio-config__runtime-setup-wizard/);
        expect(source).toMatch(/arc-studio-config__runtime-remediation-step/);
        expect(source).toMatch(/arc-studio-config__runtime-remediation-command/);
        expect(source).toMatch(/arc-studio-config__runtime-remediation-copy/);
        expect(source).toMatch(/Runtime Setup Wizard/);
        expect(source).toMatch(/No raw secrets are captured or displayed/);
        expect(source).toMatch(/Env var names only; values stay in your shell\/keychain/);
    });

    it('derives the selected capability by runtime id', () => {
        expect(source).toMatch(/runtime_id === selectedRuntime/);
    });

    it('copies only safe remediation step text', () => {
        expect(source).toMatch(/copyText/);
        expect(source).toMatch(/safe/);
        expect(source).toMatch(/step\.(?:command|text|summary|details|copyText)/);
        expect(source).not.toMatch(/navigator\.clipboard\.writeText\([^)]*process\.env/);
        expect(source).not.toMatch(/navigator\.clipboard\.writeText\([^)]*required_env/);
    });

    it('does not add network/provider/live-call or raw-secret persistence claims', () => {
        expect(source).not.toMatch(/fetch\(/);
        expect(wizardSource).not.toMatch(/provider proxy/i);
        expect(wizardSource).not.toMatch(/live API calls/i);
        expect(wizardSource).not.toMatch(/persist(?:s|ed|ing)? raw (?:secret|credential|key|token|password)s?/i);
        expect(wizardSource).not.toMatch(/save(?:s|d|ing)? raw (?:secret|credential|key|token|password)s?/i);
        expect(wizardSource).not.toMatch(/store(?:s|d|ing)? raw (?:secret|credential|key|token|password)s?/i);
    });

    it('exports runtime remediation helper contracts', () => {
        expect(helperSource).toMatch(/export interface RuntimeRemediationStep/);
        expect(helperSource).toMatch(/export interface RuntimeRemediationPlan/);
        expect(helperSource).toMatch(/export function buildRuntimeRemediationPlan/);
        expect(helperSource).toMatch(/export function isSafeRemediationCommand/);
        expect(helperSource).toMatch(/export function redactRemediationText/);
    });
});
