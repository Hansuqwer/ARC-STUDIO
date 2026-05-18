import { RuntimeCapabilityReport } from '../../common/arc-protocol';

export type RuntimeRemediationStepKind =
    | 'status'
    | 'env'
    | 'doctor'
    | 'artifact'
    | 'dependency'
    | 'profile'
    | 'export-target';

export interface RuntimeRemediationStep {
    id: string;
    kind: RuntimeRemediationStepKind;
    title: string;
    description: string;
    manual: boolean;
    copyText?: string;
    command?: string;
    envVars?: string[];
}

export interface RuntimeRemediationPlan {
    runtimeId: string;
    status: 'unknown' | 'runnable' | 'unavailable' | 'gated';
    summary: string;
    steps: RuntimeRemediationStep[];
    artifacts: string[];
}

const SECRET_ASSIGNMENT = /\b([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL)[A-Z0-9_]*)\s*=\s*([^\s'";&]+)/gi;
const BEARER_TOKEN = /\bBearer\s+[A-Za-z0-9._~+/=-]+/gi;
const SECRET_URL = /(https?:\/\/[^\s:@/]+:)[^\s@/]+(@[^\s]+)/gi;

export function isSafeRemediationCommand(command: string | null | undefined): boolean {
    if (!command) {
        return false;
    }
    return redactRemediationText(command) === command;
}

export function redactRemediationText(text: string): string {
    return text
        .replace(SECRET_ASSIGNMENT, '$1=<redacted>')
        .replace(BEARER_TOKEN, 'Bearer <redacted>')
        .replace(SECRET_URL, '$1<redacted>$2');
}

export function buildRuntimeRemediationPlan(
    report: RuntimeCapabilityReport | null | undefined
): RuntimeRemediationPlan {
    if (!report) {
        return {
            runtimeId: 'unknown',
            status: 'unknown',
            summary: 'No runtime capability report available.',
            steps: [],
            artifacts: [],
        };
    }

    const status = getStatus(report);
    const runtimeId = report.runtime_id;
    const steps: RuntimeRemediationStep[] = [];

    steps.push({
        id: 'runtime-status',
        kind: 'status',
        title: status === 'runnable' ? 'Runtime runnable' : 'Runtime not runnable',
        description: redactRemediationText(report.reason || report.availability || status),
        manual: true,
    });

    if (report.required_env.length > 0 || report.requires_paid_calls) {
        steps.push({
            id: 'env-refs',
            kind: 'env',
            title: 'Configure provider env refs',
            description: `Set env-var references only: ${report.required_env.join(', ') || 'provider-specific env refs'}. Never paste raw secret values into ARC config.`,
            manual: true,
            copyText: report.required_env.join('\n') || undefined,
            envVars: [...report.required_env],
        });
    }

    for (const action of report.doctor_actions) {
        const safeCommand = action.safe_to_auto_run && isSafeRemediationCommand(action.command);
        steps.push({
            id: `doctor-${action.id}`,
            kind: 'doctor',
            title: redactRemediationText(action.label),
            description: safeCommand
                ? redactRemediationText(action.description)
                : `${redactRemediationText(action.description)} Manual action required; command hidden because it is not safe to auto-run/copy.`,
            manual: !safeCommand,
            copyText: safeCommand ? action.command : undefined,
            command: safeCommand ? action.command : undefined,
        });
    }

    if (report.detected_artifacts.length > 0) {
        steps.push({
            id: 'detected-artifacts',
            kind: 'artifact',
            title: 'Detected artifacts',
            description: report.detected_artifacts.map(redactRemediationText).join(', '),
            manual: true,
        });
    }

    if (!report.can_run && report.doctor_actions.length === 0 && indicatesMissingSetup(report)) {
        steps.push({
            id: 'missing-dependencies',
            kind: 'dependency',
            title: 'Install or configure runtime dependencies',
            description: `Run ARC doctor for ${runtimeId}, install the adapter/CLI, then refresh runtime readiness.`,
            manual: true,
            copyText: `arc doctor runtime ${runtimeId}`,
        });
    }

    addRuntimeGuidance(runtimeId, steps);

    return {
        runtimeId,
        status,
        summary: buildSummary(runtimeId, status, steps),
        steps,
        artifacts: report.detected_artifacts.map(redactRemediationText),
    };
}

function getStatus(report: RuntimeCapabilityReport): RuntimeRemediationPlan['status'] {
    if (report.can_run) {
        return 'runnable';
    }
    if (report.required_env.length > 0 || report.requires_paid_calls || /gate|profile|paid|env/i.test(report.availability)) {
        return 'gated';
    }
    return 'unavailable';
}

function indicatesMissingSetup(report: RuntimeCapabilityReport): boolean {
    return /missing|dependency|deps|install|not[_ -]?found|unavailable|config/i.test(
        `${report.availability} ${report.reason || ''}`
    );
}

function addRuntimeGuidance(runtimeId: string, steps: RuntimeRemediationStep[]): void {
    const normalized = runtimeId.toLowerCase();
    if (normalized.includes('crewai')) {
        steps.push(exportTargetStep('crewai', 'CrewAI export target', 'CREWAI_EXPORT_PATH'));
    }
    if (normalized.includes('openai')) {
        steps.push(exportTargetStep('openai', 'OpenAI Agents export target', 'OPENAI_AGENTS_EXPORT_PATH'));
    }
    if (normalized.includes('llama')) {
        steps.push(exportTargetStep('llamaindex', 'LlamaIndex export target', 'LLAMAINDEX_EXPORT_PATH'));
    }
    if (normalized.includes('swarmgraph') || normalized.includes('langgraph')) {
        steps.push({
            id: 'runtime-profile',
            kind: 'profile',
            title: 'Select a compatible run profile',
            description: 'Use a dry-run/local profile unless paid provider calls are explicitly confirmed.',
            manual: true,
        });
    }
}

function exportTargetStep(id: string, title: string, envName: string): RuntimeRemediationStep {
    return {
        id: `${id}-export-target`,
        kind: 'export-target',
        title,
        description: `Configure ${envName} as an env-var reference for generated export output. Raw values are not displayed.`,
        manual: true,
        copyText: envName,
        envVars: [envName],
    };
}

function buildSummary(
    runtimeId: string,
    status: RuntimeRemediationPlan['status'],
    steps: RuntimeRemediationStep[]
): string {
    if (status === 'runnable') {
        return `${runtimeId} is runnable. ${steps.length - 1} optional setup step(s).`;
    }
    return `${runtimeId} is ${status}. ${steps.length - 1} remediation step(s).`;
}
