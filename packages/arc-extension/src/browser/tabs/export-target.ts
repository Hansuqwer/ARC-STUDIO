export interface ExportTargetValidation {
    runtimeId: string;
    envName: string | null;
    valid: boolean;
    status: 'valid' | 'missing' | 'unsafe' | 'not-required';
    value: string | null;
    message: string;
    remediation: string;
}

const EXPORT_TARGET_ENV_BY_RUNTIME: Array<[RegExp, string]> = [
    [/crewai/i, 'ARC_CREWAI_EXPORT'],
    [/openai/i, 'OPENAI_AGENTS_EXPORT_PATH'],
    [/llama/i, 'LLAMAINDEX_EXPORT_PATH'],
];

const MODULE_ATTR_PATTERN = /^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*:[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*$/;
const UNSAFE_CHARS_PATTERN = /[\s;&|`$<>\\]/;

export function resolveExportTargetEnvName(runtimeId: string): string | null {
    return EXPORT_TARGET_ENV_BY_RUNTIME.find(([pattern]) => pattern.test(runtimeId))?.[1] || null;
}

export function validateExportTarget(
    runtimeId: string,
    env: Record<string, string | undefined> = {}
): ExportTargetValidation {
    const envName = resolveExportTargetEnvName(runtimeId);
    if (!envName) {
        return {
            runtimeId,
            envName: null,
            valid: true,
            status: 'not-required',
            value: null,
            message: 'No export target required for this runtime.',
            remediation: 'No action required.',
        };
    }

    const rawValue = env[envName]?.trim() || '';
    const remediation = `Set ${envName} to an env-ref module target, for example ${envName}=package.module:factory.`;

    if (!rawValue) {
        return {
            runtimeId,
            envName,
            valid: false,
            status: 'missing',
            value: null,
            message: `${envName} is not configured.`,
            remediation,
        };
    }

    if (!MODULE_ATTR_PATTERN.test(rawValue) || UNSAFE_CHARS_PATTERN.test(rawValue)) {
        return {
            runtimeId,
            envName,
            valid: false,
            status: 'unsafe',
            value: null,
            message: `${envName} must use module:attr syntax.`,
            remediation,
        };
    }

    return {
        runtimeId,
        envName,
        valid: true,
        status: 'valid',
        value: rawValue,
        message: `${envName} is configured.`,
        remediation: 'No action required.',
    };
}
