import { resolveExportTargetEnvName, validateExportTarget } from '../export-target';

describe('export target helpers', () => {
    it('accepts env-ref module attr export targets', () => {
        const result = validateExportTarget('crewai+swarmgraph', {
            ARC_CREWAI_EXPORT: 'arc_exports.crewai:build_crew',
        });

        expect(result).toMatchObject({
            envName: 'ARC_CREWAI_EXPORT',
            valid: true,
            status: 'valid',
            value: 'arc_exports.crewai:build_crew',
        });
    });

    it('reports missing required export target with remediation', () => {
        const result = validateExportTarget('openai-agents', {});

        expect(result).toMatchObject({
            envName: 'OPENAI_AGENTS_EXPORT_PATH',
            valid: false,
            status: 'missing',
            value: null,
        });
        expect(result.remediation).toContain('OPENAI_AGENTS_EXPORT_PATH=package.module:factory');
    });

    it('rejects unsafe values and raw paths', () => {
        expect(validateExportTarget('crewai', { ARC_CREWAI_EXPORT: '/tmp/export.py' }).status).toBe('unsafe');
        expect(validateExportTarget('crewai', { ARC_CREWAI_EXPORT: 'pkg.mod:factory; rm -rf .' }).status).toBe('unsafe');
    });

    it('does not require targets for unrelated runtimes', () => {
        const result = validateExportTarget('swarmgraph', {});

        expect(resolveExportTargetEnvName('swarmgraph')).toBeNull();
        expect(result).toMatchObject({ valid: true, status: 'not-required', envName: null });
    });
});
